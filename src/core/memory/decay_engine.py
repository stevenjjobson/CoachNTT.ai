"""
Memory decay engine for temporal weight management.

Implements sophisticated decay algorithms with configurable parameters
and batch processing for optimal performance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

import asyncpg
from asyncpg import Pool

from .abstract_models import InteractionType


logger = logging.getLogger(__name__)


class DecayConfiguration:
    """Configuration for memory decay parameters."""
    
    def __init__(
        self,
        interaction_type: InteractionType,
        base_decay_rate: float = 0.0001,
        minimum_weight: float = 0.01,
        reinforcement_factor: float = 1.5,
        decay_acceleration_days: int = 30,
        preserve_threshold: float = 0.8
    ):
        """
        Initialize decay configuration.
        
        Args:
            interaction_type: Type of interaction this config applies to
            base_decay_rate: Base exponential decay rate per day
            minimum_weight: Minimum weight threshold (memories below are candidates for removal)
            reinforcement_factor: Multiplier for reinforcement operations
            decay_acceleration_days: Days after which decay accelerates
            preserve_threshold: Weight threshold above which memories are preserved
        """
        self.interaction_type = interaction_type
        self.base_decay_rate = base_decay_rate
        self.minimum_weight = minimum_weight
        self.reinforcement_factor = reinforcement_factor
        self.decay_acceleration_days = decay_acceleration_days
        self.preserve_threshold = preserve_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'interaction_type': self.interaction_type.value,
            'base_decay_rate': self.base_decay_rate,
            'minimum_weight': self.minimum_weight,
            'reinforcement_factor': self.reinforcement_factor,
            'decay_acceleration_days': self.decay_acceleration_days,
            'preserve_threshold': self.preserve_threshold
        }


class DecayAnalysis:
    """Analysis results from decay operations."""
    
    def __init__(
        self,
        total_processed: int,
        weight_changes: Dict[UUID, Tuple[Decimal, Decimal]],
        removed_memories: List[UUID],
        preserved_memories: List[UUID],
        processing_time_ms: int
    ):
        """
        Initialize decay analysis.
        
        Args:
            total_processed: Total number of memories processed
            weight_changes: Dictionary of memory_id -> (old_weight, new_weight)
            removed_memories: List of memory IDs that fell below minimum threshold
            preserved_memories: List of memory IDs preserved due to high importance
            processing_time_ms: Time taken for processing
        """
        self.total_processed = total_processed
        self.weight_changes = weight_changes
        self.removed_memories = removed_memories
        self.preserved_memories = preserved_memories
        self.processing_time_ms = processing_time_ms
        self.average_decay = self._calculate_average_decay()
    
    def _calculate_average_decay(self) -> float:
        """Calculate average decay percentage."""
        if not self.weight_changes:
            return 0.0
        
        total_decay = 0.0
        for old_weight, new_weight in self.weight_changes.values():
            if old_weight > 0:
                decay_percent = (float(old_weight) - float(new_weight)) / float(old_weight)
                total_decay += decay_percent
        
        return total_decay / len(self.weight_changes)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            'total_processed': self.total_processed,
            'memories_changed': len(self.weight_changes),
            'memories_removed': len(self.removed_memories),
            'memories_preserved': len(self.preserved_memories),
            'average_decay_percent': round(self.average_decay * 100, 2),
            'processing_time_ms': self.processing_time_ms
        }


class MemoryDecayEngine:
    """
    Advanced memory decay engine with configurable algorithms.
    
    Provides temporal weight management with safety-first principles.
    """
    
    def __init__(self, db_pool: Pool):
        """
        Initialize decay engine.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self._configs: Dict[InteractionType, DecayConfiguration] = {}
        self._default_config = DecayConfiguration(InteractionType.CONVERSATION)
    
    async def initialize(self) -> None:
        """Initialize engine by loading configurations from database."""
        await self._load_configurations()
    
    async def _load_configurations(self) -> None:
        """Load decay configurations from database."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    interaction_type,
                    base_decay_rate,
                    minimum_weight,
                    reinforcement_factor,
                    decay_acceleration_days,
                    preserve_threshold
                FROM public.memory_decay_config
                WHERE is_active = true
            """)
            
            for row in rows:
                interaction_type = InteractionType(row['interaction_type'])
                config = DecayConfiguration(
                    interaction_type=interaction_type,
                    base_decay_rate=float(row['base_decay_rate']),
                    minimum_weight=float(row['minimum_weight']),
                    reinforcement_factor=float(row['reinforcement_factor']),
                    decay_acceleration_days=row['decay_acceleration_days'],
                    preserve_threshold=float(row['preserve_threshold'])
                )
                self._configs[interaction_type] = config
                
        logger.info(f"Loaded {len(self._configs)} decay configurations")
    
    def get_configuration(self, interaction_type: InteractionType) -> DecayConfiguration:
        """Get decay configuration for interaction type."""
        return self._configs.get(interaction_type, self._default_config)
    
    async def calculate_decay(
        self,
        memory_id: UUID,
        current_weight: Decimal,
        last_accessed: datetime,
        interaction_type: InteractionType,
        access_count: int = 0
    ) -> Decimal:
        """
        Calculate new weight after decay using database function.
        
        Args:
            memory_id: Memory identifier
            current_weight: Current memory weight
            last_accessed: Last access timestamp
            interaction_type: Type of interaction
            access_count: Number of times accessed
            
        Returns:
            New calculated weight
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT public.calculate_memory_decay($1, $2, $3, $4)
            """, current_weight, last_accessed, interaction_type.value, access_count)
            
            return Decimal(str(result))
    
    async def apply_decay_batch(
        self,
        batch_size: int = 100,
        max_age_days: Optional[int] = None,
        interaction_types: Optional[List[InteractionType]] = None
    ) -> DecayAnalysis:
        """
        Apply decay to a batch of memories.
        
        Args:
            batch_size: Number of memories to process in one batch
            max_age_days: Only process memories older than this many days
            interaction_types: Only process these interaction types
            
        Returns:
            DecayAnalysis with processing results
        """
        start_time = datetime.utcnow()
        weight_changes = {}
        removed_memories = []
        preserved_memories = []
        
        # Build query filters
        filters = ["cm.is_validated = true"]
        params = [batch_size]
        param_count = 1
        
        if max_age_days:
            param_count += 1
            filters.append(f"cm.last_accessed < NOW() - INTERVAL '{max_age_days} days'")
        
        if interaction_types:
            param_count += 1
            type_values = [t.value for t in interaction_types]
            filters.append(f"cm.interaction_type = ANY(${param_count})")
            params.append(type_values)
        
        filter_clause = " AND ".join(filters)
        
        async with self.db_pool.acquire() as conn:
            # Get memories to process
            rows = await conn.fetch(f"""
                SELECT 
                    cm.id,
                    cm.weight,
                    cm.last_accessed,
                    cm.interaction_type,
                    cm.access_count,
                    ma.safety_score
                FROM public.cognitive_memory cm
                INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
                WHERE {filter_clause}
                ORDER BY cm.last_accessed ASC
                LIMIT $1
            """, *params)
            
            # Process each memory
            for row in rows:
                memory_id = row['id']
                current_weight = Decimal(str(row['weight']))
                last_accessed = row['last_accessed']
                interaction_type = InteractionType(row['interaction_type'])
                access_count = row['access_count']
                safety_score = Decimal(str(row['safety_score']))
                
                # Get configuration for this type
                config = self.get_configuration(interaction_type)
                
                # Check if memory should be preserved
                if current_weight >= Decimal(str(config.preserve_threshold)):
                    preserved_memories.append(memory_id)
                    continue
                
                # Calculate new weight
                new_weight = await self.calculate_decay(
                    memory_id, current_weight, last_accessed, 
                    interaction_type, access_count
                )
                
                # Check if memory should be removed (below minimum threshold)
                if new_weight <= Decimal(str(config.minimum_weight)):
                    # Only remove if safety score is below 0.9 (keep high-safety memories)
                    if safety_score < Decimal("0.9"):
                        removed_memories.append(memory_id)
                        await self._remove_memory(conn, memory_id)
                        continue
                
                # Update weight if changed significantly
                if abs(new_weight - current_weight) > Decimal("0.001"):
                    await self._update_memory_weight(conn, memory_id, new_weight)
                    weight_changes[memory_id] = (current_weight, new_weight)
        
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return DecayAnalysis(
            total_processed=len(rows),
            weight_changes=weight_changes,
            removed_memories=removed_memories,
            preserved_memories=preserved_memories,
            processing_time_ms=processing_time_ms
        )
    
    async def reinforce_memory(
        self,
        memory_id: UUID,
        strength: float = 1.0
    ) -> Optional[Decimal]:
        """
        Reinforce a memory using database function.
        
        Args:
            memory_id: Memory to reinforce
            strength: Reinforcement strength multiplier
            
        Returns:
            New weight if successful, None if memory not found
        """
        async with self.db_pool.acquire() as conn:
            try:
                result = await conn.fetchval("""
                    SELECT public.reinforce_memory($1, $2)
                """, memory_id, Decimal(str(strength)))
                
                return Decimal(str(result))
            except Exception as e:
                logger.warning(f"Failed to reinforce memory {memory_id}: {e}")
                return None
    
    async def schedule_decay_maintenance(
        self,
        interval_hours: int = 24,
        batch_size: int = 500
    ) -> None:
        """
        Schedule regular decay maintenance.
        
        Args:
            interval_hours: Hours between maintenance runs
            batch_size: Memories to process per run
        """
        logger.info(f"Starting decay maintenance every {interval_hours} hours")
        
        while True:
            try:
                # Run decay on old memories
                analysis = await self.apply_decay_batch(
                    batch_size=batch_size,
                    max_age_days=1  # Process memories older than 1 day
                )
                
                summary = analysis.get_summary()
                logger.info(
                    f"Decay maintenance completed: {summary['total_processed']} processed, "
                    f"{summary['memories_changed']} updated, "
                    f"{summary['memories_removed']} removed, "
                    f"avg decay: {summary['average_decay_percent']}%"
                )
                
                # Refresh materialized views after significant changes
                if summary['memories_changed'] > 10:
                    await self._refresh_materialized_views()
                
            except Exception as e:
                logger.error(f"Decay maintenance failed: {e}")
            
            # Wait for next interval
            await asyncio.sleep(interval_hours * 3600)
    
    async def get_decay_statistics(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get decay statistics for analysis.
        
        Args:
            days_back: Days of history to analyze
            
        Returns:
            Dictionary with decay statistics
        """
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_memories,
                    AVG(weight) as avg_weight,
                    MIN(weight) as min_weight,
                    MAX(weight) as max_weight,
                    COUNT(*) FILTER (WHERE weight < 0.1) as low_weight_count,
                    COUNT(*) FILTER (WHERE weight > 0.8) as high_weight_count,
                    COUNT(*) FILTER (WHERE last_accessed < NOW() - INTERVAL '%s days') as stale_count
                FROM public.cognitive_memory
                WHERE is_validated = true
            """ % days_back)
            
            # Get per-type statistics
            type_stats = await conn.fetch("""
                SELECT 
                    interaction_type,
                    COUNT(*) as count,
                    AVG(weight) as avg_weight,
                    AVG(access_count) as avg_access_count
                FROM public.cognitive_memory
                WHERE is_validated = true
                    AND last_accessed > NOW() - INTERVAL '%s days'
                GROUP BY interaction_type
                ORDER BY count DESC
            """ % days_back)
            
            return {
                'total_memories': stats['total_memories'],
                'weight_distribution': {
                    'average': float(stats['avg_weight']) if stats['avg_weight'] else 0,
                    'minimum': float(stats['min_weight']) if stats['min_weight'] else 0,
                    'maximum': float(stats['max_weight']) if stats['max_weight'] else 0,
                    'low_weight_count': stats['low_weight_count'],
                    'high_weight_count': stats['high_weight_count']
                },
                'staleness': {
                    'stale_memories': stats['stale_count'],
                    'stale_percentage': round(
                        (stats['stale_count'] / max(stats['total_memories'], 1)) * 100, 2
                    )
                },
                'by_interaction_type': [
                    {
                        'type': row['interaction_type'],
                        'count': row['count'],
                        'avg_weight': float(row['avg_weight']),
                        'avg_access_count': float(row['avg_access_count'])
                    }
                    for row in type_stats
                ]
            }
    
    async def _update_memory_weight(
        self,
        conn: asyncpg.Connection,
        memory_id: UUID,
        new_weight: Decimal
    ) -> None:
        """Update memory weight in database."""
        await conn.execute("""
            UPDATE public.cognitive_memory
            SET weight = $2, updated_at = NOW()
            WHERE id = $1
        """, memory_id, new_weight)
    
    async def _remove_memory(
        self,
        conn: asyncpg.Connection,
        memory_id: UUID
    ) -> None:
        """Remove memory from database (soft delete by setting weight to 0)."""
        await conn.execute("""
            UPDATE public.cognitive_memory
            SET weight = 0, updated_at = NOW()
            WHERE id = $1
        """, memory_id)
        
        logger.debug(f"Removed memory {memory_id} due to decay")
    
    async def _refresh_materialized_views(self) -> None:
        """Refresh materialized views after significant changes."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("SELECT public.refresh_memory_views()")
        
        logger.debug("Refreshed materialized views")