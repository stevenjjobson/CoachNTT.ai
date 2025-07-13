"""
Unit tests for intent models and data structures.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.core.intent.models import (
    IntentType,
    IntentResult,
    IntentMetadata,
    ConnectionType,
    Connection,
    ConnectionResult,
    QueryAnalysis,
    IntentPattern,
    ExplanationReason,
    FeedbackType,
    LearningFeedback,
    MIN_INTENT_CONFIDENCE,
    MIN_CONNECTION_STRENGTH,
    MIN_SAFETY_SCORE
)


class TestIntentType:
    """Test IntentType enum."""
    
    def test_intent_types_exist(self):
        """Test that all expected intent types exist."""
        expected_types = [
            'QUESTION', 'COMMAND', 'EXPLANATION', 'SEARCH', 'CREATE',
            'DEBUG', 'OPTIMIZE', 'REVIEW', 'LEARN', 'PLAN', 'REFLECT', 'UNKNOWN'
        ]
        
        for intent_type in expected_types:
            assert hasattr(IntentType, intent_type)
    
    def test_intent_type_values(self):
        """Test intent type string values."""
        assert IntentType.QUESTION.value == "question"
        assert IntentType.COMMAND.value == "command"
        assert IntentType.UNKNOWN.value == "unknown"


class TestIntentMetadata:
    """Test IntentMetadata data class."""
    
    def test_metadata_creation(self):
        """Test creating intent metadata."""
        metadata = IntentMetadata(
            confidence=0.85,
            safety_score=Decimal("0.9"),
            content_hash="test_hash_123",
            model_name="test_model",
            language="python",
            keywords=["test", "function"],
            processing_time_ms=150
        )
        
        assert metadata.confidence == 0.85
        assert metadata.safety_score == Decimal("0.9")
        assert metadata.content_hash == "test_hash_123"
        assert metadata.model_name == "test_model"
        assert metadata.language == "python"
        assert metadata.keywords == ["test", "function"]
        assert metadata.processing_time_ms == 150
    
    def test_metadata_defaults(self):
        """Test metadata with default values."""
        metadata = IntentMetadata(
            confidence=0.7,
            safety_score=Decimal("0.8"),
            content_hash="hash"
        )
        
        assert metadata.model_name is None
        assert metadata.language is None
        assert metadata.keywords == []
        assert metadata.entities == []
        assert metadata.processing_time_ms == 0


class TestIntentResult:
    """Test IntentResult data class."""
    
    def test_intent_result_creation(self):
        """Test creating intent result."""
        metadata = IntentMetadata(
            confidence=0.9,
            safety_score=Decimal("0.95"),
            content_hash="test_hash"
        )
        
        result = IntentResult(
            intent_type=IntentType.QUESTION,
            metadata=metadata,
            reasoning="Pattern analysis suggests question intent",
            alternative_intents=[IntentType.EXPLANATION, IntentType.LEARN]
        )
        
        assert result.intent_type == IntentType.QUESTION
        assert result.metadata.confidence == 0.9
        assert result.reasoning == "Pattern analysis suggests question intent"
        assert len(result.alternative_intents) == 2
        assert IntentType.EXPLANATION in result.alternative_intents
    
    def test_is_confident(self):
        """Test confidence checking."""
        metadata = IntentMetadata(
            confidence=0.8,
            safety_score=Decimal("0.9"),
            content_hash="hash"
        )
        
        result = IntentResult(
            intent_type=IntentType.COMMAND,
            metadata=metadata,
            reasoning="High confidence command"
        )
        
        assert result.is_confident(0.7) is True
        assert result.is_confident(0.85) is False
        assert result.is_confident() is True  # Default threshold 0.7
    
    def test_is_safe(self):
        """Test safety checking."""
        metadata = IntentMetadata(
            confidence=0.8,
            safety_score=Decimal("0.85"),
            content_hash="hash"
        )
        
        result = IntentResult(
            intent_type=IntentType.DEBUG,
            metadata=metadata,
            reasoning="Safe debug intent"
        )
        
        assert result.is_safe(Decimal("0.8")) is True
        assert result.is_safe(Decimal("0.9")) is False
        assert result.is_safe() is True  # Default threshold 0.8


class TestConnection:
    """Test Connection data class."""
    
    def test_connection_creation(self):
        """Test creating connection."""
        source_id = uuid4()
        target_id = uuid4()
        
        connection = Connection(
            source_id=source_id,
            target_id=target_id,
            connection_type=ConnectionType.SEMANTIC,
            strength=0.8,
            reasoning=ExplanationReason.SEMANTIC_SIMILARITY,
            explanation="Similar content and concepts",
            metadata={"similarity_score": 0.85}
        )
        
        assert connection.source_id == source_id
        assert connection.target_id == target_id
        assert connection.connection_type == ConnectionType.SEMANTIC
        assert connection.strength == 0.8
        assert connection.reasoning == ExplanationReason.SEMANTIC_SIMILARITY
        assert connection.explanation == "Similar content and concepts"
        assert connection.metadata["similarity_score"] == 0.85
    
    def test_is_strong(self):
        """Test connection strength checking."""
        connection = Connection(
            source_id=uuid4(),
            target_id=uuid4(),
            connection_type=ConnectionType.TEMPORAL,
            strength=0.7,
            reasoning=ExplanationReason.TEMPORAL_PROXIMITY,
            explanation="Recent related activity"
        )
        
        assert connection.is_strong(0.6) is True
        assert connection.is_strong(0.8) is False
        assert connection.is_strong() is True  # Default threshold 0.6


class TestConnectionResult:
    """Test ConnectionResult data class."""
    
    def test_connection_result_creation(self):
        """Test creating connection result."""
        query_id = uuid4()
        
        connections = [
            Connection(
                source_id=uuid4(),
                target_id=uuid4(),
                connection_type=ConnectionType.SEMANTIC,
                strength=0.9,
                reasoning=ExplanationReason.SEMANTIC_SIMILARITY,
                explanation="Very similar content"
            ),
            Connection(
                source_id=uuid4(),
                target_id=uuid4(),
                connection_type=ConnectionType.TEMPORAL,
                strength=0.5,
                reasoning=ExplanationReason.TEMPORAL_PROXIMITY,
                explanation="Recent activity"
            )
        ]
        
        result = ConnectionResult(
            query_id=query_id,
            connections=connections,
            total_candidates=10,
            processing_time_ms=250,
            explanation="Found 2 relevant connections",
            confidence=0.75
        )
        
        assert result.query_id == query_id
        assert len(result.connections) == 2
        assert result.total_candidates == 10
        assert result.processing_time_ms == 250
        assert result.confidence == 0.75
    
    def test_get_strong_connections(self):
        """Test filtering strong connections."""
        connections = [
            Connection(
                source_id=uuid4(), target_id=uuid4(),
                connection_type=ConnectionType.SEMANTIC, strength=0.9,
                reasoning=ExplanationReason.SEMANTIC_SIMILARITY, explanation="Strong"
            ),
            Connection(
                source_id=uuid4(), target_id=uuid4(),
                connection_type=ConnectionType.TEMPORAL, strength=0.4,
                reasoning=ExplanationReason.TEMPORAL_PROXIMITY, explanation="Weak"
            ),
            Connection(
                source_id=uuid4(), target_id=uuid4(),
                connection_type=ConnectionType.PATTERN, strength=0.7,
                reasoning=ExplanationReason.PATTERN_MATCH, explanation="Medium"
            )
        ]
        
        result = ConnectionResult(
            query_id=uuid4(),
            connections=connections,
            total_candidates=5,
            processing_time_ms=100,
            explanation="Test",
            confidence=0.8
        )
        
        strong_connections = result.get_strong_connections(0.6)
        assert len(strong_connections) == 2
        assert all(conn.strength >= 0.6 for conn in strong_connections)
    
    def test_get_by_type(self):
        """Test filtering connections by type."""
        connections = [
            Connection(
                source_id=uuid4(), target_id=uuid4(),
                connection_type=ConnectionType.SEMANTIC, strength=0.8,
                reasoning=ExplanationReason.SEMANTIC_SIMILARITY, explanation="Semantic"
            ),
            Connection(
                source_id=uuid4(), target_id=uuid4(),
                connection_type=ConnectionType.TEMPORAL, strength=0.6,
                reasoning=ExplanationReason.TEMPORAL_PROXIMITY, explanation="Temporal"
            ),
            Connection(
                source_id=uuid4(), target_id=uuid4(),
                connection_type=ConnectionType.SEMANTIC, strength=0.7,
                reasoning=ExplanationReason.SEMANTIC_SIMILARITY, explanation="Another semantic"
            )
        ]
        
        result = ConnectionResult(
            query_id=uuid4(),
            connections=connections,
            total_candidates=5,
            processing_time_ms=100,
            explanation="Test",
            confidence=0.8
        )
        
        semantic_connections = result.get_by_type(ConnectionType.SEMANTIC)
        assert len(semantic_connections) == 2
        assert all(conn.connection_type == ConnectionType.SEMANTIC for conn in semantic_connections)
        
        temporal_connections = result.get_by_type(ConnectionType.TEMPORAL)
        assert len(temporal_connections) == 1


class TestQueryAnalysis:
    """Test QueryAnalysis data class."""
    
    def test_query_analysis_creation(self):
        """Test creating query analysis."""
        analysis = QueryAnalysis(
            original_query="How to optimize database queries?",
            abstracted_query="How to optimize <database_system> queries?",
            safety_score=Decimal("0.9")
        )
        
        assert analysis.original_query == "How to optimize database queries?"
        assert analysis.abstracted_query == "How to optimize <database_system> queries?"
        assert analysis.safety_score == Decimal("0.9")
        assert analysis.intent_result is None
        assert analysis.connection_result is None
    
    def test_is_complete(self):
        """Test completion checking."""
        analysis = QueryAnalysis()
        assert analysis.is_complete() is False
        
        # Add intent result
        intent_metadata = IntentMetadata(
            confidence=0.8,
            safety_score=Decimal("0.9"),
            content_hash="hash"
        )
        analysis.intent_result = IntentResult(
            intent_type=IntentType.QUESTION,
            metadata=intent_metadata,
            reasoning="Question detected"
        )
        assert analysis.is_complete() is False
        
        # Add connection result
        analysis.connection_result = ConnectionResult(
            query_id=uuid4(),
            connections=[],
            total_candidates=0,
            processing_time_ms=100,
            explanation="No connections",
            confidence=0.0
        )
        assert analysis.is_complete() is True
    
    def test_is_safe_for_processing(self):
        """Test safety checking for processing."""
        analysis = QueryAnalysis(safety_score=Decimal("0.85"))
        assert analysis.is_safe_for_processing(Decimal("0.8")) is True
        assert analysis.is_safe_for_processing(Decimal("0.9")) is False


class TestIntentPattern:
    """Test IntentPattern data class."""
    
    def test_pattern_creation(self):
        """Test creating intent pattern."""
        pattern = IntentPattern(
            name="Debug-Optimize Sequence",
            description="Common pattern of debugging followed by optimization",
            intent_sequence=[IntentType.DEBUG, IntentType.OPTIMIZE],
            frequency=5,
            confidence=0.8,
            examples=["Debug slow query", "Optimize database performance"],
            safety_validated=True
        )
        
        assert pattern.name == "Debug-Optimize Sequence"
        assert len(pattern.intent_sequence) == 2
        assert pattern.frequency == 5
        assert pattern.confidence == 0.8
        assert pattern.safety_validated is True
    
    def test_is_reliable(self):
        """Test reliability checking."""
        pattern = IntentPattern(
            name="Test Pattern",
            frequency=5,
            confidence=0.8,
            safety_validated=True
        )
        
        assert pattern.is_reliable(min_frequency=3, min_confidence=0.7) is True
        assert pattern.is_reliable(min_frequency=6, min_confidence=0.7) is False
        assert pattern.is_reliable(min_frequency=3, min_confidence=0.9) is False
        
        # Safety validation required
        pattern.safety_validated = False
        assert pattern.is_reliable(min_frequency=3, min_confidence=0.7) is False


class TestLearningFeedback:
    """Test LearningFeedback data class."""
    
    def test_feedback_creation(self):
        """Test creating learning feedback."""
        query_id = uuid4()
        
        feedback = LearningFeedback(
            query_id=query_id,
            feedback_type=FeedbackType.HELPFUL,
            intent_correct=True,
            suggested_intent=IntentType.QUESTION,
            connection_helpful=True,
            comments="Very helpful suggestions",
            rating=4
        )
        
        assert feedback.query_id == query_id
        assert feedback.feedback_type == FeedbackType.HELPFUL
        assert feedback.intent_correct is True
        assert feedback.suggested_intent == IntentType.QUESTION
        assert feedback.connection_helpful is True
        assert feedback.comments == "Very helpful suggestions"
        assert feedback.rating == 4
    
    def test_is_positive(self):
        """Test positive feedback detection."""
        helpful_feedback = LearningFeedback(
            feedback_type=FeedbackType.HELPFUL
        )
        assert helpful_feedback.is_positive() is True
        
        excellent_feedback = LearningFeedback(
            feedback_type=FeedbackType.EXCELLENT
        )
        assert excellent_feedback.is_positive() is True
        
        negative_feedback = LearningFeedback(
            feedback_type=FeedbackType.NOT_HELPFUL
        )
        assert negative_feedback.is_positive() is False


class TestConstants:
    """Test module constants."""
    
    def test_constants_exist(self):
        """Test that required constants exist."""
        assert MIN_INTENT_CONFIDENCE == 0.5
        assert MIN_CONNECTION_STRENGTH == 0.3
        assert MIN_SAFETY_SCORE == Decimal("0.8")
    
    def test_constant_types(self):
        """Test constant types are correct."""
        assert isinstance(MIN_INTENT_CONFIDENCE, float)
        assert isinstance(MIN_CONNECTION_STRENGTH, float)
        assert isinstance(MIN_SAFETY_SCORE, Decimal)