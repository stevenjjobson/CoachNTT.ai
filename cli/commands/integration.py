"""
Integration commands for CoachNTT.ai CLI.

Provides commands for integration with external services including vault sync,
documentation generation, and checkpoint management with safety-first design.
"""

import click
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

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
def sync_command():
    """
    Synchronization operations.
    
    Bidirectional synchronization with external services like Obsidian vault,
    maintaining safety-first design with automatic abstraction.
    """
    pass


@sync_command.command("vault")
@click.option(
    "--direction",
    type=click.Choice(['both', 'to-vault', 'from-vault']),
    default='both',
    help="Sync direction (default: both)"
)
@click.option(
    "--template",
    type=click.Choice(['learning', 'decision', 'checkpoint', 'debug']),
    help="Template type for memory conversion"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be synced without making changes"
)
@click.option(
    "--max-memories",
    type=int,
    default=100,
    help="Maximum memories to process (default: 100)"
)
@click.option(
    "--vault-files",
    type=str,
    help="Specific vault files to sync (comma-separated paths)"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save sync report to file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def sync_vault(
    direction: str,
    template: Optional[str],
    dry_run: bool,
    max_memories: int,
    vault_files: Optional[str],
    output: Optional[str],
    debug: bool
):
    """
    Bidirectional synchronization with Obsidian vault.
    
    Synchronizes memories to/from Obsidian vault with configurable templates,
    conflict resolution, and safety validation.
    
    Examples:
        coachntt sync vault                          # Bidirectional sync
        
        coachntt sync vault --direction to-vault     # Sync memories to vault only
          --template learning
        
        coachntt sync vault --dry-run               # Preview changes
          --max-memories 50
    """
    async def _run_sync_vault():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Vault sync: direction={direction}, template={template}")
            
            # Validate parameters
            if max_memories <= 0:
                print_error("Max memories must be positive")
                return
            
            # Parse vault files if provided
            vault_file_list = None
            if vault_files:
                vault_file_list = [f.strip() for f in vault_files.split(",")]
                if debug:
                    cli.debug_print(f"Vault files: {vault_file_list}")
            
            # Show what will be done
            if dry_run:
                print_info("🔍 Dry run mode - no changes will be made")
                print_info(f"Direction: {direction}")
                print_info(f"Template: {template or 'default'}")
                print_info(f"Max memories: {max_memories}")
                if vault_file_list:
                    print_info(f"Vault files: {len(vault_file_list)} specified")
            
            # Show spinner for sync operation
            operation_desc = "Dry run analysis" if dry_run else "Vault synchronization"
            with show_spinner(f"Running {operation_desc}...") as progress:
                task = progress.add_task(description="Preparing sync operation...")
                
                # Call vault sync API
                result = await cli.sync_vault(
                    direction=direction,
                    template_type=template,
                    max_memories=max_memories,
                    vault_files=vault_file_list,
                    dry_run=dry_run
                )
                
                progress.update(task, description="Processing sync results...")
            
            if result["status"] == "success":
                sync_data = result["sync"]
                
                if dry_run:
                    print_success("Dry run completed successfully!")
                    print_info("Changes that would be made:")
                else:
                    print_success("Vault synchronization completed!")
                
                # Show sync statistics
                print_info(f"Direction: {sync_data.get('sync_direction', direction)}")
                print_info(f"Notes processed: {sync_data.get('notes_processed', 0)}")
                print_info(f"Notes created: {sync_data.get('notes_created', 0)}")
                print_info(f"Notes updated: {sync_data.get('notes_updated', 0)}")
                print_info(f"Notes skipped: {sync_data.get('notes_skipped', 0)}")
                
                # Show conflicts and safety info
                conflicts = sync_data.get('conflicts_detected', 0)
                if conflicts > 0:
                    print_warning(f"Conflicts detected: {conflicts}")
                    print_info(f"Conflicts resolved: {sync_data.get('conflicts_resolved', 0)}")
                
                safety_violations = sync_data.get('safety_violations', 0)
                if safety_violations > 0:
                    print_warning(f"Safety violations: {safety_violations}")
                else:
                    print_success("No safety violations detected")
                
                avg_safety = sync_data.get('average_safety_score', 0)
                print_info(f"Average safety score: {avg_safety:.3f}")
                
                # Show timing
                if "processing_time_ms" in sync_data:
                    sync_time = sync_data["processing_time_ms"] / 1000
                    print_info(f"Sync time: {format_duration(sync_time)}")
                
                # Show errors and warnings
                errors = sync_data.get('errors', [])
                warnings = sync_data.get('warnings', [])
                
                if errors:
                    print_error(f"Errors ({len(errors)}):")
                    for error in errors[:3]:  # Show first 3 errors
                        print_error(f"  • {error}")
                    if len(errors) > 3:
                        print_error(f"  ... and {len(errors) - 3} more")
                
                if warnings:
                    print_warning(f"Warnings ({len(warnings)}):")
                    for warning in warnings[:3]:  # Show first 3 warnings
                        print_warning(f"  • {warning}")
                    if len(warnings) > 3:
                        print_warning(f"  ... and {len(warnings) - 3} more")
                
                # Save report if requested
                if output:
                    try:
                        with open(output, 'w') as f:
                            json.dump(sync_data, f, indent=2, default=str)
                        print_success(f"Sync report saved to {output}")
                    except Exception as e:
                        print_warning(f"Failed to save report: {e}")
                
                # Show next steps
                if not dry_run and sync_data.get('success', False):
                    print()
                    print_info("Next steps:")
                    if direction in ['both', 'to-vault']:
                        print_info("  • Check your Obsidian vault for new/updated notes")
                    if direction in ['both', 'from-vault']:
                        print_info("  • Review imported memories: coachntt memory list")
                    if conflicts > 0:
                        print_info("  • Review conflict resolution in vault")
            
            elif result["status"] == "error":
                print_error(f"Vault sync failed: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check vault path configuration")
                print_info("2. Ensure vault is accessible and writable")
                print_info("3. Verify API connectivity: coachntt status")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_sync_vault())


@click.group()
def docs_command():
    """
    Documentation generation operations.
    
    Generate comprehensive project documentation from code analysis
    and memory insights with safety-first design.
    """
    pass


@docs_command.command("generate")
@click.option(
    "--types",
    type=str,
    default="readme,api,architecture,changelog",
    help="Documentation types (comma-separated, default: all)"
)
@click.option(
    "--output",
    type=click.Path(),
    default="./docs",
    help="Output directory (default: ./docs)"
)
@click.option(
    "--include-diagrams",
    is_flag=True,
    help="Generate architecture diagrams"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(['markdown', 'html']),
    default='markdown',
    help="Output format (default: markdown)"
)
@click.option(
    "--code-paths",
    type=str,
    help="Code paths to analyze (comma-separated)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def generate_docs(
    types: str,
    output: str,
    include_diagrams: bool,
    output_format: str,
    code_paths: Optional[str],
    debug: bool
):
    """
    Generate comprehensive project documentation.
    
    Creates documentation from code analysis including README, API docs,
    architecture diagrams, and changelogs with safety validation.
    
    Examples:
        coachntt docs generate                      # Generate all documentation
        
        coachntt docs generate --types api         # Generate only API docs
          --output ./api-docs
        
        coachntt docs generate --include-diagrams  # Generate with diagrams
          --format html
    """
    async def _run_generate_docs():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Generating docs: types={types}, output={output}")
            
            # Parse documentation types
            doc_types = [t.strip() for t in types.split(",")]
            valid_types = ["readme", "api", "architecture", "changelog", "coverage"]
            
            invalid_types = [t for t in doc_types if t not in valid_types]
            if invalid_types:
                print_error(f"Invalid documentation types: {', '.join(invalid_types)}")
                print_info(f"Valid types: {', '.join(valid_types)}")
                return
            
            # Parse code paths if provided
            code_path_list = None
            if code_paths:
                code_path_list = [p.strip() for p in code_paths.split(",")]
                # Validate paths exist
                for path in code_path_list:
                    if not os.path.exists(path):
                        print_error(f"Code path does not exist: {path}")
                        return
            
            # Create output directory if needed
            output_path = Path(output)
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print_error(f"Failed to create output directory: {e}")
                return
            
            # Show spinner for documentation generation
            with show_spinner("Generating documentation...") as progress:
                task = progress.add_task(description="Analyzing code and preparing documentation...")
                
                # Call docs generation API
                result = await cli.generate_docs(
                    doc_types=doc_types,
                    output_directory=str(output_path),
                    include_diagrams=include_diagrams,
                    output_format=output_format,
                    code_paths=code_path_list
                )
                
                progress.update(task, description="Finalizing documentation files...")
            
            if result["status"] == "success":
                docs_data = result["docs"]
                
                print_success("Documentation generated successfully!")
                print_info(f"Output directory: {output}")
                print_info(f"Format: {output_format.upper()}")
                
                # Show generated files
                generated_files = docs_data.get("files_generated", [])
                if generated_files:
                    print_info(f"Files generated ({len(generated_files)}):")
                    for file_info in generated_files:
                        file_path = file_info.get("file_path", "unknown")
                        doc_type = file_info.get("doc_type", "unknown")
                        size_bytes = file_info.get("size_bytes", 0)
                        
                        # Format file size
                        if size_bytes < 1024:
                            size_str = f"{size_bytes}B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes // 1024}KB"
                        else:
                            size_str = f"{size_bytes // (1024 * 1024)}MB"
                        
                        safety_status = "✅" if file_info.get("safety_validated") else "⚠️"
                        print_info(f"  {safety_status} {doc_type}: {file_path} ({size_str})")
                
                # Show statistics
                files_analyzed = docs_data.get("files_analyzed", 0)
                total_size = docs_data.get("total_size_bytes", 0)
                coverage = docs_data.get("coverage_percentage", 0)
                safety_score = docs_data.get("safety_score", 0)
                
                print_info(f"Files analyzed: {files_analyzed}")
                print_info(f"Total size: {total_size:,} bytes")
                print_info(f"Coverage: {coverage:.1f}%")
                print_info(f"Safety score: {safety_score:.3f}")
                
                # Show timing
                if "processing_time_ms" in docs_data:
                    gen_time = docs_data["processing_time_ms"] / 1000
                    print_info(f"Generation time: {format_duration(gen_time)}")
                
                # Show errors and warnings
                errors = docs_data.get('errors', [])
                warnings = docs_data.get('warnings', [])
                
                if errors:
                    print_error(f"Errors ({len(errors)}):")
                    for error in errors:
                        print_error(f"  • {error}")
                
                if warnings:
                    print_warning(f"Warnings ({len(warnings)}):")
                    for warning in warnings:
                        print_warning(f"  • {warning}")
                
                # Show next steps
                print()
                print_info("Next steps:")
                print_info(f"  • Review generated documentation in {output}")
                if include_diagrams:
                    print_info("  • Check architecture diagrams for accuracy")
                if output_format == "html":
                    print_info("  • Open HTML files in browser for viewing")
            
            elif result["status"] == "error":
                print_error(f"Documentation generation failed: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check output directory permissions")
                print_info("2. Ensure code paths are accessible")
                print_info("3. Verify API connectivity: coachntt status")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_generate_docs())


@click.group()
def checkpoint_command():
    """
    Development checkpoint operations.
    
    Create development checkpoints with git state capture and analysis
    for project milestone tracking.
    """
    pass


@checkpoint_command.command("create")
@click.argument("name")
@click.option(
    "--description",
    type=str,
    help="Checkpoint description"
)
@click.option(
    "--include-analysis",
    is_flag=True,
    help="Include code complexity analysis"
)
@click.option(
    "--max-memories",
    type=int,
    default=50,
    help="Maximum memories to include (default: 50)"
)
@click.option(
    "--memory-filters",
    type=str,
    help="Memory filters (comma-separated key=value pairs)"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save checkpoint report to file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug output"
)
def create_checkpoint(
    name: str,
    description: Optional[str],
    include_analysis: bool,
    max_memories: int,
    memory_filters: Optional[str],
    output: Optional[str],
    debug: bool
):
    """
    Create development checkpoint with git state and analysis.
    
    Creates a comprehensive checkpoint including current memories,
    git state, and optionally code complexity analysis.
    
    Examples:
        coachntt checkpoint create "API Implementation Complete"
        
        coachntt checkpoint create "Session 4.2 Complete"     # Detailed checkpoint
          --description "CLI interface implementation finished"
          --include-analysis
    """
    async def _run_create_checkpoint():
        config = CLIConfig.load_from_env()
        if debug:
            config.debug = True
        
        async with CLIEngine(config) as cli:
            if debug:
                cli.debug_print(f"Creating checkpoint: {name}")
            
            # Validate parameters
            if max_memories <= 0:
                print_error("Max memories must be positive")
                return
            
            if not name.strip():
                print_error("Checkpoint name cannot be empty")
                return
            
            # Parse memory filters if provided
            filters_dict = {}
            if memory_filters:
                try:
                    for filter_pair in memory_filters.split(","):
                        key, value = filter_pair.strip().split("=", 1)
                        filters_dict[key.strip()] = value.strip()
                except ValueError:
                    print_error("Invalid memory filters format. Use key=value,key2=value2")
                    return
                
                if debug:
                    cli.debug_print(f"Memory filters: {filters_dict}")
            
            print_info(f"Creating checkpoint: '{name}'")
            if description:
                print_info(f"Description: {description}")
            print_info(f"Max memories: {max_memories}")
            if include_analysis:
                print_info("Including code analysis")
            
            # Show spinner for checkpoint creation
            with show_spinner("Creating checkpoint...") as progress:
                task = progress.add_task(description="Capturing current state...")
                
                # Call checkpoint creation API
                result = await cli.create_checkpoint(
                    checkpoint_name=name,
                    description=description,
                    include_code_analysis=include_analysis,
                    max_memories=max_memories,
                    memory_filters=filters_dict
                )
                
                progress.update(task, description="Finalizing checkpoint...")
            
            if result["status"] == "success":
                checkpoint_data = result["checkpoint"]
                
                print_success("Checkpoint created successfully!")
                
                # Show checkpoint details
                checkpoint_id = checkpoint_data.get("checkpoint_id", "unknown")
                print_info(f"Checkpoint ID: {str(checkpoint_id)[:8]}...")
                print_info(f"Name: {checkpoint_data.get('name', name)}")
                if description:
                    print_info(f"Description: {checkpoint_data.get('description', description)}")
                print_info(f"Created: {checkpoint_data.get('created_at', 'unknown')}")
                
                # Show statistics
                memories_included = checkpoint_data.get("memories_included", 0)
                files_analyzed = checkpoint_data.get("files_analyzed", 0)
                safety_score = checkpoint_data.get("safety_score", 0)
                
                print_info(f"Memories included: {memories_included}")
                if include_analysis:
                    print_info(f"Files analyzed: {files_analyzed}")
                print_info(f"Safety score: {safety_score:.3f}")
                
                # Show timing
                if "processing_time_ms" in checkpoint_data:
                    checkpoint_time = checkpoint_data["processing_time_ms"] / 1000
                    print_info(f"Creation time: {format_duration(checkpoint_time)}")
                
                # Save checkpoint report if requested
                if output:
                    try:
                        with open(output, 'w') as f:
                            json.dump(checkpoint_data, f, indent=2, default=str)
                        print_success(f"Checkpoint report saved to {output}")
                    except Exception as e:
                        print_warning(f"Failed to save report: {e}")
                
                # Show next steps
                print()
                print_info("Next steps:")
                print_info(f"  • View checkpoint details with ID: {str(checkpoint_id)[:8]}...")
                print_info("  • Use checkpoint for rollback if needed")
                if include_analysis:
                    print_info("  • Review code analysis results")
            
            elif result["status"] == "error":
                print_error(f"Checkpoint creation failed: {result['message']}")
                if debug and "details" in result:
                    print_error(f"Details: {result['details']}")
                
                # Suggest troubleshooting
                print_info("Troubleshooting:")
                print_info("1. Check git repository status")
                print_info("2. Ensure sufficient memories exist")
                print_info("3. Verify API connectivity: coachntt status")
            
            else:
                print_error(f"Unexpected response status: {result['status']}")
    
    run_async_command(_run_create_checkpoint())


# Export commands for registration
__all__ = ["sync_command", "docs_command", "checkpoint_command"]