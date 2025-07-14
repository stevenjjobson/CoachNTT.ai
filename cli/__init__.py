"""
CoachNTT.ai CLI Module

Command-line interface for the Cognitive Coding Partner, providing immediate access
to memory management, knowledge graphs, and automation features.

This module provides a safety-first CLI that integrates with the existing API
and maintains all abstraction and validation requirements.
"""

__version__ = "0.1.0"
__author__ = "CoachNTT.ai"

from .core import CLIEngine
from .utils import format_output, safe_print

__all__ = [
    "CLIEngine",
    "format_output", 
    "safe_print"
]