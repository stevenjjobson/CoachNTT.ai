"""
CLI utility functions for output formatting and safe display.

Provides consistent output formatting, table display, and safety-compliant
content abstraction for all CLI commands.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rich_print


# Initialize Rich console for consistent output
console = Console()


def safe_print(content: Any, abstraction_required: bool = True) -> None:
    """
    Safely print content with optional abstraction.
    
    Args:
        content: Content to print
        abstraction_required: Whether to apply safety abstraction
    """
    if abstraction_required and isinstance(content, str):
        # Apply basic abstraction patterns
        content = _apply_basic_abstraction(content)
    
    console.print(content)


def _apply_basic_abstraction(text: str) -> str:
    """Apply basic abstraction patterns to text content."""
    import re
    
    # Pattern replacements for safety
    patterns = {
        r'/[a-zA-Z]:/[^/\s]+': '<file_path>',  # Windows file paths
        r'/[^/\s]+/[^/\s]+': '<directory_path>',  # Unix paths
        r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b': '<uuid>',  # UUIDs
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b': '<ip_address>',  # IP addresses
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b': '<email>',  # Email addresses
    }
    
    result = text
    for pattern, replacement in patterns.items():
        result = re.sub(pattern, replacement, result)
    
    return result


def format_output(data: Any, format_type: str = "table", title: Optional[str] = None) -> None:
    """
    Format and display data in specified format.
    
    Args:
        data: Data to format and display
        format_type: Output format (table, json, simple)
        title: Optional title for the output
    """
    if format_type == "json":
        print(json.dumps(_serialize_for_json(data), indent=2, default=str))
    elif format_type == "simple":
        _format_simple(data, title)
    else:  # table format
        _format_table(data, title)


def _serialize_for_json(obj: Any) -> Any:
    """Serialize objects for JSON output."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return {k: _serialize_for_json(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    else:
        return obj


def _format_table(data: Any, title: Optional[str] = None) -> None:
    """Format data as a Rich table."""
    if isinstance(data, list) and len(data) > 0:
        # Create table from list of dictionaries
        if isinstance(data[0], dict):
            _format_dict_table(data, title)
        else:
            _format_simple_list(data, title)
    elif isinstance(data, dict):
        _format_single_dict(data, title)
    else:
        _format_simple(data, title)


def _format_dict_table(data: List[Dict], title: Optional[str] = None) -> None:
    """Format list of dictionaries as table."""
    if not data:
        console.print("No data to display")
        return
    
    # Get all unique keys
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())
    
    # Create table
    table = Table(title=title, show_header=True, header_style="bold blue")
    
    # Add columns
    for key in sorted(all_keys):
        table.add_column(key.replace('_', ' ').title(), style="cyan")
    
    # Add rows
    for item in data:
        row = []
        for key in sorted(all_keys):
            value = item.get(key, "")
            if isinstance(value, (datetime, Decimal)):
                value = str(value)
            elif isinstance(value, bool):
                value = "✓" if value else "✗"
            row.append(str(value))
        table.add_row(*row)
    
    console.print(table)


def _format_single_dict(data: Dict, title: Optional[str] = None) -> None:
    """Format single dictionary as key-value table."""
    table = Table(title=title, show_header=True, header_style="bold blue")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    for key, value in data.items():
        if isinstance(value, (datetime, Decimal)):
            value = str(value)
        elif isinstance(value, bool):
            value = "✓" if value else "✗"
        elif isinstance(value, (list, dict)):
            value = json.dumps(value, indent=2, default=str)
        
        table.add_row(
            key.replace('_', ' ').title(),
            str(value)
        )
    
    console.print(table)


def _format_simple_list(data: List, title: Optional[str] = None) -> None:
    """Format simple list."""
    if title:
        console.print(f"\n[bold blue]{title}[/bold blue]")
    
    for i, item in enumerate(data, 1):
        console.print(f"{i}. {item}")


def _format_simple(data: Any, title: Optional[str] = None) -> None:
    """Format data in simple text format."""
    if title:
        console.print(f"\n[bold blue]{title}[/bold blue]")
    
    console.print(str(data))


def create_status_panel(title: str, status: str, details: Optional[Dict] = None) -> Panel:
    """
    Create a status panel for system information.
    
    Args:
        title: Panel title
        status: Status (healthy, warning, error)
        details: Optional details to display
    
    Returns:
        Rich Panel object
    """
    # Choose colors based on status
    if status.lower() == "healthy":
        color = "green"
        symbol = "✓"
    elif status.lower() == "warning":
        color = "yellow"
        symbol = "⚠"
    else:
        color = "red"
        symbol = "✗"
    
    # Create content
    content = f"[{color}]{symbol} {status.upper()}[/{color}]"
    
    if details:
        content += "\n\n"
        for key, value in details.items():
            content += f"[dim]{key}:[/dim] {value}\n"
    
    return Panel(
        content.strip(),
        title=title,
        border_style=color,
        padding=(1, 2)
    )


def show_spinner(message: str = "Processing..."):
    """
    Context manager for showing a spinner during operations.
    
    Args:
        message: Message to display with spinner
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    )


def print_success(message: str) -> None:
    """Print success message with green checkmark."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print warning message with yellow warning symbol."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message: str) -> None:
    """Print error message with red X."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print info message with blue info symbol."""
    console.print(f"[blue]ℹ[/blue] {message}")


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.
    
    Args:
        message: Confirmation message
        default: Default response if user just presses enter
    
    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"{message}{suffix}: ").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes', 'true', '1')


def format_bytes(bytes_value: int) -> str:
    """Format byte count as human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human readable string."""
    if seconds < 1:
        return f"{seconds*1000:.1f} ms"
    elif seconds < 60:
        return f"{seconds:.1f} s"
    elif seconds < 3600:
        return f"{seconds/60:.1f} min"
    else:
        return f"{seconds/3600:.1f} hr"