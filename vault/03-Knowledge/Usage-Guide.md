# 📚 CoachNTT.ai Complete Usage Guide

## 📋 Overview

This comprehensive guide covers all aspects of using CoachNTT.ai - from basic memory management to advanced knowledge graph operations, API integrations, and automation workflows. Whether you're a developer, researcher, or knowledge worker, this guide will help you harness the full power of cognitive coding assistance.

## 🚀 Getting Started

### First Steps After Setup

1. **Verify System Status**
```bash
# Check overall system health
python coachntt.py status

# Detailed system diagnostics
python coachntt.py status --detailed --json
```

2. **Configure CLI for Your Workflow**
```bash
# View current configuration
python coachntt.py config show

# Set preferred output format
python coachntt.py config set output_format table

# Set API connection
python coachntt.py config set api_base_url http://localhost:8000
```

3. **Create Your First Memory**
```bash
# Simple memory creation
python coachntt.py memory create "Learning about CoachNTT.ai" "This is my first memory in the cognitive coding partner system"

# Memory with metadata
python coachntt.py memory create \
  "Database optimization techniques" \
  "Use indexes, limit result sets, and optimize queries for better performance" \
  --type learning \
  --metadata project=optimization \
  --metadata priority=high
```

## 🧠 Memory Management

### Creating Memories

#### Basic Memory Creation
```bash
# Simple text memory
python coachntt.py memory create "Prompt" "Content"

# Learning memory with metadata
python coachntt.py memory create \
  "API design principles" \
  "Follow REST conventions, use proper HTTP methods, and include error handling" \
  --type learning \
  --metadata category=api \
  --metadata importance=high

# Debug memory for troubleshooting
python coachntt.py memory create \
  "Memory leak in connection pool" \
  "Found connections not being properly closed in the database service" \
  --type debug \
  --intent troubleshooting \
  --metadata severity=medium
```

#### Memory Types and Their Uses
- **learning**: Knowledge, techniques, best practices
- **decision**: Important choices and their rationale
- **context**: Project background and environmental info
- **debug**: Problem-solving and troubleshooting
- **optimization**: Performance improvements and efficiency gains

### Searching and Retrieving Memories

#### Semantic Search
```bash
# Basic semantic search
python coachntt.py memory search "database optimization"

# Search with filters
python coachntt.py memory search "API design" \
  --type learning \
  --min-score 0.8 \
  --limit 20

# Search by intent
python coachntt.py memory search "error handling" \
  --intent troubleshooting \
  --format json
```

#### Advanced Search Patterns
```bash
# Search recent memories
python coachntt.py memory list --since 7 --type learning

# Search with specific metadata
python coachntt.py memory search "performance" \
  --metadata priority=high \
  --metadata project=optimization

# Export search results
python coachntt.py memory search "database" \
  --format json \
  --output database-memories.json
```

### Memory Organization

#### Viewing Memory Details
```bash
# Show specific memory
python coachntt.py memory show abc123

# Show with related memories
python coachntt.py memory show abc123 --include-related

# Show with metadata
python coachntt.py memory show abc123 --include-metadata --format json
```

#### Updating Memories
```bash
# Update content
python coachntt.py memory update abc123 \
  --content "Updated content with new insights"

# Update metadata
python coachntt.py memory update abc123 \
  --metadata status=reviewed \
  --metadata last_updated=$(date +%Y-%m-%d)

# Update multiple fields
python coachntt.py memory update abc123 \
  --prompt "Enhanced prompt" \
  --content "Enhanced content" \
  --metadata priority=high
```

### Memory Export and Backup

#### Export Formats
```bash
# Export to JSON for data analysis
python coachntt.py memory export \
  --format json \
  --output memories-backup.json \
  --include-metadata

# Export to CSV for spreadsheet analysis
python coachntt.py memory export \
  --format csv \
  --filter type=learning \
  --output learning-memories.csv

# Export to Markdown for documentation
python coachntt.py memory export \
  --format markdown \
  --filter project=api \
  --output api-memories.md
```

#### Automated Backup Workflows
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
python coachntt.py memory export \
  --format json \
  --since 1 \
  --output "backups/daily-memories-$DATE.json"

# Weekly comprehensive backup
python coachntt.py memory export \
  --format json \
  --since 7 \
  --include-metadata \
  --output "backups/weekly-memories-$DATE.json"
```

## 🕸️ Knowledge Graph Operations

### Building Knowledge Graphs

#### Basic Graph Creation
```bash
# Build graph from recent memories
python coachntt.py graph build

# Build with specific parameters
python coachntt.py graph build \
  --max-memories 200 \
  --max-nodes 150 \
  --similarity-threshold 0.75 \
  --name "Project Architecture Graph"

# Build from code analysis
python coachntt.py graph build \
  --from-code ./src \
  --max-nodes 300 \
  --include-related \
  --output graph-metadata.json
```

#### Advanced Graph Building
```bash
# High-precision graph with strict similarity
python coachntt.py graph build \
  --similarity-threshold 0.85 \
  --max-memories 100 \
  --max-nodes 75 \
  --name "High-Precision Knowledge Map"

# Comprehensive project graph
python coachntt.py graph build \
  --from-memories \
  --from-code ./src,./cli,./scripts \
  --max-nodes 500 \
  --similarity-threshold 0.7 \
  --name "Complete Project Graph" \
  --output comprehensive-graph.json
```

### Querying Knowledge Graphs

#### Pattern-Based Queries
```bash
# Search for API-related nodes
python coachntt.py graph query abc123 --pattern "API design"

# Filter by node types
python coachntt.py graph query abc123 \
  --node-types memory,code \
  --min-safety 0.8 \
  --max-nodes 30

# Search with edge filtering
python coachntt.py graph query abc123 \
  --pattern "error handling" \
  --edge-types semantic,temporal \
  --min-weight 0.5
```

#### Advanced Graph Analysis
```bash
# Generate Mermaid visualization
python coachntt.py graph query abc123 \
  --pattern "database optimization" \
  --format mermaid \
  --output database-optimization.md

# Export for external analysis
python coachntt.py graph query abc123 \
  --node-types memory \
  --min-safety 0.9 \
  --format json \
  --output high-quality-nodes.json
```

### Graph Export and Visualization

#### Multiple Export Formats
```bash
# Mermaid diagram for documentation
python coachntt.py graph export abc123 mermaid \
  --output architecture-diagram.md \
  --include-metadata

# D3.js format for interactive visualization
python coachntt.py graph export abc123 d3 \
  --output interactive-graph.json \
  --max-nodes 100 \
  --include-metadata

# GraphML for network analysis tools
python coachntt.py graph export abc123 graphml \
  --output network-analysis.graphml \
  --min-centrality 0.5

# Cytoscape format for advanced visualization
python coachntt.py graph export abc123 cytoscape \
  --output cytoscape-graph.json \
  --include-metadata
```

#### Subgraph Extraction
```bash
# Extract subgraph around specific node
python coachntt.py graph subgraph abc123 node456 \
  --max-depth 3 \
  --max-nodes 50

# Generate focused subgraph visualization
python coachntt.py graph subgraph abc123 node456 \
  --max-depth 2 \
  --format mermaid \
  --output focused-subgraph.md

# Export subgraph for analysis
python coachntt.py graph subgraph abc123 node456 \
  --max-depth 4 \
  --min-weight 0.3 \
  --format json \
  --output subgraph-analysis.json
```

## 🔗 Integration and Automation

### Obsidian Vault Synchronization

#### Basic Sync Operations
```bash
# Bidirectional sync
python coachntt.py sync vault

# Sync memories to vault only
python coachntt.py sync vault --direction to-vault

# Sync specific vault files to memories
python coachntt.py sync vault \
  --direction from-vault \
  --vault-files "notes/project.md,daily/today.md"
```

#### Advanced Sync Features
```bash
# Preview sync without changes
python coachntt.py sync vault --dry-run --max-memories 50

# Sync with specific template
python coachntt.py sync vault \
  --direction to-vault \
  --template learning \
  --max-memories 100

# Sync with detailed reporting
python coachntt.py sync vault \
  --direction both \
  --output sync-report.json \
  --debug
```

#### Template-Based Content Creation
```bash
# Use learning template
python coachntt.py sync vault \
  --template learning \
  --direction to-vault \
  --filter type=learning

# Use decision template for important choices
python coachntt.py sync vault \
  --template decision \
  --direction to-vault \
  --filter type=decision

# Use checkpoint template for milestones
python coachntt.py sync vault \
  --template checkpoint \
  --direction to-vault \
  --filter intent=milestone
```

### Documentation Generation

#### Automated Documentation
```bash
# Generate all documentation types
python coachntt.py docs generate

# Generate specific documentation
python coachntt.py docs generate \
  --types readme,api,architecture \
  --output ./documentation

# Generate with diagrams
python coachntt.py docs generate \
  --include-diagrams \
  --format markdown \
  --output ./docs-with-diagrams
```

#### Custom Documentation Workflows
```bash
# API documentation only
python coachntt.py docs generate \
  --types api \
  --code-paths ./src/api \
  --output ./api-docs

# Architecture documentation with diagrams
python coachntt.py docs generate \
  --types architecture,readme \
  --include-diagrams \
  --code-paths ./src,./cli \
  --format markdown

# Comprehensive documentation for release
python coachntt.py docs generate \
  --types readme,api,architecture,changelog,coverage \
  --include-diagrams \
  --format html \
  --output ./release-docs
```

### Development Checkpoints

#### Creating Checkpoints
```bash
# Simple checkpoint
python coachntt.py checkpoint create "Feature Implementation Complete"

# Detailed checkpoint with analysis
python coachntt.py checkpoint create "Session 4.2d Complete" \
  --description "CLI integration and interactive mode finished" \
  --include-analysis

# Checkpoint with filtered memories
python coachntt.py checkpoint create "Learning Milestone" \
  --memory-filters "type=learning,status=complete" \
  --max-memories 30 \
  --output checkpoint-report.json
```

#### Checkpoint Best Practices
```bash
# End-of-day checkpoint
python coachntt.py checkpoint create "End of Day $(date +%Y-%m-%d)" \
  --description "Daily development progress" \
  --include-analysis \
  --memory-filters "created_today=true"

# Feature completion checkpoint
python coachntt.py checkpoint create "Feature: User Authentication" \
  --description "Complete user authentication system implementation" \
  --memory-filters "project=auth,type=learning,type=decision" \
  --include-analysis \
  --output feature-auth-checkpoint.json

# Release preparation checkpoint
python coachntt.py checkpoint create "Release v1.0 Preparation" \
  --description "Final preparations for v1.0 release" \
  --include-analysis \
  --memory-filters "priority=high,status=complete"
```

## 🖥️ Interactive CLI Mode

### Using Interactive Mode

#### Starting Interactive Session
```bash
# Start interactive mode
python coachntt.py interactive

# Start with custom history file
python coachntt.py interactive --history-file ~/.my_coachntt_history

# Start without tab completion
python coachntt.py interactive --no-completion
```

#### Interactive Commands
```bash
# Within interactive mode:
coachntt> help                    # Show available commands
coachntt> help memory             # Help for specific command group
coachntt> status                  # Check system status
coachntt> memory list --limit 5   # List recent memories
coachntt> graph list              # List available graphs
coachntt> config show             # Show configuration
coachntt> exit                    # Exit interactive mode
```

#### Interactive Workflows
```bash
# Example interactive session workflow:
coachntt> status --detailed
coachntt> memory search "optimization" --limit 5
coachntt> memory show abc123 --include-related
coachntt> graph build --max-nodes 50 --name "Quick Analysis"
coachntt> graph query xyz789 --pattern "performance"
coachntt> sync vault --dry-run
```

## 🌐 API Integration

### REST API Usage

#### Authentication
```bash
# Get access token
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/memories/"
```

#### Memory Operations via API
```bash
# Create memory
curl -X POST "http://localhost:8000/api/v1/memories/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "API testing",
    "content": "Testing memory creation via API",
    "memory_type": "learning",
    "metadata": {"source": "api-test"}
  }'

# Search memories
curl -X POST "http://localhost:8000/api/v1/memories/search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "optimization",
    "filters": {"memory_type": "learning"},
    "limit": 10
  }'
```

#### Knowledge Graph Operations via API
```bash
# Build graph
curl -X POST "http://localhost:8000/api/v1/graph/build" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_memories": true,
    "max_memories": 100,
    "max_nodes": 100,
    "similarity_threshold": 0.7,
    "graph_name": "API Test Graph"
  }'

# Query graph
curl -X POST "http://localhost:8000/api/v1/graph/{graph_id}/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "database",
    "max_nodes": 20,
    "min_safety_score": 0.8
  }'
```

### WebSocket Integration

#### Real-time Updates
```javascript
// JavaScript WebSocket example
const ws = new WebSocket('ws://localhost:8000/ws/realtime?token=YOUR_TOKEN');

ws.onopen = function(event) {
    console.log('Connected to CoachNTT.ai WebSocket');
    
    // Subscribe to channels
    ws.send(JSON.stringify({
        action: 'subscribe',
        channels: ['memory_updates', 'graph_updates']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received update:', data);
    
    if (data.channel === 'memory_updates') {
        handleMemoryUpdate(data.payload);
    } else if (data.channel === 'graph_updates') {
        handleGraphUpdate(data.payload);
    }
};
```

#### Background Task Monitoring
```bash
# Monitor background tasks via WebSocket
wscat -c "ws://localhost:8000/ws/realtime?token=YOUR_TOKEN"

# Subscribe to task updates
{"action": "subscribe", "channels": ["task_updates"]}

# Receive real-time task progress
{
  "channel": "task_updates",
  "payload": {
    "task_id": "build_graph_123",
    "status": "running",
    "progress": 45,
    "message": "Processing nodes..."
  }
}
```

## 🔄 Automation Workflows

### Scripting with CoachNTT.ai

#### Daily Automation Script
```bash
#!/bin/bash
# daily-workflow.sh

# Check system health
if ! python coachntt.py status --json | jq -r '.api.status' | grep -q "healthy"; then
    echo "System not healthy, exiting..."
    exit 1
fi

# Export recent memories
DATE=$(date +%Y%m%d)
python coachntt.py memory export \
  --format json \
  --since 1 \
  --output "backups/daily-memories-$DATE.json"

# Build daily knowledge graph
python coachntt.py graph build \
  --max-memories 50 \
  --name "Daily Graph $DATE" \
  --output "graphs/daily-graph-$DATE.json"

# Sync with vault
python coachntt.py sync vault --direction to-vault

# Generate documentation if there are updates
if git diff --quiet HEAD~1 HEAD -- src/; then
    echo "No code changes, skipping docs generation"
else
    python coachntt.py docs generate --types readme,api
fi

echo "Daily workflow completed successfully"
```

#### Weekly Report Generation
```bash
#!/bin/bash
# weekly-report.sh

WEEK_START=$(date -d 'last monday' +%Y-%m-%d)
WEEK_END=$(date +%Y-%m-%d)

# Generate weekly checkpoint
python coachntt.py checkpoint create "Weekly Report $WEEK_START to $WEEK_END" \
  --description "Automated weekly development summary" \
  --include-analysis \
  --output "reports/weekly-$WEEK_START.json"

# Export learning memories for review
python coachntt.py memory export \
  --format markdown \
  --filter type=learning \
  --since 7 \
  --output "reports/weekly-learnings-$WEEK_START.md"

# Build comprehensive graph
python coachntt.py graph build \
  --max-memories 200 \
  --max-nodes 150 \
  --name "Weekly Knowledge Graph $WEEK_START" \
  --output "reports/weekly-graph-$WEEK_START.json"

# Generate Mermaid diagram
python coachntt.py graph export $(cat reports/weekly-graph-$WEEK_START.json | jq -r '.graph_id') mermaid \
  --output "reports/weekly-diagram-$WEEK_START.md" \
  --max-nodes 100
```

### Integration Pipelines

#### CI/CD Integration
```yaml
# .github/workflows/coachntt-integration.yml
name: CoachNTT.ai Integration

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  document:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Generate documentation
        run: python coachntt.py docs generate --types readme,api,changelog
      
      - name: Create memory for build
        run: |
          python coachntt.py memory create \
            "CI/CD Build $(date)" \
            "Automated build and documentation generation for commit ${{ github.sha }}" \
            --type context \
            --metadata build_id=${{ github.run_id }} \
            --metadata commit=${{ github.sha }}
      
      - name: Commit documentation updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/
          git diff --staged --quiet || git commit -m "Auto-update documentation"
          git push
```

#### Development Workflow Integration
```bash
# git-hooks/post-commit
#!/bin/bash
# Automatically create memory for significant commits

COMMIT_MESSAGE=$(git log -1 --pretty=%B)
COMMIT_HASH=$(git rev-parse HEAD)
FILES_CHANGED=$(git diff --name-only HEAD~1 HEAD)

# Only create memory for substantial changes
if [ $(echo "$FILES_CHANGED" | wc -l) -gt 5 ]; then
    python coachntt.py memory create \
      "Commit: $COMMIT_MESSAGE" \
      "Significant code changes in: $FILES_CHANGED" \
      --type context \
      --metadata commit_hash=$COMMIT_HASH \
      --metadata files_changed=$(echo "$FILES_CHANGED" | wc -l)
fi

# Auto-generate docs for API changes
if echo "$FILES_CHANGED" | grep -q "src/api/"; then
    python coachntt.py docs generate --types api
fi
```

## 📊 Advanced Usage Patterns

### Data Analysis Workflows

#### Memory Analytics
```bash
# Export all memories for analysis
python coachntt.py memory export \
  --format json \
  --include-metadata \
  --output all-memories.json

# Analyze memory patterns with jq
cat all-memories.json | jq '.[] | select(.memory_type == "learning") | .metadata.project' | sort | uniq -c

# Generate memory statistics
python coachntt.py memory list --format json --limit 1000 | \
  jq 'group_by(.memory_type) | map({type: .[0].memory_type, count: length})'
```

#### Knowledge Graph Analysis
```bash
# Build multiple themed graphs
python coachntt.py graph build --max-memories 100 --name "API Architecture" \
  --memory-filters "project=api"

python coachntt.py graph build --max-memories 100 --name "Database Design" \
  --memory-filters "category=database"

# Export for network analysis
python coachntt.py graph export abc123 graphml \
  --output network-analysis.graphml \
  --include-metadata

# Generate comparative visualizations
python coachntt.py graph export abc123 mermaid \
  --output before-optimization.md

# After optimization
python coachntt.py graph export def456 mermaid \
  --output after-optimization.md
```

### Custom Workflow Templates

#### Research Project Workflow
```bash
# 1. Create research baseline
python coachntt.py memory create \
  "Research Project: AI Safety" \
  "Starting comprehensive research into AI safety frameworks and validation methods" \
  --type context \
  --metadata project=ai-safety \
  --metadata phase=baseline

# 2. Build initial knowledge graph
python coachntt.py graph build \
  --memory-filters "project=ai-safety" \
  --name "AI Safety Research Graph" \
  --max-nodes 200

# 3. Regular research updates
python coachntt.py memory create \
  "Safety Validation Framework Discovery" \
  "Found comprehensive framework for validating AI safety in production systems" \
  --type learning \
  --metadata project=ai-safety \
  --metadata source=research \
  --metadata importance=high

# 4. Generate research documentation
python coachntt.py docs generate \
  --types readme,architecture \
  --code-paths ./research \
  --output ./research-docs

# 5. Create milestone checkpoint
python coachntt.py checkpoint create "Research Phase 1 Complete" \
  --description "Completed initial research and framework analysis" \
  --memory-filters "project=ai-safety,phase=1" \
  --include-analysis \
  --output research-milestone-1.json
```

#### Code Review Workflow
```bash
# 1. Pre-review checkpoint
python coachntt.py checkpoint create "Pre-Review: Feature X" \
  --description "Code state before review of feature X implementation" \
  --include-analysis

# 2. Document review findings
python coachntt.py memory create \
  "Code Review: Feature X" \
  "Review identified performance bottlenecks in database queries and suggested index optimizations" \
  --type learning \
  --metadata review_type=code \
  --metadata feature=x \
  --metadata priority=high

# 3. Track review decisions
python coachntt.py memory create \
  "Decision: Database Index Strategy" \
  "Decided to implement composite indexes for user_id and timestamp combinations" \
  --type decision \
  --metadata feature=x \
  --metadata impact=performance

# 4. Post-review analysis
python coachntt.py graph build \
  --memory-filters "feature=x" \
  --name "Feature X Review Graph" \
  --max-nodes 50

# 5. Generate review documentation
python coachntt.py docs generate \
  --types changelog \
  --output ./review-docs
```

## 🔍 Troubleshooting and Debugging

### Common Usage Issues

#### Memory Management Problems
```bash
# Check memory validation
python coachntt.py memory create "Test" "Test content with /path/example" --debug

# Verify safety scores
python coachntt.py memory list --format json | jq '.[] | {id: .id, safety_score: .safety_score}'

# Check for concrete references
python coachntt.py memory search "path" --min-score 0.0 --format json
```

#### Graph Building Issues
```bash
# Debug graph building
python coachntt.py graph build --max-nodes 10 --debug

# Check node relationships
python coachntt.py graph query abc123 --format json --debug

# Verify graph structure
python coachntt.py graph show abc123 --format json
```

#### Sync and Integration Issues
```bash
# Test vault sync
python coachntt.py sync vault --dry-run --debug

# Check API connectivity
python coachntt.py status --detailed

# Verify configuration
python coachntt.py config show --format json
```

### Performance Optimization

#### Memory Operation Optimization
```bash
# Batch memory operations
python coachntt.py memory export --format json --limit 1000 | \
  jq '.[] | select(.safety_score < 0.9)' > low-quality-memories.json

# Optimize search queries
python coachntt.py memory search "query" --min-score 0.7 --limit 20

# Monitor performance
time python coachntt.py memory list --limit 100
```

#### Graph Performance Tuning
```bash
# Build smaller, focused graphs
python coachntt.py graph build --max-memories 50 --max-nodes 50

# Use higher similarity thresholds
python coachntt.py graph build --similarity-threshold 0.8

# Export optimized graphs
python coachntt.py graph export abc123 json --max-nodes 100 --min-centrality 0.5
```

## 📈 Best Practices

### Memory Organization
1. **Use consistent metadata**: Establish project, priority, and type conventions
2. **Regular review cycles**: Export and review memories weekly
3. **Quality maintenance**: Monitor safety scores and update low-quality memories
4. **Semantic clustering**: Use similar language for related concepts

### Knowledge Graph Usage
1. **Build focused graphs**: Create topic-specific graphs rather than massive ones
2. **Regular updates**: Rebuild graphs as your knowledge base grows
3. **Export for analysis**: Use external tools for complex network analysis
4. **Document insights**: Create memories about graph discoveries

### Integration Workflows
1. **Automate routine tasks**: Use scripts for daily/weekly operations
2. **Monitor system health**: Regular status checks and performance monitoring
3. **Backup strategies**: Regular exports and checkpoint creation
4. **Documentation updates**: Keep docs synchronized with code changes

### Safety and Security
1. **Monitor safety scores**: Ensure all content maintains high safety scores
2. **Regular validation**: Use safety validation tools and tests
3. **Secure configuration**: Protect API keys and database credentials
4. **Audit trails**: Maintain logs of important operations

---

**Mastery Achieved!** 🎉

You now have comprehensive knowledge of CoachNTT.ai's capabilities. Use this guide as a reference for maximizing your cognitive coding productivity with safety-first AI assistance.