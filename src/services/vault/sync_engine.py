"""
Main vault synchronization engine for memory-to-markdown conversion.

Orchestrates the complete vault sync process including template processing,
conflict resolution, and bidirectional synchronization with safety validation.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from .models import (
    VaultSyncConfig,
    VaultMetadata,
    MarkdownNote,
    SyncResult,
    ConflictInfo,
    PerformanceMetrics,
    ConflictStrategy,
    TemplateType,
    SyncDirection
)
from .markdown_converter import MarkdownConverter
from .template_processor import TemplateProcessor
from .conflict_resolver import ConflictResolver

from ...core.memory.repository import SafeMemoryRepository
from ...core.memory.abstract_models import AbstractMemoryEntry
from ...core.validation.validator import SafetyValidator
from ...core.analysis.ast_analyzer import ASTAnalyzer
from ...core.intent.engine import IntentEngine

logger = logging.getLogger(__name__)


class VaultSyncEngine:
    """
    Main engine for synchronizing memories with Obsidian vault.
    
    Provides comprehensive memory-to-markdown conversion with template processing,
    conflict resolution, and bidirectional synchronization capabilities.
    """
    
    def __init__(
        self,
        config: VaultSyncConfig,
        memory_repository: SafeMemoryRepository,
        safety_validator: Optional[SafetyValidator] = None,
        ast_analyzer: Optional[ASTAnalyzer] = None,
        intent_engine: Optional[IntentEngine] = None
    ):
        """
        Initialize vault sync engine.
        
        Args:
            config: Vault synchronization configuration
            memory_repository: Repository for accessing memories
            safety_validator: Safety validator for content abstraction
            ast_analyzer: AST analyzer for code content enrichment
            intent_engine: Intent engine for context-aware processing
        """
        self.config = config
        self.memory_repository = memory_repository
        self.safety_validator = safety_validator or SafetyValidator()
        self.ast_analyzer = ast_analyzer
        self.intent_engine = intent_engine
        
        # Initialize components
        self.markdown_converter = MarkdownConverter(
            safety_validator=self.safety_validator,
            ast_analyzer=self.ast_analyzer
        )
        
        if self.config.enable_templates:
            self.template_processor = TemplateProcessor(
                template_directory=self.config.template_directory,
                safety_validator=self.safety_validator
            )
        else:
            self.template_processor = None
        
        self.conflict_resolver = ConflictResolver(
            strategy=self.config.conflict_strategy,
            safety_validator=self.safety_validator
        )
        
        # Vault metadata
        self.metadata = VaultMetadata.create_empty()
        
        # Statistics
        self._stats = {
            'syncs_performed': 0,
            'total_notes_created': 0,
            'total_notes_updated': 0,
            'total_conflicts_resolved': 0,
            'total_processing_time_ms': 0,
            'average_safety_score': 1.0,
            'template_usage': {},
            'conflict_resolution_success_rate': 1.0
        }
        
        logger.info(f"VaultSyncEngine initialized with vault at {config.vault_path}")
    
    async def sync_memories_to_vault(
        self,
        memory_ids: Optional[List[UUID]] = None,
        template_type: Optional[TemplateType] = None,
        max_memories: Optional[int] = None
    ) -> SyncResult:
        """
        Sync memories to vault as markdown notes.
        
        Args:
            memory_ids: Specific memory IDs to sync (None for all)
            template_type: Template type to use for notes
            max_memories: Maximum number of memories to process
            
        Returns:
            Sync operation result with statistics
        """
        start_time = time.time()
        result = SyncResult(success=True)
        performance = PerformanceMetrics()
        
        try:
            logger.info(f"Starting memory-to-vault sync (template: {template_type}, max: {max_memories})")
            
            # Step 1: Retrieve memories to sync
            memories = await self._get_memories_for_sync(memory_ids, max_memories)
            result.notes_processed = len(memories)
            
            if not memories:
                logger.info("No memories found for sync")
                return result
            
            logger.debug(f"Found {len(memories)} memories to sync")
            
            # Step 2: Convert memories to markdown notes
            conversion_start = time.time()
            notes = []
            
            for memory in memories:
                try:
                    note = await self._convert_memory_to_note(memory, template_type)
                    if note and note.is_safe_for_export():
                        notes.append(note)
                    else:
                        result.safety_violations += 1
                        result.add_warning(f"Memory {memory.id} failed safety validation")
                        
                except Exception as e:
                    logger.error(f"Failed to convert memory {memory.id}: {e}")
                    result.add_error(f"Conversion failed for memory {memory.id}: {str(e)}")
            
            performance.conversion_time_ms = (time.time() - conversion_start) * 1000
            
            # Step 3: Process templates if enabled
            if self.template_processor and template_type:
                template_start = time.time()
                await self._apply_templates_to_notes(notes, template_type)
                performance.template_processing_time_ms = (time.time() - template_start) * 1000
            
            # Step 4: Detect and resolve conflicts
            conflict_start = time.time()
            conflicts = await self._detect_vault_conflicts(notes)
            result.conflicts_detected = len(conflicts)
            
            if conflicts:
                resolved_conflicts = await self._resolve_conflicts(conflicts)
                result.conflicts_resolved = len(resolved_conflicts)
            
            performance.conflict_detection_time_ms = (time.time() - conflict_start) * 1000
            
            # Step 5: Write notes to vault
            write_start = time.time()
            for note in notes:
                try:
                    success = await self._write_note_to_vault(note)
                    if success:
                        if note.file_path and note.file_path.exists():
                            result.notes_updated += 1
                        else:
                            result.notes_created += 1
                    else:
                        result.notes_skipped += 1
                        
                except Exception as e:
                    logger.error(f"Failed to write note {note.title_pattern}: {e}")
                    result.add_error(f"Write failed for note {note.title_pattern}: {str(e)}")
            
            # Step 6: Generate backlinks if enabled
            if self.config.enable_backlinks:
                backlink_start = time.time()
                await self._generate_backlinks(notes)
                performance.backlink_resolution_time_ms = (time.time() - backlink_start) * 1000
            
            # Finalize results
            total_time = (time.time() - start_time) * 1000
            result.processing_time_ms = int(total_time)
            performance.total_time_ms = total_time
            
            # Calculate average safety score
            if notes:
                avg_safety = sum(note.safety_score for note in notes) / len(notes)
                result.average_safety_score = avg_safety
            
            # Update statistics
            self._update_sync_stats(result, performance)
            
            # Update metadata
            self.metadata.last_sync_timestamp = datetime.now()
            self.metadata.notes_created += result.notes_created
            self.metadata.notes_updated += result.notes_updated
            self.metadata.conflicts_detected += result.conflicts_detected
            self.metadata.sync_duration_ms = result.processing_time_ms
            
            logger.info(
                f"Vault sync completed in {total_time:.1f}ms: "
                f"{result.notes_created} created, {result.notes_updated} updated, "
                f"{result.conflicts_detected} conflicts, safety: {result.average_safety_score:.3f}"
            )
            
            # Check performance targets
            if not performance.meets_targets():
                result.add_warning("Performance targets not met")
                logger.warning(f"Performance targets missed: {performance.__dict__}")
            
            return result
            
        except Exception as e:
            logger.error(f"Vault sync failed: {e}")
            result.success = False
            result.add_error(f"Sync operation failed: {str(e)}")
            return result
    
    async def sync_vault_to_memories(
        self,
        vault_files: Optional[List[Path]] = None
    ) -> SyncResult:
        """
        Sync vault markdown notes back to memories.
        
        Args:
            vault_files: Specific files to sync (None for all)
            
        Returns:
            Sync operation result
        """
        start_time = time.time()
        result = SyncResult(success=True)
        
        try:
            logger.info("Starting vault-to-memory sync")
            
            # Step 1: Scan vault for markdown files
            if vault_files is None:
                vault_files = list(self.config.vault_path.glob("*.md"))
            
            result.notes_processed = len(vault_files)
            
            # Step 2: Parse markdown files and convert to memories
            for file_path in vault_files:
                try:
                    note = await self._parse_markdown_file(file_path)
                    if note:
                        # Check if memory already exists
                        existing_memory = await self._find_memory_for_note(note)
                        
                        if existing_memory:
                            # Update existing memory
                            updated = await self._update_memory_from_note(existing_memory, note)
                            if updated:
                                result.notes_updated += 1
                        else:
                            # Create new memory
                            created = await self._create_memory_from_note(note)
                            if created:
                                result.notes_created += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process vault file {file_path}: {e}")
                    result.add_error(f"Failed to process {file_path.name}: {str(e)}")
            
            total_time = (time.time() - start_time) * 1000
            result.processing_time_ms = int(total_time)
            
            logger.info(
                f"Vault-to-memory sync completed in {total_time:.1f}ms: "
                f"{result.notes_created} created, {result.notes_updated} updated"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Vault-to-memory sync failed: {e}")
            result.success = False
            result.add_error(f"Sync operation failed: {str(e)}")
            return result
    
    async def _get_memories_for_sync(
        self,
        memory_ids: Optional[List[UUID]] = None,
        max_memories: Optional[int] = None
    ) -> List[AbstractMemoryEntry]:
        """Get memories to sync based on criteria."""
        try:
            if memory_ids:
                # Get specific memories
                memories = []
                for memory_id in memory_ids:
                    memory = await self.memory_repository.get_memory(memory_id)
                    if memory:
                        memories.append(memory)
                return memories
            else:
                # Get recent memories
                limit = min(max_memories or 100, self.config.batch_size)
                memories = await self.memory_repository.get_recent_memories(limit=limit)
                return memories
                
        except Exception as e:
            logger.error(f"Failed to retrieve memories for sync: {e}")
            return []
    
    async def _convert_memory_to_note(
        self,
        memory: AbstractMemoryEntry,
        template_type: Optional[TemplateType] = None
    ) -> Optional[MarkdownNote]:
        """Convert memory to markdown note."""
        try:
            return await self.markdown_converter.convert_memory_to_markdown(
                memory=memory,
                template_type=template_type,
                enable_backlinks=self.config.enable_backlinks,
                enable_tags=self.config.enable_tag_extraction
            )
        except Exception as e:
            logger.error(f"Memory conversion failed for {memory.id}: {e}")
            return None
    
    async def _apply_templates_to_notes(
        self,
        notes: List[MarkdownNote],
        template_type: TemplateType
    ) -> None:
        """Apply templates to notes."""
        if not self.template_processor:
            return
        
        for note in notes:
            try:
                await self.template_processor.apply_template(note, template_type)
            except Exception as e:
                logger.warning(f"Template application failed for {note.title_pattern}: {e}")
    
    async def _detect_vault_conflicts(self, notes: List[MarkdownNote]) -> List[ConflictInfo]:
        """Detect conflicts between notes and existing vault files."""
        conflicts = []
        
        for note in notes:
            try:
                vault_file = self.config.vault_path / note.get_filename()
                if vault_file.exists():
                    conflict = await self.conflict_resolver.detect_conflict(note, vault_file)
                    if conflict:
                        conflicts.append(conflict)
            except Exception as e:
                logger.warning(f"Conflict detection failed for {note.title_pattern}: {e}")
        
        return conflicts
    
    async def _resolve_conflicts(self, conflicts: List[ConflictInfo]) -> List[ConflictInfo]:
        """Resolve detected conflicts."""
        resolved = []
        
        for conflict in conflicts:
            try:
                resolution = await self.conflict_resolver.resolve_conflict(conflict)
                if resolution and resolution.resolved:
                    resolved.append(resolution)
            except Exception as e:
                logger.error(f"Conflict resolution failed for {conflict.conflict_id}: {e}")
        
        return resolved
    
    async def _write_note_to_vault(self, note: MarkdownNote) -> bool:
        """Write note to vault file."""
        try:
            # Validate note safety
            if not note.is_safe_for_export():
                logger.warning(f"Note {note.title_pattern} failed safety check")
                return False
            
            # Determine file path
            if not note.file_path:
                note.file_path = self.config.vault_path / note.get_filename()
            
            # Write markdown content
            markdown_content = note.get_full_markdown()
            note.file_path.write_text(markdown_content, encoding='utf-8')
            
            logger.debug(f"Written note to {note.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write note {note.title_pattern}: {e}")
            return False
    
    async def _generate_backlinks(self, notes: List[MarkdownNote]) -> None:
        """Generate backlinks between related notes."""
        # This is a simplified implementation
        # In a full implementation, this would use semantic similarity
        # and connection finding from the intent engine
        
        for i, note1 in enumerate(notes):
            for j, note2 in enumerate(notes):
                if i != j:
                    # Simple keyword-based relation detection
                    if await self._notes_are_related(note1, note2):
                        if note2.title_pattern not in note1.backlinks:
                            note1.backlinks.append(note2.title_pattern)
    
    async def _notes_are_related(self, note1: MarkdownNote, note2: MarkdownNote) -> bool:
        """Determine if two notes are related (simplified)."""
        # Simple implementation - check for common tags or keywords
        common_tags = note1.tags.intersection(note2.tags)
        return len(common_tags) > 0
    
    async def _parse_markdown_file(self, file_path: Path) -> Optional[MarkdownNote]:
        """Parse markdown file into note structure."""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Basic parsing - in full implementation would use proper markdown parser
            note = MarkdownNote(
                title_pattern=f"<imported_note_{file_path.stem}>",
                content=content,
                file_path=file_path,
                created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                updated_at=datetime.fromtimestamp(file_path.stat().st_mtime)
            )
            
            return note
            
        except Exception as e:
            logger.error(f"Failed to parse markdown file {file_path}: {e}")
            return None
    
    async def _find_memory_for_note(self, note: MarkdownNote) -> Optional[AbstractMemoryEntry]:
        """Find existing memory that corresponds to a note."""
        # Simplified implementation - would use proper matching in full version
        return None
    
    async def _create_memory_from_note(self, note: MarkdownNote) -> bool:
        """Create new memory from note."""
        # Simplified implementation
        return True
    
    async def _update_memory_from_note(
        self,
        memory: AbstractMemoryEntry,
        note: MarkdownNote
    ) -> bool:
        """Update existing memory from note."""
        # Simplified implementation
        return True
    
    def _update_sync_stats(self, result: SyncResult, performance: PerformanceMetrics) -> None:
        """Update synchronization statistics."""
        self._stats['syncs_performed'] += 1
        self._stats['total_notes_created'] += result.notes_created
        self._stats['total_notes_updated'] += result.notes_updated
        self._stats['total_conflicts_resolved'] += result.conflicts_resolved
        self._stats['total_processing_time_ms'] += result.processing_time_ms
        
        if result.conflicts_detected > 0:
            self._stats['conflict_resolution_success_rate'] = (
                result.conflicts_resolved / result.conflicts_detected
            )
        
        # Track performance
        if not hasattr(self, '_performance_history'):
            self._performance_history = []
        self._performance_history.append(performance)
        
        # Keep only recent performance data
        if len(self._performance_history) > 100:
            self._performance_history = self._performance_history[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vault sync statistics."""
        stats = self._stats.copy()
        
        # Add metadata
        stats['vault_metadata'] = self.metadata.__dict__
        
        # Add component stats
        stats['component_stats'] = {
            'markdown_converter': self.markdown_converter.get_stats(),
            'conflict_resolver': self.conflict_resolver.get_stats()
        }
        
        if self.template_processor:
            stats['component_stats']['template_processor'] = self.template_processor.get_stats()
        
        # Add performance averages
        if hasattr(self, '_performance_history') and self._performance_history:
            recent_perf = self._performance_history[-10:]  # Last 10 operations
            stats['recent_performance'] = {
                'avg_conversion_time_ms': sum(p.conversion_time_ms for p in recent_perf) / len(recent_perf),
                'avg_template_time_ms': sum(p.template_processing_time_ms for p in recent_perf) / len(recent_perf),
                'avg_conflict_time_ms': sum(p.conflict_detection_time_ms for p in recent_perf) / len(recent_perf),
                'avg_backlink_time_ms': sum(p.backlink_resolution_time_ms for p in recent_perf) / len(recent_perf),
                'targets_met_rate': sum(1 for p in recent_perf if p.meets_targets()) / len(recent_perf)
            }
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down vault sync engine...")
        
        if self.template_processor:
            await self.template_processor.shutdown()
        
        await self.conflict_resolver.shutdown()
        await self.markdown_converter.shutdown()
        
        logger.info("Vault sync engine shutdown completed")