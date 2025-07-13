"""
Services module for CoachNTT.ai.

Provides high-level service components for vault synchronization, 
automation, and integration with external systems.
"""

# Vault services
from .vault import (
    VaultSyncEngine,
    VaultSyncConfig,
    MarkdownConverter,
    TemplateProcessor,
    ConflictResolver,
    MarkdownNote,
    SyncResult,
    ConflictStrategy,
    TemplateType,
    VaultMetadata
)

__all__ = [
    # Vault sync services
    'VaultSyncEngine',
    'VaultSyncConfig', 
    'MarkdownConverter',
    'TemplateProcessor',
    'ConflictResolver',
    
    # Data models
    'MarkdownNote',
    'SyncResult',
    'VaultMetadata',
    
    # Enums
    'ConflictStrategy',
    'TemplateType'
]