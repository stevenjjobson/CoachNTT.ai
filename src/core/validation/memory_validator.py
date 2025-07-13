"""
Memory validation pipeline for the Cognitive Coding Partner.
Ensures all memories are properly abstracted before storage.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from src.core.validation.validator import SafetyValidator
from src.core.safety.models import (
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    AbstractionResult
)


logger = logging.getLogger(__name__)


@dataclass
class MemoryValidationStage:
    """A stage in the memory validation pipeline."""
    name: str
    description: str
    validator: callable
    required: bool = True
    continue_on_failure: bool = False


class MemoryValidationPipeline:
    """
    Multi-stage validation pipeline for memory entries.
    Ensures memories meet all safety requirements before storage.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, abstraction_engine=None):
        """
        Initialize the memory validation pipeline.
        
        Args:
            config: Configuration for the pipeline
            abstraction_engine: Pre-configured abstraction engine (to avoid circular imports)
        """
        self.config = config or {}
        self.abstraction_engine = abstraction_engine
        self.safety_validator = SafetyValidator(config)
        self.stages = self._initialize_stages()
        self._validation_history = []
        logger.info(f"Initialized MemoryValidationPipeline with {len(self.stages)} stages")
    
    def _initialize_stages(self) -> List[MemoryValidationStage]:
        """Initialize validation stages."""
        return [
            MemoryValidationStage(
                name="structure_validation",
                description="Validate memory structure and required fields",
                validator=self._validate_structure,
                required=True,
                continue_on_failure=False
            ),
            MemoryValidationStage(
                name="content_abstraction",
                description="Abstract all concrete references in content",
                validator=self._validate_and_abstract_content,
                required=True,
                continue_on_failure=False
            ),
            MemoryValidationStage(
                name="safety_validation",
                description="Validate abstraction safety and quality",
                validator=self._validate_safety,
                required=True,
                continue_on_failure=False
            ),
            MemoryValidationStage(
                name="temporal_validation",
                description="Validate temporal aspects and freshness",
                validator=self._validate_temporal,
                required=False,
                continue_on_failure=True
            ),
            MemoryValidationStage(
                name="consistency_validation",
                description="Validate consistency with existing memories",
                validator=self._validate_consistency,
                required=False,
                continue_on_failure=True
            ),
        ]
    
    def validate_memory(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a memory entry through all pipeline stages.
        
        Args:
            memory_data: Memory data to validate
            
        Returns:
            ValidationResult with combined results from all stages
        """
        start_time = datetime.now()
        all_errors = []
        all_warnings = []
        stage_results = {}
        
        # Create a working copy to avoid modifying original
        working_data = memory_data.copy()
        
        # Run through each validation stage
        for stage in self.stages:
            logger.info(f"Running validation stage: {stage.name}")
            
            try:
                result = stage.validator(working_data)
                stage_results[stage.name] = result
                
                # Collect errors and warnings
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                
                # Check if we should continue
                if not result.valid and stage.required and not stage.continue_on_failure:
                    logger.error(f"Stage '{stage.name}' failed, stopping pipeline")
                    break
                    
            except Exception as e:
                logger.error(f"Stage '{stage.name}' raised exception: {e}")
                error = ValidationError(
                    code="E_STAGE_EXCEPTION",
                    message=f"Validation stage '{stage.name}' failed: {str(e)}",
                    severity=ValidationSeverity.CRITICAL,
                    context={"stage": stage.name, "error": str(e)}
                )
                all_errors.append(error)
                
                if stage.required and not stage.continue_on_failure:
                    break
        
        # Calculate overall result
        has_critical = any(e.severity == ValidationSeverity.CRITICAL for e in all_errors)
        has_required_failure = any(
            stage.name in stage_results and not stage_results[stage.name].valid and stage.required
            for stage in self.stages
        )
        
        valid = not has_critical and not has_required_failure
        
        # Calculate combined safety score
        safety_scores = [
            result.safety_score for result in stage_results.values()
            if result.safety_score is not None
        ]
        combined_safety_score = sum(safety_scores) / len(safety_scores) if safety_scores else 0.0
        
        # Update memory data with abstracted content if successful
        if 'content_abstraction' in stage_results and stage_results['content_abstraction'].valid:
            abstraction_result = working_data.get('_abstraction_result')
            if abstraction_result:
                memory_data['abstracted_prompt'] = working_data.get('abstracted_prompt', '')
                memory_data['abstracted_code'] = working_data.get('abstracted_code', '')
                memory_data['abstraction_mappings'] = working_data.get('abstraction_mappings', {})
                memory_data['safety_score'] = combined_safety_score
        
        # Record validation in history
        validation_record = {
            'timestamp': start_time.isoformat(),
            'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
            'valid': valid,
            'safety_score': combined_safety_score,
            'stages_completed': len(stage_results),
            'error_count': len(all_errors),
            'warning_count': len(all_warnings)
        }
        self._validation_history.append(validation_record)
        
        return ValidationResult(
            valid=valid,
            errors=all_errors,
            warnings=all_warnings,
            safety_score=combined_safety_score,
            metadata={
                'pipeline_stages': len(self.stages),
                'stages_completed': len(stage_results),
                'stage_results': {k: v.valid for k, v in stage_results.items()},
                'validation_timestamp': start_time.isoformat(),
                'duration_ms': validation_record['duration_ms']
            }
        )
    
    def _validate_structure(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """Validate memory structure and required fields."""
        errors = []
        
        # Required fields for a memory entry
        required_fields = ['prompt', 'code', 'interaction_id']
        
        for field in required_fields:
            if field not in memory_data:
                errors.append(ValidationError(
                    code="E_MISSING_FIELD",
                    message=f"Missing required field: {field}",
                    severity=ValidationSeverity.ERROR,
                    context={"field": field}
                ))
            elif not memory_data[field]:
                errors.append(ValidationError(
                    code="E_EMPTY_FIELD",
                    message=f"Required field is empty: {field}",
                    severity=ValidationSeverity.ERROR,
                    context={"field": field}
                ))
        
        # Validate field types
        type_checks = {
            'prompt': str,
            'code': str,
            'interaction_id': str,
            'files_involved': list,
            'tags': list
        }
        
        for field, expected_type in type_checks.items():
            if field in memory_data and not isinstance(memory_data[field], expected_type):
                errors.append(ValidationError(
                    code="E_INVALID_TYPE",
                    message=f"Invalid type for field '{field}'",
                    severity=ValidationSeverity.ERROR,
                    context={
                        "field": field,
                        "expected": expected_type.__name__,
                        "actual": type(memory_data[field]).__name__
                    }
                ))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            metadata={"stage": "structure_validation"}
        )
    
    def _validate_and_abstract_content(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """Abstract concrete references in memory content."""
        errors = []
        warnings = []
        
        if not self.abstraction_engine:
            errors.append(ValidationError(
                code="E_NO_ABSTRACTION_ENGINE",
                message="No abstraction engine configured",
                severity=ValidationSeverity.CRITICAL,
                context={}
            ))
            return ValidationResult(
                valid=False,
                errors=errors,
                metadata={"stage": "content_abstraction"}
            )
        
        try:
            # Combine prompt and code for abstraction
            prompt = memory_data.get('prompt', '')
            code = memory_data.get('code', '')
            
            # Create combined content with clear separation
            combined_content = f"{prompt}\n\n---CODE---\n\n{code}"
            
            # Perform abstraction
            abstraction_result = self.abstraction_engine.abstract(
                combined_content,
                context={'type': 'memory_entry', 'interaction_id': memory_data.get('interaction_id')}
            )
            
            # Store the result for later stages
            memory_data['_abstraction_result'] = abstraction_result
            
            if abstraction_result.is_safe:
                # Split abstracted content back
                parts = abstraction_result.abstracted_content.split('\n\n---CODE---\n\n', 1)
                memory_data['abstracted_prompt'] = parts[0] if parts else ''
                memory_data['abstracted_code'] = parts[1] if len(parts) > 1 else ''
                memory_data['abstraction_mappings'] = abstraction_result.mappings
                
                # Add abstraction metadata
                memory_data['abstraction_metadata'] = {
                    'reference_count': len(abstraction_result.references),
                    'abstraction_count': len(abstraction_result.abstractions),
                    'coverage_score': abstraction_result.coverage_score,
                    'processing_time_ms': abstraction_result.processing_time_ms
                }
                
                logger.info(
                    f"Abstracted {len(abstraction_result.abstractions)} references "
                    f"with coverage score: {abstraction_result.coverage_score:.2f}"
                )
            else:
                errors.extend(abstraction_result.validation.errors)
                warnings.extend(abstraction_result.validation.warnings)
                
        except Exception as e:
            logger.error(f"Abstraction failed: {e}")
            errors.append(ValidationError(
                code="E_ABSTRACTION_FAILED",
                message=f"Failed to abstract content: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
                context={"error": str(e)}
            ))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            safety_score=abstraction_result.validation.safety_score if 'abstraction_result' in memory_data else 0.0,
            metadata={"stage": "content_abstraction"}
        )
    
    def _validate_safety(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """Validate safety of abstracted content."""
        abstraction_result = memory_data.get('_abstraction_result')
        
        if not abstraction_result:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    code="E_NO_ABSTRACTION",
                    message="No abstraction result found",
                    severity=ValidationSeverity.CRITICAL,
                    context={}
                )],
                metadata={"stage": "safety_validation"}
            )
        
        # Use the validation from abstraction result
        validation = abstraction_result.validation
        
        # Additional safety checks specific to memories
        errors = list(validation.errors)
        warnings = list(validation.warnings)
        
        # Check for high-risk patterns in abstracted content
        abstracted_content = memory_data.get('abstracted_prompt', '') + '\n' + memory_data.get('abstracted_code', '')
        
        # Ensure no concrete paths remain
        import re
        if re.search(r'[C-Z]:\\|/home/|/Users/', abstracted_content):
            errors.append(ValidationError(
                code="E_CONCRETE_PATH",
                message="Concrete file paths detected in abstracted content",
                severity=ValidationSeverity.CRITICAL,
                context={"pattern": "absolute_path"}
            ))
        
        # Ensure no real IPs remain
        if re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', abstracted_content):
            # Check if it's a placeholder
            if not re.search(r'<[^>]*ip[^>]*>', abstracted_content):
                errors.append(ValidationError(
                    code="E_CONCRETE_IP",
                    message="Concrete IP address detected in abstracted content",
                    severity=ValidationSeverity.CRITICAL,
                    context={"pattern": "ip_address"}
                ))
        
        return ValidationResult(
            valid=len(errors) == 0 and validation.safety_score >= 0.8,
            errors=errors,
            warnings=warnings,
            safety_score=validation.safety_score,
            metadata={"stage": "safety_validation"}
        )
    
    def _validate_temporal(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """Validate temporal aspects of the memory."""
        warnings = []
        
        # Check if memory has timestamp
        if 'created_at' not in memory_data:
            memory_data['created_at'] = datetime.now().isoformat()
        
        # Check for temporal references in content
        abstraction_result = memory_data.get('_abstraction_result')
        if abstraction_result:
            temporal_refs = [
                ref for ref in abstraction_result.references
                if ref.type.value == 'timestamp'
            ]
            
            if temporal_refs:
                warnings.append(ValidationError(
                    code="W_TEMPORAL_REFS",
                    message=f"Found {len(temporal_refs)} temporal references",
                    severity=ValidationSeverity.INFO,
                    context={"count": len(temporal_refs)},
                    suggestion="Ensure temporal references don't become stale"
                ))
        
        return ValidationResult(
            valid=True,
            warnings=warnings,
            metadata={"stage": "temporal_validation"}
        )
    
    def _validate_consistency(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """Validate consistency with existing memories."""
        # This is a placeholder for consistency checking
        # In a real implementation, this would check against existing memories
        # for duplicate content, conflicting information, etc.
        
        warnings = []
        
        # Check abstraction consistency
        if 'abstraction_mappings' in memory_data:
            mappings = memory_data['abstraction_mappings']
            
            # Check for inconsistent abstractions of the same value
            reverse_mappings = {}
            for original, abstracted in mappings.items():
                if abstracted not in reverse_mappings:
                    reverse_mappings[abstracted] = []
                reverse_mappings[abstracted].append(original)
            
            for abstracted, originals in reverse_mappings.items():
                if len(originals) > 1 and len(set(originals)) > 1:
                    warnings.append(ValidationError(
                        code="W_INCONSISTENT_ABSTRACTION",
                        message=f"Multiple different values mapped to same abstraction",
                        severity=ValidationSeverity.WARNING,
                        context={
                            "abstraction": abstracted,
                            "originals": originals[:3]  # Limit for brevity
                        }
                    ))
        
        return ValidationResult(
            valid=True,
            warnings=warnings,
            metadata={"stage": "consistency_validation"}
        )
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get statistics about validation history."""
        if not self._validation_history:
            return {"total_validations": 0}
        
        total = len(self._validation_history)
        successful = sum(1 for v in self._validation_history if v['valid'])
        
        safety_scores = [v['safety_score'] for v in self._validation_history if v['safety_score'] > 0]
        avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 0.0
        
        durations = [v['duration_ms'] for v in self._validation_history]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return {
            "total_validations": total,
            "successful_validations": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "average_safety_score": avg_safety,
            "average_duration_ms": avg_duration,
            "stages_per_validation": len(self.stages)
        }