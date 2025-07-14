"""
Knowledge graph API endpoints.

This module provides REST endpoints for building, querying, and exporting
knowledge graphs from memory data with safety-first design.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import PlainTextResponse

from ..dependencies import CurrentUser, get_knowledge_graph_builder
from ..models.graph import (
    GraphBuildRequest,
    GraphResponse,
    GraphQuery,
    GraphQueryResult,
    GraphExportRequest,
    GraphExportResult,
    SubgraphRequest,
    GraphNode,
    GraphEdge
)
from ...services.vault.graph_builder import KnowledgeGraphBuilder
from ...services.vault.graph_models import KnowledgeGraph
from ...services.vault.graph_exporters import (
    MermaidExporter,
    JSONExporter,
    D3Exporter,
    CytoscapeExporter,
    GraphMLExporter
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory graph storage (in production, this would be a proper database)
_graph_storage: Dict[UUID, KnowledgeGraph] = {}


@router.post(
    "/build",
    response_model=GraphResponse,
    summary="Build knowledge graph",
    description="Build a knowledge graph from memories and optionally code files"
)
async def build_graph(
    request: GraphBuildRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    graph_builder: KnowledgeGraphBuilder = Depends(get_knowledge_graph_builder),
) -> GraphResponse:
    """Build a knowledge graph from memories and code."""
    try:
        logger.info(f"Building graph for user {current_user['sub']} with {request.max_memories} max memories")
        
        # Convert string paths to Path objects if provided
        code_paths = None
        if request.code_paths:
            code_paths = [Path(path) for path in request.code_paths]
            # Validate paths exist
            for path in code_paths:
                if not path.exists():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Code path does not exist: {path}"
                    )
        
        # Build the graph
        graph = await graph_builder.build_graph(
            memory_ids=request.memory_ids,
            code_paths=code_paths,
            max_memories=request.max_memories,
            include_related=request.include_related,
            graph_name=request.graph_name
        )
        
        # Store graph in memory (in production, save to database)
        _graph_storage[graph.graph_id] = graph
        
        # Calculate metrics
        metrics = graph.calculate_metrics()
        
        # Create response
        response = GraphResponse(
            graph_id=graph.graph_id,
            name=graph.name,
            description=graph.description,
            metrics=metrics,
            created_at=graph.created_at,
            updated_at=graph.updated_at
        )
        
        logger.info(
            f"Graph built successfully: {graph.node_count} nodes, "
            f"{graph.edge_count} edges in {graph.build_time_ms:.1f}ms"
        )
        
        return response
        
    except ValueError as e:
        logger.warning(f"Graph build validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph building failed"
        )


@router.get(
    "/{graph_id}",
    response_model=GraphResponse,
    summary="Get graph metadata",
    description="Retrieve knowledge graph metadata and statistics"
)
async def get_graph(
    graph_id: UUID,
    current_user: CurrentUser,
) -> GraphResponse:
    """Get knowledge graph metadata."""
    try:
        # Retrieve graph from storage
        if graph_id not in _graph_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph not found"
            )
        
        graph = _graph_storage[graph_id]
        
        # Calculate current metrics
        metrics = graph.calculate_metrics()
        
        response = GraphResponse(
            graph_id=graph.graph_id,
            name=graph.name,
            description=graph.description,
            metrics=metrics,
            created_at=graph.created_at,
            updated_at=graph.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve graph {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve graph"
        )


@router.post(
    "/{graph_id}/query",
    response_model=GraphQueryResult,
    summary="Query knowledge graph",
    description="Query a knowledge graph with semantic and structural filters"
)
async def query_graph(
    graph_id: UUID,
    query: GraphQuery,
    current_user: CurrentUser,
    graph_builder: KnowledgeGraphBuilder = Depends(get_knowledge_graph_builder),
) -> GraphQueryResult:
    """Query a knowledge graph with filters."""
    try:
        # Retrieve graph from storage
        if graph_id not in _graph_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph not found"
            )
        
        graph = _graph_storage[graph_id]
        
        # Convert Pydantic models to internal models
        from ...services.vault.graph_models import GraphQuery as InternalGraphQuery
        
        internal_query = InternalGraphQuery(
            node_types=query.node_types,
            edge_types=query.edge_types,
            min_node_safety_score=query.min_node_safety_score,
            min_edge_weight=query.min_edge_weight,
            min_edge_confidence=query.min_edge_confidence,
            node_content_pattern=query.node_content_pattern,
            node_created_after=query.node_created_after,
            max_nodes=query.max_nodes,
            max_edges=query.max_edges,
            sort_by=query.sort_by,
            sort_descending=query.sort_descending
        )
        
        # Execute query
        result = await graph_builder.query_graph(graph, internal_query)
        
        # Convert results to API models
        api_nodes = []
        for node in result.nodes:
            api_node = GraphNode(
                node_id=node.node_id,
                node_type=node.node_type,
                title_pattern=node.title_pattern,
                description_pattern=node.description_pattern,
                safety_score=node.safety_score,
                is_validated=node.is_validated,
                created_at=node.created_at,
                centrality_score=node.centrality_score,
                source_type=node.source_type,
                source_file=node.source_file
            )
            api_nodes.append(api_node)
        
        api_edges = []
        for edge in result.edges:
            api_edge = GraphEdge(
                edge_id=edge.edge_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                edge_type=edge.edge_type,
                weight=edge.weight,
                confidence=edge.confidence,
                explanation_pattern=edge.explanation_pattern,
                temporal_distance_hours=edge.temporal_distance_hours,
                temporal_weight=edge.temporal_weight,
                safety_score=edge.safety_score,
                is_bidirectional=edge.is_bidirectional
            )
            api_edges.append(api_edge)
        
        response = GraphQueryResult(
            nodes=api_nodes,
            edges=api_edges,
            query_time_ms=result.query_time_ms,
            nodes_examined=result.nodes_examined,
            edges_examined=result.edges_examined
        )
        
        logger.debug(
            f"Graph query completed: {len(api_nodes)} nodes, "
            f"{len(api_edges)} edges in {result.query_time_ms:.1f}ms"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph query failed for {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph query failed"
        )


@router.post(
    "/{graph_id}/export",
    response_model=GraphExportResult,
    summary="Export knowledge graph",
    description="Export knowledge graph in various formats (Mermaid, JSON, GraphML, etc.)"
)
async def export_graph(
    graph_id: UUID,
    export_request: GraphExportRequest,
    current_user: CurrentUser,
) -> GraphExportResult:
    """Export knowledge graph in specified format."""
    try:
        start_time = time.time()
        
        # Retrieve graph from storage
        if graph_id not in _graph_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph not found"
            )
        
        graph = _graph_storage[graph_id]
        
        # Filter graph if requested
        if export_request.max_nodes or export_request.filter_by_centrality:
            nodes_to_include = list(graph.nodes.values())
            
            # Filter by centrality if specified
            if export_request.filter_by_centrality:
                nodes_to_include = [
                    n for n in nodes_to_include 
                    if n.centrality_score and n.centrality_score >= export_request.filter_by_centrality
                ]
            
            # Limit nodes if specified
            if export_request.max_nodes and len(nodes_to_include) > export_request.max_nodes:
                # Sort by centrality and take top nodes
                nodes_to_include.sort(key=lambda n: n.centrality_score or 0, reverse=True)
                nodes_to_include = nodes_to_include[:export_request.max_nodes]
            
            # Filter edges to only include those between included nodes
            node_ids = {n.node_id for n in nodes_to_include}
            edges_to_include = [
                e for e in graph.edges.values()
                if e.source_node_id in node_ids and e.target_node_id in node_ids
            ]
        else:
            nodes_to_include = list(graph.nodes.values())
            edges_to_include = list(graph.edges.values())
        
        # Select appropriate exporter
        exporter = None
        if export_request.format == "mermaid":
            exporter = MermaidExporter()
        elif export_request.format == "json":
            exporter = JSONExporter()
        elif export_request.format == "d3":
            exporter = D3Exporter()
        elif export_request.format == "cytoscape":
            exporter = CytoscapeExporter()
        elif export_request.format == "graphml":
            exporter = GraphMLExporter()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {export_request.format}"
            )
        
        # Create temporary filtered graph for export
        filtered_graph = KnowledgeGraph(
            name=f"{graph.name}_filtered",
            description=f"Filtered export of {graph.name}"
        )
        
        for node in nodes_to_include:
            filtered_graph.add_node(node)
        
        for edge in edges_to_include:
            filtered_graph.add_edge(edge)
        
        # Export graph
        exported_content = await exporter.export_graph(
            filtered_graph,
            include_metadata=export_request.include_metadata
        )
        
        # Validate safety of exported content
        safety_validated = True
        try:
            # Simple safety check - ensure no concrete references leaked
            if "<" not in exported_content or ">" not in exported_content:
                logger.warning("Exported content may not be properly abstracted")
                safety_validated = False
        except Exception as e:
            logger.warning(f"Safety validation failed for export: {e}")
            safety_validated = False
        
        export_time_ms = (time.time() - start_time) * 1000
        
        response = GraphExportResult(
            format=export_request.format,
            content=exported_content,
            node_count=len(nodes_to_include),
            edge_count=len(edges_to_include),
            export_time_ms=export_time_ms,
            safety_validated=safety_validated
        )
        
        logger.info(
            f"Graph exported in {export_request.format} format: "
            f"{len(nodes_to_include)} nodes, {len(edges_to_include)} edges, "
            f"{export_time_ms:.1f}ms"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph export failed for {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph export failed"
        )


@router.post(
    "/{graph_id}/subgraph",
    response_model=GraphQueryResult,
    summary="Extract subgraph",
    description="Extract a subgraph around a specific node with configurable depth"
)
async def get_subgraph(
    graph_id: UUID,
    subgraph_request: SubgraphRequest,
    current_user: CurrentUser,
) -> GraphQueryResult:
    """Extract a subgraph around a specific node."""
    try:
        start_time = time.time()
        
        # Retrieve graph from storage
        if graph_id not in _graph_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph not found"
            )
        
        graph = _graph_storage[graph_id]
        
        # Check if center node exists
        if subgraph_request.center_node_id not in graph.nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Center node not found in graph"
            )
        
        # Extract subgraph using breadth-first search
        visited_nodes = set()
        nodes_to_include = []
        edges_to_include = []
        
        # Queue for BFS: (node_id, depth)
        queue = [(subgraph_request.center_node_id, 0)]
        visited_nodes.add(subgraph_request.center_node_id)
        
        while queue and len(nodes_to_include) < subgraph_request.max_nodes:
            current_node_id, depth = queue.pop(0)
            current_node = graph.nodes[current_node_id]
            nodes_to_include.append(current_node)
            
            # If we haven't reached max depth, explore neighbors
            if depth < subgraph_request.max_depth:
                for edge in graph.edges.values():
                    # Check edge weight threshold
                    if edge.weight < subgraph_request.min_edge_weight:
                        continue
                    
                    # Check edge type filter
                    if (subgraph_request.include_edge_types and 
                        edge.edge_type not in subgraph_request.include_edge_types):
                        continue
                    
                    neighbor_id = None
                    if edge.source_node_id == current_node_id:
                        neighbor_id = edge.target_node_id
                    elif edge.target_node_id == current_node_id:
                        neighbor_id = edge.source_node_id
                    
                    if neighbor_id and neighbor_id not in visited_nodes:
                        if neighbor_id in graph.nodes:
                            queue.append((neighbor_id, depth + 1))
                            visited_nodes.add(neighbor_id)
                    
                    # Include edge if both nodes are in subgraph
                    if (edge.source_node_id in visited_nodes and 
                        edge.target_node_id in visited_nodes):
                        edges_to_include.append(edge)
        
        # Convert to API models
        api_nodes = []
        for node in nodes_to_include:
            api_node = GraphNode(
                node_id=node.node_id,
                node_type=node.node_type,
                title_pattern=node.title_pattern,
                description_pattern=node.description_pattern,
                safety_score=node.safety_score,
                is_validated=node.is_validated,
                created_at=node.created_at,
                centrality_score=node.centrality_score,
                source_type=node.source_type,
                source_file=node.source_file
            )
            api_nodes.append(api_node)
        
        api_edges = []
        for edge in edges_to_include:
            api_edge = GraphEdge(
                edge_id=edge.edge_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                edge_type=edge.edge_type,
                weight=edge.weight,
                confidence=edge.confidence,
                explanation_pattern=edge.explanation_pattern,
                temporal_distance_hours=edge.temporal_distance_hours,
                temporal_weight=edge.temporal_weight,
                safety_score=edge.safety_score,
                is_bidirectional=edge.is_bidirectional
            )
            api_edges.append(api_edge)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        response = GraphQueryResult(
            nodes=api_nodes,
            edges=api_edges,
            query_time_ms=query_time_ms,
            nodes_examined=len(graph.nodes),
            edges_examined=len(graph.edges)
        )
        
        logger.debug(
            f"Subgraph extracted: {len(api_nodes)} nodes, "
            f"{len(api_edges)} edges in {query_time_ms:.1f}ms"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subgraph extraction failed for {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subgraph extraction failed"
        )


@router.get(
    "/",
    summary="List available graphs",
    description="Get list of available knowledge graphs for the current user"
)
async def list_graphs(
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """List available knowledge graphs."""
    try:
        graphs = []
        for graph_id, graph in _graph_storage.items():
            metrics = graph.calculate_metrics()
            graphs.append({
                "graph_id": graph_id,
                "name": graph.name,
                "description": graph.description,
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
                "created_at": graph.created_at,
                "updated_at": graph.updated_at,
                "average_safety_score": metrics.average_safety_score
            })
        
        return {
            "graphs": graphs,
            "total_count": len(graphs)
        }
        
    except Exception as e:
        logger.error(f"Failed to list graphs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list graphs"
        )


@router.delete(
    "/{graph_id}",
    summary="Delete knowledge graph",
    description="Delete a knowledge graph and all associated data"
)
async def delete_graph(
    graph_id: UUID,
    current_user: CurrentUser,
) -> Dict[str, str]:
    """Delete a knowledge graph."""
    try:
        if graph_id not in _graph_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph not found"
            )
        
        # Remove graph from storage
        graph = _graph_storage.pop(graph_id)
        
        logger.info(f"Graph {graph_id} ({graph.name}) deleted by user {current_user['sub']}")
        
        return {
            "message": "Graph deleted successfully",
            "graph_id": str(graph_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete graph {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete graph"
        )