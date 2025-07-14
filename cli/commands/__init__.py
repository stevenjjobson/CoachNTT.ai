"""
CLI Commands module for CoachNTT.ai.

This module contains all CLI command implementations organized by functional area:
- status: System health and connectivity commands
- memory: Memory management operations
- graph: Knowledge graph operations (planned)
- integration: Vault sync and automation commands (planned)
"""

from .status import status_command
from .memory import memory_command

# Command registry for the main CLI
COMMANDS = {
    "status": status_command,
    "memory": memory_command,
}

__all__ = [
    "COMMANDS",
    "status_command", 
    "memory_command"
]