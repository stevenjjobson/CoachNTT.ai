"""
Configuration management commands for CoachNTT.ai CLI.

Provides commands for viewing, setting, and managing CLI configuration
with environment variable integration and validation.
"""

import click
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from ..core import CLIConfig
from ..utils import (
    print_success,
    print_warning,
    print_error,
    print_info,
    format_output
)


# Configuration schema with validation rules
CONFIG_SCHEMA = {
    "api_base_url": {
        "description": "Base URL for the CoachNTT.ai API server",
        "type": "string",
        "default": "http://localhost:8000",
        "validation": lambda x: x.startswith(("http://", "https://"))
    },
    "api_timeout": {
        "description": "API request timeout in seconds",
        "type": "integer",
        "default": 30,
        "validation": lambda x: isinstance(x, int) and 1 <= x <= 300
    },
    "output_format": {
        "description": "Default output format for commands",
        "type": "string",
        "default": "table",
        "validation": lambda x: x in ["table", "json", "simple"]
    },
    "max_results": {
        "description": "Maximum number of results to return by default",
        "type": "integer", 
        "default": 10,
        "validation": lambda x: isinstance(x, int) and 1 <= x <= 100
    },
    "debug": {
        "description": "Enable debug output",
        "type": "boolean",
        "default": False,
        "validation": lambda x: isinstance(x, bool)
    }
}


def get_config_file_path() -> Path:
    """Get the path to the CLI configuration file."""
    # Use XDG config directory on Linux/Mac, AppData on Windows
    if os.name == 'posix':
        config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
    else:
        config_dir = Path(os.environ.get('APPDATA', '~/.config')).expanduser()
    
    return config_dir / 'coachntt' / 'config.json'


def load_config_file() -> Dict[str, Any]:
    """Load configuration from file."""
    config_file = get_config_file_path()
    
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print_warning(f"Failed to load config file: {e}")
        return {}


def save_config_file(config: Dict[str, Any]) -> bool:
    """Save configuration to file."""
    config_file = get_config_file_path()
    
    try:
        # Create directory if needed
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
    except Exception as e:
        print_error(f"Failed to save config file: {e}")
        return False


def get_current_config() -> Dict[str, Any]:
    """Get current configuration from all sources."""
    # Start with defaults
    config = {key: schema["default"] for key, schema in CONFIG_SCHEMA.items()}
    
    # Override with file config
    file_config = load_config_file()
    config.update(file_config)
    
    # Override with environment variables
    env_mapping = {
        "api_base_url": "COACHNTT_API_BASE_URL",
        "api_timeout": "COACHNTT_API_TIMEOUT", 
        "output_format": "COACHNTT_OUTPUT_FORMAT",
        "max_results": "COACHNTT_MAX_RESULTS",
        "debug": "COACHNTT_DEBUG"
    }
    
    for config_key, env_key in env_mapping.items():
        env_value = os.environ.get(env_key)
        if env_value is not None:
            # Convert based on schema type
            schema = CONFIG_SCHEMA[config_key]
            try:
                if schema["type"] == "integer":
                    config[config_key] = int(env_value)
                elif schema["type"] == "boolean":
                    config[config_key] = env_value.lower() in ("true", "1", "yes", "on")
                else:
                    config[config_key] = env_value
            except ValueError:
                print_warning(f"Invalid value for {env_key}: {env_value}")
    
    return config


def validate_config_value(key: str, value: Any) -> bool:
    """Validate a configuration value."""
    if key not in CONFIG_SCHEMA:
        return False
    
    schema = CONFIG_SCHEMA[key]
    validator = schema.get("validation")
    
    if validator:
        try:
            return validator(value)
        except Exception:
            return False
    
    return True


@click.group()
def config_command():
    """
    Configuration management operations.
    
    View and manage CLI configuration including API settings,
    output formats, and behavior preferences.
    """
    pass


@config_command.command("show")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['table', 'json', 'simple']),
    default='table',
    help="Output format (default: table)"
)
@click.option(
    "--sources",
    is_flag=True,
    help="Show configuration sources (file, env, default)"
)
def show_config(output_format: str, sources: bool):
    """
    Display current configuration.
    
    Shows all configuration values from defaults, config file,
    and environment variables with their current effective values.
    
    Examples:
        coachntt config show                       # Show current config
        coachntt config show --format json        # JSON output
        coachntt config show --sources            # Show config sources
    """
    try:
        current_config = get_current_config()
        
        if sources:
            # Show configuration sources
            file_config = load_config_file()
            env_mapping = {
                "api_base_url": "COACHNTT_API_BASE_URL",
                "api_timeout": "COACHNTT_API_TIMEOUT",
                "output_format": "COACHNTT_OUTPUT_FORMAT", 
                "max_results": "COACHNTT_MAX_RESULTS",
                "debug": "COACHNTT_DEBUG"
            }
            
            config_with_sources = []
            for key, schema in CONFIG_SCHEMA.items():
                source = "default"
                if key in file_config:
                    source = "file"
                if os.environ.get(env_mapping.get(key)):
                    source = "environment"
                
                config_with_sources.append({
                    "Setting": key,
                    "Value": str(current_config[key]),
                    "Source": source,
                    "Description": schema["description"]
                })
            
            if output_format == "json":
                format_output(config_with_sources, "json")
            else:
                format_output(config_with_sources, output_format, "Configuration Settings")
        
        else:
            # Show current configuration
            if output_format == "json":
                format_output(current_config, "json")
            else:
                config_display = []
                for key, value in current_config.items():
                    schema = CONFIG_SCHEMA.get(key, {})
                    config_display.append({
                        "Setting": key,
                        "Value": str(value),
                        "Description": schema.get("description", "")
                    })
                
                format_output(config_display, output_format, "Current Configuration")
        
        # Show config file location
        config_file = get_config_file_path()
        print_info(f"Config file: {config_file}")
        if config_file.exists():
            print_info("Use 'coachntt config show --sources' to see configuration sources")
        else:
            print_info("Config file does not exist (using defaults and environment)")
    
    except Exception as e:
        print_error(f"Failed to show configuration: {e}")


@config_command.command("set")
@click.argument("setting")
@click.argument("value")
@click.option(
    "--global",
    "global_config",
    is_flag=True,
    help="Save to global config file (default: save to file)"
)
def set_config(setting: str, value: str, global_config: bool):
    """
    Set configuration value.
    
    Updates a configuration setting and saves it to the config file.
    The value will be validated according to the setting's schema.
    
    Examples:
        coachntt config set api_base_url http://localhost:8000
        coachntt config set output_format json
        coachntt config set max_results 20
        coachntt config set debug true
    """
    try:
        # Validate setting name
        if setting not in CONFIG_SCHEMA:
            print_error(f"Unknown setting: {setting}")
            print_info("Use 'coachntt config list' to see available settings")
            return
        
        schema = CONFIG_SCHEMA[setting]
        
        # Convert value based on schema type
        converted_value = value
        try:
            if schema["type"] == "integer":
                converted_value = int(value)
            elif schema["type"] == "boolean":
                converted_value = value.lower() in ("true", "1", "yes", "on")
        except ValueError:
            print_error(f"Invalid value for {setting}: {value}")
            print_info(f"Expected {schema['type']}")
            return
        
        # Validate the value
        if not validate_config_value(setting, converted_value):
            print_error(f"Invalid value for {setting}: {value}")
            print_info(f"Description: {schema['description']}")
            
            # Show valid options for choice fields
            if schema["type"] == "string" and hasattr(schema.get("validation"), "__code__"):
                # Try to extract valid choices from validation function
                if "table" in str(schema.get("validation", "")):
                    print_info("Valid options: table, json, simple")
            
            return
        
        # Load current file config
        file_config = load_config_file()
        
        # Update the setting
        file_config[setting] = converted_value
        
        # Save to file
        if save_config_file(file_config):
            print_success(f"Configuration updated: {setting} = {converted_value}")
            print_info(f"Saved to: {get_config_file_path()}")
            
            # Show current effective value
            current_config = get_current_config()
            effective_value = current_config[setting]
            
            if effective_value != converted_value:
                print_warning(f"Note: Effective value is {effective_value} (environment variable override)")
        else:
            print_error("Failed to save configuration")
    
    except Exception as e:
        print_error(f"Failed to set configuration: {e}")


@config_command.command("list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['table', 'json', 'simple']),
    default='table',
    help="Output format (default: table)"
)
def list_settings(output_format: str):
    """
    List all available configuration settings.
    
    Shows all configurable settings with their descriptions,
    types, and default values.
    
    Examples:
        coachntt config list                       # List all settings
        coachntt config list --format json        # JSON output
    """
    try:
        settings_list = []
        
        for key, schema in CONFIG_SCHEMA.items():
            settings_list.append({
                "Setting": key,
                "Type": schema["type"],
                "Default": str(schema["default"]),
                "Description": schema["description"]
            })
        
        if output_format == "json":
            format_output(settings_list, "json")
        else:
            format_output(settings_list, output_format, "Available Configuration Settings")
        
        print()
        print_info("Set values with: coachntt config set <setting> <value>")
        print_info("View current config: coachntt config show")
    
    except Exception as e:
        print_error(f"Failed to list settings: {e}")


@config_command.command("reset")
@click.argument("setting", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Reset all settings to defaults"
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt"
)
def reset_config(setting: Optional[str], all: bool, confirm: bool):
    """
    Reset configuration settings to defaults.
    
    Resets one or all configuration settings to their default values
    by removing them from the config file.
    
    Examples:
        coachntt config reset api_base_url         # Reset single setting
        coachntt config reset --all               # Reset all settings
    """
    try:
        if not setting and not all:
            print_error("Must specify a setting or use --all")
            return
        
        if all and not confirm:
            from ..utils import confirm_action
            if not confirm_action("Reset all configuration settings to defaults?"):
                print_info("Reset cancelled")
                return
        
        # Load current file config
        file_config = load_config_file()
        
        if all:
            # Clear all settings
            file_config.clear()
            print_success("All configuration settings reset to defaults")
        else:
            # Reset specific setting
            if setting not in CONFIG_SCHEMA:
                print_error(f"Unknown setting: {setting}")
                return
            
            if setting in file_config:
                del file_config[setting]
                print_success(f"Setting '{setting}' reset to default")
            else:
                print_info(f"Setting '{setting}' was already at default value")
        
        # Save updated config
        if save_config_file(file_config):
            print_info(f"Configuration saved to: {get_config_file_path()}")
        else:
            print_error("Failed to save configuration")
    
    except Exception as e:
        print_error(f"Failed to reset configuration: {e}")


@config_command.command("path")
def show_config_path():
    """
    Show configuration file path.
    
    Displays the path to the configuration file and whether it exists.
    
    Examples:
        coachntt config path                       # Show config file path
    """
    try:
        config_file = get_config_file_path()
        print_info(f"Configuration file: {config_file}")
        
        if config_file.exists():
            print_success("Config file exists")
            
            # Show file size and modification time
            stat = config_file.stat()
            size = stat.st_size
            
            from datetime import datetime
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            print_info(f"Size: {size} bytes")
            print_info(f"Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print_warning("Config file does not exist")
            print_info("Using defaults and environment variables")
        
        # Show environment variables
        env_vars = [
            "COACHNTT_API_BASE_URL",
            "COACHNTT_API_TIMEOUT",
            "COACHNTT_OUTPUT_FORMAT",
            "COACHNTT_MAX_RESULTS",
            "COACHNTT_DEBUG"
        ]
        
        active_env_vars = [var for var in env_vars if os.environ.get(var)]
        
        if active_env_vars:
            print_info(f"Active environment variables: {', '.join(active_env_vars)}")
        else:
            print_info("No environment variables set")
    
    except Exception as e:
        print_error(f"Failed to show config path: {e}")


# Export for command registration
__all__ = ["config_command"]