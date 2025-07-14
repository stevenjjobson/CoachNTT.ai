"""
Knowledge graph API models.

This module provides Pydantic models for knowledge graph operations,
including graph building, querying, and export functionality.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ...services.vault.graph_models import NodeType, EdgeType


class GraphBuildRequest(BaseModel):
    """Model for building a knowledge graph."""
    
    memory_ids: Optional[List[UUID]] = Field(
        None,
        description="Specific memory IDs to include (None for recent memories)"
    )
    code_paths: Optional[List[str]] = Field(
        None,
        description="Code file paths to analyze and include in graph"
    )
    max_memories: int = Field(
        100,
        description="Maximum number of memories to process",
        ge=1,
        le=1000
    )
    include_related: bool = Field(
        True,
        description="Include related memories using intent analysis"
    )
    graph_name: Optional[str] = Field(
        None,
        description="Optional name for the graph",
        max_length=100
    )
    enable_code_analysis: bool = Field(
        True,
        description="Enable analysis of code files"
    )
    enable_temporal_weighting: bool = Field(
        True,
        description="Enable temporal weighting of connections"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "max_memories": 50,
                    "include_related": True,
                    "graph_name": "API Development Graph",
                    "enable_code_analysis": True,
                    "enable_temporal_weighting": True
                }
            ]
        }
    )


class GraphNode(BaseModel):
    """Model for a knowledge graph node."""
    
    node_id: UUID = Field(
        ...,
        description="Unique node identifier"
    )
    node_type: NodeType = Field(
        ...,
        description="Type of node (memory, code_module, code_function, etc.)"
    )
    title_pattern: str = Field(
        ...,
        description="Abstracted title pattern",
        max_length=200
    )
    description_pattern: str = Field(
        ...,
        description="Abstracted description pattern",
        max_length=500
    )
    safety_score: Decimal = Field(
        ...,
        description="Safety validation score",
        ge=0,
        le=1
    )
    is_validated: bool = Field(
        ...,
        description="Whether the node passed safety validation"
    )
    created_at: datetime = Field(
        ...,
        description="Node creation timestamp"
    )
    centrality_score: Optional[float] = Field(
        None,
        description="Graph centrality score",
        ge=0,
        le=1
    )
    source_type: str = Field(
        ...,
        description="Source type (memory, ast_analysis, etc.)"
    )
    source_file: Optional[str] = Field(
        None,
        description="Source file path for code nodes"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "node_id": "123e4567-e89b-12d3-a456-426614174000",
                    "node_type": "memory",
                    "title_pattern": "<memory_api_design>",
                    "description_pattern": "Design patterns for <api_framework>...",
                    "safety_score": 0.95,
                    "is_validated": True,
                    "created_at": "2024-01-13T10:00:00Z",
                    "centrality_score": 0.75,
                    "source_type": "memory"
                }
            ]
        }
    )


class GraphEdge(BaseModel):
    """Model for a knowledge graph edge."""
    
    edge_id: UUID = Field(
        ...,
        description="Unique edge identifier"
    )
    source_node_id: UUID = Field(
        ...,
        description="Source node ID"
    )
    target_node_id: UUID = Field(
        ...,
        description="Target node ID"
    )
    edge_type: EdgeType = Field(
        ...,
        description="Type of relationship"
    )
    weight: float = Field(
        ...,
        description="Edge weight/strength",
        ge=0,
        le=1
    )
    confidence: float = Field(
        ...,
        description="Confidence in the relationship",
        ge=0,
        le=1
    )
    explanation_pattern: str = Field(
        ...,
        description="Abstracted explanation of the relationship",
        max_length=200
    )
    temporal_distance_hours: Optional[float] = Field(
        None,
        description="Temporal distance in hours",
        ge=0
    )
    temporal_weight: Optional[float] = Field(
        None,
        description="Temporal weight factor",
        ge=0,
        le=1
    )
    safety_score: Decimal = Field(
        ...,
        description="Safety validation score",
        ge=0,
        le=1
    )
    is_bidirectional: bool = Field(
        ...,
        description="Whether the relationship is bidirectional"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "edge_id": "223e4567-e89b-12d3-a456-426614174001",
                    "source_node_id": "123e4567-e89b-12d3-a456-426614174000",
                    "target_node_id": "323e4567-e89b-12d3-a456-426614174002",
                    "edge_type": "similar_to",
                    "weight": 0.85,
                    "confidence": 0.92,
                    "explanation_pattern": "Semantic similarity of 0.85",
                    "temporal_distance_hours": 2.5,
                    "temporal_weight": 0.95,
                    "safety_score": 0.98,
                    "is_bidirectional": True
                }
            ]
        }
    )


class GraphMetrics(BaseModel):
    """Model for graph metrics and statistics."""
    
    node_count: int = Field(
        ...,
        description="Total number of nodes",
        ge=0
    )
    edge_count: int = Field(
        ...,
        description="Total number of edges", 
        ge=0
    )
    density: float = Field(
        ...,
        description="Graph density (0-1)",
        ge=0,
        le=1
    )
    average_degree: float = Field(
        ...,
        description="Average node degree",
        ge=0
    )
    connected_components: int = Field(
        ...,
        description="Number of connected components",
        ge=0
    )
    average_safety_score: Decimal = Field(
        ...,
        description="Average safety score across all nodes",
        ge=0,
        le=1
    )
    build_time_ms: float = Field(
        ...,
        description="Graph build time in milliseconds",
        ge=0
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "node_count": 25,
                    "edge_count": 45,
                    "density": 0.15,
                    "average_degree": 3.6,
                    "connected_components": 2,
                    "average_safety_score": 0.92,
                    "build_time_ms": 850.5
                }
            ]
        }
    )


class GraphResponse(BaseModel):
    """Model for graph creation/retrieval response."""
    
    graph_id: UUID = Field(
        ...,
        description="Unique graph identifier"
    )
    name: str = Field(
        ...,
        description="Graph name"
    )
    description: str = Field(
        ...,
        description="Graph description"
    )
    metrics: GraphMetrics = Field(
        ...,
        description="Graph metrics and statistics"
    )
    created_at: datetime = Field(
        ...,
        description="Graph creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "graph_id": "423e4567-e89b-12d3-a456-426614174003",
                    "name": "API Development Graph",
                    "description": "Knowledge graph for API development memories",
                    "metrics": {
                        "node_count": 25,
                        "edge_count": 45,
                        "density": 0.15,
                        "average_degree": 3.6,
                        "connected_components": 2,
                        "average_safety_score": 0.92,
                        "build_time_ms": 850.5
                    },
                    "created_at": "2024-01-13T10:00:00Z",
                    "updated_at": "2024-01-13T10:00:00Z"
                }
            ]
        }
    )


class GraphQuery(BaseModel):
    """Model for querying a knowledge graph."""
    
    node_types: Optional[List[NodeType]] = Field(
        None,
        description="Filter by node types"
    )
    edge_types: Optional[List[EdgeType]] = Field(
        None,
        description="Filter by edge types"
    )
    min_node_safety_score: float = Field(
        0.0,
        description="Minimum node safety score",
        ge=0,
        le=1
    )
    min_edge_weight: float = Field(
        0.0,
        description="Minimum edge weight",
        ge=0,
        le=1
    )
    min_edge_confidence: float = Field(
        0.0,
        description="Minimum edge confidence",
        ge=0,
        le=1
    )
    node_content_pattern: Optional[str] = Field(
        None,
        description="Search pattern for node content",
        max_length=100
    )
    node_created_after: Optional[datetime] = Field(
        None,
        description="Filter nodes created after this timestamp"
    )
    max_nodes: int = Field(
        50,
        description="Maximum nodes to return",
        ge=1,
        le=500
    )
    max_edges: int = Field(
        100,
        description="Maximum edges to return",
        ge=1,
        le=1000
    )
    sort_by: str = Field(
        "centrality",
        description="Sort criteria (centrality, created_at, safety_score)",
        regex="^(centrality|created_at|safety_score)$"
    )
    sort_descending: bool = Field(
        True,
        description="Sort in descending order"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "node_types": ["memory", "code_function"],
                    "min_node_safety_score": 0.8,
                    "min_edge_weight": 0.5,
                    "node_content_pattern": "api",
                    "max_nodes": 20,
                    "sort_by": "centrality",
                    "sort_descending": True
                }
            ]
        }
    )


class GraphQueryResult(BaseModel):
    """Model for graph query results."""
    
    nodes: List[GraphNode] = Field(
        ...,
        description="Filtered nodes"
    )
    edges: List[GraphEdge] = Field(
        ...,
        description="Filtered edges"
    )
    query_time_ms: float = Field(
        ...,
        description="Query execution time in milliseconds",
        ge=0
    )
    nodes_examined: int = Field(
        ...,
        description="Total nodes examined",
        ge=0
    )
    edges_examined: int = Field(
        ...,
        description="Total edges examined",
        ge=0
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nodes": [],
                    "edges": [],
                    "query_time_ms": 125.5,
                    "nodes_examined": 25,
                    "edges_examined": 45
                }
            ]
        }
    )


class GraphExportRequest(BaseModel):
    """Model for graph export request."""
    
    format: str = Field(
        ...,
        description="Export format (mermaid, json, d3, cytoscape, graphml)",
        regex="^(mermaid|json|d3|cytoscape|graphml)$"
    )
    include_metadata: bool = Field(
        True,
        description="Include node and edge metadata in export"
    )
    max_nodes: Optional[int] = Field(
        None,
        description="Maximum nodes to export (None for all)",
        ge=1,
        le=1000
    )
    filter_by_centrality: Optional[float] = Field(
        None,
        description="Minimum centrality score for inclusion",
        ge=0,
        le=1
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "format": "mermaid",
                    "include_metadata": True,
                    "max_nodes": 50,
                    "filter_by_centrality": 0.1
                }
            ]
        }
    )


class GraphExportResult(BaseModel):
    """Model for graph export result."""
    
    format: str = Field(
        ...,
        description="Export format used"
    )
    content: str = Field(
        ...,
        description="Exported graph content"
    )
    node_count: int = Field(
        ...,
        description="Number of nodes exported",
        ge=0
    )
    edge_count: int = Field(
        ...,
        description="Number of edges exported",
        ge=0
    )
    export_time_ms: float = Field(
        ...,
        description="Export processing time in milliseconds",
        ge=0
    )
    safety_validated: bool = Field(
        ...,
        description="Whether export passed safety validation"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "format": "mermaid",
                    "content": "graph TD\n  A[<memory_api>] --> B[<function_handler>]",
                    "node_count": 25,
                    "edge_count": 40,
                    "export_time_ms": 185.2,
                    "safety_validated": True
                }
            ]
        }
    )


class SubgraphRequest(BaseModel):
    """Model for subgraph extraction request."""
    
    center_node_id: UUID = Field(
        ...,
        description="ID of the center node"
    )
    max_depth: int = Field(
        2,
        description="Maximum depth from center node",
        ge=1,
        le=5
    )
    max_nodes: int = Field(
        20,
        description="Maximum nodes to include",
        ge=1,
        le=100
    )
    min_edge_weight: float = Field(
        0.3,
        description="Minimum edge weight to follow",
        ge=0,
        le=1
    )
    include_edge_types: Optional[List[EdgeType]] = Field(
        None,
        description="Edge types to include (None for all)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "center_node_id": "123e4567-e89b-12d3-a456-426614174000",
                    "max_depth": 2,
                    "max_nodes": 15,
                    "min_edge_weight": 0.5,
                    "include_edge_types": ["similar_to", "related_to"]
                }
            ]
        }
    )