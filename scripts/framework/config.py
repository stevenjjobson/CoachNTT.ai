"""
Configuration management for script automation framework.

Provides centralized configuration loading and validation for all automation scripts
with safety-first design and environment-aware settings.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ScriptFrameworkConfig:
    """Configuration for the script automation framework."""
    
    # Core settings
    project_root: Path
    scripts_root: Path
    logs_directory: Path
    
    # Safety settings
    safety_score_threshold: Decimal = Decimal("0.8")
    enable_safety_validation: bool = True
    abstract_all_output: bool = True
    
    # Performance settings
    max_execution_time_seconds: int = 300  # 5 minutes
    max_memory_usage_mb: int = 1024
    max_concurrent_scripts: int = 3
    
    # Git settings
    enable_git_integration: bool = True
    git_backup_before_operations: bool = True
    git_auto_commit_results: bool = False
    
    # Vault sync settings
    vault_sync_enabled: bool = True
    vault_sync_auto_mode: bool = False
    vault_sync_batch_size: int = 50
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_rotation_size_mb: int = 10
    log_retention_days: int = 30
    
    # Dependency validation
    required_dependencies: List[str] = field(default_factory=lambda: [
        "git", "python3", "psutil", "gitpython", "click", "rich"
    ])
    
    # Environment settings
    environment: str = "development"
    debug_mode: bool = False
    dry_run_mode: bool = False


def load_script_config(
    config_path: Optional[Path] = None,
    environment: Optional[str] = None
) -> ScriptFrameworkConfig:
    """
    Load script framework configuration from file or environment.
    
    Args:
        config_path: Path to configuration file (optional)
        environment: Environment name (development/production)
        
    Returns:
        Loaded configuration object
    """
    # Determine project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent  # Navigate up from scripts/framework/
    
    # Set default paths
    scripts_root = project_root / "scripts"
    logs_directory = project_root / "logs" / "scripts"
    
    # Create logs directory if it doesn't exist
    logs_directory.mkdir(parents=True, exist_ok=True)
    
    # Load base configuration
    config = ScriptFrameworkConfig(
        project_root=project_root,
        scripts_root=scripts_root,
        logs_directory=logs_directory
    )
    
    # Override with environment variables
    config.environment = environment or os.getenv("SCRIPT_ENVIRONMENT", "development")
    config.debug_mode = os.getenv("SCRIPT_DEBUG", "false").lower() == "true"
    config.dry_run_mode = os.getenv("SCRIPT_DRY_RUN", "false").lower() == "true"
    
    # Safety settings from environment
    if os.getenv("SCRIPT_SAFETY_THRESHOLD"):
        config.safety_score_threshold = Decimal(os.getenv("SCRIPT_SAFETY_THRESHOLD"))
    
    config.enable_safety_validation = os.getenv("SCRIPT_SAFETY_VALIDATION", "true").lower() == "true"
    config.abstract_all_output = os.getenv("SCRIPT_ABSTRACT_OUTPUT", "true").lower() == "true"
    
    # Performance settings from environment
    if os.getenv("SCRIPT_MAX_EXECUTION_TIME"):
        config.max_execution_time_seconds = int(os.getenv("SCRIPT_MAX_EXECUTION_TIME"))
    
    if os.getenv("SCRIPT_MAX_MEMORY_MB"):
        config.max_memory_usage_mb = int(os.getenv("SCRIPT_MAX_MEMORY_MB"))
    
    # Git settings from environment
    config.enable_git_integration = os.getenv("SCRIPT_GIT_INTEGRATION", "true").lower() == "true"
    config.git_backup_before_operations = os.getenv("SCRIPT_GIT_BACKUP", "true").lower() == "true"
    config.git_auto_commit_results = os.getenv("SCRIPT_GIT_AUTO_COMMIT", "false").lower() == "true"
    
    # Vault sync settings from environment
    config.vault_sync_enabled = os.getenv("SCRIPT_VAULT_SYNC", "true").lower() == "true"
    config.vault_sync_auto_mode = os.getenv("SCRIPT_VAULT_AUTO", "false").lower() == "true"
    
    if os.getenv("SCRIPT_VAULT_BATCH_SIZE"):
        config.vault_sync_batch_size = int(os.getenv("SCRIPT_VAULT_BATCH_SIZE"))
    
    # Logging settings from environment
    config.log_level = os.getenv("SCRIPT_LOG_LEVEL", "INFO").upper()
    
    # Load from config file if provided
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                _update_config_from_dict(config, file_config)
        except Exception as e:
            # Don't fail if config file is invalid, use defaults
            print(f"Warning: Failed to load config from {config_path}: {e}")
    
    # Environment-specific adjustments
    if config.environment == "production":
        config.debug_mode = False
        config.dry_run_mode = False
        config.log_level = "INFO"
        config.git_auto_commit_results = False  # Never auto-commit in production
    elif config.environment == "development":
        config.debug_mode = True
        config.log_level = "DEBUG"
    
    return config


def _update_config_from_dict(config: ScriptFrameworkConfig, config_dict: Dict[str, Any]) -> None:
    """Update configuration object from dictionary."""
    for key, value in config_dict.items():
        if hasattr(config, key):
            # Handle special types
            if key == "safety_score_threshold" and isinstance(value, (int, float, str)):
                setattr(config, key, Decimal(str(value)))
            elif key in ["project_root", "scripts_root", "logs_directory"] and isinstance(value, str):
                setattr(config, key, Path(value))
            else:
                setattr(config, key, value)


def save_script_config(config: ScriptFrameworkConfig, config_path: Path) -> bool:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        config_path: Path to save configuration to
        
    Returns:
        Whether save was successful
    """
    try:
        config_dict = {
            "safety_score_threshold": str(config.safety_score_threshold),
            "enable_safety_validation": config.enable_safety_validation,
            "abstract_all_output": config.abstract_all_output,
            "max_execution_time_seconds": config.max_execution_time_seconds,
            "max_memory_usage_mb": config.max_memory_usage_mb,
            "max_concurrent_scripts": config.max_concurrent_scripts,
            "enable_git_integration": config.enable_git_integration,
            "git_backup_before_operations": config.git_backup_before_operations,
            "git_auto_commit_results": config.git_auto_commit_results,
            "vault_sync_enabled": config.vault_sync_enabled,
            "vault_sync_auto_mode": config.vault_sync_auto_mode,
            "vault_sync_batch_size": config.vault_sync_batch_size,
            "log_level": config.log_level,
            "log_format": config.log_format,
            "log_rotation_size_mb": config.log_rotation_size_mb,
            "log_retention_days": config.log_retention_days,
            "required_dependencies": config.required_dependencies,
            "environment": config.environment,
            "debug_mode": config.debug_mode,
            "dry_run_mode": config.dry_run_mode
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return True
        
    except Exception:
        return False