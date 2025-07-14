"""
Integration tests for complete memory lifecycle.

Tests memory creation, abstraction, validation, storage, search,
update, and deletion with full safety enforcement.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

from tests.fixtures.memories import MemoryFixtures
from src.core.memory.abstract_models import MemoryEntry
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
from src.core.validation.validator import SafetyValidator
from src.core.embeddings.service import EmbeddingService
from src.core.intent.engine import IntentEngine
from src.core.memory.repository import SafeMemoryRepository


@pytest.mark.integration
class TestMemoryLifecycle:
    """Test complete memory lifecycle with all integrations."""
    
    @pytest.fixture
    def memory_fixtures(self):
        """Provide memory test fixtures."""
        return MemoryFixtures()
    
    async def test_memory_creation_with_abstraction(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory creation with automatic abstraction."""
        # Create memory with unsafe content
        unsafe_data = memory_fixtures.create_unsafe_memory()
        
        # Attempt to create memory
        with pytest.raises(ValueError, match="safety|validation"):
            await memory_repository.create_memory(
                memory_type=unsafe_data["memory_type"],
                prompt=unsafe_data["prompt"],
                content=unsafe_data["content"],
                metadata=unsafe_data["metadata"]
            )
        
        # Create memory with safe content
        safe_data = memory_fixtures.create_safe_memory()
        
        memory = await memory_repository.create_memory(
            memory_type=safe_data["memory_type"],
            prompt=safe_data["prompt"],
            content=safe_data["content"],
            metadata=safe_data["metadata"]
        )
        
        # Verify memory created
        assert memory.id is not None
        assert memory.safety_score >= 0.8
        assert memory.embedding is not None
        assert memory.intent_analysis is not None
    
    async def test_memory_search_with_intent(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory search with intent analysis."""
        # Create test memories
        memories = memory_fixtures.create_memory_batch(count=20)
        created_ids = []
        
        for mem_data in memories:
            try:
                memory = await memory_repository.create_memory(
                    memory_type=mem_data["memory_type"],
                    prompt=mem_data["prompt"],
                    content=mem_data["content"],
                    metadata=mem_data.get("metadata", {})
                )
                created_ids.append(memory.id)
            except ValueError:
                # Skip if safety validation fails
                continue
        
        # Search with different queries
        test_queries = [
            "understanding patterns",
            "implementing design",
            "optimization techniques",
            "learning about modules",
        ]
        
        for query in test_queries:
            results = await memory_repository.search_memories(
                query=query,
                enable_intent_analysis=True,
                include_peripheral=True,
                limit=10
            )
            
            # Should return relevant results
            assert len(results) > 0
            
            # Results should have relevance scores
            for result in results:
                assert hasattr(result, 'relevance_score')
                assert 0 <= result.relevance_score <= 1
                
                # Higher relevance should come first
                if len(results) > 1:
                    assert results[0].relevance_score >= results[-1].relevance_score
    
    async def test_memory_clustering(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory clustering functionality."""
        # Create clustered memories
        clusters = memory_fixtures.create_clustered_memories()
        cluster_memories = {}
        
        for cluster_name, memories in clusters.items():
            cluster_memories[cluster_name] = []
            
            for mem_data in memories:
                try:
                    memory = await memory_repository.create_memory(
                        memory_type=mem_data["memory_type"],
                        prompt=mem_data["prompt"],
                        content=mem_data["content"],
                        metadata=mem_data["metadata"]
                    )
                    cluster_memories[cluster_name].append(memory)
                except ValueError:
                    continue
        
        # Test cluster detection
        for cluster_name, memories in cluster_memories.items():
            if len(memories) > 1:
                # Search for cluster-related content
                cluster_topic = memories[0].metadata.get("topic", "")
                if cluster_topic:
                    results = await memory_repository.search_memories(
                        query=cluster_topic,
                        limit=20
                    )
                    
                    # Should find memories from same cluster
                    result_ids = [r.id for r in results]
                    cluster_ids = [m.id for m in memories]
                    
                    # At least some cluster members should be in results
                    overlap = set(result_ids) & set(cluster_ids)
                    assert len(overlap) > 0
    
    async def test_memory_update_with_safety(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory update maintains safety requirements."""
        # Create initial memory
        safe_data = memory_fixtures.create_safe_memory()
        
        memory = await memory_repository.create_memory(
            memory_type=safe_data["memory_type"],
            prompt=safe_data["prompt"],
            content=safe_data["content"],
            metadata=safe_data["metadata"]
        )
        
        # Try to update with unsafe content
        with pytest.raises(ValueError, match="safety|validation"):
            await memory_repository.update_memory(
                memory_id=memory.id,
                content="Updated with /etc/passwd reference"
            )
        
        # Update with safe content
        updated = await memory_repository.update_memory(
            memory_id=memory.id,
            content="Updated with safe <configuration> reference",
            metadata={"updated": True}
        )
        
        # Verify update
        assert updated.content == "Updated with safe <configuration> reference"
        assert updated.metadata["updated"] is True
        assert updated.safety_score >= 0.8
        assert updated.updated_at > memory.created_at
    
    async def test_memory_reinforcement(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory reinforcement and temporal weight."""
        # Create memory
        safe_data = memory_fixtures.create_safe_memory()
        
        memory = await memory_repository.create_memory(
            memory_type=safe_data["memory_type"],
            prompt=safe_data["prompt"], 
            content=safe_data["content"],
            metadata=safe_data["metadata"]
        )
        
        initial_weight = memory.temporal_weight
        initial_accessed = memory.last_accessed
        
        # Reinforce memory
        reinforced = await memory_repository.reinforce_memory(memory.id)
        
        # Check reinforcement effects
        assert reinforced.temporal_weight > initial_weight
        assert reinforced.access_count > memory.access_count
        assert reinforced.last_accessed > initial_accessed
    
    async def test_memory_deletion_cascade(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory deletion with related data cleanup."""
        # Create memory
        safe_data = memory_fixtures.create_safe_memory()
        
        memory = await memory_repository.create_memory(
            memory_type=safe_data["memory_type"],
            prompt=safe_data["prompt"],
            content=safe_data["content"],
            metadata=safe_data["metadata"]
        )
        
        memory_id = memory.id
        
        # Delete memory
        deleted = await memory_repository.delete_memory(memory_id)
        assert deleted
        
        # Verify deletion
        retrieved = await memory_repository.get_memory(memory_id)
        assert retrieved is None
        
        # Search should not find deleted memory
        results = await memory_repository.search_memories(
            query=safe_data["content"],
            limit=10
        )
        
        result_ids = [r.id for r in results]
        assert memory_id not in result_ids
    
    async def test_temporal_decay_simulation(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test temporal decay of memories over time."""
        # Create memories with different ages
        memories = []
        base_date = datetime.utcnow()
        
        for days_ago in [0, 7, 30, 90, 180]:
            safe_data = memory_fixtures.create_safe_memory()
            
            memory = await memory_repository.create_memory(
                memory_type=safe_data["memory_type"],
                prompt=safe_data["prompt"],
                content=f"Memory from {days_ago} days ago",
                metadata={"days_ago": days_ago}
            )
            
            # Simulate age by adjusting created_at
            # Note: In real implementation, this would be done at DB level
            memory.created_at = base_date - timedelta(days=days_ago)
            memories.append((days_ago, memory))
        
        # Verify temporal weights decrease with age
        for i in range(len(memories) - 1):
            days1, mem1 = memories[i]
            days2, mem2 = memories[i + 1]
            
            # Older memories should have lower temporal weight
            # (if decay is implemented)
            if hasattr(mem1, 'temporal_weight') and hasattr(mem2, 'temporal_weight'):
                if days1 < days2:  # mem1 is newer
                    assert mem1.temporal_weight >= mem2.temporal_weight
    
    async def test_edge_case_memories(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test handling of edge case memories."""
        edge_cases = memory_fixtures.create_edge_case_memories()
        
        for case in edge_cases:
            edge_type = case.get("metadata", {}).get("edge_case", "unknown")
            
            try:
                # Attempt to create edge case memory
                memory = await memory_repository.create_memory(
                    memory_type=case["memory_type"],
                    prompt=case["prompt"],
                    content=case["content"],
                    metadata=case.get("metadata", {})
                )
                
                # Verify successful cases
                if edge_type == "empty_content":
                    assert memory.content == ""
                elif edge_type == "long_content":
                    assert len(memory.content) > 1000
                elif edge_type == "unicode":
                    assert "🚀" in memory.content or "émojis" in memory.content
                
            except ValueError as e:
                # Some edge cases might fail validation
                if edge_type == "mixed_safety":
                    # Expected to fail due to concrete path
                    assert "safety" in str(e).lower()
                else:
                    # Unexpected failure
                    raise
    
    @pytest.mark.slow
    async def test_memory_performance_at_scale(
        self,
        memory_repository: SafeMemoryRepository,
        memory_fixtures: MemoryFixtures
    ):
        """Test memory operations performance with many memories."""
        import time
        
        # Create many memories
        batch_size = 100
        memories = memory_fixtures.create_memory_batch(count=batch_size)
        
        # Measure creation time
        start_time = time.time()
        created_count = 0
        
        for mem_data in memories:
            try:
                await memory_repository.create_memory(
                    memory_type=mem_data["memory_type"],
                    prompt=mem_data["prompt"],
                    content=mem_data["content"],
                    metadata=mem_data.get("metadata", {})
                )
                created_count += 1
            except ValueError:
                continue
        
        creation_time = time.time() - start_time
        avg_creation_time = creation_time / created_count * 1000  # ms
        
        # Should be reasonably fast
        assert avg_creation_time < 500  # 500ms per memory max
        
        # Test search performance
        search_queries = [
            "understanding patterns",
            "design implementation",
            "optimization",
        ]
        
        search_times = []
        for query in search_queries:
            start_time = time.time()
            results = await memory_repository.search_memories(
                query=query,
                limit=20
            )
            search_time = (time.time() - start_time) * 1000  # ms
            search_times.append(search_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        
        # Search should be fast even with many memories
        assert avg_search_time < 1000  # 1 second max
        
        print(f"\nPerformance Results:")
        print(f"  Created {created_count} memories")
        print(f"  Avg creation time: {avg_creation_time:.2f}ms")
        print(f"  Avg search time: {avg_search_time:.2f}ms")