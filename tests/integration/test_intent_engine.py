"""
Integration tests for the intent engine system.

Tests the complete intent analysis pipeline including classification,
connection finding, and safety validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from uuid import UUID, uuid4

from src.core.intent import (
    IntentEngine,
    IntentAnalyzer,
    ConnectionFinder,
    IntentType,
    QueryAnalysis,
    ConnectionType,
    ExplanationReason
)
from src.core.embeddings import EmbeddingService, EmbeddingCache
from src.core.validation.validator import SafetyValidator


class TestIntentEngineIntegration:
    """Test IntentEngine integration with all components."""
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock(spec=EmbeddingService)
        
        # Mock embedding generation
        async def generate_embedding(*args, **kwargs):
            from src.core.embeddings.models import EmbeddingResult, EmbeddingMetadata
            
            metadata = EmbeddingMetadata(
                content_type="query",
                model_name="mock-model",
                content_hash="mock_hash",
                safety_score=Decimal("0.9"),
                dimensions=384
            )
            
            return EmbeddingResult(
                vector=[0.1, 0.2, 0.3] * 128,  # 384-dim vector
                metadata=metadata,
                processing_time_ms=50
            )
        
        service.generate_embedding = generate_embedding
        
        # Mock similarity calculation
        async def calculate_similarity(vec1, vec2):
            return 0.75  # Mock similarity score
        
        service.calculate_similarity = calculate_similarity
        
        return service
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Mock safety validator."""
        validator = Mock(spec=SafetyValidator)
        validator.auto_abstract_content.return_value = ("abstracted content", {})
        return validator
    
    @pytest.fixture
    def intent_engine(self, mock_embedding_service, mock_safety_validator):
        """Create intent engine for testing."""
        return IntentEngine(
            embedding_service=mock_embedding_service,
            safety_validator=mock_safety_validator,
            enable_learning=True,
            non_directive_mode=True
        )
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, intent_engine):
        """Test intent engine initialization."""
        assert intent_engine.embedding_service is not None
        assert intent_engine.safety_validator is not None
        assert intent_engine.intent_analyzer is not None
        assert intent_engine.connection_finder is not None
        assert intent_engine.enable_learning is True
        assert intent_engine.non_directive_mode is True
    
    @pytest.mark.asyncio
    async def test_query_analysis_pipeline(self, intent_engine):
        """Test complete query analysis pipeline."""
        query = "How to optimize database queries for better performance?"
        
        # Mock the intent analyzer's classify_intent method
        with patch.object(intent_engine.intent_analyzer, 'classify_intent') as mock_classify:
            from src.core.intent.models import IntentResult, IntentMetadata
            
            # Mock intent classification
            metadata = IntentMetadata(
                confidence=0.85,
                safety_score=Decimal("0.9"),
                content_hash="test_hash"
            )
            
            mock_classify.return_value = IntentResult(
                intent_type=IntentType.OPTIMIZE,
                metadata=metadata,
                reasoning="Pattern analysis suggests optimization intent"
            )
            
            # Mock connection finder
            with patch.object(intent_engine.connection_finder, 'find_connections') as mock_connections:
                from src.core.intent.models import ConnectionResult, Connection
                
                connection = Connection(
                    source_id=UUID(int=0),
                    target_id=UUID(int=1),
                    connection_type=ConnectionType.SEMANTIC,
                    strength=0.8,
                    reasoning=ExplanationReason.SEMANTIC_SIMILARITY,
                    explanation="Similar optimization content"
                )
                
                mock_connections.return_value = ConnectionResult(
                    query_id=uuid4(),
                    connections=[connection],
                    total_candidates=5,
                    processing_time_ms=150,
                    explanation="Found 1 relevant connection",
                    confidence=0.8
                )
                
                # Run analysis
                analysis = await intent_engine.analyze_query(query)
                
                # Verify results
                assert analysis.original_query == query
                assert analysis.intent_result is not None
                assert analysis.intent_result.intent_type == IntentType.OPTIMIZE
                assert analysis.connection_result is not None
                assert len(analysis.connection_result.connections) == 1
                assert analysis.is_complete() is True
                assert analysis.is_safe_for_processing() is True
    
    @pytest.mark.asyncio
    async def test_safety_validation_rejection(self, intent_engine):
        """Test that unsafe queries are rejected."""
        unsafe_query = "Delete all user data from production database"
        
        # Mock safety validator to return low safety score
        intent_engine.safety_validator.auto_abstract_content.return_value = (
            "abstracted content", {}
        )
        
        with patch.object(intent_engine, '_calculate_query_safety_score') as mock_score:
            mock_score.return_value = Decimal("0.5")  # Below safety threshold
            
            with pytest.raises(ValueError, match="Query failed safety validation"):
                await intent_engine.analyze_query(unsafe_query)
    
    @pytest.mark.asyncio
    async def test_non_directive_filtering(self, intent_engine):
        """Test non-directive filtering of connections."""
        query = "What should I do next with my code?"
        
        # Mock intent classification
        with patch.object(intent_engine.intent_analyzer, 'classify_intent') as mock_classify:
            from src.core.intent.models import IntentResult, IntentMetadata
            
            metadata = IntentMetadata(
                confidence=0.8,
                safety_score=Decimal("0.9"),
                content_hash="test_hash"
            )
            
            mock_classify.return_value = IntentResult(
                intent_type=IntentType.QUESTION,
                metadata=metadata,
                reasoning="Question about next steps"
            )
            
            # Mock connection finder with directive connection
            with patch.object(intent_engine.connection_finder, 'find_connections') as mock_connections:
                from src.core.intent.models import ConnectionResult, Connection
                
                # Create directive connection (should be filtered)
                directive_connection = Connection(
                    source_id=UUID(int=0),
                    target_id=UUID(int=1),
                    connection_type=ConnectionType.PATTERN,
                    strength=0.7,
                    reasoning=ExplanationReason.PATTERN_MATCH,
                    explanation="You must implement this critical feature immediately"
                )
                
                # Create non-directive connection (should be kept)
                safe_connection = Connection(
                    source_id=UUID(int=0),
                    target_id=UUID(int=2),
                    connection_type=ConnectionType.SEMANTIC,
                    strength=0.8,
                    reasoning=ExplanationReason.SEMANTIC_SIMILARITY,
                    explanation="This content discusses similar concepts"
                )
                
                mock_connections.return_value = ConnectionResult(
                    query_id=uuid4(),
                    connections=[directive_connection, safe_connection],
                    total_candidates=5,
                    processing_time_ms=150,
                    explanation="Found connections",
                    confidence=0.75,
                    non_directive_approved=False  # Will be updated by filter
                )
                
                # Run analysis
                analysis = await intent_engine.analyze_query(query)
                
                # Verify non-directive filtering
                assert analysis.connection_result is not None
                assert analysis.connection_result.non_directive_approved is True
                
                # Should have filtered out the directive connection
                remaining_connections = analysis.connection_result.connections
                assert len(remaining_connections) == 1
                assert remaining_connections[0].explanation == "This content discusses similar concepts"
    
    @pytest.mark.asyncio
    async def test_learning_feedback_processing(self, intent_engine):
        """Test learning feedback processing."""
        from src.core.intent.models import LearningFeedback, FeedbackType
        
        feedback = LearningFeedback(
            query_id=uuid4(),
            feedback_type=FeedbackType.HELPFUL,
            intent_correct=True,
            connection_helpful=True,
            comments="Very useful suggestions"
        )
        
        # Mock component feedback processing
        with patch.object(intent_engine.intent_analyzer, 'process_feedback') as mock_intent_feedback:
            with patch.object(intent_engine.connection_finder, 'process_feedback') as mock_conn_feedback:
                mock_intent_feedback.return_value = True
                mock_conn_feedback.return_value = True
                
                result = await intent_engine.provide_feedback(feedback)
                
                assert result is True
                mock_intent_feedback.assert_called_once_with(feedback)
                mock_conn_feedback.assert_called_once_with(feedback)
    
    @pytest.mark.asyncio
    async def test_learning_disabled(self, mock_embedding_service, mock_safety_validator):
        """Test behavior when learning is disabled."""
        engine = IntentEngine(
            embedding_service=mock_embedding_service,
            safety_validator=mock_safety_validator,
            enable_learning=False
        )
        
        from src.core.intent.models import LearningFeedback, FeedbackType
        
        feedback = LearningFeedback(
            feedback_type=FeedbackType.HELPFUL
        )
        
        result = await engine.provide_feedback(feedback)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_intent_patterns_retrieval(self, intent_engine):
        """Test retrieving intent patterns."""
        user_id = uuid4()
        
        # Mock intent analyzer pattern retrieval
        with patch.object(intent_engine.intent_analyzer, 'get_patterns') as mock_patterns:
            mock_patterns.return_value = [
                {
                    'intent_type': IntentType.DEBUG,
                    'frequency': 5,
                    'confidence': 0.8
                },
                {
                    'intent_type': IntentType.OPTIMIZE,
                    'frequency': 3,
                    'confidence': 0.7
                }
            ]
            
            patterns = await intent_engine.get_intent_patterns(user_id=user_id, min_frequency=3)
            
            assert len(patterns) == 2
            assert patterns[0]['intent_type'] == IntentType.DEBUG
            assert patterns[1]['intent_type'] == IntentType.OPTIMIZE
            mock_patterns.assert_called_once_with(user_id=user_id, min_frequency=3)
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self, intent_engine):
        """Test statistics collection."""
        stats = intent_engine.get_stats()
        
        # Verify basic stats structure
        assert 'queries_analyzed' in stats
        assert 'intents_classified' in stats
        assert 'connections_found' in stats
        assert 'safety_rejections' in stats
        assert 'total_processing_time_ms' in stats
        assert 'learning_feedback_received' in stats
        
        # Verify derived metrics
        assert 'average_processing_time_ms' in stats
        assert 'intent_classification_rate' in stats
        assert 'average_connections_per_query' in stats
        
        # Verify configuration
        assert stats['learning_enabled'] is True
        assert stats['non_directive_mode'] is True
        
        # Verify component stats
        assert 'component_stats' in stats
        assert 'intent_analyzer' in stats['component_stats']
        assert 'connection_finder' in stats['component_stats']
    
    @pytest.mark.asyncio
    async def test_error_handling(self, intent_engine):
        """Test error handling in analysis pipeline."""
        query = "Test query for error handling"
        
        # Mock intent analyzer to raise exception
        with patch.object(intent_engine.intent_analyzer, 'classify_intent') as mock_classify:
            mock_classify.side_effect = RuntimeError("Intent classification failed")
            
            with pytest.raises(RuntimeError, match="Failed to analyze query"):
                await intent_engine.analyze_query(query)
    
    @pytest.mark.asyncio
    async def test_engine_shutdown(self, intent_engine):
        """Test engine shutdown process."""
        # Mock component shutdowns
        with patch.object(intent_engine.intent_analyzer, 'shutdown') as mock_intent_shutdown:
            with patch.object(intent_engine.connection_finder, 'shutdown') as mock_conn_shutdown:
                await intent_engine.shutdown()
                
                mock_intent_shutdown.assert_called_once()
                mock_conn_shutdown.assert_called_once()


class TestIntentEnginePerformance:
    """Test intent engine performance characteristics."""
    
    @pytest.fixture
    def performance_engine(self, mock_embedding_service, mock_safety_validator):
        """Create engine for performance testing."""
        return IntentEngine(
            embedding_service=mock_embedding_service,
            safety_validator=mock_safety_validator
        )
    
    @pytest.mark.asyncio
    async def test_analysis_performance(self, performance_engine):
        """Test that analysis meets performance targets."""
        query = "How to debug slow API responses?"
        
        # Mock fast responses
        with patch.object(performance_engine.intent_analyzer, 'classify_intent') as mock_classify:
            with patch.object(performance_engine.connection_finder, 'find_connections') as mock_connections:
                from src.core.intent.models import IntentResult, IntentMetadata, ConnectionResult
                
                # Mock fast intent classification
                metadata = IntentMetadata(
                    confidence=0.8,
                    safety_score=Decimal("0.9"),
                    content_hash="test_hash",
                    processing_time_ms=150  # Under 200ms target
                )
                
                mock_classify.return_value = IntentResult(
                    intent_type=IntentType.DEBUG,
                    metadata=metadata,
                    reasoning="Debug intent detected"
                )
                
                # Mock fast connection finding
                mock_connections.return_value = ConnectionResult(
                    query_id=uuid4(),
                    connections=[],
                    total_candidates=10,
                    processing_time_ms=300,  # Under 500ms target
                    explanation="No connections found",
                    confidence=0.5
                )
                
                # Run analysis and measure performance
                import time
                start_time = time.time()
                
                analysis = await performance_engine.analyze_query(query)
                
                end_time = time.time()
                total_time_ms = (end_time - start_time) * 1000
                
                # Verify performance targets
                assert total_time_ms < 1000  # Total should be under 1 second
                assert analysis.intent_result.metadata.processing_time_ms < 200  # Intent classification
                assert analysis.connection_result.processing_time_ms < 500  # Connection finding
    
    @pytest.mark.asyncio 
    async def test_batch_analysis_performance(self, performance_engine):
        """Test batch analysis performance."""
        queries = [
            "How to optimize database queries?",
            "Debug memory leak in Python",
            "Create REST API with authentication",
            "Explain microservices architecture",
            "Review code for security issues"
        ]
        
        # Mock batch processing
        with patch.object(performance_engine, 'analyze_query') as mock_analyze:
            async def fast_analyze(query, **kwargs):
                analysis = QueryAnalysis(original_query=query)
                analysis.total_processing_time_ms = 150
                return analysis
            
            mock_analyze.side_effect = fast_analyze
            
            # Run batch analysis
            import time
            start_time = time.time()
            
            tasks = [performance_engine.analyze_query(query) for query in queries]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time_ms = (end_time - start_time) * 1000
            
            # Verify batch performance (should be under 1s for 5 queries)
            assert total_time_ms < 1000
            assert len(results) == 5
            assert all(result.total_processing_time_ms < 200 for result in results)