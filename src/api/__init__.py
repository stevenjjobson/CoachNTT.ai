"""
CoachNTT.ai REST API module.

This module provides the FastAPI application for the cognitive coding partner,
with safety-first design and comprehensive abstraction enforcement.
"""

from .config import APISettings, get_settings
from .main import app, get_application

__all__ = [
    "app",
    "get_application",
    "APISettings",
    "get_settings",
]

__version__ = "1.0.0"