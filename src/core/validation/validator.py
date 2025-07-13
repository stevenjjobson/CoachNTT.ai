"""
SafetyValidator: Validates abstractions meet safety requirements.
Ensures all concrete references are properly abstracted and safe for storage.
"""
import re
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from src.core.safety.models import (
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    Abstraction,
    Reference,
    ReferenceType
)
from src.core.abstraction.extractor import ReferenceExtractor


logger = logging.getLogger(__name__)


class SafetyValidator:
    """
    Validates that content meets safety requirements.
    This is the final safety check before storage.
    """
    
    # Minimum safety score required
    MINIMUM_SAFETY_SCORE = 0.8
    
    # Error codes
    ERROR_CODES = {
        'E001': 'Concrete file path detected without abstraction',
        'E002': 'Safety score below threshold',
        'E003': 'Unabstracted identifier found',
        'E004': 'Concrete URL detected',
        'E005': 'Token or secret exposed',
        'E006': 'Inconsistent abstraction',
        'E007': 'Missing required abstraction',
        'E008': 'Invalid placeholder format',
        'E009': 'Overlapping abstractions',
        'E010': 'Abstraction coverage incomplete',
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the safety validator.
        
        Args:
            config: Configuration for validation
        """
        self.config = config or {}
        self.minimum_score = self.config.get('minimum_safety_score', self.MINIMUM_SAFETY_SCORE)
        self.extractor = ReferenceExtractor()
        self.placeholder_pattern = re.compile(r'<[^<>]+>')
        logger.info(f"Initialized SafetyValidator with minimum score: {self.minimum_score}")
    
    def validate(
        self,
        original_content: str,
        abstracted_content: str,
        abstractions: List[Abstraction],
        mappings: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate that abstractions meet safety requirements.
        
        Args:
            original_content: Original content with concrete references
            abstracted_content: Content after abstraction
            abstractions: List of abstractions applied
            mappings: Mapping of original to abstracted values
            context: Additional validation context
            
        Returns:
            ValidationResult with safety score and any errors/warnings
        """
        context = context or {}
        errors = []
        warnings = []
        
        # Stage 1: Validate abstraction completeness
        completeness_errors = self._validate_completeness(
            original_content, abstracted_content, abstractions
        )
        errors.extend(completeness_errors)
        
        # Stage 2: Check for remaining concrete references
        concrete_errors = self._check_remaining_concrete_refs(abstracted_content)
        errors.extend(concrete_errors)
        
        # Stage 3: Validate abstraction consistency
        consistency_errors = self._validate_consistency(abstractions)
        errors.extend(consistency_errors)
        
        # Stage 4: Validate placeholder format
        format_errors = self._validate_placeholder_format(abstracted_content)
        errors.extend(format_errors)
        
        # Stage 5: Check for security issues
        security_warnings = self._check_security_issues(
            original_content, abstracted_content, abstractions
        )
        warnings.extend(security_warnings)
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(
            original_content,
            abstracted_content,
            abstractions,
            errors,
            warnings
        )
        
        # Check if minimum score is met
        if safety_score < self.minimum_score:
            errors.append(ValidationError(
                code='E002',
                message=f'Safety score {safety_score:.2f} below threshold {self.minimum_score}',
                severity=ValidationSeverity.CRITICAL,
                context={'safety_score': safety_score, 'threshold': self.minimum_score}
            ))
        
        # Determine overall validity
        valid = len(errors) == 0 and safety_score >= self.minimum_score
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            safety_score=safety_score,
            metadata={
                'abstraction_count': len(abstractions),
                'coverage': self._calculate_coverage(original_content, abstractions),
                'validation_timestamp': datetime.now().isoformat(),
                'validator_version': '1.0.0'
            }
        )
    
    def _validate_completeness(
        self,
        original_content: str,
        abstracted_content: str,
        abstractions: List[Abstraction]
    ) -> List[ValidationError]:
        """Validate that all concrete references were abstracted."""
        errors = []
        
        # Extract references from original content
        original_refs = self.extractor.extract_references(original_content)
        
        # Check if all references have corresponding abstractions
        abstracted_values = {a.original for a in abstractions}
        
        for ref in original_refs:
            if ref.value not in abstracted_values:
                # Check if it's partially covered
                partially_covered = any(
                    ref.value in a.original for a in abstractions
                )
                
                if not partially_covered:
                    errors.append(ValidationError(
                        code='E007',
                        message=f'Missing abstraction for {ref.type.value}: {ref.value[:50]}...',
                        severity=ValidationSeverity.ERROR,
                        context={
                            'reference_type': ref.type.value,
                            'value': ref.value,
                            'position': ref.position
                        },
                        suggestion=f'Add abstraction for this {ref.type.value} reference'
                    ))
        
        # Calculate coverage
        if original_refs:
            coverage = len(abstractions) / len(original_refs)
            if coverage < 1.0:
                errors.append(ValidationError(
                    code='E010',
                    message=f'Abstraction coverage {coverage:.1%} is incomplete',
                    severity=ValidationSeverity.ERROR,
                    context={
                        'coverage': coverage,
                        'total_references': len(original_refs),
                        'abstracted': len(abstractions)
                    }
                ))
        
        return errors
    
    def _check_remaining_concrete_refs(self, abstracted_content: str) -> List[ValidationError]:
        """Check for any remaining concrete references in abstracted content."""
        errors = []
        
        # Re-scan abstracted content for concrete references
        remaining_refs = self.extractor.extract_references(abstracted_content)
        
        # Filter out placeholders
        concrete_refs = [
            ref for ref in remaining_refs
            if not self._is_placeholder(ref.value)
        ]
        
        # Create errors for each remaining concrete reference
        for ref in concrete_refs:
            error_code_map = {
                ReferenceType.FILE_PATH: 'E001',
                ReferenceType.IDENTIFIER: 'E003',
                ReferenceType.URL: 'E004',
                ReferenceType.TOKEN: 'E005',
            }
            
            error_code = error_code_map.get(ref.type, 'E007')
            
            errors.append(ValidationError(
                code=error_code,
                message=f'{ref.type.value} not abstracted: {ref.value[:50]}...',
                severity=ValidationSeverity.CRITICAL,
                context={
                    'type': ref.type.value,
                    'value': ref.value,
                    'position': ref.position
                },
                suggestion=f'Abstract this {ref.type.value} reference'
            ))
        
        return errors
    
    def _validate_consistency(self, abstractions: List[Abstraction]) -> List[ValidationError]:
        """Validate that similar references are abstracted consistently."""
        errors = []
        
        # Group abstractions by original value
        abstraction_groups: Dict[str, List[Abstraction]] = {}
        for abstr in abstractions:
            key = abstr.original
            if key not in abstraction_groups:
                abstraction_groups[key] = []
            abstraction_groups[key].append(abstr)
        
        # Check consistency within groups
        for original, group in abstraction_groups.items():
            if len(group) > 1:
                # All abstractions for the same original should be identical
                unique_abstractions = set(a.abstracted for a in group)
                if len(unique_abstractions) > 1:
                    errors.append(ValidationError(
                        code='E006',
                        message=f'Inconsistent abstraction for: {original[:50]}...',
                        severity=ValidationSeverity.ERROR,
                        context={
                            'original': original,
                            'abstractions': list(unique_abstractions)
                        },
                        suggestion='Use the same abstraction for identical references'
                    ))
        
        # Check for similar references with different abstractions
        self._check_similar_reference_consistency(abstractions, errors)
        
        return errors
    
    def _check_similar_reference_consistency(
        self,
        abstractions: List[Abstraction],
        errors: List[ValidationError]
    ) -> None:
        """Check that similar references use consistent abstraction patterns."""
        # Group by reference type
        by_type: Dict[ReferenceType, List[Abstraction]] = {}
        for abstr in abstractions:
            if abstr.reference_type not in by_type:
                by_type[abstr.reference_type] = []
            by_type[abstr.reference_type].append(abstr)
        
        # Check consistency within each type
        for ref_type, type_abstractions in by_type.items():
            if ref_type == ReferenceType.IDENTIFIER:
                # Check that similar IDs use similar patterns
                id_patterns: Dict[str, Set[str]] = {}
                for abstr in type_abstractions:
                    # Extract the pattern (e.g., user_id -> <user_id>)
                    if '_id' in abstr.original.lower():
                        base = abstr.original.lower().split('_id')[0]
                        if base not in id_patterns:
                            id_patterns[base] = set()
                        id_patterns[base].add(abstr.abstracted)
                
                # Check for inconsistencies
                for base, patterns in id_patterns.items():
                    if len(patterns) > 1:
                        errors.append(ValidationError(
                            code='E006',
                            message=f'Inconsistent ID abstraction pattern for {base}_id',
                            severity=ValidationSeverity.WARNING,
                            context={
                                'base': base,
                                'patterns': list(patterns)
                            },
                            suggestion=f'Use consistent pattern like <{base}_id>'
                        ))
    
    def _validate_placeholder_format(self, abstracted_content: str) -> List[ValidationError]:
        """Validate that all placeholders are properly formatted."""
        errors = []
        
        # Find all placeholders
        placeholders = self.placeholder_pattern.findall(abstracted_content)
        
        for placeholder in placeholders:
            # Check for nested placeholders
            if placeholder.count('<') > 1 or placeholder.count('>') > 1:
                errors.append(ValidationError(
                    code='E008',
                    message=f'Invalid nested placeholder: {placeholder}',
                    severity=ValidationSeverity.ERROR,
                    context={'placeholder': placeholder},
                    suggestion='Use single-level placeholders only'
                ))
            
            # Check for empty placeholders
            inner = placeholder[1:-1].strip()
            if not inner:
                errors.append(ValidationError(
                    code='E008',
                    message='Empty placeholder detected',
                    severity=ValidationSeverity.ERROR,
                    context={'placeholder': placeholder},
                    suggestion='Provide meaningful placeholder names'
                ))
            
            # Check for spaces in placeholders
            if ' ' in inner:
                errors.append(ValidationError(
                    code='E008',
                    message=f'Placeholder contains spaces: {placeholder}',
                    severity=ValidationSeverity.WARNING,
                    context={'placeholder': placeholder},
                    suggestion='Use underscores instead of spaces'
                ))
        
        return errors
    
    def _check_security_issues(
        self,
        original_content: str,
        abstracted_content: str,
        abstractions: List[Abstraction]
    ) -> List[ValidationError]:
        """Check for potential security issues."""
        warnings = []
        
        # Check for high-risk content that might have been missed
        high_risk_patterns = [
            (r'(?i)password\s*=\s*["\']?[^"\'\s]+', 'password'),
            (r'(?i)api[_\-]?key\s*=\s*["\']?[^"\'\s]+', 'api_key'),
            (r'(?i)secret\s*=\s*["\']?[^"\'\s]+', 'secret'),
            (r'(?i)token\s*=\s*["\']?[^"\'\s]+', 'token'),
            (r'(?i)private[_\-]?key', 'private_key'),
        ]
        
        for pattern, risk_type in high_risk_patterns:
            if re.search(pattern, abstracted_content):
                # Check if it's properly abstracted
                match = re.search(pattern, abstracted_content)
                if match and not self._is_placeholder(match.group(0)):
                    warnings.append(ValidationError(
                        code='E005',
                        message=f'Potential {risk_type} exposure detected',
                        severity=ValidationSeverity.CRITICAL,
                        context={
                            'type': risk_type,
                            'pattern': pattern
                        },
                        suggestion=f'Ensure all {risk_type} values are abstracted'
                    ))
        
        # Check abstraction metadata for sensitive info
        for abstr in abstractions:
            if abstr.reference_type == ReferenceType.TOKEN:
                # Ensure token abstractions don't leak info
                if len(abstr.original) > 4 and abstr.original[:4] in abstr.abstracted:
                    warnings.append(ValidationError(
                        code='E005',
                        message='Token abstraction may leak information',
                        severity=ValidationSeverity.WARNING,
                        context={
                            'abstraction': abstr.abstracted,
                            'type': 'token_prefix'
                        },
                        suggestion='Use generic placeholders for sensitive data'
                    ))
        
        return warnings
    
    def _calculate_safety_score(
        self,
        original_content: str,
        abstracted_content: str,
        abstractions: List[Abstraction],
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> float:
        """
        Calculate overall safety score based on validation results.
        
        Returns:
            Safety score between 0.0 and 1.0
        """
        # Component weights
        weights = {
            'coverage': 0.30,
            'error_penalty': 0.25,
            'consistency': 0.20,
            'quality': 0.15,
            'warning_penalty': 0.10,
        }
        
        scores = {}
        
        # Coverage score
        coverage = self._calculate_coverage(original_content, abstractions)
        scores['coverage'] = coverage
        
        # Error penalty
        error_penalty = 0.0
        for error in errors:
            if error.severity == ValidationSeverity.CRITICAL:
                error_penalty += 0.2
            elif error.severity == ValidationSeverity.ERROR:
                error_penalty += 0.1
        scores['error_penalty'] = max(0, 1.0 - error_penalty)
        
        # Consistency score
        unique_originals = len(set(a.original for a in abstractions))
        unique_mappings = len(set((a.original, a.abstracted) for a in abstractions))
        consistency = unique_originals / unique_mappings if unique_mappings > 0 else 1.0
        scores['consistency'] = consistency
        
        # Quality score (based on abstraction types)
        quality = self._calculate_abstraction_quality(abstractions)
        scores['quality'] = quality
        
        # Warning penalty
        warning_penalty = len(warnings) * 0.05
        scores['warning_penalty'] = max(0, 1.0 - warning_penalty)
        
        # Calculate weighted score
        total_score = sum(weights[k] * scores[k] for k in weights)
        
        # Apply critical error override
        if any(e.severity == ValidationSeverity.CRITICAL for e in errors):
            total_score *= 0.5
        
        return min(max(total_score, 0.0), 1.0)
    
    def _calculate_coverage(
        self, original_content: str, abstractions: List[Abstraction]
    ) -> float:
        """Calculate abstraction coverage."""
        if not original_content:
            return 1.0
        
        # Calculate total length of abstracted content
        total_abstracted = sum(len(a.original) for a in abstractions)
        
        # Also consider number of references
        original_refs = self.extractor.extract_references(original_content)
        if not original_refs:
            return 1.0
        
        ref_coverage = len(abstractions) / len(original_refs)
        
        return min(ref_coverage, 1.0)
    
    def _calculate_abstraction_quality(self, abstractions: List[Abstraction]) -> float:
        """Calculate quality score based on abstraction patterns."""
        if not abstractions:
            return 1.0
        
        quality_scores = []
        
        for abstr in abstractions:
            score = 1.0
            
            # Penalize overly generic abstractions
            if abstr.abstracted in ['<reference>', '<value>', '<data>']:
                score *= 0.7
            
            # Reward specific, semantic abstractions
            if any(specific in abstr.abstracted for specific in [
                '_id>', '_url>', '_path>', '_key>', '_token>'
            ]):
                score *= 1.1
            
            # Check placeholder specificity
            placeholder_content = abstr.abstracted.strip('<>')
            if '_' in placeholder_content:  # Compound, specific placeholder
                score *= 1.05
            
            quality_scores.append(min(score, 1.0))
        
        return sum(quality_scores) / len(quality_scores)
    
    def _is_placeholder(self, value: str) -> bool:
        """Check if a value is a placeholder."""
        return bool(self.placeholder_pattern.match(value.strip()))
    
    def validate_storage_ready(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate that data is ready for storage.
        
        Args:
            data: Data dictionary to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        
        # Required fields for storage
        required_fields = {
            'abstracted_prompt': str,
            'abstracted_code': str,
            'abstraction_mappings': dict,
            'safety_score': float,
            'validation_timestamp': str,
        }
        
        # Check required fields
        for field, expected_type in required_fields.items():
            if field not in data:
                errors.append(ValidationError(
                    code='E007',
                    message=f'Missing required field: {field}',
                    severity=ValidationSeverity.CRITICAL,
                    context={'field': field}
                ))
            elif not isinstance(data[field], expected_type):
                errors.append(ValidationError(
                    code='E008',
                    message=f'Invalid type for {field}: expected {expected_type.__name__}',
                    severity=ValidationSeverity.ERROR,
                    context={
                        'field': field,
                        'expected': expected_type.__name__,
                        'actual': type(data[field]).__name__
                    }
                ))
        
        # Validate safety score
        if 'safety_score' in data and data['safety_score'] < self.minimum_score:
            errors.append(ValidationError(
                code='E002',
                message=f"Safety score {data['safety_score']} below minimum {self.minimum_score}",
                severity=ValidationSeverity.CRITICAL,
                context={
                    'safety_score': data['safety_score'],
                    'minimum': self.minimum_score
                }
            ))
        
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            safety_score=data.get('safety_score', 0.0),
            metadata={'storage_validation': True}
        )