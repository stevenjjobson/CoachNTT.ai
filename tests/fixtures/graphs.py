"""
Knowledge graph test fixtures for comprehensive testing.

Provides graph structures, nodes, edges, and complex graph scenarios.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Tuple
import random
import json


class GraphFixtures:
    """Comprehensive knowledge graph test fixtures."""
    
    @staticmethod
    def create_simple_graph() -> Dict[str, Any]:
        """Create a simple graph with few nodes and edges."""
        graph_id = str(uuid.uuid4())
        
        nodes = [
            {
                "id": "node_1",
                "type": "memory",
                "content": "Understanding <design_pattern> implementation",
                "metadata": {
                    "memory_type": "learning",
                    "topic": "patterns",
                },
                "safety_score": 0.95,
                "centrality": 0.8,
            },
            {
                "id": "node_2", 
                "type": "code",
                "content": "Pattern implementation in <module_name>",
                "metadata": {
                    "language": "python",
                    "complexity": 5,
                },
                "safety_score": 0.98,
                "centrality": 0.6,
            },
            {
                "id": "node_3",
                "type": "memory",
                "content": "Decision to use <pattern_type> for <use_case>",
                "metadata": {
                    "memory_type": "decision",
                    "impact": "high",
                },
                "safety_score": 0.92,
                "centrality": 0.7,
            },
        ]
        
        edges = [
            {
                "source": "node_1",
                "target": "node_2",
                "type": "implements",
                "weight": 0.9,
                "metadata": {"confidence": "high"},
            },
            {
                "source": "node_1",
                "target": "node_3",
                "type": "relates_to",
                "weight": 0.7,
                "metadata": {"relationship": "conceptual"},
            },
            {
                "source": "node_3",
                "target": "node_2",
                "type": "influences",
                "weight": 0.8,
                "metadata": {"impact": "direct"},
            },
        ]
        
        return {
            "id": graph_id,
            "name": "Test Simple Graph",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "graph_type": "simple",
            },
        }
    
    @staticmethod
    def create_complex_graph(
        node_count: int = 50,
        edge_density: float = 0.3
    ) -> Dict[str, Any]:
        """Create a complex graph with many nodes and edges."""
        graph_id = str(uuid.uuid4())
        
        # Node types and content templates
        node_types = ["memory", "code", "concept", "decision", "optimization"]
        content_templates = {
            "memory": [
                "Learning about <concept_name> in <context>",
                "Understanding <pattern_name> for <use_case>",
                "Discovered <technique_name> improves <metric>",
            ],
            "code": [
                "Implementation of <algorithm_name> in <module>",
                "Refactored <component_name> using <pattern>",
                "Added <feature_name> to <service_name>",
            ],
            "concept": [
                "The principle of <concept_name>",
                "Abstract pattern: <pattern_description>",
                "Architecture concept: <architecture_element>",
            ],
            "decision": [
                "Chose <option_a> over <option_b> because <reason>",
                "Decided to implement <solution_name>",
                "Selected <technology_name> for <requirement>",
            ],
            "optimization": [
                "Optimized <component_name> by <percentage>%",
                "Improved <metric_name> through <technique>",
                "Reduced <resource_name> usage in <context>",
            ],
        }
        
        # Create nodes
        nodes = []
        for i in range(node_count):
            node_type = random.choice(node_types)
            content_template = random.choice(content_templates[node_type])
            
            node = {
                "id": f"node_{i}",
                "type": node_type,
                "content": content_template,
                "metadata": {
                    "index": i,
                    "cluster": i % 5,  # Create 5 clusters
                    "importance": random.uniform(0.1, 1.0),
                },
                "safety_score": random.uniform(0.85, 0.99),
                "centrality": 0.0,  # Will be calculated
            }
            nodes.append(node)
        
        # Create edges based on density
        edges = []
        edge_types = ["relates_to", "implements", "influences", "depends_on", "contradicts"]
        max_edges = int(node_count * (node_count - 1) * edge_density / 2)
        
        edge_count = 0
        for i in range(node_count):
            for j in range(i + 1, node_count):
                if edge_count >= max_edges:
                    break
                
                # Higher probability of edges within same cluster
                same_cluster = nodes[i]["metadata"]["cluster"] == nodes[j]["metadata"]["cluster"]
                edge_probability = 0.8 if same_cluster else 0.2
                
                if random.random() < edge_probability:
                    edge = {
                        "source": f"node_{i}",
                        "target": f"node_{j}",
                        "type": random.choice(edge_types),
                        "weight": random.uniform(0.1, 1.0),
                        "metadata": {
                            "same_cluster": same_cluster,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    }
                    edges.append(edge)
                    edge_count += 1
        
        # Calculate basic centrality (degree centrality)
        degree_count = {f"node_{i}": 0 for i in range(node_count)}
        for edge in edges:
            degree_count[edge["source"]] += 1
            degree_count[edge["target"]] += 1
        
        max_degree = max(degree_count.values()) if degree_count else 1
        for node in nodes:
            node["centrality"] = degree_count[node["id"]] / max_degree
        
        return {
            "id": graph_id,
            "name": f"Test Complex Graph ({node_count} nodes)",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "edge_density": edge_density,
                "graph_type": "complex",
                "clusters": 5,
            },
        }
    
    @staticmethod
    def create_hierarchical_graph() -> Dict[str, Any]:
        """Create a hierarchical graph structure."""
        graph_id = str(uuid.uuid4())
        
        # Create tree structure
        levels = {
            0: ["root"],
            1: ["child_1_1", "child_1_2", "child_1_3"],
            2: ["child_2_1", "child_2_2", "child_2_3", "child_2_4", "child_2_5"],
            3: ["leaf_1", "leaf_2", "leaf_3", "leaf_4", "leaf_5", "leaf_6"],
        }
        
        nodes = []
        node_index = 0
        
        for level, node_ids in levels.items():
            for node_id in node_ids:
                node = {
                    "id": node_id,
                    "type": "concept" if level < 2 else "memory",
                    "content": f"Level {level} concept: <{node_id}_content>",
                    "metadata": {
                        "level": level,
                        "hierarchy_position": node_index,
                    },
                    "safety_score": 0.95,
                    "centrality": 1.0 / (level + 1),  # Higher level = higher centrality
                }
                nodes.append(node)
                node_index += 1
        
        # Create hierarchical edges
        edges = []
        
        # Connect root to level 1
        for child in levels[1]:
            edges.append({
                "source": "root",
                "target": child,
                "type": "parent_of",
                "weight": 1.0,
                "metadata": {"hierarchy": True},
            })
        
        # Connect level 1 to level 2
        for i, parent in enumerate(levels[1]):
            # Each parent gets 1-2 children
            child_count = min(2, len(levels[2]) - i * 2)
            for j in range(child_count):
                child_idx = i * 2 + j
                if child_idx < len(levels[2]):
                    edges.append({
                        "source": parent,
                        "target": levels[2][child_idx],
                        "type": "parent_of",
                        "weight": 0.9,
                        "metadata": {"hierarchy": True},
                    })
        
        # Connect level 2 to leaves
        for i, parent in enumerate(levels[2]):
            if i < len(levels[3]):
                edges.append({
                    "source": parent,
                    "target": levels[3][i],
                    "type": "parent_of",
                    "weight": 0.8,
                    "metadata": {"hierarchy": True},
                })
        
        # Add some cross-hierarchy connections
        edges.extend([
            {
                "source": "child_1_1",
                "target": "child_1_2",
                "type": "relates_to",
                "weight": 0.6,
                "metadata": {"hierarchy": False},
            },
            {
                "source": "child_2_1",
                "target": "child_2_3",
                "type": "similar_to",
                "weight": 0.7,
                "metadata": {"hierarchy": False},
            },
        ])
        
        return {
            "id": graph_id,
            "name": "Test Hierarchical Graph",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "graph_type": "hierarchical",
                "levels": len(levels),
            },
        }
    
    @staticmethod
    def create_disconnected_graph() -> Dict[str, Any]:
        """Create a graph with disconnected components."""
        graph_id = str(uuid.uuid4())
        
        # Create three disconnected components
        components = []
        nodes = []
        edges = []
        
        # Component 1: Triangle
        comp1_nodes = ["comp1_1", "comp1_2", "comp1_3"]
        for i, node_id in enumerate(comp1_nodes):
            nodes.append({
                "id": node_id,
                "type": "memory",
                "content": f"Component 1 node {i}",
                "metadata": {"component": 1},
                "safety_score": 0.95,
                "centrality": 0.33,
            })
        
        edges.extend([
            {"source": "comp1_1", "target": "comp1_2", "type": "relates_to", "weight": 0.8},
            {"source": "comp1_2", "target": "comp1_3", "type": "relates_to", "weight": 0.7},
            {"source": "comp1_3", "target": "comp1_1", "type": "relates_to", "weight": 0.9},
        ])
        
        # Component 2: Star
        comp2_center = "comp2_center"
        nodes.append({
            "id": comp2_center,
            "type": "concept",
            "content": "Central concept node",
            "metadata": {"component": 2, "role": "center"},
            "safety_score": 0.98,
            "centrality": 1.0,
        })
        
        for i in range(4):
            node_id = f"comp2_spoke_{i}"
            nodes.append({
                "id": node_id,
                "type": "memory",
                "content": f"Spoke node {i}",
                "metadata": {"component": 2, "role": "spoke"},
                "safety_score": 0.92,
                "centrality": 0.25,
            })
            edges.append({
                "source": comp2_center,
                "target": node_id,
                "type": "connects_to",
                "weight": 0.6 + i * 0.1,
            })
        
        # Component 3: Single node
        nodes.append({
            "id": "comp3_isolated",
            "type": "decision",
            "content": "Isolated decision node",
            "metadata": {"component": 3},
            "safety_score": 0.90,
            "centrality": 0.0,
        })
        
        return {
            "id": graph_id,
            "name": "Test Disconnected Graph",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "graph_type": "disconnected",
                "components": 3,
            },
        }
    
    @staticmethod
    def create_graph_query_fixtures() -> Dict[str, Any]:
        """Create fixtures for testing graph queries."""
        base_graph = GraphFixtures.create_complex_graph(20, 0.4)
        
        # Add specific patterns for querying
        # High centrality nodes
        for node in base_graph["nodes"][:3]:
            node["centrality"] = random.uniform(0.8, 1.0)
        
        # Low safety score nodes
        for node in base_graph["nodes"][3:6]:
            node["safety_score"] = random.uniform(0.6, 0.75)
        
        # Specific content patterns
        base_graph["nodes"][6]["content"] = "Testing query pattern matching"
        base_graph["nodes"][7]["content"] = "Another query pattern example"
        
        # Specific edge types
        for edge in base_graph["edges"][:5]:
            edge["type"] = "test_edge_type"
        
        return {
            "graph": base_graph,
            "test_queries": {
                "high_centrality": {
                    "min_centrality": 0.8,
                    "expected_count": 3,
                },
                "low_safety": {
                    "max_safety_score": 0.75,
                    "expected_count": 3,
                },
                "content_pattern": {
                    "pattern": "query pattern",
                    "expected_count": 2,
                },
                "edge_type": {
                    "edge_types": ["test_edge_type"],
                    "expected_edge_count": 5,
                },
            },
        }
    
    @staticmethod
    def create_export_format_fixtures() -> Dict[str, Any]:
        """Create fixtures for testing different export formats."""
        simple_graph = GraphFixtures.create_simple_graph()
        
        return {
            "graph": simple_graph,
            "expected_formats": {
                "mermaid": {
                    "contains": ["graph TD", "-->", "classDef"],
                    "node_count": 3,
                    "edge_count": 3,
                },
                "json": {
                    "has_keys": ["nodes", "edges", "metadata"],
                    "valid_json": True,
                },
                "d3": {
                    "has_keys": ["nodes", "links"],
                    "node_structure": ["id", "group", "value"],
                    "link_structure": ["source", "target", "value"],
                },
                "cytoscape": {
                    "has_keys": ["elements"],
                    "element_structure": ["data", "position"],
                },
                "graphml": {
                    "contains": ['<?xml', '<graphml', '<node', '<edge'],
                    "valid_xml": True,
                },
            },
        }