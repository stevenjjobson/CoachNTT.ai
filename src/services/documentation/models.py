"""
Data models for documentation generation service.

Defines types, configurations, and result structures for automated
documentation generation with safety compliance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path
from datetime import datetime
from decimal import Decimal


class DocumentationType(Enum):
    """Types of documentation that can be generated."""
    README = "readme"
    API_DOCS = "api_docs"
    CHANGELOG = "changelog"
    ARCHITECTURE = "architecture"
    CODE_REFERENCE = "code_reference"
    DIAGRAMS = "diagrams"


class DiagramType(Enum):
    """Types of diagrams that can be generated."""
    FLOWCHART = "flowchart"
    DEPENDENCY_GRAPH = "dependency_graph"
    CLASS_DIAGRAM = "class_diagram"
    SEQUENCE_DIAGRAM = "sequence_diagram"
    ARCHITECTURE_OVERVIEW = "architecture_overview"


@dataclass
class TemplateConfig:
    """Configuration for documentation templates."""
    
    template_name: str
    template_path: Optional[Path] = None
    template_content: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Safety settings
    enable_safety_validation: bool = True
    require_abstraction: bool = True
    max_concrete_references: int = 0
    
    # Output settings
    output_format: str = "markdown"
    include_metadata: bool = True
    include_generation_timestamp: bool = True


@dataclass
class DiagramConfig:
    """Configuration for diagram generation."""
    
    diagram_type: DiagramType
    include_dependencies: bool = True
    include_complexity_info: bool = False
    max_nodes: int = 50
    max_depth: int = 5
    
    # Mermaid-specific settings
    mermaid_theme: str = "default"
    node_styling: Dict[str, str] = field(default_factory=dict)
    edge_styling: Dict[str, str] = field(default_factory=dict)
    
    # Safety settings
    abstract_node_names: bool = True
    hide_private_members: bool = True


@dataclass
class DocumentationConfig:
    """Main configuration for documentation generation."""
    
    # Project settings
    project_root: Path
    docs_output_dir: Path
    project_name: str = "Project"
    project_description: str = ""
    
    # Generation settings
    enabled_types: List[DocumentationType] = field(default_factory=lambda: [
        DocumentationType.README,
        DocumentationType.API_DOCS,
        DocumentationType.ARCHITECTURE
    ])
    
    # Template settings
    templates_dir: Optional[Path] = None
    custom_templates: Dict[str, TemplateConfig] = field(default_factory=dict)
    
    # AST analysis settings
    analyze_code: bool = True
    include_complexity_metrics: bool = True
    include_dependency_analysis: bool = True
    
    # Git integration
    enable_git_integration: bool = True
    auto_commit_docs: bool = False
    changelog_from_git: bool = True
    
    # Safety settings
    safety_score_threshold: Decimal = Decimal("0.8")
    enforce_abstraction: bool = True
    validate_output: bool = True
    
    # Performance settings
    max_processing_time_seconds: int = 300
    enable_caching: bool = True
    parallel_processing: bool = True


@dataclass
class DocumentationMetadata:
    """Metadata for generated documentation."""
    
    generator_version: str = "1.0.0"
    generation_timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: int = 0
    
    # Source analysis info
    analyzed_files_count: int = 0
    functions_analyzed: int = 0
    classes_analyzed: int = 0
    total_lines_of_code: int = 0
    
    # Safety metrics
    safety_score: Decimal = Decimal("1.0")
    concrete_references_removed: int = 0
    abstraction_applied: bool = True
    
    # Generation statistics
    sections_generated: int = 0
    diagrams_generated: int = 0
    templates_used: List[str] = field(default_factory=list)


@dataclass
class DocumentationSection:
    """A section of generated documentation."""
    
    section_id: str
    title: str
    content: str
    section_type: str = "text"
    
    # Ordering and structure
    order: int = 0
    parent_section: Optional[str] = None
    subsections: List[str] = field(default_factory=list)
    
    # Metadata
    generated_from: List[str] = field(default_factory=list)  # Source files
    template_used: Optional[str] = None
    safety_validated: bool = False
    
    # Formatting
    format: str = "markdown"
    include_in_toc: bool = True


@dataclass
class DiagramResult:
    """Result of diagram generation."""
    
    diagram_type: DiagramType
    diagram_id: str
    
    # Content
    mermaid_code: str = ""
    rendered_path: Optional[Path] = None
    
    # Metadata
    nodes_count: int = 0
    edges_count: int = 0
    complexity_score: float = 0.0
    generation_time_ms: int = 0
    
    # Safety
    abstractions_applied: int = 0
    safety_compliant: bool = True


@dataclass
class DocumentationResult:
    """Complete result of documentation generation."""
    
    # Generation info
    config: DocumentationConfig
    metadata: DocumentationMetadata
    
    # Generated content
    sections: List[DocumentationSection] = field(default_factory=list)
    diagrams: List[DiagramResult] = field(default_factory=list)
    
    # File outputs
    generated_files: Dict[str, Path] = field(default_factory=dict)
    updated_files: List[Path] = field(default_factory=list)
    
    # Status
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def total_processing_time_ms(self) -> int:
        """Total processing time including all components."""
        return self.metadata.processing_time_ms
    
    @property
    def documentation_coverage(self) -> float:
        """Calculate documentation coverage score."""
        if self.metadata.functions_analyzed == 0 and self.metadata.classes_analyzed == 0:
            return 1.0
        
        documented_items = len([s for s in self.sections if s.section_type in ["function", "class"]])
        total_items = self.metadata.functions_analyzed + self.metadata.classes_analyzed
        
        return documented_items / max(1, total_items)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get generation summary."""
        return {
            'success': self.success,
            'processing_time_ms': self.total_processing_time_ms,
            'sections_generated': len(self.sections),
            'diagrams_generated': len(self.diagrams),
            'files_generated': len(self.generated_files),
            'files_updated': len(self.updated_files),
            'documentation_coverage': self.documentation_coverage,
            'safety_score': float(self.metadata.safety_score),
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings)
        }


@dataclass
class CodeAnalysisInput:
    """Input for code analysis during documentation generation."""
    
    file_path: Path
    content: Optional[str] = None
    language: Optional[str] = None
    
    # Analysis options
    include_functions: bool = True
    include_classes: bool = True
    include_imports: bool = True
    include_complexity: bool = True
    
    # Safety options
    abstract_content: bool = True
    validate_safety: bool = True


@dataclass 
class ChangelogEntry:
    """Entry in generated changelog."""
    
    version: str
    date: datetime
    description: str
    changes: List[str] = field(default_factory=list)
    
    # Git integration
    commit_hash: Optional[str] = None
    author: Optional[str] = None
    
    # Classification
    change_type: str = "feature"  # feature, bugfix, breaking, docs, etc.
    breaking_changes: List[str] = field(default_factory=list)


@dataclass
class APIDocEntry:
    """Entry for API documentation."""
    
    name: str
    type: str  # function, class, method, property
    signature: str
    description: str = ""
    
    # Details
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    return_description: str = ""
    
    # Examples and notes
    examples: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)
    
    # Safety
    abstracted_name: str = ""
    safety_validated: bool = False
    
    # Source info
    source_file: Optional[str] = None
    line_number: Optional[int] = None