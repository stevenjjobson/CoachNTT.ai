"""
ConcreteAbstractionEngine: Full implementation of the abstraction engine.
Combines ReferenceExtractor, PatternGenerator, and SafetyValidator.
"""
import logging
from typing import Dict, List, Optional, Any

from src.core.abstraction.engine import AbstractionEngine
from src.core.abstraction.extractor import ReferenceExtractor
from src.core.abstraction.generator import PatternGenerator
from src.core.validation.validator import SafetyValidator
from src.core.safety.models import (
    Reference,
    Abstraction,
    ValidationResult,
    ValidationError,
    ValidationSeverity
)


logger = logging.getLogger(__name__)


class ConcreteAbstractionEngine(AbstractionEngine):
    """
    Concrete implementation of the abstraction engine.
    This is the main entry point for all abstraction operations in CCP.
    """
    
    def _initialize(self) -> None:
        """Initialize engine components."""
        self.extractor = ReferenceExtractor()
        self.generator = PatternGenerator(self.config)
        self.validator = SafetyValidator(self.config)
        logger.info("Initialized ConcreteAbstractionEngine")
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load abstraction patterns."""
        # Patterns will be loaded after initialization
        return {}
    
    def _load_validators(self) -> Dict[str, Any]:
        """Load validators."""
        # Validators will be loaded after initialization
        return {}
    
    def _detect_references(
        self, content: str, context: Dict[str, Any]
    ) -> List[Reference]:
        """
        Detect all concrete references in the content.
        
        Args:
            content: Content to scan for references
            context: Additional context
            
        Returns:
            List of detected references
        """
        try:
            references = self.extractor.extract_references(content, context)
            logger.debug(f"Detected {len(references)} references")
            
            # Log reference types for debugging
            type_counts = {}
            for ref in references:
                type_counts[ref.type.value] = type_counts.get(ref.type.value, 0) + 1
            logger.debug(f"Reference types: {type_counts}")
            
            return references
            
        except Exception as e:
            logger.error(f"Reference detection failed: {e}")
            return []
    
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
        abstractions = []
        
        for reference in references:
            try:
                abstraction = self.generator.generate_abstraction(reference, context)
                abstractions.append(abstraction)
                logger.debug(
                    f"Abstracted {reference.value[:50]}... to {abstraction.abstracted}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to generate abstraction for {reference.value}: {e}"
                )
                # Continue with other references
        
        return abstractions
    
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
        try:
            result = self.validator.validate(
                original_content=original,
                abstracted_content=abstracted,
                abstractions=abstractions,
                mappings=mappings
            )
            
            logger.info(
                f"Validation complete - Score: {result.safety_score:.2f}, "
                f"Valid: {result.valid}, Errors: {len(result.errors)}, "
                f"Warnings: {len(result.warnings)}"
            )
            
            # Log any critical errors
            for error in result.errors:
                if error.severity == ValidationSeverity.CRITICAL:
                    logger.error(f"Critical validation error: {error.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            # Return failed validation
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        code="E_VALIDATION_FAILED",
                        message=f"Validation process failed: {str(e)}",
                        severity=ValidationSeverity.CRITICAL,
                        context={"error": str(e)}
                    )
                ],
                safety_score=0.0
            )
    
    def add_custom_pattern(
        self,
        name: str,
        pattern: str,
        reference_type: str,
        confidence: float = 0.8
    ) -> None:
        """
        Add a custom extraction pattern.
        
        Args:
            name: Name for the pattern
            pattern: Regular expression pattern
            reference_type: Type of reference (as string)
            confidence: Confidence level for matches
        """
        from src.core.safety.models import ReferenceType
        
        # Convert string to ReferenceType
        try:
            ref_type = ReferenceType(reference_type)
        except ValueError:
            ref_type = ReferenceType.UNKNOWN
            logger.warning(
                f"Unknown reference type '{reference_type}', using UNKNOWN"
            )
        
        self.extractor.add_custom_pattern(name, pattern, ref_type, confidence)
        logger.info(f"Added custom pattern '{name}' for {ref_type.value}")
    
    def validate_memory_entry(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a memory entry is ready for storage.
        
        Args:
            memory_data: Memory data to validate
            
        Returns:
            ValidationResult
        """
        # First check if it has required abstraction fields
        if 'abstracted_prompt' not in memory_data or 'abstracted_code' not in memory_data:
            # Need to perform abstraction first
            prompt = memory_data.get('prompt', '')
            code = memory_data.get('code', '')
            
            # Combine for abstraction
            combined = f"{prompt}\n\n{code}"
            
            # Perform abstraction
            result = self.abstract(combined, {'type': 'memory_entry'})
            
            if not result.is_safe:
                return result.validation
            
            # Split back
            parts = result.abstracted_content.split('\n\n', 1)
            memory_data['abstracted_prompt'] = parts[0] if parts else ''
            memory_data['abstracted_code'] = parts[1] if len(parts) > 1 else ''
            memory_data['abstraction_mappings'] = result.mappings
            memory_data['safety_score'] = result.validation.safety_score
            memory_data['validation_timestamp'] = result.validation.metadata.get(
                'validation_timestamp'
            )
        
        # Validate storage readiness
        return self.validator.validate_storage_ready(memory_data)
    
    def get_abstraction_stats(self) -> Dict[str, Any]:
        """Get statistics about the abstraction engine."""
        stats = {
            'engine_type': 'ConcreteAbstractionEngine',
            'extractor_patterns': self.extractor.get_pattern_stats(),
            'minimum_safety_score': self.validator.minimum_score,
            'placeholder_format': self.generator.placeholder_format,
            'config': self.config
        }
        return stats