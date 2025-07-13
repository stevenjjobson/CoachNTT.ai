"""
Integration tests for the embedding system.

Tests the complete embedding pipeline including service, cache, and memory integration.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.core.embeddings import (
    EmbeddingService,
    EmbeddingCache,
    ContentType,
    BatchEmbeddingRequest
)
from src.core.memory import SafeMemoryRepository
from src.core.validation.validator import SafetyValidator


class TestEmbeddingServiceIntegration:
    """Test EmbeddingService integration without sentence-transformers dependency."""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer model."""
        with patch('src.core.embeddings.service.SENTENCE_TRANSFORMERS_AVAILABLE', True):
            with patch('src.core.embeddings.service.SentenceTransformer') as mock_st:
                # Create mock model instance
                mock_model = Mock()
                mock_model.encode.return_value = [[0.1, 0.2, 0.3]]  # Mock embedding
                mock_st.return_value = mock_model
                yield mock_model
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Mock SafetyValidator."""
        validator = Mock(spec=SafetyValidator)
        validator.auto_abstract_content.return_value = ("abstracted content", {})
        return validator
    
    @pytest.fixture
    def embedding_cache(self):
        """Create embedding cache for testing."""
        return EmbeddingCache(max_size=10, default_ttl_seconds=3600)
    
    @pytest.fixture
    def embedding_service(self, embedding_cache, mock_safety_validator, mock_sentence_transformer):
        """Create embedding service for testing."""
        with patch('src.core.embeddings.service.torch') as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            
            service = EmbeddingService(
                cache=embedding_cache,
                safety_validator=mock_safety_validator,
                device='cpu'
            )
            return service
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, embedding_service):
        """Test service initialization."""
        assert embedding_service.device == 'cpu'
        assert embedding_service.cache is not None
        assert embedding_service.safety_validator is not None
        assert len(embedding_service.model_configs) > 0
    
    @pytest.mark.asyncio
    async def test_single_embedding_generation(self, embedding_service, mock_sentence_transformer):
        """Test single embedding generation."""
        content = "This is test content for embedding"
        
        result = await embedding_service.generate_embedding(
            content=content,
            content_type=ContentType.TEXT
        )
        
        assert result.vector == [0.1, 0.2, 0.3]
        assert result.metadata.content_type == ContentType.TEXT
        assert result.metadata.safety_score >= Decimal("0.8")
        assert result.processing_time_ms >= 0
        assert result.cache_hit is False
        
        # Verify model was called
        mock_sentence_transformer.encode.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, embedding_service, mock_sentence_transformer):
        """Test embedding caching."""
        content = "Test content for caching"
        
        # First call should generate embedding
        result1 = await embedding_service.generate_embedding(content=content)
        assert result1.cache_hit is False
        
        # Second call should hit cache
        result2 = await embedding_service.generate_embedding(content=content)
        assert result2.cache_hit is True
        assert result2.vector == result1.vector
        
        # Model should only be called once
        assert mock_sentence_transformer.encode.call_count == 1
    
    @pytest.mark.asyncio
    async def test_content_type_detection(self, embedding_service):
        """Test automatic content type detection."""
        # Test code content
        code_content = "def hello_world(): print('Hello, World!')"
        code_result = await embedding_service.generate_embedding(
            content=code_content,
            content_type=ContentType.CODE
        )
        assert code_result.metadata.content_type == ContentType.CODE
        
        # Test documentation content
        doc_content = "This is a comprehensive guide to the API"
        doc_result = await embedding_service.generate_embedding(
            content=doc_content,
            content_type=ContentType.DOCUMENTATION
        )
        assert doc_result.metadata.content_type == ContentType.DOCUMENTATION
    
    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self, embedding_service, mock_sentence_transformer):
        """Test batch embedding generation."""
        # Configure mock to return multiple embeddings
        mock_sentence_transformer.encode.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        
        request = BatchEmbeddingRequest(
            texts=["text1", "text2", "text3"],
            content_type=ContentType.TEXT
        )
        
        batch_result = await embedding_service.generate_batch_embeddings(request)
        
        assert len(batch_result.results) == 3
        assert batch_result.generated_count == 3
        assert batch_result.cache_hits == 0
        assert batch_result.total_processing_time_ms >= 0
        
        # Check individual results
        for i, result in enumerate(batch_result.results):
            expected_vector = [0.1 + i*0.3, 0.2 + i*0.3, 0.3 + i*0.3]
            assert result.vector == expected_vector
            assert result.cache_hit is False
    
    @pytest.mark.asyncio
    async def test_batch_with_cache_hits(self, embedding_service, mock_sentence_transformer):
        """Test batch processing with some cache hits."""
        # Pre-populate cache with one embedding
        await embedding_service.generate_embedding("text1")
        
        # Configure mock for remaining embeddings
        mock_sentence_transformer.encode.return_value = [
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        
        request = BatchEmbeddingRequest(
            texts=["text1", "text2", "text3"],  # text1 should be cached
            content_type=ContentType.TEXT
        )
        
        batch_result = await embedding_service.generate_batch_embeddings(request)
        
        assert len(batch_result.results) == 3
        assert batch_result.cache_hits == 1
        assert batch_result.generated_count == 2
        assert batch_result.cache_hit_rate == 1/3
        
        # First result should be cache hit
        assert batch_result.results[0].cache_hit is True
    
    @pytest.mark.asyncio
    async def test_safety_validation(self, embedding_service, mock_safety_validator):
        """Test safety validation during embedding generation."""
        # Configure validator to return low safety score
        mock_safety_validator.auto_abstract_content.return_value = ("safe content", {})
        
        # Test with safety validation enabled
        result = await embedding_service.generate_embedding(
            content="test content",
            validate_safety=True
        )
        assert result.metadata.safety_score >= Decimal("0.8")
        
        # Test with safety validation disabled
        result_no_validation = await embedding_service.generate_embedding(
            content="test content",
            validate_safety=False
        )
        assert result_no_validation.metadata.safety_score == Decimal("1.0")
    
    @pytest.mark.asyncio
    async def test_similarity_calculation(self, embedding_service):
        """Test similarity calculation between embeddings."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]
        
        # Identical vectors
        similarity = await embedding_service.calculate_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-7
        
        # Orthogonal vectors
        similarity = await embedding_service.calculate_similarity(vec1, vec3)
        assert abs(similarity - 0.0) < 1e-7
    
    @pytest.mark.asyncio
    async def test_find_most_similar(self, embedding_service):
        """Test finding most similar embeddings."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            [1.0, 0.0, 0.0],  # Identical
            [0.9, 0.1, 0.0],  # Similar
            [0.0, 1.0, 0.0],  # Orthogonal
            [-1.0, 0.0, 0.0]  # Opposite
        ]
        
        results = await embedding_service.find_most_similar(
            query, candidates, top_k=2
        )
        
        assert len(results) == 2
        # First result should be identical vector (index 0)
        assert results[0][0] == 0
        assert abs(results[0][1] - 1.0) < 1e-7
        # Second result should be similar vector (index 1)
        assert results[1][0] == 1
    
    def test_get_stats(self, embedding_service):
        """Test statistics collection."""
        stats = embedding_service.get_stats()
        
        expected_keys = [
            'embeddings_generated', 'cache_hits', 'cache_misses',
            'safety_rejections', 'total_processing_time_ms', 'model_loads',
            'cache_hit_rate', 'average_processing_time_ms', 'loaded_models',
            'device', 'cache_enabled'
        ]
        
        for key in expected_keys:
            assert key in stats
        
        assert stats['device'] == 'cpu'
        assert stats['cache_enabled'] is True
    
    @pytest.mark.asyncio
    async def test_model_warmup(self, embedding_service, mock_sentence_transformer):
        """Test model warmup functionality."""
        await embedding_service.warm_up_models()
        
        # Models should be loaded for configured content types
        assert len(embedding_service._models) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, embedding_service):
        """Test error handling in embedding generation."""
        # Test empty content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await embedding_service.generate_embedding("")
        
        # Test dimension mismatch would be caught by model validation
    
    @pytest.mark.asyncio
    async def test_service_shutdown(self, embedding_service):
        """Test service shutdown cleanup."""
        # Add some data first
        await embedding_service.generate_embedding("test content")
        
        # Shutdown should clear resources
        await embedding_service.shutdown()
        
        assert len(embedding_service._models) == 0


class TestMemoryRepositoryIntegration:
    """Test integration with SafeMemoryRepository."""
    
    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool."""
        pool = Mock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock database operations
        conn.execute.return_value = None
        conn.fetchrow.return_value = None
        conn.fetch.return_value = []
        
        return pool
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock(spec=EmbeddingService)
        
        # Mock embedding generation
        async def generate_embedding(*args, **kwargs):
            from src.core.embeddings.models import EmbeddingResult, EmbeddingMetadata
            from decimal import Decimal
            
            metadata = EmbeddingMetadata(
                content_type=ContentType.TEXT,
                model_name="mock-model",
                content_hash="a" * 64,
                safety_score=Decimal("0.9"),
                dimensions=3
            )
            
            return EmbeddingResult(
                vector=[0.1, 0.2, 0.3],
                metadata=metadata,
                processing_time_ms=50
            )
        
        service.generate_embedding = generate_embedding
        return service
    
    @pytest.fixture
    def memory_repository(self, mock_db_pool, mock_embedding_service):
        """Create memory repository with mocked dependencies."""
        with patch('src.core.memory.repository.MemoryValidator'):
            with patch('src.core.memory.repository.MemoryClusterManager'):
                with patch('src.core.memory.repository.MemoryDecayEngine'):
                    repo = SafeMemoryRepository(
                        db_pool=mock_db_pool,
                        embedding_service=mock_embedding_service
                    )
                    return repo
    
    @pytest.mark.asyncio
    async def test_memory_creation_with_embeddings(self, memory_repository, mock_embedding_service):
        """Test memory creation with automatic embedding generation."""
        with patch.object(memory_repository.validator, 'auto_abstract_content') as mock_abstract:
            mock_abstract.return_value = ("abstracted prompt", {})
            
            with patch.object(memory_repository.validator, 'validate_memory_entry') as mock_validate:
                from src.core.memory.abstract_models import ValidationResult
                mock_validate.return_value = ValidationResult(is_valid=True, violations=[])
                
                with patch.object(memory_repository, '_store_memory') as mock_store:
                    memory = await memory_repository.create_memory(
                        prompt="Test prompt",
                        response="Test response",
                        generate_embeddings=True
                    )
                    
                    # Verify memory was created
                    assert memory is not None
                    
                    # Verify embeddings were generated
                    assert mock_embedding_service.generate_embedding.call_count == 2  # prompt + response
                    
                    # Verify storage was called with embeddings
                    mock_store.assert_called_once()
                    args = mock_store.call_args[0]
                    assert len(args) == 3  # memory, prompt_embedding, response_embedding
                    assert args[1] == [0.1, 0.2, 0.3]  # prompt_embedding
                    assert args[2] == [0.1, 0.2, 0.3]  # response_embedding
    
    @pytest.mark.asyncio
    async def test_memory_creation_without_embeddings(self, memory_repository, mock_embedding_service):
        """Test memory creation without embedding generation."""
        with patch.object(memory_repository.validator, 'auto_abstract_content') as mock_abstract:
            mock_abstract.return_value = ("abstracted prompt", {})
            
            with patch.object(memory_repository.validator, 'validate_memory_entry') as mock_validate:
                from src.core.memory.abstract_models import ValidationResult
                mock_validate.return_value = ValidationResult(is_valid=True, violations=[])
                
                with patch.object(memory_repository, '_store_memory') as mock_store:
                    memory = await memory_repository.create_memory(
                        prompt="Test prompt",
                        response="Test response",
                        generate_embeddings=False
                    )
                    
                    # Verify memory was created
                    assert memory is not None
                    
                    # Verify no embeddings were generated
                    mock_embedding_service.generate_embedding.assert_not_called()
                    
                    # Verify storage was called without embeddings
                    mock_store.assert_called_once()
                    args = mock_store.call_args[0]
                    assert len(args) == 3  # memory, None, None
                    assert args[1] is None  # prompt_embedding
                    assert args[2] is None  # response_embedding
    
    @pytest.mark.asyncio
    async def test_content_type_determination(self, memory_repository):
        """Test content type determination logic."""
        # Test code content
        code_type = memory_repository._determine_content_type(
            "def function():", 
            "return value",
            {}
        )
        assert code_type == ContentType.CODE
        
        # Test documentation content
        doc_type = memory_repository._determine_content_type(
            "This is documentation",
            "explaining the API guide",
            {}
        )
        assert doc_type == ContentType.DOCUMENTATION
        
        # Test explicit content type in metadata
        explicit_type = memory_repository._determine_content_type(
            "some content",
            "some response",
            {"content_type": "code"}
        )
        assert explicit_type == ContentType.CODE
        
        # Test default to text
        text_type = memory_repository._determine_content_type(
            "regular conversation",
            "normal response",
            {}
        )
        assert text_type == ContentType.TEXT
    
    @pytest.mark.asyncio
    async def test_embedding_error_handling(self, memory_repository, mock_embedding_service):
        """Test handling of embedding generation errors."""
        # Configure embedding service to raise an error
        async def failing_generate_embedding(*args, **kwargs):
            raise RuntimeError("Embedding generation failed")
        
        mock_embedding_service.generate_embedding = failing_generate_embedding
        
        with patch.object(memory_repository.validator, 'auto_abstract_content') as mock_abstract:
            mock_abstract.return_value = ("abstracted prompt", {})
            
            with patch.object(memory_repository.validator, 'validate_memory_entry') as mock_validate:
                from src.core.memory.abstract_models import ValidationResult
                mock_validate.return_value = ValidationResult(is_valid=True, violations=[])
                
                with patch.object(memory_repository, '_store_memory') as mock_store:
                    # Should not raise error, but continue without embeddings
                    memory = await memory_repository.create_memory(
                        prompt="Test prompt",
                        response="Test response",
                        generate_embeddings=True
                    )
                    
                    # Memory should still be created
                    assert memory is not None
                    
                    # Storage should be called with None embeddings
                    mock_store.assert_called_once()
                    args = mock_store.call_args[0]
                    assert args[1] is None  # prompt_embedding
                    assert args[2] is None  # response_embedding


class TestEndToEndIntegration:
    """Test complete end-to-end integration."""
    
    @pytest.mark.asyncio
    async def test_complete_embedding_pipeline(self):
        """Test complete embedding pipeline from content to cache."""
        # This would require a more complete integration test
        # with actual database and possibly mocked sentence-transformers
        pass
    
    @pytest.mark.asyncio 
    async def test_clustering_with_embeddings(self):
        """Test clustering integration with enhanced embeddings."""
        # Test would verify that cluster manager uses improved embeddings
        pass
    
    @pytest.mark.asyncio
    async def test_search_performance_improvement(self):
        """Test that search performance is improved with new embeddings."""
        # Test would measure search performance before/after
        pass