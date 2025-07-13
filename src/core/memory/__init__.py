"""
Memory module for the Cognitive Coding Partner.

Provides comprehensive memory management with safety-first principles,
including temporal decay, semantic clustering, and relationship tracking.
"""

from .abstract_models import (
    AbstractMemoryEntry,
    SafeInteraction,
    ValidationStatus,
    InteractionType,
    ReferenceType,
    MemoryMetadata,
    Reference,
    ValidationResult,
    AbstractionMapping,
)

from .validator import MemoryValidator

from .repository import SafeMemoryRepository

from .decay_engine import (
    MemoryDecayEngine,
    DecayConfiguration,
    DecayAnalysis,
)

from .cluster_manager import (
    MemoryClusterManager,
    MemoryCluster,
    ClusterType,
    ClusterMember,
    ClusteringResult,
)

# Embedding support
from ..embeddings import (
    EmbeddingService,
    EmbeddingCache,
    EmbeddingResult,
    EmbeddingMetadata,
    ContentType,
    ModelConfig,
)

__all__ = [
    # Core models
    "AbstractMemoryEntry",
    "SafeInteraction",
    "ValidationStatus",
    "InteractionType",
    "ReferenceType",
    "MemoryMetadata",
    "Reference",
    "ValidationResult",
    "AbstractionMapping",
    
    # Validation
    "MemoryValidator",
    
    # Repository
    "SafeMemoryRepository",
    
    # Decay engine
    "MemoryDecayEngine",
    "DecayConfiguration", 
    "DecayAnalysis",
    
    # Clustering
    "MemoryClusterManager",
    "MemoryCluster",
    "ClusterType",
    "ClusterMember",
    "ClusteringResult",
    
    # Embeddings
    "EmbeddingService",
    "EmbeddingCache",
    "EmbeddingResult",
    "EmbeddingMetadata",
    "ContentType",
    "ModelConfig",
]

# Version info
__version__ = "1.4.0"
__author__ = "Cognitive Coding Partner Team"
__description__ = "Safety-first memory management with temporal decay and semantic clustering"