"""
Tests for embedding cache functionality.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime

from src.core.embeddings.cache import EmbeddingCache
from src.core.embeddings.models import (
    EmbeddingResult,
    EmbeddingMetadata,
    ContentType,
    CacheEntry
)


class TestEmbeddingCache:
    """Test EmbeddingCache functionality."""
    
    def create_test_embedding(self, content: str = "test", dimensions: int = 3) -> EmbeddingResult:
        """Create a test embedding result."""
        metadata = EmbeddingMetadata(
            content_type=ContentType.TEXT,
            model_name="test-model",
            content_hash="a" * 64,
            safety_score=Decimal("0.9"),
            dimensions=dimensions
        )
        
        vector = [0.1] * dimensions
        
        return EmbeddingResult(
            vector=vector,
            metadata=metadata,
            processing_time_ms=100
        )
    
    @pytest.fixture
    def cache(self):
        """Create cache instance for testing."""
        return EmbeddingCache(
            max_size=5,
            default_ttl_seconds=3600,
            min_safety_score=0.8
        )
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = EmbeddingCache(
            max_size=100,
            default_ttl_seconds=1800,
            min_safety_score=0.7
        )
        
        assert cache.max_size == 100
        assert cache.default_ttl_seconds == 1800
        assert cache.min_safety_score == 0.7
        assert cache.enable_stats is True
    
    def test_generate_cache_key(self, cache):
        """Test cache key generation."""
        key1 = cache.generate_cache_key(
            "test content",
            "model1",
            ContentType.TEXT,
            "en"
        )
        
        key2 = cache.generate_cache_key(
            "test content",
            "model1",
            ContentType.TEXT,
            "en"
        )
        
        key3 = cache.generate_cache_key(
            "test content",
            "model2",  # Different model
            ContentType.TEXT,
            "en"
        )
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different model should generate different key
        assert key1 != key3
        
        # Key should be deterministic
        assert len(key1.split(":")) == 4  # hash:content_type:model:language
    
    @pytest.mark.asyncio
    async def test_put_and_get(self, cache):
        """Test basic put and get operations."""
        embedding = self.create_test_embedding()
        cache_key = "test-key"
        
        # Put embedding in cache
        success = await cache.put(cache_key, embedding)
        assert success is True
        
        # Retrieve embedding from cache
        cached_embedding = await cache.get(cache_key)
        assert cached_embedding is not None
        assert cached_embedding.vector == embedding.vector
        assert cached_embedding.cache_hit is True
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss behavior."""
        result = await cache.get("nonexistent-key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_safety_score_rejection(self, cache):
        """Test rejection of low safety score embeddings."""
        # Create embedding with low safety score
        embedding = self.create_test_embedding()
        embedding.metadata.safety_score = Decimal("0.7")  # Below threshold
        
        cache_key = "low-safety-key"
        
        # Should reject storage
        success = await cache.put(cache_key, embedding)
        assert success is False
        
        # Should not be retrievable
        result = await cache.get(cache_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_safety_score_filtering(self, cache):
        """Test filtering of cached embeddings that become unsafe."""
        # Create embedding with good safety score
        embedding = self.create_test_embedding()
        embedding.metadata.safety_score = Decimal("0.9")
        
        cache_key = "test-key"
        
        # Store in cache
        await cache.put(cache_key, embedding)
        
        # Modify minimum safety score to be higher
        cache.min_safety_score = 0.95
        
        # Should be rejected on retrieval
        result = await cache.get(cache_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        # Create cache with very short TTL
        cache = EmbeddingCache(
            max_size=5,
            default_ttl_seconds=0,  # Immediate expiration
            min_safety_score=0.8
        )
        
        embedding = self.create_test_embedding()
        cache_key = "expiring-key"
        
        # Store in cache
        await cache.put(cache_key, embedding)
        
        # Should be expired immediately
        result = await cache.get(cache_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction behavior."""
        # Fill cache to capacity
        embeddings = []
        for i in range(5):  # Cache max_size is 5
            embedding = self.create_test_embedding(f"content{i}")
            key = f"key{i}"
            embeddings.append((key, embedding))
            await cache.put(key, embedding)
        
        # Add one more to trigger eviction
        extra_embedding = self.create_test_embedding("extra")
        await cache.put("extra-key", extra_embedding)
        
        # First key should be evicted
        result = await cache.get("key0")
        assert result is None
        
        # Last key should still be there
        result = await cache.get("extra-key")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_lru_access_order(self, cache):
        """Test LRU access order updating."""
        # Add two items
        emb1 = self.create_test_embedding("content1")
        emb2 = self.create_test_embedding("content2")
        
        await cache.put("key1", emb1)
        await cache.put("key2", emb2)
        
        # Access first item to make it recently used
        await cache.get("key1")
        
        # Fill cache to capacity
        for i in range(4):  # Add 3 more (cache size is 5)
            embedding = self.create_test_embedding(f"filler{i}")
            await cache.put(f"filler{i}", embedding)
        
        # Key2 should be evicted (oldest unused), key1 should remain
        assert await cache.get("key1") is not None
        assert await cache.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_batch_operations(self, cache):
        """Test batch put and get operations."""
        # Create multiple embeddings
        embeddings = {}
        for i in range(3):
            key = f"batch-key{i}"
            embedding = self.create_test_embedding(f"content{i}")
            embeddings[key] = embedding
        
        # Batch put
        success_count = await cache.put_batch(embeddings)
        assert success_count == 3
        
        # Batch get
        keys = list(embeddings.keys())
        results = await cache.get_batch(keys)
        
        assert len(results) == 3
        for key in keys:
            assert key in results
            assert results[key].cache_hit is True
    
    @pytest.mark.asyncio
    async def test_invalidation(self, cache):
        """Test cache invalidation."""
        embedding = self.create_test_embedding()
        cache_key = "test-key"
        
        # Store and verify
        await cache.put(cache_key, embedding)
        assert await cache.get(cache_key) is not None
        
        # Invalidate specific key
        success = await cache.invalidate(cache_key)
        assert success is True
        assert await cache.get(cache_key) is None
        
        # Invalidate non-existent key
        success = await cache.invalidate("nonexistent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_pattern_invalidation(self, cache):
        """Test pattern-based invalidation."""
        # Add multiple embeddings with different patterns
        patterns = ["model1-key1", "model1-key2", "model2-key1"]
        for pattern in patterns:
            embedding = self.create_test_embedding()
            await cache.put(pattern, embedding)
        
        # Invalidate all model1 keys
        count = await cache.invalidate_pattern("model1")
        assert count == 2
        
        # Check results
        assert await cache.get("model1-key1") is None
        assert await cache.get("model1-key2") is None
        assert await cache.get("model2-key1") is not None
    
    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test cache clearing."""
        # Add multiple embeddings
        for i in range(3):
            embedding = self.create_test_embedding(f"content{i}")
            await cache.put(f"key{i}", embedding)
        
        # Clear cache
        await cache.clear()
        
        # All should be gone
        for i in range(3):
            assert await cache.get(f"key{i}") is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test expired entry cleanup."""
        # Create cache with mixed TTLs
        cache = EmbeddingCache(max_size=5, default_ttl_seconds=3600)
        
        # Add entries with different TTLs
        emb1 = self.create_test_embedding("content1")
        emb2 = self.create_test_embedding("content2")
        emb3 = self.create_test_embedding("content3")
        
        await cache.put("key1", emb1, ttl_seconds=0)  # Expired
        await cache.put("key2", emb2, ttl_seconds=3600)  # Not expired
        await cache.put("key3", emb3, ttl_seconds=0)  # Expired
        
        # Cleanup expired entries
        cleaned_count = await cache.cleanup_expired()
        assert cleaned_count == 2
        
        # Check remaining entries
        assert await cache.get("key1") is None
        assert await cache.get("key2") is not None
        assert await cache.get("key3") is None
    
    def test_get_stats(self, cache):
        """Test statistics collection."""
        stats = cache.get_stats()
        
        expected_keys = [
            'hits', 'misses', 'evictions', 'expirations',
            'safety_rejections', 'total_requests', 'cache_size',
            'max_size', 'hit_rate', 'memory_usage_estimate'
        ]
        
        for key in expected_keys:
            assert key in stats
        
        assert stats['max_size'] == 5
        assert stats['cache_size'] == 0
        assert stats['hit_rate'] == 0.0
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, cache):
        """Test statistics tracking during operations."""
        embedding = self.create_test_embedding()
        cache_key = "test-key"
        
        # Initial stats
        initial_stats = cache.get_stats()
        
        # Put and get operations
        await cache.put(cache_key, embedding)
        await cache.get(cache_key)  # Hit
        await cache.get("nonexistent")  # Miss
        
        # Check updated stats
        final_stats = cache.get_stats()
        
        assert final_stats['hits'] == initial_stats['hits'] + 1
        assert final_stats['misses'] == initial_stats['misses'] + 1
        assert final_stats['total_requests'] == initial_stats['total_requests'] + 2
        assert final_stats['cache_size'] == 1
    
    def test_get_cache_info(self, cache):
        """Test detailed cache information."""
        info = cache.get_cache_info()
        
        expected_keys = [
            'total_entries', 'max_size', 'default_ttl_seconds',
            'min_safety_score', 'entries'
        ]
        
        for key in expected_keys:
            assert key in info
        
        assert info['total_entries'] == 0
        assert info['max_size'] == 5
        assert info['entries'] == []
    
    @pytest.mark.asyncio
    async def test_cache_info_with_entries(self, cache):
        """Test cache info with actual entries."""
        # Add an embedding
        embedding = self.create_test_embedding()
        await cache.put("test-key", embedding)
        
        info = cache.get_cache_info()
        
        assert info['total_entries'] == 1
        assert len(info['entries']) == 1
        
        entry_info = info['entries'][0]
        assert entry_info['key'] == "test-key"
        assert entry_info['access_count'] == 0
        assert entry_info['safety_score'] == 0.9
        assert entry_info['dimensions'] == 3
        assert entry_info['expired'] is False
    
    def test_memory_usage_estimation(self, cache):
        """Test memory usage estimation."""
        stats = cache.get_stats()
        
        # Empty cache should have zero usage
        assert stats['memory_usage_estimate'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test behavior when cache is disabled."""
        # This would be tested in the service tests where cache=None
        pass