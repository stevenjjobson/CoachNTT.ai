"""
Design pattern detection for code analysis.

Identifies common design patterns (Singleton, Factory, Observer) with safety-first abstraction.
"""

import re
import ast
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .models import (
    DesignPattern,
    PatternMatch,
    PatternType,
    AnalysisResult,
    LanguageType,
    ClassStructure,
    FunctionSignature
)
from ..validation.validator import SafetyValidator

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Design pattern detection for various programming languages.
    
    Identifies common patterns while maintaining safety through abstraction.
    """
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        """
        Initialize pattern detector.
        
        Args:
            safety_validator: Safety validator for content abstraction
        """
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Pattern detection thresholds
        self.confidence_threshold = 0.7
        
        # Statistics
        self._stats = {
            'detections_performed': 0,
            'singleton_patterns_found': 0,
            'factory_patterns_found': 0,
            'observer_patterns_found': 0,
            'total_processing_time_ms': 0
        }
        
        logger.info("PatternDetector initialized")
    
    async def detect_patterns(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> List[DesignPattern]:
        """
        Detect design patterns in the analyzed code.
        
        Args:
            analysis_result: AST analysis result
            content: Abstracted source code content
            
        Returns:
            List of detected design patterns
        """
        import time
        start_time = time.time()
        
        try:
            patterns = []
            
            # Detect different pattern types
            singleton_patterns = await self._detect_singleton_patterns(analysis_result, content)
            if singleton_patterns:
                patterns.extend(singleton_patterns)
                self._stats['singleton_patterns_found'] += len(singleton_patterns)
            
            factory_patterns = await self._detect_factory_patterns(analysis_result, content)
            if factory_patterns:
                patterns.extend(factory_patterns)
                self._stats['factory_patterns_found'] += len(factory_patterns)
            
            observer_patterns = await self._detect_observer_patterns(analysis_result, content)
            if observer_patterns:
                patterns.extend(observer_patterns)
                self._stats['observer_patterns_found'] += len(observer_patterns)
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self._stats['detections_performed'] += 1
            self._stats['total_processing_time_ms'] += processing_time
            
            logger.debug(f"Pattern detection completed in {processing_time:.1f}ms: {len(patterns)} patterns found")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []
    
    async def _detect_singleton_patterns(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> List[DesignPattern]:
        """
        Detect Singleton pattern implementations.
        
        Args:
            analysis_result: AST analysis result
            content: Abstracted source code content
            
        Returns:
            List of Singleton pattern matches
        """
        singleton_patterns = []
        
        if analysis_result.language == LanguageType.PYTHON:
            singleton_patterns.extend(await self._detect_python_singleton(analysis_result, content))
        elif analysis_result.language in [LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]:
            singleton_patterns.extend(await self._detect_javascript_singleton(analysis_result, content))
        
        return singleton_patterns
    
    async def _detect_python_singleton(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> List[DesignPattern]:
        """Detect Python Singleton patterns."""
        patterns = []
        
        for class_struct in analysis_result.classes:
            matches = []
            confidence_factors = []
            
            # Check for __new__ method override (classic singleton)
            has_new_method = any(
                method.name_pattern == "<new_method>" or "__new__" in method.name_pattern
                for method in class_struct.methods
            )
            
            if has_new_method:
                match = PatternMatch(
                    pattern_type=PatternType.SINGLETON,
                    confidence=0.8,
                    elements=[class_struct.name_pattern],
                    explanation="Class overrides __new__ method (singleton indicator)",
                    location_pattern=f"<class_{class_struct.name_pattern}>"
                )
                matches.append(match)
                confidence_factors.append(0.8)
            
            # Check for instance variable and getInstance method
            has_instance_pattern = self._check_instance_pattern(content, class_struct.name_pattern)
            if has_instance_pattern:
                match = PatternMatch(
                    pattern_type=PatternType.SINGLETON,
                    confidence=0.7,
                    elements=[class_struct.name_pattern],
                    explanation="Class has instance variable and getInstance pattern",
                    location_pattern=f"<class_{class_struct.name_pattern}>"
                )
                matches.append(match)
                confidence_factors.append(0.7)
            
            # Check for metaclass singleton
            if self._check_metaclass_singleton(content):
                match = PatternMatch(
                    pattern_type=PatternType.SINGLETON,
                    confidence=0.9,
                    elements=[class_struct.name_pattern],
                    explanation="Uses metaclass for singleton implementation",
                    location_pattern=f"<class_{class_struct.name_pattern}>"
                )
                matches.append(match)
                confidence_factors.append(0.9)
            
            # Create pattern if matches found
            if matches:
                overall_confidence = max(confidence_factors)
                pattern = DesignPattern(
                    pattern_type=PatternType.SINGLETON,
                    matches=matches,
                    overall_confidence=overall_confidence
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_javascript_singleton(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> List[DesignPattern]:
        """Detect JavaScript/TypeScript Singleton patterns."""
        patterns = []
        
        # Check for module singleton pattern
        if self._check_module_singleton(content):
            match = PatternMatch(
                pattern_type=PatternType.SINGLETON,
                confidence=0.8,
                elements=["<module_export>"],
                explanation="Module exports singleton object",
                location_pattern="<module_level>"
            )
            
            pattern = DesignPattern(
                pattern_type=PatternType.SINGLETON,
                matches=[match],
                overall_confidence=0.8
            )
            patterns.append(pattern)
        
        # Check for class-based singleton
        for class_struct in analysis_result.classes:
            if self._check_js_class_singleton(content, class_struct.name_pattern):
                match = PatternMatch(
                    pattern_type=PatternType.SINGLETON,
                    confidence=0.7,
                    elements=[class_struct.name_pattern],
                    explanation="Class implements singleton pattern with static instance",
                    location_pattern=f"<class_{class_struct.name_pattern}>"
                )
                
                pattern = DesignPattern(
                    pattern_type=PatternType.SINGLETON,
                    matches=[match],
                    overall_confidence=0.7
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_factory_patterns(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> List[DesignPattern]:
        """
        Detect Factory pattern implementations.
        
        Args:
            analysis_result: AST analysis result
            content: Abstracted source code content
            
        Returns:
            List of Factory pattern matches
        """
        factory_patterns = []
        
        # Look for factory method patterns
        for func in analysis_result.functions:
            if self._is_factory_method(func, content):
                match = PatternMatch(
                    pattern_type=PatternType.FACTORY,
                    confidence=0.8,
                    elements=[func.name_pattern],
                    explanation="Function creates and returns objects based on parameters",
                    location_pattern=f"<function_{func.name_pattern}>"
                )
                
                pattern = DesignPattern(
                    pattern_type=PatternType.FACTORY,
                    matches=[match],
                    overall_confidence=0.8
                )
                factory_patterns.append(pattern)
        
        # Look for factory class patterns
        for class_struct in analysis_result.classes:
            if self._is_factory_class(class_struct, content):
                match = PatternMatch(
                    pattern_type=PatternType.FACTORY,
                    confidence=0.7,
                    elements=[class_struct.name_pattern],
                    explanation="Class provides factory methods for object creation",
                    location_pattern=f"<class_{class_struct.name_pattern}>"
                )
                
                pattern = DesignPattern(
                    pattern_type=PatternType.FACTORY,
                    matches=[match],
                    overall_confidence=0.7
                )
                factory_patterns.append(pattern)
        
        return factory_patterns
    
    async def _detect_observer_patterns(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> List[DesignPattern]:
        """
        Detect Observer pattern implementations.
        
        Args:
            analysis_result: AST analysis result
            content: Abstracted source code content
            
        Returns:
            List of Observer pattern matches
        """
        observer_patterns = []
        
        for class_struct in analysis_result.classes:
            observer_elements = []
            confidence_factors = []
            
            # Check for observer interface methods
            has_update_method = any(
                "update" in method.name_pattern.lower() or "notify" in method.name_pattern.lower()
                for method in class_struct.methods
            )
            
            # Check for subject interface methods
            has_subject_methods = any(
                method.name_pattern.lower() in ["<add_observer>", "<remove_observer>", "<notify_observers>"]
                for method in class_struct.methods
            )
            
            # Check for observer list/collection
            has_observer_collection = self._check_observer_collection(content, class_struct.name_pattern)
            
            if has_update_method:
                observer_elements.append(f"<observer_{class_struct.name_pattern}>")
                confidence_factors.append(0.6)
            
            if has_subject_methods:
                observer_elements.append(f"<subject_{class_struct.name_pattern}>")
                confidence_factors.append(0.8)
            
            if has_observer_collection:
                confidence_factors.append(0.7)
            
            # Create pattern if sufficient evidence
            if len(confidence_factors) >= 2 or max(confidence_factors, default=0) >= 0.8:
                overall_confidence = sum(confidence_factors) / len(confidence_factors)
                
                match = PatternMatch(
                    pattern_type=PatternType.OBSERVER,
                    confidence=overall_confidence,
                    elements=observer_elements,
                    explanation="Class implements observer pattern with notify/update mechanism",
                    location_pattern=f"<class_{class_struct.name_pattern}>"
                )
                
                pattern = DesignPattern(
                    pattern_type=PatternType.OBSERVER,
                    matches=[match],
                    overall_confidence=overall_confidence
                )
                observer_patterns.append(pattern)
        
        return observer_patterns
    
    def _check_instance_pattern(self, content: str, class_pattern: str) -> bool:
        """Check for instance variable and getInstance pattern."""
        # Look for patterns like _instance = None or getInstance()
        instance_patterns = [
            r'_instance\s*=\s*None',
            r'instance\s*=\s*None',
            r'def\s+getInstance\s*\(',
            r'def\s+get_instance\s*\('
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in instance_patterns)
    
    def _check_metaclass_singleton(self, content: str) -> bool:
        """Check for metaclass-based singleton implementation."""
        metaclass_patterns = [
            r'class\s+\w+\s*\(\s*type\s*\)',
            r'metaclass\s*=\s*\w+',
            r'__call__.*singleton'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in metaclass_patterns)
    
    def _check_module_singleton(self, content: str) -> bool:
        """Check for JavaScript module singleton pattern."""
        module_patterns = [
            r'module\.exports\s*=\s*\{',
            r'export\s+default\s*\{',
            r'const\s+\w+\s*=\s*\{.*\}.*export'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in module_patterns)
    
    def _check_js_class_singleton(self, content: str, class_pattern: str) -> bool:
        """Check for JavaScript class-based singleton."""
        js_singleton_patterns = [
            r'static\s+instance',
            r'static\s+getInstance\s*\(',
            r'if\s*\(.*instance.*\)',
            r'new\.target'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in js_singleton_patterns)
    
    def _is_factory_method(self, func: FunctionSignature, content: str) -> bool:
        """Check if function is a factory method."""
        # Check function name patterns
        factory_name_patterns = [
            "create", "build", "make", "factory", "new"
        ]
        
        name_indicates_factory = any(
            pattern in func.name_pattern.lower() 
            for pattern in factory_name_patterns
        )
        
        # Check return patterns (simplified check)
        returns_object = func.return_type and func.return_type != "None"
        
        # Check parameters (factory methods often take parameters)
        has_parameters = func.parameter_count > 0
        
        # Combined score
        score = 0
        if name_indicates_factory:
            score += 0.6
        if returns_object:
            score += 0.3
        if has_parameters:
            score += 0.2
        
        return score >= 0.7
    
    def _is_factory_class(self, class_struct: ClassStructure, content: str) -> bool:
        """Check if class is a factory class."""
        # Check for factory methods in class
        factory_methods = sum(
            1 for method in class_struct.methods
            if self._is_factory_method(method, content)
        )
        
        # Check class name
        name_indicates_factory = any(
            pattern in class_struct.name_pattern.lower()
            for pattern in ["factory", "builder", "creator"]
        )
        
        return factory_methods >= 2 or (factory_methods >= 1 and name_indicates_factory)
    
    def _check_observer_collection(self, content: str, class_pattern: str) -> bool:
        """Check for observer collection in class."""
        collection_patterns = [
            r'observers\s*=\s*\[\]',
            r'listeners\s*=\s*\[\]',
            r'subscribers\s*=\s*\[\]',
            r'self\.observers',
            r'self\.listeners'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in collection_patterns)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pattern detection statistics."""
        stats = self._stats.copy()
        
        if stats['detections_performed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['detections_performed']
            )
            stats['singleton_detection_rate'] = (
                stats['singleton_patterns_found'] / stats['detections_performed']
            )
            stats['factory_detection_rate'] = (
                stats['factory_patterns_found'] / stats['detections_performed']
            )
            stats['observer_detection_rate'] = (
                stats['observer_patterns_found'] / stats['detections_performed']
            )
        else:
            stats.update({
                'average_processing_time_ms': 0,
                'singleton_detection_rate': 0,
                'factory_detection_rate': 0,
                'observer_detection_rate': 0
            })
        
        return stats