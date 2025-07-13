"""
Memory cluster manager for semantic grouping and similarity search.

Implements sophisticated clustering algorithms using vector embeddings
while maintaining safety-first principles.
"""

import logging
import math
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from uuid import UUID, uuid4

import asyncpg
import numpy as np
from asyncpg import Pool

from .abstract_models import InteractionType


logger = logging.getLogger(__name__)


class ClusterType(Enum):
    """Types of memory clusters."""
    TOPIC = "topic"
    SESSION = "session"
    PROJECT = "project"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    PATTERN = "pattern"


class ClusterMember:
    """Represents a memory's membership in a cluster."""
    
    def __init__(
        self,
        memory_id: UUID,
        membership_score: float,
        added_at: datetime = None
    ):
        """
        Initialize cluster member.
        
        Args:
            memory_id: ID of the memory
            membership_score: Strength of membership (0.0 to 1.0)
            added_at: When the memory was added to cluster
        """
        self.memory_id = memory_id
        self.membership_score = membership_score
        self.added_at = added_at or datetime.utcnow()


class MemoryCluster:
    """Represents a cluster of related memories."""
    
    def __init__(
        self,
        cluster_id: UUID = None,
        cluster_name: str = "",
        cluster_type: ClusterType = ClusterType.SEMANTIC,
        centroid_embedding: Optional[List[float]] = None,
        member_count: int = 0,
        avg_safety_score: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        last_accessed: datetime = None
    ):
        """Initialize memory cluster."""
        self.cluster_id = cluster_id or uuid4()
        self.cluster_name = cluster_name
        self.cluster_type = cluster_type
        self.centroid_embedding = centroid_embedding
        self.member_count = member_count
        self.avg_safety_score = avg_safety_score
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_accessed = last_accessed or datetime.utcnow()
        self.members: List[ClusterMember] = []
    
    def add_member(self, memory_id: UUID, membership_score: float) -> None:
        """Add a memory to this cluster."""
        member = ClusterMember(memory_id, membership_score)
        self.members.append(member)
        self.member_count = len(self.members)
        self.updated_at = datetime.utcnow()
    
    def remove_member(self, memory_id: UUID) -> bool:
        """Remove a memory from this cluster."""
        for i, member in enumerate(self.members):
            if member.memory_id == memory_id:
                del self.members[i]
                self.member_count = len(self.members)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def calculate_centroid(self, embeddings: Dict[UUID, List[float]]) -> List[float]:
        """Calculate cluster centroid from member embeddings."""
        if not self.members or not embeddings:
            return [0.0] * 1536  # Default embedding size
        
        # Weighted average based on membership scores
        centroid = np.zeros(1536)
        total_weight = 0.0
        
        for member in self.members:
            if member.memory_id in embeddings:
                embedding = np.array(embeddings[member.memory_id])
                weight = member.membership_score
                centroid += embedding * weight
                total_weight += weight
        
        if total_weight > 0:
            centroid /= total_weight
        
        return centroid.tolist()


class ClusteringResult:
    """Results from a clustering operation."""
    
    def __init__(
        self,
        clusters_created: int,
        clusters_updated: int,
        memories_clustered: int,
        processing_time_ms: int,
        quality_score: float
    ):
        """Initialize clustering result."""
        self.clusters_created = clusters_created
        self.clusters_updated = clusters_updated
        self.memories_clustered = memories_clustered
        self.processing_time_ms = processing_time_ms
        self.quality_score = quality_score
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of clustering operation."""
        return {
            'clusters_created': self.clusters_created,
            'clusters_updated': self.clusters_updated,
            'memories_clustered': self.memories_clustered,
            'processing_time_ms': self.processing_time_ms,
            'quality_score': round(self.quality_score, 3)
        }


class MemoryClusterManager:
    """
    Advanced memory clustering system with safety-first principles.
    
    Groups related memories for efficient retrieval and analysis.
    """
    
    def __init__(self, db_pool: Pool):
        """
        Initialize cluster manager.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.min_cluster_size = 2
        self.max_cluster_size = 50
        self.similarity_threshold = 0.7
        self.min_safety_score = Decimal("0.8")
    
    async def create_cluster(
        self,
        cluster_name: str,
        cluster_type: ClusterType,
        initial_memories: Optional[List[UUID]] = None
    ) -> MemoryCluster:
        """
        Create a new memory cluster.
        
        Args:
            cluster_name: Human-readable cluster name
            cluster_type: Type of cluster
            initial_memories: Optional list of memory IDs to add initially
            
        Returns:
            Created MemoryCluster
        """
        cluster = MemoryCluster(
            cluster_name=cluster_name,
            cluster_type=cluster_type
        )
        
        # Store cluster in database
        await self._store_cluster(cluster)
        
        # Add initial memories if provided
        if initial_memories:
            for memory_id in initial_memories:
                await self.add_memory_to_cluster(cluster.cluster_id, memory_id)
        
        return cluster
    
    async def add_memory_to_cluster(
        self,
        cluster_id: UUID,
        memory_id: UUID,
        membership_score: float = 1.0
    ) -> bool:
        """
        Add a memory to a cluster.
        
        Args:
            cluster_id: Cluster to add to
            memory_id: Memory to add
            membership_score: Strength of membership
            
        Returns:
            True if added successfully
        """
        # Verify memory meets safety requirements
        async with self.db_pool.acquire() as conn:
            safety_check = await conn.fetchrow("""
                SELECT ma.safety_score, cm.is_validated
                FROM public.cognitive_memory cm
                INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
                WHERE cm.id = $1
            """, memory_id)
            
            if not safety_check or not safety_check['is_validated']:
                logger.warning(f"Memory {memory_id} not validated, cannot add to cluster")
                return False
            
            if Decimal(str(safety_check['safety_score'])) < self.min_safety_score:
                logger.warning(f"Memory {memory_id} safety score too low for clustering")
                return False
            
            # Add to cluster
            await conn.execute("""
                INSERT INTO public.memory_cluster_members (cluster_id, memory_id, membership_score)
                VALUES ($1, $2, $3)
                ON CONFLICT (cluster_id, memory_id) 
                DO UPDATE SET membership_score = $3, added_at = NOW()
            """, cluster_id, memory_id, Decimal(str(membership_score)))
            
            return True
    
    async def remove_memory_from_cluster(
        self,
        cluster_id: UUID,
        memory_id: UUID
    ) -> bool:
        """
        Remove a memory from a cluster.
        
        Args:
            cluster_id: Cluster to remove from
            memory_id: Memory to remove
            
        Returns:
            True if removed successfully
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM public.memory_cluster_members
                WHERE cluster_id = $1 AND memory_id = $2
            """, cluster_id, memory_id)
            
            return result.split()[-1] == '1'
    
    async def find_similar_memories(
        self,
        memory_id: UUID,
        similarity_threshold: float = None,
        max_results: int = 10
    ) -> List[Tuple[UUID, float]]:
        """
        Find memories similar to a given memory using embeddings.
        
        Args:
            memory_id: Source memory
            similarity_threshold: Minimum similarity score
            max_results: Maximum results to return
            
        Returns:
            List of (memory_id, similarity_score) tuples
        """
        threshold = similarity_threshold or self.similarity_threshold
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH source AS (
                    SELECT prompt_embedding, response_embedding
                    FROM public.cognitive_memory
                    WHERE id = $1 AND is_validated = true
                )
                SELECT 
                    cm.id,
                    GREATEST(
                        1 - (cm.prompt_embedding <=> s.prompt_embedding),
                        1 - (cm.response_embedding <=> s.response_embedding)
                    ) as similarity
                FROM public.cognitive_memory cm, source s
                WHERE cm.id != $1
                    AND cm.is_validated = true
                    AND GREATEST(
                        1 - (cm.prompt_embedding <=> s.prompt_embedding),
                        1 - (cm.response_embedding <=> s.response_embedding)
                    ) >= $2
                ORDER BY similarity DESC
                LIMIT $3
            """, memory_id, threshold, max_results)
            
            return [(row['id'], float(row['similarity'])) for row in rows]
    
    async def auto_cluster_memories(
        self,
        min_cluster_size: int = None,
        max_clusters: int = 20,
        interaction_types: Optional[List[InteractionType]] = None
    ) -> ClusteringResult:
        """
        Automatically cluster memories using similarity analysis.
        
        Args:
            min_cluster_size: Minimum memories per cluster
            max_clusters: Maximum number of clusters to create
            interaction_types: Only cluster these interaction types
            
        Returns:
            ClusteringResult with operation details
        """
        start_time = datetime.utcnow()
        min_size = min_cluster_size or self.min_cluster_size
        clusters_created = 0
        clusters_updated = 0
        memories_clustered = 0
        
        # Get candidate memories for clustering
        async with self.db_pool.acquire() as conn:
            # Build query filter
            type_filter = ""
            params = [self.min_safety_score]
            
            if interaction_types:
                type_values = [t.value for t in interaction_types]
                type_filter = "AND cm.interaction_type = ANY($2)"
                params.append(type_values)
            
            memories = await conn.fetch(f"""
                SELECT 
                    cm.id,
                    cm.prompt_embedding,
                    cm.response_embedding,
                    cm.interaction_type,
                    ma.safety_score
                FROM public.cognitive_memory cm
                INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
                WHERE cm.is_validated = true
                    AND ma.safety_score >= $1
                    AND cm.prompt_embedding IS NOT NULL
                    AND cm.response_embedding IS NOT NULL
                    {type_filter}
                ORDER BY cm.last_accessed DESC
                LIMIT 500
            """, *params)
            
            if len(memories) < min_size:
                logger.info("Not enough memories for clustering")
                return ClusteringResult(0, 0, 0, 0, 0.0)
            
            # Create similarity matrix
            memory_ids = [row['id'] for row in memories]
            embeddings = {}
            
            for row in memories:
                # Combine prompt and response embeddings
                prompt_emb = np.array(row['prompt_embedding'])
                response_emb = np.array(row['response_embedding'])
                combined_emb = (prompt_emb + response_emb) / 2
                embeddings[row['id']] = combined_emb.tolist()
            
            # Find clusters using hierarchical clustering
            clusters = await self._hierarchical_clustering(
                memory_ids, embeddings, min_size, max_clusters
            )
            
            # Create clusters in database
            for i, cluster_members in enumerate(clusters):
                if len(cluster_members) >= min_size:
                    cluster_name = f"Auto-Cluster-{i+1}-{datetime.utcnow().strftime('%Y%m%d')}"
                    cluster = await self.create_cluster(
                        cluster_name=cluster_name,
                        cluster_type=ClusterType.SEMANTIC
                    )
                    
                    # Add members
                    for memory_id, score in cluster_members:
                        await self.add_memory_to_cluster(
                            cluster.cluster_id, memory_id, score
                        )
                        memories_clustered += 1
                    
                    clusters_created += 1
            
            # Update existing clusters
            existing_clusters = await self._update_existing_clusters()
            clusters_updated = len(existing_clusters)
        
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        quality_score = await self._calculate_clustering_quality()
        
        return ClusteringResult(
            clusters_created=clusters_created,
            clusters_updated=clusters_updated,
            memories_clustered=memories_clustered,
            processing_time_ms=processing_time_ms,
            quality_score=quality_score
        )
    
    async def get_cluster_recommendations(
        self,
        memory_id: UUID,
        max_recommendations: int = 5
    ) -> List[Tuple[UUID, str, float]]:
        """
        Get cluster recommendations for a memory.
        
        Args:
            memory_id: Memory to find clusters for
            max_recommendations: Maximum recommendations
            
        Returns:
            List of (cluster_id, cluster_name, fit_score) tuples
        """
        async with self.db_pool.acquire() as conn:
            # Get memory embedding
            memory_row = await conn.fetchrow("""
                SELECT prompt_embedding, response_embedding
                FROM public.cognitive_memory
                WHERE id = $1 AND is_validated = true
            """, memory_id)
            
            if not memory_row:
                return []
            
            # Get clusters with their centroids
            cluster_rows = await conn.fetch("""
                SELECT 
                    id,
                    cluster_name,
                    centroid_embedding,
                    member_count,
                    avg_safety_score
                FROM public.memory_clusters
                WHERE member_count < $1 AND avg_safety_score >= $2
                ORDER BY last_accessed DESC
            """, self.max_cluster_size, self.min_safety_score)
            
            recommendations = []
            memory_embedding = np.array(
                (np.array(memory_row['prompt_embedding']) + 
                 np.array(memory_row['response_embedding'])) / 2
            )
            
            for cluster_row in cluster_rows:
                if cluster_row['centroid_embedding']:
                    centroid = np.array(cluster_row['centroid_embedding'])
                    similarity = self._cosine_similarity(memory_embedding, centroid)
                    
                    if similarity >= self.similarity_threshold:
                        recommendations.append((
                            cluster_row['id'],
                            cluster_row['cluster_name'],
                            float(similarity)
                        ))
            
            # Sort by fit score and limit results
            recommendations.sort(key=lambda x: x[2], reverse=True)
            return recommendations[:max_recommendations]
    
    async def get_cluster_statistics(self) -> Dict[str, Any]:
        """Get clustering statistics for analysis."""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_clusters,
                    AVG(member_count) as avg_members_per_cluster,
                    MIN(member_count) as min_members,
                    MAX(member_count) as max_members,
                    AVG(avg_safety_score) as avg_safety_score
                FROM public.memory_clusters
            """)
            
            type_stats = await conn.fetch("""
                SELECT 
                    cluster_type,
                    COUNT(*) as count,
                    AVG(member_count) as avg_members
                FROM public.memory_clusters
                GROUP BY cluster_type
                ORDER BY count DESC
            """)
            
            # Calculate clustering coverage
            coverage = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT mcm.memory_id) as clustered_memories,
                    (SELECT COUNT(*) FROM public.cognitive_memory WHERE is_validated = true) as total_memories
                FROM public.memory_cluster_members mcm
            """)
            
            coverage_percent = 0.0
            if coverage['total_memories'] > 0:
                coverage_percent = (coverage['clustered_memories'] / coverage['total_memories']) * 100
            
            return {
                'total_clusters': stats['total_clusters'],
                'cluster_size_distribution': {
                    'average': float(stats['avg_members_per_cluster']) if stats['avg_members_per_cluster'] else 0,
                    'minimum': stats['min_members'],
                    'maximum': stats['max_members']
                },
                'average_safety_score': float(stats['avg_safety_score']) if stats['avg_safety_score'] else 0,
                'coverage': {
                    'clustered_memories': coverage['clustered_memories'],
                    'total_memories': coverage['total_memories'],
                    'coverage_percentage': round(coverage_percent, 2)
                },
                'by_cluster_type': [
                    {
                        'type': row['cluster_type'],
                        'count': row['count'],
                        'avg_members': float(row['avg_members'])
                    }
                    for row in type_stats
                ]
            }
    
    async def _store_cluster(self, cluster: MemoryCluster) -> None:
        """Store cluster in database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO public.memory_clusters (
                    id, cluster_name, cluster_type, centroid_embedding,
                    member_count, avg_safety_score, created_at, updated_at,
                    last_accessed, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                cluster.cluster_id,
                cluster.cluster_name,
                cluster.cluster_type.value,
                cluster.centroid_embedding,
                cluster.member_count,
                cluster.avg_safety_score,
                cluster.created_at,
                cluster.updated_at,
                cluster.last_accessed,
                cluster.metadata
            )
    
    async def _hierarchical_clustering(
        self,
        memory_ids: List[UUID],
        embeddings: Dict[UUID, List[float]],
        min_size: int,
        max_clusters: int
    ) -> List[List[Tuple[UUID, float]]]:
        """
        Perform hierarchical clustering on memories.
        
        Returns clusters as lists of (memory_id, membership_score) tuples.
        """
        # Simple agglomerative clustering implementation
        clusters = [[memory_id] for memory_id in memory_ids]
        
        while len(clusters) > max_clusters:
            # Find closest clusters
            min_distance = float('inf')
            merge_indices = (0, 1)
            
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    distance = self._cluster_distance(
                        clusters[i], clusters[j], embeddings
                    )
                    if distance < min_distance:
                        min_distance = distance
                        merge_indices = (i, j)
            
            # Stop if minimum distance is too large
            if min_distance > (1.0 - self.similarity_threshold):
                break
            
            # Merge closest clusters
            i, j = merge_indices
            merged_cluster = clusters[i] + clusters[j]
            
            # Remove old clusters (remove higher index first)
            if i > j:
                i, j = j, i
            del clusters[j]
            del clusters[i]
            
            # Add merged cluster
            clusters.append(merged_cluster)
        
        # Convert to result format with membership scores
        result_clusters = []
        for cluster in clusters:
            if len(cluster) >= min_size:
                # Calculate membership scores based on similarity to centroid
                cluster_embeddings = [embeddings[mid] for mid in cluster]
                centroid = np.mean(cluster_embeddings, axis=0)
                
                cluster_with_scores = []
                for memory_id in cluster:
                    embedding = np.array(embeddings[memory_id])
                    similarity = self._cosine_similarity(embedding, centroid)
                    cluster_with_scores.append((memory_id, float(similarity)))
                
                result_clusters.append(cluster_with_scores)
        
        return result_clusters
    
    def _cluster_distance(
        self,
        cluster1: List[UUID],
        cluster2: List[UUID],
        embeddings: Dict[UUID, List[float]]
    ) -> float:
        """Calculate distance between two clusters using average linkage."""
        distances = []
        
        for id1 in cluster1:
            for id2 in cluster2:
                emb1 = np.array(embeddings[id1])
                emb2 = np.array(embeddings[id2])
                distance = 1.0 - self._cosine_similarity(emb1, emb2)
                distances.append(distance)
        
        return sum(distances) / len(distances) if distances else float('inf')
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    async def _update_existing_clusters(self) -> List[UUID]:
        """Update centroids and statistics for existing clusters."""
        updated_clusters = []
        
        async with self.db_pool.acquire() as conn:
            # Get clusters that need updating
            clusters = await conn.fetch("""
                SELECT id FROM public.memory_clusters
                WHERE updated_at < NOW() - INTERVAL '1 hour'
            """)
            
            for cluster_row in clusters:
                cluster_id = cluster_row['id']
                
                # Get member embeddings
                members = await conn.fetch("""
                    SELECT 
                        mcm.memory_id,
                        mcm.membership_score,
                        cm.prompt_embedding,
                        cm.response_embedding
                    FROM public.memory_cluster_members mcm
                    INNER JOIN public.cognitive_memory cm ON mcm.memory_id = cm.id
                    WHERE mcm.cluster_id = $1 AND cm.is_validated = true
                """, cluster_id)
                
                if members:
                    # Calculate new centroid
                    embeddings = {}
                    for member in members:
                        combined_emb = (
                            np.array(member['prompt_embedding']) + 
                            np.array(member['response_embedding'])
                        ) / 2
                        embeddings[member['memory_id']] = combined_emb.tolist()
                    
                    # Create temporary cluster for centroid calculation
                    temp_cluster = MemoryCluster()
                    for member in members:
                        temp_cluster.add_member(
                            member['memory_id'], 
                            float(member['membership_score'])
                        )
                    
                    new_centroid = temp_cluster.calculate_centroid(embeddings)
                    
                    # Update cluster
                    await conn.execute("""
                        UPDATE public.memory_clusters
                        SET centroid_embedding = $2, updated_at = NOW()
                        WHERE id = $1
                    """, cluster_id, new_centroid)
                    
                    updated_clusters.append(cluster_id)
        
        return updated_clusters
    
    async def _calculate_clustering_quality(self) -> float:
        """Calculate overall clustering quality score."""
        async with self.db_pool.acquire() as conn:
            # Calculate silhouette-like score
            quality_metrics = await conn.fetchrow("""
                SELECT 
                    AVG(avg_safety_score) as avg_safety,
                    AVG(member_count) as avg_size,
                    COUNT(*) as total_clusters
                FROM public.memory_clusters
                WHERE member_count >= 2
            """)
            
            if not quality_metrics or quality_metrics['total_clusters'] == 0:
                return 0.0
            
            # Simple quality score based on safety and size distribution
            safety_score = float(quality_metrics['avg_safety']) if quality_metrics['avg_safety'] else 0
            size_score = min(1.0, float(quality_metrics['avg_size']) / 10.0)  # Normalize to 0-1
            cluster_count_score = min(1.0, quality_metrics['total_clusters'] / 20.0)  # Prefer more clusters up to 20
            
            return (safety_score * 0.5) + (size_score * 0.3) + (cluster_count_score * 0.2)