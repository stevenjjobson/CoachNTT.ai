"""
Data models for knowledge graph representation with safety-first design.

Provides node and edge structures for building semantic knowledge graphs
from memories, code analysis, and intent connections.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal

from ...core.safety.models import MIN_SAFETY_SCORE


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""
    MEMORY = "memory"
    CODE_FUNCTION = "code_function"
    CODE_CLASS = "code_class"
    CODE_MODULE = "code_module"
    CONCEPT = "concept"
    INTENT = "intent"
    CLUSTER = "cluster"
    TAG = "tag"
    PATTERN = "pattern"


class EdgeType(Enum):
    """Types of edges/relationships in the knowledge graph."""
    # Semantic relationships
    SIMILAR_TO = "similar_to"
    RELATED_TO = "related_to"
    EXPLAINS = "explains"
    CONTRADICTS = "contradicts"
    
    # Temporal relationships
    FOLLOWS = "follows"
    PRECEDES = "precedes"
    CONCURRENT_WITH = "concurrent_with"
    
    # Code relationships
    CALLS = "calls"
    IMPORTS = "imports"
    INHERITS_FROM = "inherits_from"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    
    # Intent relationships
    ANSWERS = "answers"
    ELABORATES = "elaborates"
    REFINES = "refines"
    
    # Cluster relationships
    MEMBER_OF = "member_of"
    REPRESENTATIVE_OF = "representative_of"


@dataclass
class GraphNode:
    """
    Represents a node in the knowledge graph.
    
    All content must be abstracted for safety compliance.
    """
    node_id: UUID = field(default_factory=uuid4)
    node_type: NodeType = NodeType.MEMORY
    content_hash: str = ""
    
    # Abstracted content
    title_pattern: str = ""
    description_pattern: str = ""
    abstracted_content: Dict[str, Any] = field(default_factory=dict)
    
    # Source information
    source_id: Optional[UUID] = None  # Memory ID, code hash, etc.
    source_type: str = ""  # "memory", "ast_analysis", "intent_analysis"
    source_file: Optional[str] = None  # For code nodes
    
    # Safety and validation
    safety_score: Decimal = Decimal("1.0")
    is_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Graph properties
    in_degree: int = 0  # Number of incoming edges
    out_degree: int = 0  # Number of outgoing edges
    centrality_score: float = 0.0
    
    # Embedding vector (optional)
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    
    def __post_init__(self):
        """Validate node after initialization."""
        if self.safety_score < MIN_SAFETY_SCORE:
            raise ValueError(
                f"Node safety score {self.safety_score} below minimum {MIN_SAFETY_SCORE}"
            )
        
        if not self.title_pattern:
            raise ValueError("Node must have a title pattern")
    
    def is_safe_for_export(self) -> bool:
        """Check if node is safe for external export."""
        return (
            self.is_validated and
            self.safety_score >= MIN_SAFETY_SCORE and
            len(self.validation_errors) == 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'node_id': str(self.node_id),
            'node_type': self.node_type.value,
            'title_pattern': self.title_pattern,
            'description_pattern': self.description_pattern,
            'safety_score': float(self.safety_score),
            'created_at': self.created_at.isoformat(),
            'in_degree': self.in_degree,
            'out_degree': self.out_degree,
            'centrality_score': self.centrality_score
        }


@dataclass
class GraphEdge:
    """
    Represents an edge/relationship between nodes in the knowledge graph.
    
    All explanations must be abstracted for safety compliance.
    """
    edge_id: UUID = field(default_factory=uuid4)
    source_node_id: UUID = field(default_factory=uuid4)
    target_node_id: UUID = field(default_factory=uuid4)
    edge_type: EdgeType = EdgeType.RELATED_TO
    
    # Relationship strength and confidence
    weight: float = 0.5  # 0.0 to 1.0
    confidence: float = 0.8  # Confidence in the relationship
    
    # Temporal properties
    temporal_distance_hours: Optional[float] = None
    temporal_weight: float = 1.0
    
    # Explanation (must be abstracted)
    explanation_pattern: str = ""
    reasoning: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Safety and validation
    safety_score: Decimal = Decimal("1.0")
    is_validated: bool = False
    is_bidirectional: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"  # "system", "user", "inference"
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate edge after initialization."""
        if self.source_node_id == self.target_node_id:
            raise ValueError("Self-loops not allowed in knowledge graph")
        
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Edge weight {self.weight} must be between 0 and 1")
        
        if self.safety_score < MIN_SAFETY_SCORE:
            raise ValueError(
                f"Edge safety score {self.safety_score} below minimum {MIN_SAFETY_SCORE}"
            )
    
    def calculate_combined_weight(self) -> float:
        """Calculate combined weight including temporal factors."""
        base_weight = self.weight * self.confidence
        return base_weight * self.temporal_weight
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'edge_id': str(self.edge_id),
            'source_node_id': str(self.source_node_id),
            'target_node_id': str(self.target_node_id),
            'edge_type': self.edge_type.value,
            'weight': self.weight,
            'confidence': self.confidence,
            'temporal_weight': self.temporal_weight,
            'explanation_pattern': self.explanation_pattern,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class KnowledgeGraph:
    """
    Main knowledge graph structure containing nodes and edges.
    
    Provides methods for graph manipulation and analysis.
    """
    graph_id: UUID = field(default_factory=uuid4)
    name: str = "knowledge_graph"
    description: str = "Safety-validated knowledge graph"
    
    # Graph components
    nodes: Dict[UUID, GraphNode] = field(default_factory=dict)
    edges: Dict[UUID, GraphEdge] = field(default_factory=dict)
    
    # Indexes for efficient lookups
    node_type_index: Dict[NodeType, Set[UUID]] = field(default_factory=dict)
    edge_type_index: Dict[EdgeType, Set[UUID]] = field(default_factory=dict)
    adjacency_list: Dict[UUID, Dict[UUID, UUID]] = field(default_factory=dict)  # source -> target -> edge_id
    
    # Graph metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    node_count: int = 0
    edge_count: int = 0
    
    # Performance metrics
    build_time_ms: float = 0.0
    last_query_time_ms: float = 0.0
    
    # Safety metrics
    average_safety_score: Decimal = Decimal("1.0")
    min_safety_score: Decimal = Decimal("1.0")
    validation_coverage: float = 1.0  # Percentage of validated nodes/edges
    
    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        if not node.is_safe_for_export():
            raise ValueError(f"Node {node.node_id} failed safety validation")
        
        self.nodes[node.node_id] = node
        
        # Update indexes
        if node.node_type not in self.node_type_index:
            self.node_type_index[node.node_type] = set()
        self.node_type_index[node.node_type].add(node.node_id)
        
        # Initialize adjacency list entry
        if node.node_id not in self.adjacency_list:
            self.adjacency_list[node.node_id] = {}
        
        self.node_count += 1
        self.updated_at = datetime.now()
    
    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        # Verify nodes exist
        if edge.source_node_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_node_id} not found")
        if edge.target_node_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_node_id} not found")
        
        self.edges[edge.edge_id] = edge
        
        # Update indexes
        if edge.edge_type not in self.edge_type_index:
            self.edge_type_index[edge.edge_type] = set()
        self.edge_type_index[edge.edge_type].add(edge.edge_id)
        
        # Update adjacency list
        if edge.source_node_id not in self.adjacency_list:
            self.adjacency_list[edge.source_node_id] = {}
        self.adjacency_list[edge.source_node_id][edge.target_node_id] = edge.edge_id
        
        # Update node degrees
        self.nodes[edge.source_node_id].out_degree += 1
        self.nodes[edge.target_node_id].in_degree += 1
        
        # Handle bidirectional edges
        if edge.is_bidirectional:
            if edge.target_node_id not in self.adjacency_list:
                self.adjacency_list[edge.target_node_id] = {}
            self.adjacency_list[edge.target_node_id][edge.source_node_id] = edge.edge_id
            self.nodes[edge.target_node_id].out_degree += 1
            self.nodes[edge.source_node_id].in_degree += 1
        
        self.edge_count += 1
        self.updated_at = datetime.now()
    
    def get_neighbors(self, node_id: UUID) -> List[Tuple[UUID, GraphEdge]]:
        """Get all neighboring nodes and connecting edges."""
        neighbors = []
        
        # Outgoing edges
        if node_id in self.adjacency_list:
            for target_id, edge_id in self.adjacency_list[node_id].items():
                neighbors.append((target_id, self.edges[edge_id]))
        
        # Incoming edges (for bidirectional or explicit incoming)
        for source_id, targets in self.adjacency_list.items():
            if node_id in targets and source_id != node_id:
                edge_id = targets[node_id]
                edge = self.edges[edge_id]
                if edge.is_bidirectional or edge.target_node_id == node_id:
                    neighbors.append((source_id, edge))
        
        return neighbors
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Get all nodes of a specific type."""
        node_ids = self.node_type_index.get(node_type, set())
        return [self.nodes[node_id] for node_id in node_ids]
    
    def get_edges_by_type(self, edge_type: EdgeType) -> List[GraphEdge]:
        """Get all edges of a specific type."""
        edge_ids = self.edge_type_index.get(edge_type, set())
        return [self.edges[edge_id] for edge_id in edge_ids]
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate graph metrics and statistics."""
        if not self.nodes:
            return {
                'node_count': 0,
                'edge_count': 0,
                'average_degree': 0,
                'density': 0,
                'connected_components': 0
            }
        
        total_degree = sum(node.in_degree + node.out_degree for node in self.nodes.values())
        average_degree = total_degree / len(self.nodes) if self.nodes else 0
        
        # Calculate density (actual edges / possible edges)
        max_edges = len(self.nodes) * (len(self.nodes) - 1)
        density = self.edge_count / max_edges if max_edges > 0 else 0
        
        # Calculate safety metrics
        safety_scores = [node.safety_score for node in self.nodes.values()]
        safety_scores.extend([edge.safety_score for edge in self.edges.values()])
        
        self.average_safety_score = (
            sum(safety_scores) / len(safety_scores) 
            if safety_scores else Decimal("1.0")
        )
        self.min_safety_score = min(safety_scores) if safety_scores else Decimal("1.0")
        
        validated_items = (
            sum(1 for node in self.nodes.values() if node.is_validated) +
            sum(1 for edge in self.edges.values() if edge.is_validated)
        )
        total_items = len(self.nodes) + len(self.edges)
        self.validation_coverage = validated_items / total_items if total_items > 0 else 1.0
        
        return {
            'node_count': self.node_count,
            'edge_count': self.edge_count,
            'average_degree': average_degree,
            'density': density,
            'average_safety_score': float(self.average_safety_score),
            'min_safety_score': float(self.min_safety_score),
            'validation_coverage': self.validation_coverage,
            'node_types': {nt.value: len(nodes) for nt, nodes in self.node_type_index.items()},
            'edge_types': {et.value: len(edges) for et, edges in self.edge_type_index.items()}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization."""
        return {
            'graph_id': str(self.graph_id),
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metrics': self.calculate_metrics(),
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [edge.to_dict() for edge in self.edges.values()]
        }


@dataclass
class GraphQuery:
    """Query parameters for filtering and searching the knowledge graph."""
    # Node filters
    node_types: Optional[List[NodeType]] = None
    min_node_safety_score: float = 0.8
    node_created_after: Optional[datetime] = None
    node_content_pattern: Optional[str] = None
    
    # Edge filters
    edge_types: Optional[List[EdgeType]] = None
    min_edge_weight: float = 0.0
    min_edge_confidence: float = 0.0
    
    # Graph traversal
    start_node_id: Optional[UUID] = None
    max_depth: int = 3
    follow_edge_types: Optional[List[EdgeType]] = None
    
    # Result limits
    max_nodes: int = 100
    max_edges: int = 200
    include_neighbors: bool = True
    
    # Sorting
    sort_by: str = "centrality"  # "centrality", "created_at", "safety_score"
    sort_descending: bool = True


@dataclass
class GraphQueryResult:
    """Results from a graph query."""
    query: GraphQuery
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    subgraph: Optional[KnowledgeGraph] = None
    
    # Query metadata
    query_time_ms: float = 0.0
    nodes_examined: int = 0
    edges_examined: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'node_count': len(self.nodes),
            'edge_count': len(self.edges),
            'query_time_ms': self.query_time_ms,
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': [edge.to_dict() for edge in self.edges]
        }