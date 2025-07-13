"""
AST Code Analysis Module for Cognitive Coding Partner.

Provides abstract syntax tree analysis, pattern detection, and code understanding
with safety-first abstraction of all concrete references.
"""

from .models import (
    # Core analysis models
    AnalysisResult,
    AnalysisMetadata,
    LanguageType,
    PatternType,
    ComplexityMetrics,
    
    # Function and class models
    FunctionSignature,
    ClassStructure,
    VariableScope,
    DependencyNode,
    
    # Pattern detection models
    DesignPattern,
    PatternMatch,
    
    # Quality assessment
    QualityMetrics,
    QualityIssue,
    QualityLevel
)

from .ast_analyzer import ASTAnalyzer
from .language_detector import LanguageDetector
from .pattern_detector import PatternDetector
from .complexity_analyzer import ComplexityAnalyzer

__all__ = [
    # Core models
    'AnalysisResult',
    'AnalysisMetadata', 
    'LanguageType',
    'PatternType',
    'ComplexityMetrics',
    
    # Structure models
    'FunctionSignature',
    'ClassStructure',
    'VariableScope',
    'DependencyNode',
    
    # Pattern models
    'DesignPattern',
    'PatternMatch',
    
    # Quality models
    'QualityMetrics',
    'QualityIssue',
    'QualityLevel',
    
    # Core analyzers
    'ASTAnalyzer',
    'LanguageDetector',
    'PatternDetector',
    'ComplexityAnalyzer'
]