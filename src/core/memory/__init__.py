"""
Memory models and repository for CoachNTT.ai.

This module provides safety-first memory abstractions with mandatory validation.
All memory operations enforce abstraction and prevent concrete references.
"""

from .abstract_models import (
    AbstractMemoryEntry,
    SafeInteraction,
    ValidationResult,
    MemoryMetadata,
    Reference,
    AbstractionMapping,
)
from .repository import SafeMemoryRepository
from .validator import MemoryValidator

__all__ = [
    "AbstractMemoryEntry",
    "SafeInteraction",
    "ValidationResult",
    "MemoryMetadata",
    "Reference",
    "AbstractionMapping",
    "SafeMemoryRepository",
    "MemoryValidator",
]