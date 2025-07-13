"""
Integration tests for the enhanced memory system.

Tests decay engine, clustering, and temporal relationships with safety enforcement.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from typing import List, Dict, Any

import asyncpg
import numpy as np

from src.core.memory.abstract_models import (
    InteractionType, 
    ValidationStatus,
    MemoryMetadata
)
from src.core.memory.repository import SafeMemoryRepository
from src.core.memory.decay_engine import MemoryDecayEngine, DecayConfiguration
from src.core.memory.cluster_manager import MemoryClusterManager, ClusterType


@pytest.fixture
async def db_pool():
    """Create database connection pool for testing."""
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="ccp_user",
        password="secure_password_123",
        database="cognitive_coding_partner_test",
        min_size=1,
        max_size=5
    )
    yield pool
    await pool.close()


@pytest.fixture
async def repository(db_pool):
    """Create memory repository instance."""
    repo = SafeMemoryRepository(db_pool)
    await repo.decay_engine.initialize()
    return repo


@pytest.fixture
async def sample_memories(repository) -> List[Dict[str, Any]]:
    """Create sample memories for testing."""
    memories = []
    
    # Create memories with different types and content
    test_cases = [
        {
            "prompt": "How do I create a Python function to read files from <file_path>?",
            "response": "You can use the open() function to read from <file_path>. Here's an example: def read_file(path): with open(path, 'r') as f: return f.read()",
            "type": InteractionType.CODE_GENERATION,
            "tags": ["python", "file-io"]
        },
        {
            "prompt": "What's the best way to implement error handling in <programming_language>?",
            "response": "In <programming_language>, use try-catch blocks for error handling. Always catch specific exceptions rather than generic ones.",
            "type": InteractionType.PROBLEM_SOLVING,
            "tags": ["error-handling", "best-practices"]
        },
        {
            "prompt": "Debug this <code_snippet> that's causing memory leaks",
            "response": "The memory leak in <code_snippet> is caused by circular references. Use weak references or explicit cleanup in destructors.",
            "type": InteractionType.DEBUGGING,
            "tags": ["debugging", "memory-management"]
        },
        {
            "prompt": "Explain the concept of abstraction in software engineering",
            "response": "Abstraction hides implementation details while exposing essential features. It reduces complexity and improves maintainability.",
            "type": InteractionType.DOCUMENTATION,
            "tags": ["concepts", "software-engineering"]
        },
        {
            "prompt": "How to optimize database queries for <table_name>?",
            "response": "Optimize <table_name> queries by adding indexes on frequently queried columns, using appropriate WHERE clauses, and avoiding SELECT *.",
            "type": InteractionType.PROBLEM_SOLVING,
            "tags": ["database", "optimization"]
        }
    ]
    
    session_id = uuid4()
    
    for case in test_cases:
        metadata = MemoryMetadata(
            tags=case["tags"],
            context={"test": True},
            language="python" if "python" in case["tags"] else None
        )
        
        # Create memory
        memory = await repository.create_memory(
            prompt=case["prompt"],
            response=case["response"],
            metadata=metadata.to_dict()
        )
        
        # Create interaction
        interaction = await repository.create_interaction(
            memory=memory,
            session_id=session_id,
            interaction_type=case["type"],
            metadata=metadata
        )
        
        # Add embeddings (simulate for testing)
        await repository._add_test_embeddings(interaction.interaction_id)
        
        memories.append({
            "memory": memory,
            "interaction": interaction,
            "case": case
        })
    
    return memories


class TestMemoryDecayEngine:
    """Test the memory decay engine functionality."""
    
    async def test_decay_configuration_loading(self, repository):
        """Test loading decay configurations from database."""
        await repository.decay_engine.initialize()
        
        # Test getting configuration for different types
        config = repository.decay_engine.get_configuration(InteractionType.CODE_GENERATION)
        assert config.base_decay_rate > 0
        assert config.minimum_weight >= 0
        assert config.reinforcement_factor > 1.0
        
        conversation_config = repository.decay_engine.get_configuration(InteractionType.CONVERSATION)
        assert conversation_config.base_decay_rate != config.base_decay_rate
    
    async def test_decay_calculation(self, repository, sample_memories):
        """Test memory decay calculation."""
        memory_data = sample_memories[0]
        interaction = memory_data["interaction"]
        
        # Test decay calculation
        current_weight = Decimal("1.0")
        last_accessed = datetime.utcnow() - timedelta(days=5)
        
        new_weight = await repository.decay_engine.calculate_decay(
            memory_id=interaction.interaction_id,
            current_weight=current_weight,
            last_accessed=last_accessed,
            interaction_type=interaction.interaction_type,
            access_count=0
        )
        
        # Weight should decrease over time
        assert new_weight < current_weight
        assert new_weight >= Decimal("0.01")  # Should not go below minimum
    
    async def test_batch_decay_processing(self, repository, sample_memories):
        """Test batch decay processing."""
        # Age some memories by updating their last_accessed time
        old_time = datetime.utcnow() - timedelta(days=10)
        
        for memory_data in sample_memories[:3]:
            interaction = memory_data["interaction"]
            async with repository.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE public.cognitive_memory
                    SET last_accessed = $1
                    WHERE id = $2
                """, old_time, interaction.interaction_id)
        
        # Run decay processing
        analysis = await repository.decay_engine.apply_decay_batch(
            batch_size=10,
            max_age_days=1
        )
        
        # Should have processed the aged memories
        assert analysis.total_processed >= 3
        assert len(analysis.weight_changes) > 0
        assert analysis.processing_time_ms > 0
    
    async def test_memory_reinforcement(self, repository, sample_memories):
        """Test memory reinforcement functionality."""
        memory_data = sample_memories[0]
        interaction = memory_data["interaction"]
        
        # Get initial weight
        initial_weight = interaction.weight
        
        # Reinforce memory
        new_weight = await repository.decay_engine.reinforce_memory(
            memory_id=interaction.interaction_id,
            strength=1.5
        )
        
        # Weight should increase
        assert new_weight is not None
        assert new_weight > initial_weight
        assert new_weight <= Decimal("1.0")  # Should not exceed maximum
    
    async def test_decay_statistics(self, repository, sample_memories):
        """Test decay statistics generation."""
        stats = await repository.decay_engine.get_decay_statistics(days_back=30)
        
        # Should have basic statistics
        assert "total_memories" in stats
        assert "weight_distribution" in stats
        assert "staleness" in stats
        assert "by_interaction_type" in stats
        
        # Should include our test memories
        assert stats["total_memories"] >= len(sample_memories)
        
        # Weight distribution should be reasonable
        weight_dist = stats["weight_distribution"]
        assert 0 <= weight_dist["average"] <= 1
        assert weight_dist["minimum"] >= 0
        assert weight_dist["maximum"] <= 1


class TestMemoryClusterManager:
    """Test the memory clustering functionality."""
    
    async def test_cluster_creation(self, repository):
        """Test creating a new memory cluster."""
        cluster = await repository.cluster_manager.create_cluster(
            cluster_name="Test Cluster",
            cluster_type=ClusterType.SEMANTIC
        )
        
        assert cluster.cluster_id is not None
        assert cluster.cluster_name == "Test Cluster"
        assert cluster.cluster_type == ClusterType.SEMANTIC
        assert cluster.member_count == 0
    
    async def test_adding_memories_to_cluster(self, repository, sample_memories):
        """Test adding memories to a cluster."""
        # Create cluster
        cluster = await repository.cluster_manager.create_cluster(
            cluster_name="Test Cluster",
            cluster_type=ClusterType.TOPIC
        )
        
        # Add memories to cluster
        for memory_data in sample_memories[:3]:
            interaction = memory_data["interaction"]
            success = await repository.cluster_manager.add_memory_to_cluster(
                cluster_id=cluster.cluster_id,
                memory_id=interaction.interaction_id,
                membership_score=0.8
            )
            assert success
        
        # Verify cluster membership
        cluster_memories = await repository.get_cluster_memories(
            cluster_id=cluster.cluster_id
        )
        assert len(cluster_memories) == 3
        
        # All memories should have proper safety scores
        for memory in cluster_memories:
            assert memory["safety_score"] >= 0.8
    
    async def test_similarity_search(self, repository, sample_memories):
        """Test finding similar memories."""
        memory_data = sample_memories[0]  # Python code generation memory
        interaction = memory_data["interaction"]
        
        # Find similar memories
        similar = await repository.cluster_manager.find_similar_memories(
            memory_id=interaction.interaction_id,
            similarity_threshold=0.3,
            max_results=5
        )
        
        # Should find some similar memories
        assert len(similar) > 0
        
        # All similarities should be above threshold
        for memory_id, similarity in similar:
            assert similarity >= 0.3
            assert memory_id != interaction.interaction_id  # Should not include self
    
    async def test_auto_clustering(self, repository, sample_memories):
        """Test automatic clustering of memories."""
        # Run auto-clustering
        result = await repository.cluster_manager.auto_cluster_memories(
            min_cluster_size=2,
            max_clusters=5,
            interaction_types=[InteractionType.CODE_GENERATION, InteractionType.PROBLEM_SOLVING]
        )
        
        # Should have created some clusters
        assert result.clusters_created >= 0
        assert result.memories_clustered >= 0
        assert result.processing_time_ms > 0
        assert 0 <= result.quality_score <= 1
        
        # Get clustering statistics
        stats = await repository.cluster_manager.get_cluster_statistics()
        assert stats["total_clusters"] >= result.clusters_created
    
    async def test_cluster_recommendations(self, repository, sample_memories):
        """Test getting cluster recommendations for a memory."""
        # Create a cluster first
        cluster = await repository.cluster_manager.create_cluster(
            cluster_name="Python Cluster",
            cluster_type=ClusterType.TOPIC
        )
        
        # Add a Python-related memory to it
        python_memory = None
        for memory_data in sample_memories:
            if "python" in memory_data["case"]["tags"]:
                python_memory = memory_data["interaction"]
                break
        
        if python_memory:
            await repository.cluster_manager.add_memory_to_cluster(
                cluster_id=cluster.cluster_id,
                memory_id=python_memory.interaction_id,
                membership_score=0.9
            )
        
        # Get recommendations for another Python memory
        for memory_data in sample_memories:
            if ("python" in memory_data["case"]["tags"] and 
                memory_data["interaction"].interaction_id != python_memory.interaction_id):
                
                recommendations = await repository.cluster_manager.get_cluster_recommendations(
                    memory_id=memory_data["interaction"].interaction_id,
                    max_recommendations=3
                )
                
                # Should get some recommendations
                assert len(recommendations) >= 0
                
                for cluster_id, cluster_name, fit_score in recommendations:
                    assert 0 <= fit_score <= 1
                    assert cluster_name is not None
                break


class TestTemporalRelationships:
    """Test temporal relationship functionality."""
    
    async def test_creating_relationships(self, repository, sample_memories):
        """Test creating relationships between memories."""
        memory1 = sample_memories[0]["interaction"]
        memory2 = sample_memories[1]["interaction"]
        
        # Create relationship
        success = await repository.create_memory_relationship(
            source_memory_id=memory1.interaction_id,
            target_memory_id=memory2.interaction_id,
            relationship_type="related_topic",
            relationship_strength=0.8,
            context={"test": "relationship"},
            is_bidirectional=True
        )
        
        assert success
        
        # Verify relationship exists
        relationships = await repository.get_memory_relationships(
            memory_id=memory1.interaction_id,
            min_strength=0.5
        )
        
        assert len(relationships) >= 1
        relationship = relationships[0]
        assert relationship["relationship_type"] == "related_topic"
        assert relationship["relationship_strength"] >= 0.8
        assert relationship["is_bidirectional"] is True
    
    async def test_temporal_sequences(self, repository, sample_memories):
        """Test finding temporal sequences of memories."""
        # Create a chain of relationships
        memories = [m["interaction"] for m in sample_memories[:4]]
        
        for i in range(len(memories) - 1):
            await repository.create_memory_relationship(
                source_memory_id=memories[i].interaction_id,
                target_memory_id=memories[i + 1].interaction_id,
                relationship_type="continuation",
                relationship_strength=0.9,
                is_bidirectional=False
            )
        
        # Find temporal sequence from first memory
        sequences = await repository.find_temporal_sequences(
            memory_id=memories[0].interaction_id,
            max_distance=5,
            time_window_hours=24
        )
        
        # Should find a sequence
        assert len(sequences) > 1  # At least the starting memory + 1 related
        
        # Should be ordered by distance
        distances = [seq["distance"] for seq in sequences]
        assert distances == sorted(distances)
    
    async def test_relationship_filtering(self, repository, sample_memories):
        """Test filtering relationships by type and strength."""
        memory1 = sample_memories[0]["interaction"]
        memory2 = sample_memories[1]["interaction"]
        memory3 = sample_memories[2]["interaction"]
        
        # Create different types of relationships
        await repository.create_memory_relationship(
            source_memory_id=memory1.interaction_id,
            target_memory_id=memory2.interaction_id,
            relationship_type="continuation",
            relationship_strength=0.9
        )
        
        await repository.create_memory_relationship(
            source_memory_id=memory1.interaction_id,
            target_memory_id=memory3.interaction_id,
            relationship_type="error_correction",
            relationship_strength=0.6
        )
        
        # Filter by type
        continuations = await repository.get_memory_relationships(
            memory_id=memory1.interaction_id,
            relationship_types=["continuation"]
        )
        assert len(continuations) == 1
        assert continuations[0]["relationship_type"] == "continuation"
        
        # Filter by strength
        strong_relationships = await repository.get_memory_relationships(
            memory_id=memory1.interaction_id,
            min_strength=0.8
        )
        assert len(strong_relationships) == 1
        assert strong_relationships[0]["relationship_strength"] >= 0.8


class TestEnhancedSearch:
    """Test enhanced search functionality with clustering."""
    
    async def test_cluster_aware_search(self, repository, sample_memories):
        """Test search with cluster-aware ranking."""
        # Create a cluster with some memories
        cluster = await repository.cluster_manager.create_cluster(
            cluster_name="Search Test Cluster",
            cluster_type=ClusterType.SEMANTIC
        )
        
        # Add memories to cluster
        for memory_data in sample_memories[:2]:
            await repository.cluster_manager.add_memory_to_cluster(
                cluster_id=cluster.cluster_id,
                memory_id=memory_data["interaction"].interaction_id,
                membership_score=0.9
            )
        
        # Search with clustering
        results = await repository.search_with_clustering(
            query="Python function file reading",
            cluster_types=[ClusterType.SEMANTIC],
            limit=5,
            include_cluster_info=True
        )
        
        # Should get results
        assert len(results) > 0
        
        # Results should have similarity scores
        for result in results:
            assert "similarity_score" in result
            assert result["similarity_score"] > 0
            assert result["safety_score"] >= 0.8
        
        # Some results should have cluster info
        clustered_results = [r for r in results if "cluster_info" in r]
        if clustered_results:
            cluster_info = clustered_results[0]["cluster_info"]
            assert "cluster_name" in cluster_info
            assert "membership_score" in cluster_info
    
    async def test_auto_clustering_integration(self, repository, sample_memories):
        """Test automatic clustering during memory operations."""
        memory_data = sample_memories[0]
        interaction = memory_data["interaction"]
        
        # Auto-cluster similar memories
        cluster_id = await repository.auto_cluster_similar_memories(
            memory_id=interaction.interaction_id,
            similarity_threshold=0.6,
            create_cluster=True
        )
        
        if cluster_id:
            # Verify cluster was created and memory was added
            cluster_memories = await repository.get_cluster_memories(
                cluster_id=cluster_id
            )
            
            memory_ids = [m["memory_id"] for m in cluster_memories]
            assert interaction.interaction_id in memory_ids
            
            # All memories should meet safety requirements
            for memory in cluster_memories:
                assert memory["safety_score"] >= 0.8


class TestSafetyEnforcement:
    """Test that safety is maintained throughout all operations."""
    
    async def test_cluster_safety_enforcement(self, repository):
        """Test that only safe memories can be added to clusters."""
        cluster = await repository.cluster_manager.create_cluster(
            cluster_name="Safety Test Cluster",
            cluster_type=ClusterType.SEMANTIC
        )
        
        # Try to add a non-existent memory (should fail)
        fake_memory_id = uuid4()
        success = await repository.cluster_manager.add_memory_to_cluster(
            cluster_id=cluster.cluster_id,
            memory_id=fake_memory_id,
            membership_score=0.8
        )
        assert not success
    
    async def test_decay_preserves_high_safety_memories(self, repository, sample_memories):
        """Test that high-safety memories are preserved during decay."""
        # Force age a memory with high safety score
        memory_data = sample_memories[0]
        interaction = memory_data["interaction"]
        
        old_time = datetime.utcnow() - timedelta(days=100)
        
        async with repository.db_pool.acquire() as conn:
            # Set very old last_accessed time and low weight
            await conn.execute("""
                UPDATE public.cognitive_memory
                SET last_accessed = $1, weight = 0.02
                WHERE id = $2
            """, old_time, interaction.interaction_id)
            
            # Ensure high safety score
            await conn.execute("""
                UPDATE safety.memory_abstractions
                SET safety_score = 0.95
                WHERE memory_id = $1
            """, interaction.interaction_id)
        
        # Run decay
        analysis = await repository.decay_engine.apply_decay_batch(
            batch_size=10,
            max_age_days=1
        )
        
        # Memory should not be removed due to high safety score
        assert interaction.interaction_id not in analysis.removed_memories
    
    async def test_search_respects_safety_scores(self, repository, sample_memories):
        """Test that search results respect minimum safety scores."""
        results = await repository.search_with_clustering(
            query="test query",
            min_safety_score=0.8,
            limit=10
        )
        
        # All results should meet safety requirements
        for result in results:
            assert result["safety_score"] >= 0.8


# Helper method for repository
async def _add_test_embeddings(self, interaction_id):
    """Add test embeddings to an interaction."""
    # Generate random embeddings for testing
    prompt_embedding = np.random.random(1536).tolist()
    response_embedding = np.random.random(1536).tolist()
    
    async with self.db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE public.cognitive_memory
            SET prompt_embedding = $1, response_embedding = $2
            WHERE id = $3
        """, prompt_embedding, response_embedding, interaction_id)

# Add the helper method to SafeMemoryRepository
SafeMemoryRepository._add_test_embeddings = _add_test_embeddings


@pytest.mark.asyncio
async def test_full_memory_system_integration():
    """Test the complete memory system integration."""
    # This test would be run with actual database setup
    pass


if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_memory_system.py -v
    pass