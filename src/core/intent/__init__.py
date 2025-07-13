"""
Intent analysis and connection finding system for cognitive memory.

Provides intelligent query analysis, intent classification, and connection discovery
while maintaining safety-first principles and non-directive interactions.
"""

from .models import (
    IntentType,
    IntentResult,
    IntentMetadata,
    ConnectionType,
    Connection,
    ConnectionResult,
    QueryAnalysis,
    IntentPattern,
    ExplanationReason,
    FeedbackType,
    LearningFeedback
)

from .engine import IntentEngine
from .analyzer import IntentAnalyzer
from .connections import ConnectionFinder

__all__ = [
    # Models
    'IntentType',
    'IntentResult', 
    'IntentMetadata',
    'ConnectionType',
    'Connection',
    'ConnectionResult',
    'QueryAnalysis',
    'IntentPattern',
    'ExplanationReason',
    'FeedbackType',
    'LearningFeedback',
    
    # Core classes
    'IntentEngine',
    'IntentAnalyzer',
    'ConnectionFinder'
]