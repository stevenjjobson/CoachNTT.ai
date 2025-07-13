"""
Data models for the embedding system.

Defines the core data structures used throughout the embedding pipeline.
"""

import hashlib
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class ContentType(Enum):
    """Types of content for embedding generation."""
    TEXT = "text"
    CODE = "code"
    DOCUMENTATION = "documentation"
    QUERY = "query"
    MIXED = "mixed"


class ModelConfig(BaseModel):
    """Configuration for embedding models."""
    model_name: str
    content_types: List[ContentType]
    dimensions: int = 384  # Default for sentence-transformers
    max_length: int = 512
    device: str = "cpu"
    batch_size: int = 32
    
    @validator('model_name')
    def validate_model_name(cls, v):
        """Validate model name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model name cannot be empty")
        return v.strip()


class EmbeddingMetadata(BaseModel):
    """Metadata associated with an embedding."""
    content_type: ContentType
    model_name: str
    model_version: str = "1.0.0"
    language: Optional[str] = None
    safety_score: Decimal = Decimal("0.0")
    content_hash: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    dimensions: int = 384
    
    @validator('content_hash')
    def validate_content_hash(cls, v):
        """Validate content hash format."""
        if not v or len(v) != 64:  # SHA-256 hex length
            raise ValueError("Content hash must be 64-character SHA-256 hex string")
        return v
    
    @validator('safety_score')
    def validate_safety_score(cls, v):
        """Validate safety score is within valid range."""
        if v < 0 or v > 1:
            raise ValueError("Safety score must be between 0.0 and 1.0")
        return v


class EmbeddingResult(BaseModel):
    """Result of embedding generation."""
    embedding_id: UUID = Field(default_factory=uuid4)
    vector: List[float]
    metadata: EmbeddingMetadata
    processing_time_ms: int = 0
    cache_hit: bool = False
    
    @validator('vector')
    def validate_vector_dimensions(cls, v, values):
        """Validate vector dimensions match metadata."""
        if 'metadata' in values and len(v) != values['metadata'].dimensions:
            raise ValueError(
                f"Vector length ({len(v)}) doesn't match metadata dimensions "
                f"({values['metadata'].dimensions})"
            )
        return v
    
    @validator('vector')
    def validate_vector_values(cls, v):
        """Validate vector contains valid float values."""
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numeric values")
        if not all(-1.0 <= x <= 1.0 for x in v):
            raise ValueError("Vector values should be normalized between -1.0 and 1.0")
        return v


class CacheEntry(BaseModel):
    """Cache entry for embeddings."""
    cache_key: str
    embedding_result: EmbeddingResult
    created_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = None
    
    @validator('cache_key')
    def validate_cache_key(cls, v):
        """Validate cache key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Cache key cannot be empty")
        return v.strip()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        return age_seconds > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class BatchEmbeddingRequest(BaseModel):
    """Request for batch embedding generation."""
    texts: List[str]
    content_type: ContentType = ContentType.TEXT
    model_name: Optional[str] = None
    language: Optional[str] = None
    include_metadata: bool = True
    
    @validator('texts')
    def validate_texts(cls, v):
        """Validate text inputs."""
        if not v:
            raise ValueError("Texts list cannot be empty")
        if len(v) > 100:  # Reasonable batch limit
            raise ValueError("Batch size cannot exceed 100 texts")
        if any(not text.strip() for text in v):
            raise ValueError("All texts must be non-empty")
        return v


class BatchEmbeddingResult(BaseModel):
    """Result of batch embedding generation."""
    request_id: UUID = Field(default_factory=uuid4)
    results: List[EmbeddingResult]
    total_processing_time_ms: int = 0
    cache_hits: int = 0
    generated_count: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = len(self.results)
        return (self.cache_hits / total) if total > 0 else 0.0
    
    @property
    def average_processing_time_ms(self) -> float:
        """Calculate average processing time per embedding."""
        total = len(self.results)
        return (self.total_processing_time_ms / total) if total > 0 else 0.0


class EmbeddingQualityMetrics(BaseModel):
    """Quality metrics for embedding evaluation."""
    embedding_id: UUID
    consistency_score: float = 0.0  # Consistency across multiple generations
    diversity_score: float = 0.0    # How different from other embeddings
    magnitude: float = 0.0           # Vector magnitude
    sparsity: float = 0.0           # Percentage of near-zero values
    outlier_score: float = 0.0       # How much of an outlier this embedding is
    
    @validator('consistency_score', 'diversity_score', 'magnitude', 
               'sparsity', 'outlier_score')
    def validate_metric_range(cls, v):
        """Validate metric values are within valid range."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Metric values must be between 0.0 and 1.0")
        return v


def generate_content_hash(content: str, model_name: str = "") -> str:
    """
    Generate a SHA-256 hash for content and model combination.
    
    Args:
        content: The content to hash
        model_name: Model name to include in hash
        
    Returns:
        64-character SHA-256 hex string
    """
    content_bytes = f"{content}:{model_name}".encode('utf-8')
    return hashlib.sha256(content_bytes).hexdigest()


def normalize_vector(vector: List[float]) -> List[float]:
    """
    Normalize a vector to unit length.
    
    Args:
        vector: Input vector
        
    Returns:
        Normalized vector
    """
    magnitude = sum(x * x for x in vector) ** 0.5
    if magnitude == 0:
        return vector
    return [x / magnitude for x in vector]


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score (-1.0 to 1.0)
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same dimensions")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)