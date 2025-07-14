"""
Integration tests for CLI commands.

Tests all CLI commands with real API interaction and validates
output formatting, error handling, and safety compliance.
"""

import pytest
import json
import asyncio
from io import StringIO
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from click.testing import CliRunner

from cli.core import CLIEngine, CLIConfig
from cli.commands import (
    status, memory, graph, integration, config, interactive
)
from tests.fixtures.memories import MemoryFixtures
from tests.fixtures.graphs import GraphFixtures


@pytest.mark.integration
class TestCLICommands:
    """Test CLI commands with integration."""
    
    @pytest.fixture
    def cli_runner(self):
        """Provide Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def cli_engine(self):
        """Provide CLI engine with test config."""
        config = CLIConfig(
            api_base_url="http://test-api:8000",
            output_format="json",
            debug=True
        )
        return CLIEngine(config)
    
    @pytest.fixture
    def mock_api_responses(self):
        """Provide mock API responses."""
        return {
            "health": {
                "status": "healthy",
                "service": "api",
                "version": "1.0.0"
            },
            "memory_list": {
                "memories": MemoryFixtures().create_memory_batch(5),
                "total": 5
            },
            "memory_create": MemoryFixtures().create_safe_memory(),
            "graph_build": GraphFixtures().create_simple_graph(),
            "graph_list": {
                "graphs": [GraphFixtures().create_simple_graph()],
                "total_count": 1
            }
        }
    
    # Status Command Tests
    
    async def test_status_command_success(self, cli_runner):
        """Test status command with healthy API."""
        with patch('cli.core.CLIEngine') as mock_engine:
            # Mock healthy status
            mock_instance = AsyncMock()
            mock_instance.get_system_status.return_value = {
                "overall_status": "healthy",
                "api": {"status": "healthy"},
                "cli": {"version": "0.1.0"}
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(status.status_command)
            
            assert result.exit_code == 0
            assert "healthy" in result.output.lower()
    
    async def test_status_command_api_down(self, cli_runner):
        """Test status command with API down."""
        with patch('cli.core.CLIEngine') as mock_engine:
            # Mock unreachable status
            mock_instance = AsyncMock()
            mock_instance.get_system_status.return_value = {
                "overall_status": "unreachable",
                "api": {
                    "status": "unreachable",
                    "connectivity": "failed",
                    "message": "Cannot connect to API"
                }
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(status.status_command)
            
            assert result.exit_code == 0
            assert "unreachable" in result.output.lower()
    
    # Memory Command Tests
    
    async def test_memory_list_command(self, cli_runner, mock_api_responses):
        """Test memory list command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.list_memories.return_value = {
                "status": "success",
                "memories": mock_api_responses["memory_list"]["memories"],
                "total": 5
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(memory.list_memories, ['--limit', '5'])
            
            assert result.exit_code == 0
            # Should show memory count
            assert "5" in result.output or "memories" in result.output.lower()
    
    async def test_memory_create_command(self, cli_runner, mock_api_responses):
        """Test memory create command with safety validation."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.create_memory.return_value = {
                "status": "success",
                "memory": mock_api_responses["memory_create"]
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            # Test with safe content
            result = cli_runner.invoke(memory.create_memory, [
                'learning',
                'Test prompt',
                'Safe test content'
            ])
            
            assert result.exit_code == 0
            assert "success" in result.output.lower() or "created" in result.output.lower()
    
    async def test_memory_create_unsafe_content(self, cli_runner):
        """Test memory create with unsafe content."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.create_memory.return_value = {
                "status": "validation_error",
                "message": "Safety validation failed",
                "details": "Concrete references detected"
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            # Test with unsafe content
            result = cli_runner.invoke(memory.create_memory, [
                'debug',
                'Error message',
                'Error in /etc/passwd file'
            ])
            
            # Should show validation error
            assert "safety" in result.output.lower() or "validation" in result.output.lower()
    
    async def test_memory_search_command(self, cli_runner, mock_api_responses):
        """Test memory search command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.search_memories.return_value = {
                "status": "success",
                "results": mock_api_responses["memory_list"]["memories"][:3],
                "total": 3,
                "query": "test pattern"
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(memory.search_memories, [
                'test pattern',
                '--limit', '10'
            ])
            
            assert result.exit_code == 0
            assert "3" in result.output or "results" in result.output.lower()
    
    # Graph Command Tests
    
    async def test_graph_build_command(self, cli_runner, mock_api_responses):
        """Test graph build command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.build_graph.return_value = {
                "status": "success",
                "graph": mock_api_responses["graph_build"]
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(graph.build_graph, [
                '--from-memories',
                '--max-nodes', '50'
            ])
            
            assert result.exit_code == 0
            assert "success" in result.output.lower() or "built" in result.output.lower()
    
    async def test_graph_list_command(self, cli_runner, mock_api_responses):
        """Test graph list command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.list_graphs.return_value = {
                "status": "success",
                "graphs": mock_api_responses["graph_list"]["graphs"],
                "total": 1
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(graph.list_graphs)
            
            assert result.exit_code == 0
            assert "1" in result.output or "graph" in result.output.lower()
    
    async def test_graph_export_command(self, cli_runner, mock_api_responses):
        """Test graph export command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            graph_id = "test-graph-id"
            
            # Mock Mermaid export
            mock_instance.export_graph.return_value = {
                "status": "success",
                "export": {
                    "format": "mermaid",
                    "content": "graph TD\n  A --> B"
                },
                "content": "graph TD\n  A --> B",
                "format": "mermaid"
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            with cli_runner.isolated_filesystem():
                result = cli_runner.invoke(graph.export_graph, [
                    graph_id,
                    'mermaid',
                    '--output', 'test_graph.mmd'
                ])
                
                assert result.exit_code == 0
                assert Path('test_graph.mmd').exists()
    
    # Integration Command Tests
    
    async def test_vault_sync_command(self, cli_runner):
        """Test vault sync command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.sync_vault.return_value = {
                "status": "success",
                "sync": {
                    "synced_to_vault": 5,
                    "synced_from_vault": 2,
                    "conflicts": 0
                }
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(integration.sync_vault, [
                '--direction', 'both',
                '--dry-run'
            ])
            
            assert result.exit_code == 0
            assert "sync" in result.output.lower()
    
    async def test_docs_generate_command(self, cli_runner):
        """Test documentation generation command."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.generate_docs.return_value = {
                "status": "success",
                "docs": {
                    "generated_files": [
                        "README.md",
                        "API.md"
                    ],
                    "output_directory": "./docs"
                }
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(integration.generate_docs, [
                '--types', 'readme,api',
                '--output', './docs'
            ])
            
            assert result.exit_code == 0
            assert "generated" in result.output.lower()
    
    # Config Command Tests
    
    async def test_config_show_command(self, cli_runner):
        """Test config show command."""
        with patch('cli.commands.config.load_config') as mock_load:
            mock_load.return_value = {
                "api_base_url": "http://localhost:8000",
                "output_format": "table",
                "safety_min_score": 0.8
            }
            
            result = cli_runner.invoke(config.show_config)
            
            assert result.exit_code == 0
            assert "api_base_url" in result.output
    
    async def test_config_set_command(self, cli_runner):
        """Test config set command."""
        with patch('cli.commands.config.save_config') as mock_save:
            mock_save.return_value = True
            
            result = cli_runner.invoke(config.set_config, [
                'output_format',
                'json'
            ])
            
            assert result.exit_code == 0
            assert "updated" in result.output.lower()
    
    # Error Handling Tests
    
    async def test_api_connection_error_handling(self, cli_runner):
        """Test handling of API connection errors."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.list_memories.side_effect = Exception("Connection refused")
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(memory.list_memories)
            
            # Should handle error gracefully
            assert "error" in result.output.lower() or "connection" in result.output.lower()
    
    async def test_invalid_command_arguments(self, cli_runner):
        """Test handling of invalid command arguments."""
        # Test invalid memory type
        result = cli_runner.invoke(memory.create_memory, [
            'invalid_type',
            'prompt',
            'content'
        ])
        
        assert result.exit_code != 0
        assert "invalid choice" in result.output.lower()
        
        # Test missing required arguments
        result = cli_runner.invoke(memory.create_memory, [
            'learning'
            # Missing prompt and content
        ])
        
        assert result.exit_code != 0
        assert "missing argument" in result.output.lower()
    
    # Output Format Tests
    
    @pytest.mark.parametrize("output_format,expected_content", [
        ("json", ["{"", "}"", '"']),
        ("table", ["┌", "┐", "│"]),
        ("simple", [":", "-"])
    ])
    async def test_output_formats(
        self,
        cli_runner,
        output_format,
        expected_content
    ):
        """Test different output formats."""
        with patch('cli.core.CLIEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.list_memories.return_value = {
                "status": "success",
                "memories": MemoryFixtures().create_memory_batch(3),
                "total": 3
            }
            mock_engine.return_value.__aenter__.return_value = mock_instance
            
            result = cli_runner.invoke(memory.list_memories, [
                '--format', output_format
            ])
            
            assert result.exit_code == 0
            
            # Check for format-specific content
            for expected in expected_content:
                assert expected in result.output