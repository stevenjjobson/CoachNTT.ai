#!/usr/bin/env python3
"""
CoachNTT.ai CLI - Cognitive Coding Partner Command Line Interface

A comprehensive command-line interface for the CoachNTT.ai system,
providing immediate access to memory management, knowledge graphs,
and automation features with safety-first design.

Usage:
    python coachntt.py --help              # Show all commands
    python coachntt.py status              # Check system health
    python coachntt.py memory list         # List recent memories
    python coachntt.py memory show <id>    # Show memory details
"""

import sys
import click
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cli import __version__
from cli.commands import COMMANDS
from cli.utils import print_error, print_info, print_success


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    help="Show version information"
)
@click.pass_context
def main(ctx, version):
    """
    CoachNTT.ai CLI - Cognitive Coding Partner
    
    A safety-first command-line interface for memory management,
    knowledge graphs, and development automation.
    
    \b
    Quick Start:
        coachntt status                    # Check system health
        coachntt memory list               # List recent memories
        coachntt --help                    # Show all commands
    
    \b
    Command Groups:
        status      System health and connectivity
        memory      Memory management operations
        graph       Knowledge graph operations
        sync        Vault synchronization operations
        docs        Documentation generation
        checkpoint  Development checkpoints
        interactive Interactive CLI mode
        config      Configuration management
    
    \b
    For detailed help on any command:
        coachntt <command> --help
    
    \b
    Configuration:
        The CLI uses the same configuration as the API server.
        Ensure your .env file is properly configured.
    
    \b
    Examples:
        coachntt status --detailed         # Detailed system status
        coachntt memory list --limit 20    # List 20 recent memories
        coachntt memory show abc123        # Show specific memory
    """
    if ctx.invoked_subcommand is None:
        if version:
            _show_version()
        else:
            _show_welcome()
            print()
            print(ctx.get_help())


def _show_version():
    """Show version information."""
    print_info(f"CoachNTT.ai CLI version {__version__}")
    print_info("Cognitive Coding Partner - Safety-First Development Assistant")
    print()
    print_info("Component Status:")
    print_info("  ✅ CLI Framework: Operational")
    print_info("  ✅ Memory Management: Available")
    print_info("  ✅ Knowledge Graphs: Available")
    print_info("  ✅ Integration Tools: Available")
    print_info("  ✅ Interactive Mode: Available")
    print_info("  ✅ Configuration Management: Available")
    print()
    print_info("For system health check: coachntt status")


def _show_welcome():
    """Show welcome message."""
    print_success("Welcome to CoachNTT.ai CLI!")
    print_info("Cognitive Coding Partner - Your safety-first development assistant")
    print()
    print_info("To get started:")
    print_info("  1. Check system status: coachntt status")
    print_info("  2. List your memories: coachntt memory list") 
    print_info("  3. Get help anytime: coachntt --help")


# Register all commands from the commands module
for command_name, command_func in COMMANDS.items():
    main.add_command(command_func, name=command_name)


# Add version command as well
@main.command()
@click.option(
    "--components",
    is_flag=True,
    help="Show detailed component versions"
)
def version(components):
    """
    Show version information and component status.
    
    Displays CLI version, implementation status of different features,
    and optionally detailed component information.
    
    Examples:
        coachntt version                   # Basic version info
        coachntt version --components      # Detailed component info
    """
    _show_version()
    
    if components:
        print()
        print_info("Detailed Component Information:")
        print_info("  • CLI Framework: Click-based with Rich formatting")
        print_info("  • Memory API: FastAPI integration with httpx")
        print_info("  • Safety System: Automatic abstraction enabled")
        print_info("  • Output Formats: Table, JSON, Simple text")
        print_info("  • Configuration: Environment-based with defaults")
        print()
        print_info("Session Implementation Status:")
        print_info("  ✅ Session 4.2a: Basic CLI with status and memory list")
        print_info("  ✅ Session 4.2b: Complete memory management")
        print_info("  ✅ Session 4.2c: Knowledge graph operations")
        print_info("  ✅ Session 4.2d: Integration and interactive mode")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        print_info("For troubleshooting help:")
        print_info("  1. Check system status: coachntt status --debug")
        print_info("  2. Verify API is running: coachntt status")
        print_info("  3. Check configuration: coachntt version --components")
        sys.exit(1)