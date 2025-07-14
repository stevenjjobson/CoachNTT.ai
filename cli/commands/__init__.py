"""
CLI Commands module for CoachNTT.ai.

This module contains all CLI command implementations organized by functional area:
- status: System health and connectivity commands
- memory: Memory management operations
- graph: Knowledge graph operations
- integration: Vault sync, docs generation, and checkpoint commands
- interactive: Interactive CLI mode with tab completion
- config: Configuration management commands
"""

from .status import status_command
from .memory import memory_command
from .graph import graph_command
from .integration import sync_command, docs_command, checkpoint_command
from .interactive import interactive_command
from .config import config_command

# Command registry for the main CLI
COMMANDS = {
    "status": status_command,
    "memory": memory_command,
    "graph": graph_command,
    "sync": sync_command,
    "docs": docs_command,
    "checkpoint": checkpoint_command,
    "interactive": interactive_command,
    "config": config_command,
}

__all__ = [
    "COMMANDS",
    "status_command", 
    "memory_command",
    "graph_command",
    "sync_command",
    "docs_command", 
    "checkpoint_command",
    "interactive_command",
    "config_command"
]