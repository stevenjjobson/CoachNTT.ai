"""
Memory management commands for CoachNTT.ai CLI.

Provides commands for listing, searching, viewing, and managing memories
with safety-first design and comprehensive output formatting.
"""

import click
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..core import CLIEngine, CLIConfig, run_async_command
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
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Listing memories: limit={limit}, type={memory_type}, since={since}")
            
            # Validate limit
            validated_limit = limit
            if validated_limit > 50:
                print_warning("Limit capped at 50 for performance")
                validated_limit = 50
            
            # Show spinner for API call
            with show_spinner("Fetching memories...") as progress:
                task = progress.add_task(description="Querying memory repository...")
                
                # Get memories from API
                result = await cli.list_memories(
                    limit=validated_limit,
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
                    if len(memories) == validated_limit and total > validated_limit:
                        print_info(f"Showing {validated_limit} of {total} memories. Use --limit to see more.")
                    
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
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Showing memory: {memory_id}")
            
            # Show spinner for API call
            with show_spinner("Fetching memory details...") as progress:
                task = progress.add_task(description="Querying memory...")
                
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


@memory_command.command("create")
@click.argument("prompt")
@click.argument("content")
@click.option(
    "--type",
    "memory_type",
    type=click.Choice(['learning', 'decision', 'context', 'debug', 'optimization']),
    default='learning',
    help="Memory type (default: learning)"
)
@click.option(
    "--metadata",
    multiple=True,
    help="Add metadata as key=value pairs (can be used multiple times)"
)
@click.option(
    "--intent",
    type=str,
    help="Specify intent type for better categorization"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def create_memory(
    prompt: str, 
    content: str, 
    memory_type: str, 
    metadata: tuple, 
    intent: Optional[str],
    debug: bool
):
    """
    Create a new memory with automatic safety validation.
    
    Creates a memory that will be automatically abstracted and validated
    for safety compliance before storage.
    
    Examples:
        coachntt memory create "How to optimize database queries" "Use indexes and limit result sets"
        
        coachntt memory create \
          "API endpoint design" \
          "REST endpoints should follow resource naming" \
          --type learning \
          --metadata project=api \
          --metadata priority=high
        
        coachntt memory create \
          "Memory leak in service" \
          "Found memory leak in connection pool" \
          --type debug \
          --intent troubleshooting
    """
    async def _run_create_memory():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Creating memory: type={memory_type}, intent={intent}")
            
            # Validate inputs
            if not prompt.strip():
                print_error("Prompt cannot be empty")
                return
            
            if not content.strip():
                print_error("Content cannot be empty")
                return
            
            # Parse metadata
            metadata_dict = {}
            for meta_item in metadata:
                if "=" not in meta_item:
                    print_error(f"Invalid metadata format: {meta_item}. Use key=value")
                    return
                
                key, value = meta_item.split("=", 1)
                metadata_dict[key.strip()] = value.strip()
            
            if debug:
                cli.debug_print(f"Parsed metadata: {metadata_dict}")
            
            # Show spinner for API call
            with show_spinner("Creating memory...") as progress:
                task = progress.add_task(description="Validating and storing memory...")
                
                # Create memory through API
                result = await cli.create_memory(
                    memory_type=memory_type,
                    prompt=prompt,
                    content=content,
                    metadata=metadata_dict,
                    intent=intent
                )
                
                progress.update(task, description="Processing result...")
            
            if result["status"] == "success":
                memory = result["memory"]
                memory_id = str(memory["memory_id"])[:8] + "..."
                
                print_success(f"Memory created successfully!")
                print_info(f"Memory ID: {memory_id}")
                print_info(f"Type: {memory['memory_type']}")
                print_info(f"Safety Score: {float(memory['safety_score']):.3f}")
                
                if memory.get("metadata"):
                    print_info(f"Metadata: {len(memory['metadata'])} items")
                
                print()
                print_info("Memory has been safely abstracted and is ready for use.")
                print_info(f"Use 'coachntt memory show {memory['memory_id']}' to view details")
            
            elif result["status"] == "validation_error":
                print_error("Failed to create memory due to validation errors:")
                try:
                    # Try to parse error details
                    import json
                    details = json.loads(result.get("details", "{}"))
                    if isinstance(details, dict) and "detail" in details:
                        if isinstance(details["detail"], list):
                            for error in details["detail"]:
                                print_error(f"  • {error.get('msg', error)}")
                        else:
                            print_error(f"  • {details['detail']}")
                    else:
                        print_error(f"  • {result.get('details', 'Unknown validation error')}")
                except:
                    print_error(f"  • {result.get('details', 'Unknown validation error')}")
                
                print()
                print_info("Common validation issues:")
                print_info("  • Prompt must be 1-5000 characters")
                print_info("  • Content must be 1-50000 characters") 
                print_info("  • Memory type must be valid (learning, decision, etc.)")
            
            elif result["status"] == "error":
                print_error(f"Failed to create memory: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Verify API server is running")
                print_info("3. Check network connectivity")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_create_memory())


@memory_command.command("search")
@click.argument("query")
@click.option(
    "--type",
    "memory_type",
    type=click.Choice(['learning', 'decision', 'context', 'debug', 'optimization']),
    help="Filter by memory type"
)
@click.option(
    "--intent",
    type=str,
    help="Filter by intent type"
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of results to return (default: 10, max: 50)"
)
@click.option(
    "--min-score",
    type=float,
    help="Minimum relevance score (0.0-1.0)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['table', 'json', 'simple']),
    default='table',
    help="Output format (default: table)"
)
@click.option(
    "--no-intent-analysis",
    is_flag=True,
    help="Disable intent-based search (use basic text search)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def search_memories(
    query: str,
    memory_type: Optional[str],
    intent: Optional[str],
    limit: int,
    min_score: Optional[float],
    output_format: str,
    no_intent_analysis: bool,
    debug: bool
):
    """
    Search memories using semantic similarity and filters.
    
    Performs intelligent search using semantic similarity and intent analysis
    to find the most relevant memories for your query.
    
    Examples:
        coachntt memory search "database optimization"
        
        coachntt memory search "API design" --type learning --min-score 0.8
        
        coachntt memory search "error handling" --intent troubleshooting --limit 5
        
        coachntt memory search "react components" --format json --no-intent-analysis
    """
    async def _run_search_memories():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Searching: query='{query}', type={memory_type}, intent={intent}")
            
            # Validate inputs
            if not query.strip():
                print_error("Search query cannot be empty")
                return
            
            validated_limit = limit
            if validated_limit > 50:
                print_warning("Limit capped at 50 for performance")
                validated_limit = 50
            
            if min_score is not None and (min_score < 0 or min_score > 1):
                print_error("Minimum score must be between 0.0 and 1.0")
                return
            
            # Show spinner for API call
            with show_spinner("Searching memories...") as progress:
                task = progress.add_task(description="Analyzing query and finding matches...")
                
                # Build memory types list
                memory_types = [memory_type] if memory_type else None
                
                # Search memories through API
                result = await cli.search_memories(
                    query=query,
                    memory_types=memory_types,
                    min_score=min_score,
                    limit=validated_limit,
                    enable_intent_analysis=not no_intent_analysis
                )
                
                progress.update(task, description="Processing results...")
            
            if result["status"] == "success":
                search_results = result["results"]
                total = result["total"]
                
                if not search_results:
                    print_info("No memories found matching your search criteria")
                    print_info("Try:")
                    print_info("  • Broadening your search terms")
                    print_info("  • Removing filters (--type, --min-score)")
                    print_info("  • Using different keywords")
                    return
                
                # Format results for display
                if output_format == "json":
                    cli.format_and_display(search_results, "json")
                else:
                    formatted_results = _format_search_results_for_display(search_results)
                    
                    # Build title with search info
                    search_info = []
                    if memory_type:
                        search_info.append(f"type={memory_type}")
                    if intent:
                        search_info.append(f"intent={intent}")
                    if min_score:
                        search_info.append(f"min-score={min_score}")
                    
                    title = f"Search Results for '{query}' ({total} found"
                    if search_info:
                        title += f", filtered by {', '.join(search_info)}"
                    title += ")"
                    
                    cli.format_and_display(formatted_results, output_format, title)
                    
                    # Show search insights
                    if not no_intent_analysis:
                        print_info("Search used semantic similarity and intent analysis")
                    else:
                        print_info("Search used basic text matching")
                    
                    # Show relevance info
                    if search_results:
                        max_score = max(r.get("relevance_score", 0) for r in search_results)
                        min_result_score = min(r.get("relevance_score", 0) for r in search_results)
                        print_info(f"Relevance scores range: {min_result_score:.3f} - {max_score:.3f}")
                    
                    if total == validated_limit:
                        print_info(f"Showing top {validated_limit} results. Use --limit to see more.")
            
            elif result["status"] == "error":
                print_error(f"Failed to search memories: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Verify API server is running")
                print_info("3. Try a simpler search query")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_search_memories())


def _format_search_results_for_display(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format search results for table display."""
    formatted = []
    
    for result in search_results:
        memory = result.get("memory", {})
        
        formatted_result = {
            "ID": str(memory.get("memory_id", ""))[:8] + "...",
            "Type": memory.get("memory_type", "unknown"),
            "Relevance": f"{float(result.get('relevance_score', 0)):.3f}",
            "Match": result.get("match_reason", "unknown")[:15],
            "Prompt": _truncate_text(memory.get("abstracted_prompt", ""), 35),
            "Content": _truncate_text(memory.get("abstracted_content", ""), 40),
            "Safety": f"{float(memory.get('safety_score', 0)):.2f}",
            "Created": _format_relative_time(memory.get("created_at"))
        }
        formatted.append(formatted_result)
    
    return formatted


@memory_command.command("export")
@click.option(
    "--format",
    "export_format",
    type=click.Choice(['json', 'csv', 'markdown']),
    default='json',
    help="Export format (default: json)"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path (default: stdout)"
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
    help="Export memories from last N days"
)
@click.option(
    "--limit",
    type=int,
    help="Maximum memories to export"
)
@click.option(
    "--include-metadata",
    is_flag=True,
    help="Include all metadata in export"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def export_memories(
    export_format: str,
    output: Optional[str],
    memory_type: Optional[str],
    since: Optional[int],
    limit: Optional[int],
    include_metadata: bool,
    debug: bool
):
    """
    Export memories to various formats.
    
    Exports your memories in JSON, CSV, or Markdown format with optional
    filtering and metadata inclusion.
    
    Examples:
        coachntt memory export --format json --output memories.json
        
        coachntt memory export \
          --format markdown \
          --type learning \
          --output learning-notes.md
        
        coachntt memory export \
          --format csv \
          --since 30 \
          --include-metadata \
          --output analysis.csv
    """
    async def _run_export_memories():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Exporting: format={export_format}, type={memory_type}, since={since}")
            
            # Build filters
            filters = {}
            if memory_type:
                filters["type"] = memory_type
            if since:
                filters["since_days"] = since
            
            # Show spinner for API call
            with show_spinner("Exporting memories...") as progress:
                task = progress.add_task(description="Fetching memories...")
                
                # Export memories through API
                result = await cli.export_memories(
                    format_type=export_format,
                    filters=filters,
                    limit=limit
                )
                
                progress.update(task, description="Formatting export...")
            
            if result["status"] == "success":
                memories = result["memories"]
                total = result["total"]
                
                if not memories:
                    print_info("No memories found matching your export criteria")
                    return
                
                # Format the export data
                if export_format == "json":
                    export_data = _format_json_export(memories, include_metadata)
                elif export_format == "csv":
                    export_data = _format_csv_export(memories, include_metadata)
                elif export_format == "markdown":
                    export_data = _format_markdown_export(memories, include_metadata)
                else:
                    print_error(f"Unsupported export format: {export_format}")
                    return
                
                # Output to file or stdout
                if output:
                    try:
                        with open(output, 'w', encoding='utf-8') as f:
                            f.write(export_data)
                        
                        print_success(f"Exported {total} memories to {output}")
                        print_info(f"Format: {export_format.upper()}")
                        
                        # Show file info
                        import os
                        file_size = os.path.getsize(output)
                        if file_size < 1024:
                            size_str = f"{file_size} bytes"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size // 1024} KB"
                        else:
                            size_str = f"{file_size // (1024 * 1024)} MB"
                        
                        print_info(f"File size: {size_str}")
                        
                        if filters:
                            filter_info = []
                            for key, value in filters.items():
                                filter_info.append(f"{key}={value}")
                            print_info(f"Filters applied: {', '.join(filter_info)}")
                        
                    except Exception as e:
                        print_error(f"Failed to write to {output}: {e}")
                        return
                else:
                    # Output to stdout
                    print(export_data)
            
            elif result["status"] == "error":
                print_error(f"Failed to export memories: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Verify API server is running")
                print_info("3. Check available disk space")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_export_memories())


def _format_json_export(memories: List[Dict[str, Any]], include_metadata: bool) -> str:
    """Format memories as JSON export."""
    import json
    
    export_data = {
        "export_info": {
            "format": "json",
            "timestamp": datetime.now().isoformat(),
            "total_memories": len(memories),
            "include_metadata": include_metadata
        },
        "memories": []
    }
    
    for memory in memories:
        memory_data = {
            "memory_id": str(memory.get("memory_id", "")),
            "memory_type": memory.get("memory_type", ""),
            "abstracted_prompt": memory.get("abstracted_prompt", ""),
            "abstracted_content": memory.get("abstracted_content", ""),
            "safety_score": float(memory.get("safety_score", 0)),
            "temporal_weight": float(memory.get("temporal_weight", 0)),
            "created_at": memory.get("created_at", ""),
            "accessed_at": memory.get("accessed_at", ""),
            "access_count": memory.get("access_count", 0)
        }
        
        if include_metadata and memory.get("metadata"):
            memory_data["metadata"] = memory["metadata"]
        
        export_data["memories"].append(memory_data)
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def _format_csv_export(memories: List[Dict[str, Any]], include_metadata: bool) -> str:
    """Format memories as CSV export."""
    import csv
    import io
    
    output = io.StringIO()
    
    # Define CSV headers
    headers = [
        "memory_id", "memory_type", "abstracted_prompt", "abstracted_content",
        "safety_score", "temporal_weight", "created_at", "accessed_at", "access_count"
    ]
    
    if include_metadata:
        headers.append("metadata")
    
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for memory in memories:
        row = [
            str(memory.get("memory_id", "")),
            memory.get("memory_type", ""),
            memory.get("abstracted_prompt", ""),
            memory.get("abstracted_content", ""),
            float(memory.get("safety_score", 0)),
            float(memory.get("temporal_weight", 0)),
            memory.get("created_at", ""),
            memory.get("accessed_at", ""),
            memory.get("access_count", 0)
        ]
        
        if include_metadata:
            metadata = memory.get("metadata", {})
            # Convert metadata to JSON string for CSV
            import json
            row.append(json.dumps(metadata) if metadata else "")
        
        writer.writerow(row)
    
    return output.getvalue()


def _format_markdown_export(memories: List[Dict[str, Any]], include_metadata: bool) -> str:
    """Format memories as Markdown export."""
    lines = []
    
    # Header
    lines.append("# Memory Export")
    lines.append("")
    lines.append(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total Memories:** {len(memories)}")
    lines.append(f"**Include Metadata:** {'Yes' if include_metadata else 'No'}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Memories
    for i, memory in enumerate(memories, 1):
        memory_id = str(memory.get("memory_id", ""))[:8] + "..."
        memory_type = memory.get("memory_type", "unknown")
        
        lines.append(f"## {i}. {memory_type.title()} Memory - {memory_id}")
        lines.append("")
        
        # Basic info
        lines.append(f"**Type:** {memory_type}")
        lines.append(f"**Safety Score:** {float(memory.get('safety_score', 0)):.3f}")
        lines.append(f"**Temporal Weight:** {float(memory.get('temporal_weight', 0)):.3f}")
        lines.append(f"**Created:** {memory.get('created_at', '')}")
        lines.append(f"**Access Count:** {memory.get('access_count', 0)}")
        lines.append("")
        
        # Content
        lines.append("### Prompt")
        lines.append(f"> {memory.get('abstracted_prompt', '')}")
        lines.append("")
        
        lines.append("### Content")
        content = memory.get("abstracted_content", "")
        # Simple markdown formatting for content
        for line in content.split('\n'):
            lines.append(line)
        lines.append("")
        
        # Metadata if requested
        if include_metadata and memory.get("metadata"):
            lines.append("### Metadata")
            metadata = memory["metadata"]
            for key, value in metadata.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return '\n'.join(lines)


@memory_command.command("update")
@click.argument("memory_id")
@click.option(
    "--prompt",
    type=str,
    help="Update the prompt text"
)
@click.option(
    "--content",
    type=str,
    help="Update the content text"
)
@click.option(
    "--metadata",
    multiple=True,
    help="Update metadata as key=value pairs (can be used multiple times)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def update_memory(
    memory_id: str,
    prompt: Optional[str],
    content: Optional[str],
    metadata: tuple,
    debug: bool
):
    """
    Update an existing memory.
    
    Updates the prompt, content, or metadata of an existing memory.
    At least one field must be provided for update.
    
    Examples:
        coachntt memory update abc123 --content "Updated content with new information"
        
        coachntt memory update abc123 \
          --prompt "Updated prompt" \
          --content "Updated content" \
          --metadata priority=high
    """
    async def _run_update_memory():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Updating memory: {memory_id}")
            
            # Validate that at least one update field is provided
            if not prompt and not content and not metadata:
                print_error("At least one update field must be provided")
                print_info("Available options: --prompt, --content, --metadata")
                return
            
            # Parse metadata if provided
            metadata_dict = None
            if metadata:
                metadata_dict = {}
                for meta_item in metadata:
                    if "=" not in meta_item:
                        print_error(f"Invalid metadata format: {meta_item}. Use key=value")
                        return
                    
                    key, value = meta_item.split("=", 1)
                    metadata_dict[key.strip()] = value.strip()
            
            if debug:
                cli.debug_print(f"Update fields: prompt={bool(prompt)}, content={bool(content)}, metadata={bool(metadata_dict)}")
            
            # Show spinner for API call
            with show_spinner("Updating memory...") as progress:
                task = progress.add_task(description="Validating and updating memory...")
                
                # Update memory through API
                result = await cli.update_memory(
                    memory_id=memory_id,
                    prompt=prompt,
                    content=content,
                    metadata=metadata_dict
                )
                
                progress.update(task, description="Processing result...")
            
            if result["status"] == "success":
                memory = result["memory"]
                memory_id_short = str(memory["memory_id"])[:8] + "..."
                
                print_success(f"Memory updated successfully!")
                print_info(f"Memory ID: {memory_id_short}")
                print_info(f"Type: {memory['memory_type']}")
                print_info(f"Safety Score: {float(memory['safety_score']):.3f}")
                
                # Show what was updated
                updates = []
                if prompt:
                    updates.append("prompt")
                if content:
                    updates.append("content")
                if metadata_dict:
                    updates.append(f"metadata ({len(metadata_dict)} items)")
                
                print_info(f"Updated: {', '.join(updates)}")
                print()
                print_info("Memory has been re-validated and safely abstracted.")
                print_info(f"Use 'coachntt memory show {memory['memory_id']}' to view updated details")
            
            elif result["status"] == "not_found":
                print_error(f"Memory not found: {memory_id}")
                print_info("Use 'coachntt memory list' to see available memories")
            
            elif result["status"] == "validation_error":
                print_error("Failed to update memory due to validation errors:")
                try:
                    import json
                    details = json.loads(result.get("details", "{}"))
                    if isinstance(details, dict) and "detail" in details:
                        if isinstance(details["detail"], list):
                            for error in details["detail"]:
                                print_error(f"  • {error.get('msg', error)}")
                        else:
                            print_error(f"  • {details['detail']}")
                    else:
                        print_error(f"  • {result.get('details', 'Unknown validation error')}")
                except:
                    print_error(f"  • {result.get('details', 'Unknown validation error')}")
            
            elif result["status"] == "error":
                print_error(f"Failed to update memory: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Verify memory ID is correct")
                print_info("3. Check network connectivity")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_update_memory())


@memory_command.command("delete")
@click.argument("memory_id")
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def delete_memory(memory_id: str, force: bool, debug: bool):
    """
    Delete a memory permanently.
    
    Permanently removes a memory from the system. This action cannot be undone.
    By default, you will be prompted for confirmation.
    
    Examples:
        coachntt memory delete abc123
        
        coachntt memory delete abc123 --force  # Skip confirmation
    """
    async def _run_delete_memory():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Deleting memory: {memory_id}")
            
            # Get memory details first for confirmation
            if not force:
                with show_spinner("Fetching memory details...") as progress:
                    task = progress.add_task(description="Loading memory...")
                    memory_result = await cli.get_memory(memory_id)
                    progress.update(task, description="Processing...")
                
                if memory_result["status"] == "success":
                    memory = memory_result["memory"]
                    memory_type = memory.get("memory_type", "unknown")
                    created_at = memory.get("created_at", "unknown")
                    
                    print_warning("⚠️  You are about to delete a memory permanently.")
                    print_info(f"Memory ID: {memory_id}")
                    print_info(f"Type: {memory_type}")
                    print_info(f"Created: {created_at}")
                    print_info(f"Prompt: {_truncate_text(memory.get('abstracted_prompt', ''), 60)}")
                    print()
                    
                    # Ask for confirmation
                    import click
                    if not click.confirm("Are you sure you want to delete this memory?"):
                        print_info("Delete operation cancelled")
                        return
                
                elif memory_result["status"] == "not_found":
                    print_error(f"Memory not found: {memory_id}")
                    print_info("Use 'coachntt memory list' to see available memories")
                    return
                
                else:
                    print_warning("Could not fetch memory details for confirmation")
                    print_info(f"Memory ID: {memory_id}")
                    
                    import click
                    if not click.confirm("Continue with deletion anyway?"):
                        print_info("Delete operation cancelled")
                        return
            
            # Show spinner for deletion
            with show_spinner("Deleting memory...") as progress:
                task = progress.add_task(description="Removing memory from system...")
                
                # Delete memory through API
                result = await cli.delete_memory(memory_id, force=force)
                
                progress.update(task, description="Processing result...")
            
            if result["status"] == "success":
                print_success("Memory deleted successfully!")
                print_info(f"Memory {memory_id} has been permanently removed")
                print_warning("This action cannot be undone")
            
            elif result["status"] == "not_found":
                print_error(f"Memory not found: {memory_id}")
                print_info("The memory may have already been deleted")
                print_info("Use 'coachntt memory list' to see available memories")
            
            elif result["status"] == "error":
                print_error(f"Failed to delete memory: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Verify memory ID is correct")
                print_info("3. Check network connectivity")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_delete_memory())


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