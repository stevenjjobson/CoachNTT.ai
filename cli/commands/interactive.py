"""
Interactive CLI mode for CoachNTT.ai.

Provides an interactive command-line interface with tab completion,
command history, and built-in help system.
"""

import click
import os
import sys
import atexit
import readline
import shlex
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..core import CLIEngine, CLIConfig
from ..utils import print_success, print_error, print_info, print_warning


class InteractiveCLI:
    """Interactive CLI session manager."""
    
    def __init__(self, history_file: Optional[str] = None, enable_completion: bool = True):
        """
        Initialize interactive CLI.
        
        Args:
            history_file: Path to command history file
            enable_completion: Enable tab completion
        """
        self.history_file = history_file or os.path.expanduser("~/.coachntt_history")
        self.enable_completion = enable_completion
        self.session_active = False
        self.commands = {}
        self._setup_readline()
        self._load_commands()
    
    def _setup_readline(self):
        """Setup readline for command history and completion."""
        try:
            # Load command history
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
            
            # Set history length
            readline.set_history_length(1000)
            
            # Save history on exit
            atexit.register(self._save_history)
            
            # Setup tab completion
            if self.enable_completion:
                readline.set_completer(self._complete_command)
                readline.parse_and_bind("tab: complete")
                
                # Enable history search with up/down arrows
                readline.parse_and_bind("\\e[A: history-search-backward")
                readline.parse_and_bind("\\e[B: history-search-forward")
        
        except ImportError:
            print_warning("Readline not available - history and completion disabled")
        except Exception as e:
            print_warning(f"Failed to setup readline: {e}")
    
    def _save_history(self):
        """Save command history to file."""
        try:
            # Create directory if needed
            history_dir = os.path.dirname(self.history_file)
            if history_dir:
                os.makedirs(history_dir, exist_ok=True)
            
            readline.write_history_file(self.history_file)
        except Exception as e:
            print_warning(f"Failed to save history: {e}")
    
    def _load_commands(self):
        """Load available commands for completion."""
        self.commands = {
            # System commands
            "status": "Check system health and connectivity",
            "version": "Show version information",
            "help": "Show help for commands",
            "exit": "Exit interactive mode",
            "quit": "Exit interactive mode",
            
            # Memory commands
            "memory": {
                "list": "List recent memories",
                "create": "Create new memory",
                "search": "Search memories",
                "show": "Show memory details",
                "update": "Update memory",
                "delete": "Delete memory",
                "export": "Export memories"
            },
            
            # Graph commands
            "graph": {
                "build": "Build knowledge graph",
                "list": "List available graphs",
                "show": "Show graph details",
                "query": "Query knowledge graph",
                "export": "Export graph",
                "subgraph": "Extract subgraph",
                "delete": "Delete graph"
            },
            
            # Integration commands
            "sync": {
                "vault": "Synchronize with Obsidian vault"
            },
            "docs": {
                "generate": "Generate project documentation"
            },
            "checkpoint": {
                "create": "Create development checkpoint"
            },
            
            # Configuration commands
            "config": {
                "show": "Show current configuration",
                "set": "Set configuration value",
                "list": "List available settings"
            }
        }
    
    def _complete_command(self, text: str, state: int) -> Optional[str]:
        """
        Tab completion for commands.
        
        Args:
            text: Current text being completed
            state: Completion state
        
        Returns:
            Next completion option or None
        """
        try:
            line = readline.get_line_buffer()
            parts = shlex.split(line) if line else []
            
            # If we're at the beginning or first word
            if not parts or (len(parts) == 1 and not line.endswith(' ')):
                matches = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]
                return matches[state] if state < len(matches) else None
            
            # Handle subcommands
            if len(parts) >= 1:
                main_cmd = parts[0]
                if main_cmd in self.commands and isinstance(self.commands[main_cmd], dict):
                    if len(parts) == 1 and line.endswith(' '):
                        # Complete first subcommand
                        matches = list(self.commands[main_cmd].keys())
                        return matches[state] if state < len(matches) else None
                    elif len(parts) == 2 and not line.endswith(' '):
                        # Complete partial subcommand
                        matches = [sub for sub in self.commands[main_cmd].keys() 
                                 if sub.startswith(parts[1])]
                        return matches[state] if state < len(matches) else None
            
            return None
        
        except Exception:
            return None
    
    def _show_welcome(self):
        """Show welcome message for interactive mode."""
        print_success("Welcome to CoachNTT.ai Interactive CLI!")
        print_info("Type 'help' for available commands or 'exit' to quit.")
        print_info("Use Tab for command completion and arrow keys for history.")
        print()
    
    def _show_help(self, command: Optional[str] = None):
        """
        Show help for commands.
        
        Args:
            command: Specific command to show help for
        """
        if not command:
            print_info("Available commands:")
            print()
            for cmd, desc in self.commands.items():
                if isinstance(desc, dict):
                    print_info(f"  {cmd:<12} - Command group with subcommands")
                    for sub, sub_desc in desc.items():
                        print_info(f"    {sub:<10} - {sub_desc}")
                else:
                    print_info(f"  {cmd:<12} - {desc}")
            print()
            print_info("Use 'help <command>' for detailed help on a specific command.")
            print_info("Use Tab for completion and arrow keys for command history.")
        else:
            if command in self.commands:
                if isinstance(self.commands[command], dict):
                    print_info(f"'{command}' subcommands:")
                    for sub, desc in self.commands[command].items():
                        print_info(f"  {command} {sub:<10} - {desc}")
                else:
                    print_info(f"{command}: {self.commands[command]}")
            else:
                print_error(f"Unknown command: {command}")
                print_info("Type 'help' for available commands.")
    
    async def _execute_command(self, command_line: str) -> bool:
        """
        Execute a command line.
        
        Args:
            command_line: Full command line to execute
        
        Returns:
            True to continue session, False to exit
        """
        try:
            parts = shlex.split(command_line.strip())
            if not parts:
                return True
            
            cmd = parts[0].lower()
            
            # Handle built-in commands
            if cmd in ['exit', 'quit']:
                return False
            elif cmd == 'help':
                help_cmd = parts[1] if len(parts) > 1 else None
                self._show_help(help_cmd)
                return True
            elif cmd == 'clear':
                os.system('clear' if os.name == 'posix' else 'cls')
                return True
            
            # For other commands, we need to execute them through the main CLI
            # This is a bit of a hack, but it allows us to reuse existing command logic
            from ...coachntt import main
            
            # Temporarily redirect argv
            original_argv = sys.argv
            try:
                sys.argv = ['coachntt'] + parts
                
                # Capture the context and invoke the command
                # Note: This is a simplified approach for the interactive mode
                # In a full implementation, we would have a more sophisticated
                # command dispatcher that doesn't rely on sys.argv manipulation
                
                print_info(f"Executing: {' '.join(parts)}")
                
                # For now, just show that the command would be executed
                # In a real implementation, this would invoke the actual command
                print_info("(Command execution would happen here)")
                
            finally:
                sys.argv = original_argv
            
            return True
        
        except KeyboardInterrupt:
            print()  # New line after ^C
            return True
        except EOFError:
            print()  # New line after ^D
            return False
        except Exception as e:
            print_error(f"Error executing command: {e}")
            return True
    
    async def run(self):
        """Run the interactive CLI session."""
        self.session_active = True
        self._show_welcome()
        
        try:
            while self.session_active:
                try:
                    # Get input with prompt
                    command_line = input("coachntt> ")
                    
                    # Skip empty lines
                    if not command_line.strip():
                        continue
                    
                    # Execute command
                    should_continue = await self._execute_command(command_line)
                    if not should_continue:
                        break
                
                except KeyboardInterrupt:
                    print()  # New line after ^C
                    continue
                except EOFError:
                    print()  # New line after ^D
                    break
        
        finally:
            self.session_active = False
            print_info("Goodbye!")


@click.command()
@click.option(
    "--history-file",
    type=click.Path(),
    help="Command history file location"
)
@click.option(
    "--no-completion",
    is_flag=True,
    help="Disable tab completion"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def interactive_command(
    history_file: Optional[str],
    no_completion: bool,
    debug: bool
):
    """
    Enter interactive CLI mode with command completion.
    
    Provides an interactive shell with tab completion, command history,
    and built-in help system for all CoachNTT.ai commands.
    
    Features:
    - Tab completion for commands and options
    - Command history with up/down arrows
    - Built-in help with 'help' command
    - Exit with 'exit' or Ctrl+D
    
    Examples:
        coachntt interactive                           # Start interactive mode
        
        coachntt interactive --history-file ~/.my_history  # Custom history file
        
        coachntt interactive --no-completion           # Disable tab completion
    """
    try:
        import asyncio
        
        # Create interactive CLI instance
        interactive_cli = InteractiveCLI(
            history_file=history_file,
            enable_completion=not no_completion
        )
        
        # Check if we can connect to the API first
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async def check_api_and_run():
            """Check API connectivity and run interactive mode."""
            async with CLIEngine(config) as cli:
                if debug:
                    cli.debug_print("Starting interactive mode")
                
                # Check API connectivity
                health_check = await cli.check_api_health()
                if health_check["status"] != "healthy":
                    print_warning("API server is not fully healthy")
                    print_info(f"Status: {health_check['status']}")
                    print_info("Some commands may not work properly")
                    print()
                
                # Run interactive session
                await interactive_cli.run()
        
        # Run the interactive session
        asyncio.run(check_api_and_run())
    
    except KeyboardInterrupt:
        print_info("\nInteractive mode cancelled")
    except Exception as e:
        print_error(f"Failed to start interactive mode: {e}")
        if debug:
            import traceback
            traceback.print_exc()


# Export for command registration
__all__ = ["interactive_command"]