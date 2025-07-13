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
from .cluster_manager import MemoryClusterManager, ClusterType
from .decay_engine import MemoryDecayEngine
from ..embeddings import EmbeddingService, EmbeddingCache, ContentType
from ..intent import IntentEngine, IntentType, QueryAnalysis


logger = logging.getLogger(__name__)


class SafeMemoryRepository:
    """
    Repository for safe memory storage with mandatory validation.
    
    All memory operations go through validation before storage.
    """
    
    def __init__(
        self, 
        db_pool: Pool,
        embedding_service: Optional[EmbeddingService] = None,
        intent_engine: Optional[IntentEngine] = None
    ):
        """
        Initialize repository with database connection pool.
        
        Args:
            db_pool: AsyncPG connection pool
            embedding_service: Optional embedding service for enhanced similarity
            intent_engine: Optional intent engine for query analysis
        """
        self.db_pool = db_pool
        self.validator = MemoryValidator()
        self.cluster_manager = MemoryClusterManager(db_pool)
        self.decay_engine = MemoryDecayEngine(db_pool)
        
        # Initialize embedding service with cache
        if embedding_service is None:
            embedding_cache = EmbeddingCache(max_size=1000, default_ttl_seconds=3600)
            self.embedding_service = EmbeddingService(cache=embedding_cache)
        else:
            self.embedding_service = embedding_service
            
        # Initialize intent engine
        self.intent_engine = intent_engine
    
    async def create_memory(
        self,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
        auto_abstract: bool = True,
        generate_embeddings: bool = True,
        analyze_intent: bool = True,
        user_id: Optional[UUID] = None
    ) -> AbstractMemoryEntry:
        """
        Create a new memory entry with automatic abstraction, embeddings, and intent analysis.
        
        Args:
            prompt: The original prompt
            response: The original response
            metadata: Additional metadata
            auto_abstract: Whether to automatically abstract content
            generate_embeddings: Whether to generate embeddings automatically
            analyze_intent: Whether to analyze intent
            user_id: User ID for personalized intent analysis
            
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
        
        # Analyze intent if enabled and engine available
        intent_metadata = {}
        if analyze_intent and self.intent_engine:
            try:
                query_analysis = await self.intent_engine.analyze_query(
                    query=abstracted_prompt,
                    context=metadata,
                    user_id=user_id,
                    include_connections=False  # Don't include connections during memory creation
                )
                
                if query_analysis.intent_result:
                    intent_metadata = {
                        'intent_type': query_analysis.intent_result.intent_type.value,
                        'intent_confidence': query_analysis.intent_result.metadata.confidence,
                        'intent_reasoning': query_analysis.intent_result.reasoning,
                        'intent_safety_score': float(query_analysis.intent_result.metadata.safety_score),
                        'query_analysis_id': str(query_analysis.query_id)
                    }
                    
                    logger.debug(
                        f"Analyzed intent: {query_analysis.intent_result.intent_type} "
                        f"(confidence: {query_analysis.intent_result.metadata.confidence:.2f})"
                    )
                
            except Exception as e:
                logger.warning(f"Intent analysis failed during memory creation: {e}")
                # Continue without intent analysis - it's optional
        
        # Merge intent metadata with provided metadata
        combined_metadata = {**(metadata or {}), **intent_metadata}
        
        # Create memory entry
        memory = AbstractMemoryEntry(
            abstracted_prompt=abstracted_prompt,
            abstracted_response=abstracted_response,
            abstracted_content=combined_metadata,
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
        
        # Generate embeddings if requested
        prompt_embedding = None
        response_embedding = None
        
        if generate_embeddings:
            try:
                # Determine content type based on metadata or content analysis
                content_type = self._determine_content_type(prompt, response, metadata)
                
                # Generate embeddings for abstracted content
                prompt_result = await self.embedding_service.generate_embedding(
                    content=abstracted_prompt,
                    content_type=content_type
                )
                
                response_result = await self.embedding_service.generate_embedding(
                    content=abstracted_response or "",
                    content_type=content_type
                )
                
                prompt_embedding = prompt_result.vector
                response_embedding = response_result.vector
                
                logger.debug(
                    f"Generated embeddings: prompt={len(prompt_embedding)}d, "
                    f"response={len(response_embedding)}d"
                )
                
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}")
                # Continue without embeddings - they're optional
        
        # Store in database
        await self._store_memory(memory, prompt_embedding, response_embedding)
        
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
        
        # Store in database (embeddings will be retrieved from memory)
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
    
    async def create_memory_relationship(
        self,
        source_memory_id: UUID,
        target_memory_id: UUID,
        relationship_type: str,
        relationship_strength: float = 0.5,
        context: Optional[Dict[str, Any]] = None,
        is_bidirectional: bool = False
    ) -> bool:
        """
        Create a relationship between two memories.
        
        Args:
            source_memory_id: Source memory
            target_memory_id: Target memory
            relationship_type: Type of relationship
            relationship_strength: Strength of relationship (0.0 to 1.0)
            context: Additional context for the relationship
            is_bidirectional: Whether relationship works both ways
            
        Returns:
            True if relationship created successfully
        """
        # Validate relationship type
        valid_types = [
            'continuation', 'refinement', 'contradiction', 'expansion',
            'implementation', 'question_answer', 'error_correction', 'related_topic'
        ]
        
        if relationship_type not in valid_types:
            raise ValueError(f"Invalid relationship type: {relationship_type}")
        
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO public.memory_relationships (
                        source_memory_id, target_memory_id, relationship_type,
                        relationship_strength, context, is_bidirectional
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                    source_memory_id, target_memory_id, relationship_type,
                    Decimal(str(relationship_strength)), context or {}, is_bidirectional
                )
                return True
            except Exception as e:
                logger.error(f"Failed to create relationship: {e}")
                return False
    
    async def get_memory_relationships(
        self,
        memory_id: UUID,
        relationship_types: Optional[List[str]] = None,
        min_strength: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a memory.
        
        Args:
            memory_id: Memory to get relationships for
            relationship_types: Filter by relationship types
            min_strength: Minimum relationship strength
            
        Returns:
            List of relationship dictionaries
        """
        async with self.db_pool.acquire() as conn:
            # Build query filters
            type_filter = ""
            params = [memory_id, memory_id, min_strength]
            
            if relationship_types:
                type_filter = "AND relationship_type = ANY($4)"
                params.append(relationship_types)
            
            rows = await conn.fetch(f"""
                SELECT 
                    id,
                    source_memory_id,
                    target_memory_id,
                    relationship_type,
                    relationship_strength,
                    context,
                    is_bidirectional,
                    created_at
                FROM public.memory_relationships
                WHERE (source_memory_id = $1 OR (target_memory_id = $2 AND is_bidirectional = true))
                    AND relationship_strength >= $3
                    {type_filter}
                ORDER BY relationship_strength DESC, created_at DESC
            """, *params)
            
            return [dict(row) for row in rows]
    
    async def find_temporal_sequences(
        self,
        memory_id: UUID,
        max_distance: int = 5,
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Find temporal sequences of memories related to a given memory.
        
        Args:
            memory_id: Starting memory
            max_distance: Maximum relationship distance to traverse
            time_window_hours: Time window for temporal relationships
            
        Returns:
            List of memory sequences with temporal context
        """
        async with self.db_pool.acquire() as conn:
            # Use recursive CTE to find temporal sequences
            sequences = await conn.fetch("""
                WITH RECURSIVE temporal_sequence AS (
                    -- Base case: start with the given memory
                    SELECT 
                        cm.id,
                        cm.session_id,
                        cm.created_at,
                        cm.interaction_type,
                        0 as distance,
                        ARRAY[cm.id] as path
                    FROM public.cognitive_memory cm
                    WHERE cm.id = $1 AND cm.is_validated = true
                    
                    UNION ALL
                    
                    -- Recursive case: find related memories
                    SELECT 
                        cm.id,
                        cm.session_id,
                        cm.created_at,
                        cm.interaction_type,
                        ts.distance + 1,
                        ts.path || cm.id
                    FROM temporal_sequence ts
                    JOIN public.memory_relationships mr ON (
                        (mr.source_memory_id = ts.id OR 
                         (mr.target_memory_id = ts.id AND mr.is_bidirectional = true))
                        AND mr.relationship_type IN ('continuation', 'refinement', 'expansion')
                    )
                    JOIN public.cognitive_memory cm ON (
                        CASE 
                            WHEN mr.source_memory_id = ts.id THEN cm.id = mr.target_memory_id
                            ELSE cm.id = mr.source_memory_id
                        END
                    )
                    WHERE ts.distance < $2
                        AND cm.is_validated = true
                        AND cm.id != ALL(ts.path)  -- Prevent cycles
                        AND ABS(EXTRACT(EPOCH FROM (cm.created_at - ts.created_at))) / 3600 <= $3
                )
                SELECT 
                    ts.*,
                    ma.abstracted_prompt,
                    ma.safety_score
                FROM temporal_sequence ts
                JOIN safety.memory_abstractions ma ON ts.id = ma.memory_id
                ORDER BY distance, created_at
            """, memory_id, max_distance, time_window_hours)
            
            return [dict(row) for row in sequences]
    
    async def search_with_clustering(
        self,
        query: str,
        cluster_types: Optional[List[ClusterType]] = None,
        limit: int = 10,
        min_safety_score: float = 0.8,
        include_cluster_info: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for memories with cluster-aware ranking.
        
        Args:
            query: Search query (will be abstracted)
            cluster_types: Filter by cluster types
            limit: Maximum results
            min_safety_score: Minimum safety score filter
            include_cluster_info: Include cluster membership info
            
        Returns:
            List of memory dictionaries with cluster information
        """
        # Abstract the query
        abstracted_query, _ = self.validator.auto_abstract_content(query)
        
        async with self.db_pool.acquire() as conn:
            # Build cluster type filter
            cluster_filter = ""
            params = [abstracted_query, min_safety_score, limit]
            
            if cluster_types:
                cluster_values = [ct.value for ct in cluster_types]
                cluster_filter = "AND mc.cluster_type = ANY($4)"
                params.append(cluster_values)
            
            # Search with cluster boosting
            rows = await conn.fetch(f"""
                WITH search_results AS (
                    SELECT 
                        ma.memory_id,
                        ma.abstracted_prompt,
                        ma.abstracted_response,
                        ma.safety_score,
                        similarity(
                            ma.abstracted_prompt || ' ' || ma.abstracted_response,
                            $1
                        ) as base_similarity,
                        cm.weight,
                        cm.access_count,
                        cm.last_accessed
                    FROM safety.memory_abstractions ma
                    INNER JOIN public.cognitive_memory cm ON ma.memory_id = cm.id
                    WHERE ma.validation_status = 'validated'
                        AND ma.safety_score >= $2
                        AND similarity(
                            ma.abstracted_prompt || ' ' || ma.abstracted_response,
                            $1
                        ) > 0.2
                ),
                clustered_results AS (
                    SELECT 
                        sr.*,
                        mcm.cluster_id,
                        mcm.membership_score,
                        mc.cluster_name,
                        mc.cluster_type,
                        mc.member_count,
                        -- Boost score based on cluster membership and size
                        sr.base_similarity * (1 + (mcm.membership_score * 0.2)) * 
                        (1 + (LEAST(mc.member_count, 10) * 0.01)) as boosted_similarity
                    FROM search_results sr
                    LEFT JOIN public.memory_cluster_members mcm ON sr.memory_id = mcm.memory_id
                    LEFT JOIN public.memory_clusters mc ON mcm.cluster_id = mc.id
                    WHERE mc.id IS NULL OR mc.avg_safety_score >= $2
                        {cluster_filter}
                )
                SELECT 
                    memory_id,
                    abstracted_prompt,
                    abstracted_response,
                    safety_score,
                    base_similarity,
                    COALESCE(boosted_similarity, base_similarity) as final_similarity,
                    weight,
                    access_count,
                    last_accessed,
                    cluster_id,
                    membership_score,
                    cluster_name,
                    cluster_type,
                    member_count
                FROM clustered_results
                ORDER BY final_similarity DESC, weight DESC
                LIMIT $3
            """, *params)
            
            results = []
            for row in rows:
                result = {
                    'memory_id': row['memory_id'],
                    'abstracted_prompt': row['abstracted_prompt'],
                    'abstracted_response': row['abstracted_response'],
                    'safety_score': float(row['safety_score']),
                    'similarity_score': float(row['final_similarity']),
                    'weight': float(row['weight']),
                    'access_count': row['access_count'],
                    'last_accessed': row['last_accessed']
                }
                
                if include_cluster_info and row['cluster_id']:
                    result['cluster_info'] = {
                        'cluster_id': row['cluster_id'],
                        'cluster_name': row['cluster_name'],
                        'cluster_type': row['cluster_type'],
                        'membership_score': float(row['membership_score']),
                        'member_count': row['member_count']
                    }
                
                results.append(result)
            
            return results
    
    async def get_cluster_memories(
        self,
        cluster_id: UUID,
        sort_by: str = 'membership_score',
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all memories in a cluster.
        
        Args:
            cluster_id: Cluster to retrieve memories from
            sort_by: Sort field ('membership_score', 'weight', 'last_accessed')
            limit: Maximum results
            
        Returns:
            List of memory dictionaries
        """
        valid_sorts = ['membership_score', 'weight', 'last_accessed', 'created_at']
        if sort_by not in valid_sorts:
            sort_by = 'membership_score'
        
        async with self.db_pool.acquire() as conn:
            query = f"""
                SELECT 
                    cm.id as memory_id,
                    ma.abstracted_prompt,
                    ma.abstracted_response,
                    ma.safety_score,
                    cm.weight,
                    cm.access_count,
                    cm.last_accessed,
                    cm.created_at,
                    mcm.membership_score,
                    mcm.added_at
                FROM public.memory_cluster_members mcm
                INNER JOIN public.cognitive_memory cm ON mcm.memory_id = cm.id
                INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
                WHERE mcm.cluster_id = $1
                    AND cm.is_validated = true
                ORDER BY {sort_by} DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            rows = await conn.fetch(query, cluster_id)
            
            return [
                {
                    'memory_id': row['memory_id'],
                    'abstracted_prompt': row['abstracted_prompt'],
                    'abstracted_response': row['abstracted_response'],
                    'safety_score': float(row['safety_score']),
                    'weight': float(row['weight']),
                    'access_count': row['access_count'],
                    'last_accessed': row['last_accessed'],
                    'created_at': row['created_at'],
                    'membership_score': float(row['membership_score']),
                    'added_at': row['added_at']
                }
                for row in rows
            ]
    
    async def auto_cluster_similar_memories(
        self,
        memory_id: UUID,
        similarity_threshold: float = 0.8,
        create_cluster: bool = True
    ) -> Optional[UUID]:
        """
        Automatically cluster memories similar to a given memory.
        
        Args:
            memory_id: Source memory for clustering
            similarity_threshold: Minimum similarity for clustering
            create_cluster: Whether to create a new cluster if none suitable exists
            
        Returns:
            Cluster ID if successful, None otherwise
        """
        # Find similar memories
        similar_memories = await self.cluster_manager.find_similar_memories(
            memory_id, similarity_threshold, max_results=20
        )
        
        if len(similar_memories) < 2:  # Need at least 2 memories for a cluster
            return None
        
        # Check if any existing cluster would be suitable
        recommendations = await self.cluster_manager.get_cluster_recommendations(
            memory_id, max_recommendations=3
        )
        
        for cluster_id, cluster_name, fit_score in recommendations:
            if fit_score >= similarity_threshold:
                # Add to existing cluster
                await self.cluster_manager.add_memory_to_cluster(
                    cluster_id, memory_id, fit_score
                )
                return cluster_id
        
        if create_cluster:
            # Create new cluster
            cluster_name = f"Auto-Cluster-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            cluster = await self.cluster_manager.create_cluster(
                cluster_name=cluster_name,
                cluster_type=ClusterType.SEMANTIC
            )
            
            # Add source memory
            await self.cluster_manager.add_memory_to_cluster(
                cluster.cluster_id, memory_id, 1.0
            )
            
            # Add similar memories
            for similar_id, similarity in similar_memories:
                if similarity >= similarity_threshold:
                    await self.cluster_manager.add_memory_to_cluster(
                        cluster.cluster_id, similar_id, similarity
                    )
            
            return cluster.cluster_id
        
        return None
    
    async def apply_memory_decay(
        self,
        batch_size: int = 100,
        interaction_types: Optional[List[InteractionType]] = None
    ) -> Dict[str, Any]:
        """
        Apply temporal decay to memories.
        
        Args:
            batch_size: Number of memories to process
            interaction_types: Only process these interaction types
            
        Returns:
            Decay analysis summary
        """
        analysis = await self.decay_engine.apply_decay_batch(
            batch_size=batch_size,
            interaction_types=interaction_types
        )
        
        return analysis.get_summary()
    
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
    
    def _determine_content_type(
        self, 
        prompt: str, 
        response: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentType:
        """
        Determine the content type for embedding generation.
        
        Args:
            prompt: The prompt content
            response: The response content
            metadata: Optional metadata with hints
            
        Returns:
            ContentType for embedding model selection
        """
        # Check metadata for explicit content type
        if metadata and 'content_type' in metadata:
            content_type_str = metadata['content_type'].lower()
            if content_type_str == 'code':
                return ContentType.CODE
            elif content_type_str == 'documentation':
                return ContentType.DOCUMENTATION
            elif content_type_str == 'query':
                return ContentType.QUERY
        
        # Analyze content for code patterns
        combined_content = f"{prompt} {response}".lower()
        
        # Code indicators
        code_indicators = [
            'def ', 'function', 'class ', 'import ', 'from ',
            'if __name__', 'return ', 'print(', 'console.log',
            '#!/', '<?php', '<script', '<html', 'SELECT ', 'INSERT ',
            'CREATE TABLE', 'function(', '=>', 'async ', 'await ',
            'public class', 'private ', 'protected ', '#include'
        ]
        
        # Documentation indicators
        doc_indicators = [
            'readme', 'documentation', 'guide', 'tutorial',
            'installation', 'getting started', 'api reference',
            'changelog', 'license', 'contributing'
        ]
        
        # Count indicators
        code_score = sum(1 for indicator in code_indicators if indicator in combined_content)
        doc_score = sum(1 for indicator in doc_indicators if indicator in combined_content)
        
        # Determine type based on scores
        if code_score > doc_score and code_score > 0:
            return ContentType.CODE
        elif doc_score > 0:
            return ContentType.DOCUMENTATION
        else:
            return ContentType.TEXT
    
    async def _store_memory(
        self, 
        memory: AbstractMemoryEntry, 
        prompt_embedding: Optional[List[float]] = None,
        response_embedding: Optional[List[float]] = None
    ) -> None:
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
            # Get embeddings from the associated memory if available
            prompt_embedding = interaction.prompt_embedding
            response_embedding = interaction.response_embedding
            
            # If embeddings not set on interaction, try to get from memory
            if not prompt_embedding or not response_embedding:
                memory_embeddings = await conn.fetchrow("""
                    SELECT prompt_embedding, response_embedding
                    FROM public.cognitive_memory cm
                    WHERE cm.abstraction_id = $1
                    ORDER BY cm.created_at DESC
                    LIMIT 1
                """, interaction.abstraction_id)
                
                if memory_embeddings:
                    prompt_embedding = prompt_embedding or memory_embeddings['prompt_embedding']
                    response_embedding = response_embedding or memory_embeddings['response_embedding']
            
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
                prompt_embedding,
                response_embedding,
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
    
    async def search_with_intent_analysis(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        max_connections: int = 10,
        include_similar_intents: bool = True,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search memories using intent analysis and connection finding.
        
        This method combines traditional search with intent analysis to provide
        more relevant and contextual results.
        
        Args:
            query: Search query
            user_id: User ID for personalized analysis
            context: Additional context for intent analysis
            max_connections: Maximum connections to find
            include_similar_intents: Whether to include memories with similar intents
            limit: Maximum search results
            
        Returns:
            Dictionary with search results, intent analysis, and connections
        """
        if not self.intent_engine:
            # Fallback to regular search if no intent engine
            logger.warning("Intent engine not available, falling back to regular search")
            results = await self.search_with_clustering(query, limit=limit)
            return {
                'query': query,
                'intent_analysis': None,
                'search_results': results,
                'connections': [],
                'total_results': len(results)
            }
        
        try:
            # Step 1: Analyze query intent
            logger.debug(f"Analyzing intent for search query: {query[:100]}...")
            
            query_analysis = await self.intent_engine.analyze_query(
                query=query,
                context=context,
                user_id=user_id,
                include_connections=True,
                max_connections=max_connections
            )
            
            # Step 2: Perform regular search
            search_results = await self.search_with_clustering(
                query=query,
                limit=limit
            )
            
            # Step 3: Enhance results with intent-based filtering and ranking
            enhanced_results = await self._enhance_results_with_intent(
                search_results,
                query_analysis,
                include_similar_intents
            )
            
            # Step 4: Get connections from intent analysis
            connections = []
            if query_analysis.connection_result:
                connections = [
                    {
                        'target_id': str(conn.target_id),
                        'connection_type': conn.connection_type.value,
                        'strength': conn.strength,
                        'explanation': conn.explanation,
                        'reasoning': conn.reasoning.value
                    }
                    for conn in query_analysis.connection_result.connections
                ]
            
            result = {
                'query': query,
                'intent_analysis': {
                    'intent_type': query_analysis.intent_result.intent_type.value if query_analysis.intent_result else None,
                    'confidence': query_analysis.intent_result.metadata.confidence if query_analysis.intent_result else 0.0,
                    'reasoning': query_analysis.intent_result.reasoning if query_analysis.intent_result else None,
                    'safety_score': float(query_analysis.safety_score),
                    'processing_time_ms': query_analysis.total_processing_time_ms
                },
                'search_results': enhanced_results,
                'connections': connections,
                'total_results': len(enhanced_results),
                'connection_count': len(connections)
            }
            
            logger.info(
                f"Intent-aware search completed: {len(enhanced_results)} results, "
                f"{len(connections)} connections for intent: {query_analysis.intent_result.intent_type if query_analysis.intent_result else 'unknown'}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Intent-aware search failed: {e}")
            # Fallback to regular search
            search_results = await self.search_with_clustering(query, limit=limit)
            return {
                'query': query,
                'intent_analysis': {'error': str(e)},
                'search_results': search_results,
                'connections': [],
                'total_results': len(search_results)
            }
    
    async def _enhance_results_with_intent(
        self,
        search_results: List[Dict[str, Any]],
        query_analysis: QueryAnalysis,
        include_similar_intents: bool
    ) -> List[Dict[str, Any]]:
        """
        Enhance search results using intent analysis.
        
        Args:
            search_results: Original search results
            query_analysis: Intent analysis results
            include_similar_intents: Whether to boost similar intents
            
        Returns:
            Enhanced and re-ranked search results
        """
        if not query_analysis.intent_result:
            return search_results
        
        query_intent = query_analysis.intent_result.intent_type
        enhanced_results = []
        
        for result in search_results:
            enhanced_result = result.copy()
            
            # Check if memory has intent metadata
            memory_metadata = result.get('abstracted_content', {})
            memory_intent_str = memory_metadata.get('intent_type')
            
            intent_boost = 0.0
            intent_match = False
            
            if memory_intent_str:
                try:
                    memory_intent = IntentType(memory_intent_str)
                    
                    # Exact intent match
                    if memory_intent == query_intent:
                        intent_boost = 0.3
                        intent_match = True
                    # Similar intent (simplified similarity)
                    elif include_similar_intents and self._are_intents_similar(query_intent, memory_intent):
                        intent_boost = 0.1
                        intent_match = True
                    
                except ValueError:
                    # Invalid intent type in metadata
                    pass
            
            # Apply intent boost to similarity score
            original_similarity = result.get('similarity', 0.0)
            enhanced_similarity = min(1.0, original_similarity + intent_boost)
            
            enhanced_result.update({
                'original_similarity': original_similarity,
                'intent_boosted_similarity': enhanced_similarity,
                'intent_match': intent_match,
                'intent_boost': intent_boost,
                'memory_intent': memory_intent_str
            })
            
            enhanced_results.append(enhanced_result)
        
        # Re-sort by enhanced similarity
        enhanced_results.sort(
            key=lambda x: x.get('intent_boosted_similarity', 0),
            reverse=True
        )
        
        return enhanced_results
    
    def _are_intents_similar(self, intent1: IntentType, intent2: IntentType) -> bool:
        """Check if two intents are similar (simplified logic)."""
        similar_groups = [
            {IntentType.QUESTION, IntentType.EXPLANATION, IntentType.LEARN},
            {IntentType.DEBUG, IntentType.OPTIMIZE, IntentType.REVIEW},
            {IntentType.CREATE, IntentType.PLAN, IntentType.COMMAND},
            {IntentType.SEARCH, IntentType.REVIEW, IntentType.REFLECT}
        ]
        
        for group in similar_groups:
            if intent1 in group and intent2 in group:
                return True
        
        return False