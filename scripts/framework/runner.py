"""
Main script execution framework for CoachNTT.ai automation.

Provides centralized script execution with dependency validation, safety checks,
performance monitoring, and integration with existing core systems.
"""

import asyncio
import subprocess
import time
import psutil
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .config import ScriptFrameworkConfig, load_script_config
from .logger import ScriptLogger, LogLevel


class ScriptType(Enum):
    """Types of scripts supported by the framework."""
    PYTHON = "python"
    SHELL = "shell"
    BASH = "bash"


class ScriptStatus(Enum):
    """Script execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ScriptConfig:
    """Configuration for a single script execution."""
    
    script_path: Path
    script_type: ScriptType
    name: str
    description: str = ""
    
    # Execution settings
    timeout_seconds: int = 300
    max_memory_mb: int = 512
    working_directory: Optional[Path] = None
    environment_vars: Dict[str, str] = field(default_factory=dict)
    
    # Safety settings
    enable_safety_validation: bool = True
    require_git_clean: bool = False
    create_backup: bool = True
    
    # Dependencies
    required_commands: List[str] = field(default_factory=list)
    required_files: List[Path] = field(default_factory=list)
    
    # Arguments
    arguments: List[str] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """Validate script configuration."""
        errors = []
        
        if not self.script_path.exists():
            errors.append(f"Script file not found: {self.script_path}")
        
        if not self.script_path.is_file():
            errors.append(f"Script path is not a file: {self.script_path}")
        
        if self.working_directory and not self.working_directory.exists():
            errors.append(f"Working directory not found: {self.working_directory}")
        
        # Check required commands
        for cmd in self.required_commands:
            if not shutil.which(cmd):
                errors.append(f"Required command not found: {cmd}")
        
        # Check required files
        for file_path in self.required_files:
            if not file_path.exists():
                errors.append(f"Required file not found: {file_path}")
        
        return errors


@dataclass
class ScriptResult:
    """Result of script execution."""
    
    script_name: str
    status: ScriptStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Execution details
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    
    # Performance metrics
    execution_time_seconds: float = 0.0
    max_memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Safety metrics
    safety_score: float = 1.0
    safety_violations: List[str] = field(default_factory=list)
    concrete_references_detected: int = 0
    
    # Error information
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Whether script executed successfully."""
        return self.status == ScriptStatus.COMPLETED and self.exit_code == 0
    
    @property
    def duration_ms(self) -> int:
        """Execution duration in milliseconds."""
        return int(self.execution_time_seconds * 1000)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary dictionary."""
        return {
            'script_name': self.script_name,
            'status': self.status.value,
            'success': self.success,
            'execution_time_seconds': self.execution_time_seconds,
            'exit_code': self.exit_code,
            'max_memory_usage_mb': self.max_memory_usage_mb,
            'safety_score': self.safety_score,
            'safety_violations_count': len(self.safety_violations),
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings)
        }


class ScriptRunner:
    """
    Main script execution framework with safety validation and monitoring.
    
    Provides centralized execution of automation scripts with dependency validation,
    performance monitoring, safety checks, and integration with existing systems.
    """
    
    def __init__(
        self,
        config: Optional[ScriptFrameworkConfig] = None,
        logger: Optional[ScriptLogger] = None
    ):
        """
        Initialize script runner.
        
        Args:
            config: Framework configuration (loads default if None)
            logger: Logger instance (creates default if None)
        """
        self.config = config or load_script_config()
        self.logger = logger or ScriptLogger(
            script_name="framework",
            log_level=LogLevel(self.config.log_level),
            log_directory=self.config.logs_directory,
            abstract_content=self.config.abstract_all_output
        )
        
        # Execution tracking
        self._running_scripts: Dict[str, subprocess.Popen] = {}
        self._execution_history: List[ScriptResult] = []
        
        # Safety validator (placeholder - would import from core in real implementation)
        self._safety_validator = None
        
        self.logger.info("ScriptRunner initialized", 
                        environment=self.config.environment,
                        safety_validation=self.config.enable_safety_validation)
    
    async def execute_script(
        self,
        script_config: ScriptConfig,
        capture_output: bool = True,
        monitor_performance: bool = True
    ) -> ScriptResult:
        """
        Execute a single script with monitoring and validation.
        
        Args:
            script_config: Script configuration
            capture_output: Whether to capture stdout/stderr
            monitor_performance: Whether to monitor performance metrics
            
        Returns:
            Script execution result
        """
        self.logger.info(f"Starting script execution: {script_config.name}")
        
        # Create result object
        result = ScriptResult(
            script_name=script_config.name,
            status=ScriptStatus.PENDING,
            start_time=datetime.now()
        )
        
        try:
            # Phase 1: Pre-execution validation
            validation_errors = await self._validate_script_execution(script_config)
            if validation_errors:
                result.status = ScriptStatus.FAILED
                result.errors.extend(validation_errors)
                self.logger.error(f"Script validation failed: {validation_errors}")
                return result
            
            # Phase 2: Create backup if requested
            if script_config.create_backup and self.config.git_backup_before_operations:
                backup_success = await self._create_git_backup(script_config.name)
                if not backup_success:
                    result.warnings.append("Failed to create git backup")
            
            # Phase 3: Execute script
            result.status = ScriptStatus.RUNNING
            start_time = time.time()
            
            process = await self._start_script_process(script_config, capture_output)
            self._running_scripts[script_config.name] = process
            
            # Phase 4: Monitor execution
            if monitor_performance:
                await self._monitor_script_execution(process, result, script_config)
            else:
                # Simple wait without monitoring
                try:
                    stdout, stderr = await asyncio.wait_for(
                        asyncio.create_task(self._communicate_with_process(process)),
                        timeout=script_config.timeout_seconds
                    )
                    result.stdout = stdout
                    result.stderr = stderr
                    result.exit_code = process.returncode
                except asyncio.TimeoutError:
                    result.status = ScriptStatus.TIMEOUT
                    process.kill()
            
            # Phase 5: Post-execution processing
            end_time = time.time()
            result.execution_time_seconds = end_time - start_time
            result.end_time = datetime.now()
            
            if result.status == ScriptStatus.RUNNING:
                if result.exit_code == 0:
                    result.status = ScriptStatus.COMPLETED
                else:
                    result.status = ScriptStatus.FAILED
            
            # Phase 6: Safety validation of output
            if self.config.enable_safety_validation and script_config.enable_safety_validation:
                await self._validate_script_output(result)
            
            # Phase 7: Log results
            self._log_execution_result(result)
            
            # Store in history
            self._execution_history.append(result)
            
            return result
            
        except Exception as e:
            result.status = ScriptStatus.FAILED
            result.errors.append(f"Execution failed: {str(e)}")
            result.end_time = datetime.now()
            self.logger.error(f"Script execution failed: {e}")
            return result
        
        finally:
            # Clean up
            if script_config.name in self._running_scripts:
                del self._running_scripts[script_config.name]
    
    async def _validate_script_execution(self, script_config: ScriptConfig) -> List[str]:
        """Validate script can be executed safely."""
        errors = []
        
        # Basic configuration validation
        config_errors = script_config.validate()
        errors.extend(config_errors)
        
        # Check framework dependencies
        for dep in self.config.required_dependencies:
            if dep in ['psutil', 'gitpython', 'click', 'rich']:
                # Python dependencies - check by import
                try:
                    __import__(dep.replace('-', '_'))
                except ImportError:
                    errors.append(f"Required Python dependency not available: {dep}")
            else:
                # System dependencies - check command availability
                if not shutil.which(dep):
                    errors.append(f"Required system dependency not found: {dep}")
        
        # Git repository check if required
        if script_config.require_git_clean and self.config.enable_git_integration:
            if not await self._is_git_repository_clean():
                errors.append("Git repository has uncommitted changes but script requires clean state")
        
        # Memory and resource checks
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        if script_config.max_memory_mb > available_memory_mb:
            errors.append(f"Insufficient memory: {script_config.max_memory_mb}MB required, {available_memory_mb:.0f}MB available")
        
        return errors
    
    async def _start_script_process(
        self,
        script_config: ScriptConfig,
        capture_output: bool
    ) -> subprocess.Popen:
        """Start script process with appropriate configuration."""
        # Build command
        if script_config.script_type == ScriptType.PYTHON:
            cmd = ["python3", str(script_config.script_path)]
        elif script_config.script_type in [ScriptType.SHELL, ScriptType.BASH]:
            cmd = ["bash", str(script_config.script_path)]
        else:
            raise ValueError(f"Unsupported script type: {script_config.script_type}")
        
        # Add arguments
        cmd.extend(script_config.arguments)
        
        # Setup environment
        env = dict(os.environ)
        env.update(script_config.environment_vars)
        
        # Add framework environment variables
        env['SCRIPT_FRAMEWORK_ENABLED'] = 'true'
        env['SCRIPT_SAFETY_VALIDATION'] = str(self.config.enable_safety_validation)
        env['SCRIPT_DRY_RUN'] = str(self.config.dry_run_mode)
        
        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            cwd=script_config.working_directory or self.config.project_root,
            env=env,
            text=True
        )
        
        self.logger.debug(f"Started process {process.pid} for {script_config.name}")
        return process
    
    async def _communicate_with_process(self, process: subprocess.Popen) -> tuple[str, str]:
        """Communicate with process and get output."""
        try:
            stdout, stderr = process.communicate()
            return stdout or "", stderr or ""
        except Exception as e:
            self.logger.error(f"Failed to communicate with process: {e}")
            return "", str(e)
    
    async def _monitor_script_execution(
        self,
        process: subprocess.Popen,
        result: ScriptResult,
        script_config: ScriptConfig
    ) -> None:
        """Monitor script execution with performance tracking."""
        try:
            psutil_process = psutil.Process(process.pid)
            max_memory = 0.0
            cpu_times = []
            
            start_time = time.time()
            timeout = script_config.timeout_seconds
            
            while process.poll() is None:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Check timeout
                if elapsed > timeout:
                    result.status = ScriptStatus.TIMEOUT
                    process.kill()
                    break
                
                try:
                    # Monitor memory usage
                    memory_info = psutil_process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    max_memory = max(max_memory, memory_mb)
                    
                    # Monitor CPU usage
                    cpu_percent = psutil_process.cpu_percent()
                    cpu_times.append(cpu_percent)
                    
                    # Check memory limit
                    if memory_mb > script_config.max_memory_mb:
                        result.status = ScriptStatus.FAILED
                        result.errors.append(f"Memory limit exceeded: {memory_mb:.1f}MB > {script_config.max_memory_mb}MB")
                        process.kill()
                        break
                    
                except psutil.NoSuchProcess:
                    # Process finished
                    break
                
                # Sleep briefly before next check
                await asyncio.sleep(0.1)
            
            # Get final output
            stdout, stderr = await self._communicate_with_process(process)
            result.stdout = stdout
            result.stderr = stderr
            result.exit_code = process.returncode
            
            # Set performance metrics
            result.max_memory_usage_mb = max_memory
            result.cpu_usage_percent = sum(cpu_times) / len(cpu_times) if cpu_times else 0.0
            
        except Exception as e:
            self.logger.error(f"Error monitoring script execution: {e}")
            result.warnings.append(f"Monitoring error: {str(e)}")
    
    async def _create_git_backup(self, script_name: str) -> bool:
        """Create git backup before script execution."""
        try:
            import git
            
            repo = git.Repo(self.config.project_root)
            
            # Create backup branch
            backup_branch_name = f"backup-{script_name}-{int(time.time())}"
            backup_branch = repo.create_head(backup_branch_name)
            
            self.logger.info(f"Created git backup branch: {backup_branch_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create git backup: {e}")
            return False
    
    async def _is_git_repository_clean(self) -> bool:
        """Check if git repository is clean."""
        try:
            import git
            
            repo = git.Repo(self.config.project_root)
            return not repo.is_dirty()
            
        except Exception as e:
            self.logger.warning(f"Could not check git status: {e}")
            return True  # Assume clean if we can't check
    
    async def _validate_script_output(self, result: ScriptResult) -> None:
        """Validate script output for safety compliance."""
        # This would use the actual SafetyValidator in the full implementation
        combined_output = f"{result.stdout}\n{result.stderr}"
        
        # Simple safety validation (placeholder)
        concrete_refs = 0
        safety_violations = []
        
        # Check for file paths
        import re
        file_paths = re.findall(r'/[^\s]+', combined_output)
        if file_paths:
            concrete_refs += len(file_paths)
            safety_violations.append(f"File paths detected in output: {len(file_paths)}")
        
        # Check for URLs
        urls = re.findall(r'https?://[^\s]+', combined_output)
        if urls:
            concrete_refs += len(urls)
            safety_violations.append(f"URLs detected in output: {len(urls)}")
        
        # Calculate safety score
        safety_score = max(0.0, 1.0 - (concrete_refs * 0.1))
        
        result.safety_score = safety_score
        result.concrete_references_detected = concrete_refs
        result.safety_violations = safety_violations
        
        if safety_score < self.config.safety_score_threshold:
            result.warnings.append(f"Safety score below threshold: {safety_score:.3f}")
    
    def _log_execution_result(self, result: ScriptResult) -> None:
        """Log script execution result."""
        if result.success:
            self.logger.info(
                f"Script {result.script_name} completed successfully",
                **result.get_summary()
            )
        else:
            self.logger.error(
                f"Script {result.script_name} failed",
                **result.get_summary()
            )
        
        # Log performance
        self.logger.log_performance(
            operation=f"script_execution_{result.script_name}",
            duration_ms=result.duration_ms,
            memory_usage_mb=result.max_memory_usage_mb
        )
        
        # Log safety validation
        self.logger.log_safety_validation(
            content_type="script_output",
            safety_score=result.safety_score,
            validation_passed=len(result.safety_violations) == 0
        )
    
    def get_execution_history(self, limit: Optional[int] = None) -> List[ScriptResult]:
        """Get script execution history."""
        history = sorted(self._execution_history, key=lambda r: r.start_time, reverse=True)
        return history[:limit] if limit else history
    
    def get_running_scripts(self) -> List[str]:
        """Get list of currently running scripts."""
        return list(self._running_scripts.keys())
    
    async def cancel_script(self, script_name: str) -> bool:
        """Cancel a running script."""
        if script_name in self._running_scripts:
            try:
                process = self._running_scripts[script_name]
                process.terminate()
                
                # Wait briefly for graceful termination
                await asyncio.sleep(1.0)
                
                if process.poll() is None:
                    # Force kill if still running
                    process.kill()
                
                self.logger.info(f"Cancelled script: {script_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to cancel script {script_name}: {e}")
                return False
        
        return False
    
    def get_framework_stats(self) -> Dict[str, Any]:
        """Get framework statistics."""
        total_executions = len(self._execution_history)
        successful_executions = len([r for r in self._execution_history if r.success])
        
        if total_executions > 0:
            success_rate = successful_executions / total_executions
            avg_duration = sum(r.execution_time_seconds for r in self._execution_history) / total_executions
            avg_memory = sum(r.max_memory_usage_mb for r in self._execution_history) / total_executions
            avg_safety_score = sum(r.safety_score for r in self._execution_history) / total_executions
        else:
            success_rate = 0.0
            avg_duration = 0.0
            avg_memory = 0.0
            avg_safety_score = 1.0
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': success_rate,
            'currently_running': len(self._running_scripts),
            'average_duration_seconds': avg_duration,
            'average_memory_usage_mb': avg_memory,
            'average_safety_score': avg_safety_score,
            'framework_config': {
                'environment': self.config.environment,
                'safety_validation_enabled': self.config.enable_safety_validation,
                'git_integration_enabled': self.config.enable_git_integration
            }
        }


# Import os for environment variables
import os