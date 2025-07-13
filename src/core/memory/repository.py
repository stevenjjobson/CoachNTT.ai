"""
Safe memory repository with mandatory abstraction enforcement.

Provides database access layer for memory operations with built-in safety validation.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

import asyncpg
from asyncpg import Pool

from .abstract_models import (
    AbstractMemoryEntry,
    SafeInteraction,
    ValidationStatus,
    InteractionType,
    MemoryMetadata,
    Reference,
    ReferenceType,
    AbstractionMapping,
)
from .validator import MemoryValidator


logger = logging.getLogger(__name__)


class SafeMemoryRepository:
    """
    Repository for safe memory storage with mandatory validation.
    
    All memory operations go through validation before storage.
    """
    
    def __init__(self, db_pool: Pool):
        """
        Initialize repository with database connection pool.
        
        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        self.validator = MemoryValidator()
    
    async def create_memory(
        self,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
        auto_abstract: bool = True
    ) -> AbstractMemoryEntry:
        """
        Create a new memory entry with automatic abstraction.
        
        Args:
            prompt: The original prompt
            response: The original response
            metadata: Additional metadata
            auto_abstract: Whether to automatically abstract content
            
        Returns:
            Created AbstractMemoryEntry
            
        Raises:
            ValueError: If validation fails
        """
        # Combine content for abstraction
        full_content = f"{prompt}\n{response}"
        
        if auto_abstract:
            # Automatically abstract the content
            abstracted_content, mappings = self.validator.auto_abstract_content(full_content)
            abstracted_parts = abstracted_content.split('\n', 1)
            abstracted_prompt = abstracted_parts[0]
            abstracted_response = abstracted_parts[1] if len(abstracted_parts) > 1 else ""
        else:
            # Use content as-is (must already be abstracted)
            abstracted_prompt = prompt
            abstracted_response = response
            mappings = {}
        
        # Create memory entry
        memory = AbstractMemoryEntry(
            abstracted_prompt=abstracted_prompt,
            abstracted_response=abstracted_response,
            abstracted_content=metadata or {},
            abstraction_mapping=AbstractionMapping(mappings=mappings)
        )
        
        # Add references based on detected mappings
        for concrete, placeholder in mappings.items():
            # Determine reference type
            if '/' in concrete or '\\' in concrete:
                ref_type = ReferenceType.FILE_PATH
            elif '://' in concrete:
                ref_type = ReferenceType.URL
            elif '@' in concrete and '.' in concrete:
                ref_type = ReferenceType.USER_DATA
            elif any(key in concrete.lower() for key in ['password', 'token', 'key']):
                ref_type = ReferenceType.CREDENTIAL
            else:
                ref_type = ReferenceType.VARIABLE
            
            memory.add_reference(ref_type, concrete, placeholder)
        
        # Validate the memory
        validation_result = self.validator.validate_memory_entry(memory)
        
        if not validation_result.is_valid:
            raise ValueError(
                f"Memory validation failed: {validation_result.violations}"
            )
        
        # Store in database
        await self._store_memory(memory)
        
        return memory
    
    async def create_interaction(
        self,
        memory: AbstractMemoryEntry,
        session_id: UUID,
        interaction_type: InteractionType,
        metadata: Optional[MemoryMetadata] = None
    ) -> SafeInteraction:
        """
        Create a new interaction linked to a memory.
        
        Args:
            memory: The associated memory entry
            session_id: Session identifier
            interaction_type: Type of interaction
            metadata: Additional metadata
            
        Returns:
            Created SafeInteraction
            
        Raises:
            ValueError: If validation fails
        """
        interaction = SafeInteraction(
            session_id=session_id,
            interaction_type=interaction_type,
            abstraction_id=memory.memory_id,
            metadata=metadata or MemoryMetadata()
        )
        
        # Validate interaction
        errors = self.validator.validate_interaction(interaction, memory)
        if errors:
            raise ValueError(f"Interaction validation failed: {errors}")
        
        # Store in database
        await self._store_interaction(interaction)
        
        return interaction
    
    async def get_memory(self, memory_id: UUID) -> Optional[AbstractMemoryEntry]:
        """
        Retrieve a memory entry by ID.
        
        Args:
            memory_id: The memory ID to retrieve
            
        Returns:
            AbstractMemoryEntry if found, None otherwise
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    memory_id,
                    abstracted_content,
                    abstracted_prompt,
                    abstracted_response,
                    concrete_references,
                    abstraction_mapping,
                    safety_score,
                    validation_status,
                    quality_metrics_id,
                    created_at,
                    updated_at
                FROM safety.memory_abstractions
                WHERE memory_id = $1
            """, memory_id)
            
            if not row:
                return None
            
            return self._row_to_memory(row)
    
    async def get_interaction(self, interaction_id: UUID) -> Optional[SafeInteraction]:
        """
        Retrieve an interaction by ID.
        
        Args:
            interaction_id: The interaction ID to retrieve
            
        Returns:
            SafeInteraction if found, None otherwise
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    id as interaction_id,
                    session_id,
                    interaction_type,
                    abstraction_id,
                    weight,
                    last_accessed,
                    access_count,
                    tags,
                    metadata,
                    prompt_embedding,
                    response_embedding,
                    is_validated,
                    validation_errors,
                    created_at,
                    updated_at
                FROM public.cognitive_memory
                WHERE id = $1
            """, interaction_id)
            
            if not row:
                return None
            
            return self._row_to_interaction(row)
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        min_safety_score: float = 0.8
    ) -> List[Tuple[AbstractMemoryEntry, float]]:
        """
        Search for memories using text similarity.
        
        Args:
            query: Search query (will be abstracted)
            limit: Maximum results
            min_safety_score: Minimum safety score filter
            
        Returns:
            List of (memory, similarity_score) tuples
        """
        # Abstract the query
        abstracted_query, _ = self.validator.auto_abstract_content(query)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    ma.*,
                    similarity(
                        abstracted_prompt || ' ' || abstracted_response,
                        $1
                    ) as sim_score
                FROM safety.memory_abstractions ma
                WHERE validation_status = 'validated'
                    AND safety_score >= $2
                    AND similarity(
                        abstracted_prompt || ' ' || abstracted_response,
                        $1
                    ) > 0.3
                ORDER BY sim_score DESC
                LIMIT $3
            """, abstracted_query, min_safety_score, limit)
            
            results = []
            for row in rows:
                memory = self._row_to_memory(row)
                similarity = row['sim_score']
                results.append((memory, similarity))
            
            return results
    
    async def find_related_interactions(
        self,
        interaction_id: UUID,
        limit: int = 10
    ) -> List[SafeInteraction]:
        """
        Find interactions related to a given interaction.
        
        Args:
            interaction_id: Source interaction ID
            limit: Maximum results
            
        Returns:
            List of related interactions
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH source AS (
                    SELECT prompt_embedding, response_embedding
                    FROM public.cognitive_memory
                    WHERE id = $1
                )
                SELECT 
                    cm.*,
                    1 - (cm.prompt_embedding <=> s.prompt_embedding) as prompt_sim,
                    1 - (cm.response_embedding <=> s.response_embedding) as response_sim
                FROM public.cognitive_memory cm, source s
                WHERE cm.id != $1
                    AND cm.is_validated = true
                    AND (
                        1 - (cm.prompt_embedding <=> s.prompt_embedding) > 0.7
                        OR
                        1 - (cm.response_embedding <=> s.response_embedding) > 0.7
                    )
                ORDER BY GREATEST(
                    1 - (cm.prompt_embedding <=> s.prompt_embedding),
                    1 - (cm.response_embedding <=> s.response_embedding)
                ) DESC
                LIMIT $2
            """, interaction_id, limit)
            
            return [self._row_to_interaction(row) for row in rows]
    
    async def update_memory_score(
        self,
        memory_id: UUID,
        new_score: Decimal
    ) -> bool:
        """
        Update memory safety score (triggers revalidation).
        
        Args:
            memory_id: Memory to update
            new_score: New safety score
            
        Returns:
            True if updated, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE safety.memory_abstractions
                SET safety_score = $2,
                    updated_at = NOW()
                WHERE memory_id = $1
            """, memory_id, new_score)
            
            return result.split()[-1] == '1'
    
    async def reinforce_interaction(
        self,
        interaction_id: UUID,
        strength: float = 1.0
    ) -> Optional[Decimal]:
        """
        Reinforce an interaction (increase weight).
        
        Args:
            interaction_id: Interaction to reinforce
            strength: Reinforcement strength multiplier
            
        Returns:
            New weight if successful, None if not found
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE public.cognitive_memory
                SET weight = LEAST(1.0, weight * 1.5 * $2),
                    last_accessed = NOW(),
                    access_count = access_count + 1,
                    updated_at = NOW()
                WHERE id = $1
                RETURNING weight
            """, interaction_id, strength)
            
            if row:
                return Decimal(str(row['weight']))
            return None
    
    async def _store_memory(self, memory: AbstractMemoryEntry) -> None:
        """Store memory entry in database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO safety.memory_abstractions (
                    memory_id,
                    abstracted_content,
                    abstracted_prompt,
                    abstracted_response,
                    concrete_references,
                    abstraction_mapping,
                    safety_score,
                    validation_status,
                    quality_metrics_id,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                memory.memory_id,
                memory.abstracted_content,
                memory.abstracted_prompt,
                memory.abstracted_response,
                {
                    ref.placeholder: {
                        'type': ref.ref_type.value,
                        'value': ref.original_value,
                        'context': ref.context
                    }
                    for ref in memory.concrete_references
                },
                memory.abstraction_mapping.mappings,
                memory.safety_score,
                memory.validation_status.value,
                memory.quality_metrics_id,
                memory.created_at,
                memory.updated_at
            )
    
    async def _store_interaction(self, interaction: SafeInteraction) -> None:
        """Store interaction in database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO public.cognitive_memory (
                    id,
                    session_id,
                    interaction_type,
                    abstraction_id,
                    weight,
                    last_accessed,
                    access_count,
                    tags,
                    metadata,
                    prompt_embedding,
                    response_embedding,
                    is_validated,
                    validation_errors,
                    created_at,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                )
            """,
                interaction.interaction_id,
                interaction.session_id,
                interaction.interaction_type.value,
                interaction.abstraction_id,
                interaction.weight,
                interaction.last_accessed,
                interaction.access_count,
                interaction.metadata.tags,
                {
                    'context': interaction.metadata.context,
                    'source': interaction.metadata.source,
                    'language': interaction.metadata.language,
                    'framework': interaction.metadata.framework
                },
                interaction.prompt_embedding,
                interaction.response_embedding,
                interaction.is_validated,
                interaction.validation_errors,
                interaction.created_at,
                interaction.updated_at
            )
    
    def _row_to_memory(self, row: asyncpg.Record) -> AbstractMemoryEntry:
        """Convert database row to AbstractMemoryEntry."""
        memory = AbstractMemoryEntry(
            memory_id=row['memory_id'],
            abstracted_prompt=row['abstracted_prompt'],
            abstracted_response=row['abstracted_response'] or "",
            abstracted_content=row['abstracted_content'],
            safety_score=Decimal(str(row['safety_score'])),
            validation_status=ValidationStatus(row['validation_status']),
            quality_metrics_id=row['quality_metrics_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        # Reconstruct abstraction mapping
        if row['abstraction_mapping']:
            memory.abstraction_mapping = AbstractionMapping(
                mappings=row['abstraction_mapping']
            )
        
        # Reconstruct references
        if row['concrete_references']:
            for placeholder, ref_data in row['concrete_references'].items():
                memory.concrete_references.append(Reference(
                    ref_type=ReferenceType(ref_data['type']),
                    original_value=ref_data['value'],
                    placeholder=placeholder,
                    context=ref_data.get('context')
                ))
        
        return memory
    
    def _row_to_interaction(self, row: asyncpg.Record) -> SafeInteraction:
        """Convert database row to SafeInteraction."""
        metadata = MemoryMetadata(
            tags=row['tags'] or [],
            context=row['metadata'].get('context', {}) if row['metadata'] else {},
            source=row['metadata'].get('source') if row['metadata'] else None,
            language=row['metadata'].get('language') if row['metadata'] else None,
            framework=row['metadata'].get('framework') if row['metadata'] else None
        )
        
        return SafeInteraction(
            interaction_id=row.get('interaction_id') or row['id'],
            session_id=row['session_id'],
            interaction_type=InteractionType(row['interaction_type']),
            abstraction_id=row['abstraction_id'],
            weight=Decimal(str(row['weight'])),
            last_accessed=row['last_accessed'],
            access_count=row['access_count'],
            metadata=metadata,
            prompt_embedding=row['prompt_embedding'],
            response_embedding=row['response_embedding'],
            is_validated=row['is_validated'],
            validation_errors=row['validation_errors'] or [],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )