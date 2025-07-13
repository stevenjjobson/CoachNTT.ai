"""
Data models for AST code analysis.

All models enforce safety-first abstraction of concrete references.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Union
from enum import Enum
from decimal import Decimal
from uuid import UUID, uuid4


class LanguageType(Enum):
    """Supported programming languages for AST analysis."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


class PatternType(Enum):
    """Design patterns that can be detected."""
    SINGLETON = "singleton"
    FACTORY = "factory"
    OBSERVER = "observer"
    STRATEGY = "strategy"
    DECORATOR = "decorator"
    ADAPTER = "adapter"
    COMMAND = "command"
    FACADE = "facade"


class QualityLevel(Enum):
    """Code quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class AnalysisMetadata:
    """Metadata for analysis operations."""
    analysis_id: UUID = field(default_factory=uuid4)
    timestamp: float = field(default_factory=time.time)
    processing_time_ms: int = 0
    safety_score: Decimal = field(default=Decimal("0.0"))
    abstraction_performed: bool = False
    concrete_references_found: int = 0


@dataclass
class ComplexityMetrics:
    """Code complexity measurements."""
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    lines_of_code: int = 0
    maintainability_index: float = 0.0
    halstead_difficulty: float = 0.0
    
    def get_complexity_level(self) -> QualityLevel:
        """Determine complexity level based on metrics."""
        # Use cyclomatic complexity as primary indicator
        if self.cyclomatic_complexity <= 5:
            return QualityLevel.EXCELLENT
        elif self.cyclomatic_complexity <= 10:
            return QualityLevel.GOOD
        elif self.cyclomatic_complexity <= 20:
            return QualityLevel.FAIR
        elif self.cyclomatic_complexity <= 30:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL


@dataclass
class FunctionSignature:
    """Abstracted function signature information."""
    name_pattern: str  # Abstracted function name (e.g., "<function_verb_noun>")
    parameter_count: int = 0
    parameter_types: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    is_async: bool = False
    is_generator: bool = False
    decorators: List[str] = field(default_factory=list)
    docstring_present: bool = False
    complexity_metrics: Optional[ComplexityMetrics] = None
    
    def get_signature_pattern(self) -> str:
        """Generate abstracted signature pattern."""
        params = f"<{self.parameter_count}_params>"
        async_prefix = "async " if self.is_async else ""
        return_info = f" -> <{self.return_type}>" if self.return_type else ""
        
        return f"{async_prefix}{self.name_pattern}({params}){return_info}"


@dataclass 
class ClassStructure:
    """Abstracted class structure information."""
    name_pattern: str  # Abstracted class name (e.g., "<class_concept>")
    method_count: int = 0
    property_count: int = 0
    inheritance_depth: int = 0
    base_class_patterns: List[str] = field(default_factory=list)
    methods: List[FunctionSignature] = field(default_factory=list)
    has_init: bool = False
    has_str: bool = False
    has_repr: bool = False
    design_patterns: List[PatternType] = field(default_factory=list)
    
    def get_class_pattern(self) -> str:
        """Generate abstracted class pattern."""
        inheritance = f"(<{len(self.base_class_patterns)}_bases>)" if self.base_class_patterns else ""
        return f"{self.name_pattern}{inheritance}"


@dataclass
class VariableScope:
    """Variable scope and usage tracking."""
    scope_type: str  # "global", "local", "class", "instance"
    variable_patterns: Set[str] = field(default_factory=set)
    assignments: int = 0
    references: int = 0
    modifications: int = 0
    
    def get_usage_ratio(self) -> float:
        """Calculate variable usage efficiency."""
        if self.assignments == 0:
            return 0.0
        return (self.references + self.modifications) / self.assignments


@dataclass
class DependencyNode:
    """Node in the dependency graph."""
    node_id: str
    node_type: str  # "function", "class", "module"
    name_pattern: str  # Abstracted name
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    
    def get_coupling_score(self) -> float:
        """Calculate coupling score (lower is better)."""
        total_connections = len(self.dependencies) + len(self.dependents)
        return min(total_connections / 10.0, 1.0)  # Normalize to 0-1


@dataclass
class PatternMatch:
    """Detected design pattern match."""
    pattern_type: PatternType
    confidence: float
    elements: List[str] = field(default_factory=list)  # Abstracted element names
    explanation: str = ""
    location_pattern: str = ""  # Abstracted location (e.g., "<class_at_line_range>")
    
    def is_confident_match(self) -> bool:
        """Check if pattern match is confident enough."""
        return self.confidence >= 0.7


@dataclass
class DesignPattern:
    """Complete design pattern analysis."""
    pattern_type: PatternType
    matches: List[PatternMatch] = field(default_factory=list)
    overall_confidence: float = 0.0
    
    def get_best_match(self) -> Optional[PatternMatch]:
        """Get the most confident pattern match."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.confidence)


@dataclass
class QualityIssue:
    """Code quality issue detected."""
    issue_type: str
    severity: QualityLevel
    description: str
    location_pattern: str  # Abstracted location
    suggestion: str = ""
    
    def is_critical(self) -> bool:
        """Check if issue is critical."""
        return self.severity in [QualityLevel.CRITICAL, QualityLevel.POOR]


@dataclass
class QualityMetrics:
    """Overall code quality assessment."""
    overall_score: float = 0.0  # 0.0-1.0
    maintainability: float = 0.0
    readability: float = 0.0
    testability: float = 0.0
    issues: List[QualityIssue] = field(default_factory=list)
    
    def get_quality_level(self) -> QualityLevel:
        """Determine overall quality level."""
        if self.overall_score >= 0.9:
            return QualityLevel.EXCELLENT
        elif self.overall_score >= 0.7:
            return QualityLevel.GOOD
        elif self.overall_score >= 0.5:
            return QualityLevel.FAIR
        elif self.overall_score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def get_critical_issues(self) -> List[QualityIssue]:
        """Get all critical quality issues."""
        return [issue for issue in self.issues if issue.is_critical()]


@dataclass
class AnalysisResult:
    """Complete AST analysis result."""
    metadata: AnalysisMetadata = field(default_factory=AnalysisMetadata)
    language: LanguageType = LanguageType.UNKNOWN
    
    # Structure analysis
    functions: List[FunctionSignature] = field(default_factory=list)
    classes: List[ClassStructure] = field(default_factory=list)
    variables: Dict[str, VariableScope] = field(default_factory=dict)
    
    # Pattern analysis
    design_patterns: List[DesignPattern] = field(default_factory=list)
    complexity_metrics: Optional[ComplexityMetrics] = None
    
    # Dependency analysis
    dependency_graph: Dict[str, DependencyNode] = field(default_factory=dict)
    
    # Quality assessment
    quality_metrics: Optional[QualityMetrics] = None
    
    # Safety and abstraction
    abstracted_content: str = ""
    concrete_references_removed: int = 0
    
    def is_analysis_complete(self) -> bool:
        """Check if analysis is complete and valid."""
        return (
            self.language != LanguageType.UNKNOWN and
            self.metadata.safety_score >= Decimal("0.8") and
            (len(self.functions) > 0 or len(self.classes) > 0)
        )
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the analysis."""
        return {
            'language': self.language.value,
            'function_count': len(self.functions),
            'class_count': len(self.classes),
            'pattern_count': len(self.design_patterns),
            'complexity_score': self.complexity_metrics.cyclomatic_complexity if self.complexity_metrics else 0,
            'quality_score': self.quality_metrics.overall_score if self.quality_metrics else 0.0,
            'safety_score': float(self.metadata.safety_score),
            'processing_time_ms': self.metadata.processing_time_ms
        }
    
    def get_detected_patterns(self) -> List[PatternType]:
        """Get list of confidently detected patterns."""
        patterns = []
        for design_pattern in self.design_patterns:
            best_match = design_pattern.get_best_match()
            if best_match and best_match.is_confident_match():
                patterns.append(design_pattern.pattern_type)
        return patterns


# Constants for analysis validation
MIN_SAFETY_SCORE = Decimal("0.8")
MAX_PROCESSING_TIME_MS = 5000  # 5 seconds max
DEFAULT_CONFIDENCE_THRESHOLD = 0.7