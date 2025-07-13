"""
Memory validation service for safety enforcement.

Provides comprehensive validation of memory entries to ensure
all concrete references are properly abstracted.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple

from ..abstraction.rules import AbstractionRules
from ..validation.validator import SafetyValidator
from ..validation.memory_validator import MemoryValidationPipeline
from ..validation.quality_scorer import AbstractionQualityScorer
from .abstract_models import (
    AbstractMemoryEntry,
    SafeInteraction,
    ValidationResult,
    ValidationStatus,
    ReferenceType,
)


class MemoryValidator:
    """
    Comprehensive memory validation service.
    
    Validates memory entries for safety, quality, and proper abstraction.
    """
    
    def __init__(self):
        """Initialize validator with required components."""
        self.safety_validator = SafetyValidator()
        self.quality_scorer = AbstractionQualityScorer()
        self.pipeline = MemoryValidationPipeline()
        self.rules = AbstractionRules()
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for validation."""
        self.patterns = {
            'file_path': re.compile(r'(/(?:home|Users|usr|var|etc)/[a-zA-Z0-9._/-]+|[A-Z]:\\[a-zA-Z0-9._\\-]+)'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'url': re.compile(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[/a-zA-Z0-9._~:/?#@!$&\'()*+,;=-]*'),
            'credential': re.compile(r'(password|secret|token|key|api_key)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
            'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            'placeholder': re.compile(r'<[a-zA-Z][a-zA-Z0-9_]*>'),
            'connection_string': re.compile(r'(postgresql|mysql|mongodb)://[a-zA-Z0-9:@.-]+'),
        }
    
    def validate_memory_entry(self, memory: AbstractMemoryEntry) -> ValidationResult:
        """
        Validate a complete memory entry.
        
        Args:
            memory: The memory entry to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        start_time = datetime.utcnow()
        violations = []
        suggestions = []
        
        # Step 1: Check for concrete references
        concrete_refs = self._detect_concrete_references(memory.full_content)
        if concrete_refs:
            for ref_type, matches in concrete_refs.items():
                violations.append({
                    'type': 'concrete_reference',
                    'severity': 'critical',
                    'reference_type': ref_type,
                    'count': len(matches),
                    'examples': matches[:3]  # First 3 examples
                })
            suggestions.append("Replace all concrete references with placeholders")
        
        # Step 2: Check placeholder density
        density = memory.get_placeholder_density()
        if density < 0.1 and len(memory.full_content) > 100:
            violations.append({
                'type': 'low_placeholder_density',
                'severity': 'medium',
                'density': density,
                'required': 0.1
            })
            suggestions.append("Add more placeholders to improve abstraction")
        
        # Step 3: Validate abstraction mappings
        mapping_issues = self._validate_mappings(memory)
        violations.extend(mapping_issues)
        
        # Step 4: Check safety score requirements
        if memory.validation_status == ValidationStatus.VALIDATED and memory.safety_score < Decimal("0.8"):
            violations.append({
                'type': 'invalid_safety_score',
                'severity': 'critical',
                'score': float(memory.safety_score),
                'required': 0.8
            })
        
        # Step 5: Calculate quality score
        quality_result = self.quality_scorer.score_abstraction(
            original="",  # We don't store original
            abstracted=memory.full_content,
            concrete_refs={ref.placeholder: ref.original_value for ref in memory.concrete_references}
        )
        
        # Determine overall validity
        is_valid = len([v for v in violations if v['severity'] == 'critical']) == 0
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(
            violations=violations,
            quality_score=quality_result['quality_score'],
            placeholder_density=density
        )
        
        # Update memory validation status
        if is_valid and safety_score >= Decimal("0.8"):
            memory.validation_status = ValidationStatus.VALIDATED
        elif safety_score < Decimal("0.5"):
            memory.validation_status = ValidationStatus.QUARANTINED
        else:
            memory.validation_status = ValidationStatus.PENDING
        
        memory.safety_score = safety_score
        
        # Calculate processing time
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        result = ValidationResult(
            is_valid=is_valid,
            safety_score=safety_score,
            violations=violations,
            suggestions=suggestions,
            processing_time_ms=processing_time_ms
        )
        
        memory.validation_result = result
        memory.updated_at = datetime.utcnow()
        
        return result
    
    def validate_interaction(self, interaction: SafeInteraction, memory: AbstractMemoryEntry) -> List[str]:
        """
        Validate a safe interaction.
        
        Args:
            interaction: The interaction to validate
            memory: The associated memory entry
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Ensure memory is validated
        if memory.validation_status != ValidationStatus.VALIDATED:
            errors.append(f"Associated memory is not validated: {memory.validation_status.value}")
        
        # Check safety score
        if memory.safety_score < Decimal("0.8"):
            errors.append(f"Associated memory safety score too low: {memory.safety_score}")
        
        # Validate metadata
        try:
            # This will raise if metadata contains concrete references
            interaction.metadata.__post_init__()
        except ValueError as e:
            errors.append(f"Metadata validation failed: {str(e)}")
        
        # Update interaction validation status
        interaction.is_validated = len(errors) == 0
        interaction.validation_errors = errors
        interaction.updated_at = datetime.utcnow()
        
        return errors
    
    def _detect_concrete_references(self, content: str) -> Dict[str, List[str]]:
        """Detect concrete references in content."""
        found_refs = {}
        
        for ref_type, pattern in self.patterns.items():
            if ref_type == 'placeholder':
                continue  # Skip placeholder pattern
            
            matches = pattern.findall(content)
            if matches:
                # Filter out matches that are within placeholders
                filtered_matches = []
                for match in matches:
                    # Check if this match is part of a placeholder
                    if not re.search(f'<[^>]*{re.escape(match)}[^<]*>', content):
                        filtered_matches.append(match)
                
                if filtered_matches:
                    found_refs[ref_type] = filtered_matches
        
        return found_refs
    
    def _validate_mappings(self, memory: AbstractMemoryEntry) -> List[Dict[str, Any]]:
        """Validate abstraction mappings."""
        issues = []
        
        # Check that all placeholders in content have mappings
        placeholders_in_content = set(self.patterns['placeholder'].findall(memory.full_content))
        placeholders_in_mapping = set(memory.abstraction_mapping.mappings.keys())
        
        # Missing mappings
        missing = placeholders_in_content - placeholders_in_mapping
        if missing:
            issues.append({
                'type': 'missing_mapping',
                'severity': 'high',
                'placeholders': list(missing)
            })
        
        # Unused mappings
        unused = placeholders_in_mapping - placeholders_in_content
        if unused:
            issues.append({
                'type': 'unused_mapping',
                'severity': 'low',
                'placeholders': list(unused)
            })
        
        # Check mapping values don't appear in content
        for placeholder, value in memory.abstraction_mapping.mappings.items():
            if value in memory.full_content:
                issues.append({
                    'type': 'concrete_value_in_content',
                    'severity': 'critical',
                    'placeholder': placeholder,
                    'value': value[:50] + '...' if len(value) > 50 else value
                })
        
        return issues
    
    def _calculate_safety_score(
        self,
        violations: List[Dict[str, Any]],
        quality_score: float,
        placeholder_density: float
    ) -> Decimal:
        """Calculate overall safety score."""
        # Start with quality score
        score = quality_score
        
        # Apply violation penalties
        for violation in violations:
            if violation['severity'] == 'critical':
                score *= 0.3  # Heavy penalty
            elif violation['severity'] == 'high':
                score *= 0.7
            elif violation['severity'] == 'medium':
                score *= 0.9
            else:  # low
                score *= 0.95
        
        # Bonus for good placeholder density
        if placeholder_density > 0.2:
            score *= 1.1
        
        # Cap at 1.0
        score = min(1.0, score)
        
        # Round to 2 decimal places
        return Decimal(str(round(score, 2)))
    
    def suggest_abstractions(self, content: str) -> Dict[str, str]:
        """
        Suggest abstractions for concrete references in content.
        
        Args:
            content: The content to analyze
            
        Returns:
            Dictionary mapping concrete values to suggested placeholders
        """
        suggestions = {}
        concrete_refs = self._detect_concrete_references(content)
        
        for ref_type, matches in concrete_refs.items():
            for match in matches:
                # Generate placeholder name based on type and content
                if ref_type == 'file_path':
                    if 'home' in match.lower():
                        placeholder = '<user_home_path>'
                    elif 'config' in match.lower():
                        placeholder = '<config_file_path>'
                    else:
                        placeholder = '<file_path>'
                elif ref_type == 'ip_address':
                    placeholder = '<ip_address>'
                elif ref_type == 'url':
                    if 'api' in match.lower():
                        placeholder = '<api_endpoint>'
                    else:
                        placeholder = '<url>'
                elif ref_type == 'credential':
                    if 'password' in match.lower():
                        placeholder = '<password>'
                    elif 'token' in match.lower():
                        placeholder = '<token>'
                    else:
                        placeholder = '<credential>'
                elif ref_type == 'email':
                    placeholder = '<email_address>'
                elif ref_type == 'connection_string':
                    placeholder = '<database_connection>'
                else:
                    placeholder = f'<{ref_type}>'
                
                # Make unique if needed
                base_placeholder = placeholder
                counter = 1
                while placeholder in suggestions.values():
                    placeholder = f'{base_placeholder[:-1]}_{counter}>'
                    counter += 1
                
                suggestions[match] = placeholder
        
        return suggestions
    
    def auto_abstract_content(self, content: str) -> Tuple[str, Dict[str, str]]:
        """
        Automatically abstract content by replacing concrete references.
        
        Args:
            content: The content to abstract
            
        Returns:
            Tuple of (abstracted_content, mapping_dict)
        """
        suggestions = self.suggest_abstractions(content)
        abstracted = content
        
        # Sort by length (longest first) to avoid partial replacements
        for concrete, placeholder in sorted(suggestions.items(), key=lambda x: len(x[0]), reverse=True):
            abstracted = abstracted.replace(concrete, placeholder)
        
        return abstracted, suggestions