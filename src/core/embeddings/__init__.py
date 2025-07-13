"""
Vector embeddings module for enhanced similarity search and clustering.

Provides sentence-transformer-based embedding generation with safety-first principles.
"""

from .service import EmbeddingService
from .cache import EmbeddingCache
from .models import (
    EmbeddingResult,
    EmbeddingMetadata,
    ContentType,
    ModelConfig,
    CacheEntry
)

__all__ = [
    'EmbeddingService',
    'EmbeddingCache', 
    'EmbeddingResult',
    'EmbeddingMetadata',
    'ContentType',
    'ModelConfig',
    'CacheEntry'
]