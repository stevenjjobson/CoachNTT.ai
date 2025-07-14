"""
Integration API models.

This module provides Pydantic models for integration operations,
including vault sync, documentation generation, and checkpoint management.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ...services.vault.models import TemplateType, ConflictStrategy, SyncDirection


class CheckpointRequest(BaseModel):
    """Model for creating a memory checkpoint."""
    
    checkpoint_name: str = Field(
        ...,
        description="Name for the checkpoint",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        description="Optional description of the checkpoint",
        max_length=500
    )
    include_code_analysis: bool = Field(
        True,
        description="Include code analysis in checkpoint"
    )
    memory_filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters for which memories to include"
    )
    max_memories: int = Field(
        100,
        description="Maximum memories to include in checkpoint",
        ge=1,
        le=1000
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "checkpoint_name": "API Development Milestone",
                    "description": "Checkpoint after implementing REST API foundation",
                    "include_code_analysis": True,
                    "max_memories": 50
                }
            ]
        }
    )


class CheckpointResponse(BaseModel):
    """Model for checkpoint creation response."""
    
    checkpoint_id: UUID = Field(
        ...,
        description="Unique checkpoint identifier"
    )
    name: str = Field(
        ...,
        description="Checkpoint name"
    )
    description: Optional[str] = Field(
        None,
        description="Checkpoint description"
    )
    memories_included: int = Field(
        ...,
        description="Number of memories included",
        ge=0
    )
    files_analyzed: int = Field(
        ...,
        description="Number of code files analyzed",
        ge=0
    )
    safety_score: Decimal = Field(
        ...,
        description="Average safety score of checkpoint",
        ge=0,
        le=1
    )
    created_at: datetime = Field(
        ...,
        description="Checkpoint creation timestamp"
    )
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds",
        ge=0
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "checkpoint_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "API Development Milestone",
                    "description": "Checkpoint after implementing REST API foundation",
                    "memories_included": 45,
                    "files_analyzed": 12,
                    "safety_score": 0.92,
                    "created_at": "2024-01-13T10:00:00Z",
                    "processing_time_ms": 1250.5
                }
            ]
        }
    )


class VaultSyncRequest(BaseModel):
    """Model for vault synchronization request."""
    
    sync_direction: SyncDirection = Field(
        SyncDirection.MEMORIES_TO_VAULT,
        description="Direction of synchronization"
    )
    memory_ids: Optional[List[UUID]] = Field(
        None,
        description="Specific memory IDs to sync (None for all recent)"
    )
    vault_files: Optional[List[str]] = Field(
        None,
        description="Specific vault files to sync (for vault-to-memories)"
    )
    template_type: Optional[TemplateType] = Field(
        None,
        description="Template type to use for markdown generation"
    )
    max_memories: int = Field(
        100,
        description="Maximum memories to process",
        ge=1,
        le=500
    )
    conflict_strategy: ConflictStrategy = Field(
        ConflictStrategy.SAFE_MERGE,
        description="Strategy for handling conflicts"
    )
    enable_backlinks: bool = Field(
        True,
        description="Enable backlink generation"
    )
    enable_tag_extraction: bool = Field(
        True,
        description="Enable tag extraction from content"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sync_direction": "memories_to_vault",
                    "template_type": "learning",
                    "max_memories": 50,
                    "conflict_strategy": "safe_merge",
                    "enable_backlinks": True,
                    "enable_tag_extraction": True
                }
            ]
        }
    )


class VaultSyncResponse(BaseModel):
    """Model for vault synchronization response."""
    
    sync_id: UUID = Field(
        ...,
        description="Unique sync operation identifier"
    )
    success: bool = Field(
        ...,
        description="Whether sync completed successfully"
    )
    sync_direction: SyncDirection = Field(
        ...,
        description="Direction of synchronization performed"
    )
    notes_processed: int = Field(
        ...,
        description="Total notes processed",
        ge=0
    )
    notes_created: int = Field(
        ...,
        description="Number of notes created",
        ge=0
    )
    notes_updated: int = Field(
        ...,
        description="Number of notes updated",
        ge=0
    )
    notes_skipped: int = Field(
        ...,
        description="Number of notes skipped",
        ge=0
    )
    conflicts_detected: int = Field(
        ...,
        description="Number of conflicts detected",
        ge=0
    )
    conflicts_resolved: int = Field(
        ...,
        description="Number of conflicts resolved",
        ge=0
    )
    safety_violations: int = Field(
        ...,
        description="Number of safety violations detected",
        ge=0
    )
    average_safety_score: Decimal = Field(
        ...,
        description="Average safety score of processed content",
        ge=0,
        le=1
    )
    processing_time_ms: int = Field(
        ...,
        description="Total processing time in milliseconds",
        ge=0
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of warnings generated"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "sync_id": "223e4567-e89b-12d3-a456-426614174001",
                    "success": True,
                    "sync_direction": "memories_to_vault",
                    "notes_processed": 25,
                    "notes_created": 20,
                    "notes_updated": 5,
                    "notes_skipped": 0,
                    "conflicts_detected": 2,
                    "conflicts_resolved": 2,
                    "safety_violations": 0,
                    "average_safety_score": 0.94,
                    "processing_time_ms": 2500,
                    "errors": [],
                    "warnings": ["Template not found for 1 memory"]
                }
            ]
        }
    )


class DocumentationGenerateRequest(BaseModel):
    """Model for documentation generation request."""
    
    doc_types: List[str] = Field(
        ...,
        description="Types of documentation to generate",
        min_items=1
    )
    output_directory: Optional[str] = Field(
        None,
        description="Output directory for generated docs"
    )
    include_api_docs: bool = Field(
        True,
        description="Include API documentation"
    )
    include_architecture_diagrams: bool = Field(
        True,
        description="Include architecture diagrams"
    )
    include_changelog: bool = Field(
        True,
        description="Include changelog generation"
    )
    max_depth: int = Field(
        3,
        description="Maximum directory depth for code analysis",
        ge=1,
        le=10
    )
    file_patterns: List[str] = Field(
        default_factory=lambda: ["*.py", "*.js", "*.ts"],
        description="File patterns to include in analysis"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["__pycache__", "node_modules", ".git"],
        description="Patterns to exclude from analysis"
    )
    
    @field_validator("doc_types")
    @classmethod
    def validate_doc_types(cls, v):
        """Validate documentation types."""
        valid_types = ["readme", "api", "changelog", "architecture", "coverage"]
        for doc_type in v:
            if doc_type.lower() not in valid_types:
                raise ValueError(f"Invalid documentation type: {doc_type}")
        return [t.lower() for t in v]
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "doc_types": ["readme", "api", "architecture"],
                    "include_api_docs": True,
                    "include_architecture_diagrams": True,
                    "include_changelog": True,
                    "max_depth": 3,
                    "file_patterns": ["*.py", "*.js"],
                    "exclude_patterns": ["__pycache__", "node_modules"]
                }
            ]
        }
    )


class DocumentationFile(BaseModel):
    """Model for a generated documentation file."""
    
    file_path: str = Field(
        ...,
        description="Path to the generated file"
    )
    doc_type: str = Field(
        ...,
        description="Type of documentation"
    )
    size_bytes: int = Field(
        ...,
        description="File size in bytes",
        ge=0
    )
    line_count: int = Field(
        ...,
        description="Number of lines in file",
        ge=0
    )
    safety_validated: bool = Field(
        ...,
        description="Whether content passed safety validation"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "file_path": "./docs/README.md",
                    "doc_type": "readme",
                    "size_bytes": 5432,
                    "line_count": 142,
                    "safety_validated": True
                }
            ]
        }
    )


class DocumentationGenerateResponse(BaseModel):
    """Model for documentation generation response."""
    
    generation_id: UUID = Field(
        ...,
        description="Unique generation operation identifier"
    )
    success: bool = Field(
        ...,
        description="Whether generation completed successfully"
    )
    files_generated: List[DocumentationFile] = Field(
        ...,
        description="List of generated documentation files"
    )
    files_analyzed: int = Field(
        ...,
        description="Number of source files analyzed",
        ge=0
    )
    total_size_bytes: int = Field(
        ...,
        description="Total size of generated files in bytes",
        ge=0
    )
    coverage_percentage: float = Field(
        ...,
        description="Documentation coverage percentage",
        ge=0,
        le=100
    )
    safety_score: Decimal = Field(
        ...,
        description="Average safety score of generated content",
        ge=0,
        le=1
    )
    processing_time_ms: float = Field(
        ...,
        description="Total processing time in milliseconds",
        ge=0
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of warnings generated"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "generation_id": "323e4567-e89b-12d3-a456-426614174002",
                    "success": True,
                    "files_generated": [
                        {
                            "file_path": "./docs/README.md",
                            "doc_type": "readme",
                            "size_bytes": 5432,
                            "line_count": 142,
                            "safety_validated": True
                        }
                    ],
                    "files_analyzed": 25,
                    "total_size_bytes": 15678,
                    "coverage_percentage": 87.5,
                    "safety_score": 0.96,
                    "processing_time_ms": 3250.8,
                    "errors": [],
                    "warnings": ["Some files missing docstrings"]
                }
            ]
        }
    )


class IntegrationStatus(BaseModel):
    """Model for integration service status."""
    
    service_name: str = Field(
        ...,
        description="Name of the integration service"
    )
    status: str = Field(
        ...,
        description="Current status (healthy, degraded, unavailable)"
    )
    last_check: datetime = Field(
        ...,
        description="Last health check timestamp"
    )
    response_time_ms: Optional[float] = Field(
        None,
        description="Response time in milliseconds",
        ge=0
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if service is unhealthy"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional service metadata"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "service_name": "vault_sync",
                    "status": "healthy",
                    "last_check": "2024-01-13T10:00:00Z",
                    "response_time_ms": 125.5,
                    "error_message": None,
                    "metadata": {"version": "1.0.0", "uptime_hours": 24.5}
                }
            ]
        }
    )


class IntegrationStatusResponse(BaseModel):
    """Model for integration status response."""
    
    overall_status: str = Field(
        ...,
        description="Overall status of all integrations"
    )
    services: List[IntegrationStatus] = Field(
        ...,
        description="Status of individual services"
    )
    healthy_count: int = Field(
        ...,
        description="Number of healthy services",
        ge=0
    )
    total_count: int = Field(
        ...,
        description="Total number of services",
        ge=0
    )
    last_updated: datetime = Field(
        ...,
        description="Last status update timestamp"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "overall_status": "healthy",
                    "services": [
                        {
                            "service_name": "vault_sync",
                            "status": "healthy",
                            "last_check": "2024-01-13T10:00:00Z",
                            "response_time_ms": 125.5,
                            "error_message": None,
                            "metadata": {"version": "1.0.0"}
                        }
                    ],
                    "healthy_count": 1,
                    "total_count": 1,
                    "last_updated": "2024-01-13T10:00:00Z"
                }
            ]
        }
    )


class BackgroundTaskStatus(BaseModel):
    """Model for background task status."""
    
    task_id: UUID = Field(
        ...,
        description="Unique task identifier"
    )
    task_type: str = Field(
        ...,
        description="Type of background task"
    )
    status: str = Field(
        ...,
        description="Current task status (pending, running, completed, failed)"
    )
    progress_percentage: float = Field(
        ...,
        description="Task completion percentage",
        ge=0,
        le=100
    )
    started_at: datetime = Field(
        ...,
        description="Task start timestamp"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion timestamp"
    )
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Task result data (if completed)"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message (if failed)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "task_id": "423e4567-e89b-12d3-a456-426614174003",
                    "task_type": "vault_sync",
                    "status": "running",
                    "progress_percentage": 65.0,
                    "started_at": "2024-01-13T10:00:00Z",
                    "estimated_completion": "2024-01-13T10:05:00Z",
                    "result": None,
                    "error_message": None
                }
            ]
        }
    )