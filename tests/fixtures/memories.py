"""
Memory test fixtures for comprehensive testing.

Provides various memory data patterns including safe, unsafe, and edge cases.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random


class MemoryFixtures:
    """Comprehensive memory test fixtures."""
    
    @staticmethod
    def create_safe_memory(
        memory_type: str = "learning",
        custom_content: str = None
    ) -> Dict[str, Any]:
        """Create a safe memory with proper abstraction."""
        memory_id = str(uuid.uuid4())
        
        safe_contents = [
            "Understanding the pattern of <module_name> in the <project_structure>",
            "The <api_endpoint> follows RESTful design principles",
            "Implementing <design_pattern> for better code organization",
            "Fixed issue in <component_name> by refactoring <method_name>",
            "Learned about <technology_concept> and its applications",
        ]
        
        return {
            "id": memory_id,
            "memory_type": memory_type,
            "prompt": f"Test prompt for {memory_type}",
            "content": custom_content or random.choice(safe_contents),
            "metadata": {
                "test": True,
                "fixture": "safe_memory",
                "abstraction_applied": True,
            },
            "safety_score": 0.95,
            "created_at": datetime.utcnow().isoformat(),
            "temporal_weight": 1.0,
        }
    
    @staticmethod
    def create_unsafe_memory() -> Dict[str, Any]:
        """Create memory with concrete references (should fail validation)."""
        unsafe_contents = [
            "Error in /home/user/project/src/main.py at line 42",
            "Connect to database at postgresql://user:pass@localhost:5432/db",
            "API key is sk-1234567890abcdef stored in config.json",
            "Send email to john.doe@company.com about the issue",
            "The file C:\\Users\\Admin\\Documents\\secrets.txt contains passwords",
        ]
        
        return {
            "id": str(uuid.uuid4()),
            "memory_type": "debug",
            "prompt": "Debug error message",
            "content": random.choice(unsafe_contents),
            "metadata": {
                "test": True,
                "fixture": "unsafe_memory",
                "should_fail": True,
            },
            "created_at": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def create_edge_case_memories() -> List[Dict[str, Any]]:
        """Create memories with edge cases for testing."""
        return [
            # Empty content
            {
                "id": str(uuid.uuid4()),
                "memory_type": "context",
                "prompt": "Empty test",
                "content": "",
                "metadata": {"edge_case": "empty_content"},
            },
            # Very long content
            {
                "id": str(uuid.uuid4()),
                "memory_type": "learning",
                "prompt": "Long content test",
                "content": "This is a test. " * 1000,  # ~4000 chars
                "metadata": {"edge_case": "long_content"},
            },
            # Unicode and special characters
            {
                "id": str(uuid.uuid4()),
                "memory_type": "context",
                "prompt": "Unicode test",
                "content": "Testing émojis 🚀 and spëcial çharacters ñ",
                "metadata": {"edge_case": "unicode"},
            },
            # Mixed safe and unsafe
            {
                "id": str(uuid.uuid4()),
                "memory_type": "decision",
                "prompt": "Mixed content test",
                "content": "The <pattern_name> is located at /etc/config which is not ideal",
                "metadata": {"edge_case": "mixed_safety"},
            },
            # Minimal required fields only
            {
                "memory_type": "context",
                "prompt": "Minimal test",
                "content": "Minimal content",
            },
            # Maximum metadata
            {
                "id": str(uuid.uuid4()),
                "memory_type": "optimization",
                "prompt": "Metadata test",
                "content": "Testing metadata limits",
                "metadata": {
                    f"key_{i}": f"value_{i}" for i in range(50)
                },
            },
        ]
    
    @staticmethod
    def create_memory_batch(
        count: int = 10,
        memory_types: List[str] = None,
        days_range: int = 30
    ) -> List[Dict[str, Any]]:
        """Create a batch of memories for testing."""
        if not memory_types:
            memory_types = ["learning", "decision", "context", "debug", "optimization"]
        
        memories = []
        base_date = datetime.utcnow()
        
        for i in range(count):
            memory_type = random.choice(memory_types)
            days_ago = random.randint(0, days_range)
            created_at = base_date - timedelta(days=days_ago)
            
            # Mix of safe and abstracted content
            memory = MemoryFixtures.create_safe_memory(memory_type)
            memory["created_at"] = created_at.isoformat()
            memory["temporal_weight"] = 1.0 * (0.99 ** days_ago)  # Decay simulation
            memory["metadata"]["batch_index"] = i
            memory["metadata"]["days_ago"] = days_ago
            
            memories.append(memory)
        
        return memories
    
    @staticmethod
    def create_clustered_memories() -> Dict[str, List[Dict[str, Any]]]:
        """Create memories organized in semantic clusters."""
        clusters = {
            "testing_cluster": [
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "learning",
                    "prompt": "Unit testing patterns",
                    "content": "Understanding <test_framework> patterns and <assertion_methods>",
                    "metadata": {"cluster": "testing", "topic": "unit_tests"},
                },
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "learning",
                    "prompt": "Integration testing",
                    "content": "Testing <component_interaction> with <mock_services>",
                    "metadata": {"cluster": "testing", "topic": "integration_tests"},
                },
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "decision",
                    "prompt": "Test framework choice",
                    "content": "Chose <test_framework> for its <framework_features>",
                    "metadata": {"cluster": "testing", "topic": "framework_decision"},
                },
            ],
            "api_cluster": [
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "learning",
                    "prompt": "REST API design",
                    "content": "Implementing <rest_principles> in <api_layer>",
                    "metadata": {"cluster": "api", "topic": "rest_design"},
                },
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "optimization",
                    "prompt": "API performance",
                    "content": "Optimized <endpoint_name> using <caching_strategy>",
                    "metadata": {"cluster": "api", "topic": "performance"},
                },
            ],
            "database_cluster": [
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "learning",
                    "prompt": "Database indexing",
                    "content": "Created indexes on <table_columns> for <query_optimization>",
                    "metadata": {"cluster": "database", "topic": "indexing"},
                },
                {
                    "id": str(uuid.uuid4()),
                    "memory_type": "debug",
                    "prompt": "Query optimization",
                    "content": "Fixed slow query in <query_name> by <optimization_technique>",
                    "metadata": {"cluster": "database", "topic": "optimization"},
                },
            ],
        }
        
        # Add embeddings simulation (would be real embeddings in production)
        for cluster_memories in clusters.values():
            for memory in cluster_memories:
                memory["embedding"] = [random.random() for _ in range(384)]  # Mock embedding
                memory["safety_score"] = random.uniform(0.85, 0.99)
                memory["created_at"] = datetime.utcnow().isoformat()
        
        return clusters
    
    @staticmethod
    def create_search_test_data() -> Dict[str, Any]:
        """Create test data for search functionality."""
        return {
            "exact_matches": [
                {
                    "id": str(uuid.uuid4()),
                    "content": "Exact phrase: implementing caching strategy",
                    "memory_type": "learning",
                    "prompt": "Caching implementation",
                },
                {
                    "id": str(uuid.uuid4()),
                    "content": "Another exact phrase: implementing caching strategy here",
                    "memory_type": "optimization",
                    "prompt": "Performance improvement",
                },
            ],
            "semantic_matches": [
                {
                    "id": str(uuid.uuid4()),
                    "content": "Using cache to improve performance",
                    "memory_type": "optimization",
                    "prompt": "Speed optimization",
                },
                {
                    "id": str(uuid.uuid4()),
                    "content": "Memory storage optimization techniques",
                    "memory_type": "learning",
                    "prompt": "Storage patterns",
                },
            ],
            "no_matches": [
                {
                    "id": str(uuid.uuid4()),
                    "content": "Completely unrelated content about frontend styling",
                    "memory_type": "context",
                    "prompt": "UI design",
                },
                {
                    "id": str(uuid.uuid4()),
                    "content": "Documentation about user authentication flow",
                    "memory_type": "learning", 
                    "prompt": "Auth flow",
                },
            ],
            "search_queries": {
                "exact": "implementing caching strategy",
                "semantic": "cache performance optimization",
                "typo": "implmenting cching stratgy",
                "partial": "caching",
                "no_match": "quantum computing algorithms",
            }
        }