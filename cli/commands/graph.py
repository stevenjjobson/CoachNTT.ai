"""
Knowledge graph commands for CoachNTT.ai CLI.

Provides commands for building, querying, exporting, and managing knowledge graphs
with safety-first design and comprehensive output formatting.
"""

import click
import json
import os
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
    format_duration,
    confirm_action
)


@click.group()
def graph_command():
    """
    Knowledge graph operations.
    
    Build, query, export, and manage knowledge graphs from your memories
    and code analysis. All operations maintain safety-first design with
    automatic abstraction of sensitive information.
    """
    pass


@graph_command.command("build")
@click.option(
    "--from-memories",
    is_flag=True,
    default=True,
    help="Build from recent memories (default: true)"
)
@click.option(
    "--from-code",
    type=click.Path(exists=True),
    help="Include code analysis from specified path"
)
@click.option(
    "--max-memories",
    type=int,
    default=100,
    help="Maximum memories to include (default: 100)"
)
@click.option(
    "--max-nodes",
    type=int,
    default=100,
    help="Maximum nodes in graph (default: 100)"
)
@click.option(
    "--similarity-threshold",
    type=float,
    default=0.7,
    help="Minimum similarity for edges (default: 0.7)"
)
@click.option(
    "--name",
    type=str,
    help="Name for the graph"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save graph metadata to file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def build_graph(
    from_memories: bool,
    from_code: Optional[str],
    max_memories: int,
    max_nodes: int,
    similarity_threshold: float,
    name: Optional[str],
    output: Optional[str],
    debug: bool
):
    """
    Build knowledge graph from memories and code analysis.
    
    Creates a comprehensive knowledge graph by analyzing your memories
    and optionally including code structure analysis. The graph uses
    semantic similarity to create connections between related concepts.
    
    Examples:
        coachntt graph build                           # Build from recent memories
        
        coachntt graph build \
          --from-code ./src \
          --max-nodes 200 \
          --name "API Architecture Graph"
        
        coachntt graph build \
          --similarity-threshold 0.8 \
          --max-memories 50 \
          --output graph-metadata.json
    """
    async def _run_build_graph():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Building graph: memories={from_memories}, code={from_code}")
            
            # Validate parameters
            if similarity_threshold < 0 or similarity_threshold > 1:
                print_error("Similarity threshold must be between 0.0 and 1.0")
                return
            
            if max_memories <= 0 or max_nodes <= 0:
                print_error("Max memories and max nodes must be positive")
                return
            
            # Prepare code paths if provided
            code_paths = None
            if from_code:
                if not os.path.exists(from_code):
                    print_error(f"Code path does not exist: {from_code}")
                    return
                code_paths = [from_code]
                if debug:
                    cli.debug_print(f"Including code analysis from: {from_code}")
            
            # Generate graph name if not provided
            graph_name = name or f"Graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Show spinner for graph building
            with show_spinner("Building knowledge graph...") as progress:
                task = progress.add_task(description="Analyzing memories and building connections...")
                
                # Build graph through API
                result = await cli.build_graph(
                    code_paths=code_paths,
                    max_memories=max_memories,
                    max_nodes=max_nodes,
                    similarity_threshold=similarity_threshold,
                    graph_name=graph_name,
                    include_related=True
                )
                
                progress.update(task, description="Finalizing graph structure...")
            
            if result["status"] == "success":
                graph = result["graph"]
                graph_id = graph.get("graph_id", "unknown")
                
                print_success(f"Knowledge graph built successfully!")
                print_info(f"Graph ID: {str(graph_id)[:8]}...")
                print_info(f"Name: {graph.get('name', 'Unnamed')}")
                
                # Show metrics if available
                if "metrics" in graph:
                    metrics = graph["metrics"]
                    print_info(f"Nodes: {metrics.get('node_count', 0)}")
                    print_info(f"Edges: {metrics.get('edge_count', 0)}")
                    print_info(f"Avg Safety Score: {metrics.get('average_safety_score', 0):.3f}")
                    
                    if "build_time_ms" in metrics:
                        build_time = metrics["build_time_ms"] / 1000
                        print_info(f"Build Time: {format_duration(build_time)}")
                
                # Save metadata if requested
                if output:
                    try:
                        with open(output, 'w') as f:
                            json.dump(graph, f, indent=2, default=str)
                        print_success(f"Graph metadata saved to {output}")
                    except Exception as e:
                        print_warning(f"Failed to save metadata: {e}")
                
                print()
                print_info("Next steps:")
                print_info(f"  • Query graph: coachntt graph query {graph_id}")
                print_info(f"  • Export graph: coachntt graph export {graph_id} mermaid")
                print_info(f"  • View details: coachntt graph show {graph_id}")
            
            elif result["status"] == "error":
                print_error(f"Failed to build graph: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check API status: coachntt status")
                print_info("2. Ensure sufficient memories exist")
                print_info("3. Verify code paths are accessible")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_build_graph())


@graph_command.command("list")
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
def list_graphs(output_format: str, debug: bool):
    """
    List available knowledge graphs.
    
    Shows all available knowledge graphs with their metadata,
    including node/edge counts, creation dates, and safety metrics.
    
    Examples:
        coachntt graph list                    # List all graphs
        coachntt graph list --format json     # JSON output for scripts
    """
    async def _run_list_graphs():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print("Listing available graphs")
            
            # Show spinner for API call
            with show_spinner("Fetching graphs...") as progress:
                task = progress.add_task(description="Querying graph repository...")
                
                result = await cli.list_graphs()
                
                progress.update(task, description="Processing results...")
            
            if result["status"] == "success":
                graphs = result["graphs"]
                total = result["total"]
                
                if not graphs:
                    print_info("No knowledge graphs found")
                    print_info("Create your first graph with: coachntt graph build")
                    return
                
                # Format graphs for display
                if output_format == "json":
                    cli.format_and_display(graphs, "json")
                else:
                    formatted_graphs = _format_graphs_for_display(graphs)
                    title = f"Knowledge Graphs ({total} total)"
                    cli.format_and_display(formatted_graphs, output_format, title)
                    
                    print_info(f"Use 'coachntt graph show <id>' to view graph details")
            
            elif result["status"] == "error":
                print_error(f"Failed to list graphs: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_list_graphs())


@graph_command.command("show")
@click.argument("graph_id")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['pretty', 'json']),
    default='pretty',
    help="Output format (default: pretty)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def show_graph(graph_id: str, output_format: str, debug: bool):
    """
    Display detailed information about a specific graph.
    
    Shows comprehensive graph metadata including structure statistics,
    safety metrics, and creation details.
    
    Examples:
        coachntt graph show abc123                # Show graph details
        coachntt graph show abc123 --format json # JSON output
    """
    async def _run_show_graph():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Showing graph: {graph_id}")
            
            # Show spinner for API call
            with show_spinner("Fetching graph details...") as progress:
                task = progress.add_task(description="Loading graph metadata...")
                
                result = await cli.get_graph(graph_id)
                
                progress.update(task, description="Processing details...")
            
            if result["status"] == "success":
                graph = result["graph"]
                
                if output_format == "json":
                    cli.format_and_display(graph, "json")
                else:
                    # Format for pretty display
                    formatted_graph = _format_graph_details(graph)
                    cli.format_and_display(
                        formatted_graph,
                        "table",
                        f"Graph Details: {str(graph.get('graph_id', ''))[:8]}..."
                    )
            
            elif result["status"] == "not_found":
                print_error(f"Graph not found: {graph_id}")
                print_info("Use 'coachntt graph list' to see available graphs")
            
            elif result["status"] == "error":
                print_error(f"Failed to fetch graph: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_show_graph())


@graph_command.command("query")
@click.argument("graph_id")
@click.option(
    "--pattern",
    type=str,
    help="Content pattern to search for in nodes"
)
@click.option(
    "--node-types",
    type=str,
    help="Filter by node types (comma-separated)"
)
@click.option(
    "--edge-types", 
    type=str,
    help="Filter by edge types (comma-separated)"
)
@click.option(
    "--min-safety",
    type=float,
    help="Minimum node safety score (0.0-1.0)"
)
@click.option(
    "--min-weight",
    type=float,
    help="Minimum edge weight (0.0-1.0)"
)
@click.option(
    "--max-nodes",
    type=int,
    default=50,
    help="Maximum nodes to return (default: 50)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['table', 'json', 'mermaid']),
    default='table',
    help="Output format (default: table)"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save results to file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def query_graph(
    graph_id: str,
    pattern: Optional[str],
    node_types: Optional[str],
    edge_types: Optional[str],
    min_safety: Optional[float],
    min_weight: Optional[float],
    max_nodes: int,
    output_format: str,
    output: Optional[str],
    debug: bool
):
    """
    Query knowledge graph with semantic and structural filters.
    
    Performs advanced queries on the knowledge graph using various filters
    to find relevant nodes and their connections.
    
    Examples:
        coachntt graph query abc123 --pattern "API design"
        
        coachntt graph query abc123 \
          --node-types memory,code \
          --min-safety 0.8 \
          --max-nodes 20
        
        coachntt graph query abc123 \
          --pattern "error handling" \
          --format mermaid \
          --output error-handling-graph.md
    """
    async def _run_query_graph():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Querying graph: {graph_id}")
            
            # Parse node and edge types
            node_types_list = None
            if node_types:
                node_types_list = [t.strip() for t in node_types.split(",")]
            
            edge_types_list = None
            if edge_types:
                edge_types_list = [t.strip() for t in edge_types.split(",")]
            
            # Validate parameters
            if min_safety is not None and (min_safety < 0 or min_safety > 1):
                print_error("Minimum safety score must be between 0.0 and 1.0")
                return
            
            if min_weight is not None and (min_weight < 0 or min_weight > 1):
                print_error("Minimum edge weight must be between 0.0 and 1.0")
                return
            
            if max_nodes <= 0:
                print_error("Max nodes must be positive")
                return
            
            # Show spinner for API call
            with show_spinner("Querying knowledge graph...") as progress:
                task = progress.add_task(description="Searching nodes and edges...")
                
                result = await cli.query_graph(
                    graph_id=graph_id,
                    node_types=node_types_list,
                    edge_types=edge_types_list,
                    min_node_safety_score=min_safety,
                    min_edge_weight=min_weight,
                    node_content_pattern=pattern,
                    max_nodes=max_nodes
                )
                
                progress.update(task, description="Processing query results...")
            
            if result["status"] == "success":
                query_result = result["result"]
                nodes = query_result.get("nodes", [])
                edges = query_result.get("edges", [])
                query_time = query_result.get("query_time_ms", 0)
                
                if not nodes:
                    print_info("No nodes found matching your query criteria")
                    print_info("Try:")
                    print_info("  • Broadening your search pattern")
                    print_info("  • Removing or adjusting filters")
                    print_info("  • Increasing max-nodes limit")
                    return
                
                # Format and display results
                if output_format == "json":
                    output_data = query_result
                elif output_format == "mermaid":
                    output_data = _format_query_as_mermaid(nodes, edges)
                else:  # table format
                    output_data = _format_query_results_for_display(nodes, edges)
                
                if output and output_format != "table":
                    # Save to file for non-table formats
                    try:
                        with open(output, 'w') as f:
                            if output_format == "json":
                                json.dump(output_data, f, indent=2, default=str)
                            else:  # mermaid
                                f.write(output_data)
                        print_success(f"Query results saved to {output}")
                    except Exception as e:
                        print_error(f"Failed to save results: {e}")
                        return
                else:
                    # Display on screen
                    if output_format == "mermaid":
                        print(output_data)
                    else:
                        title = f"Query Results for {graph_id[:8]}... ({len(nodes)} nodes, {len(edges)} edges)"
                        cli.format_and_display(output_data, "table", title)
                
                # Show query statistics
                print_info(f"Query completed in {query_time:.1f}ms")
                print_info(f"Found {len(nodes)} nodes and {len(edges)} edges")
                
                # Show filters applied
                filters = []
                if pattern:
                    filters.append(f"pattern='{pattern}'")
                if node_types_list:
                    filters.append(f"node_types={','.join(node_types_list)}")
                if min_safety:
                    filters.append(f"min_safety={min_safety}")
                if filters:
                    print_info(f"Filters: {', '.join(filters)}")
            
            elif result["status"] == "not_found":
                print_error(f"Graph not found: {graph_id}")
                print_info("Use 'coachntt graph list' to see available graphs")
            
            elif result["status"] == "error":
                print_error(f"Failed to query graph: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_query_graph())


@graph_command.command("export")
@click.argument("graph_id")
@click.argument("format_type", type=click.Choice(['mermaid', 'json', 'd3', 'cytoscape', 'graphml']))
@click.option(
    "--output",
    type=click.Path(),
    required=True,
    help="Output file path (required)"
)
@click.option(
    "--max-nodes",
    type=int,
    help="Maximum nodes to export"
)
@click.option(
    "--min-centrality",
    type=float,
    help="Filter by minimum centrality score"
)
@click.option(
    "--include-metadata",
    is_flag=True,
    help="Include node/edge metadata"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def export_graph(
    graph_id: str,
    format_type: str,
    output: str,
    max_nodes: Optional[int],
    min_centrality: Optional[float],
    include_metadata: bool,
    debug: bool
):
    """
    Export knowledge graph in various formats.
    
    Exports the graph in multiple formats suitable for visualization,
    analysis, or integration with other tools.
    
    Examples:
        coachntt graph export abc123 mermaid --output graph.md
        
        coachntt graph export abc123 d3 \
          --output graph.json \
          --max-nodes 50 \
          --include-metadata
        
        coachntt graph export abc123 graphml \
          --output analysis.graphml \
          --min-centrality 0.5
    """
    async def _run_export_graph():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Exporting graph {graph_id} to {format_type}")
            
            # Validate parameters
            if min_centrality is not None and (min_centrality < 0 or min_centrality > 1):
                print_error("Minimum centrality must be between 0.0 and 1.0")
                return
            
            if max_nodes is not None and max_nodes <= 0:
                print_error("Max nodes must be positive")
                return
            
            # Check output directory exists
            output_dir = os.path.dirname(output)
            if output_dir and not os.path.exists(output_dir):
                print_error(f"Output directory does not exist: {output_dir}")
                return
            
            # Show spinner for export
            with show_spinner("Exporting knowledge graph...") as progress:
                task = progress.add_task(description=f"Generating {format_type.upper()} export...")
                
                result = await cli.export_graph(
                    graph_id=graph_id,
                    format_type=format_type,
                    output_file=output,
                    max_nodes=max_nodes,
                    filter_by_centrality=min_centrality,
                    include_metadata=include_metadata
                )
                
                progress.update(task, description="Finalizing export...")
            
            if result["status"] == "success":
                export_data = result["export"]
                content = result["content"]
                
                # Write content to file
                try:
                    with open(output, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print_success(f"Graph exported successfully!")
                    print_info(f"Format: {format_type.upper()}")
                    print_info(f"Output: {output}")
                    
                    # Show export statistics
                    if "node_count" in export_data:
                        print_info(f"Nodes: {export_data['node_count']}")
                    if "edge_count" in export_data:
                        print_info(f"Edges: {export_data['edge_count']}")
                    if "export_time_ms" in export_data:
                        export_time = export_data["export_time_ms"] / 1000
                        print_info(f"Export Time: {format_duration(export_time)}")
                    
                    # Show file info
                    file_size = os.path.getsize(output)
                    if file_size < 1024:
                        size_str = f"{file_size} bytes"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size // 1024} KB"
                    else:
                        size_str = f"{file_size // (1024 * 1024)} MB"
                    print_info(f"File Size: {size_str}")
                    
                    # Show filters applied
                    filters = []
                    if max_nodes:
                        filters.append(f"max_nodes={max_nodes}")
                    if min_centrality:
                        filters.append(f"min_centrality={min_centrality}")
                    if include_metadata:
                        filters.append("metadata=included")
                    if filters:
                        print_info(f"Filters: {', '.join(filters)}")
                    
                    # Show safety validation status
                    if export_data.get("safety_validated"):
                        print_success("Content safety validated")
                    else:
                        print_warning("Safety validation inconclusive")
                
                except Exception as e:
                    print_error(f"Failed to write export to {output}: {e}")
            
            elif result["status"] == "not_found":
                print_error(f"Graph not found: {graph_id}")
                print_info("Use 'coachntt graph list' to see available graphs")
            
            elif result["status"] == "error":
                print_error(f"Failed to export graph: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_export_graph())


@graph_command.command("subgraph")
@click.argument("graph_id")
@click.argument("center_node_id")
@click.option(
    "--max-depth",
    type=int,
    default=3,
    help="Maximum traversal depth (default: 3)"
)
@click.option(
    "--max-nodes",
    type=int,
    default=50,
    help="Maximum nodes to include (default: 50)"
)
@click.option(
    "--min-weight",
    type=float,
    default=0.1,
    help="Minimum edge weight (default: 0.1)"
)
@click.option(
    "--edge-types",
    type=str,
    help="Edge types to include (comma-separated)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['table', 'json', 'mermaid']),
    default='table',
    help="Output format (default: table)"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save subgraph to file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def get_subgraph(
    graph_id: str,
    center_node_id: str,
    max_depth: int,
    max_nodes: int,
    min_weight: float,
    edge_types: Optional[str],
    output_format: str,
    output: Optional[str],
    debug: bool
):
    """
    Extract subgraph around a specific node.
    
    Extracts a focused subgraph by traversing from a center node
    to a specified depth, useful for exploring local neighborhoods
    in the knowledge graph.
    
    Examples:
        coachntt graph subgraph abc123 node456 --max-depth 2
        
        coachntt graph subgraph abc123 node456 \
          --max-depth 3 \
          --max-nodes 30 \
          --format mermaid \
          --output subgraph.md
    """
    async def _run_get_subgraph():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Extracting subgraph from {graph_id} around {center_node_id}")
            
            # Parse edge types
            edge_types_list = None
            if edge_types:
                edge_types_list = [t.strip() for t in edge_types.split(",")]
            
            # Validate parameters
            if max_depth <= 0 or max_nodes <= 0:
                print_error("Max depth and max nodes must be positive")
                return
            
            if min_weight < 0 or min_weight > 1:
                print_error("Minimum edge weight must be between 0.0 and 1.0")
                return
            
            # Show spinner for subgraph extraction
            with show_spinner("Extracting subgraph...") as progress:
                task = progress.add_task(description="Traversing graph from center node...")
                
                result = await cli.get_subgraph(
                    graph_id=graph_id,
                    center_node_id=center_node_id,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    min_edge_weight=min_weight,
                    include_edge_types=edge_types_list
                )
                
                progress.update(task, description="Building subgraph structure...")
            
            if result["status"] == "success":
                subgraph = result["subgraph"]
                nodes = subgraph.get("nodes", [])
                edges = subgraph.get("edges", [])
                query_time = subgraph.get("query_time_ms", 0)
                
                if not nodes:
                    print_info("No nodes found in subgraph")
                    print_info("Try:")
                    print_info("  • Increasing max-depth")
                    print_info("  • Reducing min-weight threshold")
                    print_info("  • Checking center node ID is correct")
                    return
                
                # Format and display results
                if output_format == "json":
                    output_data = subgraph
                elif output_format == "mermaid":
                    output_data = _format_query_as_mermaid(nodes, edges)
                else:  # table format
                    output_data = _format_query_results_for_display(nodes, edges)
                
                if output and output_format != "table":
                    # Save to file
                    try:
                        with open(output, 'w') as f:
                            if output_format == "json":
                                json.dump(output_data, f, indent=2, default=str)
                            else:  # mermaid
                                f.write(output_data)
                        print_success(f"Subgraph saved to {output}")
                    except Exception as e:
                        print_error(f"Failed to save subgraph: {e}")
                        return
                else:
                    # Display on screen
                    if output_format == "mermaid":
                        print(output_data)
                    else:
                        title = f"Subgraph around {center_node_id[:8]}... ({len(nodes)} nodes, {len(edges)} edges)"
                        cli.format_and_display(output_data, "table", title)
                
                # Show extraction statistics
                print_info(f"Extraction completed in {query_time:.1f}ms")
                print_info(f"Center: {center_node_id[:8]}...")
                print_info(f"Depth: {max_depth}, Nodes: {len(nodes)}, Edges: {len(edges)}")
            
            elif result["status"] == "not_found":
                print_error(f"Graph or center node not found")
                print_info("Check that both graph ID and center node ID are correct")
            
            elif result["status"] == "error":
                print_error(f"Failed to extract subgraph: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_get_subgraph())


@graph_command.command("delete")
@click.argument("graph_id")
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
def delete_graph(graph_id: str, force: bool, debug: bool):
    """
    Delete a knowledge graph permanently.
    
    Permanently removes a knowledge graph and all associated data.
    This action cannot be undone. By default, you will be prompted
    for confirmation.
    
    Examples:
        coachntt graph delete abc123              # Delete with confirmation
        coachntt graph delete abc123 --force     # Delete without confirmation
    """
    async def _run_delete_graph():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Deleting graph: {graph_id}")
            
            # Get graph details first for confirmation
            if not force:
                with show_spinner("Fetching graph details...") as progress:
                    task = progress.add_task(description="Loading graph...")
                    graph_result = await cli.get_graph(graph_id)
                    progress.update(task, description="Processing...")
                
                if graph_result["status"] == "success":
                    graph = graph_result["graph"]
                    graph_name = graph.get("name", "Unnamed")
                    created_at = graph.get("created_at", "unknown")
                    
                    print_warning("⚠️  You are about to delete a knowledge graph permanently.")
                    print_info(f"Graph ID: {graph_id}")
                    print_info(f"Name: {graph_name}")
                    print_info(f"Created: {created_at}")
                    
                    if "metrics" in graph:
                        metrics = graph["metrics"]
                        print_info(f"Nodes: {metrics.get('node_count', 0)}")
                        print_info(f"Edges: {metrics.get('edge_count', 0)}")
                    
                    print()
                    
                    # Ask for confirmation
                    if not confirm_action("Are you sure you want to delete this graph?"):
                        print_info("Delete operation cancelled")
                        return
                
                elif graph_result["status"] == "not_found":
                    print_error(f"Graph not found: {graph_id}")
                    print_info("Use 'coachntt graph list' to see available graphs")
                    return
                
                else:
                    print_warning("Could not fetch graph details for confirmation")
                    print_info(f"Graph ID: {graph_id}")
                    
                    if not confirm_action("Continue with deletion anyway?"):
                        print_info("Delete operation cancelled")
                        return
            
            # Show spinner for deletion
            with show_spinner("Deleting graph...") as progress:
                task = progress.add_task(description="Removing graph from system...")
                
                result = await cli.delete_graph(graph_id)
                
                progress.update(task, description="Processing result...")
            
            if result["status"] == "success":
                print_success("Knowledge graph deleted successfully!")
                print_info(f"Graph {graph_id} has been permanently removed")
                print_warning("This action cannot be undone")
            
            elif result["status"] == "not_found":
                print_error(f"Graph not found: {graph_id}")
                print_info("The graph may have already been deleted")
                print_info("Use 'coachntt graph list' to see available graphs")
            
            elif result["status"] == "error":
                print_error(f"Failed to delete graph: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_delete_graph())


def _format_graphs_for_display(graphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format graphs for table display."""
    formatted = []
    
    for graph in graphs:
        formatted_graph = {
            "ID": str(graph.get("graph_id", ""))[:8] + "...",
            "Name": graph.get("name", "Unnamed")[:30],
            "Nodes": graph.get("node_count", 0),
            "Edges": graph.get("edge_count", 0),
            "Safety": f"{float(graph.get('average_safety_score', 0)):.2f}",
            "Created": _format_relative_time(graph.get("created_at"))
        }
        formatted.append(formatted_graph)
    
    return formatted


def _format_graph_details(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Format single graph for detailed display."""
    details = {
        "Graph ID": str(graph.get("graph_id", "")),
        "Name": graph.get("name", "Unnamed"),
        "Description": graph.get("description", "No description"),
        "Created": graph.get("created_at", "unknown"),
        "Updated": graph.get("updated_at", "unknown")
    }
    
    # Add metrics if available
    if "metrics" in graph:
        metrics = graph["metrics"]
        details.update({
            "Node Count": metrics.get("node_count", 0),
            "Edge Count": metrics.get("edge_count", 0),
            "Average Safety Score": f"{float(metrics.get('average_safety_score', 0)):.3f}",
            "Density": f"{float(metrics.get('density', 0)):.3f}",
            "Avg Clustering": f"{float(metrics.get('average_clustering', 0)):.3f}"
        })
    
    return details


def _format_query_results_for_display(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format query results for table display."""
    formatted = []
    
    # Format nodes
    for node in nodes:
        formatted_node = {
            "Type": "Node",
            "ID": str(node.get("node_id", ""))[:8] + "...",
            "Node Type": node.get("node_type", "unknown"),
            "Title": _truncate_text(node.get("title_pattern", ""), 25),
            "Safety": f"{float(node.get('safety_score', 0)):.2f}",
            "Centrality": f"{float(node.get('centrality_score', 0) or 0):.2f}",
            "Source": node.get("source_type", "unknown")
        }
        formatted.append(formatted_node)
    
    # Format edges
    for edge in edges:
        formatted_edge = {
            "Type": "Edge",
            "ID": str(edge.get("edge_id", ""))[:8] + "...",
            "Edge Type": edge.get("edge_type", "unknown"),
            "Weight": f"{float(edge.get('weight', 0)):.2f}",
            "Confidence": f"{float(edge.get('confidence', 0)):.2f}",
            "Source": str(edge.get("source_node_id", ""))[:8] + "...",
            "Target": str(edge.get("target_node_id", ""))[:8] + "..."
        }
        formatted.append(formatted_edge)
    
    return formatted


def _format_query_as_mermaid(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """Format query results as Mermaid diagram."""
    lines = ["graph TD"]
    
    # Add nodes
    for node in nodes:
        node_id = str(node.get("node_id", ""))[:8]
        title = _truncate_text(node.get("title_pattern", "Node"), 15)
        node_type = node.get("node_type", "unknown")
        
        # Choose node shape based on type
        if node_type == "memory":
            shape = f'["{title}"]'
        elif node_type == "code":
            shape = f'{{{title}}}'
        else:
            shape = f'("{title}")'
        
        lines.append(f'    {node_id}{shape}')
    
    # Add edges
    for edge in edges:
        source = str(edge.get("source_node_id", ""))[:8]
        target = str(edge.get("target_node_id", ""))[:8]
        edge_type = edge.get("edge_type", "related")
        weight = float(edge.get("weight", 0))
        
        # Choose arrow style based on edge type and weight
        if weight > 0.8:
            arrow = " ==> "
        elif weight > 0.5:
            arrow = " --> "
        else:
            arrow = " -.-> "
        
        lines.append(f'    {source}{arrow}{target}')
    
    return '\n'.join(lines)


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
__all__ = ["graph_command"]