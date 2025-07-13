"""
Abstract memory models with mandatory safety validation.

All memory entries must be abstracted with placeholders replacing concrete references.
This module defines the core data structures for safe memory storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class ValidationStatus(Enum):
    """Memory validation status."""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class InteractionType(Enum):
    """Types of AI interactions."""
    CONVERSATION = "conversation"
    CODE_GENERATION = "code_generation"
    PROBLEM_SOLVING = "problem_solving"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"


class ReferenceType(Enum):
    """Types of concrete references that must be abstracted."""
    FILE_PATH = "file_path"
    URL = "url"
    CREDENTIAL = "credential"
    VARIABLE = "variable"
    API_ENDPOINT = "api_endpoint"
    DATABASE_CONNECTION = "database_connection"
    CONTAINER_NAME = "container_name"
    SERVICE_NAME = "service_name"
    USER_DATA = "user_data"


@dataclass
class Reference:
    """A concrete reference that needs abstraction."""
    ref_type: ReferenceType
    original_value: str
    placeholder: str
    context: Optional[str] = None
    
    def __post_init__(self):
        """Validate reference format."""
        if not self.placeholder.startswith("<") or not self.placeholder.endswith(">"):
            raise ValueError(f"Placeholder must be in format <name>, got: {self.placeholder}")
        
        # Ensure placeholder doesn't contain the original value
        if self.original_value.lower() in self.placeholder.lower():
            raise ValueError("Placeholder cannot contain the original value")


@dataclass
class ValidationResult:
    """Result of memory validation."""
    is_valid: bool
    safety_score: Decimal
    violations: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    
    def __post_init__(self):
        """Validate safety score range."""
        if not (Decimal("0.0") <= self.safety_score <= Decimal("1.0")):
            raise ValueError(f"Safety score must be between 0.0 and 1.0, got: {self.safety_score}")
        
        # Ensure invalid results have low scores
        if not self.is_valid and self.safety_score >= Decimal("0.8"):
            raise ValueError("Invalid results cannot have safety score >= 0.8")


@dataclass
class MemoryMetadata:
    """Metadata for memory entries."""
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    
    def __post_init__(self):
        """Validate metadata doesn't contain concrete references."""
        # Check tags
        for tag in self.tags:
            if "/" in tag or "\\" in tag or ":" in tag:
                raise ValueError(f"Tag contains path-like characters: {tag}")
        
        # Check context values
        self._validate_dict_safety(self.context)
    
    def _validate_dict_safety(self, data: Dict[str, Any], path: str = ""):
        """Recursively validate dictionary for concrete references."""
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check for sensitive keys
            if any(sensitive in key.lower() for sensitive in ["password", "secret", "token", "key"]):
                if isinstance(value, str) and len(value) > 0 and "<" not in value:
                    raise ValueError(f"Sensitive field {current_path} contains non-abstracted value")
            
            # Recursively check nested dictionaries
            if isinstance(value, dict):
                self._validate_dict_safety(value, current_path)
            elif isinstance(value, str):
                # Basic concrete reference checks
                if any(pattern in value for pattern in ["/home/", "C:\\", "://", "@"]):
                    if "<" not in value:  # Allow if it has placeholders
                        raise ValueError(f"Field {current_path} contains concrete reference: {value[:50]}...")


@dataclass
class AbstractionMapping:
    """Mapping between placeholders and concrete values."""
    mappings: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate mapping format."""
        for placeholder, value in self.mappings.items():
            if not (placeholder.startswith("<") and placeholder.endswith(">")):
                # Auto-wrap in brackets if not present
                clean_name = placeholder.strip("<>")
                del self.mappings[placeholder]
                self.mappings[f"<{clean_name}>"] = value
    
    def add_mapping(self, placeholder: str, concrete_value: str) -> None:
        """Add a new mapping with validation."""
        if not placeholder.startswith("<") or not placeholder.endswith(">"):
            placeholder = f"<{placeholder.strip('<>')}>"
        self.mappings[placeholder] = concrete_value
    
    def apply_to_text(self, text: str, reverse: bool = False) -> str:
        """Apply mappings to text (forward or reverse)."""
        result = text
        for placeholder, concrete in self.mappings.items():
            if reverse:
                result = result.replace(placeholder, concrete)
            else:
                result = result.replace(concrete, placeholder)
        return result


@dataclass
class AbstractMemoryEntry:
    """
    Abstract memory entry with mandatory safety validation.
    
    This is the core memory model that enforces abstraction of all concrete references.
    No memory can be created without proper abstraction and validation.
    """
    memory_id: UUID = field(default_factory=uuid4)
    abstracted_prompt: str = ""
    abstracted_response: str = ""
    abstracted_content: Dict[str, Any] = field(default_factory=dict)
    concrete_references: List[Reference] = field(default_factory=list)
    abstraction_mapping: AbstractionMapping = field(default_factory=AbstractionMapping)
    safety_score: Decimal = Decimal("0.0")
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_result: Optional[ValidationResult] = None
    quality_metrics_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate memory entry on creation."""
        # Ensure all text fields have placeholders if they have content
        if self.abstracted_prompt and "<" not in self.abstracted_prompt:
            if any(char in self.abstracted_prompt for char in ["/", "\\", "://", "@"]):
                raise ValueError("Prompt contains concrete references without placeholders")
        
        if self.abstracted_response and "<" not in self.abstracted_response:
            if any(char in self.abstracted_response for char in ["/", "\\", "://", "@"]):
                raise ValueError("Response contains concrete references without placeholders")
        
        # Validate safety score
        if self.validation_status == ValidationStatus.VALIDATED and self.safety_score < Decimal("0.8"):
            raise ValueError("Validated memories must have safety score >= 0.8")
        
        # Ensure rejected/quarantined memories have low scores
        if self.validation_status in [ValidationStatus.REJECTED, ValidationStatus.QUARANTINED]:
            if self.safety_score >= Decimal("0.8"):
                raise ValueError(f"{self.validation_status.value} memories cannot have safety score >= 0.8")
    
    @property
    def full_content(self) -> str:
        """Get all content combined for validation."""
        parts = []
        if self.abstracted_prompt:
            parts.append(self.abstracted_prompt)
        if self.abstracted_response:
            parts.append(self.abstracted_response)
        if self.abstracted_content:
            parts.append(str(self.abstracted_content))
        return " ".join(parts)
    
    def add_reference(self, ref_type: ReferenceType, original: str, placeholder: str, context: str = None) -> None:
        """Add a concrete reference with its abstraction."""
        ref = Reference(
            ref_type=ref_type,
            original_value=original,
            placeholder=placeholder,
            context=context
        )
        self.concrete_references.append(ref)
        self.abstraction_mapping.add_mapping(placeholder, original)
    
    def get_placeholder_count(self) -> int:
        """Count placeholders in all content."""
        import re
        pattern = r'<[a-zA-Z][a-zA-Z0-9_]*>'
        matches = re.findall(pattern, self.full_content)
        return len(matches)
    
    def get_placeholder_density(self) -> float:
        """Calculate placeholder density (placeholders per 100 characters)."""
        content_length = len(self.full_content)
        if content_length == 0:
            return 1.0  # Empty content is safe
        return (self.get_placeholder_count() / content_length) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "memory_id": str(self.memory_id),
            "abstracted_prompt": self.abstracted_prompt,
            "abstracted_response": self.abstracted_response,
            "abstracted_content": self.abstracted_content,
            "concrete_references": [
                {
                    "ref_type": ref.ref_type.value,
                    "original_value": ref.original_value,
                    "placeholder": ref.placeholder,
                    "context": ref.context
                }
                for ref in self.concrete_references
            ],
            "abstraction_mapping": self.abstraction_mapping.mappings,
            "safety_score": str(self.safety_score),
            "validation_status": self.validation_status.value,
            "validation_result": {
                "is_valid": self.validation_result.is_valid,
                "safety_score": str(self.validation_result.safety_score),
                "violations": self.validation_result.violations,
                "suggestions": self.validation_result.suggestions,
                "processing_time_ms": self.validation_result.processing_time_ms
            } if self.validation_result else None,
            "quality_metrics_id": str(self.quality_metrics_id) if self.quality_metrics_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class SafeInteraction:
    """
    Represents a safe interaction with the AI system.
    
    Links to an AbstractMemoryEntry and adds interaction-specific metadata.
    """
    interaction_id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    interaction_type: InteractionType = InteractionType.CONVERSATION
    abstraction_id: UUID = None  # Required link to AbstractMemoryEntry
    weight: Decimal = Decimal("1.0")
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)
    prompt_embedding: Optional[List[float]] = None
    response_embedding: Optional[List[float]] = None
    is_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate interaction data."""
        # Abstraction ID is mandatory
        if self.abstraction_id is None:
            raise ValueError("abstraction_id is required for SafeInteraction")
        
        # Validate weight range
        if not (Decimal("0.0") <= self.weight <= Decimal("1.0")):
            raise ValueError(f"Weight must be between 0.0 and 1.0, got: {self.weight}")
        
        # Validate embeddings if present
        if self.prompt_embedding and len(self.prompt_embedding) != 1536:
            raise ValueError(f"Prompt embedding must have 1536 dimensions, got: {len(self.prompt_embedding)}")
        
        if self.response_embedding and len(self.response_embedding) != 1536:
            raise ValueError(f"Response embedding must have 1536 dimensions, got: {len(self.response_embedding)}")
        
        # Ensure temporal consistency
        if self.last_accessed < self.created_at:
            self.last_accessed = self.created_at
    
    def record_access(self) -> None:
        """Record an access to this memory."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def calculate_decay(self, base_rate: float = 0.0001, min_weight: float = 0.01) -> Decimal:
        """Calculate weight decay based on time since last access."""
        days_elapsed = (datetime.utcnow() - self.last_accessed).days
        
        # Apply exponential decay
        import math
        new_weight = float(self.weight) * math.exp(-base_rate * days_elapsed)
        
        # Apply access count bonus
        if self.access_count > 1:
            new_weight *= (1 + math.log(self.access_count) * 0.05)
        
        # Enforce minimum and maximum
        new_weight = max(min_weight, min(1.0, new_weight))
        
        return Decimal(str(round(new_weight, 4)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "interaction_id": str(self.interaction_id),
            "session_id": str(self.session_id),
            "interaction_type": self.interaction_type.value,
            "abstraction_id": str(self.abstraction_id),
            "weight": str(self.weight),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "metadata": {
                "tags": self.metadata.tags,
                "context": self.metadata.context,
                "source": self.metadata.source,
                "language": self.metadata.language,
                "framework": self.metadata.framework
            },
            "prompt_embedding": self.prompt_embedding,
            "response_embedding": self.response_embedding,
            "is_validated": self.is_validated,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }