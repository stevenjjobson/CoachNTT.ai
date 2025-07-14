"""
Memory management commands for CoachNTT.ai CLI.

Provides commands for listing, searching, viewing, and managing memories
with safety-first design and comprehensive output formatting.
"""

import click
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..core import CLIEngine, run_async_command
from ..utils import (
    format_output,
    print_success,
    print_warning,
    print_error,
    print_info,
    show_spinner,
    format_duration
)


@click.group()
def memory_command():
    """
    Memory management operations.
    
    Manage your memories with create, search, list, and export operations.
    All operations maintain safety-first design with automatic abstraction.
    """
    pass


@memory_command.command("list")
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of memories to show (default: 10, max: 50)"
)
@click.option(
    "--type",
    "memory_type",
    type=click.Choice(['learning', 'decision', 'context', 'debug', 'optimization']),
    help="Filter by memory type"
)
@click.option(
    "--since",
    type=int,
    default=7,
    help="Show memories from last N days (default: 7)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['table', 'json', 'simple']),
    default='table',
    help="Output format (default: table)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def list_memories(
    limit: int, 
    memory_type: Optional[str], 
    since: int, 
    output_format: str,
    debug: bool
):
    """
    List recent memories with safety abstraction.
    
    Shows your recent memories with automatically abstracted content,
    preserving privacy while maintaining utility for development work.
    
    Examples:
        coachntt memory list                           # List 10 recent memories
        coachntt memory list --limit 20 --type learning  # List 20 learning memories
        coachntt memory list --format json --limit 5   # JSON output for scripts
        coachntt memory list --since 3                 # Memories from last 3 days
    """
    async def _run_list_memories():
        config = CLIEngine.CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Listing memories: limit={limit}, type={memory_type}, since={since}")
            
            # Validate limit
            if limit > 50:
                print_warning("Limit capped at 50 for performance")
                limit = 50
            
            # Show spinner for API call
            with show_spinner("Fetching memories...") as progress:
                task = progress.add_task("fetch", description="Querying memory repository...")
                
                # Get memories from API
                result = await cli.list_memories(
                    limit=limit,
                    memory_type=memory_type,
                    since_days=since
                )
                
                progress.update(task, description="Processing results...")
            
            if result["status"] == "success":
                memories = result["memories"]
                total = result["total"]
                
                if not memories:
                    print_info("No memories found matching your criteria")
                    print_info("Try adjusting --since or --type filters, or create some memories first")
                    return
                
                # Format memories for display
                formatted_memories = _format_memories_for_display(memories)
                
                # Display results
                if output_format == "json":
                    cli.format_and_display(result, "json")
                else:
                    # Show summary
                    filters_desc = []
                    if memory_type:
                        filters_desc.append(f"type={memory_type}")
                    if since != 7:
                        filters_desc.append(f"since={since} days")
                    
                    title = f"Recent Memories ({len(memories)} of {total}"
                    if filters_desc:
                        title += f", filtered by {', '.join(filters_desc)}"
                    title += ")"
                    
                    cli.format_and_display(formatted_memories, output_format, title)
                    
                    # Show helpful info
                    if len(memories) == limit and total > limit:
                        print_info(f"Showing {limit} of {total} memories. Use --limit to see more.")
                    
                    print_info(f"Use 'coachntt memory show <id>' to view full details")
            
            elif result["status"] == "error":
                print_error(f"Failed to fetch memories: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Verify API server is running")
                print_info("3. Check network connectivity")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_list_memories())


@memory_command.command("show")
@click.argument("memory_id")
@click.option(
    "--format",
    "output_format", 
    type=click.Choice(['pretty', 'json']),
    default='pretty',
    help="Output format (default: pretty)"
)
@click.option(
    "--include-related",
    is_flag=True,
    help="Show related memories and connections"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def show_memory(memory_id: str, output_format: str, include_related: bool, debug: bool):
    """
    Display detailed information about a specific memory.
    
    Shows complete memory details including metadata, safety scores,
    and optionally related memories and semantic connections.
    
    Examples:
        coachntt memory show abc123                    # Show memory details
        coachntt memory show abc123 --include-related  # Include related memories  
        coachntt memory show abc123 --format json      # JSON output
    """
    async def _run_show_memory():
        config = CLIEngine.CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Showing memory: {memory_id}")
            
            # Show spinner for API call
            with show_spinner("Fetching memory details...") as progress:
                task = progress.add_task("fetch", description="Querying memory...")
                
                result = await cli.get_memory(memory_id)
                
                progress.update(task, description="Processing details...")
            
            if result["status"] == "success":
                memory = result["memory"]
                
                if output_format == "json":
                    cli.format_and_display(memory, "json")
                else:
                    # Format for pretty display
                    formatted_memory = _format_memory_details(memory)
                    cli.format_and_display(
                        formatted_memory, 
                        "table", 
                        f"Memory Details: {memory_id[:8]}..."
                    )
                    
                    # Show related memories if requested
                    if include_related:
                        print_info("Related memories feature coming in Session 4.2b")
            
            elif result["status"] == "not_found":
                print_error(f"Memory not found: {memory_id}")
                print_info("Use 'coachntt memory list' to see available memories")
            
            elif result["status"] == "error":
                print_error(f"Failed to fetch memory: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_show_memory())


def _format_memories_for_display(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format memories for table display."""
    formatted = []
    
    for memory in memories:
        # Extract key fields for table display
        formatted_memory = {
            "ID": str(memory.get("memory_id", ""))[:8] + "...",
            "Type": memory.get("memory_type", "unknown"),
            "Prompt": _truncate_text(memory.get("abstracted_prompt", ""), 40),
            "Content": _truncate_text(memory.get("abstracted_content", ""), 50),
            "Safety": f"{float(memory.get('safety_score', 0)):.2f}",
            "Created": _format_relative_time(memory.get("created_at")),
            "Accessed": memory.get("access_count", 0)
        }
        formatted.append(formatted_memory)
    
    return formatted


def _format_memory_details(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Format single memory for detailed display."""
    return {
        "Memory ID": str(memory.get("memory_id", "")),
        "Type": memory.get("memory_type", "unknown"),
        "Abstracted Prompt": memory.get("abstracted_prompt", ""),
        "Abstracted Content": memory.get("abstracted_content", ""),
        "Safety Score": f"{float(memory.get('safety_score', 0)):.3f}",
        "Temporal Weight": f"{float(memory.get('temporal_weight', 0)):.3f}",
        "Created At": memory.get("created_at", ""),
        "Last Accessed": memory.get("accessed_at", ""), 
        "Access Count": memory.get("access_count", 0),
        "Metadata": memory.get("metadata", {}) or "None"
    }


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to specified length with ellipsis."""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def _format_relative_time(timestamp_str: Optional[str]) -> str:
    """Format timestamp as relative time."""
    if not timestamp_str:
        return "unknown"
    
    try:
        # Parse ISO timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timestamp.tzinfo)
        
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"
    
    except Exception:
        return "unknown"


# Export for command registration
__all__ = ["memory_command"]