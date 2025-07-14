"""
CLI Commands module for CoachNTT.ai.

This module contains all CLI command implementations organized by functional area:
- status: System health and connectivity commands
- memory: Memory management operations
- graph: Knowledge graph operations
- integration: Vault sync and automation commands (planned)
"""

from .status import status_command
from .memory import memory_command
from .graph import graph_command

# Command registry for the main CLI
COMMANDS = {
    "status": status_command,
    "memory": memory_command,
    "graph": graph_command,
}

__all__ = [
    "COMMANDS",
    "status_command", 
    "memory_command",
    "graph_command"
]