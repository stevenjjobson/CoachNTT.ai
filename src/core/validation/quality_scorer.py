"""
Abstraction quality scorer for the Cognitive Coding Partner.
Provides detailed quality assessment of abstractions beyond basic safety checks.
"""
import re
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter

from src.core.safety.models import (
    AbstractionResult,
    Abstraction,
    Reference,
    ReferenceType
)


logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Detailed quality score for an abstraction."""
    overall_score: float  # 0.0 to 1.0
    component_scores: Dict[str, float]
    feedback: List[str]
    strengths: List[str]
    improvements: List[str]
    metadata: Dict[str, Any]


@dataclass
class AbstractionQualityMetrics:
    """Metrics for abstraction quality assessment."""
    specificity_score: float = 0.0
    consistency_score: float = 0.0
    completeness_score: float = 0.0
    semantic_score: float = 0.0
    efficiency_score: float = 0.0
    maintainability_score: float = 0.0


class AbstractionQualityScorer:
    """
    Scores abstraction quality across multiple dimensions.
    Provides detailed feedback on abstraction patterns and effectiveness.
    """
    
    # Quality weights for different components
    COMPONENT_WEIGHTS = {
        'specificity': 0.20,    # How specific/semantic the abstractions are
        'consistency': 0.25,    # Internal consistency of abstractions
        'completeness': 0.20,   # Coverage of all references
        'semantic': 0.15,       # Semantic preservation
        'efficiency': 0.10,     # Efficiency/conciseness
        'maintainability': 0.10 # How maintainable the abstractions are
    }
    
    # Threshold scores for quality levels
    QUALITY_THRESHOLDS = {
        'excellent': 0.9,
        'good': 0.8,
        'acceptable': 0.7,
        'poor': 0.5,
        'unacceptable': 0.0
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the quality scorer.
        
        Args:
            config: Configuration for scoring
        """
        self.config = config or {}
        self.weights = self.config.get('component_weights', self.COMPONENT_WEIGHTS)
        self.thresholds = self.config.get('quality_thresholds', self.QUALITY_THRESHOLDS)
        logger.info("Initialized AbstractionQualityScorer")
    
    def score_abstraction_result(self, result: AbstractionResult) -> QualityScore:
        """
        Score the quality of an abstraction result.
        
        Args:
            result: The abstraction result to score
            
        Returns:
            QualityScore with detailed assessment
        """
        # Calculate component scores
        component_scores = self._calculate_component_scores(result)
        
        # Calculate overall weighted score
        overall_score = sum(
            self.weights.get(component, 0.0) * score
            for component, score in component_scores.items()
        )
        
        # Generate feedback
        feedback, strengths, improvements = self._generate_feedback(result, component_scores)
        
        # Create metadata
        metadata = self._generate_metadata(result, component_scores)
        
        quality_score = QualityScore(
            overall_score=overall_score,
            component_scores=component_scores,
            feedback=feedback,
            strengths=strengths,
            improvements=improvements,
            metadata=metadata
        )
        
        logger.info(f"Scored abstraction quality: {overall_score:.3f}")
        return quality_score
    
    def _calculate_component_scores(self, result: AbstractionResult) -> Dict[str, float]:
        """Calculate scores for each quality component."""
        return {
            'specificity': self._score_specificity(result),
            'consistency': self._score_consistency(result),
            'completeness': self._score_completeness(result),
            'semantic': self._score_semantic_preservation(result),
            'efficiency': self._score_efficiency(result),
            'maintainability': self._score_maintainability(result)
        }
    
    def _score_specificity(self, result: AbstractionResult) -> float:
        """
        Score how specific and semantic the abstractions are.
        Higher scores for descriptive, context-aware abstractions.
        """
        if not result.abstractions:
            return 0.0
        
        specificity_scores = []
        
        for abstraction in result.abstractions:
            score = 0.5  # Base score
            abstracted = abstraction.abstracted.lower()
            
            # Reward specific, semantic abstractions
            if any(specific in abstracted for specific in [
                '_id', '_url', '_path', '_key', '_token', '_config',
                '_service', '_host', '_port', '_database', '_user'
            ]):
                score += 0.3
            
            # Reward compound abstractions (multiple concepts)
            if '_' in abstracted.strip('<>'):
                score += 0.2
            
            # Penalize overly generic abstractions
            generic_terms = ['reference', 'value', 'data', 'item', 'thing']
            if any(term in abstracted for term in generic_terms):
                score -= 0.3
            
            # Reward context-aware abstractions
            original_lower = abstraction.original.lower()
            if 'user' in original_lower and 'user' in abstracted:
                score += 0.1
            if 'database' in original_lower and 'db' in abstracted:
                score += 0.1
            if 'config' in original_lower and 'config' in abstracted:
                score += 0.1
            
            # Ensure score is in valid range
            specificity_scores.append(max(0.0, min(1.0, score)))
        
        return sum(specificity_scores) / len(specificity_scores)
    
    def _score_consistency(self, result: AbstractionResult) -> float:
        """
        Score internal consistency of abstractions.
        Higher scores for consistent patterns and mappings.
        """
        if not result.abstractions:
            return 1.0
        
        consistency_penalties = 0.0
        total_checks = 0
        
        # Check for consistent abstraction patterns
        type_patterns = {}
        for abstraction in result.abstractions:
            ref_type = abstraction.reference_type
            pattern = abstraction.abstracted
            
            if ref_type not in type_patterns:
                type_patterns[ref_type] = []
            type_patterns[ref_type].append(pattern)
        
        # Penalize inconsistent patterns within each type
        for ref_type, patterns in type_patterns.items():
            unique_patterns = set(patterns)
            if len(unique_patterns) > 1:
                # Similar references should use similar patterns
                similar_count = 0
                for i, pattern1 in enumerate(unique_patterns):
                    for pattern2 in list(unique_patterns)[i+1:]:
                        if self._are_patterns_similar(pattern1, pattern2):
                            similar_count += 1
                        total_checks += 1
                
                if total_checks > 0:
                    consistency_penalties += (total_checks - similar_count) / total_checks * 0.3
        
        # Check for one-to-one mapping consistency
        mapping_consistency = self._check_mapping_consistency(result.mappings)
        if mapping_consistency < 1.0:
            consistency_penalties += (1.0 - mapping_consistency) * 0.4
        
        # Check for placeholder format consistency
        format_consistency = self._check_format_consistency(result.abstractions)
        if format_consistency < 1.0:
            consistency_penalties += (1.0 - format_consistency) * 0.3
        
        return max(0.0, 1.0 - consistency_penalties)
    
    def _score_completeness(self, result: AbstractionResult) -> float:
        """
        Score completeness of abstraction coverage.
        Higher scores for complete abstraction of all references.
        """
        if not result.references:
            return 1.0  # No references to abstract
        
        # Basic coverage score
        coverage = len(result.abstractions) / len(result.references)
        
        # Penalize missing high-priority references
        critical_types = {ReferenceType.TOKEN, ReferenceType.FILE_PATH, ReferenceType.URL}
        critical_refs = [r for r in result.references if r.type in critical_types]
        critical_abstracted = [a for a in result.abstractions if a.reference_type in critical_types]
        
        if critical_refs:
            critical_coverage = len(critical_abstracted) / len(critical_refs)
            # Weight critical coverage heavily
            coverage = 0.3 * coverage + 0.7 * critical_coverage
        
        # Check for partial abstractions (incomplete coverage of multi-part references)
        partial_penalty = self._calculate_partial_abstraction_penalty(result)
        
        return max(0.0, min(1.0, coverage - partial_penalty))
    
    def _score_semantic_preservation(self, result: AbstractionResult) -> float:
        """
        Score how well abstractions preserve semantic meaning.
        Higher scores for abstractions that maintain context and purpose.
        """
        if not result.abstractions:
            return 1.0
        
        semantic_scores = []
        
        for abstraction in result.abstractions:
            score = 0.5  # Base score
            
            original = abstraction.original.lower()
            abstracted = abstraction.abstracted.lower()
            
            # Reward preservation of key semantic elements
            semantic_indicators = {
                'user': ['user', 'person', 'account'],
                'database': ['db', 'database', 'data'],
                'config': ['config', 'setting', 'option'],
                'auth': ['auth', 'login', 'credential'],
                'api': ['api', 'service', 'endpoint'],
                'file': ['file', 'path', 'document'],
                'network': ['network', 'ip', 'host'],
                'time': ['time', 'date', 'timestamp']
            }
            
            for concept, indicators in semantic_indicators.items():
                if concept in original:
                    if any(indicator in abstracted for indicator in indicators):
                        score += 0.2
                    else:
                        score -= 0.1  # Penalty for losing semantic meaning
            
            # Reward abstractions that maintain functional context
            if 'id' in original and 'id' in abstracted:
                score += 0.15
            if 'key' in original and 'key' in abstracted:
                score += 0.15
            if 'token' in original and 'token' in abstracted:
                score += 0.15
            
            # Penalize abstractions that lose too much meaning
            if len(abstracted.strip('<>')) < 3:  # Very short abstractions
                score -= 0.2
            
            semantic_scores.append(max(0.0, min(1.0, score)))
        
        return sum(semantic_scores) / len(semantic_scores)
    
    def _score_efficiency(self, result: AbstractionResult) -> float:
        """
        Score efficiency of the abstraction process.
        Higher scores for concise, well-optimized abstractions.
        """
        if not result.abstractions:
            return 1.0
        
        # Score based on abstraction ratio
        original_length = sum(len(a.original) for a in result.abstractions)
        abstracted_length = sum(len(a.abstracted) for a in result.abstractions)
        
        if original_length == 0:
            return 1.0
        
        # Ideal ratio is moderate compression (0.3 to 0.7)
        ratio = abstracted_length / original_length
        if 0.3 <= ratio <= 0.7:
            efficiency_score = 1.0
        elif ratio < 0.3:
            # Too much compression, might lose meaning
            efficiency_score = ratio / 0.3
        else:
            # Too little compression, not efficient
            efficiency_score = max(0.0, 1.0 - (ratio - 0.7) / 0.3)
        
        # Bonus for avoiding redundant abstractions
        unique_abstractions = len(set(a.abstracted for a in result.abstractions))
        redundancy_score = unique_abstractions / len(result.abstractions)
        
        # Processing time efficiency
        time_efficiency = 1.0
        if result.processing_time_ms > 1000:  # More than 1 second
            time_efficiency = max(0.0, 1.0 - (result.processing_time_ms - 1000) / 5000)
        
        return (efficiency_score * 0.5 + redundancy_score * 0.3 + time_efficiency * 0.2)
    
    def _score_maintainability(self, result: AbstractionResult) -> float:
        """
        Score maintainability of abstractions.
        Higher scores for abstractions that are easy to understand and update.
        """
        if not result.abstractions:
            return 1.0
        
        maintainability_scores = []
        
        for abstraction in result.abstractions:
            score = 0.5  # Base score
            abstracted = abstraction.abstracted
            
            # Reward clear, readable placeholder names
            placeholder_content = abstracted.strip('<>')
            
            # Good naming conventions
            if re.match(r'^[a-z][a-z0-9_]*[a-z0-9]$', placeholder_content):
                score += 0.2
            
            # Appropriate length (5-25 characters)
            if 5 <= len(placeholder_content) <= 25:
                score += 0.15
            else:
                score -= 0.1
            
            # Avoid abbreviations that are unclear
            unclear_abbrevs = ['tmp', 'cfg', 'usr', 'sys', 'obj', 'var']
            if any(abbrev in placeholder_content for abbrev in unclear_abbrevs):
                score -= 0.1
            
            # Reward hierarchical naming
            if '_' in placeholder_content:
                parts = placeholder_content.split('_')
                if len(parts) == 2 and all(len(part) > 2 for part in parts):
                    score += 0.15
            
            # Penalize overly complex or nested structures
            if placeholder_content.count('_') > 3:
                score -= 0.2
            
            maintainability_scores.append(max(0.0, min(1.0, score)))
        
        return sum(maintainability_scores) / len(maintainability_scores)
    
    def _are_patterns_similar(self, pattern1: str, pattern2: str) -> bool:
        """Check if two abstraction patterns are similar."""
        # Remove brackets for comparison
        clean1 = pattern1.strip('<>')
        clean2 = pattern2.strip('<>')
        
        # Check for similar structure
        if '_' in clean1 and '_' in clean2:
            parts1 = clean1.split('_')
            parts2 = clean2.split('_')
            
            # Similar if same number of parts and some parts match
            if len(parts1) == len(parts2):
                matches = sum(1 for p1, p2 in zip(parts1, parts2) if p1 == p2)
                return matches >= len(parts1) * 0.6
        
        # Check for exact match or substring relationship
        return clean1 == clean2 or clean1 in clean2 or clean2 in clean1
    
    def _check_mapping_consistency(self, mappings: Dict[str, str]) -> float:
        """Check for one-to-one mapping consistency."""
        if not mappings:
            return 1.0
        
        # Check for many-to-one mappings (multiple originals -> same abstraction)
        reverse_mappings = {}
        for original, abstracted in mappings.items():
            if abstracted not in reverse_mappings:
                reverse_mappings[abstracted] = []
            reverse_mappings[abstracted].append(original)
        
        consistent_mappings = 0
        for abstracted, originals in reverse_mappings.items():
            if len(set(originals)) == 1:  # All originals are the same
                consistent_mappings += len(originals)
        
        return consistent_mappings / len(mappings)
    
    def _check_format_consistency(self, abstractions: List[Abstraction]) -> float:
        """Check consistency of placeholder format."""
        if not abstractions:
            return 1.0
        
        formats = [self._get_placeholder_format(a.abstracted) for a in abstractions]
        unique_formats = set(formats)
        
        # All should use the same format
        return 1.0 if len(unique_formats) == 1 else 0.7
    
    def _get_placeholder_format(self, abstraction: str) -> str:
        """Extract the format pattern of a placeholder."""
        if abstraction.startswith('<') and abstraction.endswith('>'):
            return 'angle_brackets'
        elif abstraction.startswith('{') and abstraction.endswith('}'):
            return 'curly_brackets'
        elif abstraction.startswith('[') and abstraction.endswith(']'):
            return 'square_brackets'
        else:
            return 'unknown'
    
    def _calculate_partial_abstraction_penalty(self, result: AbstractionResult) -> float:
        """Calculate penalty for partial abstractions."""
        penalty = 0.0
        
        # Check for references that should be abstracted together
        file_path_refs = [r for r in result.references if r.type == ReferenceType.FILE_PATH]
        if len(file_path_refs) > 1:
            # Group by directory path
            path_groups = {}
            for ref in file_path_refs:
                directory = '/'.join(ref.value.split('/')[:-1]) if '/' in ref.value else ''
                if directory not in path_groups:
                    path_groups[directory] = []
                path_groups[directory].append(ref)
            
            # Penalize if files from same directory use different abstraction patterns
            for directory, refs in path_groups.items():
                if len(refs) > 1:
                    abstractions_for_group = [
                        a for a in result.abstractions
                        if any(a.original == ref.value for ref in refs)
                    ]
                    if len(abstractions_for_group) > 1:
                        patterns = set(a.abstracted for a in abstractions_for_group)
                        if len(patterns) > 1:
                            penalty += 0.1
        
        return min(penalty, 0.5)  # Cap at 50% penalty
    
    def _generate_feedback(
        self,
        result: AbstractionResult,
        component_scores: Dict[str, float]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate detailed feedback about abstraction quality."""
        feedback = []
        strengths = []
        improvements = []
        
        # Overall assessment
        overall_score = sum(
            self.weights.get(component, 0.0) * score
            for component, score in component_scores.items()
        )
        
        quality_level = self._get_quality_level(overall_score)
        feedback.append(f"Overall abstraction quality: {quality_level} ({overall_score:.3f})")
        
        # Component-specific feedback
        for component, score in component_scores.items():
            if score >= 0.8:
                strengths.append(f"Excellent {component} ({score:.2f})")
            elif score >= 0.6:
                feedback.append(f"Good {component} ({score:.2f})")
            else:
                improvements.append(f"Improve {component} ({score:.2f})")
        
        # Specific recommendations
        if component_scores.get('specificity', 0) < 0.6:
            improvements.append("Use more specific, semantic placeholder names")
        
        if component_scores.get('consistency', 0) < 0.7:
            improvements.append("Ensure consistent abstraction patterns for similar references")
        
        if component_scores.get('completeness', 0) < 0.8:
            improvements.append("Abstract all detected concrete references")
        
        return feedback, strengths, improvements
    
    def _generate_metadata(
        self,
        result: AbstractionResult,
        component_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate metadata about the scoring process."""
        return {
            "scorer_version": "1.0.0",
            "scoring_timestamp": logger.info.__defaults__,  # Would use datetime in real implementation
            "abstraction_count": len(result.abstractions),
            "reference_count": len(result.references),
            "processing_time_ms": result.processing_time_ms,
            "coverage_ratio": result.coverage_score,
            "quality_level": self._get_quality_level(
                sum(self.weights.get(c, 0.0) * s for c, s in component_scores.items())
            ),
            "component_weights": self.weights,
            "reference_type_distribution": dict(Counter(r.type for r in result.references))
        }
    
    def _get_quality_level(self, score: float) -> str:
        """Get quality level name for a score."""
        for level, threshold in sorted(self.thresholds.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return level
        return "unacceptable"
    
    def get_scoring_statistics(self, scores: List[QualityScore]) -> Dict[str, Any]:
        """Generate statistics from multiple quality scores."""
        if not scores:
            return {}
        
        overall_scores = [s.overall_score for s in scores]
        component_averages = {}
        
        # Calculate component averages
        for component in self.COMPONENT_WEIGHTS.keys():
            component_scores = [s.component_scores.get(component, 0.0) for s in scores]
            component_averages[component] = sum(component_scores) / len(component_scores)
        
        return {
            "total_assessments": len(scores),
            "average_overall_score": sum(overall_scores) / len(overall_scores),
            "min_score": min(overall_scores),
            "max_score": max(overall_scores),
            "component_averages": component_averages,
            "quality_distribution": {
                level: sum(1 for s in overall_scores if self._get_quality_level(s) == level)
                for level in self.thresholds.keys()
            }
        }