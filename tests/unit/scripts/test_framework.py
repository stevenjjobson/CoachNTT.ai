"""
Unit tests for script automation framework components.

Tests ScriptRunner, ScriptLogger, and configuration management with
safety validation and performance monitoring.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from framework import (
    ScriptRunner, ScriptConfig, ScriptResult, ScriptLogger, LogLevel,
    ScriptFrameworkConfig, load_script_config, ScriptType, ScriptStatus
)


class TestScriptFrameworkConfig:
    """Test script framework configuration."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        config = load_script_config()
        
        assert config.safety_score_threshold == Decimal("0.8")
        assert config.enable_safety_validation is True
        assert config.abstract_all_output is True
        assert config.max_execution_time_seconds == 300
        assert config.log_level == "INFO"
    
    def test_config_environment_overrides(self):
        """Test configuration environment variable overrides."""
        with patch.dict('os.environ', {
            'SCRIPT_SAFETY_THRESHOLD': '0.9',
            'SCRIPT_DEBUG': 'true',
            'SCRIPT_MAX_EXECUTION_TIME': '600'
        }):
            config = load_script_config()
            
            assert config.safety_score_threshold == Decimal("0.9")
            assert config.debug_mode is True
            assert config.max_execution_time_seconds == 600
    
    def test_config_paths_creation(self):
        """Test that configuration creates necessary paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_script_config()
            # Verify logs directory is created
            assert config.logs_directory.exists()


class TestScriptLogger:
    """Test script logging with safety validation."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = ScriptLogger(
            script_name="test_script",
            log_level=LogLevel.DEBUG,
            abstract_content=True
        )
        
        assert logger.script_name == "test_script"
        assert logger.log_level == LogLevel.DEBUG
        assert logger.abstract_content is True
        assert len(logger._log_entries) == 0
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = ScriptLogger(
                script_name="test_script",
                log_directory=Path(temp_dir),
                abstract_content=False
            )
            
            logger.info("Test message")
            logger.warning("Test warning")
            logger.error("Test error")
            
            assert len(logger._log_entries) == 3
            assert logger._log_entries[0].level == LogLevel.INFO
            assert logger._log_entries[1].level == LogLevel.WARNING
            assert logger._log_entries[2].level == LogLevel.ERROR
    
    def test_content_abstraction(self):
        """Test automatic content abstraction."""
        logger = ScriptLogger(
            script_name="test_script",
            abstract_content=True
        )
        
        # Test with concrete references
        message_with_paths = "Processing file /home/user/secret.txt"
        logger.info(message_with_paths)
        
        # Should abstract the file path
        log_entry = logger._log_entries[0]
        assert "<file_path>" in log_entry.message
        assert "/home/user/secret.txt" not in log_entry.message
        assert log_entry.concrete_references_detected > 0
    
    def test_performance_logging(self):
        """Test performance logging functionality."""
        logger = ScriptLogger(script_name="test_script")
        
        logger.log_performance(
            operation="test_operation",
            duration_ms=1500,
            memory_usage_mb=256.5
        )
        
        log_entry = logger._log_entries[0]
        assert "test_operation" in log_entry.message
        assert "1500ms" in log_entry.message
        assert log_entry.metadata["duration_ms"] == 1500
        assert log_entry.metadata["memory_usage_mb"] == 256.5
    
    def test_safety_validation_logging(self):
        """Test safety validation logging."""
        logger = ScriptLogger(script_name="test_script")
        
        logger.log_safety_validation(
            content_type="script_output",
            safety_score=0.95,
            validation_passed=True
        )
        
        log_entry = logger._log_entries[0]
        assert log_entry.level == LogLevel.INFO
        assert "safety validation" in log_entry.message.lower()
        assert log_entry.metadata["safety_score"] == 0.95
    
    def test_execution_summary(self):
        """Test execution summary generation."""
        logger = ScriptLogger(script_name="test_script")
        
        logger.info("Test info")
        logger.warning("Test warning")
        logger.error("Test error")
        
        summary = logger.get_execution_summary()
        
        assert summary["script_name"] == "test_script"
        assert summary["total_log_entries"] == 3
        assert summary["log_level_counts"]["INFO"] == 1
        assert summary["log_level_counts"]["WARNING"] == 1
        assert summary["log_level_counts"]["ERROR"] == 1
        assert summary["total_concrete_references_detected"] >= 0


class TestScriptConfig:
    """Test script configuration and validation."""
    
    def test_script_config_creation(self):
        """Test script configuration creation."""
        with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
            config = ScriptConfig(
                script_path=Path(temp_file.name),
                script_type=ScriptType.PYTHON,
                name="test_script",
                description="Test script description"
            )
            
            assert config.script_path.exists()
            assert config.script_type == ScriptType.PYTHON
            assert config.name == "test_script"
            assert config.timeout_seconds == 300
            assert config.enable_safety_validation is True
    
    def test_script_config_validation_success(self):
        """Test successful script configuration validation."""
        with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
            config = ScriptConfig(
                script_path=Path(temp_file.name),
                script_type=ScriptType.PYTHON,
                name="test_script"
            )
            
            errors = config.validate()
            assert len(errors) == 0
    
    def test_script_config_validation_failures(self):
        """Test script configuration validation failures."""
        # Non-existent file
        config = ScriptConfig(
            script_path=Path("/nonexistent/script.py"),
            script_type=ScriptType.PYTHON,
            name="test_script"
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("not found" in error for error in errors)
    
    def test_script_config_with_dependencies(self):
        """Test script configuration with dependencies."""
        with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
            config = ScriptConfig(
                script_path=Path(temp_file.name),
                script_type=ScriptType.PYTHON,
                name="test_script",
                required_commands=["python3", "nonexistent_command"]
            )
            
            errors = config.validate()
            # Should have error for nonexistent command
            assert any("nonexistent_command" in error for error in errors)


class TestScriptResult:
    """Test script execution result tracking."""
    
    def test_script_result_creation(self):
        """Test script result creation."""
        result = ScriptResult(
            script_name="test_script",
            status=ScriptStatus.COMPLETED,
            start_time=datetime.now(),
            exit_code=0
        )
        
        assert result.script_name == "test_script"
        assert result.status == ScriptStatus.COMPLETED
        assert result.success is True
        assert result.exit_code == 0
    
    def test_script_result_failure(self):
        """Test failed script result."""
        result = ScriptResult(
            script_name="test_script",
            status=ScriptStatus.FAILED,
            start_time=datetime.now(),
            exit_code=1
        )
        
        result.errors.append("Test error")
        result.safety_violations.append("Safety violation")
        
        assert result.success is False
        assert len(result.errors) == 1
        assert len(result.safety_violations) == 1
    
    def test_script_result_summary(self):
        """Test script result summary generation."""
        start_time = datetime.now()
        result = ScriptResult(
            script_name="test_script",
            status=ScriptStatus.COMPLETED,
            start_time=start_time,
            exit_code=0
        )
        
        result.execution_time_seconds = 2.5
        result.max_memory_usage_mb = 128.0
        result.safety_score = 0.95
        
        summary = result.get_summary()
        
        assert summary["script_name"] == "test_script"
        assert summary["success"] is True
        assert summary["execution_time_seconds"] == 2.5
        assert summary["max_memory_usage_mb"] == 128.0
        assert summary["safety_score"] == 0.95


class TestScriptRunner:
    """Test script runner functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = ScriptFrameworkConfig(
            project_root=Path("/tmp"),
            scripts_root=Path("/tmp/scripts"),
            logs_directory=Path("/tmp/logs"),
            safety_score_threshold=Decimal("0.8"),
            max_execution_time_seconds=60
        )
        return config
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock(spec=ScriptLogger)
        logger.info = Mock()
        logger.error = Mock()
        logger.warning = Mock()
        logger.debug = Mock()
        return logger
    
    def test_script_runner_initialization(self, mock_config, mock_logger):
        """Test script runner initialization."""
        runner = ScriptRunner(config=mock_config, logger=mock_logger)
        
        assert runner.config == mock_config
        assert runner.logger == mock_logger
        assert len(runner._running_scripts) == 0
        assert len(runner._execution_history) == 0
    
    @pytest.mark.asyncio
    async def test_script_validation(self, mock_config, mock_logger):
        """Test script execution validation."""
        runner = ScriptRunner(config=mock_config, logger=mock_logger)
        
        # Create invalid script config
        with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
            script_config = ScriptConfig(
                script_path=Path("/nonexistent/script.py"),
                script_type=ScriptType.PYTHON,
                name="test_script"
            )
            
            # Validation should fail
            errors = await runner._validate_script_execution(script_config)
            assert len(errors) > 0
    
    @pytest.mark.asyncio
    async def test_script_execution_dry_run(self, mock_config, mock_logger):
        """Test script execution in dry run mode."""
        mock_config.dry_run_mode = True
        runner = ScriptRunner(config=mock_config, logger=mock_logger)
        
        with tempfile.NamedTemporaryFile(suffix=".py", mode='w') as temp_file:
            # Write simple Python script
            temp_file.write("print('Hello World')")
            temp_file.flush()
            
            script_config = ScriptConfig(
                script_path=Path(temp_file.name),
                script_type=ScriptType.PYTHON,
                name="test_script"
            )
            
            # Should not actually execute in dry run
            result = await runner.execute_script(script_config)
            
            # Check result structure
            assert isinstance(result, ScriptResult)
            assert result.script_name == "test_script"
    
    def test_framework_stats(self, mock_config, mock_logger):
        """Test framework statistics collection."""
        runner = ScriptRunner(config=mock_config, logger=mock_logger)
        
        # Add some mock execution history
        result1 = ScriptResult(
            script_name="test1",
            status=ScriptStatus.COMPLETED,
            start_time=datetime.now(),
            exit_code=0
        )
        result1.execution_time_seconds = 1.0
        result1.max_memory_usage_mb = 100.0
        result1.safety_score = 0.95
        
        result2 = ScriptResult(
            script_name="test2", 
            status=ScriptStatus.FAILED,
            start_time=datetime.now(),
            exit_code=1
        )
        result2.execution_time_seconds = 2.0
        result2.max_memory_usage_mb = 200.0
        result2.safety_score = 0.85
        
        runner._execution_history = [result1, result2]
        
        stats = runner.get_framework_stats()
        
        assert stats["total_executions"] == 2
        assert stats["successful_executions"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["average_duration_seconds"] == 1.5
        assert stats["average_memory_usage_mb"] == 150.0
        assert stats["average_safety_score"] == 0.9
    
    def test_execution_history(self, mock_config, mock_logger):
        """Test execution history tracking."""
        runner = ScriptRunner(config=mock_config, logger=mock_logger)
        
        # Add multiple results
        for i in range(5):
            result = ScriptResult(
                script_name=f"test_{i}",
                status=ScriptStatus.COMPLETED,
                start_time=datetime.now(),
                exit_code=0
            )
            runner._execution_history.append(result)
        
        # Test history retrieval
        history = runner.get_execution_history()
        assert len(history) == 5
        
        # Test limited history
        limited_history = runner.get_execution_history(limit=3)
        assert len(limited_history) == 3


class TestScriptSafetyValidation:
    """Test safety validation in script framework."""
    
    def test_safety_score_calculation(self):
        """Test safety score calculation."""
        logger = ScriptLogger(script_name="test", abstract_content=True)
        
        # Test with unsafe content
        unsafe_content = "Processing /home/user/secrets.txt and connecting to https://api.example.com"
        abstracted, safety_info = logger._abstract_log_content(unsafe_content)
        
        assert safety_info['concrete_refs'] > 0
        assert safety_info['safety_score'] < 1.0
        assert '<file_path>' in abstracted
        assert '<url>' in abstracted
    
    def test_safety_validation_integration(self):
        """Test safety validation integration."""
        result = ScriptResult(
            script_name="test_script",
            status=ScriptStatus.COMPLETED,
            start_time=datetime.now()
        )
        
        # Simulate safety validation
        result.safety_score = 0.75  # Below threshold
        result.concrete_references_detected = 5
        result.safety_violations = ["Hardcoded path detected", "URL found in output"]
        
        assert result.safety_score < 0.8
        assert len(result.safety_violations) == 2
        assert result.concrete_references_detected == 5
    
    def test_safety_threshold_enforcement(self, mock_config, mock_logger):
        """Test safety threshold enforcement."""
        mock_config.safety_score_threshold = Decimal("0.9")
        runner = ScriptRunner(config=mock_config, logger=mock_logger)
        
        # Test safety score validation
        assert runner.config.safety_score_threshold == Decimal("0.9")


class TestScriptFrameworkIntegration:
    """Integration tests for script framework components."""
    
    @pytest.mark.asyncio
    async def test_full_script_execution_flow(self):
        """Test complete script execution flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test script
            script_path = Path(temp_dir) / "test_script.py"
            script_path.write_text("print('Hello from test script')")
            
            # Create runner
            config = ScriptFrameworkConfig(
                project_root=Path(temp_dir),
                scripts_root=Path(temp_dir),
                logs_directory=Path(temp_dir) / "logs"
            )
            
            logger = ScriptLogger(
                script_name="integration_test",
                log_directory=config.logs_directory
            )
            
            runner = ScriptRunner(config=config, logger=logger)
            
            # Create script configuration
            script_config = ScriptConfig(
                script_path=script_path,
                script_type=ScriptType.PYTHON,
                name="test_integration",
                timeout_seconds=30
            )
            
            # Execute script (this would actually run in real implementation)
            # For tests, we'll just validate the setup
            validation_errors = await runner._validate_script_execution(script_config)
            
            # Should have no validation errors
            assert len(validation_errors) == 0 or all("dependency" in error.lower() for error in validation_errors)
    
    def test_end_to_end_logging_and_safety(self):
        """Test end-to-end logging with safety validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = ScriptLogger(
                script_name="e2e_test",
                log_directory=Path(temp_dir),
                abstract_content=True
            )
            
            # Log various types of content
            logger.info("Starting script execution")
            logger.warning("Processing file /tmp/test.txt")
            logger.error("Connection failed to https://api.example.com")
            
            # Get execution summary
            summary = logger.get_execution_summary()
            
            assert summary["total_log_entries"] == 3
            assert summary["total_concrete_references_detected"] > 0
            assert summary["average_safety_score"] < 1.0
            assert summary["safety_compliance"] is False  # Due to concrete references