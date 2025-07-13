"""
Tests for embedding models and data structures.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.core.embeddings.models import (
    ContentType,
    ModelConfig,
    EmbeddingMetadata,
    EmbeddingResult,
    CacheEntry,
    BatchEmbeddingRequest,
    BatchEmbeddingResult,
    EmbeddingQualityMetrics,
    generate_content_hash,
    normalize_vector,
    calculate_cosine_similarity
)


class TestContentType:
    """Test ContentType enum."""
    
    def test_content_types(self):
        """Test all content types are available."""
        assert ContentType.TEXT.value == "text"
        assert ContentType.CODE.value == "code"
        assert ContentType.DOCUMENTATION.value == "documentation"
        assert ContentType.QUERY.value == "query"
        assert ContentType.MIXED.value == "mixed"


class TestModelConfig:
    """Test ModelConfig validation."""
    
    def test_valid_config(self):
        """Test valid model configuration."""
        config = ModelConfig(
            model_name="test-model",
            content_types=[ContentType.TEXT],
            dimensions=384,
            max_length=512,
            batch_size=32
        )
        
        assert config.model_name == "test-model"
        assert config.dimensions == 384
        assert config.max_length == 512
        assert config.batch_size == 32
    
    def test_invalid_model_name(self):
        """Test model name validation."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ModelConfig(
                model_name="",
                content_types=[ContentType.TEXT]
            )
        
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ModelConfig(
                model_name="   ",
                content_types=[ContentType.TEXT]
            )
    
    def test_model_name_strip(self):
        """Test model name is stripped."""
        config = ModelConfig(
            model_name="  test-model  ",
            content_types=[ContentType.TEXT]
        )
        assert config.model_name == "test-model"


class TestEmbeddingMetadata:
    """Test EmbeddingMetadata validation."""
    
    def test_valid_metadata(self):
        """Test valid metadata creation."""
        content_hash = "a" * 64  # Valid SHA-256 hex
        metadata = EmbeddingMetadata(
            content_type=ContentType.TEXT,
            model_name="test-model",
            content_hash=content_hash,
            safety_score=Decimal("0.9"),
            dimensions=384
        )
        
        assert metadata.content_type == ContentType.TEXT
        assert metadata.model_name == "test-model"
        assert metadata.content_hash == content_hash
        assert metadata.safety_score == Decimal("0.9")
        assert metadata.dimensions == 384
    
    def test_invalid_content_hash(self):
        """Test content hash validation."""
        with pytest.raises(ValueError, match="Content hash must be 64-character"):
            EmbeddingMetadata(
                content_type=ContentType.TEXT,
                model_name="test-model",
                content_hash="invalid",
                safety_score=Decimal("0.9")
            )
    
    def test_invalid_safety_score(self):
        """Test safety score validation."""
        content_hash = "a" * 64
        
        with pytest.raises(ValueError, match="Safety score must be between 0.0 and 1.0"):
            EmbeddingMetadata(
                content_type=ContentType.TEXT,
                model_name="test-model",
                content_hash=content_hash,
                safety_score=Decimal("-0.1")
            )
        
        with pytest.raises(ValueError, match="Safety score must be between 0.0 and 1.0"):
            EmbeddingMetadata(
                content_type=ContentType.TEXT,
                model_name="test-model",
                content_hash=content_hash,
                safety_score=Decimal("1.1")
            )


class TestEmbeddingResult:
    """Test EmbeddingResult validation."""
    
    def create_valid_metadata(self):
        """Create valid metadata for testing."""
        return EmbeddingMetadata(
            content_type=ContentType.TEXT,
            model_name="test-model",
            content_hash="a" * 64,
            safety_score=Decimal("0.9"),
            dimensions=3
        )
    
    def test_valid_result(self):
        """Test valid embedding result."""
        metadata = self.create_valid_metadata()
        vector = [0.1, 0.2, 0.3]
        
        result = EmbeddingResult(
            vector=vector,
            metadata=metadata,
            processing_time_ms=100
        )
        
        assert result.vector == vector
        assert result.metadata == metadata
        assert result.processing_time_ms == 100
        assert result.cache_hit is False
    
    def test_vector_dimension_mismatch(self):
        """Test vector dimension validation."""
        metadata = self.create_valid_metadata()  # dimensions=3
        vector = [0.1, 0.2]  # Only 2 dimensions
        
        with pytest.raises(ValueError, match="Vector length .* doesn't match metadata dimensions"):
            EmbeddingResult(
                vector=vector,
                metadata=metadata
            )
    
    def test_invalid_vector_values(self):
        """Test vector value validation."""
        metadata = self.create_valid_metadata()
        
        # Test non-numeric values
        with pytest.raises(ValueError, match="Vector must contain only numeric values"):
            EmbeddingResult(
                vector=["a", "b", "c"],
                metadata=metadata
            )
        
        # Test values outside range
        with pytest.raises(ValueError, match="Vector values should be normalized"):
            EmbeddingResult(
                vector=[2.0, 0.0, 0.0],  # Value > 1.0
                metadata=metadata
            )


class TestCacheEntry:
    """Test CacheEntry functionality."""
    
    def create_valid_result(self):
        """Create valid embedding result for testing."""
        metadata = EmbeddingMetadata(
            content_type=ContentType.TEXT,
            model_name="test-model",
            content_hash="a" * 64,
            safety_score=Decimal("0.9"),
            dimensions=3
        )
        
        return EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            metadata=metadata
        )
    
    def test_valid_entry(self):
        """Test valid cache entry."""
        result = self.create_valid_result()
        entry = CacheEntry(
            cache_key="test-key",
            embedding_result=result,
            ttl_seconds=3600
        )
        
        assert entry.cache_key == "test-key"
        assert entry.embedding_result == result
        assert entry.ttl_seconds == 3600
        assert entry.access_count == 0
    
    def test_invalid_cache_key(self):
        """Test cache key validation."""
        result = self.create_valid_result()
        
        with pytest.raises(ValueError, match="Cache key cannot be empty"):
            CacheEntry(
                cache_key="",
                embedding_result=result
            )
        
        with pytest.raises(ValueError, match="Cache key cannot be empty"):
            CacheEntry(
                cache_key="   ",
                embedding_result=result
            )
    
    def test_cache_key_strip(self):
        """Test cache key is stripped."""
        result = self.create_valid_result()
        entry = CacheEntry(
            cache_key="  test-key  ",
            embedding_result=result
        )
        assert entry.cache_key == "test-key"
    
    def test_expiration(self):
        """Test cache entry expiration."""
        result = self.create_valid_result()
        
        # Entry without TTL never expires
        entry = CacheEntry(
            cache_key="test-key",
            embedding_result=result,
            ttl_seconds=None
        )
        assert not entry.is_expired()
        
        # Entry with very short TTL expires quickly
        entry = CacheEntry(
            cache_key="test-key",
            embedding_result=result,
            ttl_seconds=0
        )
        assert entry.is_expired()
    
    def test_touch(self):
        """Test access count update."""
        result = self.create_valid_result()
        entry = CacheEntry(
            cache_key="test-key",
            embedding_result=result
        )
        
        assert entry.access_count == 0
        initial_accessed = entry.last_accessed
        
        entry.touch()
        
        assert entry.access_count == 1
        assert entry.last_accessed >= initial_accessed


class TestBatchEmbeddingRequest:
    """Test BatchEmbeddingRequest validation."""
    
    def test_valid_request(self):
        """Test valid batch request."""
        request = BatchEmbeddingRequest(
            texts=["text1", "text2", "text3"],
            content_type=ContentType.TEXT,
            model_name="test-model"
        )
        
        assert len(request.texts) == 3
        assert request.content_type == ContentType.TEXT
        assert request.model_name == "test-model"
    
    def test_empty_texts(self):
        """Test empty texts validation."""
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            BatchEmbeddingRequest(texts=[])
    
    def test_too_many_texts(self):
        """Test batch size limit."""
        texts = [f"text{i}" for i in range(101)]  # 101 texts
        
        with pytest.raises(ValueError, match="Batch size cannot exceed 100"):
            BatchEmbeddingRequest(texts=texts)
    
    def test_empty_text_in_batch(self):
        """Test empty text in batch."""
        with pytest.raises(ValueError, match="All texts must be non-empty"):
            BatchEmbeddingRequest(texts=["text1", "", "text3"])
        
        with pytest.raises(ValueError, match="All texts must be non-empty"):
            BatchEmbeddingRequest(texts=["text1", "   ", "text3"])


class TestBatchEmbeddingResult:
    """Test BatchEmbeddingResult functionality."""
    
    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        result = BatchEmbeddingResult(
            results=[],
            cache_hits=3,
            generated_count=2
        )
        
        # Simulate 5 total results (3 cache hits + 2 generated)
        result.results = [None] * 5
        
        assert result.cache_hit_rate == 0.6  # 3/5
    
    def test_average_processing_time(self):
        """Test average processing time calculation."""
        result = BatchEmbeddingResult(
            results=[],
            total_processing_time_ms=1000,
            generated_count=4
        )
        
        assert result.average_processing_time_ms == 250.0  # 1000/4
    
    def test_zero_division_protection(self):
        """Test zero division protection."""
        result = BatchEmbeddingResult(results=[], cache_hits=0, generated_count=0)
        
        assert result.cache_hit_rate == 0.0
        assert result.average_processing_time_ms == 0.0


class TestEmbeddingQualityMetrics:
    """Test EmbeddingQualityMetrics validation."""
    
    def test_valid_metrics(self):
        """Test valid quality metrics."""
        metrics = EmbeddingQualityMetrics(
            embedding_id=uuid4(),
            consistency_score=0.8,
            diversity_score=0.6,
            magnitude=0.9,
            sparsity=0.1,
            outlier_score=0.2
        )
        
        assert 0.0 <= metrics.consistency_score <= 1.0
        assert 0.0 <= metrics.diversity_score <= 1.0
        assert 0.0 <= metrics.magnitude <= 1.0
        assert 0.0 <= metrics.sparsity <= 1.0
        assert 0.0 <= metrics.outlier_score <= 1.0
    
    def test_invalid_metric_values(self):
        """Test metric value validation."""
        embedding_id = uuid4()
        
        with pytest.raises(ValueError, match="Metric values must be between 0.0 and 1.0"):
            EmbeddingQualityMetrics(
                embedding_id=embedding_id,
                consistency_score=-0.1
            )
        
        with pytest.raises(ValueError, match="Metric values must be between 0.0 and 1.0"):
            EmbeddingQualityMetrics(
                embedding_id=embedding_id,
                diversity_score=1.1
            )


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_generate_content_hash(self):
        """Test content hash generation."""
        hash1 = generate_content_hash("test content", "model1")
        hash2 = generate_content_hash("test content", "model1")
        hash3 = generate_content_hash("test content", "model2")
        hash4 = generate_content_hash("different content", "model1")
        
        # Same content and model should produce same hash
        assert hash1 == hash2
        
        # Different model should produce different hash
        assert hash1 != hash3
        
        # Different content should produce different hash
        assert hash1 != hash4
        
        # All hashes should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64
        assert len(hash3) == 64
        assert len(hash4) == 64
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        # Test normal vector
        vector = [3.0, 4.0]
        normalized = normalize_vector(vector)
        magnitude = sum(x * x for x in normalized) ** 0.5
        assert abs(magnitude - 1.0) < 1e-7
        
        # Test zero vector
        zero_vector = [0.0, 0.0]
        normalized_zero = normalize_vector(zero_vector)
        assert normalized_zero == zero_vector
        
        # Test single element
        single = [5.0]
        normalized_single = normalize_vector(single)
        assert normalized_single == [1.0]
    
    def test_calculate_cosine_similarity(self):
        """Test cosine similarity calculation."""
        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-7
        
        # Test orthogonal vectors
        vec3 = [1.0, 0.0, 0.0]
        vec4 = [0.0, 1.0, 0.0]
        similarity = calculate_cosine_similarity(vec3, vec4)
        assert abs(similarity - 0.0) < 1e-7
        
        # Test opposite vectors
        vec5 = [1.0, 0.0, 0.0]
        vec6 = [-1.0, 0.0, 0.0]
        similarity = calculate_cosine_similarity(vec5, vec6)
        assert abs(similarity - (-1.0)) < 1e-7
        
        # Test dimension mismatch
        with pytest.raises(ValueError, match="Vectors must have the same dimensions"):
            calculate_cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
        
        # Test zero vectors
        zero1 = [0.0, 0.0]
        zero2 = [0.0, 0.0]
        similarity = calculate_cosine_similarity(zero1, zero2)
        assert similarity == 0.0