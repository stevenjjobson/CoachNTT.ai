"""
Knowledge graph builder for creating semantic connections between memories and code.

Orchestrates node extraction, edge detection, and graph construction with
safety-first design and temporal weighting.
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta
from pathlib import Path
import math

from .graph_models import (
    GraphNode, GraphEdge, KnowledgeGraph,
    NodeType, EdgeType, GraphQuery, GraphQueryResult
)

from ...core.memory.repository import SafeMemoryRepository
from ...core.memory.abstract_models import AbstractMemoryEntry
from ...core.analysis.ast_analyzer import ASTAnalyzer
from ...core.analysis.models import AnalysisResult
from ...core.embeddings.service import EmbeddingService
from ...core.embeddings.models import ContentType
from ...core.intent.engine import IntentEngine
from ...core.intent.connections import ConnectionFinder
from ...core.validation.validator import SafetyValidator

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """
    Main engine for building knowledge graphs from various sources.
    
    Integrates memory repository, code analysis, and intent connections
    to create a comprehensive semantic graph with safety validation.
    """
    
    def __init__(
        self,
        memory_repository: SafeMemoryRepository,
        ast_analyzer: Optional[ASTAnalyzer] = None,
        embedding_service: Optional[EmbeddingService] = None,
        intent_engine: Optional[IntentEngine] = None,
        safety_validator: Optional[SafetyValidator] = None,
        enable_code_analysis: bool = True,
        enable_temporal_weighting: bool = True
    ):
        """
        Initialize knowledge graph builder.
        
        Args:
            memory_repository: Repository for accessing memories
            ast_analyzer: AST analyzer for code understanding
            embedding_service: Service for semantic similarity
            intent_engine: Intent analysis engine
            safety_validator: Safety validator for content
            enable_code_analysis: Whether to include code nodes
            enable_temporal_weighting: Whether to weight by time
        """
        self.memory_repository = memory_repository
        self.ast_analyzer = ast_analyzer
        self.embedding_service = embedding_service
        self.intent_engine = intent_engine
        self.safety_validator = safety_validator or SafetyValidator()
        self.enable_code_analysis = enable_code_analysis
        self.enable_temporal_weighting = enable_temporal_weighting
        
        # Configuration
        self.similarity_threshold = 0.7
        self.temporal_decay_constant = 168  # Hours (1 week)
        self.min_edge_weight = 0.3
        self.batch_size = 100
        
        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}
        
        # Statistics
        self._stats = {
            'graphs_built': 0,
            'nodes_created': 0,
            'edges_created': 0,
            'memories_processed': 0,
            'code_files_analyzed': 0,
            'safety_violations': 0,
            'total_build_time_ms': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("KnowledgeGraphBuilder initialized")
    
    async def build_graph(
        self,
        memory_ids: Optional[List[UUID]] = None,
        code_paths: Optional[List[Path]] = None,
        max_memories: int = 100,
        include_related: bool = True,
        graph_name: Optional[str] = None
    ) -> KnowledgeGraph:
        """
        Build a knowledge graph from memories and code.
        
        Args:
            memory_ids: Specific memory IDs to include
            code_paths: Code files to analyze
            max_memories: Maximum memories to process
            include_related: Whether to include related memories
            graph_name: Optional name for the graph
            
        Returns:
            Constructed knowledge graph
        """
        start_time = time.time()
        
        try:
            logger.info(f"Building knowledge graph (max_memories={max_memories})")
            
            # Initialize graph
            graph = KnowledgeGraph(
                name=graph_name or f"knowledge_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Safety-validated semantic knowledge graph"
            )
            
            # Step 1: Extract memory nodes
            memory_nodes = await self._extract_memory_nodes(
                memory_ids, max_memories, include_related
            )
            for node in memory_nodes:
                graph.add_node(node)
            
            self._stats['memories_processed'] += len(memory_nodes)
            logger.debug(f"Added {len(memory_nodes)} memory nodes")
            
            # Step 2: Extract code nodes (if enabled)
            if self.enable_code_analysis and self.ast_analyzer and code_paths:
                code_nodes = await self._extract_code_nodes(code_paths)
                for node in code_nodes:
                    graph.add_node(node)
                
                self._stats['code_files_analyzed'] += len(code_paths)
                logger.debug(f"Added {len(code_nodes)} code nodes")
            
            # Step 3: Detect semantic edges
            if self.embedding_service:
                semantic_edges = await self._detect_semantic_edges(graph)
                for edge in semantic_edges:
                    graph.add_edge(edge)
                
                logger.debug(f"Added {len(semantic_edges)} semantic edges")
            
            # Step 4: Detect temporal edges
            if self.enable_temporal_weighting:
                temporal_edges = await self._detect_temporal_edges(graph)
                for edge in temporal_edges:
                    graph.add_edge(edge)
                
                logger.debug(f"Added {len(temporal_edges)} temporal edges")
            
            # Step 5: Detect code dependency edges
            if self.enable_code_analysis and code_nodes:
                dependency_edges = await self._detect_code_dependencies(graph)
                for edge in dependency_edges:
                    graph.add_edge(edge)
                
                logger.debug(f"Added {len(dependency_edges)} dependency edges")
            
            # Step 6: Calculate graph metrics
            metrics = graph.calculate_metrics()
            
            # Update statistics
            graph.build_time_ms = (time.time() - start_time) * 1000
            self._stats['graphs_built'] += 1
            self._stats['nodes_created'] += graph.node_count
            self._stats['edges_created'] += graph.edge_count
            self._stats['total_build_time_ms'] += graph.build_time_ms
            
            logger.info(
                f"Graph built successfully: {graph.node_count} nodes, "
                f"{graph.edge_count} edges, {graph.build_time_ms:.1f}ms"
            )
            
            return graph
            
        except Exception as e:
            logger.error(f"Graph building failed: {e}")
            raise
    
    async def _extract_memory_nodes(
        self,
        memory_ids: Optional[List[UUID]],
        max_memories: int,
        include_related: bool
    ) -> List[GraphNode]:
        """Extract nodes from memories."""
        nodes = []
        
        try:
            # Get memories
            if memory_ids:
                memories = []
                for memory_id in memory_ids[:max_memories]:
                    memory = await self.memory_repository.get_memory(memory_id)
                    if memory:
                        memories.append(memory)
            else:
                # Get recent memories
                search_results = await self.memory_repository.search_with_clustering(
                    query="*",  # Will be abstracted
                    limit=max_memories
                )
                memories = []
                for result in search_results:
                    memory = await self.memory_repository.get_memory(result['memory_id'])
                    if memory:
                        memories.append(memory)
            
            # Convert to nodes
            for memory in memories:
                node = await self._memory_to_node(memory)
                if node:
                    nodes.append(node)
            
            # Include related memories if requested
            if include_related and self.intent_engine:
                related_nodes = await self._find_related_memory_nodes(memories)
                nodes.extend(related_nodes)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Memory node extraction failed: {e}")
            return nodes
    
    async def _memory_to_node(self, memory: AbstractMemoryEntry) -> Optional[GraphNode]:
        """Convert a memory to a graph node."""
        try:
            # Create content hash
            content = f"{memory.abstracted_prompt}|{memory.abstracted_response}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # Generate embedding if available
            embedding = None
            if self.embedding_service:
                cached_key = f"memory_{memory.memory_id}"
                if cached_key in self._embedding_cache:
                    embedding = self._embedding_cache[cached_key]
                    self._stats['cache_hits'] += 1
                else:
                    result = await self.embedding_service.generate_embedding(
                        content=memory.abstracted_prompt,
                        content_type=ContentType.TEXT
                    )
                    embedding = result.vector
                    self._embedding_cache[cached_key] = embedding
                    self._stats['cache_misses'] += 1
            
            node = GraphNode(
                node_type=NodeType.MEMORY,
                content_hash=content_hash,
                title_pattern=f"<memory_{content_hash}>",
                description_pattern=memory.abstracted_prompt[:100] + "...",
                abstracted_content={
                    'prompt': memory.abstracted_prompt,
                    'response': memory.abstracted_response,
                    'metadata': memory.abstracted_content
                },
                source_id=memory.memory_id,
                source_type="memory",
                safety_score=memory.safety_score,
                is_validated=memory.validation_status.value == "validated",
                created_at=memory.created_at,
                embedding=embedding
            )
            
            return node
            
        except Exception as e:
            logger.warning(f"Failed to convert memory to node: {e}")
            self._stats['safety_violations'] += 1
            return None
    
    async def _extract_code_nodes(self, code_paths: List[Path]) -> List[GraphNode]:
        """Extract nodes from code files."""
        nodes = []
        
        for path in code_paths:
            try:
                if not path.exists():
                    continue
                
                content = path.read_text(encoding='utf-8')
                
                # Analyze code
                analysis = await self.ast_analyzer.analyze_code(
                    content=content,
                    filename=str(path)
                )
                
                # Create module node
                module_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                module_node = GraphNode(
                    node_type=NodeType.CODE_MODULE,
                    content_hash=module_hash,
                    title_pattern=f"<module_{path.stem}>",
                    description_pattern=f"Code module with {len(analysis.functions)} functions",
                    abstracted_content={
                        'language': analysis.language.value,
                        'functions': len(analysis.functions),
                        'classes': len(analysis.classes),
                        'complexity': analysis.aggregate_complexity
                    },
                    source_id=None,
                    source_type="ast_analysis",
                    source_file=str(path),
                    safety_score=Decimal(str(analysis.metadata.safety_score)),
                    is_validated=True
                )
                nodes.append(module_node)
                
                # Create function nodes
                for func in analysis.functions:
                    func_node = GraphNode(
                        node_type=NodeType.CODE_FUNCTION,
                        content_hash=hashlib.sha256(func.name_pattern.encode()).hexdigest()[:16],
                        title_pattern=func.name_pattern,
                        description_pattern=f"Function with {func.parameter_count} parameters",
                        abstracted_content={
                            'parameters': func.parameter_count,
                            'return_type': func.return_type,
                            'is_async': func.is_async,
                            'has_docstring': func.docstring_present
                        },
                        source_type="ast_analysis",
                        source_file=str(path),
                        safety_score=Decimal("1.0"),
                        is_validated=True
                    )
                    nodes.append(func_node)
                
                # Create class nodes
                for cls in analysis.classes:
                    class_node = GraphNode(
                        node_type=NodeType.CODE_CLASS,
                        content_hash=hashlib.sha256(cls.name_pattern.encode()).hexdigest()[:16],
                        title_pattern=cls.name_pattern,
                        description_pattern=f"Class with {cls.method_count} methods",
                        abstracted_content={
                            'methods': cls.method_count,
                            'properties': cls.property_count,
                            'base_classes': cls.base_class_patterns,
                            'has_init': cls.has_init
                        },
                        source_type="ast_analysis",
                        source_file=str(path),
                        safety_score=Decimal("1.0"),
                        is_validated=True
                    )
                    nodes.append(class_node)
                
            except Exception as e:
                logger.warning(f"Failed to extract nodes from {path}: {e}")
                continue
        
        return nodes
    
    async def _detect_semantic_edges(self, graph: KnowledgeGraph) -> List[GraphEdge]:
        """Detect edges based on semantic similarity."""
        edges = []
        
        if not self.embedding_service:
            return edges
        
        # Get nodes with embeddings
        nodes_with_embeddings = [
            node for node in graph.nodes.values()
            if node.embedding is not None
        ]
        
        # Compare pairs
        for i, node1 in enumerate(nodes_with_embeddings):
            for j, node2 in enumerate(nodes_with_embeddings[i+1:], i+1):
                try:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(node1.embedding, node2.embedding)
                    
                    if similarity >= self.similarity_threshold:
                        # Determine edge type based on node types
                        edge_type = self._determine_edge_type(node1, node2, similarity)
                        
                        # Calculate temporal weight if applicable
                        temporal_weight = 1.0
                        temporal_distance = None
                        
                        if self.enable_temporal_weighting:
                            temporal_weight, temporal_distance = self._calculate_temporal_weight(
                                node1.created_at, node2.created_at
                            )
                        
                        edge = GraphEdge(
                            source_node_id=node1.node_id,
                            target_node_id=node2.node_id,
                            edge_type=edge_type,
                            weight=similarity,
                            confidence=0.9,  # High confidence for embedding similarity
                            temporal_distance_hours=temporal_distance,
                            temporal_weight=temporal_weight,
                            explanation_pattern=f"Semantic similarity of {similarity:.2f}",
                            reasoning=["Embedding vector similarity above threshold"],
                            safety_score=min(node1.safety_score, node2.safety_score),
                            is_validated=True,
                            is_bidirectional=True
                        )
                        
                        edges.append(edge)
                        
                except Exception as e:
                    logger.warning(f"Failed to create semantic edge: {e}")
                    continue
        
        return edges
    
    async def _detect_temporal_edges(self, graph: KnowledgeGraph) -> List[GraphEdge]:
        """Detect edges based on temporal proximity."""
        edges = []
        
        # Get memory nodes sorted by time
        memory_nodes = sorted(
            [n for n in graph.nodes.values() if n.node_type == NodeType.MEMORY],
            key=lambda n: n.created_at
        )
        
        # Find temporal sequences
        for i, node1 in enumerate(memory_nodes):
            for j, node2 in enumerate(memory_nodes[i+1:], i+1):
                time_diff = (node2.created_at - node1.created_at).total_seconds() / 3600
                
                # Check if within temporal window
                if time_diff <= 24:  # 24 hours
                    # Calculate temporal weight
                    temporal_weight = math.exp(-time_diff / self.temporal_decay_constant)
                    
                    if temporal_weight >= self.min_edge_weight:
                        edge = GraphEdge(
                            source_node_id=node1.node_id,
                            target_node_id=node2.node_id,
                            edge_type=EdgeType.FOLLOWS,
                            weight=temporal_weight,
                            confidence=0.8,
                            temporal_distance_hours=time_diff,
                            temporal_weight=temporal_weight,
                            explanation_pattern=f"Temporal sequence with {time_diff:.1f} hours gap",
                            reasoning=["Temporal proximity within window"],
                            safety_score=min(node1.safety_score, node2.safety_score),
                            is_validated=True,
                            is_bidirectional=False
                        )
                        
                        edges.append(edge)
        
        return edges
    
    async def _detect_code_dependencies(self, graph: KnowledgeGraph) -> List[GraphEdge]:
        """Detect edges based on code dependencies."""
        edges = []
        
        # Get code nodes by file
        nodes_by_file: Dict[str, List[GraphNode]] = {}
        for node in graph.nodes.values():
            if node.source_file and node.node_type in [NodeType.CODE_FUNCTION, NodeType.CODE_CLASS]:
                if node.source_file not in nodes_by_file:
                    nodes_by_file[node.source_file] = []
                nodes_by_file[node.source_file].append(node)
        
        # Create edges within files (simplified - real implementation would use AST)
        for file_nodes in nodes_by_file.values():
            module_node = next(
                (n for n in graph.nodes.values() 
                 if n.node_type == NodeType.CODE_MODULE and n.source_file == file_nodes[0].source_file),
                None
            )
            
            if module_node:
                for node in file_nodes:
                    edge = GraphEdge(
                        source_node_id=module_node.node_id,
                        target_node_id=node.node_id,
                        edge_type=EdgeType.DEPENDS_ON,
                        weight=0.9,
                        confidence=1.0,
                        explanation_pattern="Module contains code element",
                        reasoning=["Structural containment relationship"],
                        safety_score=Decimal("1.0"),
                        is_validated=True,
                        is_bidirectional=False
                    )
                    edges.append(edge)
        
        return edges
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _determine_edge_type(
        self, 
        node1: GraphNode, 
        node2: GraphNode, 
        similarity: float
    ) -> EdgeType:
        """Determine edge type based on nodes and similarity."""
        # High similarity suggests close relationship
        if similarity > 0.9:
            return EdgeType.SIMILAR_TO
        
        # Different types suggest explanation relationship
        if node1.node_type != node2.node_type:
            if node1.node_type == NodeType.CODE_FUNCTION and node2.node_type == NodeType.MEMORY:
                return EdgeType.EXPLAINS
            elif node1.node_type == NodeType.MEMORY and node2.node_type == NodeType.CODE_FUNCTION:
                return EdgeType.EXPLAINS
        
        # Default to related
        return EdgeType.RELATED_TO
    
    def _calculate_temporal_weight(
        self, 
        time1: datetime, 
        time2: datetime
    ) -> Tuple[float, float]:
        """Calculate temporal weight between two timestamps."""
        time_diff_hours = abs((time2 - time1).total_seconds()) / 3600
        temporal_weight = math.exp(-time_diff_hours / self.temporal_decay_constant)
        return temporal_weight, time_diff_hours
    
    async def _find_related_memory_nodes(
        self, 
        base_memories: List[AbstractMemoryEntry]
    ) -> List[GraphNode]:
        """Find related memories using intent engine."""
        related_nodes = []
        
        if not self.intent_engine:
            return related_nodes
        
        # This is simplified - real implementation would use ConnectionFinder
        # to find semantic and temporal connections
        
        return related_nodes
    
    async def query_graph(
        self,
        graph: KnowledgeGraph,
        query: GraphQuery
    ) -> GraphQueryResult:
        """
        Query the knowledge graph with filters.
        
        Args:
            graph: Knowledge graph to query
            query: Query parameters
            
        Returns:
            Query results with filtered nodes and edges
        """
        start_time = time.time()
        result = GraphQueryResult(query=query)
        
        try:
            # Filter nodes
            filtered_nodes = []
            for node in graph.nodes.values():
                # Check node type filter
                if query.node_types and node.node_type not in query.node_types:
                    continue
                
                # Check safety score
                if float(node.safety_score) < query.min_node_safety_score:
                    continue
                
                # Check creation time
                if query.node_created_after and node.created_at < query.node_created_after:
                    continue
                
                # Check content pattern
                if query.node_content_pattern:
                    pattern = query.node_content_pattern.lower()
                    if (pattern not in node.title_pattern.lower() and 
                        pattern not in node.description_pattern.lower()):
                        continue
                
                filtered_nodes.append(node)
                result.nodes_examined += 1
            
            # Sort nodes
            if query.sort_by == "centrality":
                filtered_nodes.sort(key=lambda n: n.centrality_score, reverse=query.sort_descending)
            elif query.sort_by == "created_at":
                filtered_nodes.sort(key=lambda n: n.created_at, reverse=query.sort_descending)
            elif query.sort_by == "safety_score":
                filtered_nodes.sort(key=lambda n: n.safety_score, reverse=query.sort_descending)
            
            # Limit nodes
            result.nodes = filtered_nodes[:query.max_nodes]
            
            # Filter edges
            node_ids = {n.node_id for n in result.nodes}
            filtered_edges = []
            
            for edge in graph.edges.values():
                # Check if nodes are in result
                if (edge.source_node_id not in node_ids or 
                    edge.target_node_id not in node_ids):
                    continue
                
                # Check edge type filter
                if query.edge_types and edge.edge_type not in query.edge_types:
                    continue
                
                # Check weight and confidence
                if edge.weight < query.min_edge_weight:
                    continue
                if edge.confidence < query.min_edge_confidence:
                    continue
                
                filtered_edges.append(edge)
                result.edges_examined += 1
            
            # Limit edges
            result.edges = filtered_edges[:query.max_edges]
            
            # Create subgraph if requested
            if len(result.nodes) > 0:
                subgraph = KnowledgeGraph(
                    name=f"{graph.name}_query_result",
                    description="Query result subgraph"
                )
                
                for node in result.nodes:
                    subgraph.add_node(node)
                
                for edge in result.edges:
                    if (edge.source_node_id in subgraph.nodes and 
                        edge.target_node_id in subgraph.nodes):
                        subgraph.add_edge(edge)
                
                result.subgraph = subgraph
            
            result.query_time_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Graph query completed: {len(result.nodes)} nodes, "
                f"{len(result.edges)} edges in {result.query_time_ms:.1f}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            result.query_time_ms = (time.time() - start_time) * 1000
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get builder statistics."""
        stats = self._stats.copy()
        
        # Add cache statistics
        total_lookups = stats['cache_hits'] + stats['cache_misses']
        stats['cache_hit_rate'] = (
            stats['cache_hits'] / total_lookups if total_lookups > 0 else 0.0
        )
        
        # Add averages
        if stats['graphs_built'] > 0:
            stats['avg_nodes_per_graph'] = stats['nodes_created'] / stats['graphs_built']
            stats['avg_edges_per_graph'] = stats['edges_created'] / stats['graphs_built']
            stats['avg_build_time_ms'] = stats['total_build_time_ms'] / stats['graphs_built']
        
        return stats