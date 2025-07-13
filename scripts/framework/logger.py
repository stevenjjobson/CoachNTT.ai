"""
Centralized logging system for script automation framework.

Provides safety-first logging with content abstraction, structured output,
and integration with existing logging infrastructure.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


class LogLevel(Enum):
    """Log levels for script framework."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry with safety validation."""
    
    timestamp: datetime
    level: LogLevel
    script_name: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Safety tracking
    safety_score: float = 1.0
    is_abstracted: bool = True
    concrete_references_detected: int = 0
    
    # Performance tracking
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    
    
class ScriptLogger:
    """
    Safety-first logger for automation scripts.
    
    Provides structured logging with automatic content abstraction,
    performance tracking, and integration with existing safety systems.
    """
    
    def __init__(
        self,
        script_name: str,
        log_level: LogLevel = LogLevel.INFO,
        log_directory: Optional[Path] = None,
        enable_console: bool = True,
        enable_rich_formatting: bool = True,
        abstract_content: bool = True
    ):
        """
        Initialize script logger.
        
        Args:
            script_name: Name of the script using this logger
            log_level: Minimum log level to output
            log_directory: Directory for log files
            enable_console: Whether to enable console output
            enable_rich_formatting: Whether to use rich formatting
            abstract_content: Whether to abstract log content
        """
        self.script_name = script_name
        self.log_level = log_level
        self.log_directory = log_directory or Path("logs/scripts")
        self.enable_console = enable_console
        self.enable_rich_formatting = enable_rich_formatting
        self.abstract_content = abstract_content
        
        # Create log directory if needed
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize loggers
        self._setup_loggers()
        
        # Performance tracking
        self._start_time = time.time()
        self._log_entries: List[LogEntry] = []
        
        # Safety validator (would be imported from core in real implementation)
        self._safety_validator = None  # Placeholder for actual validator
        
        # Rich console for formatting
        if self.enable_rich_formatting:
            self.console = Console()
        else:
            self.console = None
    
    def _setup_loggers(self) -> None:
        """Set up file and console loggers."""
        # Create main logger
        self.logger = logging.getLogger(f"script.{self.script_name}")
        self.logger.setLevel(getattr(logging, self.log_level.value))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        log_file = self.log_directory / f"{self.script_name}.log"
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        if self.enable_console:
            if self.enable_rich_formatting:
                console_handler = RichHandler(console=self.console, rich_tracebacks=True)
            else:
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter(
                    '%(levelname)s - %(name)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
            
            self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **metadata) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, metadata)
    
    def info(self, message: str, **metadata) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, metadata)
    
    def warning(self, message: str, **metadata) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, metadata)
    
    def error(self, message: str, **metadata) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, metadata)
    
    def critical(self, message: str, **metadata) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, metadata)
    
    def _log(self, level: LogLevel, message: str, metadata: Dict[str, Any]) -> None:
        """Internal logging method with safety validation."""
        # Abstract content if enabled
        if self.abstract_content:
            abstracted_message, safety_info = self._abstract_log_content(message)
            abstracted_metadata = {
                k: self._abstract_log_content(str(v))[0] if isinstance(v, str) else v
                for k, v in metadata.items()
            }
        else:
            abstracted_message = message
            abstracted_metadata = metadata
            safety_info = {'safety_score': 1.0, 'concrete_refs': 0}
        
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            script_name=self.script_name,
            message=abstracted_message,
            metadata=abstracted_metadata,
            safety_score=safety_info['safety_score'],
            concrete_references_detected=safety_info['concrete_refs']
        )
        
        # Store entry
        self._log_entries.append(entry)
        
        # Log to standard logger
        log_method = getattr(self.logger, level.value.lower())
        if abstracted_metadata:
            log_method(f"{abstracted_message} | Metadata: {abstracted_metadata}")
        else:
            log_method(abstracted_message)
    
    def _abstract_log_content(self, content: str) -> tuple[str, Dict[str, Any]]:
        """
        Abstract potentially sensitive content from log messages.
        
        This is a simplified implementation. In the full system, this would
        use the actual SafetyValidator from the core system.
        """
        # Simple abstraction patterns
        abstracted = content
        concrete_refs = 0
        
        # Abstract file paths
        import re
        
        # File paths
        if '/' in content or '\\' in content:
            abstracted = re.sub(r'/[^\s]+', '<file_path>', abstracted)
            abstracted = re.sub(r'\\[^\s]+', '<file_path>', abstracted)
            concrete_refs += len(re.findall(r'[/\\][^\s]+', content))
        
        # URLs
        if '://' in content:
            abstracted = re.sub(r'https?://[^\s]+', '<url>', abstracted)
            concrete_refs += len(re.findall(r'https?://[^\s]+', content))
        
        # Email addresses
        if '@' in content and '.' in content:
            abstracted = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<email>', abstracted)
            concrete_refs += len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content))
        
        # Calculate safety score (1.0 = fully safe, 0.0 = many concrete refs)
        safety_score = max(0.0, 1.0 - (concrete_refs * 0.1))
        
        return abstracted, {
            'safety_score': safety_score,
            'concrete_refs': concrete_refs
        }
    
    def log_performance(
        self,
        operation: str,
        duration_ms: int,
        memory_usage_mb: Optional[float] = None,
        **metadata
    ) -> None:
        """Log performance metrics for an operation."""
        perf_metadata = {
            'operation': operation,
            'duration_ms': duration_ms,
            'memory_usage_mb': memory_usage_mb,
            **metadata
        }
        
        self.info(f"Performance: {operation} completed in {duration_ms}ms", **perf_metadata)
    
    def log_safety_validation(
        self,
        content_type: str,
        safety_score: float,
        validation_passed: bool,
        **metadata
    ) -> None:
        """Log safety validation results."""
        safety_metadata = {
            'content_type': content_type,
            'safety_score': safety_score,
            'validation_passed': validation_passed,
            **metadata
        }
        
        level = LogLevel.INFO if validation_passed else LogLevel.WARNING
        message = f"Safety validation: {content_type} {'passed' if validation_passed else 'failed'} (score: {safety_score:.3f})"
        
        self._log(level, message, safety_metadata)
    
    def log_git_operation(
        self,
        operation: str,
        success: bool,
        details: Dict[str, Any]
    ) -> None:
        """Log git operation results."""
        git_metadata = {
            'git_operation': operation,
            'success': success,
            **details
        }
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Git {operation}: {'completed successfully' if success else 'failed'}"
        
        self._log(level, message, git_metadata)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of script execution."""
        total_time = time.time() - self._start_time
        
        # Count log levels
        level_counts = {}
        for level in LogLevel:
            level_counts[level.value] = len([e for e in self._log_entries if e.level == level])
        
        # Calculate average safety score
        safety_scores = [e.safety_score for e in self._log_entries]
        avg_safety_score = sum(safety_scores) / len(safety_scores) if safety_scores else 1.0
        
        # Total concrete references detected
        total_concrete_refs = sum(e.concrete_references_detected for e in self._log_entries)
        
        return {
            'script_name': self.script_name,
            'total_execution_time_seconds': total_time,
            'total_log_entries': len(self._log_entries),
            'log_level_counts': level_counts,
            'average_safety_score': avg_safety_score,
            'total_concrete_references_detected': total_concrete_refs,
            'safety_compliance': avg_safety_score >= 0.8 and total_concrete_refs == 0
        }
    
    def flush_logs(self) -> None:
        """Flush all log handlers."""
        for handler in self.logger.handlers:
            handler.flush()
    
    def close(self) -> None:
        """Close logger and clean up resources."""
        self.flush_logs()
        
        for handler in self.logger.handlers:
            handler.close()
        
        # Log execution summary
        summary = self.get_execution_summary()
        self.info("Script execution completed", **summary)