#!/usr/bin/env python3
"""
Safe rollback script for CoachNTT.ai development operations.

Provides comprehensive rollback capabilities with safety validation, backup creation,
and integration with the script automation framework.

Usage:
    python3 rollback.py [options]

Options:
    --target COMMIT/BRANCH  Target commit or branch to rollback to
    --dry-run              Show what would be done without executing
    --force                Force rollback even with uncommitted changes
    --backup               Create backup before rollback (default: true)
    --validate             Run safety validation after rollback
    --help                 Show this help message

Example:
    python3 rollback.py --target HEAD~1 --validate
    python3 rollback.py --target backup-vault-sync-123456 --dry-run
"""

import asyncio
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

# Add framework path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import git
    from git import Repo, InvalidGitRepositoryError, GitCommandError
except ImportError:
    print("ERROR: GitPython is required. Install with: pip install gitpython")
    sys.exit(1)

from framework import ScriptRunner, ScriptConfig, ScriptResult, ScriptLogger, LogLevel


@dataclass
class RollbackTarget:
    """Represents a rollback target with validation."""
    
    target_ref: str  # Commit hash, branch name, or tag
    target_type: str  # 'commit', 'branch', or 'tag'
    commit_hash: str
    commit_message: str
    commit_date: datetime
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class RollbackPlan:
    """Plan for rollback operation with safety checks."""
    
    target: RollbackTarget
    current_commit: str
    current_branch: str
    
    # Changes that will be affected
    files_to_change: List[str] = field(default_factory=list)
    commits_to_lose: List[str] = field(default_factory=list)
    
    # Safety validations
    has_uncommitted_changes: bool = False
    affects_critical_files: bool = False
    potential_data_loss: bool = False
    
    # Backup information
    backup_branch_name: Optional[str] = None
    backup_created: bool = False
    
    # Risk assessment
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors: List[str] = field(default_factory=list)
    
    def is_safe_to_execute(self) -> bool:
        """Check if rollback plan is safe to execute."""
        if self.risk_level == "CRITICAL":
            return False
        
        if self.has_uncommitted_changes and not self.backup_created:
            return False
        
        if self.potential_data_loss and not self.backup_created:
            return False
        
        return True


class SafeRollbackManager:
    """
    Safe rollback manager with comprehensive validation and safety checks.
    
    Provides git rollback operations with mandatory safety validation,
    backup creation, and integration with the script automation framework.
    """
    
    def __init__(
        self,
        project_root: Optional[Path] = None,
        logger: Optional[ScriptLogger] = None,
        dry_run: bool = False
    ):
        """
        Initialize rollback manager.
        
        Args:
            project_root: Project root directory (auto-detected if None)
            logger: Logger instance (creates default if None)
            dry_run: Whether to run in dry-run mode
        """
        self.project_root = project_root or self._detect_project_root()
        self.dry_run = dry_run
        
        # Initialize logger
        self.logger = logger or ScriptLogger(
            script_name="rollback",
            log_level=LogLevel.INFO,
            abstract_content=True
        )
        
        # Initialize git repository
        try:
            self.repo = Repo(self.project_root)
        except InvalidGitRepositoryError:
            self.logger.error(f"Not a git repository: {self.project_root}")
            raise ValueError(f"Directory is not a git repository: {self.project_root}")
        
        # Critical files that require special attention
        self.critical_files = {
            "migrations/",
            "src/core/safety/",
            "src/core/validation/",
            "config/production/",
            "pyproject.toml",
            "requirements.txt"
        }
        
        self.logger.info(
            "SafeRollbackManager initialized",
            project_root=str(self.project_root),
            dry_run=self.dry_run,
            current_branch=self.repo.active_branch.name
        )
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current_dir = Path(__file__).parent
        
        # Look for indicators of project root
        for _ in range(5):  # Max 5 levels up
            if (current_dir / ".git").exists():
                return current_dir
            if (current_dir / "pyproject.toml").exists():
                return current_dir
            current_dir = current_dir.parent
        
        # Fallback to current directory
        return Path.cwd()
    
    async def analyze_rollback_target(self, target_ref: str) -> RollbackTarget:
        """
        Analyze and validate rollback target.
        
        Args:
            target_ref: Git reference (commit, branch, tag)
            
        Returns:
            RollbackTarget with validation results
        """
        self.logger.info(f"Analyzing rollback target: {target_ref}")
        
        target = RollbackTarget(
            target_ref=target_ref,
            target_type="unknown",
            commit_hash="",
            commit_message="",
            commit_date=datetime.now()
        )
        
        try:
            # Resolve reference to commit
            commit = self.repo.commit(target_ref)
            target.commit_hash = commit.hexsha
            target.commit_message = commit.message.strip()
            target.commit_date = datetime.fromtimestamp(commit.committed_date)
            
            # Determine target type
            try:
                # Check if it's a branch
                self.repo.heads[target_ref]
                target.target_type = "branch"
            except IndexError:
                try:
                    # Check if it's a tag
                    self.repo.tags[target_ref]
                    target.target_type = "tag"
                except IndexError:
                    # Must be a commit hash
                    target.target_type = "commit"
            
            # Validate target
            await self._validate_rollback_target(target)
            
            self.logger.info(
                f"Rollback target analyzed",
                target_type=target.target_type,
                commit_hash=target.commit_hash[:8],
                commit_date=target.commit_date.isoformat()
            )
            
            return target
            
        except Exception as e:
            target.is_valid = False
            target.validation_errors.append(f"Invalid git reference: {str(e)}")
            self.logger.error(f"Failed to analyze rollback target: {e}")
            return target
    
    async def _validate_rollback_target(self, target: RollbackTarget) -> None:
        """Validate rollback target for safety."""
        # Check if target is reachable from current branch
        try:
            current_commit = self.repo.head.commit
            
            # Check if target is an ancestor or the current commit
            if target.commit_hash == current_commit.hexsha:
                target.validation_errors.append("Target is the current commit")
                return
            
            # Check if target is in the history
            try:
                self.repo.git.merge_base(current_commit.hexsha, target.commit_hash)
            except GitCommandError:
                target.validation_errors.append("Target commit is not in the current branch history")
                return
            
            # Check age of target (warn if older than 30 days)
            age_days = (datetime.now() - target.commit_date).days
            if age_days > 30:
                target.validation_errors.append(f"Target commit is {age_days} days old")
            
        except Exception as e:
            target.validation_errors.append(f"Validation error: {str(e)}")
    
    async def create_rollback_plan(
        self,
        target: RollbackTarget,
        create_backup: bool = True
    ) -> RollbackPlan:
        """
        Create detailed rollback plan with safety analysis.
        
        Args:
            target: Validated rollback target
            create_backup: Whether to create backup before rollback
            
        Returns:
            Comprehensive rollback plan
        """
        self.logger.info("Creating rollback plan")
        
        current_commit = self.repo.head.commit
        current_branch = self.repo.active_branch.name
        
        plan = RollbackPlan(
            target=target,
            current_commit=current_commit.hexsha,
            current_branch=current_branch
        )
        
        # Check for uncommitted changes
        plan.has_uncommitted_changes = self.repo.is_dirty()
        if plan.has_uncommitted_changes:
            plan.risk_factors.append("Uncommitted changes present")
        
        # Analyze commits that will be lost
        try:
            commits_between = list(self.repo.iter_commits(
                f"{target.commit_hash}..{current_commit.hexsha}"
            ))
            plan.commits_to_lose = [c.hexsha[:8] for c in commits_between]
            
            if len(commits_between) > 10:
                plan.risk_factors.append(f"Many commits will be lost ({len(commits_between)})")
        
        except Exception as e:
            self.logger.warning(f"Could not analyze commit range: {e}")
        
        # Analyze files that will be changed
        try:
            diff = current_commit.diff(target.commit_hash)
            plan.files_to_change = [item.a_path or item.b_path for item in diff]
            
            # Check for critical files
            for file_path in plan.files_to_change:
                if any(critical in file_path for critical in self.critical_files):
                    plan.affects_critical_files = True
                    plan.risk_factors.append(f"Critical file affected: {file_path}")
        
        except Exception as e:
            self.logger.warning(f"Could not analyze file changes: {e}")
        
        # Assess data loss potential
        if len(plan.commits_to_lose) > 0:
            plan.potential_data_loss = True
            plan.risk_factors.append("Potential data loss from lost commits")
        
        # Create backup plan if requested
        if create_backup:
            timestamp = int(time.time())
            plan.backup_branch_name = f"backup-before-rollback-{timestamp}"
        
        # Calculate risk level
        plan.risk_level = self._calculate_risk_level(plan)
        
        self.logger.info(
            "Rollback plan created",
            commits_to_lose=len(plan.commits_to_lose),
            files_to_change=len(plan.files_to_change),
            risk_level=plan.risk_level,
            affects_critical_files=plan.affects_critical_files
        )
        
        return plan
    
    def _calculate_risk_level(self, plan: RollbackPlan) -> str:
        """Calculate risk level for rollback operation."""
        risk_score = 0
        
        # Risk factors
        if plan.has_uncommitted_changes:
            risk_score += 2
        
        if plan.affects_critical_files:
            risk_score += 3
        
        if len(plan.commits_to_lose) > 5:
            risk_score += 2
        elif len(plan.commits_to_lose) > 0:
            risk_score += 1
        
        if len(plan.files_to_change) > 20:
            risk_score += 2
        elif len(plan.files_to_change) > 5:
            risk_score += 1
        
        # Additional risk factors
        risk_score += len(plan.risk_factors)
        
        # Determine level
        if risk_score >= 8:
            return "CRITICAL"
        elif risk_score >= 5:
            return "HIGH"
        elif risk_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def execute_rollback_plan(
        self,
        plan: RollbackPlan,
        force: bool = False,
        run_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Execute rollback plan with safety checks.
        
        Args:
            plan: Rollback plan to execute
            force: Force execution even if unsafe
            run_validation: Run safety validation after rollback
            
        Returns:
            Execution result dictionary
        """
        self.logger.info("Executing rollback plan")
        
        result = {
            "success": False,
            "backup_created": False,
            "rollback_completed": False,
            "validation_passed": True,
            "errors": [],
            "warnings": []
        }
        
        # Safety check
        if not plan.is_safe_to_execute() and not force:
            error_msg = f"Rollback plan is not safe to execute (risk level: {plan.risk_level})"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            return result
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would execute rollback plan")
            return self._simulate_rollback_execution(plan)
        
        try:
            # Phase 1: Create backup if requested
            if plan.backup_branch_name:
                backup_success = await self._create_backup_branch(plan.backup_branch_name)
                result["backup_created"] = backup_success
                plan.backup_created = backup_success
                
                if not backup_success and not force:
                    result["errors"].append("Failed to create backup and force not specified")
                    return result
            
            # Phase 2: Stash uncommitted changes if present
            stash_ref = None
            if plan.has_uncommitted_changes:
                stash_ref = await self._stash_uncommitted_changes()
                if stash_ref:
                    self.logger.info("Uncommitted changes stashed")
                else:
                    result["warnings"].append("Could not stash uncommitted changes")
            
            # Phase 3: Perform rollback
            rollback_success = await self._perform_git_rollback(plan.target)
            result["rollback_completed"] = rollback_success
            
            if not rollback_success:
                result["errors"].append("Git rollback failed")
                # Attempt to restore stashed changes
                if stash_ref:
                    await self._restore_stashed_changes(stash_ref)
                return result
            
            # Phase 4: Run safety validation if requested
            if run_validation:
                validation_result = await self._run_post_rollback_validation()
                result["validation_passed"] = validation_result["passed"]
                if not validation_result["passed"]:
                    result["warnings"].extend(validation_result["issues"])
            
            result["success"] = True
            self.logger.info("Rollback completed successfully")
            
        except Exception as e:
            error_msg = f"Rollback execution failed: {str(e)}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result
    
    def _simulate_rollback_execution(self, plan: RollbackPlan) -> Dict[str, Any]:
        """Simulate rollback execution for dry-run mode."""
        self.logger.info("=== DRY RUN SIMULATION ===")
        
        result = {
            "success": True,
            "backup_created": bool(plan.backup_branch_name),
            "rollback_completed": True,
            "validation_passed": True,
            "errors": [],
            "warnings": [],
            "simulation": True
        }
        
        # Log what would happen
        if plan.backup_branch_name:
            self.logger.info(f"Would create backup branch: {plan.backup_branch_name}")
        
        if plan.has_uncommitted_changes:
            self.logger.info("Would stash uncommitted changes")
        
        self.logger.info(f"Would rollback to: {plan.target.commit_hash[:8]}")
        self.logger.info(f"Would affect {len(plan.files_to_change)} files")
        self.logger.info(f"Would lose {len(plan.commits_to_lose)} commits")
        
        if plan.affects_critical_files:
            self.logger.warning("Would modify critical files")
        
        self.logger.info("=== END SIMULATION ===")
        
        return result
    
    async def _create_backup_branch(self, branch_name: str) -> bool:
        """Create backup branch from current state."""
        try:
            backup_branch = self.repo.create_head(branch_name)
            self.logger.info(f"Created backup branch: {branch_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create backup branch: {e}")
            return False
    
    async def _stash_uncommitted_changes(self) -> Optional[str]:
        """Stash uncommitted changes."""
        try:
            stash_message = f"Pre-rollback stash {int(time.time())}"
            stash_ref = self.repo.git.stash("push", "-m", stash_message)
            return stash_ref
        except Exception as e:
            self.logger.error(f"Failed to stash changes: {e}")
            return None
    
    async def _restore_stashed_changes(self, stash_ref: str) -> bool:
        """Restore stashed changes."""
        try:
            self.repo.git.stash("pop")
            self.logger.info("Restored stashed changes")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore stashed changes: {e}")
            return False
    
    async def _perform_git_rollback(self, target: RollbackTarget) -> bool:
        """Perform the actual git rollback."""
        try:
            # Reset to target commit
            self.repo.git.reset("--hard", target.commit_hash)
            self.logger.info(f"Reset to commit: {target.commit_hash[:8]}")
            return True
        except Exception as e:
            self.logger.error(f"Git rollback failed: {e}")
            return False
    
    async def _run_post_rollback_validation(self) -> Dict[str, Any]:
        """Run safety validation after rollback."""
        self.logger.info("Running post-rollback validation")
        
        validation_result = {
            "passed": True,
            "issues": []
        }
        
        try:
            # Check repository state
            if self.repo.is_dirty():
                validation_result["issues"].append("Repository is dirty after rollback")
            
            # Check critical files exist
            for critical_path in self.critical_files:
                full_path = self.project_root / critical_path
                if not full_path.exists():
                    validation_result["issues"].append(f"Critical path missing: {critical_path}")
            
            # Check if Python can import core modules
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-c", "import src.core; print('Core modules OK')"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    validation_result["issues"].append("Core modules failed to import")
            except Exception as e:
                validation_result["issues"].append(f"Module validation error: {str(e)}")
            
            validation_result["passed"] = len(validation_result["issues"]) == 0
            
        except Exception as e:
            validation_result["passed"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def get_available_targets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of available rollback targets."""
        targets = []
        
        # Recent commits
        for commit in self.repo.iter_commits(max_count=limit):
            targets.append({
                "type": "commit",
                "ref": commit.hexsha[:8],
                "full_ref": commit.hexsha,
                "message": commit.message.strip()[:60],
                "date": datetime.fromtimestamp(commit.committed_date),
                "author": "<author>"  # Abstracted for safety
            })
        
        # Branches
        for branch in self.repo.heads:
            if branch.name != self.repo.active_branch.name:
                targets.append({
                    "type": "branch",
                    "ref": branch.name,
                    "full_ref": branch.name,
                    "message": f"Branch: {branch.name}",
                    "date": datetime.fromtimestamp(branch.commit.committed_date),
                    "author": "<author>"
                })
        
        # Tags
        for tag in self.repo.tags:
            targets.append({
                "type": "tag",
                "ref": tag.name,
                "full_ref": tag.name,
                "message": f"Tag: {tag.name}",
                "date": datetime.fromtimestamp(tag.commit.committed_date),
                "author": "<author>"
            })
        
        # Sort by date (newest first)
        targets.sort(key=lambda x: x["date"], reverse=True)
        
        return targets


async def main():
    """Main rollback script function."""
    parser = argparse.ArgumentParser(
        description="Safe rollback script for CoachNTT.ai development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 rollback.py --target HEAD~1 --validate
    python3 rollback.py --target backup-vault-sync-123456 --dry-run
    python3 rollback.py --list-targets
        """
    )
    
    parser.add_argument(
        "--target",
        help="Target commit, branch, or tag to rollback to"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rollback even with high risk"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup branch"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run safety validation after rollback"
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="List available rollback targets"
    )
    
    args = parser.parse_args()
    
    # Initialize rollback manager
    try:
        manager = SafeRollbackManager(dry_run=args.dry_run)
    except Exception as e:
        print(f"ERROR: Failed to initialize rollback manager: {e}")
        return 1
    
    try:
        # List targets mode
        if args.list_targets:
            targets = manager.get_available_targets()
            print("\nAvailable rollback targets:")
            print("=" * 80)
            for target in targets:
                print(f"{target['type']:8} {target['ref']:15} {target['date'].strftime('%Y-%m-%d %H:%M')} {target['message']}")
            return 0
        
        # Validate arguments
        if not args.target:
            parser.error("Target is required (use --list-targets to see options)")
        
        # Phase 1: Analyze target
        target = await manager.analyze_rollback_target(args.target)
        if not target.is_valid:
            print(f"ERROR: Invalid rollback target: {', '.join(target.validation_errors)}")
            return 1
        
        # Phase 2: Create rollback plan
        plan = await manager.create_rollback_plan(
            target,
            create_backup=not args.no_backup
        )
        
        # Phase 3: Display plan and confirm
        print(f"\nRollback Plan Summary:")
        print(f"Target: {target.target_ref} ({target.commit_hash[:8]})")
        print(f"Risk Level: {plan.risk_level}")
        print(f"Commits to lose: {len(plan.commits_to_lose)}")
        print(f"Files to change: {len(plan.files_to_change)}")
        print(f"Critical files affected: {plan.affects_critical_files}")
        
        if plan.risk_factors:
            print(f"Risk factors: {', '.join(plan.risk_factors)}")
        
        if not args.dry_run and not args.force:
            if plan.risk_level in ["HIGH", "CRITICAL"]:
                print(f"\nWARNING: High risk rollback! Use --force to proceed.")
                return 1
            
            confirm = input("\nProceed with rollback? (yes/no): ")
            if confirm.lower() != "yes":
                print("Rollback cancelled.")
                return 0
        
        # Phase 4: Execute rollback
        result = await manager.execute_rollback_plan(
            plan,
            force=args.force,
            run_validation=args.validate
        )
        
        # Phase 5: Report results
        if result["success"]:
            print("\nRollback completed successfully!")
            if args.dry_run:
                print("(This was a dry run - no changes were made)")
        else:
            print("\nRollback failed!")
            for error in result["errors"]:
                print(f"ERROR: {error}")
        
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        
        return 0 if result["success"] else 1
        
    except KeyboardInterrupt:
        print("\nRollback cancelled by user.")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)