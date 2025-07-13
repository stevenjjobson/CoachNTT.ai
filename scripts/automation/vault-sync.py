#!/usr/bin/env python3
"""
Automated vault synchronization script for CoachNTT.ai.

Provides automated memory-to-markdown conversion and vault synchronization
with safety validation, conflict resolution, and integration with the
existing VaultSyncEngine.

Usage:
    python3 vault-sync.py [options]

Options:
    --mode MODE             Sync mode: auto, manual, scheduled
    --template TYPE         Template type: checkpoint, learning, decision
    --max-memories N        Maximum memories to sync (default: 50)
    --vault-path PATH       Vault directory path
    --dry-run              Show what would be done without executing
    --force                Force sync even with conflicts
    --validate             Run safety validation after sync
    --help                 Show this help message

Example:
    python3 vault-sync.py --mode auto --template checkpoint --max-memories 25
    python3 vault-sync.py --mode manual --vault-path /path/to/vault --validate
"""

import asyncio
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

# Add framework and src paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from framework import ScriptRunner, ScriptConfig, ScriptResult, ScriptLogger, LogLevel

# Import vault sync components (these would be the actual imports in real implementation)
try:
    from services.vault import (
        VaultSyncEngine, VaultSyncConfig, TemplateType, ConflictStrategy,
        SyncDirection, SyncResult
    )
    from core.memory.repository import SafeMemoryRepository
    from core.validation.validator import SafetyValidator
    from core.analysis.ast_analyzer import ASTAnalyzer
    from core.intent.engine import IntentEngine
except ImportError as e:
    print(f"ERROR: Could not import vault sync components: {e}")
    print("This script requires the full CoachNTT.ai system to be set up")
    sys.exit(1)


@dataclass
class VaultSyncSession:
    """Vault synchronization session tracking."""
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Configuration
    mode: str = "auto"
    template_type: Optional[TemplateType] = None
    max_memories: int = 50
    vault_path: Optional[Path] = None
    
    # Results
    sync_results: List[SyncResult] = field(default_factory=list)
    total_notes_created: int = 0
    total_notes_updated: int = 0
    total_conflicts_resolved: int = 0
    total_safety_violations: int = 0
    
    # Performance
    total_processing_time_ms: int = 0
    average_safety_score: float = 1.0
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Whether session completed successfully."""
        return len(self.errors) == 0 and len(self.sync_results) > 0
    
    @property
    def duration_seconds(self) -> float:
        """Session duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return {
            'session_id': self.session_id,
            'mode': self.mode,
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'notes_created': self.total_notes_created,
            'notes_updated': self.total_notes_updated,
            'conflicts_resolved': self.total_conflicts_resolved,
            'safety_violations': self.total_safety_violations,
            'average_safety_score': self.average_safety_score,
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings)
        }


class AutomatedVaultSync:
    """
    Automated vault synchronization manager.
    
    Provides comprehensive automation for memory-to-markdown conversion
    and vault synchronization with safety validation and conflict resolution.
    """
    
    def __init__(
        self,
        project_root: Optional[Path] = None,
        logger: Optional[ScriptLogger] = None,
        dry_run: bool = False
    ):
        """
        Initialize automated vault sync.
        
        Args:
            project_root: Project root directory
            logger: Logger instance
            dry_run: Whether to run in dry-run mode
        """
        self.project_root = project_root or self._detect_project_root()
        self.dry_run = dry_run
        
        # Initialize logger
        self.logger = logger or ScriptLogger(
            script_name="vault-sync",
            log_level=LogLevel.INFO,
            abstract_content=True
        )
        
        # Default vault path
        self.default_vault_path = self.project_root / "vault"
        
        # Core components (would be initialized with actual services)
        self.memory_repository: Optional[SafeMemoryRepository] = None
        self.safety_validator: Optional[SafetyValidator] = None
        self.ast_analyzer: Optional[ASTAnalyzer] = None
        self.intent_engine: Optional[IntentEngine] = None
        self.vault_sync_engine: Optional[VaultSyncEngine] = None
        
        # Session tracking
        self.current_session: Optional[VaultSyncSession] = None
        self.session_history: List[VaultSyncSession] = []
        
        self.logger.info(
            "AutomatedVaultSync initialized",
            project_root=str(self.project_root),
            dry_run=self.dry_run,
            vault_path=str(self.default_vault_path)
        )
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current_dir = Path(__file__).parent
        
        for _ in range(5):
            if (current_dir / ".git").exists() or (current_dir / "pyproject.toml").exists():
                return current_dir
            current_dir = current_dir.parent
        
        return Path.cwd()
    
    async def initialize_services(self) -> bool:
        """Initialize vault sync services."""
        try:
            # In a real implementation, these would be properly initialized
            # with database connections, configuration, etc.
            
            self.logger.info("Initializing vault sync services...")
            
            # Initialize safety validator
            self.safety_validator = SafetyValidator()
            
            # Initialize AST analyzer
            self.ast_analyzer = ASTAnalyzer()
            
            # Initialize intent engine (placeholder)
            # self.intent_engine = IntentEngine(...)
            
            # Initialize memory repository (placeholder)
            # self.memory_repository = SafeMemoryRepository(db_pool, ...)
            
            self.logger.info("Vault sync services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            return False
    
    async def create_vault_sync_engine(
        self,
        vault_path: Path,
        template_type: Optional[TemplateType] = None
    ) -> VaultSyncEngine:
        """Create configured vault sync engine."""
        
        # Create vault sync configuration
        config = VaultSyncConfig(
            vault_path=vault_path,
            enable_backlinks=True,
            enable_templates=True,
            enable_tag_extraction=True,
            conflict_strategy=ConflictStrategy.SAFE_MERGE,
            batch_size=50,
            safety_score_threshold=Decimal("0.8")
        )
        
        # Create vault sync engine
        engine = VaultSyncEngine(
            config=config,
            memory_repository=self.memory_repository,
            safety_validator=self.safety_validator,
            ast_analyzer=self.ast_analyzer,
            intent_engine=self.intent_engine
        )
        
        return engine
    
    async def run_automated_sync(
        self,
        mode: str = "auto",
        template_type: Optional[TemplateType] = None,
        max_memories: int = 50,
        vault_path: Optional[Path] = None,
        force: bool = False,
        validate: bool = True
    ) -> VaultSyncSession:
        """
        Run automated vault synchronization.
        
        Args:
            mode: Sync mode (auto, manual, scheduled)
            template_type: Template type to use
            max_memories: Maximum memories to sync
            vault_path: Vault directory path
            force: Force sync even with conflicts
            validate: Run validation after sync
            
        Returns:
            Vault sync session with results
        """
        session_id = f"vault_sync_{int(time.time())}"
        session = VaultSyncSession(
            session_id=session_id,
            start_time=datetime.now(),
            mode=mode,
            template_type=template_type,
            max_memories=max_memories,
            vault_path=vault_path or self.default_vault_path
        )
        
        self.current_session = session
        self.logger.info(f"Starting vault sync session: {session_id}")
        
        try:
            # Phase 1: Initialize services
            if not await self.initialize_services():
                session.errors.append("Failed to initialize services")
                return session
            
            # Phase 2: Validate vault path
            vault_path = session.vault_path
            if not await self._validate_vault_path(vault_path):
                session.errors.append(f"Invalid vault path: {vault_path}")
                return session
            
            # Phase 3: Create vault sync engine
            if self.dry_run:
                self.logger.info("DRY RUN: Would create vault sync engine")
                sync_engine = None
            else:
                sync_engine = await self.create_vault_sync_engine(vault_path, template_type)
                self.vault_sync_engine = sync_engine
            
            # Phase 4: Execute sync based on mode
            if mode == "auto":
                await self._run_auto_sync(session, sync_engine, template_type, max_memories)
            elif mode == "manual":
                await self._run_manual_sync(session, sync_engine, template_type, max_memories)
            elif mode == "scheduled":
                await self._run_scheduled_sync(session, sync_engine, template_type, max_memories)
            else:
                session.errors.append(f"Unknown sync mode: {mode}")
                return session
            
            # Phase 5: Post-sync validation
            if validate and not self.dry_run:
                await self._run_post_sync_validation(session, vault_path)
            
            # Phase 6: Generate sync report
            await self._generate_sync_report(session)
            
        except Exception as e:
            error_msg = f"Vault sync session failed: {str(e)}"
            self.logger.error(error_msg)
            session.errors.append(error_msg)
        
        finally:
            session.end_time = datetime.now()
            self.session_history.append(session)
            self._log_session_completion(session)
        
        return session
    
    async def _validate_vault_path(self, vault_path: Path) -> bool:
        """Validate vault directory path."""
        try:
            if not vault_path.exists():
                vault_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created vault directory: {vault_path}")
            
            if not vault_path.is_dir():
                self.logger.error(f"Vault path is not a directory: {vault_path}")
                return False
            
            # Check write permissions
            test_file = vault_path / ".vault_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                self.logger.error(f"No write permission to vault: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Vault path validation failed: {e}")
            return False
    
    async def _run_auto_sync(
        self,
        session: VaultSyncSession,
        sync_engine: Optional[VaultSyncEngine],
        template_type: Optional[TemplateType],
        max_memories: int
    ):
        """Run automatic synchronization."""
        self.logger.info("Running automatic vault sync")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would sync memories to vault automatically")
            self._simulate_sync_result(session, max_memories)
            return
        
        try:
            # Sync memories to vault
            result = await sync_engine.sync_memories_to_vault(
                memory_ids=None,  # Auto-select memories
                template_type=template_type,
                max_memories=max_memories
            )
            
            session.sync_results.append(result)
            self._update_session_from_result(session, result)
            
            self.logger.info(
                "Auto sync completed",
                notes_created=result.notes_created,
                notes_updated=result.notes_updated,
                conflicts=result.conflicts_detected
            )
            
        except Exception as e:
            error_msg = f"Auto sync failed: {str(e)}"
            self.logger.error(error_msg)
            session.errors.append(error_msg)
    
    async def _run_manual_sync(
        self,
        session: VaultSyncSession,
        sync_engine: Optional[VaultSyncEngine],
        template_type: Optional[TemplateType],
        max_memories: int
    ):
        """Run manual synchronization with user interaction."""
        self.logger.info("Running manual vault sync")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would run manual sync with user interaction")
            self._simulate_sync_result(session, max_memories)
            return
        
        try:
            # In manual mode, we could add interactive features like:
            # - Memory selection
            # - Template customization
            # - Conflict resolution choices
            
            # For now, run similar to auto but with more logging
            result = await sync_engine.sync_memories_to_vault(
                template_type=template_type,
                max_memories=max_memories
            )
            
            session.sync_results.append(result)
            self._update_session_from_result(session, result)
            
            self.logger.info("Manual sync completed")
            
        except Exception as e:
            error_msg = f"Manual sync failed: {str(e)}"
            self.logger.error(error_msg)
            session.errors.append(error_msg)
    
    async def _run_scheduled_sync(
        self,
        session: VaultSyncSession,
        sync_engine: Optional[VaultSyncEngine],
        template_type: Optional[TemplateType],
        max_memories: int
    ):
        """Run scheduled synchronization."""
        self.logger.info("Running scheduled vault sync")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would run scheduled sync")
            self._simulate_sync_result(session, max_memories)
            return
        
        try:
            # For scheduled sync, we might want to:
            # - Use checkpoint template by default
            # - Sync only recent memories
            # - Handle conflicts conservatively
            
            default_template = template_type or TemplateType.CHECKPOINT
            
            result = await sync_engine.sync_memories_to_vault(
                template_type=default_template,
                max_memories=max_memories
            )
            
            session.sync_results.append(result)
            self._update_session_from_result(session, result)
            
            self.logger.info("Scheduled sync completed")
            
        except Exception as e:
            error_msg = f"Scheduled sync failed: {str(e)}"
            self.logger.error(error_msg)
            session.errors.append(error_msg)
    
    def _simulate_sync_result(self, session: VaultSyncSession, max_memories: int):
        """Simulate sync result for dry-run mode."""
        # Create simulated result
        simulated_result = type('SyncResult', (), {
            'success': True,
            'notes_created': min(max_memories, 15),
            'notes_updated': min(max_memories // 3, 5),
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'safety_violations': 0,
            'processing_time_ms': 2500,
            'average_safety_score': 0.95,
            'errors': [],
            'warnings': []
        })()
        
        session.sync_results.append(simulated_result)
        self._update_session_from_result(session, simulated_result)
    
    def _update_session_from_result(self, session: VaultSyncSession, result):
        """Update session statistics from sync result."""
        session.total_notes_created += result.notes_created
        session.total_notes_updated += result.notes_updated
        session.total_conflicts_resolved += getattr(result, 'conflicts_resolved', 0)
        session.total_safety_violations += getattr(result, 'safety_violations', 0)
        session.total_processing_time_ms += getattr(result, 'processing_time_ms', 0)
        
        # Update average safety score
        if hasattr(result, 'average_safety_score') and result.average_safety_score:
            if session.average_safety_score == 1.0:  # First result
                session.average_safety_score = result.average_safety_score
            else:
                # Simple average (could be weighted)
                session.average_safety_score = (session.average_safety_score + result.average_safety_score) / 2
        
        # Collect errors and warnings
        if hasattr(result, 'errors'):
            session.errors.extend(result.errors)
        if hasattr(result, 'warnings'):
            session.warnings.extend(result.warnings)
    
    async def _run_post_sync_validation(self, session: VaultSyncSession, vault_path: Path):
        """Run post-sync validation."""
        self.logger.info("Running post-sync validation")
        
        try:
            validation_results = {
                'files_created': 0,
                'files_validated': 0,
                'safety_violations': 0,
                'markdown_errors': 0
            }
            
            # Validate created markdown files
            for md_file in vault_path.glob("*.md"):
                validation_results['files_created'] += 1
                
                try:
                    content = md_file.read_text(encoding='utf-8')
                    
                    # Basic markdown validation
                    if not content.strip():
                        session.warnings.append(f"Empty markdown file: {md_file.name}")
                        continue
                    
                    # Safety validation
                    if self.safety_validator:
                        abstracted_content, mappings = self.safety_validator.auto_abstract_content(content)
                        if len(mappings) > 0:
                            validation_results['safety_violations'] += len(mappings)
                            session.warnings.append(f"Safety violations in {md_file.name}: {len(mappings)}")
                    
                    validation_results['files_validated'] += 1
                    
                except Exception as e:
                    validation_results['markdown_errors'] += 1
                    session.warnings.append(f"Validation error in {md_file.name}: {str(e)}")
            
            self.logger.info(
                "Post-sync validation completed",
                **validation_results
            )
            
        except Exception as e:
            error_msg = f"Post-sync validation failed: {str(e)}"
            self.logger.error(error_msg)
            session.errors.append(error_msg)
    
    async def _generate_sync_report(self, session: VaultSyncSession):
        """Generate comprehensive sync report."""
        self.logger.info("Generating sync report")
        
        report_path = self.project_root / "logs" / "vault_sync" / f"{session.session_id}_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            report_content = f"""# Vault Sync Report

**Session ID**: {session.session_id}
**Mode**: {session.mode}
**Started**: {session.start_time.isoformat()}
**Completed**: {session.end_time.isoformat() if session.end_time else 'In Progress'}
**Duration**: {session.duration_seconds:.1f} seconds

## Summary

- **Success**: {'✅' if session.success else '❌'}
- **Notes Created**: {session.total_notes_created}
- **Notes Updated**: {session.total_notes_updated}
- **Conflicts Resolved**: {session.total_conflicts_resolved}
- **Safety Violations**: {session.total_safety_violations}
- **Average Safety Score**: {session.average_safety_score:.3f}
- **Processing Time**: {session.total_processing_time_ms}ms

## Results

"""
            
            for i, result in enumerate(session.sync_results, 1):
                report_content += f"""### Sync Operation {i}

- **Notes Created**: {result.notes_created}
- **Notes Updated**: {result.notes_updated}
- **Conflicts Detected**: {getattr(result, 'conflicts_detected', 0)}
- **Processing Time**: {getattr(result, 'processing_time_ms', 0)}ms

"""
            
            if session.errors:
                report_content += "## Errors\n\n"
                for error in session.errors:
                    report_content += f"- {error}\n"
                report_content += "\n"
            
            if session.warnings:
                report_content += "## Warnings\n\n"
                for warning in session.warnings:
                    report_content += f"- {warning}\n"
                report_content += "\n"
            
            report_content += f"""## Configuration

- **Template Type**: {session.template_type.value if session.template_type else 'None'}
- **Max Memories**: {session.max_memories}
- **Vault Path**: {session.vault_path}
- **Dry Run**: {self.dry_run}

---
*Report generated by CoachNTT.ai Script Automation Framework*
"""
            
            if not self.dry_run:
                report_path.write_text(report_content, encoding='utf-8')
                self.logger.info(f"Sync report saved: {report_path}")
            else:
                self.logger.info("DRY RUN: Would save sync report")
            
        except Exception as e:
            self.logger.error(f"Failed to generate sync report: {e}")
    
    def _log_session_completion(self, session: VaultSyncSession):
        """Log session completion with summary."""
        if session.success:
            self.logger.info(
                f"Vault sync session {session.session_id} completed successfully",
                **session.get_summary()
            )
        else:
            self.logger.error(
                f"Vault sync session {session.session_id} failed",
                **session.get_summary()
            )
    
    def get_session_history(self, limit: Optional[int] = None) -> List[VaultSyncSession]:
        """Get vault sync session history."""
        history = sorted(self.session_history, key=lambda s: s.start_time, reverse=True)
        return history[:limit] if limit else history
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get comprehensive sync statistics."""
        if not self.session_history:
            return {"message": "No sync sessions recorded"}
        
        total_sessions = len(self.session_history)
        successful_sessions = len([s for s in self.session_history if s.success])
        total_notes_created = sum(s.total_notes_created for s in self.session_history)
        total_notes_updated = sum(s.total_notes_updated for s in self.session_history)
        total_conflicts = sum(s.total_conflicts_resolved for s in self.session_history)
        
        avg_safety_score = sum(s.average_safety_score for s in self.session_history) / total_sessions
        avg_duration = sum(s.duration_seconds for s in self.session_history) / total_sessions
        
        return {
            'total_sessions': total_sessions,
            'successful_sessions': successful_sessions,
            'success_rate': successful_sessions / total_sessions,
            'total_notes_created': total_notes_created,
            'total_notes_updated': total_notes_updated,
            'total_conflicts_resolved': total_conflicts,
            'average_safety_score': avg_safety_score,
            'average_duration_seconds': avg_duration,
            'last_sync': self.session_history[-1].start_time.isoformat()
        }


async def main():
    """Main vault sync automation function."""
    parser = argparse.ArgumentParser(
        description="Automated vault synchronization for CoachNTT.ai",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--mode",
        choices=["auto", "manual", "scheduled"],
        default="auto",
        help="Synchronization mode"
    )
    parser.add_argument(
        "--template",
        choices=["checkpoint", "learning", "decision"],
        help="Template type for markdown conversion"
    )
    parser.add_argument(
        "--max-memories",
        type=int,
        default=50,
        help="Maximum memories to sync"
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        help="Vault directory path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync even with conflicts"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation after sync"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show sync statistics and exit"
    )
    
    args = parser.parse_args()
    
    # Parse template type
    template_type = None
    if args.template:
        template_map = {
            "checkpoint": TemplateType.CHECKPOINT,
            "learning": TemplateType.LEARNING,
            "decision": TemplateType.DECISION
        }
        template_type = template_map.get(args.template)
    
    # Initialize vault sync manager
    vault_sync = AutomatedVaultSync(dry_run=args.dry_run)
    
    try:
        if args.stats:
            # Show statistics
            stats = vault_sync.get_sync_statistics()
            print("Vault Sync Statistics:")
            print("=" * 50)
            for key, value in stats.items():
                print(f"{key}: {value}")
            return 0
        
        # Run vault synchronization
        session = await vault_sync.run_automated_sync(
            mode=args.mode,
            template_type=template_type,
            max_memories=args.max_memories,
            vault_path=args.vault_path,
            force=args.force,
            validate=args.validate
        )
        
        # Print results
        print(f"\nVault Sync Session Results:")
        print(f"Session ID: {session.session_id}")
        print(f"Success: {'✅' if session.success else '❌'}")
        print(f"Duration: {session.duration_seconds:.1f} seconds")
        print(f"Notes Created: {session.total_notes_created}")
        print(f"Notes Updated: {session.total_notes_updated}")
        print(f"Safety Score: {session.average_safety_score:.3f}")
        
        if args.dry_run:
            print("\n(This was a dry run - no changes were made)")
        
        if session.errors:
            print(f"\nErrors ({len(session.errors)}):")
            for error in session.errors:
                print(f"  - {error}")
        
        if session.warnings:
            print(f"\nWarnings ({len(session.warnings)}):")
            for warning in session.warnings:
                print(f"  - {warning}")
        
        return 0 if session.success else 1
        
    except KeyboardInterrupt:
        print("\nVault sync cancelled by user.")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)