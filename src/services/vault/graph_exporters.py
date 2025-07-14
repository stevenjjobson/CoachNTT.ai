"""
Graph exporters for various visualization formats with safety validation.

Provides Mermaid diagram generation, JSON export, and other formats
for knowledge graph visualization and exploration.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from decimal import Decimal

from .graph_models import (
    KnowledgeGraph, GraphNode, GraphEdge,
    NodeType, EdgeType
)
from ...core.validation.validator import SafetyValidator

logger = logging.getLogger(__name__)


class GraphExporter:
    """Base class for graph exporters with safety validation."""
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        """
        Initialize exporter.
        
        Args:
            safety_validator: Safety validator for content
        """
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Statistics
        self._stats = {
            'exports_performed': 0,
            'nodes_exported': 0,
            'edges_exported': 0,
            'safety_violations': 0,
            'total_export_time_ms': 0
        }
    
    def validate_graph_safety(self, graph: KnowledgeGraph) -> bool:
        """Validate graph safety before export."""
        # Check minimum safety score
        if graph.min_safety_score < Decimal("0.8"):
            logger.warning(f"Graph minimum safety score too low: {graph.min_safety_score}")
            self._stats['safety_violations'] += 1
            return False
        
        # Check validation coverage
        if graph.validation_coverage < 0.9:
            logger.warning(f"Graph validation coverage too low: {graph.validation_coverage}")
            self._stats['safety_violations'] += 1
            return False
        
        return True


class MermaidExporter(GraphExporter):
    """
    Exports knowledge graphs as Mermaid diagrams.
    
    Generates flowchart and graph visualizations compatible with
    Mermaid.js for rendering in documentation.
    """
    
    def __init__(
        self,
        safety_validator: Optional[SafetyValidator] = None,
        max_nodes: int = 50,
        max_edges: int = 100
    ):
        """
        Initialize Mermaid exporter.
        
        Args:
            safety_validator: Safety validator
            max_nodes: Maximum nodes to include
            max_edges: Maximum edges to include
        """
        super().__init__(safety_validator)
        self.max_nodes = max_nodes
        self.max_edges = max_edges
        
        # Node type styling
        self.node_styles = {
            NodeType.MEMORY: "fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
            NodeType.CODE_FUNCTION: "fill:#f3e5f5,stroke:#4a148c,stroke-width:2px",
            NodeType.CODE_CLASS: "fill:#fce4ec,stroke:#880e4f,stroke-width:2px",
            NodeType.CODE_MODULE: "fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px",
            NodeType.CONCEPT: "fill:#fff3e0,stroke:#e65100,stroke-width:2px",
            NodeType.INTENT: "fill:#fafafa,stroke:#212121,stroke-width:2px",
            NodeType.CLUSTER: "fill:#e3f2fd,stroke:#0d47a1,stroke-width:3px",
            NodeType.TAG: "fill:#f5f5f5,stroke:#616161,stroke-width:1px"
        }
        
        # Edge type styling
        self.edge_styles = {
            EdgeType.SIMILAR_TO: "stroke:#2196f3,stroke-width:2px",
            EdgeType.RELATED_TO: "stroke:#4caf50,stroke-width:1px",
            EdgeType.FOLLOWS: "stroke:#ff9800,stroke-width:2px",
            EdgeType.DEPENDS_ON: "stroke:#f44336,stroke-width:2px",
            EdgeType.EXPLAINS: "stroke:#9c27b0,stroke-width:2px"
        }
    
    def export_graph(
        self,
        graph: KnowledgeGraph,
        diagram_type: str = "graph",
        direction: str = "TD",
        include_subgraphs: bool = True
    ) -> str:
        """
        Export graph as Mermaid diagram.
        
        Args:
            graph: Knowledge graph to export
            diagram_type: "graph" or "flowchart"
            direction: Graph direction (TD, LR, BT, RL)
            include_subgraphs: Whether to group by node type
            
        Returns:
            Mermaid diagram code
        """
        import time
        start_time = time.time()
        
        try:
            # Validate safety
            if not self.validate_graph_safety(graph):
                raise ValueError("Graph failed safety validation")
            
            # Start diagram
            lines = [f"{diagram_type} {direction}"]
            
            # Get nodes to export (limited)
            nodes_to_export = list(graph.nodes.values())[:self.max_nodes]
            node_ids_to_export = {n.node_id for n in nodes_to_export}
            
            # Group nodes by type if using subgraphs
            if include_subgraphs:
                nodes_by_type: Dict[NodeType, List[GraphNode]] = {}
                for node in nodes_to_export:
                    if node.node_type not in nodes_by_type:
                        nodes_by_type[node.node_type] = []
                    nodes_by_type[node.node_type].append(node)
                
                # Create subgraphs
                for node_type, type_nodes in nodes_by_type.items():
                    lines.append(f"    subgraph {node_type.value}")
                    for node in type_nodes:
                        lines.append(self._format_node(node))
                    lines.append("    end")
            else:
                # Add all nodes
                for node in nodes_to_export:
                    lines.append(self._format_node(node))
            
            # Add edges (limited)
            edges_added = 0
            for edge in graph.edges.values():
                if edges_added >= self.max_edges:
                    break
                
                # Only include edges between exported nodes
                if (edge.source_node_id in node_ids_to_export and 
                    edge.target_node_id in node_ids_to_export):
                    lines.append(self._format_edge(edge, graph))
                    edges_added += 1
            
            # Add styling
            lines.extend(self._generate_styles(nodes_to_export))
            
            # Update statistics
            self._stats['exports_performed'] += 1
            self._stats['nodes_exported'] += len(nodes_to_export)
            self._stats['edges_exported'] += edges_added
            self._stats['total_export_time_ms'] += (time.time() - start_time) * 1000
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Mermaid export failed: {e}")
            raise
    
    def export_subgraph(
        self,
        graph: KnowledgeGraph,
        center_node_id: str,
        depth: int = 2,
        max_neighbors: int = 10
    ) -> str:
        """
        Export a subgraph centered on a specific node.
        
        Args:
            graph: Knowledge graph
            center_node_id: Central node ID
            depth: Maximum depth to traverse
            max_neighbors: Maximum neighbors per node
            
        Returns:
            Mermaid diagram of subgraph
        """
        try:
            # Find nodes within depth
            nodes_to_include: Set[str] = {center_node_id}
            current_layer = {center_node_id}
            
            for _ in range(depth):
                next_layer = set()
                for node_id in current_layer:
                    neighbors = graph.get_neighbors(node_id)
                    for neighbor_id, _ in neighbors[:max_neighbors]:
                        next_layer.add(neighbor_id)
                        nodes_to_include.add(neighbor_id)
                current_layer = next_layer
            
            # Create subgraph
            subgraph = KnowledgeGraph(
                name=f"{graph.name}_subgraph",
                description=f"Subgraph centered on node {center_node_id}"
            )
            
            # Add nodes
            for node_id in nodes_to_include:
                if node_id in graph.nodes:
                    subgraph.add_node(graph.nodes[node_id])
            
            # Add edges
            for edge in graph.edges.values():
                if (edge.source_node_id in nodes_to_include and 
                    edge.target_node_id in nodes_to_include):
                    subgraph.add_edge(edge)
            
            # Export subgraph
            return self.export_graph(subgraph, include_subgraphs=False)
            
        except Exception as e:
            logger.error(f"Subgraph export failed: {e}")
            raise
    
    def _format_node(self, node: GraphNode) -> str:
        """Format a node for Mermaid."""
        # Create safe node ID
        node_id = f"node_{str(node.node_id).replace('-', '')[:8]}"
        
        # Format label (ensure safety)
        label = node.title_pattern
        if len(label) > 30:
            label = label[:27] + "..."
        
        # Choose shape based on type
        if node.node_type == NodeType.MEMORY:
            return f"    {node_id}[{label}]"
        elif node.node_type in [NodeType.CODE_FUNCTION, NodeType.CODE_CLASS]:
            return f"    {node_id}{{{label}}}"
        elif node.node_type == NodeType.CODE_MODULE:
            return f"    {node_id}[/{label}/]"
        elif node.node_type == NodeType.CLUSTER:
            return f"    {node_id}(({label}))"
        else:
            return f"    {node_id}[{label}]"
    
    def _format_edge(self, edge: GraphEdge, graph: KnowledgeGraph) -> str:
        """Format an edge for Mermaid."""
        # Create safe node IDs
        source_id = f"node_{str(edge.source_node_id).replace('-', '')[:8]}"
        target_id = f"node_{str(edge.target_node_id).replace('-', '')[:8]}"
        
        # Format label
        label = f"{edge.weight:.2f}"
        
        # Choose arrow style based on type
        if edge.edge_type == EdgeType.SIMILAR_TO:
            arrow = "-..-"
        elif edge.edge_type == EdgeType.DEPENDS_ON:
            arrow = "-->"
        elif edge.edge_type == EdgeType.FOLLOWS:
            arrow = "==>"
        else:
            arrow = "--"
        
        if edge.is_bidirectional:
            arrow = "<" + arrow + ">"
        else:
            arrow = arrow + ">"
        
        return f"    {source_id} {arrow}|{label}| {target_id}"
    
    def _generate_styles(self, nodes: List[GraphNode]) -> List[str]:
        """Generate style definitions."""
        lines = []
        
        # Generate class definitions for node types
        node_types_used = {node.node_type for node in nodes}
        
        for node_type in node_types_used:
            if node_type in self.node_styles:
                class_name = f"nodeType_{node_type.value}"
                lines.append(f"    classDef {class_name} {self.node_styles[node_type]}")
        
        # Apply classes to nodes
        for node_type in node_types_used:
            node_ids = [
                f"node_{str(n.node_id).replace('-', '')[:8]}"
                for n in nodes if n.node_type == node_type
            ]
            if node_ids:
                class_name = f"nodeType_{node_type.value}"
                lines.append(f"    class {','.join(node_ids)} {class_name}")
        
        return lines


class JSONExporter(GraphExporter):
    """
    Exports knowledge graphs as JSON for machine processing.
    
    Generates various JSON formats including D3.js compatible format.
    """
    
    def export_graph(
        self,
        graph: KnowledgeGraph,
        format_type: str = "standard",
        include_embeddings: bool = False,
        pretty_print: bool = True
    ) -> str:
        """
        Export graph as JSON.
        
        Args:
            graph: Knowledge graph to export
            format_type: "standard", "d3", or "cytoscape"
            include_embeddings: Whether to include embedding vectors
            pretty_print: Whether to format JSON
            
        Returns:
            JSON string
        """
        import time
        start_time = time.time()
        
        try:
            # Validate safety
            if not self.validate_graph_safety(graph):
                raise ValueError("Graph failed safety validation")
            
            if format_type == "standard":
                data = self._export_standard_format(graph, include_embeddings)
            elif format_type == "d3":
                data = self._export_d3_format(graph)
            elif format_type == "cytoscape":
                data = self._export_cytoscape_format(graph)
            else:
                raise ValueError(f"Unknown format type: {format_type}")
            
            # Update statistics
            self._stats['exports_performed'] += 1
            self._stats['nodes_exported'] += len(graph.nodes)
            self._stats['edges_exported'] += len(graph.edges)
            self._stats['total_export_time_ms'] += (time.time() - start_time) * 1000
            
            # Convert to JSON
            if pretty_print:
                return json.dumps(data, indent=2, default=str)
            else:
                return json.dumps(data, default=str)
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise
    
    def _export_standard_format(
        self,
        graph: KnowledgeGraph,
        include_embeddings: bool
    ) -> Dict[str, Any]:
        """Export in standard format."""
        data = {
            "graph": {
                "id": str(graph.graph_id),
                "name": graph.name,
                "description": graph.description,
                "created_at": graph.created_at.isoformat(),
                "updated_at": graph.updated_at.isoformat(),
                "metrics": graph.calculate_metrics()
            },
            "nodes": [],
            "edges": []
        }
        
        # Export nodes
        for node in graph.nodes.values():
            node_data = {
                "id": str(node.node_id),
                "type": node.node_type.value,
                "title": node.title_pattern,
                "description": node.description_pattern,
                "safety_score": float(node.safety_score),
                "created_at": node.created_at.isoformat(),
                "in_degree": node.in_degree,
                "out_degree": node.out_degree,
                "centrality_score": node.centrality_score
            }
            
            if include_embeddings and node.embedding:
                node_data["embedding"] = node.embedding
            
            data["nodes"].append(node_data)
        
        # Export edges
        for edge in graph.edges.values():
            edge_data = {
                "id": str(edge.edge_id),
                "source": str(edge.source_node_id),
                "target": str(edge.target_node_id),
                "type": edge.edge_type.value,
                "weight": edge.weight,
                "confidence": edge.confidence,
                "temporal_weight": edge.temporal_weight,
                "explanation": edge.explanation_pattern,
                "created_at": edge.created_at.isoformat()
            }
            
            data["edges"].append(edge_data)
        
        return data
    
    def _export_d3_format(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Export in D3.js force-directed graph format."""
        data = {
            "nodes": [],
            "links": []
        }
        
        # Create node index mapping
        node_index = {}
        
        # Export nodes with index
        for i, node in enumerate(graph.nodes.values()):
            node_index[node.node_id] = i
            
            data["nodes"].append({
                "id": str(node.node_id),
                "name": node.title_pattern,
                "group": node.node_type.value,
                "val": node.centrality_score * 10 + 1  # Node size
            })
        
        # Export edges as links
        for edge in graph.edges.values():
            if edge.source_node_id in node_index and edge.target_node_id in node_index:
                data["links"].append({
                    "source": node_index[edge.source_node_id],
                    "target": node_index[edge.target_node_id],
                    "value": edge.weight
                })
        
        return data
    
    def _export_cytoscape_format(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Export in Cytoscape.js format."""
        elements = []
        
        # Export nodes
        for node in graph.nodes.values():
            elements.append({
                "data": {
                    "id": str(node.node_id),
                    "label": node.title_pattern,
                    "type": node.node_type.value,
                    "safety_score": float(node.safety_score)
                }
            })
        
        # Export edges
        for edge in graph.edges.values():
            elements.append({
                "data": {
                    "id": str(edge.edge_id),
                    "source": str(edge.source_node_id),
                    "target": str(edge.target_node_id),
                    "weight": edge.weight,
                    "type": edge.edge_type.value
                }
            })
        
        return {"elements": elements}


class GraphMLExporter(GraphExporter):
    """
    Exports knowledge graphs as GraphML for network analysis tools.
    
    GraphML is an XML-based format supported by many graph analysis tools.
    """
    
    def export_graph(self, graph: KnowledgeGraph) -> str:
        """
        Export graph as GraphML XML.
        
        Args:
            graph: Knowledge graph to export
            
        Returns:
            GraphML XML string
        """
        import time
        import xml.etree.ElementTree as ET
        start_time = time.time()
        
        try:
            # Validate safety
            if not self.validate_graph_safety(graph):
                raise ValueError("Graph failed safety validation")
            
            # Create root element
            root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
            
            # Define attributes
            self._add_attribute_definitions(root)
            
            # Create graph element
            graph_elem = ET.SubElement(root, "graph", id=str(graph.graph_id), edgedefault="directed")
            
            # Add nodes
            for node in graph.nodes.values():
                node_elem = ET.SubElement(graph_elem, "node", id=str(node.node_id))
                ET.SubElement(node_elem, "data", key="label").text = node.title_pattern
                ET.SubElement(node_elem, "data", key="type").text = node.node_type.value
                ET.SubElement(node_elem, "data", key="safety_score").text = str(node.safety_score)
                ET.SubElement(node_elem, "data", key="centrality").text = str(node.centrality_score)
            
            # Add edges
            for edge in graph.edges.values():
                edge_elem = ET.SubElement(
                    graph_elem, "edge",
                    id=str(edge.edge_id),
                    source=str(edge.source_node_id),
                    target=str(edge.target_node_id)
                )
                ET.SubElement(edge_elem, "data", key="weight").text = str(edge.weight)
                ET.SubElement(edge_elem, "data", key="edge_type").text = edge.edge_type.value
            
            # Update statistics
            self._stats['exports_performed'] += 1
            self._stats['nodes_exported'] += len(graph.nodes)
            self._stats['edges_exported'] += len(graph.edges)
            self._stats['total_export_time_ms'] += (time.time() - start_time) * 1000
            
            # Convert to string
            return ET.tostring(root, encoding='unicode', method='xml')
            
        except Exception as e:
            logger.error(f"GraphML export failed: {e}")
            raise
    
    def _add_attribute_definitions(self, root):
        """Add GraphML attribute definitions."""
        # Node attributes
        ET.SubElement(root, "key", id="label", **{"for": "node", "attr.name": "label", "attr.type": "string"})
        ET.SubElement(root, "key", id="type", **{"for": "node", "attr.name": "type", "attr.type": "string"})
        ET.SubElement(root, "key", id="safety_score", **{"for": "node", "attr.name": "safety_score", "attr.type": "double"})
        ET.SubElement(root, "key", id="centrality", **{"for": "node", "attr.name": "centrality", "attr.type": "double"})
        
        # Edge attributes
        ET.SubElement(root, "key", id="weight", **{"for": "edge", "attr.name": "weight", "attr.type": "double"})
        ET.SubElement(root, "key", id="edge_type", **{"for": "edge", "attr.name": "edge_type", "attr.type": "string"})