"""
Status command implementation for CoachNTT.ai CLI.

Provides system health checking, API connectivity verification, and 
comprehensive status reporting for all system components.
"""

import click
from typing import Dict, Any

from ..core import CLIEngine, run_async_command
from ..utils import (
    format_output,
    create_status_panel,
    print_success,
    print_warning,
    print_error,
    print_info,
    show_spinner
)


@click.command()
@click.option(
    "--json", 
    "output_json",
    is_flag=True,
    help="Output status as JSON for scripting"
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Include detailed performance metrics and component information"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output for troubleshooting"
)
def status_command(output_json: bool, detailed: bool, debug: bool):
    """
    Display system health, API connectivity, and safety metrics.
    
    Checks the status of:
    - API server connectivity and response time
    - Database connection (via API health endpoint)
    - Safety validation system
    - Memory system statistics
    
    Examples:
        coachntt status                    # Basic status check
        coachntt status --detailed         # Include detailed metrics
        coachntt status --json             # JSON output for scripts
    """
    async def _run_status_check():
        config = CLIEngine.CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print("Starting system status check")
            
            # Show spinner for status check
            with show_spinner("Checking system status...") as progress:
                task = progress.add_task("status", description="Checking API connectivity...")
                
                # Get comprehensive system status
                status_data = await cli.get_system_status()
                
                progress.update(task, description="Analyzing component health...")
            
            if output_json:
                # JSON output for scripting
                cli.format_and_display(status_data, "json")
            else:
                # Rich formatted output for humans
                _display_status_report(status_data, detailed, cli)
    
    run_async_command(_run_status_check())


def _display_status_report(status_data: Dict[str, Any], detailed: bool, cli: CLIEngine) -> None:
    """Display formatted status report."""
    
    # Overall status header
    overall_status = status_data.get("overall_status", "unknown")
    timestamp = status_data.get("timestamp", "")
    
    if overall_status == "healthy":
        print_success(f"CoachNTT.ai System Status: HEALTHY")
    elif overall_status == "unreachable":
        print_error(f"CoachNTT.ai System Status: UNREACHABLE")
    else:
        print_warning(f"CoachNTT.ai System Status: DEGRADED")
    
    print_info(f"Status checked at: {timestamp}")
    print()  # Empty line for spacing
    
    # API Status Panel
    api_data = status_data.get("api", {})
    api_status = api_data.get("status", "unknown")
    
    api_details = {}
    if "response_time_ms" in api_data:
        api_details["Response Time"] = f"{api_data['response_time_ms']} ms"
    if "connectivity" in api_data:
        api_details["Connectivity"] = api_data["connectivity"]
    
    # Add detailed API info if available and requested
    if detailed and "api" in api_data and isinstance(api_data["api"], dict):
        api_info = api_data["api"]
        if "database" in api_info:
            api_details["Database"] = api_info["database"].get("status", "unknown")
        if "safety" in api_info:
            safety_info = api_info["safety"]
            api_details["Safety Score"] = safety_info.get("current_score", "unknown")
            api_details["Safety Status"] = safety_info.get("status", "unknown")
    
    api_panel = create_status_panel("API Server", api_status, api_details)
    cli.console.print(api_panel)
    
    # CLI Configuration Panel
    cli_data = status_data.get("cli", {})
    cli_details = {
        "Version": cli_data.get("version", "unknown"),
        "API URL": cli_data.get("config", {}).get("api_base_url", "unknown"),
        "Output Format": cli_data.get("config", {}).get("output_format", "unknown"),
        "Max Results": str(cli_data.get("config", {}).get("max_results", "unknown"))
    }
    
    cli_panel = create_status_panel("CLI Configuration", "configured", cli_details)
    cli.console.print(cli_panel)
    
    # Error details if system is not healthy
    if overall_status != "healthy":
        print()
        if api_data.get("message"):
            print_error(f"Issue: {api_data['message']}")
        
        print_info("Troubleshooting:")
        print_info("1. Ensure the API server is running:")
        print_info("   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
        print_info("2. Check your configuration:")
        print_info("   coachntt config --show")
        print_info("3. Verify database is accessible:")
        print_info("   docker-compose ps")
    
    # Detailed metrics if requested and available
    if detailed and overall_status == "healthy":
        print()
        print_info("System is healthy and ready for operations")
        print_info("Available commands:")
        print_info("  coachntt memory list     # List recent memories")
        print_info("  coachntt --help          # Show all commands")


# Export for command registration
__all__ = ["status_command"]