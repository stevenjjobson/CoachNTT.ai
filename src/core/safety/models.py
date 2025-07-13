"""
Safety-first data models for the Cognitive Coding Partner.
All models enforce abstraction and validation requirements.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class ReferenceType(str, Enum):
    """Types of references that require abstraction."""
    FILE_PATH = "file_path"
    IDENTIFIER = "identifier"
    URL = "url"
    IP_ADDRESS = "ip_address"
    CONTAINER = "container"
    CONFIG_VALUE = "config_value"
    TIMESTAMP = "timestamp"
    TOKEN = "token"
    UNKNOWN = "unknown"


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Reference:
    """A concrete reference detected in content."""
    type: ReferenceType
    value: str
    position: tuple[int, int]  # start, end positions
    context: str  # surrounding text for context
    confidence: float = 1.0
    detection_rule: Optional[str] = None


@dataclass
class Abstraction:
    """An abstracted version of a concrete reference."""
    original: str
    abstracted: str
    reference_type: ReferenceType
    mapping_key: str  # unique key for this abstraction
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationError:
    """A validation error with context."""
    code: str
    message: str
    severity: ValidationSeverity
    context: Dict[str, Any]
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'message': self.message,
            'severity': self.severity.value,
            'context': self.context,
            'suggestion': self.suggestion,
            'timestamp': datetime.now().isoformat()
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    safety_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_critical_errors(self) -> bool:
        return any(e.severity == ValidationSeverity.CRITICAL for e in self.errors)
    
    @property
    def passed(self) -> bool:
        return self.valid and not self.has_critical_errors


@dataclass
class AbstractionResult:
    """Result of an abstraction operation."""
    original_content: str
    abstracted_content: str
    references: List[Reference]
    abstractions: List[Abstraction]
    mappings: Dict[str, str]  # original -> abstracted
    validation: ValidationResult
    processing_time_ms: float
    
    @property
    def coverage_score(self) -> float:
        """Percentage of references that were abstracted."""
        if not self.references:
            return 1.0
        return len(self.abstractions) / len(self.references)
    
    @property
    def is_safe(self) -> bool:
        """Whether the abstraction meets safety requirements."""
        return (self.validation.passed and 
                self.coverage_score == 1.0 and
                self.validation.safety_score >= 0.8)


@dataclass
class SafetyMetrics:
    """Metrics for tracking safety validation performance."""
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    safety_scores: List[float] = field(default_factory=list)
    validation_times: List[float] = field(default_factory=list)
    error_distribution: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_validations == 0:
            return 0.0
        return self.successful_validations / self.total_validations
    
    @property
    def average_safety_score(self) -> float:
        if not self.safety_scores:
            return 0.0
        return sum(self.safety_scores) / len(self.safety_scores)
    
    @property
    def p95_validation_time(self) -> float:
        if not self.validation_times:
            return 0.0
        sorted_times = sorted(self.validation_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]


@dataclass
class ConcreteReference:
    """A concrete reference found during abstraction."""
    type: ReferenceType
    value: str
    abstracted_to: str
    
    
@dataclass
class AbstractionMetadata:
    """Metadata about the abstraction process."""
    abstraction_score: float
    reference_mappings: Dict[str, str]
    validation_timestamp: datetime
    safety_violations: List[str]
    concrete_ref_count: int
    abstracted_ref_count: int