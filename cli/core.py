"""
Core CLI engine for CoachNTT.ai.

Provides the main CLI engine that handles command routing, API communication,
and integrates with the existing script framework for safety and consistency.
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

try:
    from scripts.framework.config import load_script_config
except ImportError:
    # Fallback if script framework is not available
    def load_script_config():
        return None
from .utils import (
    format_output, 
    safe_print, 
    print_error, 
    print_warning, 
    print_success,
    print_info,
    show_spinner,
    console
)


@dataclass
class CLIConfig:
    """Configuration for CLI operations."""
    
    api_base_url: str = "http://localhost:8000"
    api_timeout: int = 30
    output_format: str = "table"
    max_results: int = 10
    debug: bool = False
    
    @classmethod
    def load_from_env(cls) -> "CLIConfig":
        """Load configuration from environment and config files."""
        # Try to load from script framework config first
        try:
            script_config = load_script_config()
            return cls(
                api_base_url=getattr(script_config, 'api_base_url', cls.api_base_url),
                api_timeout=getattr(script_config, 'api_timeout', cls.api_timeout),
                output_format=getattr(script_config, 'output_format', cls.output_format),
                max_results=getattr(script_config, 'max_results', cls.max_results),
                debug=getattr(script_config, 'debug', cls.debug)
            )
        except Exception:
            # Fall back to defaults if config loading fails
            return cls()


class CLIEngine:
    """
    Main CLI engine for CoachNTT.ai.
    
    Handles API communication, command routing, and maintains safety standards
    consistent with the existing framework.
    """
    
    def __init__(self, config: Optional[CLIConfig] = None):
        """
        Initialize CLI engine.
        
        Args:
            config: CLI configuration, loads from environment if None
        """
        self.config = config or CLIConfig.load_from_env()
        self.client: Optional[httpx.AsyncClient] = None
        self.console = console
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.config.api_base_url,
            timeout=self.config.api_timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def check_api_health(self) -> Dict[str, Any]:
        """
        Check API server health and connectivity.
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Try to reach the API health endpoint
            start_time = datetime.now()
            response = await self.client.get("/health")
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                health_data = response.json()
                health_data["response_time_ms"] = round(response_time, 2)
                return {
                    "status": "healthy",
                    "api": health_data,
                    "connectivity": "ok"
                }
            else:
                return {
                    "status": "unhealthy",
                    "api": {"status_code": response.status_code},
                    "connectivity": "error",
                    "response_time_ms": round(response_time, 2)
                }
        
        except httpx.ConnectError:
            return {
                "status": "unreachable",
                "api": {"error": "Connection refused"},
                "connectivity": "failed",
                "message": f"Cannot connect to API at {self.config.api_base_url}"
            }
        except Exception as e:
            return {
                "status": "error",
                "api": {"error": str(e)},
                "connectivity": "failed",
                "message": f"Unexpected error: {e}"
            }
    
    async def list_memories(
        self, 
        limit: int = 10, 
        memory_type: Optional[str] = None,
        since_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List recent memories from the API.
        
        Args:
            limit: Maximum number of memories to return
            memory_type: Filter by memory type
            since_days: Filter by memories from last N days
        
        Returns:
            Dictionary with memories list and metadata
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Build query parameters
            params = {"limit": min(limit, 50)}  # Cap at 50 for safety
            if memory_type:
                params["type"] = memory_type
            if since_days:
                params["since_days"] = since_days
            
            # Make API request
            response = await self.client.get("/api/v1/memories/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "memories": data.get("memories", []),
                    "total": data.get("total", 0),
                    "limit": limit,
                    "filters": {
                        "type": memory_type,
                        "since_days": since_days
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to list memories: {e}"
            }
    
    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Get specific memory by ID.
        
        Args:
            memory_id: Memory UUID
        
        Returns:
            Dictionary with memory data or error
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            response = await self.client.get(f"/api/v1/memories/{memory_id}")
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "memory": response.json()
                }
            elif response.status_code == 404:
                return {
                    "status": "not_found",
                    "message": f"Memory {memory_id} not found"
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get memory: {e}"
            }
    
    async def create_memory(
        self, 
        memory_type: str, 
        prompt: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new memory with automatic safety validation.
        
        Args:
            memory_type: Type of memory (learning, decision, context, debug, optimization)
            prompt: Original prompt or trigger for the memory
            content: Actual memory content
            metadata: Additional metadata dictionary
            intent: Optional intent specification for better categorization
        
        Returns:
            Dictionary with created memory data or error
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Prepare request data
            memory_data = {
                "memory_type": memory_type,
                "prompt": prompt,
                "content": content,
                "metadata": metadata or {}
            }
            
            # Add intent to metadata if provided
            if intent:
                memory_data["metadata"]["intent"] = intent
            
            # Make API request
            response = await self.client.post("/api/v1/memories/", json=memory_data)
            
            if response.status_code == 201:
                return {
                    "status": "success",
                    "memory": response.json()
                }
            elif response.status_code == 400:
                return {
                    "status": "validation_error",
                    "message": "Validation failed",
                    "details": response.text
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create memory: {e}"
            }
    
    async def update_memory(
        self, 
        memory_id: str, 
        prompt: Optional[str] = None, 
        content: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing memory.
        
        Args:
            memory_id: Memory UUID
            prompt: Updated prompt (optional)
            content: Updated content (optional)
            metadata: Updated metadata (optional)
        
        Returns:
            Dictionary with updated memory data or error
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Prepare update data (only include non-None values)
            update_data = {}
            if prompt is not None:
                update_data["prompt"] = prompt
            if content is not None:
                update_data["content"] = content
            if metadata is not None:
                update_data["metadata"] = metadata
            
            if not update_data:
                return {
                    "status": "error",
                    "message": "No update data provided"
                }
            
            # Make API request
            response = await self.client.put(f"/api/v1/memories/{memory_id}", json=update_data)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "memory": response.json()
                }
            elif response.status_code == 404:
                return {
                    "status": "not_found",
                    "message": f"Memory {memory_id} not found"
                }
            elif response.status_code == 400:
                return {
                    "status": "validation_error",
                    "message": "Validation failed",
                    "details": response.text
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update memory: {e}"
            }
    
    async def delete_memory(self, memory_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a memory permanently.
        
        Args:
            memory_id: Memory UUID
            force: Skip confirmation prompts if True
        
        Returns:
            Dictionary with deletion status or error
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Make API request
            response = await self.client.delete(f"/api/v1/memories/{memory_id}")
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": f"Memory {memory_id} deleted successfully"
                }
            elif response.status_code == 404:
                return {
                    "status": "not_found",
                    "message": f"Memory {memory_id} not found"
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete memory: {e}"
            }
    
    async def search_memories(
        self, 
        query: str,
        memory_types: Optional[List[str]] = None,
        intent_types: Optional[List[str]] = None,
        min_score: Optional[float] = None,
        limit: int = 10,
        enable_intent_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Search memories using semantic similarity and filters.
        
        Args:
            query: Search query string
            memory_types: Filter by memory types
            intent_types: Filter by intent types
            min_score: Minimum relevance score filter
            limit: Maximum results to return
            enable_intent_analysis: Enable intent-based search
        
        Returns:
            Dictionary with search results or error
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Prepare search request
            search_data = {
                "query": query,
                "limit": min(limit, 50),  # Cap at 50 for safety
                "enable_intent_analysis": enable_intent_analysis,
                "include_peripheral": True
            }
            
            if memory_types:
                search_data["memory_types"] = memory_types
            if min_score is not None:
                search_data["min_safety_score"] = min_score
            
            # Make API request
            response = await self.client.post("/api/v1/memories/search", json=search_data)
            
            if response.status_code == 200:
                results = response.json()
                return {
                    "status": "success",
                    "results": results,
                    "total": len(results),
                    "query": query
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to search memories: {e}"
            }
    
    async def export_memories(
        self, 
        format_type: str = "json",
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Export memories in various formats.
        
        Args:
            format_type: Export format (json, csv, markdown)
            filters: Filter criteria for export
            limit: Maximum memories to export
        
        Returns:
            Dictionary with export data or error
        """
        try:
            if not self.client:
                raise RuntimeError("CLI engine not initialized")
            
            # Get all memories matching filters
            params = {}
            if limit:
                params["limit"] = min(limit, 1000)  # Cap for safety
            
            # Apply filters if provided
            if filters:
                if "type" in filters:
                    params["type"] = filters["type"]
                if "since_days" in filters:
                    params["since_days"] = filters["since_days"]
            
            # Fetch memories
            response = await self.client.get("/api/v1/memories/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get("memories", [])
                
                return {
                    "status": "success",
                    "memories": memories,
                    "total": len(memories),
                    "format": format_type,
                    "filters": filters or {}
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to export memories: {e}"
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status including API, database, and services.
        
        Returns:
            Dictionary with complete system status
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "cli": {
                "version": "0.1.0",
                "config": {
                    "api_base_url": self.config.api_base_url,
                    "output_format": self.config.output_format,
                    "max_results": self.config.max_results
                }
            }
        }
        
        # Check API health
        api_health = await self.check_api_health()
        status["api"] = api_health
        
        # Determine overall status
        if api_health["status"] == "healthy":
            status["overall_status"] = "healthy"
        elif api_health["status"] == "unreachable":
            status["overall_status"] = "unreachable"
        else:
            status["overall_status"] = "degraded"
        
        return status
    
    def debug_print(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.config.debug:
            print_info(f"[DEBUG] {message}")
    
    def format_and_display(
        self, 
        data: Any, 
        format_type: Optional[str] = None,
        title: Optional[str] = None
    ) -> None:
        """
        Format and display data using configured output format.
        
        Args:
            data: Data to display
            format_type: Override output format
            title: Optional title for output
        """
        output_format = format_type or self.config.output_format
        format_output(data, output_format, title)


def run_async_command(coro):
    """
    Helper function to run async CLI commands.
    
    Args:
        coro: Coroutine to run
    
    Returns:
        Result of the coroutine
    """
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        print_warning("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)