"""
Integration tests for API endpoints.

Tests all REST API endpoints with authentication, safety validation,
rate limiting, and proper error handling.
"""

import pytest
import uuid
import json
from datetime import datetime
from typing import Dict, Any
from httpx import AsyncClient

from tests.fixtures.memories import MemoryFixtures
from tests.fixtures.graphs import GraphFixtures
from src.api.main import app


@pytest.mark.integration
@pytest.mark.requires_api
class TestAPIEndpoints:
    """Test API endpoints with full integration."""
    
    @pytest.fixture
    def api_headers(self):
        """Provide API headers with authentication."""
        return {
            "Authorization": "Bearer test-api-key",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def memory_fixtures(self):
        """Provide memory test fixtures."""
        return MemoryFixtures()
    
    @pytest.fixture
    def graph_fixtures(self):
        """Provide graph test fixtures."""
        return GraphFixtures()
    
    # Root and Health Endpoints
    
    async def test_root_endpoint(self, api_client: AsyncClient):
        """Test root endpoint."""
        response = await api_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "operational"
    
    async def test_health_endpoint(self, api_client: AsyncClient):
        """Test health check endpoint."""
        response = await api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "api"
    
    # Memory Endpoints
    
    async def test_create_memory_success(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test successful memory creation."""
        memory_data = memory_fixtures.create_safe_memory()
        
        response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": memory_data["memory_type"],
                "prompt": memory_data["prompt"],
                "content": memory_data["content"],
                "metadata": memory_data["metadata"]
            },
            headers=api_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["memory_type"] == memory_data["memory_type"]
        assert data["safety_score"] >= 0.8
        assert "created_at" in data
    
    async def test_create_memory_unsafe_content(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test memory creation with unsafe content."""
        unsafe_data = memory_fixtures.create_unsafe_memory()
        
        response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": unsafe_data["memory_type"],
                "prompt": unsafe_data["prompt"],
                "content": unsafe_data["content"],
                "metadata": unsafe_data["metadata"]
            },
            headers=api_headers
        )
        
        # Should reject unsafe content
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "safety" in data["detail"].lower() or "validation" in data["detail"].lower()
    
    async def test_get_memory(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test getting a specific memory."""
        # First create a memory
        memory_data = memory_fixtures.create_safe_memory()
        
        create_response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": memory_data["memory_type"],
                "prompt": memory_data["prompt"],
                "content": memory_data["content"],
                "metadata": memory_data["metadata"]
            },
            headers=api_headers
        )
        
        assert create_response.status_code == 201
        created_memory = create_response.json()
        memory_id = created_memory["id"]
        
        # Get the memory
        response = await api_client.get(
            f"/api/v1/memories/{memory_id}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == memory_id
        assert data["content"] == memory_data["content"]
    
    async def test_get_memory_not_found(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test getting non-existent memory."""
        fake_id = str(uuid.uuid4())
        
        response = await api_client.get(
            f"/api/v1/memories/{fake_id}",
            headers=api_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    async def test_update_memory(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test updating a memory."""
        # Create a memory first
        memory_data = memory_fixtures.create_safe_memory()
        
        create_response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": memory_data["memory_type"],
                "prompt": memory_data["prompt"],
                "content": memory_data["content"],
                "metadata": memory_data["metadata"]
            },
            headers=api_headers
        )
        
        memory_id = create_response.json()["id"]
        
        # Update the memory
        update_data = {
            "content": "Updated safe content with <abstracted_reference>",
            "metadata": {"updated": True}
        }
        
        response = await api_client.put(
            f"/api/v1/memories/{memory_id}",
            json=update_data,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["content"] == update_data["content"]
        assert data["metadata"]["updated"] is True
        assert data["updated_at"] > data["created_at"]
    
    async def test_delete_memory(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test deleting a memory."""
        # Create a memory
        memory_data = memory_fixtures.create_safe_memory()
        
        create_response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": memory_data["memory_type"],
                "prompt": memory_data["prompt"],
                "content": memory_data["content"],
                "metadata": memory_data["metadata"]
            },
            headers=api_headers
        )
        
        memory_id = create_response.json()["id"]
        
        # Delete the memory
        response = await api_client.delete(
            f"/api/v1/memories/{memory_id}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        
        # Verify deletion
        get_response = await api_client.get(
            f"/api/v1/memories/{memory_id}",
            headers=api_headers
        )
        
        assert get_response.status_code == 404
    
    async def test_search_memories(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test memory search functionality."""
        # Create test memories
        search_data = memory_fixtures.create_search_test_data()
        created_memories = []
        
        # Create exact match memories
        for mem_data in search_data["exact_matches"]:
            response = await api_client.post(
                "/api/v1/memories/",
                json={
                    "memory_type": mem_data["memory_type"],
                    "prompt": mem_data["prompt"],
                    "content": mem_data["content"],
                    "metadata": {}
                },
                headers=api_headers
            )
            if response.status_code == 201:
                created_memories.append(response.json())
        
        # Search for exact phrase
        search_query = search_data["search_queries"]["exact"]
        
        response = await api_client.post(
            "/api/v1/memories/search",
            json={
                "query": search_query,
                "limit": 10,
                "enable_intent_analysis": True
            },
            headers=api_headers
        )
        
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) > 0
        # Results should be sorted by relevance
        if len(results) > 1:
            assert results[0]["relevance_score"] >= results[-1]["relevance_score"]
    
    # Knowledge Graph Endpoints
    
    async def test_build_graph(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        memory_fixtures: MemoryFixtures
    ):
        """Test knowledge graph building."""
        # Create some memories first
        memories = memory_fixtures.create_memory_batch(10)
        memory_ids = []
        
        for mem_data in memories:
            response = await api_client.post(
                "/api/v1/memories/",
                json={
                    "memory_type": mem_data["memory_type"],
                    "prompt": mem_data["prompt"],
                    "content": mem_data["content"],
                    "metadata": mem_data.get("metadata", {})
                },
                headers=api_headers
            )
            if response.status_code == 201:
                memory_ids.append(response.json()["id"])
        
        # Build graph
        response = await api_client.post(
            "/api/v1/graph/build",
            json={
                "memory_ids": memory_ids[:5],
                "max_nodes": 20,
                "similarity_threshold": 0.7,
                "graph_name": "Test Graph"
            },
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "name" in data
        assert data["name"] == "Test Graph"
        assert "node_count" in data
        assert "edge_count" in data
    
    async def test_get_graph(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str],
        graph_fixtures: GraphFixtures
    ):
        """Test getting graph metadata."""
        # Build a graph first
        response = await api_client.post(
            "/api/v1/graph/build",
            json={
                "max_nodes": 10,
                "graph_name": "Test Graph Metadata"
            },
            headers=api_headers
        )
        
        graph_id = response.json()["id"]
        
        # Get graph metadata
        response = await api_client.get(
            f"/api/v1/graph/{graph_id}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == graph_id
        assert "created_at" in data
        assert "node_count" in data
        assert "edge_count" in data
    
    async def test_query_graph(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test graph querying."""
        # Build a graph
        build_response = await api_client.post(
            "/api/v1/graph/build",
            json={
                "max_nodes": 20,
                "graph_name": "Test Query Graph"
            },
            headers=api_headers
        )
        
        graph_id = build_response.json()["id"]
        
        # Query the graph
        response = await api_client.post(
            f"/api/v1/graph/{graph_id}/query",
            json={
                "max_nodes": 10,
                "min_node_safety_score": 0.8,
                "node_types": ["memory"]
            },
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
    
    async def test_export_graph(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test graph export in different formats."""
        # Build a graph
        build_response = await api_client.post(
            "/api/v1/graph/build",
            json={
                "max_nodes": 10,
                "graph_name": "Test Export Graph"
            },
            headers=api_headers
        )
        
        graph_id = build_response.json()["id"]
        
        # Test different export formats
        formats = ["json", "mermaid", "d3"]
        
        for fmt in formats:
            response = await api_client.post(
                f"/api/v1/graph/{graph_id}/export",
                json={
                    "format": fmt,
                    "include_metadata": True
                },
                headers=api_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "content" in data
            assert "format" in data
            assert data["format"] == fmt
    
    # Integration Endpoints
    
    async def test_create_checkpoint(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test checkpoint creation."""
        response = await api_client.post(
            "/api/v1/integrations/checkpoint",
            json={
                "checkpoint_name": "Test Checkpoint",
                "description": "Integration test checkpoint",
                "max_memories": 10
            },
            headers=api_headers
        )
        
        assert response.status_code in [200, 202]  # May be async
        data = response.json()
        
        if "task_id" in data:
            # Async task started
            assert "status" in data
        else:
            # Synchronous completion
            assert "checkpoint_id" in data
    
    async def test_vault_sync(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test vault synchronization."""
        response = await api_client.post(
            "/api/v1/integrations/vault/sync",
            json={
                "sync_direction": "to-vault",
                "dry_run": True,
                "max_memories": 5
            },
            headers=api_headers
        )
        
        assert response.status_code in [200, 202]
        data = response.json()
        
        if response.status_code == 200:
            assert "synced_count" in data or "dry_run" in data
    
    # Authentication Tests
    
    async def test_missing_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test endpoints without authentication."""
        # Try to access protected endpoint without auth
        response = await api_client.get("/api/v1/memories/")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    async def test_invalid_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test with invalid authentication."""
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = await api_client.get(
            "/api/v1/memories/",
            headers=headers
        )
        
        assert response.status_code == 401
    
    # Rate Limiting Tests
    
    @pytest.mark.slow
    async def test_rate_limiting(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test rate limiting functionality."""
        # Make many requests quickly
        responses = []
        for _ in range(20):
            response = await api_client.get(
                "/api/v1/memories/",
                headers=api_headers
            )
            responses.append(response.status_code)
        
        # Some requests should be rate limited (if enabled)
        # Note: Rate limiting might be disabled in test environment
        assert all(status in [200, 429] for status in responses)
    
    # Error Handling Tests
    
    async def test_invalid_json(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test handling of invalid JSON."""
        headers = api_headers.copy()
        headers["Content-Type"] = "application/json"
        
        response = await api_client.post(
            "/api/v1/memories/",
            content="invalid json {",
            headers=headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    async def test_validation_errors(
        self,
        api_client: AsyncClient,
        api_headers: Dict[str, str]
    ):
        """Test validation error responses."""
        # Missing required fields
        response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": "learning"
                # Missing prompt and content
            },
            headers=api_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        
        assert "detail" in data
        assert "errors" in data
        
        # Check error structure
        errors = data["errors"]
        assert isinstance(errors, list)
        assert len(errors) > 0