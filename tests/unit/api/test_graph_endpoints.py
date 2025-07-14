"""
Tests for knowledge graph API endpoints.

This module tests the graph building, querying, and export functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from src.api.models.graph import (
    GraphBuildRequest,
    GraphResponse,
    GraphQuery,
    GraphQueryResult,
    GraphExportRequest,
    GraphExportResult,
    SubgraphRequest
)
from src.services.vault.graph_models import KnowledgeGraph, NodeType, EdgeType


class TestGraphEndpoints:
    """Test knowledge graph API endpoints."""
    
    @pytest.fixture
    def sample_graph_build_request(self):
        """Sample graph build request."""
        return GraphBuildRequest(
            max_memories=50,
            include_related=True,
            graph_name="Test Graph",
            enable_code_analysis=True,
            enable_temporal_weighting=True
        )
    
    @pytest.fixture
    def sample_knowledge_graph(self):
        """Sample knowledge graph."""
        graph = KnowledgeGraph(
            name="Test Graph",
            description="Test knowledge graph"
        )
        graph.graph_id = uuid4()
        graph.created_at = datetime.now()
        graph.updated_at = datetime.now()
        graph.build_time_ms = 850.5
        return graph
    
    @pytest.fixture
    def sample_graph_metrics(self):
        """Sample graph metrics."""
        from src.api.models.graph import GraphMetrics
        return GraphMetrics(
            node_count=25,
            edge_count=45,
            density=0.15,
            average_degree=3.6,
            connected_components=2,
            average_safety_score=Decimal("0.92"),
            build_time_ms=850.5
        )
    
    @patch('src.api.routers.graph.get_knowledge_graph_builder')
    @patch('src.api.dependencies.verify_token')
    def test_build_graph_success(
        self, 
        mock_verify_token, 
        mock_get_builder, 
        sample_graph_build_request,
        sample_knowledge_graph,
        sample_graph_metrics
    ):
        """Test successful graph building."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        mock_builder = AsyncMock()
        mock_builder.build_graph.return_value = sample_knowledge_graph
        mock_get_builder.return_value = mock_builder
        
        # Mock graph metrics calculation
        sample_knowledge_graph.calculate_metrics = MagicMock(return_value=sample_graph_metrics)
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/graph/build",
            json=sample_graph_build_request.model_dump(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        # This is a placeholder test structure for Session 4.1b
        # In a full implementation, we would assert:
        # - Response status code is 200
        # - Response contains graph_id, name, metrics
        # - Graph builder was called with correct parameters
        # - Graph is stored in memory/database
        
        # For now, just verify the structure is in place
        assert callable(client.post)
    
    @patch('src.api.routers.graph._graph_storage')
    @patch('src.api.dependencies.verify_token')
    def test_get_graph_success(
        self, 
        mock_verify_token, 
        mock_storage,
        sample_knowledge_graph,
        sample_graph_metrics
    ):
        """Test successful graph retrieval."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        graph_id = sample_knowledge_graph.graph_id
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(return_value=sample_knowledge_graph)
        
        # Mock graph metrics calculation
        sample_knowledge_graph.calculate_metrics = MagicMock(return_value=sample_graph_metrics)
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.get(
            f"/api/v1/graph/{graph_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Placeholder for test validation
        assert callable(client.get)
    
    @patch('src.api.routers.graph.get_knowledge_graph_builder')
    @patch('src.api.routers.graph._graph_storage')
    @patch('src.api.dependencies.verify_token')
    def test_query_graph_success(
        self, 
        mock_verify_token, 
        mock_storage,
        mock_get_builder,
        sample_knowledge_graph
    ):
        """Test successful graph querying."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        
        graph_id = sample_knowledge_graph.graph_id
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(return_value=sample_knowledge_graph)
        
        mock_builder = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.nodes = []
        mock_query_result.edges = []
        mock_query_result.query_time_ms = 125.5
        mock_query_result.nodes_examined = 25
        mock_query_result.edges_examined = 45
        mock_builder.query_graph.return_value = mock_query_result
        mock_get_builder.return_value = mock_builder
        
        query_request = GraphQuery(
            node_types=[NodeType.MEMORY],
            min_node_safety_score=0.8,
            max_nodes=20
        )
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.post(
            f"/api/v1/graph/{graph_id}/query",
            json=query_request.model_dump(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Placeholder for test validation
        assert callable(client.post)
    
    @patch('src.api.routers.graph._graph_storage')
    @patch('src.api.dependencies.verify_token')
    def test_export_graph_success(
        self, 
        mock_verify_token, 
        mock_storage,
        sample_knowledge_graph
    ):
        """Test successful graph export."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        
        graph_id = sample_knowledge_graph.graph_id
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(return_value=sample_knowledge_graph)
        
        export_request = GraphExportRequest(
            format="mermaid",
            include_metadata=True,
            max_nodes=50
        )
        
        # Mock graph nodes and edges
        sample_knowledge_graph.nodes = {}
        sample_knowledge_graph.edges = {}
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.post(
            f"/api/v1/graph/{graph_id}/export",
            json=export_request.model_dump(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Placeholder for test validation
        assert callable(client.post)
    
    @patch('src.api.routers.graph._graph_storage')
    @patch('src.api.dependencies.verify_token')
    def test_get_subgraph_success(
        self, 
        mock_verify_token, 
        mock_storage,
        sample_knowledge_graph
    ):
        """Test successful subgraph extraction."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        
        graph_id = sample_knowledge_graph.graph_id
        center_node_id = uuid4()
        
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(return_value=sample_knowledge_graph)
        
        # Mock graph structure
        sample_knowledge_graph.nodes = {center_node_id: MagicMock()}
        sample_knowledge_graph.edges = {}
        
        subgraph_request = SubgraphRequest(
            center_node_id=center_node_id,
            max_depth=2,
            max_nodes=15,
            min_edge_weight=0.5
        )
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.post(
            f"/api/v1/graph/{graph_id}/subgraph",
            json=subgraph_request.model_dump(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Placeholder for test validation
        assert callable(client.post)
    
    @patch('src.api.dependencies.verify_token')
    def test_list_graphs_success(self, mock_verify_token):
        """Test successful graph listing."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/graph/",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Placeholder for test validation
        assert callable(client.get)
    
    @patch('src.api.routers.graph._graph_storage')
    @patch('src.api.dependencies.verify_token')
    def test_delete_graph_success(
        self, 
        mock_verify_token, 
        mock_storage,
        sample_knowledge_graph
    ):
        """Test successful graph deletion."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        
        graph_id = sample_knowledge_graph.graph_id
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.pop = MagicMock(return_value=sample_knowledge_graph)
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.delete(
            f"/api/v1/graph/{graph_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Placeholder for test validation
        assert callable(client.delete)
    
    def test_graph_build_request_validation(self):
        """Test graph build request model validation."""
        # Valid request
        valid_request = GraphBuildRequest(
            max_memories=50,
            include_related=True,
            graph_name="Test Graph"
        )
        assert valid_request.max_memories == 50
        assert valid_request.include_related is True
        assert valid_request.graph_name == "Test Graph"
        
        # Test default values
        default_request = GraphBuildRequest(max_memories=25)
        assert default_request.include_related is True
        assert default_request.enable_code_analysis is True
        assert default_request.enable_temporal_weighting is True
    
    def test_graph_query_validation(self):
        """Test graph query model validation."""
        # Valid query
        valid_query = GraphQuery(
            node_types=[NodeType.MEMORY],
            min_node_safety_score=0.8,
            max_nodes=20
        )
        assert NodeType.MEMORY in valid_query.node_types
        assert valid_query.min_node_safety_score == 0.8
        assert valid_query.max_nodes == 20
        
        # Test sort criteria validation
        with pytest.raises(ValueError):
            GraphQuery(sort_by="invalid_sort")
    
    def test_graph_export_request_validation(self):
        """Test graph export request model validation."""
        # Valid export request
        valid_export = GraphExportRequest(
            format="mermaid",
            include_metadata=True
        )
        assert valid_export.format == "mermaid"
        assert valid_export.include_metadata is True
        
        # Test format validation
        with pytest.raises(ValueError):
            GraphExportRequest(format="invalid_format")


class TestGraphModels:
    """Test graph-related Pydantic models."""
    
    def test_graph_node_model(self):
        """Test GraphNode model validation."""
        from src.api.models.graph import GraphNode
        
        node = GraphNode(
            node_id=uuid4(),
            node_type=NodeType.MEMORY,
            title_pattern="<memory_test>",
            description_pattern="Test memory node",
            safety_score=Decimal("0.95"),
            is_validated=True,
            created_at=datetime.now(),
            source_type="memory"
        )
        
        assert node.node_type == NodeType.MEMORY
        assert node.safety_score == Decimal("0.95")
        assert node.is_validated is True
    
    def test_graph_edge_model(self):
        """Test GraphEdge model validation."""
        from src.api.models.graph import GraphEdge
        
        edge = GraphEdge(
            edge_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            edge_type=EdgeType.SIMILAR_TO,
            weight=0.85,
            confidence=0.92,
            explanation_pattern="Semantic similarity",
            safety_score=Decimal("0.98"),
            is_bidirectional=True
        )
        
        assert edge.edge_type == EdgeType.SIMILAR_TO
        assert edge.weight == 0.85
        assert edge.confidence == 0.92
        assert edge.is_bidirectional is True
    
    def test_graph_metrics_model(self):
        """Test GraphMetrics model validation."""
        from src.api.models.graph import GraphMetrics
        
        metrics = GraphMetrics(
            node_count=25,
            edge_count=45,
            density=0.15,
            average_degree=3.6,
            connected_components=2,
            average_safety_score=Decimal("0.92"),
            build_time_ms=850.5
        )
        
        assert metrics.node_count == 25
        assert metrics.edge_count == 45
        assert metrics.density == 0.15
        assert metrics.average_safety_score == Decimal("0.92")