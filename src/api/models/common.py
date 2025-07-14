"""
Common API models used across endpoints.

This module provides shared Pydantic models for standard API responses,
errors, and pagination.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated data
T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    detail: str = Field(
        ...,
        description="Human-readable error message"
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for correlation"
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Detailed validation errors"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Request content failed safety validation",
                    "error_code": "SAFETY_VALIDATION_FAILED",
                    "request_id": "123e4567-e89b-12d3-a456-426614174000"
                }
            ]
        }
    }


class SuccessResponse(BaseModel):
    """Standard success response model."""
    
    message: str = Field(
        ...,
        description="Success message"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional response data"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Operation completed successfully",
                    "data": {"processed_items": 10}
                }
            ]
        }
    }


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    
    page: int = Field(
        ...,
        description="Current page number",
        ge=1
    )
    page_size: int = Field(
        ...,
        description="Items per page",
        ge=1
    )
    total_items: int = Field(
        ...,
        description="Total number of items",
        ge=0
    )
    total_pages: int = Field(
        ...,
        description="Total number of pages",
        ge=0
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page"
    )
    has_previous: bool = Field(
        ...,
        description="Whether there is a previous page"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    
    items: List[T] = Field(
        ...,
        description="List of items for current page"
    )
    meta: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [{"id": "123", "name": "Example"}],
                    "meta": {
                        "page": 1,
                        "page_size": 20,
                        "total_items": 100,
                        "total_pages": 5,
                        "has_next": True,
                        "has_previous": False
                    }
                }
            ]
        }
    }


class HealthStatus(BaseModel):
    """Health check status model."""
    
    status: str = Field(
        ...,
        description="Service health status",
        pattern="^(healthy|degraded|unhealthy)$"
    )
    service: str = Field(
        ...,
        description="Service name"
    )
    checks: Optional[Dict[str, bool]] = Field(
        None,
        description="Individual health checks"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "service": "api",
                    "checks": {
                        "database": True,
                        "cache": True,
                        "embeddings": True
                    }
                }
            ]
        }
    }