# 🚀 CoachNTT.ai Effective Usage Guide

## 📋 Overview

This guide is for users who already have CoachNTT.ai installed and want to maximize its value in their daily development workflow. Learn practical patterns, time-saving techniques, and real-world applications that transform how you code, learn, and manage knowledge.

## ⏰ Daily Workflow Integration

### Morning Startup Routine (5 minutes)

Start each day by establishing context and reviewing your knowledge state:

```bash
# 1. Check system health
python coachntt.py status

# 2. Review yesterday's learnings
python coachntt.py memory list --since 1 --type learning --limit 5

# 3. Check active knowledge graphs
python coachntt.py graph list

# 4. Sync with vault for overnight changes
python coachntt.py sync vault --direction from-vault

# 5. Create morning context memory
python coachntt.py memory create \
  "Morning Context $(date +%Y-%m-%d)" \
  "Starting work on: [current projects and priorities]" \
  --type context \
  --metadata time=morning
```

**Pro Tip**: Create a shell alias for this routine:
```bash
alias ccp-morning='python coachntt.py status && python coachntt.py memory list --since 1 --type learning --limit 5 && python coachntt.py sync vault --direction from-vault'
```

### Throughout-the-Day Usage Patterns

#### 🐛 Debugging Sessions
When encountering bugs or issues:

```bash
# Record the bug discovery
python coachntt.py memory create \
  "Bug: Authentication token expiry" \
  "JWT tokens expire after 30 minutes but refresh logic not triggering. Error in middleware/auth.py line 45" \
  --type debug \
  --metadata severity=high \
  --metadata component=auth \
  --intent troubleshooting

# After finding solution
python coachntt.py memory create \
  "Solution: Authentication token refresh" \
  "Fixed by adding token refresh check in middleware before expiry. Added 5-minute buffer." \
  --type learning \
  --metadata fixes_bug=auth_token_expiry \
  --metadata component=auth
```

#### 📚 Learning New Concepts
When learning something new:

```bash
# Capture new knowledge immediately
python coachntt.py memory create \
  "Python async context managers" \
  "async with statement manages async resources. Use __aenter__ and __aexit__ methods. Example: async with aiohttp.ClientSession() as session" \
  --type learning \
  --metadata topic=python \
  --metadata subtopic=async \
  --metadata source=documentation

# Build connections to existing knowledge
python coachntt.py memory search "async" --type learning --limit 10
python coachntt.py graph build --memory-filters "topic=python,subtopic=async" --name "Python Async Knowledge"
```

#### 🎯 Decision Making
Document important decisions:

```bash
# Record architectural decisions
python coachntt.py memory create \
  "Decision: Use Redis for caching" \
  "Chose Redis over Memcached for caching layer. Reasons: 1) Data persistence options 2) Pub/sub for cache invalidation 3) Better data structures" \
  --type decision \
  --metadata impact=high \
  --metadata area=architecture \
  --metadata alternatives="memcached,in-memory"

# Link to implementation
python coachntt.py memory create \
  "Redis cache implementation" \
  "Implemented Redis caching with 1-hour TTL for embeddings. Connection pool size 10. Using Redis 7.0 with persistence disabled for cache." \
  --type context \
  --metadata implements_decision=redis_caching \
  --metadata config=production
```

### End-of-Day Wrap-up (10 minutes)

Consolidate daily learnings and prepare for tomorrow:

```bash
# 1. Create daily summary
python coachntt.py checkpoint create "Daily Summary $(date +%Y-%m-%d)" \
  --description "Completed: [what you achieved]. Learned: [key insights]. Tomorrow: [priorities]" \
  --memory-filters "created_today=true" \
  --include-analysis

# 2. Export today's memories for review
python coachntt.py memory export \
  --format markdown \
  --since 1 \
  --output "daily-notes/$(date +%Y-%m-%d).md"

# 3. Build daily knowledge graph
python coachntt.py graph build \
  --max-memories 50 \
  --memory-filters "created_today=true" \
  --name "Daily Graph $(date +%Y-%m-%d)"

# 4. Sync to vault
python coachntt.py sync vault --direction to-vault

# 5. Quick performance check
python coachntt.py memory list --format json | jq 'length' # Total memories
python coachntt.py status --json | jq '.performance'
```

### Weekly Review Process (30 minutes)

Every Friday, conduct a comprehensive review:

```bash
#!/bin/bash
# weekly-review.sh

echo "=== Weekly CoachNTT.ai Review ==="
WEEK_START=$(date -d 'last monday' +%Y-%m-%d)

# 1. Generate weekly report
python coachntt.py checkpoint create "Weekly Review $WEEK_START" \
  --description "Weekly development summary and learnings" \
  --memory-filters "created_this_week=true" \
  --include-analysis \
  --output "reports/weekly-$WEEK_START.json"

# 2. Analyze learning patterns
echo "Learning Summary:"
python coachntt.py memory list --since 7 --type learning --format json | \
  jq -r '.[] | .metadata.topic' | sort | uniq -c | sort -nr

# 3. Review decisions made
echo "Decisions This Week:"
python coachntt.py memory list --since 7 --type decision --format table

# 4. Build comprehensive weekly graph
python coachntt.py graph build \
  --max-memories 200 \
  --memory-filters "created_this_week=true" \
  --name "Weekly Knowledge Graph $WEEK_START" \
  --output "graphs/weekly-$WEEK_START.json"

# 5. Export graph visualization
GRAPH_ID=$(cat graphs/weekly-$WEEK_START.json | jq -r '.graph_id')
python coachntt.py graph export $GRAPH_ID mermaid \
  --output "reports/weekly-graph-$WEEK_START.md"

# 6. Clean up low-quality memories
python coachntt.py memory list --format json | \
  jq '.[] | select(.safety_score < 0.85) | .id' | \
  while read id; do
    echo "Review low-quality memory: $id"
    python coachntt.py memory show $id
  done

# 7. Generate documentation updates
python coachntt.py docs generate --types changelog --output ./docs/weekly
```

## 🧠 Memory Management Best Practices

### What to Memorize

#### Always Capture
1. **Bug Solutions**: Every bug you solve is future time saved
2. **Learning Moments**: New concepts, patterns, techniques
3. **Decisions**: Architectural choices and their rationale
4. **Project Context**: Setup steps, configuration details
5. **Code Patterns**: Reusable solutions and implementations

#### Smart Memory Creation

```bash
# Rich metadata example
python coachntt.py memory create \
  "Optimized database query for user search" \
  "Replaced N+1 query with single JOIN. Performance improved from 500ms to 50ms. Used: SELECT users.*, COUNT(posts.id) FROM users LEFT JOIN posts..." \
  --type optimization \
  --metadata project=user-service \
  --metadata performance_gain=10x \
  --metadata before_time=500ms \
  --metadata after_time=50ms \
  --metadata query_type=join \
  --metadata database=postgresql
```

### Effective Tagging and Metadata

#### Metadata Strategy
Create consistent metadata taxonomies:

```python
# Recommended metadata patterns
METADATA_TAXONOMY = {
    "project": ["api", "frontend", "database", "infrastructure"],
    "component": ["auth", "user", "payment", "notification"],
    "priority": ["critical", "high", "medium", "low"],
    "status": ["active", "resolved", "pending", "archived"],
    "language": ["python", "javascript", "sql", "bash"],
    "framework": ["fastapi", "react", "django", "express"],
    "topic": ["performance", "security", "architecture", "testing"]
}
```

#### Tag Consistency Script
```bash
#!/bin/bash
# check-metadata-consistency.sh

# Extract all unique metadata keys
echo "=== Metadata Key Analysis ==="
python coachntt.py memory list --format json --limit 1000 | \
  jq -r '.[] | .metadata | keys[]' | sort | uniq -c | sort -nr

# Check for similar but different keys
echo -e "\n=== Potential Duplicate Keys ==="
python coachntt.py memory list --format json --limit 1000 | \
  jq -r '.[] | .metadata | keys[]' | sort | uniq | \
  awk '{print tolower($0), $0}' | sort | \
  awk 'prev_lower == $1 && prev_orig != $2 {print prev_orig " vs " $2} {prev_lower=$1; prev_orig=$2}'
```

### Memory Organization Strategies

#### Hierarchical Organization
```bash
# Project-based organization
python coachntt.py memory create \
  "Project: E-commerce Platform" \
  "Main project context for e-commerce platform. Tech stack: FastAPI, React, PostgreSQL" \
  --type context \
  --metadata project=ecommerce \
  --metadata level=project \
  --metadata parent=root

# Component within project
python coachntt.py memory create \
  "Component: Payment Service" \
  "Payment processing service using Stripe API. Handles subscriptions and one-time payments" \
  --type context \
  --metadata project=ecommerce \
  --metadata component=payment \
  --metadata level=component \
  --metadata parent=ecommerce_project
```

#### Time-based Organization
```bash
# Sprint-based memories
SPRINT="sprint-23"
python coachntt.py memory create \
  "Sprint 23: Payment Integration" \
  "Implementing Stripe payment integration with webhook handling" \
  --type context \
  --metadata sprint=$SPRINT \
  --metadata start_date=2024-01-15 \
  --metadata end_date=2024-01-29
```

### Search Optimization Techniques

#### Multi-faceted Search
```bash
# Complex search combining multiple criteria
python coachntt.py memory search "optimization" \
  --type learning \
  --min-score 0.8 \
  --metadata project=ecommerce \
  --metadata topic=performance \
  --limit 20 \
  --format json | jq '.[] | {id, prompt, safety_score, created_at}'
```

#### Search Aliases for Common Queries
```bash
# Add to ~/.bashrc or ~/.zshrc
alias ccp-bugs='python coachntt.py memory list --type debug --limit 20'
alias ccp-decisions='python coachntt.py memory list --type decision --limit 20'
alias ccp-recent='python coachntt.py memory list --since 1 --limit 20'
alias ccp-search='python coachntt.py memory search'
```

## 🕸️ Knowledge Graph Mastery

### When to Build Graphs

#### Trigger Points for Graph Building

1. **Weekly Reviews**: Build comprehensive weekly graphs
2. **Project Milestones**: Capture knowledge at key points
3. **Learning Paths**: After learning new technology/concept
4. **Bug Post-Mortems**: Understand issue patterns
5. **Before Major Decisions**: Visualize existing knowledge

#### Strategic Graph Building
```bash
# Learning-focused graph
python coachntt.py graph build \
  --memory-filters "type=learning,created_this_month=true" \
  --max-nodes 100 \
  --similarity-threshold 0.75 \
  --name "Monthly Learning Graph"

# Project-specific graph
python coachntt.py graph build \
  --memory-filters "project=ecommerce" \
  --from-code ./src/ecommerce \
  --max-nodes 200 \
  --name "E-commerce Knowledge Graph"

# Decision impact graph
python coachntt.py graph build \
  --memory-filters "type=decision" \
  --include-related \
  --max-nodes 150 \
  --name "Decision Impact Analysis"
```

### Optimal Graph Parameters

#### Size Guidelines
- **Daily Graphs**: 30-50 nodes (focused, quick to analyze)
- **Weekly Graphs**: 100-150 nodes (comprehensive but manageable)
- **Project Graphs**: 200-300 nodes (full context)
- **Learning Graphs**: 50-100 nodes (topic-focused)

#### Similarity Threshold Tuning
```bash
# High precision (fewer, stronger connections)
python coachntt.py graph build --similarity-threshold 0.85 --name "High Precision Graph"

# Balanced (default, good for most uses)
python coachntt.py graph build --similarity-threshold 0.75 --name "Balanced Graph"

# Exploratory (more connections, discover patterns)
python coachntt.py graph build --similarity-threshold 0.65 --name "Exploratory Graph"
```

### Query Patterns for Insights

#### Finding Knowledge Gaps
```bash
# Identify isolated nodes (potential knowledge gaps)
python coachntt.py graph query $GRAPH_ID \
  --max-nodes 100 \
  --format json | \
  jq '.nodes[] | select(.edges | length < 2) | {id, content, edge_count: (.edges | length)}'
```

#### Discovering Central Concepts
```bash
# Find most connected nodes (key concepts)
python coachntt.py graph query $GRAPH_ID \
  --min-centrality 0.7 \
  --format json | \
  jq '.nodes | sort_by(.centrality_score) | reverse | .[:10] | .[] | {content, centrality: .centrality_score}'
```

#### Pattern Recognition
```bash
# Find clustering patterns
python coachntt.py graph query $GRAPH_ID \
  --pattern "error handling" \
  --format mermaid \
  --output error-patterns.md

# Extract subgraphs for specific topics
python coachntt.py graph subgraph $GRAPH_ID $NODE_ID \
  --max-depth 3 \
  --max-nodes 30 \
  --format json | \
  jq '.nodes | group_by(.metadata.topic) | map({topic: .[0].metadata.topic, count: length})'
```

### Graph Evolution Tracking

#### Version Control for Graphs
```bash
#!/bin/bash
# track-graph-evolution.sh

GRAPH_NAME="$1"
VERSION=$(date +%Y%m%d_%H%M%S)

# Build versioned graph
python coachntt.py graph build \
  --name "${GRAPH_NAME}_v${VERSION}" \
  --output "graph-versions/${GRAPH_NAME}_v${VERSION}.json"

# Compare with previous version
if [ -f "graph-versions/${GRAPH_NAME}_latest.json" ]; then
  OLD_NODES=$(cat graph-versions/${GRAPH_NAME}_latest.json | jq '.node_count')
  NEW_NODES=$(cat graph-versions/${GRAPH_NAME}_v${VERSION}.json | jq '.node_count')
  echo "Graph evolution: $OLD_NODES → $NEW_NODES nodes"
fi

# Update latest link
ln -sf "${GRAPH_NAME}_v${VERSION}.json" "graph-versions/${GRAPH_NAME}_latest.json"
```

## 🔗 Integration Workflows

### Obsidian Vault Best Practices

#### Vault Organization Structure
```
vault/
├── 00-Daily/              # Daily notes and journals
│   └── 2024-01-15.md
├── 01-Projects/           # Project-specific knowledge
│   ├── Ecommerce/
│   └── API-Service/
├── 02-Learning/           # Learning and reference
│   ├── Python/
│   └── Architecture/
├── 03-Decisions/          # Architectural decisions
│   └── ADR-001-Redis-Cache.md
├── 04-Debug/              # Bug solutions and troubleshooting
│   └── Auth-Token-Expiry.md
└── 05-Templates/          # Reusable templates
```

#### Automated Vault Sync Workflow
```bash
#!/bin/bash
# auto-vault-sync.sh

# Morning sync from vault
python coachntt.py sync vault --direction from-vault --dry-run
read -p "Proceed with sync? (y/n): " confirm
[ "$confirm" = "y" ] && python coachntt.py sync vault --direction from-vault

# Evening sync to vault
python coachntt.py sync vault \
  --direction to-vault \
  --template learning \
  --max-memories 50 \
  --output sync-report.json

# Process sync report
cat sync-report.json | jq '.synced_files | length' # Count synced files
```

### Git Integration Patterns

#### Pre-commit Knowledge Capture
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Capture significant changes
FILES_CHANGED=$(git diff --cached --name-only | wc -l)
if [ $FILES_CHANGED -gt 5 ]; then
  echo "Significant commit detected. Creating memory..."
  
  COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "Upcoming commit")
  FILES_LIST=$(git diff --cached --name-only | head -10)
  
  python coachntt.py memory create \
    "Code Change: $COMMIT_MSG" \
    "Modified files: $FILES_LIST. Major changes in this commit." \
    --type context \
    --metadata commit_size=$FILES_CHANGED \
    --metadata vcs=git
fi
```

#### Post-merge Learning Capture
```bash
#!/bin/bash
# .git/hooks/post-merge

# After merging, review new code patterns
echo "Analyzing merged code for patterns..."

# Find new functions/classes
git diff HEAD~1 HEAD --name-only | grep -E "\.(py|js|ts)$" | while read file; do
  if [ -f "$file" ]; then
    python coachntt.py memory create \
      "Merged code: $file" \
      "New code merged from branch. Review for patterns and learnings." \
      --type context \
      --metadata file=$file \
      --metadata event=merge
  fi
done
```

### Documentation Automation

#### Smart Documentation Generation
```bash
#!/bin/bash
# smart-docs.sh

# Detect what changed and generate appropriate docs
CHANGED_DIRS=$(git diff --name-only HEAD~1 HEAD | xargs -I {} dirname {} | sort | uniq)

for dir in $CHANGED_DIRS; do
  case $dir in
    src/api/*)
      echo "API changes detected, updating API docs..."
      python coachntt.py docs generate --types api --code-paths $dir
      ;;
    src/core/*)
      echo "Core changes detected, updating architecture docs..."
      python coachntt.py docs generate --types architecture --code-paths $dir
      ;;
    *)
      echo "General changes in $dir"
      ;;
  esac
done

# Always update changelog
python coachntt.py docs generate --types changelog
```

### CI/CD Pipeline Integration

#### GitHub Actions Workflow
```yaml
# .github/workflows/knowledge-capture.yml
name: Knowledge Capture

on:
  push:
    branches: [main, develop]
  pull_request:
    types: [closed]

jobs:
  capture-knowledge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install CoachNTT.ai
        run: |
          pip install -r requirements.txt
          
      - name: Capture PR Knowledge
        if: github.event_name == 'pull_request' && github.event.pull_request.merged == true
        run: |
          python coachntt.py memory create \
            "PR Merged: ${{ github.event.pull_request.title }}" \
            "PR #${{ github.event.pull_request.number }} merged. Changes: ${{ github.event.pull_request.body }}" \
            --type context \
            --metadata pr_number=${{ github.event.pull_request.number }} \
            --metadata author=${{ github.event.pull_request.user.login }}
      
      - name: Generate Updated Docs
        run: |
          python coachntt.py docs generate --types readme,changelog
          
      - name: Create Knowledge Graph
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: |
          python coachntt.py graph build \
            --from-code ./src \
            --max-nodes 200 \
            --name "CI Build ${{ github.run_number }}"
```

## 💪 Power User Features

### Custom Scripts and Automation

#### Memory Analysis Script
```python
#!/usr/bin/env python
# analyze_memories.py

import json
import subprocess
from collections import defaultdict, Counter
from datetime import datetime, timedelta

def get_memories(days=30):
    """Fetch recent memories."""
    cmd = f"python coachntt.py memory list --since {days} --format json --limit 1000"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return json.loads(result.stdout)

def analyze_patterns(memories):
    """Analyze memory patterns."""
    # Time distribution
    hour_distribution = defaultdict(int)
    type_distribution = Counter()
    metadata_keys = Counter()
    
    for memory in memories:
        # Extract hour
        created = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
        hour_distribution[created.hour] += 1
        
        # Type distribution
        type_distribution[memory['memory_type']] += 1
        
        # Metadata analysis
        for key in memory.get('metadata', {}).keys():
            metadata_keys[key] += 1
    
    return {
        'hour_distribution': dict(hour_distribution),
        'type_distribution': dict(type_distribution),
        'top_metadata_keys': metadata_keys.most_common(10),
        'total_memories': len(memories),
        'avg_safety_score': sum(m['safety_score'] for m in memories) / len(memories)
    }

def generate_report(analysis):
    """Generate analysis report."""
    print("=== Memory Analysis Report ===")
    print(f"Total Memories: {analysis['total_memories']}")
    print(f"Average Safety Score: {analysis['avg_safety_score']:.3f}")
    
    print("\nMemory Types:")
    for mem_type, count in analysis['type_distribution'].items():
        print(f"  {mem_type}: {count}")
    
    print("\nPeak Activity Hours:")
    sorted_hours = sorted(analysis['hour_distribution'].items(), 
                         key=lambda x: x[1], reverse=True)[:5]
    for hour, count in sorted_hours:
        print(f"  {hour:02d}:00 - {count} memories")
    
    print("\nTop Metadata Keys:")
    for key, count in analysis['top_metadata_keys']:
        print(f"  {key}: {count}")

if __name__ == "__main__":
    memories = get_memories(30)
    analysis = analyze_patterns(memories)
    generate_report(analysis)
```

#### Intelligent Memory Reinforcement
```python
#!/usr/bin/env python
# smart_reinforce.py

import subprocess
import json
from datetime import datetime, timedelta

def get_stale_memories():
    """Find memories that haven't been accessed recently."""
    # Get all memories from last 90 days
    cmd = "python coachntt.py memory list --since 90 --format json --limit 500"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    memories = json.loads(result.stdout)
    
    # Filter memories older than 30 days with high value
    stale = []
    cutoff = datetime.now() - timedelta(days=30)
    
    for memory in memories:
        created = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
        if created < cutoff and memory['memory_type'] in ['learning', 'decision']:
            stale.append(memory)
    
    return stale

def reinforce_memory(memory_id):
    """Reinforce a specific memory."""
    cmd = f"python coachntt.py memory reinforce {memory_id}"
    subprocess.run(cmd, shell=True)

def main():
    stale_memories = get_stale_memories()
    print(f"Found {len(stale_memories)} valuable memories that may need reinforcement")
    
    for memory in stale_memories[:10]:  # Limit to 10 per run
        print(f"\nMemory: {memory['prompt'][:50]}...")
        print(f"Type: {memory['memory_type']}, Created: {memory['created_at']}")
        
        response = input("Reinforce this memory? (y/n/q): ")
        if response.lower() == 'y':
            reinforce_memory(memory['id'])
            print("Memory reinforced!")
        elif response.lower() == 'q':
            break

if __name__ == "__main__":
    main()
```

### API Integration Patterns

#### Python API Client Wrapper
```python
# coachntt_client.py
import httpx
import asyncio
from typing import Dict, List, Optional
import json

class CoachNTTClient:
    """Async client for CoachNTT.ai API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    async def create_memory(self, prompt: str, content: str, **kwargs) -> Dict:
        """Create a new memory."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/memories/",
                json={
                    "prompt": prompt,
                    "content": content,
                    **kwargs
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def search_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """Search memories."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/memories/search",
                json={"query": query, "limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def build_graph(self, **params) -> Dict:
        """Build knowledge graph."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/graph/build",
                json=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# Usage example
async def main():
    client = CoachNTTClient()
    
    # Create memory from code analysis
    memory = await client.create_memory(
        prompt="FastAPI async best practices",
        content="Use async def for route handlers. Avoid blocking I/O. Use background tasks for long operations.",
        memory_type="learning",
        metadata={"framework": "fastapi", "topic": "async"}
    )
    print(f"Created memory: {memory['id']}")
    
    # Search related memories
    results = await client.search_memories("fastapi async", limit=5)
    print(f"Found {len(results)} related memories")

if __name__ == "__main__":
    asyncio.run(main())
```

### WebSocket Monitoring

#### Real-time Dashboard
```python
#!/usr/bin/env python
# realtime_monitor.py

import asyncio
import websockets
import json
from rich.console import Console
from rich.live import Live
from rich.table import Table
from datetime import datetime

console = Console()

class RealtimeMonitor:
    def __init__(self, ws_url: str = "ws://localhost:8000/ws/realtime"):
        self.ws_url = ws_url
        self.events = []
        self.stats = {
            "memory_created": 0,
            "memory_updated": 0,
            "graph_built": 0,
            "sync_completed": 0
        }
    
    async def connect(self, token: str):
        """Connect to WebSocket."""
        uri = f"{self.ws_url}?token={token}"
        async with websockets.connect(uri) as websocket:
            # Subscribe to channels
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channels": ["memory_updates", "graph_updates", "system_notifications"]
            }))
            
            # Start monitoring
            await self.monitor(websocket)
    
    async def monitor(self, websocket):
        """Monitor real-time events."""
        with Live(self.generate_table(), refresh_per_second=1) as live:
            async for message in websocket:
                data = json.loads(message)
                self.process_event(data)
                live.update(self.generate_table())
    
    def process_event(self, event):
        """Process incoming event."""
        self.events.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "channel": event.get("channel", "unknown"),
            "type": event.get("payload", {}).get("type", "unknown"),
            "details": str(event.get("payload", {}))[:50] + "..."
        })
        
        # Update stats
        event_type = event.get("payload", {}).get("type", "")
        if event_type in self.stats:
            self.stats[event_type] += 1
        
        # Keep only last 20 events
        self.events = self.events[-20:]
    
    def generate_table(self):
        """Generate rich table for display."""
        table = Table(title="CoachNTT.ai Real-time Monitor")
        
        # Stats section
        table.add_column("Statistic", style="cyan")
        table.add_column("Count", style="green")
        
        for stat, count in self.stats.items():
            table.add_row(stat.replace("_", " ").title(), str(count))
        
        # Recent events
        table.add_row("", "")  # Spacer
        table.add_row("[bold]Recent Events[/bold]", "[bold]Details[/bold]")
        
        for event in reversed(self.events[-10:]):
            table.add_row(
                f"{event['time']} - {event['channel']}",
                event['details']
            )
        
        return table

async def main():
    monitor = RealtimeMonitor()
    token = "your-jwt-token"  # Get from auth
    await monitor.connect(token)

if __name__ == "__main__":
    asyncio.run(main())
```

### Performance Optimization

#### Batch Operations Script
```bash
#!/bin/bash
# batch_operations.sh

# Batch memory creation from file
batch_create_memories() {
  local input_file="$1"
  
  while IFS='|' read -r prompt content type metadata; do
    python coachntt.py memory create "$prompt" "$content" \
      --type "$type" \
      --metadata "$metadata" &
    
    # Limit concurrent operations
    [ $(jobs -r | wc -l) -ge 5 ] && wait -n
  done < "$input_file"
  
  wait # Wait for all background jobs
}

# Batch memory export
batch_export() {
  local projects=("api" "frontend" "database")
  
  for project in "${projects[@]}"; do
    python coachntt.py memory export \
      --format json \
      --filter "project=$project" \
      --output "exports/${project}-memories.json" &
  done
  
  wait
  echo "Batch export complete"
}

# Performance testing
performance_test() {
  echo "=== Performance Test ==="
  
  # Memory creation speed
  time python coachntt.py memory create "Perf Test" "Test content" >/dev/null
  
  # Search performance
  time python coachntt.py memory search "test" --limit 100 >/dev/null
  
  # Graph building performance
  time python coachntt.py graph build --max-nodes 50 >/dev/null
}
```

## 🎯 Real-World Scenarios

### Bug Tracking Workflow

Complete bug lifecycle management:

```bash
#!/bin/bash
# bug_workflow.sh

# 1. When bug is discovered
bug_discovered() {
  local bug_title="$1"
  local bug_description="$2"
  local severity="${3:-medium}"
  
  # Create bug memory
  BUG_ID=$(python coachntt.py memory create \
    "Bug: $bug_title" \
    "$bug_description" \
    --type debug \
    --metadata severity=$severity \
    --metadata status=open \
    --metadata discovered_at=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --format json | jq -r '.id')
  
  echo "Bug tracked: $BUG_ID"
  
  # Search for similar bugs
  echo "Searching for similar issues..."
  python coachntt.py memory search "$bug_title" \
    --type debug \
    --limit 5
}

# 2. During investigation
bug_investigate() {
  local bug_id="$1"
  local findings="$2"
  
  python coachntt.py memory create \
    "Investigation: Bug $bug_id" \
    "$findings" \
    --type context \
    --metadata bug_id=$bug_id \
    --metadata phase=investigation
}

# 3. When solution is found
bug_solved() {
  local bug_id="$1"
  local solution="$2"
  
  # Create solution memory
  python coachntt.py memory create \
    "Solution: Bug $bug_id" \
    "$solution" \
    --type learning \
    --metadata fixes_bug=$bug_id \
    --metadata solution_type=fix
  
  # Update original bug status
  python coachntt.py memory update $bug_id \
    --metadata status=resolved \
    --metadata resolved_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  
  # Build bug resolution graph
  python coachntt.py graph build \
    --memory-filters "bug_id=$bug_id" \
    --name "Bug Resolution: $bug_id"
}

# 4. Post-mortem analysis
bug_postmortem() {
  local bug_id="$1"
  
  # Generate bug report
  echo "=== Bug Post-Mortem: $bug_id ==="
  
  # Get all related memories
  python coachntt.py memory search "$bug_id" \
    --format json | \
    jq '.[] | select(.metadata.bug_id == "'$bug_id'" or .metadata.fixes_bug == "'$bug_id'")'
  
  # Create post-mortem memory
  python coachntt.py memory create \
    "Post-mortem: Bug $bug_id" \
    "Completed analysis of bug lifecycle. Root cause identified and documented." \
    --type learning \
    --metadata bug_id=$bug_id \
    --metadata document_type=postmortem
}
```

### Learning New Technologies

Structured learning approach:

```bash
#!/bin/bash
# learning_workflow.sh

# Initialize new learning topic
start_learning() {
  local topic="$1"
  local description="$2"
  
  # Create learning context
  python coachntt.py memory create \
    "Learning: $topic" \
    "Starting to learn $topic. Goals: $description" \
    --type context \
    --metadata learning_topic=$topic \
    --metadata phase=start \
    --metadata start_date=$(date +%Y-%m-%d)
  
  # Create learning graph
  python coachntt.py graph build \
    --memory-filters "learning_topic=$topic" \
    --name "Learning Path: $topic"
}

# Capture learning progress
capture_learning() {
  local topic="$1"
  local concept="$2"
  local details="$3"
  
  python coachntt.py memory create \
    "$topic: $concept" \
    "$details" \
    --type learning \
    --metadata learning_topic=$topic \
    --metadata concept=$concept \
    --metadata understanding_level=${4:-intermediate}
}

# Learning checkpoint
learning_checkpoint() {
  local topic="$1"
  
  echo "=== Learning Checkpoint: $topic ==="
  
  # Summary of what's learned
  python coachntt.py memory list \
    --format json \
    --filter "learning_topic=$topic" | \
    jq -r '.[] | .prompt' | sort
  
  # Build comprehensive learning graph
  python coachntt.py graph build \
    --memory-filters "learning_topic=$topic" \
    --name "Learning Summary: $topic" \
    --output "learning-graphs/${topic}.json"
  
  # Export learning notes
  python coachntt.py memory export \
    --format markdown \
    --filter "learning_topic=$topic" \
    --output "learning-notes/${topic}.md"
}

# Example usage
start_learning "Rust" "Learn Rust for systems programming"
capture_learning "Rust" "Ownership" "Rust ownership model prevents memory leaks. Each value has single owner."
capture_learning "Rust" "Borrowing" "References allow borrowing values without taking ownership. & for immutable, &mut for mutable."
learning_checkpoint "Rust"
```

### Code Review Assistance

Enhance code reviews with knowledge:

```python
#!/usr/bin/env python
# code_review_assistant.py

import subprocess
import json
from pathlib import Path
import ast
import asyncio

class CodeReviewAssistant:
    def __init__(self):
        self.patterns_found = []
        self.suggestions = []
    
    async def review_file(self, file_path: str):
        """Review a single file."""
        print(f"\n=== Reviewing: {file_path} ===")
        
        # Read file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Analyze code structure
        if file_path.endswith('.py'):
            await self.analyze_python(content, file_path)
        
        # Search for similar patterns in memory
        await self.search_similar_patterns(file_path)
        
        # Generate review summary
        self.generate_review_summary(file_path)
    
    async def analyze_python(self, content: str, file_path: str):
        """Analyze Python code."""
        try:
            tree = ast.parse(content)
            
            # Find functions longer than 50 lines
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = node.end_lineno - node.lineno
                    if func_lines > 50:
                        self.suggestions.append(
                            f"Long function '{node.name}' ({func_lines} lines) - consider refactoring"
                        )
            
            # Check for common patterns
            patterns = {
                "no_type_hints": self.check_type_hints(tree),
                "nested_loops": self.check_nested_loops(tree),
                "long_parameter_lists": self.check_parameter_lists(tree)
            }
            
            for pattern, issues in patterns.items():
                if issues:
                    self.patterns_found.extend(issues)
                    
        except Exception as e:
            print(f"Error analyzing Python code: {e}")
    
    def check_type_hints(self, tree):
        """Check for missing type hints."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.returns and node.name != '__init__':
                    issues.append(f"Function '{node.name}' missing return type hint")
        return issues
    
    def check_nested_loops(self, tree):
        """Check for deeply nested loops."""
        # Simplified check - would need more complex analysis
        return []
    
    def check_parameter_lists(self, tree):
        """Check for functions with too many parameters."""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.args.args) > 5:
                    issues.append(
                        f"Function '{node.name}' has {len(node.args.args)} parameters - consider using objects"
                    )
        return issues
    
    async def search_similar_patterns(self, file_path: str):
        """Search for similar code patterns in memory."""
        # Extract key terms from file path
        terms = Path(file_path).stem.replace('_', ' ')
        
        # Search memories
        cmd = f'python coachntt.py memory search "{terms}" --type learning --limit 5 --format json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            memories = json.loads(result.stdout)
            if memories:
                print("\nRelated knowledge found:")
                for memory in memories[:3]:
                    print(f"- {memory['prompt']}")
    
    def generate_review_summary(self, file_path: str):
        """Generate and store review summary."""
        if self.suggestions or self.patterns_found:
            summary = f"Code review for {file_path}:\n"
            summary += "Suggestions:\n" + "\n".join(f"- {s}" for s in self.suggestions)
            summary += "\nPatterns found:\n" + "\n".join(f"- {p}" for p in self.patterns_found)
            
            # Store in memory
            cmd = [
                "python", "coachntt.py", "memory", "create",
                f"Code Review: {Path(file_path).name}",
                summary,
                "--type", "context",
                "--metadata", f"file={file_path}",
                "--metadata", "review_type=automated"
            ]
            subprocess.run(cmd)
            
            print("\nReview summary stored in memory")
        
        # Reset for next file
        self.patterns_found = []
        self.suggestions = []

async def main():
    assistant = CodeReviewAssistant()
    
    # Review changed files
    result = subprocess.run(
        "git diff --name-only HEAD~1 HEAD", 
        shell=True, 
        capture_output=True, 
        text=True
    )
    
    if result.returncode == 0:
        files = result.stdout.strip().split('\n')
        for file in files:
            if file.endswith(('.py', '.js', '.ts')):
                await assistant.review_file(file)

if __name__ == "__main__":
    asyncio.run(main())
```

### Project Documentation

Automated project documentation workflow:

```bash
#!/bin/bash
# project_docs_workflow.sh

# Generate comprehensive project documentation
generate_project_docs() {
  local project_name="$1"
  local project_path="$2"
  
  echo "=== Generating Documentation for $project_name ==="
  
  # 1. Analyze codebase
  python coachntt.py graph build \
    --from-code "$project_path" \
    --max-nodes 200 \
    --name "$project_name Architecture" \
    --output "docs/${project_name}-architecture.json"
  
  # 2. Generate base documentation
  python coachntt.py docs generate \
    --types readme,api,architecture \
    --code-paths "$project_path" \
    --output "docs/${project_name}"
  
  # 3. Extract key decisions
  python coachntt.py memory list \
    --type decision \
    --filter "project=$project_name" \
    --format markdown \
    --output "docs/${project_name}/decisions.md"
  
  # 4. Create learning summary
  python coachntt.py memory list \
    --type learning \
    --filter "project=$project_name" \
    --format markdown \
    --output "docs/${project_name}/learnings.md"
  
  # 5. Generate visual graph
  GRAPH_ID=$(cat docs/${project_name}-architecture.json | jq -r '.graph_id')
  python coachntt.py graph export $GRAPH_ID mermaid \
    --output "docs/${project_name}/architecture-diagram.md"
  
  # 6. Create comprehensive index
  cat > "docs/${project_name}/index.md" << EOF
# $project_name Documentation

## Overview
Generated on: $(date)

## Contents
- [README](./README.md)
- [API Documentation](./api-docs.md)
- [Architecture](./architecture.md)
- [Architecture Diagram](./architecture-diagram.md)
- [Key Decisions](./decisions.md)
- [Learnings & Insights](./learnings.md)

## Quick Stats
- Total Memories: $(python coachntt.py memory list --filter "project=$project_name" --format json | jq 'length')
- Key Decisions: $(python coachntt.py memory list --type decision --filter "project=$project_name" --format json | jq 'length')
- Learnings: $(python coachntt.py memory list --type learning --filter "project=$project_name" --format json | jq 'length')
EOF

  echo "Documentation generated in docs/${project_name}/"
}
```

### Team Knowledge Sharing

Enable team collaboration:

```python
#!/usr/bin/env python
# team_knowledge_share.py

import json
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

class TeamKnowledgeSharer:
    def __init__(self, team_members: list):
        self.team_members = team_members
    
    def generate_team_digest(self, days: int = 7):
        """Generate weekly team knowledge digest."""
        print(f"=== Team Knowledge Digest (Last {days} Days) ===\n")
        
        # Get recent memories
        cmd = f"python coachntt.py memory list --since {days} --format json --limit 200"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        memories = json.loads(result.stdout)
        
        # Categorize by type and author
        by_type = defaultdict(list)
        by_author = defaultdict(list)
        
        for memory in memories:
            by_type[memory['memory_type']].append(memory)
            author = memory.get('metadata', {}).get('author', 'unknown')
            by_author[author].append(memory)
        
        # Generate digest sections
        self._generate_learnings_section(by_type.get('learning', []))
        self._generate_decisions_section(by_type.get('decision', []))
        self._generate_bugs_section(by_type.get('debug', []))
        self._generate_author_contributions(by_author)
        
        # Create digest memory
        self._store_digest(days)
    
    def _generate_learnings_section(self, learnings):
        """Generate learnings section."""
        if not learnings:
            return
            
        print("## 📚 Key Learnings\n")
        
        # Group by topic
        by_topic = defaultdict(list)
        for learning in learnings:
            topic = learning.get('metadata', {}).get('topic', 'general')
            by_topic[topic].append(learning)
        
        for topic, items in sorted(by_topic.items()):
            print(f"### {topic.title()}")
            for item in items[:3]:  # Top 3 per topic
                print(f"- {item['prompt']}")
            print()
    
    def _generate_decisions_section(self, decisions):
        """Generate decisions section."""
        if not decisions:
            return
            
        print("## 🎯 Important Decisions\n")
        
        for decision in sorted(decisions, 
                               key=lambda x: x.get('metadata', {}).get('impact', ''), 
                               reverse=True)[:5]:
            print(f"**{decision['prompt']}**")
            print(f"Impact: {decision.get('metadata', {}).get('impact', 'unknown')}")
            print(f"Date: {decision['created_at'][:10]}")
            print()
    
    def _generate_bugs_section(self, bugs):
        """Generate bugs section."""
        if not bugs:
            return
            
        print("## 🐛 Bugs Resolved\n")
        
        resolved = [b for b in bugs if b.get('metadata', {}).get('status') == 'resolved']
        open_bugs = [b for b in bugs if b.get('metadata', {}).get('status') == 'open']
        
        print(f"Resolved: {len(resolved)}, Open: {len(open_bugs)}\n")
        
        if resolved:
            print("### Recently Resolved")
            for bug in resolved[:5]:
                print(f"- {bug['prompt']}")
    
    def _generate_author_contributions(self, by_author):
        """Generate author contributions."""
        print("\n## 👥 Team Contributions\n")
        
        for author, memories in sorted(by_author.items(), 
                                     key=lambda x: len(x[1]), 
                                     reverse=True):
            if author != 'unknown':
                print(f"**{author}**: {len(memories)} contributions")
                
                # Show top contribution
                if memories:
                    top_memory = max(memories, 
                                   key=lambda x: x.get('safety_score', 0))
                    print(f"  Best: {top_memory['prompt'][:50]}...")
        print()
    
    def _store_digest(self, days):
        """Store digest as memory."""
        digest_date = datetime.now().strftime('%Y-%m-%d')
        
        cmd = [
            "python", "coachntt.py", "memory", "create",
            f"Team Knowledge Digest - {digest_date}",
            f"Weekly digest of team knowledge for past {days} days. Shared with team.",
            "--type", "context",
            "--metadata", f"digest_type=weekly",
            "--metadata", f"days={days}",
            "--metadata", f"team_size={len(self.team_members)}"
        ]
        subprocess.run(cmd)
    
    def share_knowledge_graph(self):
        """Build and share team knowledge graph."""
        print("Building team knowledge graph...")
        
        # Build comprehensive graph
        cmd = [
            "python", "coachntt.py", "graph", "build",
            "--max-memories", "500",
            "--max-nodes", "300",
            "--name", f"Team Knowledge Graph - {datetime.now().strftime('%Y-%m-%d')}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Export for sharing
            graph_data = json.loads(result.stdout)
            graph_id = graph_data.get('graph_id')
            
            # Export in multiple formats
            formats = ['mermaid', 'json', 'd3']
            for fmt in formats:
                cmd = [
                    "python", "coachntt.py", "graph", "export",
                    graph_id, fmt,
                    "--output", f"team-graph.{fmt}"
                ]
                subprocess.run(cmd)
            
            print(f"Team knowledge graph exported in {len(formats)} formats")

# Usage
if __name__ == "__main__":
    team = TeamKnowledgeSharer(['alice', 'bob', 'charlie'])
    team.generate_team_digest(7)
    team.share_knowledge_graph()
```

## 💡 Productivity Tips

### Keyboard Shortcuts and Aliases

Add to your shell configuration:

```bash
# ~/.bashrc or ~/.zshrc

# CoachNTT.ai aliases
alias ccp='python coachntt.py'
alias ccps='python coachntt.py status'
alias ccpm='python coachntt.py memory'
alias ccpml='python coachntt.py memory list'
alias ccpmc='python coachntt.py memory create'
alias ccpms='python coachntt.py memory search'
alias ccpg='python coachntt.py graph'
alias ccpgb='python coachntt.py graph build'
alias ccpv='python coachntt.py sync vault'
alias ccpi='python coachntt.py interactive'

# Quick memory creation function
mem() {
    python coachntt.py memory create "$1" "$2" --type "${3:-learning}"
}

# Quick search function
search() {
    python coachntt.py memory search "$1" --limit 10
}

# Daily summary function
daily() {
    python coachntt.py checkpoint create "Daily Summary $(date +%Y-%m-%d)" \
        --description "$1" \
        --memory-filters "created_today=true"
}
```

### Time-Saving Techniques

#### Template-Based Memory Creation
```bash
# Create memory templates
cat > ~/.ccp_templates/bug.json << 'EOF'
{
  "type": "debug",
  "metadata": {
    "severity": "$SEVERITY",
    "component": "$COMPONENT",
    "status": "open",
    "discovered_at": "$TIMESTAMP"
  }
}
EOF

# Use template
ccp_bug() {
    local title="$1"
    local description="$2"
    local severity="${3:-medium}"
    local component="${4:-unknown}"
    
    SEVERITY=$severity COMPONENT=$component TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    envsubst < ~/.ccp_templates/bug.json > /tmp/bug_meta.json
    
    python coachntt.py memory create "Bug: $title" "$description" \
        --type debug \
        --metadata-file /tmp/bug_meta.json
}
```

#### Batch Processing Functions
```bash
# Process multiple files
ccp_analyze_dir() {
    local dir="$1"
    find "$dir" -name "*.py" -type f | while read file; do
        echo "Analyzing: $file"
        python coachntt.py memory create \
            "Code Analysis: $(basename $file)" \
            "Analyzed Python file for patterns and structure" \
            --type context \
            --metadata file=$file \
            --metadata language=python
    done
}

# Bulk reinforcement
ccp_reinforce_important() {
    python coachntt.py memory list \
        --type learning \
        --metadata importance=high \
        --format json | \
    jq -r '.[] | .id' | \
    xargs -I {} python coachntt.py memory reinforce {}
}
```

### Interactive Mode Productivity

#### Custom Interactive Commands
```python
# ~/.ccp_custom_commands.py

def custom_commands(cli):
    """Add custom commands to interactive CLI."""
    
    @cli.command()
    def today():
        """Show today's activity."""
        cli.run_command("memory list --since 1 --limit 20")
    
    @cli.command()
    def learn(topic: str, content: str):
        """Quick learning capture."""
        cli.run_command(f'memory create "{topic}" "{content}" --type learning')
    
    @cli.command()
    def bug(title: str, description: str):
        """Quick bug capture."""
        cli.run_command(f'memory create "Bug: {title}" "{description}" --type debug')
    
    @cli.command()
    def weekly():
        """Generate weekly summary."""
        cli.run_command("checkpoint create 'Weekly Summary' --memory-filters created_this_week=true")
```

## 🔧 Maintenance and Optimization

### Regular Cleanup Routines

#### Weekly Maintenance Script
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== CoachNTT.ai Weekly Maintenance ==="

# 1. Clean up low-quality memories
echo "Checking for low-quality memories..."
LOW_QUALITY=$(python coachntt.py memory list --format json | \
  jq '.[] | select(.safety_score < 0.85) | .id' | wc -l)

if [ $LOW_QUALITY -gt 0 ]; then
    echo "Found $LOW_QUALITY low-quality memories"
    python coachntt.py memory list --format json | \
      jq '.[] | select(.safety_score < 0.85) | {id, prompt, safety_score}' | \
      jq -s '.' > low_quality_memories.json
    echo "Review low_quality_memories.json for cleanup"
fi

# 2. Optimize database
echo "Optimizing database..."
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner << EOF
VACUUM ANALYZE memories;
VACUUM ANALYZE graph_nodes;
VACUUM ANALYZE graph_edges;
REINDEX TABLE memories;
EOF

# 3. Clear old caches
echo "Clearing old caches..."
find ~/.coachntt/cache -type f -mtime +7 -delete 2>/dev/null

# 4. Archive old memories
echo "Archiving old memories..."
python coachntt.py memory export \
  --format json \
  --filter "created_before=90d" \
  --output "archives/memories-$(date +%Y%m%d).json"

# 5. Generate maintenance report
cat > maintenance-report-$(date +%Y%m%d).md << EOF
# Maintenance Report - $(date +%Y-%m-%d)

## Statistics
- Total Memories: $(python coachntt.py memory list --format json | jq 'length')
- Low Quality Memories: $LOW_QUALITY
- Database Size: $(docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -t -c "SELECT pg_size_pretty(pg_database_size('cognitive_coding_partner'));")

## Actions Taken
- Database vacuum and reindex completed
- Cache cleanup completed
- Memory archive created

## Recommendations
$([ $LOW_QUALITY -gt 10 ] && echo "- Review and clean up low-quality memories")
$([ $(python coachntt.py memory list --format json | jq 'length') -gt 10000 ] && echo "- Consider archiving older memories")
EOF

echo "Maintenance complete. Report saved to maintenance-report-$(date +%Y%m%d).md"
```

### Performance Monitoring

#### System Performance Dashboard
```python
#!/usr/bin/env python
# performance_monitor.py

import subprocess
import json
import time
import statistics
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.results = {
            'memory_create': [],
            'memory_search': [],
            'graph_build': [],
            'api_health': []
        }
    
    def run_performance_tests(self):
        """Run performance benchmarks."""
        print("=== CoachNTT.ai Performance Test ===")
        print(f"Started: {datetime.now()}\n")
        
        # Test memory creation
        self._test_memory_creation()
        
        # Test memory search
        self._test_memory_search()
        
        # Test graph building
        self._test_graph_building()
        
        # Test API responsiveness
        self._test_api_health()
        
        # Generate report
        self._generate_report()
    
    def _test_memory_creation(self, iterations=5):
        """Test memory creation performance."""
        print("Testing memory creation...")
        
        for i in range(iterations):
            start = time.time()
            cmd = [
                "python", "coachntt.py", "memory", "create",
                f"Performance Test {i}",
                "Test content for performance measurement",
                "--type", "context"
            ]
            result = subprocess.run(cmd, capture_output=True)
            elapsed = time.time() - start
            
            if result.returncode == 0:
                self.results['memory_create'].append(elapsed)
        
        avg_time = statistics.mean(self.results['memory_create'])
        print(f"  Average time: {avg_time:.3f}s")
    
    def _test_memory_search(self, iterations=5):
        """Test memory search performance."""
        print("\nTesting memory search...")
        
        queries = ["test", "performance", "optimization", "learning", "debug"]
        
        for query in queries:
            start = time.time()
            cmd = f"python coachntt.py memory search '{query}' --limit 50"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            elapsed = time.time() - start
            
            if result.returncode == 0:
                self.results['memory_search'].append(elapsed)
        
        avg_time = statistics.mean(self.results['memory_search'])
        print(f"  Average time: {avg_time:.3f}s")
    
    def _test_graph_building(self):
        """Test graph building performance."""
        print("\nTesting graph building...")
        
        node_counts = [10, 50, 100]
        
        for nodes in node_counts:
            start = time.time()
            cmd = f"python coachntt.py graph build --max-nodes {nodes}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            elapsed = time.time() - start
            
            if result.returncode == 0:
                self.results['graph_build'].append({
                    'nodes': nodes,
                    'time': elapsed
                })
                print(f"  {nodes} nodes: {elapsed:.3f}s")
    
    def _test_api_health(self):
        """Test API responsiveness."""
        print("\nTesting API health...")
        
        for i in range(5):
            start = time.time()
            cmd = "curl -s http://localhost:8000/health"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            elapsed = time.time() - start
            
            if result.returncode == 0:
                self.results['api_health'].append(elapsed)
            
            time.sleep(0.5)  # Don't hammer the API
        
        avg_time = statistics.mean(self.results['api_health'])
        print(f"  Average response time: {avg_time*1000:.1f}ms")
    
    def _generate_report(self):
        """Generate performance report."""
        print("\n=== Performance Summary ===")
        
        # Check against targets
        targets = {
            'memory_create': 0.5,  # 500ms
            'memory_search': 0.2,  # 200ms
            'api_health': 0.05     # 50ms
        }
        
        issues = []
        
        for operation, times in self.results.items():
            if isinstance(times, list) and times and operation in targets:
                avg = statistics.mean(times)
                if avg > targets[operation]:
                    issues.append(f"{operation}: {avg:.3f}s (target: {targets[operation]}s)")
        
        if issues:
            print("\n⚠️  Performance Issues Detected:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ All performance targets met!")
        
        # Store results
        self._store_results()
    
    def _store_results(self):
        """Store performance results in memory."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'results': {
                'memory_create_avg': statistics.mean(self.results['memory_create']),
                'memory_search_avg': statistics.mean(self.results['memory_search']),
                'api_health_avg': statistics.mean(self.results['api_health'])
            }
        }
        
        cmd = [
            "python", "coachntt.py", "memory", "create",
            f"Performance Test - {datetime.now().strftime('%Y-%m-%d')}",
            json.dumps(summary, indent=2),
            "--type", "context",
            "--metadata", "test_type=performance",
            "--metadata", f"timestamp={summary['timestamp']}"
        ]
        subprocess.run(cmd)

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.run_performance_tests()
```

### Backup Strategies

#### Automated Backup System
```bash
#!/bin/bash
# backup_strategy.sh

# Configuration
BACKUP_DIR="/backup/coachntt"
RETENTION_DAYS=30

# Create timestamped backup
create_backup() {
    local backup_name="coachntt-backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    
    echo "Creating backup: $backup_name"
    
    # 1. Export all memories
    python coachntt.py memory export \
        --format json \
        --output "$backup_path/memories.json" \
        --include-metadata
    
    # 2. Export all graphs
    python coachntt.py graph list --format json > "$backup_path/graphs-list.json"
    
    # Export each graph
    cat "$backup_path/graphs-list.json" | jq -r '.[].id' | while read graph_id; do
        python coachntt.py graph export $graph_id json \
            --output "$backup_path/graph-$graph_id.json" \
            --include-metadata
    done
    
    # 3. Backup database
    docker-compose exec -T postgres pg_dump -U ccp_user cognitive_coding_partner | \
        gzip > "$backup_path/database.sql.gz"
    
    # 4. Backup configuration
    cp -r .env config/ "$backup_path/"
    
    # 5. Backup vault
    tar -czf "$backup_path/vault.tar.gz" vault/
    
    # 6. Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "version": "$(python coachntt.py version --json | jq -r '.version')",
    "statistics": {
        "total_memories": $(python coachntt.py memory list --format json | jq 'length'),
        "total_graphs": $(cat "$backup_path/graphs-list.json" | jq 'length'),
        "database_size": "$(docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -t -c "SELECT pg_size_pretty(pg_database_size('cognitive_coding_partner'));")"
    }
}
EOF
    
    # Compress entire backup
    tar -czf "$backup_path.tar.gz" -C "$BACKUP_DIR" "$backup_name"
    rm -rf "$backup_path"
    
    echo "Backup complete: $backup_path.tar.gz"
    
    # Clean old backups
    find "$BACKUP_DIR" -name "coachntt-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete
}

# Restore from backup
restore_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        echo "Backup file not found: $backup_file"
        exit 1
    fi
    
    echo "WARNING: This will overwrite current data!"
    read -p "Continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
    
    # Extract backup
    local temp_dir="/tmp/coachntt-restore-$$"
    mkdir -p "$temp_dir"
    tar -xzf "$backup_file" -C "$temp_dir"
    
    local backup_dir=$(ls "$temp_dir")
    
    # Show manifest
    echo "Backup Information:"
    cat "$temp_dir/$backup_dir/manifest.json" | jq .
    
    # Restore database
    echo "Restoring database..."
    gunzip -c "$temp_dir/$backup_dir/database.sql.gz" | \
        docker-compose exec -T postgres psql -U ccp_user -d cognitive_coding_partner
    
    # Restore vault
    echo "Restoring vault..."
    tar -xzf "$temp_dir/$backup_dir/vault.tar.gz" -C .
    
    # Clean up
    rm -rf "$temp_dir"
    
    echo "Restore complete!"
}

# Main
case "$1" in
    create)
        create_backup
        ;;
    restore)
        restore_backup "$2"
        ;;
    *)
        echo "Usage: $0 {create|restore <backup_file>}"
        exit 1
        ;;
esac
```

## 🎯 Continuous Improvement

### Personal Productivity Metrics

Track your CoachNTT.ai usage and improve:

```python
#!/usr/bin/env python
# productivity_metrics.py

import subprocess
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import matplotlib.pyplot as plt

class ProductivityAnalyzer:
    def analyze_usage(self, days=30):
        """Analyze CoachNTT.ai usage patterns."""
        
        # Get memories from period
        cmd = f"python coachntt.py memory list --since {days} --format json --limit 1000"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        memories = json.loads(result.stdout)
        
        # Analyze patterns
        self._analyze_time_patterns(memories)
        self._analyze_type_distribution(memories)
        self._analyze_quality_trends(memories)
        self._generate_recommendations(memories)
    
    def _analyze_time_patterns(self, memories):
        """Analyze when you're most productive."""
        hour_counts = Counter()
        day_counts = Counter()
        
        for memory in memories:
            created = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
            hour_counts[created.hour] += 1
            day_counts[created.strftime('%A')] += 1
        
        # Find peak hours
        peak_hours = hour_counts.most_common(3)
        print("🕐 Peak Productivity Hours:")
        for hour, count in peak_hours:
            print(f"  {hour:02d}:00 - {count} memories")
        
        # Most productive days
        print("\n📅 Most Productive Days:")
        for day, count in day_counts.most_common(3):
            print(f"  {day}: {count} memories")
    
    def _analyze_type_distribution(self, memories):
        """Analyze memory type balance."""
        type_counts = Counter(m['memory_type'] for m in memories)
        total = sum(type_counts.values())
        
        print("\n📊 Memory Type Distribution:")
        for mem_type, count in type_counts.most_common():
            percentage = (count / total) * 100
            print(f"  {mem_type}: {count} ({percentage:.1f}%)")
        
        # Check balance
        if type_counts['learning'] < type_counts['debug']:
            print("\n💡 Tip: You're debugging more than learning. Consider documenting solutions as learnings.")
    
    def _analyze_quality_trends(self, memories):
        """Analyze quality score trends."""
        scores_by_week = defaultdict(list)
        
        for memory in memories:
            created = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
            week = created.isocalendar()[1]
            scores_by_week[week].append(memory['safety_score'])
        
        print("\n📈 Quality Score Trends (by week):")
        for week in sorted(scores_by_week.keys())[-4:]:
            avg_score = sum(scores_by_week[week]) / len(scores_by_week[week])
            print(f"  Week {week}: {avg_score:.3f}")
    
    def _generate_recommendations(self, memories):
        """Generate personalized recommendations."""
        print("\n🎯 Personalized Recommendations:")
        
        # Check for metadata usage
        with_metadata = sum(1 for m in memories if m.get('metadata'))
        metadata_percentage = (with_metadata / len(memories)) * 100
        
        if metadata_percentage < 50:
            print("  - Add more metadata to memories for better organization")
        
        # Check for regular reviews
        week_old = datetime.now() - timedelta(days=7)
        recent = sum(1 for m in memories 
                    if datetime.fromisoformat(m['created_at'].replace('Z', '+00:00')) > week_old)
        
        if recent < 10:
            print("  - You've created fewer memories recently. Stay consistent!")
        
        # Check for graph usage
        graphs = subprocess.run(
            "python coachntt.py graph list --format json",
            shell=True, capture_output=True, text=True
        )
        graph_count = len(json.loads(graphs.stdout))
        
        if graph_count < 5:
            print("  - Build more knowledge graphs to discover patterns")

if __name__ == "__main__":
    analyzer = ProductivityAnalyzer()
    analyzer.analyze_usage(30)
```

---

**Effective Usage Mastered!** 🚀

This guide provides practical, real-world patterns for integrating CoachNTT.ai into your daily development workflow. The key to success is consistency - use it daily, capture everything important, and regularly review your accumulated knowledge. Over time, CoachNTT.ai becomes your personalized knowledge companion that grows smarter with every interaction.