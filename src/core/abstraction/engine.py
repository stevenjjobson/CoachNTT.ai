"""
AbstractionEngine: Core engine for abstracting concrete references.
This is the foundation of CCP's safety-first design.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from src.core.safety.models import (
    AbstractionResult,
    Reference,
    Abstraction,
    ValidationResult,
    ReferenceType
)


logger = logging.getLogger(__name__)


class AbstractionEngine(ABC):
    """
    Base class for abstraction operations.
    All concrete reference abstraction flows through this engine.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the abstraction engine.
        
        Args:
            config: Configuration dictionary for the engine
        """
        self.config = config or {}
        self.patterns = self._load_patterns()
        self.validators = self._load_validators()
        self._initialize()
    
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize engine-specific resources."""
        pass
    
    @abstractmethod
    def _load_patterns(self) -> Dict[str, Any]:
        """Load abstraction patterns for different reference types."""
        pass
    
    @abstractmethod
    def _load_validators(self) -> Dict[str, Any]:
        """Load validators for abstraction quality."""
        pass
    
    def abstract(self, content: str, context: Optional[Dict[str, Any]] = None) -> AbstractionResult:
        """
        Main abstraction method - converts concrete references to abstractions.
        
        Args:
            content: The content to abstract
            context: Additional context for abstraction decisions
            
        Returns:
            AbstractionResult with abstracted content and validation
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # Step 1: Detect all concrete references
            references = self._detect_references(content, context)
            logger.info(f"Detected {len(references)} references in content")
            
            # Step 2: Generate abstractions for each reference
            abstractions = self._generate_abstractions(references, context)
            logger.info(f"Generated {len(abstractions)} abstractions")
            
            # Step 3: Apply abstractions to content
            abstracted_content, mappings = self._apply_abstractions(
                content, abstractions
            )
            
            # Step 4: Validate the abstraction quality
            validation = self._validate_abstractions(
                content, abstracted_content, abstractions, mappings
            )
            
            # Step 5: Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            return AbstractionResult(
                original_content=content,
                abstracted_content=abstracted_content,
                references=references,
                abstractions=abstractions,
                mappings=mappings,
                validation=validation,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Abstraction failed: {str(e)}")
            # Return a failed result rather than raising
            return self._create_failed_result(content, str(e))
    
    @abstractmethod
    def _detect_references(self, content: str, context: Dict[str, Any]) -> List[Reference]:
        """
        Detect all concrete references in the content.
        
        Args:
            content: Content to scan for references
            context: Additional context
            
        Returns:
            List of detected references
        """
        pass
    
    @abstractmethod
    def _generate_abstractions(
        self, references: List[Reference], context: Dict[str, Any]
    ) -> List[Abstraction]:
        """
        Generate appropriate abstractions for each reference.
        
        Args:
            references: List of concrete references
            context: Additional context
            
        Returns:
            List of abstractions
        """
        pass
    
    def _apply_abstractions(
        self, content: str, abstractions: List[Abstraction]
    ) -> tuple[str, Dict[str, str]]:
        """
        Apply abstractions to content, replacing concrete with abstract.
        
        Args:
            content: Original content
            abstractions: List of abstractions to apply
            
        Returns:
            Tuple of (abstracted_content, mappings)
        """
        abstracted = content
        mappings = {}
        
        # Sort abstractions by position (reverse) to avoid position shifts
        sorted_abstractions = sorted(
            abstractions,
            key=lambda a: self._get_abstraction_position(a, content),
            reverse=True
        )
        
        for abstraction in sorted_abstractions:
            if abstraction.original in abstracted:
                abstracted = abstracted.replace(
                    abstraction.original,
                    abstraction.abstracted
                )
                mappings[abstraction.original] = abstraction.abstracted
            else:
                logger.warning(
                    f"Could not find '{abstraction.original}' in content"
                )
        
        return abstracted, mappings
    
    def _get_abstraction_position(self, abstraction: Abstraction, content: str) -> int:
        """Get the position of an abstraction in content."""
        pos = content.find(abstraction.original)
        return pos if pos >= 0 else len(content)
    
    @abstractmethod
    def _validate_abstractions(
        self,
        original: str,
        abstracted: str,
        abstractions: List[Abstraction],
        mappings: Dict[str, str]
    ) -> ValidationResult:
        """
        Validate the quality and safety of abstractions.
        
        Args:
            original: Original content
            abstracted: Abstracted content
            abstractions: List of abstractions applied
            mappings: Mapping of original to abstracted
            
        Returns:
            Validation result with safety score
        """
        pass
    
    def _create_failed_result(self, content: str, error_message: str) -> AbstractionResult:
        """Create a failed abstraction result."""
        from src.core.safety.models import ValidationError, ValidationSeverity
        
        validation = ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    code="E_ABSTRACTION_FAILED",
                    message=f"Abstraction failed: {error_message}",
                    severity=ValidationSeverity.CRITICAL,
                    context={"error": error_message}
                )
            ],
            safety_score=0.0
        )
        
        return AbstractionResult(
            original_content=content,
            abstracted_content=content,  # Return original on failure
            references=[],
            abstractions=[],
            mappings={},
            validation=validation,
            processing_time_ms=0.0
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the abstraction engine."""
        return {
            "patterns_loaded": len(self.patterns),
            "validators_loaded": len(self.validators),
            "config": self.config
        }
    
    def is_concrete_reference(self, value: str, reference_type: ReferenceType) -> bool:
        """
        Check if a value is a concrete reference that needs abstraction.
        
        Args:
            value: The value to check
            reference_type: The type of reference
            
        Returns:
            True if the value is concrete and needs abstraction
        """
        # This is a helper method that can be overridden by subclasses
        if reference_type == ReferenceType.FILE_PATH:
            return value.startswith('/') or value.startswith('\\') or ':' in value
        elif reference_type == ReferenceType.URL:
            return value.startswith('http://') or value.startswith('https://')
        elif reference_type == ReferenceType.IDENTIFIER:
            return value.isdigit() or self._is_uuid(value)
        else:
            return True  # Conservative: assume it's concrete
    
    def _is_uuid(self, value: str) -> bool:
        """Check if a value is a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value.lower()))
    
    def is_placeholder(self, value: str) -> bool:
        """
        Check if a value is already an abstraction placeholder.
        
        Args:
            value: The value to check
            
        Returns:
            True if the value is a placeholder
        """
        return value.startswith('<') and value.endswith('>')