"""
Unit tests for knowledge graph builder.

Tests graph construction, node extraction, edge detection, and
visualization export with safety validation.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
import tempfile
import math

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.services.vault.graph_builder import KnowledgeGraphBuilder
from src.services.vault.graph_models import (
    GraphNode, GraphEdge, KnowledgeGraph,
    NodeType, EdgeType, GraphQuery, GraphQueryResult
)
from src.services.vault.graph_exporters import MermaidExporter, JSONExporter
from src.core.memory.repository import SafeMemoryRepository
from src.core.memory.abstract_models import AbstractMemoryEntry, ValidationStatus
from src.core.analysis.ast_analyzer import ASTAnalyzer
from src.core.analysis.models import AnalysisResult, FunctionSignature, ClassStructure, LanguageType
from src.core.embeddings.service import EmbeddingService
from src.core.validation.validator import SafetyValidator


class TestGraphModels:
    """Test graph data models."""
    
    def test_graph_node_creation(self):
        """Test creating a graph node."""
        node = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<test_memory>",
            description_pattern="Test memory node",
            safety_score=Decimal("0.95")
        )
        
        assert node.node_type == NodeType.MEMORY
        assert node.title_pattern == "<test_memory>"
        assert node.safety_score == Decimal("0.95")
        assert node.is_validated is False
        assert node.is_safe_for_export() is False  # Not validated yet
    
    def test_graph_node_validation(self):
        """Test node safety validation."""
        # Should fail with low safety score
        with pytest.raises(ValueError):
            GraphNode(
                node_type=NodeType.MEMORY,
                title_pattern="<test>",
                safety_score=Decimal("0.5")  # Below minimum
            )
        
        # Should fail without title
        with pytest.raises(ValueError):
            GraphNode(
                node_type=NodeType.MEMORY,
                title_pattern="",
                safety_score=Decimal("0.9")
            )
    
    def test_graph_edge_creation(self):
        """Test creating a graph edge."""
        source_id = uuid4()
        target_id = uuid4()
        
        edge = GraphEdge(
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=EdgeType.SIMILAR_TO,
            weight=0.85,
            confidence=0.9
        )
        
        assert edge.source_node_id == source_id
        assert edge.target_node_id == target_id
        assert edge.edge_type == EdgeType.SIMILAR_TO
        assert edge.weight == 0.85
        assert edge.calculate_combined_weight() == 0.85 * 0.9 * 1.0
    
    def test_graph_edge_validation(self):
        """Test edge validation."""
        node_id = uuid4()
        
        # Should fail with self-loop
        with pytest.raises(ValueError):
            GraphEdge(
                source_node_id=node_id,
                target_node_id=node_id,
                edge_type=EdgeType.RELATED_TO
            )
        
        # Should fail with invalid weight
        with pytest.raises(ValueError):
            GraphEdge(
                source_node_id=uuid4(),
                target_node_id=uuid4(),
                weight=1.5  # Above maximum
            )
    
    def test_knowledge_graph_operations(self):
        """Test knowledge graph operations."""
        graph = KnowledgeGraph()
        
        # Add nodes
        node1 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_1>",
            is_validated=True
        )
        node2 = GraphNode(
            node_type=NodeType.CODE_FUNCTION,
            title_pattern="<function_1>",
            is_validated=True
        )
        
        graph.add_node(node1)
        graph.add_node(node2)
        
        assert graph.node_count == 2
        assert len(graph.nodes) == 2
        assert node1.node_id in graph.nodes
        
        # Add edge
        edge = GraphEdge(
            source_node_id=node1.node_id,
            target_node_id=node2.node_id,
            edge_type=EdgeType.EXPLAINS,
            weight=0.8
        )
        
        graph.add_edge(edge)
        
        assert graph.edge_count == 1
        assert len(graph.edges) == 1
        assert node1.out_degree == 1
        assert node2.in_degree == 1
        
        # Test neighbors
        neighbors = graph.get_neighbors(node1.node_id)
        assert len(neighbors) == 1
        assert neighbors[0][0] == node2.node_id
        
        # Test node type filtering
        memory_nodes = graph.get_nodes_by_type(NodeType.MEMORY)
        assert len(memory_nodes) == 1
        assert memory_nodes[0] == node1
        
        # Test metrics
        metrics = graph.calculate_metrics()
        assert metrics['node_count'] == 2
        assert metrics['edge_count'] == 1
        assert metrics['average_degree'] == 1.0


class TestKnowledgeGraphBuilder:
    """Test knowledge graph builder functionality."""
    
    @pytest.fixture
    def mock_memory_repository(self):
        """Create mock memory repository."""
        repo = Mock(spec=SafeMemoryRepository)
        
        # Create test memories
        test_memories = []
        for i in range(3):
            memory = Mock(spec=AbstractMemoryEntry)
            memory.memory_id = uuid4()
            memory.abstracted_prompt = f"<test_prompt_{i}>"
            memory.abstracted_response = f"<test_response_{i}>"
            memory.abstracted_content = {"test": True}
            memory.safety_score = Decimal("0.95")
            memory.validation_status = ValidationStatus.VALIDATED
            memory.created_at = datetime.now() - timedelta(hours=i)
            test_memories.append(memory)
        
        repo.get_memory = AsyncMock(side_effect=lambda id: test_memories[0])
        repo.search_with_clustering = AsyncMock(return_value=[
            {'memory_id': m.memory_id} for m in test_memories
        ])
        
        return repo
    
    @pytest.fixture
    def mock_ast_analyzer(self):
        """Create mock AST analyzer."""
        analyzer = Mock(spec=ASTAnalyzer)
        
        # Create mock analysis result
        result = Mock(spec=AnalysisResult)
        result.language = LanguageType.PYTHON
        result.functions = [
            FunctionSignature(
                name_pattern="<test_function>",
                parameter_count=2,
                return_type="str",
                is_async=False,
                docstring_present=True
            )
        ]
        result.classes = [
            ClassStructure(
                name_pattern="<test_class>",
                method_count=3,
                property_count=2,
                has_init=True
            )
        ]
        result.metadata = Mock(safety_score=0.95)
        result.aggregate_complexity = 5.0
        
        analyzer.analyze_code = AsyncMock(return_value=result)
        return analyzer
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = Mock(spec=EmbeddingService)
        
        # Generate random embeddings
        def generate_embedding(*args, **kwargs):
            result = Mock()
            result.vector = [0.1 * i for i in range(384)]  # 384-dim vector
            return result
        
        service.generate_embedding = AsyncMock(side_effect=generate_embedding)
        return service
    
    @pytest.fixture
    def graph_builder(self, mock_memory_repository, mock_ast_analyzer, mock_embedding_service):
        """Create graph builder with mocks."""
        return KnowledgeGraphBuilder(
            memory_repository=mock_memory_repository,
            ast_analyzer=mock_ast_analyzer,
            embedding_service=mock_embedding_service,
            safety_validator=SafetyValidator()
        )
    
    @pytest.mark.asyncio
    async def test_build_graph_from_memories(self, graph_builder):
        """Test building graph from memories."""
        graph = await graph_builder.build_graph(
            max_memories=3,
            include_related=False
        )
        
        # Should have memory nodes
        assert graph.node_count >= 3
        memory_nodes = graph.get_nodes_by_type(NodeType.MEMORY)
        assert len(memory_nodes) >= 3
        
        # Should have edges (semantic and temporal)
        assert graph.edge_count > 0
        
        # Check node properties
        for node in memory_nodes:
            assert node.safety_score >= Decimal("0.8")
            assert node.is_validated
            assert node.embedding is not None
    
    @pytest.mark.asyncio
    async def test_build_graph_from_code(self, graph_builder):
        """Test building graph from code files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test Python file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def test_function(a: int, b: str) -> str:
    \"\"\"Test function.\"\"\"
    return f"{a}: {b}"

class TestClass:
    def __init__(self):
        self.value = 0
    
    def method1(self):
        pass
    
    def method2(self):
        pass
""")
            
            graph = await graph_builder.build_graph(
                code_paths=[test_file]
            )
            
            # Should have code nodes
            code_nodes = (
                graph.get_nodes_by_type(NodeType.CODE_MODULE) +
                graph.get_nodes_by_type(NodeType.CODE_FUNCTION) +
                graph.get_nodes_by_type(NodeType.CODE_CLASS)
            )
            assert len(code_nodes) >= 3  # Module, function, class
            
            # Check safety compliance
            for node in code_nodes:
                assert node.safety_score >= Decimal("0.8")
                assert node.is_validated
    
    @pytest.mark.asyncio
    async def test_semantic_edge_detection(self, graph_builder):
        """Test semantic similarity edge detection."""
        # Create nodes with embeddings
        node1 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_1>",
            embedding=[1.0, 0.0, 0.0],
            is_validated=True
        )
        node2 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_2>",
            embedding=[0.9, 0.1, 0.0],  # Very similar
            is_validated=True
        )
        node3 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_3>",
            embedding=[0.0, 0.0, 1.0],  # Very different
            is_validated=True
        )
        
        graph = KnowledgeGraph()
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        
        # Detect semantic edges
        edges = await graph_builder._detect_semantic_edges(graph)
        
        # Should find edge between similar nodes
        similar_edges = [
            e for e in edges
            if (e.source_node_id == node1.node_id and e.target_node_id == node2.node_id) or
               (e.source_node_id == node2.node_id and e.target_node_id == node1.node_id)
        ]
        assert len(similar_edges) > 0
        assert similar_edges[0].weight > 0.9  # High similarity
        
        # Should not find edge between different nodes
        different_edges = [
            e for e in edges
            if node3.node_id in [e.source_node_id, e.target_node_id]
        ]
        assert len(different_edges) == 0
    
    @pytest.mark.asyncio
    async def test_temporal_edge_detection(self, graph_builder):
        """Test temporal proximity edge detection."""
        now = datetime.now()
        
        # Create nodes with timestamps
        node1 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_1>",
            created_at=now,
            is_validated=True
        )
        node2 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_2>",
            created_at=now + timedelta(hours=2),  # Close in time
            is_validated=True
        )
        node3 = GraphNode(
            node_type=NodeType.MEMORY,
            title_pattern="<memory_3>",
            created_at=now + timedelta(days=7),  # Far in time
            is_validated=True
        )
        
        graph = KnowledgeGraph()
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        
        # Detect temporal edges
        edges = await graph_builder._detect_temporal_edges(graph)
        
        # Should find edge between temporally close nodes
        close_edges = [
            e for e in edges
            if e.source_node_id == node1.node_id and e.target_node_id == node2.node_id
        ]
        assert len(close_edges) > 0
        assert close_edges[0].edge_type == EdgeType.FOLLOWS
        assert close_edges[0].temporal_distance_hours == pytest.approx(2.0, rel=0.1)
        
        # Should not find edge between temporally distant nodes
        distant_edges = [
            e for e in edges
            if (e.source_node_id == node1.node_id and e.target_node_id == node3.node_id) or
               (e.source_node_id == node2.node_id and e.target_node_id == node3.node_id)
        ]
        assert len(distant_edges) == 0
    
    @pytest.mark.asyncio
    async def test_graph_query(self, graph_builder):
        """Test graph querying functionality."""
        # Build a graph
        graph = await graph_builder.build_graph(max_memories=5)
        
        # Query by node type
        query = GraphQuery(
            node_types=[NodeType.MEMORY],
            min_node_safety_score=0.8,
            max_nodes=10
        )
        
        result = await graph_builder.query_graph(graph, query)
        
        assert isinstance(result, GraphQueryResult)
        assert len(result.nodes) <= 10
        assert all(n.node_type == NodeType.MEMORY for n in result.nodes)
        assert all(float(n.safety_score) >= 0.8 for n in result.nodes)
        assert result.query_time_ms > 0
    
    def test_cosine_similarity(self, graph_builder):
        """Test cosine similarity calculation."""
        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        similarity = graph_builder._cosine_similarity(vec1, vec1)
        assert similarity == pytest.approx(1.0)
        
        # Test orthogonal vectors
        vec2 = [0.0, 1.0, 0.0]
        similarity = graph_builder._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)
        
        # Test similar vectors
        vec3 = [0.9, 0.1, 0.0]
        similarity = graph_builder._cosine_similarity(vec1, vec3)
        assert similarity > 0.9
    
    def test_temporal_weight_calculation(self, graph_builder):
        """Test temporal weight calculation."""
        now = datetime.now()
        
        # Same time
        weight, hours = graph_builder._calculate_temporal_weight(now, now)
        assert weight == pytest.approx(1.0)
        assert hours == pytest.approx(0.0)
        
        # 24 hours apart
        later = now + timedelta(hours=24)
        weight, hours = graph_builder._calculate_temporal_weight(now, later)
        assert weight < 1.0
        assert weight > 0.8
        assert hours == pytest.approx(24.0)
        
        # Very far apart
        much_later = now + timedelta(days=30)
        weight, hours = graph_builder._calculate_temporal_weight(now, much_later)
        assert weight < 0.1
        assert hours == pytest.approx(720.0, rel=0.1)


class TestGraphExporters:
    """Test graph visualization exporters."""
    
    @pytest.fixture
    def sample_graph(self):
        """Create a sample graph for testing."""
        graph = KnowledgeGraph()
        
        # Add nodes
        nodes = [
            GraphNode(
                node_type=NodeType.MEMORY,
                title_pattern="<memory_node>",
                is_validated=True
            ),
            GraphNode(
                node_type=NodeType.CODE_FUNCTION,
                title_pattern="<function_node>",
                is_validated=True
            ),
            GraphNode(
                node_type=NodeType.CONCEPT,
                title_pattern="<concept_node>",
                is_validated=True
            )
        ]
        
        for node in nodes:
            graph.add_node(node)
        
        # Add edges
        edges = [
            GraphEdge(
                source_node_id=nodes[0].node_id,
                target_node_id=nodes[1].node_id,
                edge_type=EdgeType.EXPLAINS,
                weight=0.8
            ),
            GraphEdge(
                source_node_id=nodes[1].node_id,
                target_node_id=nodes[2].node_id,
                edge_type=EdgeType.RELATED_TO,
                weight=0.6
            )
        ]
        
        for edge in edges:
            graph.add_edge(edge)
        
        return graph
    
    def test_mermaid_export(self, sample_graph):
        """Test Mermaid diagram export."""
        exporter = MermaidExporter()
        
        mermaid_code = exporter.export_graph(
            sample_graph,
            diagram_type="graph",
            direction="TD"
        )
        
        assert "graph TD" in mermaid_code
        assert "<memory_node>" in mermaid_code
        assert "<function_node>" in mermaid_code
        assert "<concept_node>" in mermaid_code
        assert "-->" in mermaid_code  # Edge indicator
        assert "0.8" in mermaid_code  # Edge weight
    
    def test_mermaid_subgraph_export(self, sample_graph):
        """Test Mermaid subgraph export."""
        exporter = MermaidExporter()
        
        # Get first node ID
        center_node_id = list(sample_graph.nodes.keys())[0]
        
        mermaid_code = exporter.export_subgraph(
            sample_graph,
            str(center_node_id),
            depth=1,
            max_neighbors=5
        )
        
        assert "graph TD" in mermaid_code
        assert "<memory_node>" in mermaid_code
        assert "<function_node>" in mermaid_code  # Should be included as neighbor
    
    def test_json_export_standard(self, sample_graph):
        """Test JSON export in standard format."""
        exporter = JSONExporter()
        
        json_str = exporter.export_graph(
            sample_graph,
            format_type="standard",
            include_embeddings=False,
            pretty_print=True
        )
        
        import json
        data = json.loads(json_str)
        
        assert "graph" in data
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        assert data["graph"]["metrics"]["node_count"] == 3
    
    def test_json_export_d3(self, sample_graph):
        """Test JSON export in D3.js format."""
        exporter = JSONExporter()
        
        json_str = exporter.export_graph(
            sample_graph,
            format_type="d3"
        )
        
        import json
        data = json.loads(json_str)
        
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) == 3
        assert len(data["links"]) == 2
        assert "group" in data["nodes"][0]
        assert "value" in data["links"][0]
    
    def test_export_safety_validation(self):
        """Test safety validation in exports."""
        # Create graph with low safety score
        graph = KnowledgeGraph()
        graph.min_safety_score = Decimal("0.5")  # Below threshold
        
        exporter = MermaidExporter()
        
        with pytest.raises(ValueError, match="safety validation"):
            exporter.export_graph(graph)


class TestPerformance:
    """Performance tests for graph operations."""
    
    @pytest.mark.asyncio
    async def test_graph_build_performance(self):
        """Test graph building performance."""
        # Create mock repository with many memories
        repo = Mock(spec=SafeMemoryRepository)
        memories = []
        
        for i in range(100):
            memory = Mock(spec=AbstractMemoryEntry)
            memory.memory_id = uuid4()
            memory.abstracted_prompt = f"<prompt_{i}>"
            memory.abstracted_response = f"<response_{i}>"
            memory.safety_score = Decimal("0.95")
            memory.validation_status = ValidationStatus.VALIDATED
            memory.created_at = datetime.now() - timedelta(hours=i)
            memories.append(memory)
        
        repo.search_with_clustering = AsyncMock(return_value=[
            {'memory_id': m.memory_id} for m in memories
        ])
        repo.get_memory = AsyncMock(side_effect=lambda id: memories[0])
        
        # Create builder without embedding service for speed
        builder = KnowledgeGraphBuilder(
            memory_repository=repo,
            embedding_service=None,  # Skip embeddings for performance test
            enable_temporal_weighting=True
        )
        
        import time
        start = time.time()
        
        graph = await builder.build_graph(max_memories=100)
        
        build_time = (time.time() - start) * 1000
        
        # Should complete within reasonable time
        assert build_time < 1000  # Less than 1 second
        assert graph.node_count >= 100
        assert graph.build_time_ms < 1000
    
    def test_query_performance(self):
        """Test graph query performance."""
        # Create large graph
        graph = KnowledgeGraph()
        
        # Add many nodes
        for i in range(1000):
            node = GraphNode(
                node_type=NodeType.MEMORY if i % 2 == 0 else NodeType.CODE_FUNCTION,
                title_pattern=f"<node_{i}>",
                is_validated=True,
                created_at=datetime.now() - timedelta(hours=i)
            )
            graph.add_node(node)
        
        # Query with filters
        query = GraphQuery(
            node_types=[NodeType.MEMORY],
            min_node_safety_score=0.8,
            max_nodes=100
        )
        
        builder = KnowledgeGraphBuilder(
            memory_repository=Mock(),
            embedding_service=None
        )
        
        import time
        start = time.time()
        
        result = asyncio.run(builder.query_graph(graph, query))
        
        query_time = (time.time() - start) * 1000
        
        # Should be fast
        assert query_time < 50  # Less than 50ms
        assert len(result.nodes) <= 100
        assert result.query_time_ms < 50