"""
Language detection utility for code analysis.

Provides fast and accurate programming language detection with safety-first principles.
"""

import re
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from .models import LanguageType, AnalysisMetadata
from ..validation.validator import SafetyValidator


class LanguageDetector:
    """
    Fast programming language detection for code analysis.
    
    Uses file extensions, syntax patterns, and keywords to identify languages
    while maintaining safety through content abstraction.
    """
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        """
        Initialize language detector.
        
        Args:
            safety_validator: Safety validator for content abstraction
        """
        self.safety_validator = safety_validator or SafetyValidator()
        
        # File extension mappings
        self.extension_map = {
            '.py': LanguageType.PYTHON,
            '.pyx': LanguageType.PYTHON,
            '.pyi': LanguageType.PYTHON,
            '.js': LanguageType.JAVASCRIPT,
            '.jsx': LanguageType.JAVASCRIPT,
            '.mjs': LanguageType.JAVASCRIPT,
            '.ts': LanguageType.TYPESCRIPT,
            '.tsx': LanguageType.TYPESCRIPT,
        }
        
        # Language-specific patterns
        self.language_patterns = {
            LanguageType.PYTHON: [
                (r'\bdef\s+\w+\s*\(', 0.8),  # Function definitions
                (r'\bclass\s+\w+\s*\(', 0.8),  # Class definitions
                (r'\bimport\s+\w+', 0.7),  # Import statements
                (r'\bfrom\s+\w+\s+import', 0.8),  # From imports
                (r':\s*$', 0.3),  # Colon line endings
                (r'^\s*#', 0.2),  # Python comments
                (r'\bif\s+__name__\s*==\s*["\']__main__["\']', 0.9),  # Main guard
                (r'\bprint\s*\(', 0.4),  # Print function
                (r'\bself\b', 0.6),  # Self keyword
                (r'\b(True|False|None)\b', 0.5),  # Python keywords
            ],
            
            LanguageType.JAVASCRIPT: [
                (r'\bfunction\s+\w+\s*\(', 0.8),  # Function declarations
                (r'\bvar\s+\w+', 0.6),  # Var declarations
                (r'\blet\s+\w+', 0.7),  # Let declarations
                (r'\bconst\s+\w+', 0.7),  # Const declarations
                (r'//.*$', 0.3),  # Line comments
                (r'/\*.*?\*/', 0.4),  # Block comments
                (r'\bconsole\.log\s*\(', 0.6),  # Console.log
                (r'\bfunction\s*\(', 0.7),  # Anonymous functions
                (r'=>', 0.6),  # Arrow functions
                (r'\b(null|undefined)\b', 0.5),  # JS keywords
                (r';\s*$', 0.4),  # Semicolon endings
            ],
            
            LanguageType.TYPESCRIPT: [
                (r'\binterface\s+\w+', 0.9),  # Interface definitions
                (r'\btype\s+\w+\s*=', 0.8),  # Type aliases
                (r':\s*\w+\s*[=;]', 0.7),  # Type annotations
                (r'\bpublic\s+\w+', 0.6),  # Public modifier
                (r'\bprivate\s+\w+', 0.6),  # Private modifier
                (r'\bprotected\s+\w+', 0.6),  # Protected modifier
                (r'\bgeneric\s*<\w+>', 0.8),  # Generics
                (r'\benum\s+\w+', 0.8),  # Enum definitions
                (r'\bnamespace\s+\w+', 0.9),  # Namespace declarations
                (r'\bas\s+\w+', 0.5),  # Type assertions
            ]
        }
        
        # Minimum confidence threshold for detection
        self.min_confidence = 0.6
        
        # Statistics
        self._stats = {
            'detections_performed': 0,
            'python_detected': 0,
            'javascript_detected': 0,
            'typescript_detected': 0,
            'unknown_detected': 0,
            'total_processing_time_ms': 0
        }
    
    def detect_language(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> Tuple[LanguageType, float, AnalysisMetadata]:
        """
        Detect programming language from content and filename.
        
        Args:
            content: Source code content to analyze
            filename: Optional filename for extension-based detection
            
        Returns:
            Tuple of (detected_language, confidence_score, metadata)
        """
        start_time = time.time()
        
        try:
            # Abstract content for safety
            abstracted_content, concrete_refs = self.safety_validator.auto_abstract_content(content)
            
            # Initialize metadata
            metadata = AnalysisMetadata()
            metadata.concrete_references_found = len(concrete_refs)
            metadata.abstraction_performed = len(concrete_refs) > 0
            
            # Step 1: Try extension-based detection first
            extension_language = None
            extension_confidence = 0.0
            
            if filename:
                # Abstract filename to remove sensitive paths
                abstract_filename = self._abstract_filename(filename)
                extension = self._get_file_extension(abstract_filename)
                
                if extension in self.extension_map:
                    extension_language = self.extension_map[extension]
                    extension_confidence = 0.9  # High confidence for extension matches
            
            # Step 2: Pattern-based detection
            pattern_scores = self._analyze_patterns(abstracted_content)
            
            # Step 3: Combine results
            final_language, final_confidence = self._combine_detection_results(
                extension_language, extension_confidence, pattern_scores
            )
            
            # Calculate safety score
            metadata.safety_score = self._calculate_safety_score(
                len(concrete_refs), len(content), len(abstracted_content)
            )
            
            # Update processing time
            processing_time = (time.time() - start_time) * 1000
            metadata.processing_time_ms = int(processing_time)
            
            # Update statistics
            self._update_stats(final_language, processing_time)
            
            return final_language, final_confidence, metadata
            
        except Exception as e:
            # Fallback to unknown with low confidence
            metadata = AnalysisMetadata()
            metadata.processing_time_ms = int((time.time() - start_time) * 1000)
            return LanguageType.UNKNOWN, 0.0, metadata
    
    def _abstract_filename(self, filename: str) -> str:
        """Abstract filename to remove sensitive path information."""
        try:
            path = Path(filename)
            # Keep only the filename and extension, abstract the path
            return f"<file>{path.suffix}"
        except Exception:
            return "<file>"
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension safely."""
        try:
            return Path(filename).suffix.lower()
        except Exception:
            return ""
    
    def _analyze_patterns(self, content: str) -> Dict[LanguageType, float]:
        """
        Analyze content patterns to determine language.
        
        Args:
            content: Abstracted content to analyze
            
        Returns:
            Dictionary mapping languages to confidence scores
        """
        scores = {lang: 0.0 for lang in LanguageType if lang != LanguageType.UNKNOWN}
        
        # Limit content size for performance
        content_sample = content[:10000]  # First 10KB
        lines = content_sample.split('\n')
        
        for language, patterns in self.language_patterns.items():
            language_score = 0.0
            pattern_matches = 0
            
            for pattern, weight in patterns:
                try:
                    matches = len(re.findall(pattern, content_sample, re.MULTILINE))
                    if matches > 0:
                        pattern_matches += 1
                        # Normalize by content length
                        normalized_score = min(matches / max(len(lines), 1), 1.0)
                        language_score += normalized_score * weight
                except re.error:
                    # Skip invalid regex patterns
                    continue
            
            # Average score across matched patterns
            if pattern_matches > 0:
                scores[language] = min(language_score / pattern_matches, 1.0)
        
        return scores
    
    def _combine_detection_results(
        self,
        extension_language: Optional[LanguageType],
        extension_confidence: float,
        pattern_scores: Dict[LanguageType, float]
    ) -> Tuple[LanguageType, float]:
        """
        Combine extension and pattern detection results.
        
        Args:
            extension_language: Language detected from extension
            extension_confidence: Confidence from extension detection
            pattern_scores: Confidence scores from pattern analysis
            
        Returns:
            Tuple of (final_language, final_confidence)
        """
        # If extension detection is confident and matches pattern analysis
        if extension_language and extension_confidence > 0.8:
            pattern_confidence = pattern_scores.get(extension_language, 0.0)
            if pattern_confidence > 0.3:  # Pattern supports extension
                combined_confidence = (extension_confidence + pattern_confidence) / 2
                return extension_language, min(combined_confidence, 1.0)
        
        # Find highest pattern score
        if pattern_scores:
            best_language = max(pattern_scores.keys(), key=lambda k: pattern_scores[k])
            best_score = pattern_scores[best_language]
            
            if best_score >= self.min_confidence:
                return best_language, best_score
        
        # Fallback: use extension if available, otherwise unknown
        if extension_language:
            return extension_language, extension_confidence
        
        return LanguageType.UNKNOWN, 0.0
    
    def _calculate_safety_score(
        self,
        concrete_refs_found: int,
        original_length: int,
        abstracted_length: int
    ) -> float:
        """Calculate safety score for the detection process."""
        base_score = 1.0
        
        # Penalize concrete references
        if concrete_refs_found > 0:
            penalty = min(0.3, concrete_refs_found * 0.05)
            base_score -= penalty
        
        # Ensure abstraction didn't remove too much content
        if original_length > 0:
            retention_ratio = abstracted_length / original_length
            if retention_ratio < 0.5:
                base_score -= 0.2
        
        return max(base_score, 0.0)
    
    def _update_stats(self, language: LanguageType, processing_time: float) -> None:
        """Update detection statistics."""
        self._stats['detections_performed'] += 1
        self._stats['total_processing_time_ms'] += processing_time
        
        if language == LanguageType.PYTHON:
            self._stats['python_detected'] += 1
        elif language == LanguageType.JAVASCRIPT:
            self._stats['javascript_detected'] += 1
        elif language == LanguageType.TYPESCRIPT:
            self._stats['typescript_detected'] += 1
        else:
            self._stats['unknown_detected'] += 1
    
    def get_stats(self) -> Dict[str, any]:
        """Get detection statistics."""
        stats = self._stats.copy()
        
        if stats['detections_performed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['detections_performed']
            )
            stats['python_detection_rate'] = (
                stats['python_detected'] / stats['detections_performed']
            )
            stats['javascript_detection_rate'] = (
                stats['javascript_detected'] / stats['detections_performed']
            )
            stats['typescript_detection_rate'] = (
                stats['typescript_detected'] / stats['detections_performed']
            )
            stats['unknown_rate'] = (
                stats['unknown_detected'] / stats['detections_performed']
            )
        else:
            stats.update({
                'average_processing_time_ms': 0,
                'python_detection_rate': 0,
                'javascript_detection_rate': 0,
                'typescript_detection_rate': 0,
                'unknown_rate': 0
            })
        
        return stats
    
    def get_supported_languages(self) -> List[LanguageType]:
        """Get list of supported languages."""
        return [lang for lang in LanguageType if lang != LanguageType.UNKNOWN]
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(self.extension_map.keys())