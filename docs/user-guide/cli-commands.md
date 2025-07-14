# CoachNTT.ai CLI User Guide

A comprehensive command-line interface for the Cognitive Coding Partner, providing immediate access to memory management, knowledge graphs, and automation features.

## Quick Start

### Installation & Setup

1. **Ensure API is running**:
```bash
# Start the FastAPI server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Verify CLI installation**:
```bash
# Check CLI is available
python coachntt.py --help

# Check system status
python coachntt.py status
```

### First Commands to Try

```bash
# See system health and API connectivity
python coachntt.py status

# List your recent memories
python coachntt.py memory list

# Get help for any command
python coachntt.py memory --help
```

### Configuration

The CLI uses the same configuration as the API server. Ensure your `.env` file is properly configured with database and API settings.

---

## System Commands

### `coachntt --help`
✅ **Status**: Implemented  
**Description**: Show all available commands with brief descriptions

```bash
python coachntt.py --help
```

**Output**: Clean, organized help text showing command groups and usage patterns

---

### `coachntt status`
✅ **Status**: Implemented  
**Description**: Display system health, API connectivity, and safety metrics

```bash
python coachntt.py status [OPTIONS]
```

**Options**:
- `--json` - Output as JSON for scripting
- `--detailed` - Include detailed performance metrics

**Examples**:
```bash
# Basic status check
python coachntt.py status

# Detailed status with metrics
python coachntt.py status --detailed

# JSON output for scripts
python coachntt.py status --json
```

**Output**: 
- API server connectivity and response time
- Database connection status
- Safety validation metrics
- Memory system statistics
- Performance indicators

---

### `coachntt version`
✅ **Status**: Implemented  
**Description**: Show version information and component status

```bash
python coachntt.py version [OPTIONS]
```

**Options**:
- `--components` - Show detailed component versions

**Examples**:
```bash
# Basic version info
python coachntt.py version

# Detailed component information
python coachntt.py version --components
```

---

### `coachntt config`
🚧 **Status**: Planned for Session 4.2b  
**Description**: View and manage CLI configuration

```bash
python coachntt.py config [OPTIONS]
```

**Options**:
- `--show` - Display current configuration
- `--set key=value` - Set configuration value
- `--list` - List all available configuration keys

**Examples**:
```bash
# Show current configuration
python coachntt.py config --show

# Set API base URL
python coachntt.py config --set api_base_url=http://localhost:8000

# List available settings
python coachntt.py config --list
```

---

## Memory Management

### `coachntt memory list`
✅ **Status**: Implemented  
**Description**: List recent memories with safety abstraction

```bash
python coachntt.py memory list [OPTIONS]
```

**Options**:
- `--limit N` - Number of memories to show (default: 10, max: 50)
- `--type TYPE` - Filter by memory type (learning, decision, context, debug)
- `--since DAYS` - Show memories from last N days (default: 7)
- `--format json|table|simple` - Output format (default: table)

**Examples**:
```bash
# List 10 most recent memories
python coachntt.py memory list

# List 20 learning memories from last 3 days
python coachntt.py memory list --limit 20 --type learning --since 3

# Get JSON output for scripting
python coachntt.py memory list --format json --limit 5
```

**Output**: Safely abstracted memory content with IDs, types, creation dates, and relevance scores

---

### `coachntt memory create`
✅ **Status**: Implemented  
**Description**: Create new memory with automatic safety validation

```bash
python coachntt.py memory create PROMPT CONTENT [OPTIONS]
```

**Options**:
- `--type TYPE` - Memory type (learning, decision, context, debug, optimization)
- `--metadata KEY=VALUE` - Add metadata (can be used multiple times)
- `--intent TYPE` - Specify intent type for better categorization

**Examples**:
```bash
# Create a learning memory
python coachntt.py memory create "How to optimize database queries" "Use indexes and limit result sets"

# Create with metadata and specific type
python coachntt.py memory create \
  "API endpoint design" \
  "REST endpoints should follow resource naming" \
  --type learning \
  --metadata project=api \
  --metadata priority=high

# Create debug memory
python coachntt.py memory create \
  "Memory leak in service" \
  "Found memory leak in connection pool" \
  --type debug \
  --intent troubleshooting
```

---

### `coachntt memory search`
✅ **Status**: Implemented  
**Description**: Search memories using semantic similarity and filters

```bash
python coachntt.py memory search QUERY [OPTIONS]
```

**Options**:
- `--intent TYPE` - Filter by intent type
- `--type TYPE` - Filter by memory type
- `--limit N` - Number of results (default: 10, max: 50)
- `--min-score FLOAT` - Minimum relevance score (0.0-1.0)
- `--format json|table|simple` - Output format

**Examples**:
```bash
# Search for database-related memories
python coachntt.py memory search "database optimization"

# Search learning memories with high relevance
python coachntt.py memory search "API design" --type learning --min-score 0.8

# Search recent debugging memories
python coachntt.py memory search "error handling" --intent troubleshooting --limit 5
```

---

### `coachntt memory show`
✅ **Status**: Implemented  
**Description**: Display detailed information about a specific memory

```bash
python coachntt.py memory show MEMORY_ID [OPTIONS]
```

**Options**:
- `--format json|pretty` - Output format (default: pretty)
- `--include-related` - Show related memories and connections
- `--include-metadata` - Show all metadata fields

**Examples**:
```bash
# Show memory details
python coachntt.py memory show abc123

# Show with related memories
python coachntt.py memory show abc123 --include-related

# Get JSON for integration
python coachntt.py memory show abc123 --format json
```

---

### `coachntt memory export`
✅ **Status**: Implemented  
**Description**: Export memories to various formats

```bash
python coachntt.py memory export [OPTIONS]
```

**Options**:
- `--format json|csv|markdown` - Export format (default: json)
- `--output FILE` - Output file path (default: stdout)
- `--filter TYPE=VALUE` - Filter criteria (can be used multiple times)
- `--since DAYS` - Export memories from last N days
- `--include-metadata` - Include all metadata in export

**Examples**:
```bash
# Export recent memories to JSON
python coachntt.py memory export --format json --output memories.json

# Export learning memories to Markdown
python coachntt.py memory export \
  --format markdown \
  --filter type=learning \
  --output learning-notes.md

# Export CSV for analysis
python coachntt.py memory export \
  --format csv \
  --since 30 \
  --include-metadata \
  --output memory-analysis.csv
```

---

### `coachntt memory update`
✅ **Status**: Implemented  
**Description**: Update an existing memory's content or metadata

```bash
python coachntt.py memory update MEMORY_ID [OPTIONS]
```

**Options**:
- `--prompt TEXT` - Update the prompt text
- `--content TEXT` - Update the content text
- `--metadata KEY=VALUE` - Update metadata (can be used multiple times)

**Examples**:
```bash
# Update content only
python coachntt.py memory update abc123 --content "Updated content with new information"

# Update multiple fields
python coachntt.py memory update abc123 \
  --prompt "Updated prompt" \
  --content "Updated content" \
  --metadata priority=high \
  --metadata status=reviewed
```

---

### `coachntt memory delete`
✅ **Status**: Implemented  
**Description**: Delete a memory permanently with safety confirmations

```bash
python coachntt.py memory delete MEMORY_ID [OPTIONS]
```

**Options**:
- `--force` - Skip confirmation prompt

**Examples**:
```bash
# Delete with confirmation prompt
python coachntt.py memory delete abc123

# Delete without confirmation (use with caution)
python coachntt.py memory delete abc123 --force
```

---

## Knowledge Graph Operations

### `coachntt graph build`
🚧 **Status**: Planned for Session 4.2c  
**Description**: Build knowledge graph from memories and code analysis

```bash
python coachntt.py graph build [OPTIONS]
```

**Options**:
- `--from-memories` - Build from recent memories (default: true)
- `--from-code PATH` - Include code analysis from path
- `--max-nodes N` - Maximum nodes in graph (default: 100)
- `--output FILE` - Save graph data to file
- `--similarity-threshold FLOAT` - Minimum similarity for edges (default: 0.7)

**Examples**:
```bash
# Build graph from recent memories
python coachntt.py graph build

# Build comprehensive graph with code analysis
python coachntt.py graph build \
  --from-code ./src \
  --max-nodes 200 \
  --output knowledge-graph.json

# Build focused graph with high similarity
python coachntt.py graph build \
  --similarity-threshold 0.8 \
  --max-nodes 50
```

---

### `coachntt graph query`
🚧 **Status**: Planned for Session 4.2c  
**Description**: Query knowledge graph with semantic patterns

```bash
python coachntt.py graph query PATTERN [OPTIONS]
```

**Options**:
- `--format json|mermaid|table` - Output format (default: table)
- `--depth N` - Maximum traversal depth (default: 3)
- `--min-similarity FLOAT` - Minimum edge similarity (default: 0.5)
- `--output FILE` - Save results to file

**Examples**:
```bash
# Find API-related connections
python coachntt.py graph query "API design patterns"

# Deep traversal for error handling
python coachntt.py graph query "error handling" --depth 5

# Generate Mermaid diagram
python coachntt.py graph query "database" --format mermaid --output db-graph.md
```

---

### `coachntt graph export`
🚧 **Status**: Planned for Session 4.2c  
**Description**: Export knowledge graph in various formats

```bash
python coachntt.py graph export FORMAT [OPTIONS]
```

**Formats**: `mermaid`, `json`, `d3`, `cytoscape`, `graphml`

**Options**:
- `--output FILE` - Output file path (required)
- `--subgraph NODE` - Export subgraph around specific node
- `--max-depth N` - Maximum depth for subgraph (default: 3)
- `--include-metadata` - Include node/edge metadata

**Examples**:
```bash
# Export full graph as Mermaid
python coachntt.py graph export mermaid --output architecture.md

# Export D3-compatible JSON
python coachntt.py graph export d3 --output graph.json

# Export subgraph around specific topic
python coachntt.py graph export mermaid \
  --subgraph "API design" \
  --max-depth 2 \
  --output api-subgraph.md
```

---

### `coachntt graph visualize`
🚧 **Status**: Planned for Session 4.2c  
**Description**: Generate interactive visualizations of knowledge graph

```bash
python coachntt.py graph visualize [OPTIONS]
```

**Options**:
- `--format mermaid|d3|html` - Visualization format (default: mermaid)
- `--output FILE` - Save visualization to file
- `--theme light|dark|auto` - Visual theme (default: auto)
- `--interactive` - Generate interactive HTML (for d3/html formats)

**Examples**:
```bash
# Generate Mermaid diagram
python coachntt.py graph visualize --format mermaid --output graph.md

# Create interactive HTML visualization
python coachntt.py graph visualize \
  --format html \
  --interactive \
  --output knowledge-graph.html

# Dark theme D3 visualization
python coachntt.py graph visualize \
  --format d3 \
  --theme dark \
  --output graph-dark.json
```

---

## Integration & Automation

### `coachntt sync vault`
🚧 **Status**: Planned for Session 4.2d  
**Description**: Bidirectional synchronization with Obsidian vault

```bash
python coachntt.py sync vault [OPTIONS]
```

**Options**:
- `--direction both|to-vault|from-vault` - Sync direction (default: both)
- `--template TYPE` - Template type (learning, decision, checkpoint)
- `--dry-run` - Show what would be synced without making changes
- `--max-memories N` - Maximum memories to process (default: 100)

**Examples**:
```bash
# Bidirectional sync
python coachntt.py sync vault

# Sync memories to vault only
python coachntt.py sync vault --direction to-vault --template learning

# Preview sync without changes
python coachntt.py sync vault --dry-run
```

---

### `coachntt docs generate`
🚧 **Status**: Planned for Session 4.2d  
**Description**: Generate comprehensive project documentation

```bash
python coachntt.py docs generate [OPTIONS]
```

**Options**:
- `--types readme,api,architecture,changelog` - Documentation types (default: all)
- `--output DIR` - Output directory (default: ./docs)
- `--include-diagrams` - Generate architecture diagrams
- `--format markdown|html` - Output format (default: markdown)

**Examples**:
```bash
# Generate all documentation
python coachntt.py docs generate

# Generate only API docs
python coachntt.py docs generate --types api --output ./api-docs

# Generate with diagrams
python coachntt.py docs generate \
  --include-diagrams \
  --output ./documentation
```

---

### `coachntt checkpoint create`
🚧 **Status**: Planned for Session 4.2d  
**Description**: Create development checkpoint with git state and analysis

```bash
python coachntt.py checkpoint create NAME [OPTIONS]
```

**Options**:
- `--description TEXT` - Checkpoint description
- `--include-analysis` - Include code complexity analysis
- `--max-memories N` - Maximum memories to include (default: 50)

**Examples**:
```bash
# Simple checkpoint
python coachntt.py checkpoint create "API Implementation Complete"

# Detailed checkpoint with analysis
python coachntt.py checkpoint create \
  "Session 4.2 Complete" \
  --description "CLI interface implementation finished" \
  --include-analysis
```

---

## Interactive Mode

### `coachntt interactive`
🚧 **Status**: Planned for Session 4.2d  
**Description**: Enter interactive CLI mode with command completion

```bash
python coachntt.py interactive [OPTIONS]
```

**Options**:
- `--history-file FILE` - Command history file location
- `--no-completion` - Disable tab completion

**Features**:
- Tab completion for commands and options
- Command history with up/down arrows
- Built-in help with `help` command
- Exit with `exit` or Ctrl+D

**Examples**:
```bash
# Start interactive mode
python coachntt.py interactive

# Interactive mode with custom history
python coachntt.py interactive --history-file ~/.coachntt_history
```

---

## Advanced Usage Patterns

### Scripting and Automation

```bash
#!/bin/bash
# Daily memory export script

# Check system status
if python coachntt.py status --json | jq -r '.api.status' != "healthy"; then
    echo "System not healthy, skipping export"
    exit 1
fi

# Export recent memories
python coachntt.py memory export \
  --format json \
  --since 1 \
  --output "daily-memories-$(date +%Y%m%d).json"

# Sync with vault
python coachntt.py sync vault --direction to-vault
```

### Pipeline Integration

```bash
# Memory search to graph visualization pipeline
python coachntt.py memory search "API design" --format json | \
python coachntt.py graph build --from-stdin | \
python coachntt.py graph visualize --format mermaid --output api-design.md
```

### Configuration Management

```bash
# Setup for different environments
python coachntt.py config --set api_base_url=http://localhost:8000
python coachntt.py config --set output_format=json
python coachntt.py config --set max_results=20
```

---

## Troubleshooting

### Common Issues

**CLI not found**:
```bash
# Ensure you're in the project directory
cd /path/to/CoachNTT.ai
python coachntt.py --help
```

**API connection errors**:
```bash
# Check API server is running
python coachntt.py status

# Verify configuration
python coachntt.py config --show
```

**Permission errors**:
```bash
# Ensure proper file permissions
chmod +x coachntt.py

# Check output directory permissions
python coachntt.py memory export --output ./test.json
```

### Debug Mode

Most commands support a `--debug` flag for verbose output:

```bash
python coachntt.py memory list --debug
python coachntt.py status --debug
```

### Getting Help

```bash
# General help
python coachntt.py --help

# Command-specific help
python coachntt.py memory --help
python coachntt.py graph --help

# Show examples for a command
python coachntt.py memory list --examples
```

---

## Implementation Status

- ✅ **Session 4.2a Complete**: Basic CLI with status and memory list
- ✅ **Session 4.2b Complete**: Complete memory management operations
- 🚧 **Session 4.2c Planned**: Knowledge graph operations  
- 🚧 **Session 4.2d Planned**: Integration and interactive mode

### Memory Management Features ✅
- ✅ Memory creation with type and metadata support
- ✅ Advanced semantic search with intent analysis
- ✅ Memory export in JSON, CSV, and Markdown formats
- ✅ Memory update operations with validation
- ✅ Safe memory deletion with confirmations
- ✅ Comprehensive error handling and troubleshooting guidance
- ✅ Progress indicators and rich output formatting

---

## Contributing

This user guide is a living document. When implementing new CLI features:

1. Update the status from 🚧 to ✅
2. Add real examples and output samples
3. Document any new options or behaviors
4. Test all examples in the documentation

For CLI enhancement suggestions, please follow the established patterns and maintain the safety-first design principles.