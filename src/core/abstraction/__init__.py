"""
Abstraction module for the Cognitive Coding Partner.
"""

from .engine import AbstractionEngine
from .concrete_engine import ConcreteAbstractionEngine
from .extractor import ReferenceExtractor
from .generator import PatternGenerator
from .rules import AbstractionRules

__all__ = [
    'AbstractionEngine',
    'ConcreteAbstractionEngine',
    'ReferenceExtractor',
    'PatternGenerator',
    'AbstractionRules',
]