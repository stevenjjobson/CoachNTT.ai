"""
Memory-related API models.

This module provides Pydantic models for memory CRUD operations,
search, clustering, and reinforcement endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ...core.memory.models import MemoryType


class MemoryCreate(BaseModel):
    """Model for creating a new memory."""
    
    memory_type: MemoryType = Field(
        ...,
        description="Type of memory (learning, decision, checkpoint)"
    )
    prompt: str = Field(
        ...,
        description="Original prompt or trigger for the memory",
        min_length=1,
        max_length=5000
    )
    content: str = Field(
        ...,
        description="Actual memory content",
        min_length=1,
        max_length=50000
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata"
    )
    
    @field_validator("memory_type", mode="before")
    @classmethod
    def validate_memory_type(cls, v):
        """Convert string to MemoryType enum."""
        if isinstance(v, str):
            try:
                return MemoryType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid memory type: {v}")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "memory_type": "learning",
                    "prompt": "How to implement rate limiting in FastAPI?",
                    "content": "Rate limiting can be implemented using middleware...",
                    "metadata": {"tags": ["fastapi", "middleware", "rate-limiting"]}
                }
            ]
        }
    )


class MemoryUpdate(BaseModel):
    """Model for updating an existing memory."""
    
    prompt: Optional[str] = Field(
        None,
        description="Updated prompt",
        min_length=1,
        max_length=5000
    )
    content: Optional[str] = Field(
        None,
        description="Updated content",
        min_length=1,
        max_length=50000
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated metadata"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "content": "Updated content with new information...",
                    "metadata": {"tags": ["updated", "revised"]}
                }
            ]
        }
    )


class MemoryResponse(BaseModel):
    """Model for memory response."""
    
    memory_id: UUID = Field(
        ...,
        description="Unique memory identifier"
    )
    memory_type: MemoryType = Field(
        ...,
        description="Type of memory"
    )
    abstracted_prompt: str = Field(
        ...,
        description="Abstracted version of the prompt"
    )
    abstracted_content: str = Field(
        ...,
        description="Abstracted version of the content"
    )
    safety_score: Decimal = Field(
        ...,
        description="Safety validation score",
        ge=0,
        le=1
    )
    temporal_weight: Decimal = Field(
        ...,
        description="Current temporal weight",
        ge=0,
        le=1
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Memory metadata"
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )
    accessed_at: datetime = Field(
        ...,
        description="Last access timestamp"
    )
    access_count: int = Field(
        ...,
        description="Number of times accessed",
        ge=0
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "memory_id": "123e4567-e89b-12d3-a456-426614174000",
                    "memory_type": "learning",
                    "abstracted_prompt": "How to implement <rate_limiting> in <framework>?",
                    "abstracted_content": "<Rate_limiting> can be implemented using <middleware>...",
                    "safety_score": 0.95,
                    "temporal_weight": 0.85,
                    "metadata": {"tags": ["api", "middleware"]},
                    "created_at": "2024-01-13T10:00:00Z",
                    "accessed_at": "2024-01-13T12:00:00Z",
                    "access_count": 5
                }
            ]
        }
    )


class MemorySearch(BaseModel):
    """Model for memory search request."""
    
    query: str = Field(
        ...,
        description="Search query",
        min_length=1,
        max_length=1000
    )
    memory_types: Optional[List[MemoryType]] = Field(
        None,
        description="Filter by memory types"
    )
    min_safety_score: Optional[Decimal] = Field(
        None,
        description="Minimum safety score filter",
        ge=0,
        le=1
    )
    min_temporal_weight: Optional[Decimal] = Field(
        None,
        description="Minimum temporal weight filter",
        ge=0,
        le=1
    )
    limit: int = Field(
        20,
        description="Maximum results to return",
        ge=1,
        le=100
    )
    enable_intent_analysis: bool = Field(
        True,
        description="Enable intent analysis for smarter search"
    )
    include_peripheral: bool = Field(
        True,
        description="Include peripherally related memories"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "rate limiting implementation",
                    "memory_types": ["learning", "checkpoint"],
                    "min_safety_score": 0.8,
                    "limit": 10,
                    "enable_intent_analysis": True
                }
            ]
        }
    )


class MemorySearchResult(BaseModel):
    """Model for memory search result."""
    
    memory: MemoryResponse = Field(
        ...,
        description="The memory result"
    )
    relevance_score: float = Field(
        ...,
        description="Relevance score (0-1)",
        ge=0,
        le=1
    )
    match_reason: str = Field(
        ...,
        description="Reason for match (semantic, temporal, usage)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "memory": {
                        "memory_id": "123e4567-e89b-12d3-a456-426614174000",
                        "memory_type": "learning",
                        "abstracted_prompt": "How to implement <concept>?",
                        "abstracted_content": "Implementation details...",
                        "safety_score": 0.95,
                        "temporal_weight": 0.85,
                        "metadata": {},
                        "created_at": "2024-01-13T10:00:00Z",
                        "accessed_at": "2024-01-13T12:00:00Z",
                        "access_count": 5
                    },
                    "relevance_score": 0.92,
                    "match_reason": "semantic"
                }
            ]
        }
    )


class MemoryCluster(BaseModel):
    """Model for memory cluster."""
    
    cluster_id: str = Field(
        ...,
        description="Unique cluster identifier"
    )
    centroid_memory_id: UUID = Field(
        ...,
        description="ID of the cluster centroid memory"
    )
    member_ids: List[UUID] = Field(
        ...,
        description="IDs of memories in this cluster"
    )
    cluster_theme: str = Field(
        ...,
        description="Abstracted theme of the cluster"
    )
    average_safety_score: Decimal = Field(
        ...,
        description="Average safety score of cluster",
        ge=0,
        le=1
    )
    size: int = Field(
        ...,
        description="Number of memories in cluster",
        ge=1
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "cluster_id": "cluster_001",
                    "centroid_memory_id": "123e4567-e89b-12d3-a456-426614174000",
                    "member_ids": [
                        "123e4567-e89b-12d3-a456-426614174000",
                        "223e4567-e89b-12d3-a456-426614174001"
                    ],
                    "cluster_theme": "<middleware> implementation patterns",
                    "average_safety_score": 0.92,
                    "size": 2
                }
            ]
        }
    )


class MemoryReinforce(BaseModel):
    """Model for memory reinforcement request."""
    
    reinforcement_value: float = Field(
        0.1,
        description="Amount to reinforce (0-1)",
        gt=0,
        le=1
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for reinforcement",
        max_length=500
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "reinforcement_value": 0.2,
                    "reason": "Memory was particularly helpful in solving the problem"
                }
            ]
        }
    )