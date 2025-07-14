"""
Vault synchronization services for Obsidian integration.

Provides memory-to-markdown conversion, template processing, and bidirectional
vault synchronization with safety-first abstraction.
"""

from .models import (
    VaultSyncConfig,
    VaultMetadata,
    MarkdownNote,
    SyncResult,
    ConflictInfo,
    TemplateVariable,
    BacklinkInfo,
    PerformanceMetrics,
    ConflictStrategy,
    TemplateType,
    SyncDirection
)

from .sync_engine import VaultSyncEngine
from .markdown_converter import MarkdownConverter
from .template_processor import TemplateProcessor
from .conflict_resolver import ConflictResolver
from .graph_builder import KnowledgeGraphBuilder
from .graph_models import (
    GraphNode,
    GraphEdge,
    KnowledgeGraph,
    NodeType,
    EdgeType,
    GraphQuery,
    GraphQueryResult
)
from .graph_exporters import (
    MermaidExporter,
    JSONExporter,
    GraphMLExporter
)

__all__ = [
    # Core services
    'VaultSyncEngine',
    'MarkdownConverter', 
    'TemplateProcessor',
    'ConflictResolver',
    
    # Configuration and metadata
    'VaultSyncConfig',
    'VaultMetadata',
    'PerformanceMetrics',
    
    # Data models
    'MarkdownNote',
    'SyncResult',
    'ConflictInfo',
    'TemplateVariable',
    'BacklinkInfo',
    
    # Enums
    'ConflictStrategy',
    'TemplateType',
    'SyncDirection',
    
    # Knowledge graph
    'KnowledgeGraphBuilder',
    'GraphNode',
    'GraphEdge',
    'KnowledgeGraph',
    'NodeType',
    'EdgeType',
    'GraphQuery',
    'GraphQueryResult',
    
    # Graph exporters
    'MermaidExporter',
    'JSONExporter',
    'GraphMLExporter'
]