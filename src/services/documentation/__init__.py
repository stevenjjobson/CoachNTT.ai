"""
Documentation generation services for CoachNTT.ai.

Provides automated documentation generation with safety-first design,
integrating with AST analysis and script automation framework.
"""

from .generator import DocumentationGenerator
from .models import (
    DocumentationType,
    DocumentationResult,
    DocumentationConfig,
    TemplateConfig,
    DiagramConfig
)

__all__ = [
    'DocumentationGenerator',
    'DocumentationType',
    'DocumentationResult', 
    'DocumentationConfig',
    'TemplateConfig',
    'DiagramConfig'
]