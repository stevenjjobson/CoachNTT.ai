"""
Core cognitive memory system components.

Provides safety-first memory management, intent analysis, and connection finding
with mandatory abstraction enforcement.
"""

# Safety and validation
from .validation.validator import SafetyValidator
from .validation.memory_validator import MemoryValidator, MemoryValidationPipeline
from .validation.quality_scorer import AbstractionQualityScorer

# Abstraction system  
from .abstraction.engine import AbstractionEngine
from .abstraction.concrete_engine import ConcreteAbstractionEngine
from .abstraction.extractor import ReferenceExtractor
from .abstraction.generator import PatternGenerator
from .abstraction.rules import AbstractionRules

# Memory management
from .memory.abstract_models import (
    AbstractMemoryEntry,
    SafeInteraction,
    ValidationStatus,
    InteractionType,
    MemoryMetadata,
    Reference,
    ReferenceType,
    AbstractionMapping,
    ValidationResult
)
from .memory.repository import SafeMemoryRepository
from .memory.validator import MemoryValidator
from .memory.cluster_manager import MemoryClusterManager, ClusterType
from .memory.decay_engine import MemoryDecayEngine

# Embeddings system
from .embeddings import (
    EmbeddingService,
    EmbeddingCache,
    EmbeddingResult,
    EmbeddingMetadata,
    ContentType,
    ModelConfig,
    BatchEmbeddingRequest,
    BatchEmbeddingResult
)

# Intent analysis and connection finding
from .intent import (
    IntentEngine,
    IntentAnalyzer,
    ConnectionFinder,
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
    LearningFeedback
)

# Safety models
from .safety.models import (
    SafetyScore,
    ValidationError,
    AbstractionQuality,
    ReferencePattern
)

# Metrics
from .metrics.safety_metrics import SafetyMetricsCollector

__all__ = [
    # Safety and validation
    'SafetyValidator',
    'MemoryValidator', 
    'MemoryValidationPipeline',
    'AbstractionQualityScorer',
    
    # Abstraction system
    'AbstractionEngine',
    'ConcreteAbstractionEngine', 
    'ReferenceExtractor',
    'PatternGenerator',
    'AbstractionRules',
    
    # Memory management
    'AbstractMemoryEntry',
    'SafeInteraction',
    'ValidationStatus',
    'InteractionType',
    'MemoryMetadata',
    'Reference',
    'ReferenceType',
    'AbstractionMapping',
    'ValidationResult',
    'SafeMemoryRepository',
    'MemoryValidator',
    'MemoryClusterManager',
    'ClusterType',
    'MemoryDecayEngine',
    
    # Embeddings system
    'EmbeddingService',
    'EmbeddingCache',
    'EmbeddingResult',
    'EmbeddingMetadata',
    'ContentType',
    'ModelConfig',
    'BatchEmbeddingRequest',
    'BatchEmbeddingResult',
    
    # Intent analysis
    'IntentEngine',
    'IntentAnalyzer',
    'ConnectionFinder',
    'IntentType',
    'IntentResult',
    'IntentMetadata',
    'ConnectionType',
    'Connection',
    'ConnectionResult',
    'QueryAnalysis',
    'IntentPattern',
    'ExplanationReason',
    'FeedbackType',
    'LearningFeedback',
    
    # Safety models
    'SafetyScore',
    'ValidationError',
    'AbstractionQuality',
    'ReferencePattern',
    
    # Metrics
    'SafetyMetricsCollector'
]