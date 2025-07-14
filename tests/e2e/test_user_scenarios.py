"""
End-to-end user scenario tests.

Tests complete user workflows from memory creation through knowledge graph
building, vault synchronization, and documentation generation.
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from httpx import AsyncClient
from click.testing import CliRunner

from tests.fixtures.memories import MemoryFixtures
from tests.fixtures.graphs import GraphFixtures


@pytest.mark.e2e
class TestUserScenarios:
    """Test complete user workflows end-to-end."""
    
    @pytest.fixture
    def scenario_data(self):
        """Provide test data for scenarios."""
        return {
            "project_name": "TestProject",
            "learnings": [
                {
                    "prompt": "Understanding async patterns in Python",
                    "content": "Learned about <async_pattern> and <await_mechanism> for concurrent operations"
                },
                {
                    "prompt": "Implementing REST API with FastAPI",
                    "content": "Built <api_endpoints> using <fastapi_framework> with <pydantic_validation>"
                },
                {
                    "prompt": "Database optimization techniques",
                    "content": "Optimized <query_performance> using <indexing_strategy> and <connection_pooling>"
                }
            ],
            "decisions": [
                {
                    "prompt": "Choosing Python async framework",
                    "content": "Selected <fastapi_framework> over <flask_framework> for better <async_support>"
                },
                {
                    "prompt": "Database selection",
                    "content": "Chose <postgresql_database> with <pgvector_extension> for <vector_operations>"
                }
            ],
            "bugs": [
                {
                    "prompt": "Connection pool exhaustion",
                    "content": "Fixed <connection_leak> in <database_module> by implementing <proper_cleanup>"
                },
                {
                    "prompt": "Memory leak in embedding cache",
                    "content": "Resolved <memory_issue> by adding <lru_eviction> to <cache_implementation>"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_developer_learning_workflow(
        self,
        api_client: AsyncClient,
        cli_runner: CliRunner,
        scenario_data: Dict[str, Any]
    ):
        """Test developer learning and knowledge building workflow."""
        api_headers = {"Authorization": "Bearer test-api-key"}
        created_memory_ids = []
        
        # Step 1: Developer creates learning memories throughout the day
        print("\n=== Step 1: Creating learning memories ===")
        
        for learning in scenario_data["learnings"]:
            response = await api_client.post(
                "/api/v1/memories/",
                json={
                    "memory_type": "learning",
                    "prompt": learning["prompt"],
                    "content": learning["content"],
                    "metadata": {
                        "project": scenario_data["project_name"],
                        "date": datetime.utcnow().isoformat()
                    }
                },
                headers=api_headers
            )
            
            assert response.status_code == 201
            memory = response.json()
            created_memory_ids.append(memory["id"])
            print(f"✓ Created learning memory: {learning['prompt'][:30]}...")
        
        # Step 2: Developer searches for related learnings
        print("\n=== Step 2: Searching for related knowledge ===")
        
        search_response = await api_client.post(
            "/api/v1/memories/search",
            json={
                "query": "async patterns and API development",
                "memory_types": ["learning"],
                "limit": 10,
                "enable_intent_analysis": True
            },
            headers=api_headers
        )
        
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results) > 0
        print(f"✓ Found {len(search_results)} related memories")
        
        # Step 3: Build knowledge graph from learnings
        print("\n=== Step 3: Building knowledge graph ===")
        
        graph_response = await api_client.post(
            "/api/v1/graph/build",
            json={
                "memory_ids": created_memory_ids,
                "max_nodes": 50,
                "similarity_threshold": 0.7,
                "graph_name": f"{scenario_data['project_name']} Learning Graph"
            },
            headers=api_headers
        )
        
        assert graph_response.status_code == 200
        graph = graph_response.json()
        graph_id = graph["id"]
        print(f"✓ Built knowledge graph with {graph['node_count']} nodes and {graph['edge_count']} edges")
        
        # Step 4: Export graph visualization
        print("\n=== Step 4: Exporting graph visualization ===")
        
        export_response = await api_client.post(
            f"/api/v1/graph/{graph_id}/export",
            json={
                "format": "mermaid",
                "include_metadata": True
            },
            headers=api_headers
        )
        
        assert export_response.status_code == 200
        export_data = export_response.json()
        assert "graph TD" in export_data["content"]
        print("✓ Exported graph as Mermaid diagram")
        
        # Step 5: Sync to vault for permanent storage
        print("\n=== Step 5: Syncing to Obsidian vault ===")
        
        sync_response = await api_client.post(
            "/api/v1/integrations/vault/sync",
            json={
                "sync_direction": "to-vault",
                "template_type": "learning",
                "max_memories": 100
            },
            headers=api_headers
        )
        
        assert sync_response.status_code in [200, 202]
        print("✓ Synced memories to vault")
        
        # Step 6: Generate documentation
        print("\n=== Step 6: Generating documentation ===")
        
        docs_response = await api_client.post(
            "/api/v1/integrations/docs/generate",
            json={
                "doc_types": ["readme", "changelog"],
                "include_diagrams": True
            },
            headers=api_headers
        )
        
        assert docs_response.status_code in [200, 202]
        print("✓ Generated project documentation")
        
        print("\n✅ Developer learning workflow completed successfully!")
    
    @pytest.mark.asyncio
    async def test_debugging_and_optimization_workflow(
        self,
        api_client: AsyncClient,
        cli_runner: CliRunner,
        scenario_data: Dict[str, Any]
    ):
        """Test debugging and optimization workflow."""
        api_headers = {"Authorization": "Bearer test-api-key"}
        
        print("\n=== Debugging and Optimization Workflow ===")
        
        # Step 1: Record bug discoveries
        print("\n--- Recording bugs ---")
        bug_memory_ids = []
        
        for bug in scenario_data["bugs"]:
            response = await api_client.post(
                "/api/v1/memories/",
                json={
                    "memory_type": "debug",
                    "prompt": bug["prompt"],
                    "content": bug["content"],
                    "metadata": {
                        "severity": "high",
                        "status": "fixed",
                        "project": scenario_data["project_name"]
                    }
                },
                headers=api_headers
            )
            
            assert response.status_code == 201
            bug_memory_ids.append(response.json()["id"])
            print(f"✓ Recorded bug: {bug['prompt']}")
        
        # Step 2: Create optimization memories from fixes
        print("\n--- Creating optimization insights ---")
        
        optimization_response = await api_client.post(
            "/api/v1/memories/",
            json={
                "memory_type": "optimization",
                "prompt": "Performance improvements from bug fixes",
                "content": "Implemented <resource_management> and <caching_improvements> based on bug analysis",
                "metadata": {
                    "related_bugs": bug_memory_ids,
                    "performance_gain": "40%"
                }
            },
            headers=api_headers
        )
        
        assert optimization_response.status_code == 201
        print("✓ Created optimization memory")
        
        # Step 3: Search for similar issues
        print("\n--- Searching for similar issues ---")
        
        similar_search = await api_client.post(
            "/api/v1/memories/search",
            json={
                "query": "memory leak connection pool",
                "memory_types": ["debug", "optimization"],
                "limit": 10
            },
            headers=api_headers
        )
        
        assert similar_search.status_code == 200
        similar_issues = similar_search.json()
        print(f"✓ Found {len(similar_issues)} similar issues")
        
        # Step 4: Create checkpoint
        print("\n--- Creating development checkpoint ---")
        
        checkpoint_response = await api_client.post(
            "/api/v1/integrations/checkpoint",
            json={
                "checkpoint_name": "Bug fixes and optimizations",
                "description": "Fixed connection pool and memory leak issues",
                "include_code_analysis": True,
                "memory_filters": {
                    "types": ["debug", "optimization"],
                    "since_days": 7
                }
            },
            headers=api_headers
        )
        
        assert checkpoint_response.status_code in [200, 202]
        print("✓ Created development checkpoint")
        
        print("\n✅ Debugging workflow completed successfully!")
    
    @pytest.mark.asyncio
    async def test_decision_making_workflow(
        self,
        api_client: AsyncClient,
        scenario_data: Dict[str, Any]
    ):
        """Test architectural decision making workflow."""
        api_headers = {"Authorization": "Bearer test-api-key"}
        
        print("\n=== Decision Making Workflow ===")
        
        # Step 1: Record architectural decisions
        print("\n--- Recording decisions ---")
        decision_ids = []
        
        for decision in scenario_data["decisions"]:
            response = await api_client.post(
                "/api/v1/memories/",
                json={
                    "memory_type": "decision",
                    "prompt": decision["prompt"],
                    "content": decision["content"],
                    "metadata": {
                        "impact": "high",
                        "category": "architecture",
                        "project": scenario_data["project_name"]
                    }
                },
                headers=api_headers
            )
            
            assert response.status_code == 201
            decision_ids.append(response.json()["id"])
            print(f"✓ Recorded decision: {decision['prompt']}")
        
        # Step 2: Build decision graph
        print("\n--- Building decision graph ---")
        
        decision_graph = await api_client.post(
            "/api/v1/graph/build",
            json={
                "memory_ids": decision_ids,
                "graph_name": "Architecture Decisions",
                "max_nodes": 30
            },
            headers=api_headers
        )
        
        assert decision_graph.status_code == 200
        graph_data = decision_graph.json()
        print(f"✓ Built decision graph with {graph_data['node_count']} nodes")
        
        # Step 3: Analyze decision impact
        print("\n--- Analyzing decision connections ---")
        
        graph_query = await api_client.post(
            f"/api/v1/graph/{graph_data['id']}/query",
            json={
                "node_types": ["decision"],
                "min_node_safety_score": 0.8
            },
            headers=api_headers
        )
        
        assert graph_query.status_code == 200
        query_results = graph_query.json()
        print(f"✓ Analyzed {len(query_results['nodes'])} decision nodes")
        
        # Step 4: Generate decision documentation
        print("\n--- Generating ADR documentation ---")
        
        adr_response = await api_client.post(
            "/api/v1/integrations/docs/generate",
            json={
                "doc_types": ["architecture"],
                "include_diagrams": True,
                "code_paths": ["src/"]
            },
            headers=api_headers
        )
        
        assert adr_response.status_code in [200, 202]
        print("✓ Generated Architecture Decision Records")
        
        print("\n✅ Decision making workflow completed successfully!")
    
    @pytest.mark.asyncio
    async def test_cli_interactive_workflow(
        self,
        cli_runner: CliRunner
    ):
        """Test interactive CLI workflow."""
        print("\n=== Interactive CLI Workflow ===")
        
        # Mock CLI engine for testing
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            
            # Mock various operations
            mock_instance.get_system_status.return_value = {
                "overall_status": "healthy",
                "api": {"status": "healthy"}
            }
            
            mock_instance.list_memories.return_value = {
                "status": "success",
                "memories": MemoryFixtures().create_memory_batch(5),
                "total": 5
            }
            
            mock_instance.build_graph.return_value = {
                "status": "success",
                "graph": GraphFixtures().create_simple_graph()
            }
            
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            # Step 1: Check system status
            print("\n--- Checking system status ---")
            result = cli_runner.invoke(['status'])
            assert result.exit_code == 0
            print("✓ System status checked")
            
            # Step 2: List recent memories
            print("\n--- Listing recent memories ---")
            result = cli_runner.invoke(['memory', 'list', '--limit', '5'])
            assert result.exit_code == 0
            print("✓ Listed recent memories")
            
            # Step 3: Create a new memory
            print("\n--- Creating new memory ---")
            mock_instance.create_memory.return_value = {
                "status": "success",
                "memory": MemoryFixtures().create_safe_memory()
            }
            
            result = cli_runner.invoke([
                'memory', 'create',
                'learning',
                'CLI test learning',
                'Testing the CLI workflow'
            ])
            assert result.exit_code == 0
            print("✓ Created new memory via CLI")
            
            # Step 4: Build a graph
            print("\n--- Building knowledge graph ---")
            result = cli_runner.invoke([
                'graph', 'build',
                '--from-memories',
                '--max-nodes', '20'
            ])
            assert result.exit_code == 0
            print("✓ Built knowledge graph via CLI")
            
            print("\n✅ CLI interactive workflow completed successfully!")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_development_cycle(
        self,
        api_client: AsyncClient,
        scenario_data: Dict[str, Any]
    ):
        """Test complete development cycle from learning to production."""
        api_headers = {"Authorization": "Bearer test-api-key"}
        
        print("\n=== Full Development Cycle E2E Test ===")
        
        # Phase 1: Learning and exploration
        print("\n--- Phase 1: Learning ---")
        all_memory_ids = []
        
        # Create various types of memories
        for memory_type, items in [
            ("learning", scenario_data["learnings"]),
            ("decision", scenario_data["decisions"]),
            ("debug", scenario_data["bugs"])
        ]:
            for item in items:
                response = await api_client.post(
                    "/api/v1/memories/",
                    json={
                        "memory_type": memory_type,
                        "prompt": item["prompt"],
                        "content": item["content"],
                        "metadata": {"project": scenario_data["project_name"]}
                    },
                    headers=api_headers
                )
                assert response.status_code == 201
                all_memory_ids.append(response.json()["id"])
        
        print(f"✓ Created {len(all_memory_ids)} memories")
        
        # Phase 2: Knowledge synthesis
        print("\n--- Phase 2: Knowledge Synthesis ---")
        
        # Build comprehensive knowledge graph
        graph_response = await api_client.post(
            "/api/v1/graph/build",
            json={
                "memory_ids": all_memory_ids,
                "max_nodes": 100,
                "graph_name": f"{scenario_data['project_name']} Complete"
            },
            headers=api_headers
        )
        
        assert graph_response.status_code == 200
        main_graph = graph_response.json()
        print(f"✓ Built comprehensive graph: {main_graph['node_count']} nodes")
        
        # Extract subgraph for specific topic
        if all_memory_ids:
            subgraph_response = await api_client.post(
                f"/api/v1/graph/{main_graph['id']}/subgraph",
                json={
                    "center_node_id": all_memory_ids[0],
                    "max_depth": 3,
                    "max_nodes": 20
                },
                headers=api_headers
            )
            
            assert subgraph_response.status_code == 200
            print("✓ Extracted topic subgraph")
        
        # Phase 3: Documentation and sharing
        print("\n--- Phase 3: Documentation ---")
        
        # Generate comprehensive documentation
        docs_response = await api_client.post(
            "/api/v1/integrations/docs/generate",
            json={
                "doc_types": ["readme", "api", "architecture", "changelog"],
                "include_diagrams": True,
                "output_format": "markdown"
            },
            headers=api_headers
        )
        
        assert docs_response.status_code in [200, 202]
        print("✓ Generated comprehensive documentation")
        
        # Phase 4: Vault synchronization
        print("\n--- Phase 4: Knowledge Preservation ---")
        
        vault_response = await api_client.post(
            "/api/v1/integrations/vault/sync",
            json={
                "sync_direction": "both",
                "max_memories": 1000
            },
            headers=api_headers
        )
        
        assert vault_response.status_code in [200, 202]
        print("✓ Synchronized with knowledge vault")
        
        # Phase 5: Create final checkpoint
        print("\n--- Phase 5: Final Checkpoint ---")
        
        checkpoint_response = await api_client.post(
            "/api/v1/integrations/checkpoint",
            json={
                "checkpoint_name": f"{scenario_data['project_name']} v1.0",
                "description": "Complete development cycle checkpoint",
                "include_code_analysis": True
            },
            headers=api_headers
        )
        
        assert checkpoint_response.status_code in [200, 202]
        print("✓ Created final development checkpoint")
        
        print("\n✅ Full development cycle completed successfully!")
        print(f"   - Memories created: {len(all_memory_ids)}")
        print(f"   - Graph nodes: {main_graph['node_count']}")
        print(f"   - Graph edges: {main_graph['edge_count']}")
        print("   - Documentation: ✓")
        print("   - Vault sync: ✓")
        print("   - Checkpoint: ✓")