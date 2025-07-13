"""
Data models for intent analysis and connection finding.

Defines the structure for intent classification, connection discovery,
and explanation generation with safety validation built-in.
"""

from enum import Enum
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4


class IntentType(Enum):
    """Types of user intents in coding interactions."""
    
    QUESTION = "question"           # Asking for information or clarification
    COMMAND = "command"             # Requesting an action to be performed
    EXPLANATION = "explanation"     # Seeking understanding of concepts
    SEARCH = "search"               # Looking for existing information
    CREATE = "create"               # Requesting creation of new content
    DEBUG = "debug"                 # Troubleshooting or problem-solving
    OPTIMIZE = "optimize"           # Improving existing code/processes
    REVIEW = "review"               # Code/design review requests
    LEARN = "learn"                 # Educational or learning-focused
    PLAN = "plan"                   # Strategic or planning discussions
    REFLECT = "reflect"             # Retrospective or reflective analysis
    UNKNOWN = "unknown"             # Unable to classify


class ConnectionType(Enum):
    """Types of connections between memories and intents."""
    
    SEMANTIC = "semantic"           # Semantically similar content
    TEMPORAL = "temporal"           # Time-based relationships
    CAUSAL = "causal"               # Cause-and-effect relationships
    PATTERN = "pattern"             # Similar usage patterns
    CONTEXTUAL = "contextual"       # Same context or domain
    SEQUENTIAL = "sequential"       # Part of a sequence or workflow
    TOPIC = "topic"                 # Same topic or subject area
    SOLUTION = "solution"           # Problem-solution relationships


class ExplanationReason(Enum):
    """Reasons for suggesting connections."""
    
    SIMILAR_INTENT = "similar_intent"               # Similar user intent
    RELATED_TOPIC = "related_topic"                 # Related subject matter
    PREVIOUS_SOLUTION = "previous_solution"         # Previous solution to similar problem
    PATTERN_MATCH = "pattern_match"                 # Similar pattern detected
    TEMPORAL_PROXIMITY = "temporal_proximity"       # Recent related activity
    SEMANTIC_SIMILARITY = "semantic_similarity"     # Content similarity
    WORKFLOW_CONTINUATION = "workflow_continuation" # Part of ongoing workflow
    KNOWLEDGE_GAP = "knowledge_gap"                 # Addresses knowledge gap


class FeedbackType(Enum):
    """Types of user feedback for learning."""
    
    HELPFUL = "helpful"             # Connection was useful
    NOT_HELPFUL = "not_helpful"     # Connection was not useful
    IRRELEVANT = "irrelevant"       # Connection was off-topic
    WRONG = "wrong"                 # Connection was incorrect
    EXCELLENT = "excellent"         # Connection was very helpful
    CONFUSING = "confusing"         # Connection was confusing


@dataclass
class IntentMetadata:
    """Metadata for intent analysis."""
    
    confidence: float                          # Confidence score (0.0-1.0)
    safety_score: Decimal                      # Safety validation score
    content_hash: str                          # Hash of analyzed content
    model_name: Optional[str] = None           # Model used for analysis
    language: Optional[str] = None             # Content language
    domain: Optional[str] = None               # Domain/context
    complexity: Optional[str] = None           # Complexity level
    keywords: List[str] = field(default_factory=list)  # Extracted keywords
    entities: List[str] = field(default_factory=list)  # Named entities
    processing_time_ms: int = 0                # Processing time


@dataclass
class IntentResult:
    """Result of intent analysis."""
    
    intent_type: IntentType
    metadata: IntentMetadata
    reasoning: str                             # Explanation of classification
    alternative_intents: List[IntentType] = field(default_factory=list)
    embedding: Optional[List[float]] = None    # Intent-specific embedding
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """Check if intent classification is confident."""
        return self.metadata.confidence >= threshold
    
    def is_safe(self, threshold: Decimal = Decimal("0.8")) -> bool:
        """Check if intent analysis is safe."""
        return self.metadata.safety_score >= threshold


@dataclass
class Connection:
    """A connection between memories or concepts."""
    
    source_id: UUID                            # Source memory/item ID
    target_id: UUID                            # Target memory/item ID
    connection_type: ConnectionType
    strength: float                            # Connection strength (0.0-1.0)
    reasoning: ExplanationReason
    explanation: str                           # Human-readable explanation
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_strong(self, threshold: float = 0.6) -> bool:
        """Check if connection is strong."""
        return self.strength >= threshold


@dataclass
class ConnectionResult:
    """Result of connection finding analysis."""
    
    query_id: UUID                             # Query/analysis ID
    connections: List[Connection]
    total_candidates: int                      # Total items analyzed
    processing_time_ms: int
    explanation: str                           # Overall explanation
    confidence: float                          # Overall confidence
    non_directive_approved: bool = True        # Non-directive compliance
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_strong_connections(self, threshold: float = 0.6) -> List[Connection]:
        """Get connections above strength threshold."""
        return [conn for conn in self.connections if conn.is_strong(threshold)]
    
    def get_by_type(self, connection_type: ConnectionType) -> List[Connection]:
        """Get connections of specific type."""
        return [conn for conn in self.connections if conn.connection_type == connection_type]


@dataclass
class QueryAnalysis:
    """Comprehensive analysis of a user query."""
    
    query_id: UUID = field(default_factory=uuid4)
    original_query: str = ""
    abstracted_query: str = ""                 # Safety-abstracted version
    intent_result: Optional[IntentResult] = None
    connection_result: Optional[ConnectionResult] = None
    safety_score: Decimal = Decimal("0.0")
    total_processing_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_complete(self) -> bool:
        """Check if analysis is complete."""
        return (self.intent_result is not None and 
                self.connection_result is not None)
    
    def is_safe_for_processing(self, threshold: Decimal = Decimal("0.8")) -> bool:
        """Check if query is safe for processing."""
        return self.safety_score >= threshold


@dataclass
class IntentPattern:
    """Detected pattern in user intents."""
    
    pattern_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    intent_sequence: List[IntentType] = field(default_factory=list)
    frequency: int = 0                         # How often pattern occurs
    confidence: float = 0.0                    # Pattern confidence
    examples: List[str] = field(default_factory=list)  # Example queries
    triggers: List[str] = field(default_factory=list)  # Common triggers
    outcomes: List[str] = field(default_factory=list)  # Common outcomes
    safety_validated: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_reliable(self, min_frequency: int = 3, min_confidence: float = 0.7) -> bool:
        """Check if pattern is reliable for predictions."""
        return (self.frequency >= min_frequency and 
                self.confidence >= min_confidence and 
                self.safety_validated)


@dataclass
class LearningFeedback:
    """User feedback for improving intent analysis."""
    
    feedback_id: UUID = field(default_factory=uuid4)
    query_id: UUID = field(default_factory=uuid4)
    feedback_type: FeedbackType = FeedbackType.HELPFUL
    intent_correct: Optional[bool] = None      # Was intent classification correct?
    suggested_intent: Optional[IntentType] = None  # User's suggested intent
    connection_helpful: Optional[bool] = None  # Were connections helpful?
    comments: str = ""                         # Free-form feedback
    rating: Optional[int] = None               # 1-5 rating
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_positive(self) -> bool:
        """Check if feedback is positive."""
        return self.feedback_type in [FeedbackType.HELPFUL, FeedbackType.EXCELLENT]


# Type aliases for convenience
IntentConfidence = float
ConnectionStrength = float
SafetyScore = Decimal

# Constants
MIN_INTENT_CONFIDENCE = 0.5
MIN_CONNECTION_STRENGTH = 0.3
MIN_SAFETY_SCORE = Decimal("0.8")
MAX_CONNECTIONS_PER_QUERY = 10
DEFAULT_PROCESSING_TIMEOUT_MS = 5000