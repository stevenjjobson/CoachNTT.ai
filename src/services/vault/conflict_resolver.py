"""
Conflict detection and resolution for vault synchronization.

Handles conflicts between memory content and vault files with multiple
resolution strategies and safety validation.
"""

import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from .models import (
    MarkdownNote,
    ConflictInfo,
    ConflictStrategy,
    SyncDirection
)
from ...core.validation.validator import SafetyValidator

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    Resolves synchronization conflicts between memory and vault content.
    
    Provides multiple resolution strategies with safety validation and
    change tracking capabilities.
    """
    
    def __init__(
        self,
        strategy: ConflictStrategy = ConflictStrategy.SAFE_MERGE,
        safety_validator: Optional[SafetyValidator] = None
    ):
        """
        Initialize conflict resolver.
        
        Args:
            strategy: Default conflict resolution strategy
            safety_validator: Safety validator for content validation
        """
        self.default_strategy = strategy
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Statistics
        self._stats = {
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'conflicts_skipped': 0,
            'auto_resolutions': 0,
            'manual_resolutions': 0,
            'resolution_failures': 0,
            'total_processing_time_ms': 0,
            'strategy_usage': {
                'memory_wins': 0,
                'vault_wins': 0,
                'safe_merge': 0,
                'user_prompt': 0,
                'skip_conflicted': 0
            }
        }
        
        logger.info(f"ConflictResolver initialized with strategy: {strategy.value}")
    
    async def detect_conflict(
        self,
        note: MarkdownNote,
        vault_file: Path
    ) -> Optional[ConflictInfo]:
        """
        Detect conflict between note and existing vault file.
        
        Args:
            note: Markdown note to check
            vault_file: Existing vault file path
            
        Returns:
            Conflict information if conflict detected, None otherwise
        """
        try:
            if not vault_file.exists():
                return None  # No conflict if file doesn't exist
            
            # Read existing vault content
            vault_content = vault_file.read_text(encoding='utf-8')
            
            # Compare content hashes
            note_hash = self._calculate_content_hash(note.get_full_markdown())
            vault_hash = self._calculate_content_hash(vault_content)
            
            if note_hash == vault_hash:
                return None  # No conflict if content is identical
            
            # Get file timestamps
            vault_stat = vault_file.stat()
            vault_modified = datetime.fromtimestamp(vault_stat.st_mtime)
            
            # Create conflict info
            conflict = ConflictInfo(
                memory_id=note.memory_id,
                vault_file_path=vault_file,
                conflict_type=self._determine_conflict_type(note, vault_content),
                memory_content=note.get_full_markdown(),
                vault_content=vault_content,
                memory_updated_at=note.updated_at,
                vault_updated_at=vault_modified
            )
            
            self._stats['conflicts_detected'] += 1
            
            logger.debug(f"Conflict detected: {conflict.conflict_type} for {vault_file.name}")
            return conflict
            
        except Exception as e:
            logger.error(f"Conflict detection failed for {vault_file}: {e}")
            return None
    
    async def resolve_conflict(
        self,
        conflict: ConflictInfo,
        strategy: Optional[ConflictStrategy] = None
    ) -> Optional[ConflictInfo]:
        """
        Resolve detected conflict using specified strategy.
        
        Args:
            conflict: Conflict information
            strategy: Resolution strategy (uses default if None)
            
        Returns:
            Updated conflict info with resolution, None if failed
        """
        start_time = time.time()
        resolution_strategy = strategy or self.default_strategy
        
        try:
            logger.debug(f"Resolving conflict {conflict.conflict_id} with strategy: {resolution_strategy.value}")
            
            # Apply resolution strategy
            if resolution_strategy == ConflictStrategy.MEMORY_WINS:
                resolved_content = await self._resolve_memory_wins(conflict)
            elif resolution_strategy == ConflictStrategy.VAULT_WINS:
                resolved_content = await self._resolve_vault_wins(conflict)
            elif resolution_strategy == ConflictStrategy.SAFE_MERGE:
                resolved_content = await self._resolve_safe_merge(conflict)
            elif resolution_strategy == ConflictStrategy.USER_PROMPT:
                resolved_content = await self._resolve_user_prompt(conflict)
            elif resolution_strategy == ConflictStrategy.SKIP_CONFLICTED:
                resolved_content = await self._resolve_skip(conflict)
            else:
                logger.error(f"Unknown resolution strategy: {resolution_strategy}")
                return None
            
            if resolved_content is not None:
                # Validate safety of resolved content
                if await self._validate_resolution_safety(resolved_content):
                    # Write resolved content to vault
                    await self._write_resolved_content(conflict, resolved_content)
                    
                    # Update conflict info
                    conflict.resolved = True
                    conflict.resolved_at = datetime.now()
                    conflict.resolution_strategy = resolution_strategy
                    conflict.resolution_note = f"Resolved using {resolution_strategy.value}"
                    
                    # Update statistics
                    processing_time = (time.time() - start_time) * 1000
                    self._stats['conflicts_resolved'] += 1
                    self._stats['strategy_usage'][resolution_strategy.value] += 1
                    self._stats['total_processing_time_ms'] += processing_time
                    
                    if resolution_strategy != ConflictStrategy.USER_PROMPT:
                        self._stats['auto_resolutions'] += 1
                    else:
                        self._stats['manual_resolutions'] += 1
                    
                    logger.debug(f"Conflict resolved in {processing_time:.1f}ms")
                    return conflict
                else:
                    logger.warning("Resolved content failed safety validation")
                    self._stats['resolution_failures'] += 1
            else:
                logger.warning("Conflict resolution produced no content")
                self._stats['conflicts_skipped'] += 1
            
            return None
            
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            self._stats['resolution_failures'] += 1
            return None
    
    async def _resolve_memory_wins(self, conflict: ConflictInfo) -> Optional[str]:
        """Resolve conflict by using memory content."""
        try:
            # Memory content takes precedence
            return conflict.memory_content
        except Exception as e:
            logger.error(f"Memory wins resolution failed: {e}")
            return None
    
    async def _resolve_vault_wins(self, conflict: ConflictInfo) -> Optional[str]:
        """Resolve conflict by using vault content."""
        try:
            # Vault content takes precedence
            return conflict.vault_content
        except Exception as e:
            logger.error(f"Vault wins resolution failed: {e}")
            return None
    
    async def _resolve_safe_merge(self, conflict: ConflictInfo) -> Optional[str]:
        """Resolve conflict by attempting safe merge."""
        try:
            # Attempt intelligent merge based on content structure
            memory_lines = conflict.memory_content.split('\n')
            vault_lines = conflict.vault_content.split('\n')
            
            # Simple merge strategy: prefer newer content for different sections
            merged_lines = []
            
            # Use memory content as base
            merged_lines.extend(memory_lines)
            
            # Add any unique vault content that doesn't conflict
            vault_unique = await self._find_unique_vault_content(
                conflict.memory_content, 
                conflict.vault_content
            )
            
            if vault_unique:
                merged_lines.append("\n## Additional Vault Content\n")
                merged_lines.extend(vault_unique.split('\n'))
            
            merged_content = '\n'.join(merged_lines)
            
            # Validate merged content
            if await self._validate_merge_content(merged_content):
                return merged_content
            else:
                # Fall back to memory wins if merge validation fails
                logger.debug("Safe merge validation failed, falling back to memory wins")
                return conflict.memory_content
            
        except Exception as e:
            logger.error(f"Safe merge resolution failed: {e}")
            return conflict.memory_content  # Fallback to memory content
    
    async def _resolve_user_prompt(self, conflict: ConflictInfo) -> Optional[str]:
        """Resolve conflict by prompting user (simulated)."""
        try:
            # In a real implementation, this would prompt the user
            # For now, simulate by using the newer content
            
            if (conflict.memory_updated_at and conflict.vault_updated_at and
                conflict.memory_updated_at > conflict.vault_updated_at):
                logger.debug("User prompt simulation: choosing memory (newer)")
                return conflict.memory_content
            else:
                logger.debug("User prompt simulation: choosing vault (newer)")
                return conflict.vault_content
            
        except Exception as e:
            logger.error(f"User prompt resolution failed: {e}")
            return None
    
    async def _resolve_skip(self, conflict: ConflictInfo) -> Optional[str]:
        """Resolve conflict by skipping (no change)."""
        # Return None to indicate skipping
        logger.debug("Conflict skipped as per strategy")
        return None
    
    async def _find_unique_vault_content(
        self,
        memory_content: str,
        vault_content: str
    ) -> Optional[str]:
        """Find content unique to vault that doesn't conflict with memory."""
        try:
            # Simple approach: find lines in vault not in memory
            memory_lines = set(memory_content.split('\n'))
            vault_lines = vault_content.split('\n')
            
            unique_lines = []
            for line in vault_lines:
                if line.strip() and line not in memory_lines:
                    # Check if line contains potentially useful content
                    if len(line.strip()) > 10 and not line.startswith('#'):
                        unique_lines.append(line)
            
            if unique_lines:
                return '\n'.join(unique_lines)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find unique vault content: {e}")
            return None
    
    async def _validate_merge_content(self, content: str) -> bool:
        """Validate merged content for safety and structure."""
        try:
            # Check safety
            abstracted_content, concrete_refs = self.safety_validator.auto_abstract_content(content)
            if len(concrete_refs) > 0:
                logger.warning("Merged content contains concrete references")
                return False
            
            # Check basic structure (should have title and content)
            lines = content.split('\n')
            has_title = any(line.startswith('#') for line in lines[:5])
            has_content = len([line for line in lines if line.strip()]) > 3
            
            return has_title and has_content
            
        except Exception as e:
            logger.error(f"Merge validation failed: {e}")
            return False
    
    async def _validate_resolution_safety(self, content: str) -> bool:
        """Validate resolved content for safety."""
        try:
            # Use safety validator
            abstracted_content, concrete_refs = self.safety_validator.auto_abstract_content(content)
            
            # Should have minimal concrete references
            if len(concrete_refs) > 5:  # Allow some tolerance for merge content
                logger.warning(f"Resolved content has {len(concrete_refs)} concrete references")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Resolution safety validation failed: {e}")
            return False
    
    async def _write_resolved_content(
        self,
        conflict: ConflictInfo,
        content: str
    ) -> bool:
        """Write resolved content to vault file."""
        try:
            if conflict.vault_file_path:
                # Create backup of original
                backup_path = conflict.vault_file_path.with_suffix('.md.backup')
                if conflict.vault_file_path.exists():
                    backup_path.write_text(
                        conflict.vault_file_path.read_text(encoding='utf-8'),
                        encoding='utf-8'
                    )
                
                # Write resolved content
                conflict.vault_file_path.write_text(content, encoding='utf-8')
                
                logger.debug(f"Resolved content written to {conflict.vault_file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to write resolved content: {e}")
            return False
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for comparison."""
        # Normalize content for comparison
        normalized = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def _determine_conflict_type(self, note: MarkdownNote, vault_content: str) -> str:
        """Determine the type of conflict."""
        try:
            # Analyze differences to categorize conflict
            note_content = note.get_full_markdown()
            
            note_lines = len(note_content.split('\n'))
            vault_lines = len(vault_content.split('\n'))
            
            if abs(note_lines - vault_lines) > 10:
                return "major_content_difference"
            elif note.title_pattern not in vault_content:
                return "title_mismatch"
            elif "frontmatter" in vault_content.lower() and not note.frontmatter:
                return "frontmatter_difference"
            else:
                return "content_modification"
                
        except Exception:
            return "unknown_conflict"
    
    async def get_conflict_summary(
        self,
        conflicts: List[ConflictInfo]
    ) -> Dict[str, Any]:
        """Get summary of conflicts for analysis."""
        try:
            if not conflicts:
                return {'total_conflicts': 0}
            
            summary = {
                'total_conflicts': len(conflicts),
                'resolved_conflicts': len([c for c in conflicts if c.resolved]),
                'unresolved_conflicts': len([c for c in conflicts if not c.resolved]),
                'conflict_types': {},
                'resolution_strategies': {},
                'average_resolution_time': 0
            }
            
            # Analyze conflict types
            for conflict in conflicts:
                conflict_type = conflict.conflict_type
                summary['conflict_types'][conflict_type] = (
                    summary['conflict_types'].get(conflict_type, 0) + 1
                )
                
                if conflict.resolved and conflict.resolution_strategy:
                    strategy = conflict.resolution_strategy.value
                    summary['resolution_strategies'][strategy] = (
                        summary['resolution_strategies'].get(strategy, 0) + 1
                    )
            
            # Calculate resolution success rate
            if summary['total_conflicts'] > 0:
                summary['resolution_success_rate'] = (
                    summary['resolved_conflicts'] / summary['total_conflicts']
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate conflict summary: {e}")
            return {'total_conflicts': len(conflicts), 'error': str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conflict resolver statistics."""
        stats = self._stats.copy()
        
        # Add derived metrics
        total_conflicts = stats['conflicts_detected']
        if total_conflicts > 0:
            stats['resolution_success_rate'] = (
                stats['conflicts_resolved'] / total_conflicts
            )
            stats['auto_resolution_rate'] = (
                stats['auto_resolutions'] / total_conflicts
            )
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['conflicts_resolved']
                if stats['conflicts_resolved'] > 0 else 0
            )
        else:
            stats.update({
                'resolution_success_rate': 1.0,
                'auto_resolution_rate': 1.0,
                'average_processing_time_ms': 0
            })
        
        # Add strategy effectiveness
        total_strategy_usage = sum(stats['strategy_usage'].values())
        if total_strategy_usage > 0:
            stats['strategy_effectiveness'] = {
                strategy: (count / total_strategy_usage) * 100
                for strategy, count in stats['strategy_usage'].items()
            }
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down conflict resolver...")
        # No special cleanup needed
        logger.info("Conflict resolver shutdown completed")