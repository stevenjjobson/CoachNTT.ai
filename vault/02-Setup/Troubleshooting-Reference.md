# 🔧 CoachNTT.ai Troubleshooting Reference

## 📋 Overview

This comprehensive troubleshooting guide helps you diagnose and resolve common issues with the CoachNTT.ai system. Use this reference for quick problem resolution and system optimization.

## 🚨 Quick Diagnostic Commands

### System Health Check
```bash
# Comprehensive system status
python coachntt.py status --detailed --json

# API server health
curl -s http://localhost:8000/health | jq .

# Database connectivity
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "SELECT version();"

# Safety system validation
python -c "
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
engine = ConcreteAbstractionEngine()
result = engine.process_content('Test /path/example')
print(f'Safety score: {result.safety_score}')
"
```

### Configuration Verification
```bash
# Show current CLI configuration
python coachntt.py config show --format json

# Validate environment variables
env | grep -E "(POSTGRES|API|JWT|SAFETY)" | sort

# Check Docker services
docker-compose ps
docker-compose logs --tail=50
```

## 🔴 Common Issues and Solutions

### Installation and Setup Issues

#### Issue: "Python module not found"
**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'CLIEngine'
```

**Solutions:**
```bash
# Verify you're in the correct directory
pwd
ls -la | grep coachntt.py

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Verify virtual environment
which python
python --version
```

#### Issue: "Docker services won't start"
**Symptoms:**
```
ERROR: Couldn't connect to Docker daemon
postgresql container exits immediately
```

**Solutions:**
```bash
# Check Docker daemon
sudo systemctl status docker
sudo systemctl start docker

# Verify Docker Compose
docker-compose --version

# Check permissions
sudo usermod -aG docker $USER
# Log out and back in

# Clean and restart
docker-compose down -v
docker system prune -f
docker-compose up -d

# Check logs
docker-compose logs postgres
```

#### Issue: "Database connection failed"
**Symptoms:**
```
asyncpg.exceptions.ConnectionDoesNotExistError
Connection to localhost:5432 refused
```

**Solutions:**
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U ccp_user

# Verify environment variables
echo $POSTGRES_PASSWORD
echo $POSTGRES_USER
echo $POSTGRES_DB

# Test connection directly
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner

# Check port binding
netstat -tlnp | grep 5432
lsof -i :5432

# Reset database
docker-compose down -v
docker-compose up -d postgres
# Wait 30 seconds
./scripts/database/init-secure.sh
```

### API and CLI Issues

#### Issue: "API server not responding"
**Symptoms:**
```
ConnectionError: Connection refused
HTTP 500 Internal Server Error
Timeout errors
```

**Solutions:**
```bash
# Check if API server is running
curl -s http://localhost:8000/health

# Start API server manually
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Check API logs
tail -f logs/coachntt.log

# Verify dependencies
pip check
python -c "import fastapi, uvicorn; print('API deps OK')"

# Test with debug mode
DEBUG=true python -m uvicorn src.api.main:app --reload --log-level debug
```

#### Issue: "CLI commands not working"
**Symptoms:**
```
Command 'coachntt' not found
Click module errors
Authentication failures
```

**Solutions:**
```bash
# Verify CLI entry point
python coachntt.py --help

# Check Click installation
python -c "import click; print(f'Click version: {click.__version__}')"

# Test basic CLI
python coachntt.py status

# Check configuration
python coachntt.py config show

# Reset configuration
python coachntt.py config reset

# Debug mode
python coachntt.py status --debug
```

#### Issue: "Authentication/Authorization errors"
**Symptoms:**
```
HTTP 401 Unauthorized
JWT token expired
Invalid API key
```

**Solutions:**
```bash
# Check JWT configuration
echo $JWT_SECRET_KEY | wc -c  # Should be >32 characters

# Generate new JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Test without authentication
curl -s http://localhost:8000/docs

# Check API key configuration
echo $API_KEYS

# Reset authentication
python coachntt.py config set api_base_url http://localhost:8000
```

### Memory and Safety Issues

#### Issue: "Safety validation failures"
**Symptoms:**
```
Safety score too low: 0.6
Concrete references detected
Content safety validation failed
```

**Solutions:**
```bash
# Test safety engine
python -c "
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
engine = ConcreteAbstractionEngine()
content = 'This is test content'  # Use safe content
result = engine.process_content(content)
print(f'Score: {result.safety_score}, Content: {result.content}')
"

# Check safety configuration
echo $SAFETY_MIN_SCORE
echo $ABSTRACTION_PLACEHOLDER_FORMAT

# Test with simple content
python coachntt.py memory create "Safe Test" "This is completely safe content with no concrete references"

# Review safety patterns
python -c "
from src.core.abstraction.rules import AbstractionRules
rules = AbstractionRules()
print(f'Loaded {len(rules.patterns)} patterns')
"
```

#### Issue: "Memory operations slow"
**Symptoms:**
```
Memory search takes >5 seconds
Graph building times out
High memory usage
```

**Solutions:**
```bash
# Check database performance
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename = 'memories';
"

# Verify indexes
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'memories';
"

# Check memory count
python coachntt.py memory list --format json | jq 'length'

# Test with smaller datasets
python coachntt.py memory list --limit 10

# Check embedding cache
python -c "
from src.core.embeddings.service import EmbeddingService
service = EmbeddingService()
print(f'Cache stats: {service.cache.info()}')
"

# Optimize database
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "VACUUM ANALYZE memories;"
```

### Knowledge Graph Issues

#### Issue: "Graph building fails"
**Symptoms:**
```
Graph building timeout
Memory allocation errors
Empty graph generated
```

**Solutions:**
```bash
# Start with small graph
python coachntt.py graph build --max-memories 10 --max-nodes 10

# Check memory quality
python coachntt.py memory list --format json | jq '.[] | select(.safety_score < 0.8) | .id'

# Test embedding service
python -c "
from src.core.embeddings.service import EmbeddingService
service = EmbeddingService()
import asyncio
async def test():
    result = await service.generate_embedding('test content')
    print(f'Embedding length: {len(result)}')
asyncio.run(test())
"

# Monitor memory usage
python coachntt.py graph build --max-nodes 50 --debug
```

#### Issue: "Graph queries return no results"
**Symptoms:**
```
Empty query results
No matching patterns
Graph not found errors
```

**Solutions:**
```bash
# List available graphs
python coachntt.py graph list

# Check graph content
python coachntt.py graph show GRAPH_ID --format json

# Test simple query
python coachntt.py graph query GRAPH_ID --max-nodes 5

# Lower similarity threshold
python coachntt.py graph query GRAPH_ID --pattern "test" --min-weight 0.3

# Debug graph structure
python coachntt.py graph export GRAPH_ID json --output debug-graph.json
cat debug-graph.json | jq '.nodes | length'
```

### Integration Issues

#### Issue: "Vault sync failures"
**Symptoms:**
```
Vault path not found
Markdown parsing errors
Template processing failures
```

**Solutions:**
```bash
# Verify vault path
ls -la ./vault/
echo $VAULT_PATH

# Check vault structure
find ./vault -name "*.md" | head -5

# Test dry run
python coachntt.py sync vault --dry-run --debug

# Check template files
ls -la ./vault/05-Templates/

# Test with simple content
python coachntt.py memory create "Vault Test" "Simple content for vault sync test"
python coachntt.py sync vault --direction to-vault --max-memories 1
```

#### Issue: "Documentation generation fails"
**Symptoms:**
```
AST parsing errors
Template not found
File permission errors
```

**Solutions:**
```bash
# Check output directory permissions
ls -ld ./docs/
mkdir -p ./docs/generated
chmod 755 ./docs/generated

# Test with basic generation
python coachntt.py docs generate --types readme --output ./test-docs

# Check AST analyzer
python -c "
from src.core.analysis.ast_analyzer import ASTAnalyzer
analyzer = ASTAnalyzer()
result = analyzer.analyze_file('coachntt.py')
print(f'AST analysis successful: {result is not None}')
"

# Verify templates
ls -la ./src/services/documentation/templates/
```

### Performance Issues

#### Issue: "System running slowly"
**Symptoms:**
```
High CPU usage
Memory leaks
Slow response times
```

**Solutions:**
```bash
# Monitor system resources
top -p $(pgrep -f "python.*coachntt")
docker stats

# Check database connections
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';
"

# Clear caches
python -c "
from src.core.embeddings.cache import EmbeddingCache
cache = EmbeddingCache()
cache.clear()
print('Cache cleared')
"

# Optimize queries
python coachntt.py memory list --limit 10 --format simple

# Check for memory leaks
python -c "
import psutil, os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## 🔧 Advanced Troubleshooting

### Database Maintenance

#### Vacuum and Analyze
```sql
-- Connect to database
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner

-- Vacuum and analyze
VACUUM ANALYZE memories;
VACUUM ANALYZE graph_nodes;
VACUUM ANALYZE safety_validation_log;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Index Optimization
```sql
-- Check index usage
SELECT 
    indexrelname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Rebuild indexes if needed
REINDEX TABLE memories;
```

### Safety System Debugging

#### Validate Safety Engine
```python
# test_safety.py
import asyncio
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
from src.core.validation.validator import SafetyValidator

async def test_safety():
    engine = ConcreteAbstractionEngine()
    validator = SafetyValidator()
    
    test_cases = [
        "Safe content with no references",
        "Content with /path/to/file",
        "Content with user123@example.com",
        "Content with http://example.com/page"
    ]
    
    for content in test_cases:
        result = engine.process_content(content)
        validation = await validator.validate(content)
        
        print(f"Content: {content[:30]}...")
        print(f"  Abstracted: {result.content[:30]}...")
        print(f"  Safety Score: {result.safety_score}")
        print(f"  Validation: {validation.is_valid}")
        print()

if __name__ == "__main__":
    asyncio.run(test_safety())
```

### Network and Connectivity

#### Port and Service Checks
```bash
# Check listening ports
netstat -tlnp | grep -E "(5432|8000|6432)"

# Test internal connectivity
docker-compose exec postgres nc -z localhost 5432
docker network ls
docker network inspect coachntt_ccp_network

# DNS resolution
nslookup postgres
ping -c 3 postgres

# Firewall check
sudo ufw status
sudo iptables -L | grep -E "(5432|8000)"
```

### Log Analysis

#### Centralized Log Checking
```bash
# Application logs
tail -f logs/coachntt.log | grep -i error

# Docker logs
docker-compose logs --tail=100 --follow postgres
docker-compose logs --tail=100 --follow pgbouncer

# System logs
journalctl -u docker --since "1 hour ago"
dmesg | grep -i error

# Custom log analysis
grep -r "ERROR\|CRITICAL" logs/
grep -r "safety.*score.*0\.[0-7]" logs/
```

## 🚀 Performance Optimization

### Memory Usage Optimization
```bash
# Monitor memory usage
python -c "
import psutil
import gc
gc.collect()
memory_info = psutil.virtual_memory()
print(f'Available memory: {memory_info.available / 1024**3:.1f} GB')
print(f'Memory usage: {memory_info.percent}%')
"

# Optimize embedding cache
python -c "
from src.core.embeddings.service import EmbeddingService
service = EmbeddingService()
service.cache.clear()
service.cache.maxsize = 5000  # Reduce cache size
"
```

### Database Performance Tuning
```sql
-- Check slow queries
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check table statistics
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_tup_hot_upd
FROM pg_stat_user_tables
WHERE schemaname = 'public';
```

## 📊 Monitoring and Alerting

### Health Monitoring Script
```bash
#!/bin/bash
# health_monitor.sh

echo "=== CoachNTT.ai Health Check ==="
echo "Timestamp: $(date)"
echo

# API Health
echo "API Health:"
if curl -s http://localhost:8000/health >/dev/null; then
    echo "  ✅ API server responsive"
else
    echo "  ❌ API server not responding"
fi

# Database Health
echo "Database Health:"
if docker-compose exec -T postgres pg_isready -U ccp_user >/dev/null 2>&1; then
    echo "  ✅ PostgreSQL responsive"
else
    echo "  ❌ PostgreSQL not responding"
fi

# CLI Health
echo "CLI Health:"
if python coachntt.py status >/dev/null 2>&1; then
    echo "  ✅ CLI functional"
else
    echo "  ❌ CLI not functional"
fi

# Safety System Health
echo "Safety System:"
safety_score=$(python -c "
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
engine = ConcreteAbstractionEngine()
result = engine.process_content('test content')
print(result.safety_score)
" 2>/dev/null)

if [ $(echo "$safety_score > 0.8" | bc -l) -eq 1 ]; then
    echo "  ✅ Safety system operational"
else
    echo "  ❌ Safety system issues"
fi

echo
echo "=== End Health Check ==="
```

### Automated Monitoring
```bash
# Add to crontab for regular monitoring
# */5 * * * * /path/to/health_monitor.sh >> /var/log/coachntt-health.log 2>&1

# Create systemd service for continuous monitoring
sudo tee /etc/systemd/system/coachntt-monitor.service << EOF
[Unit]
Description=CoachNTT.ai Health Monitor
After=docker.service

[Service]
Type=simple
ExecStart=/path/to/health_monitor.sh
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable coachntt-monitor
sudo systemctl start coachntt-monitor
```

## 🆘 Emergency Recovery Procedures

### Complete System Reset
```bash
#!/bin/bash
# emergency_reset.sh

echo "WARNING: This will reset the entire CoachNTT.ai system!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo "Stopping all services..."
    docker-compose down -v
    
    echo "Cleaning Docker resources..."
    docker system prune -f
    docker volume prune -f
    
    echo "Removing data directories..."
    sudo rm -rf data/
    
    echo "Clearing Python cache..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find . -name "*.pyc" -delete 2>/dev/null
    
    echo "Recreating environment..."
    mkdir -p data/{postgres,postgres-logs,postgres-audit,postgres-backups,pgbouncer-logs}
    
    echo "Starting fresh system..."
    docker-compose up -d
    
    echo "Waiting for database..."
    sleep 30
    
    echo "Initializing database..."
    ./scripts/database/init-secure.sh
    
    echo "System reset complete!"
else
    echo "Reset cancelled."
fi
```

### Backup and Restore
```bash
# Create backup
#!/bin/bash
# backup_system.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating system backup in $BACKUP_DIR"

# Backup database
docker-compose exec -T postgres pg_dump -U ccp_user cognitive_coding_partner > "$BACKUP_DIR/database.sql"

# Backup configuration
cp .env "$BACKUP_DIR/"
cp -r config/ "$BACKUP_DIR/"

# Backup vault
cp -r vault/ "$BACKUP_DIR/"

# Backup memories
python coachntt.py memory export --format json --output "$BACKUP_DIR/memories.json"

# Backup graphs
python coachntt.py graph list --format json > "$BACKUP_DIR/graphs.json"

echo "Backup complete: $BACKUP_DIR"

# Restore from backup
#!/bin/bash
# restore_system.sh

BACKUP_DIR="$1"
if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "Restoring from $BACKUP_DIR"

# Restore database
docker-compose exec -T postgres psql -U ccp_user -d cognitive_coding_partner < "$BACKUP_DIR/database.sql"

# Restore configuration
cp "$BACKUP_DIR/.env" .
cp -r "$BACKUP_DIR/config/" .

# Restore vault
cp -r "$BACKUP_DIR/vault/" .

echo "Restore complete. Restart system to apply changes."
```

## 📞 Getting Additional Help

### Support Channels
1. **Documentation**: Check the master index first
2. **Logs**: Always include relevant log outputs
3. **Configuration**: Share sanitized configuration (remove secrets)
4. **System Info**: Include OS, Python version, Docker version
5. **Reproducible Steps**: Provide exact commands that trigger issues

### Reporting Issues
```bash
# Generate diagnostic report
#!/bin/bash
echo "=== CoachNTT.ai Diagnostic Report ==="
echo "Date: $(date)"
echo "OS: $(uname -a)"
echo "Python: $(python --version)"
echo "Docker: $(docker --version)"
echo "Docker Compose: $(docker-compose --version)"
echo
echo "=== System Status ==="
python coachntt.py status --detailed
echo
echo "=== Configuration ==="
python coachntt.py config show
echo
echo "=== Docker Services ==="
docker-compose ps
echo
echo "=== Recent Logs ==="
tail -50 logs/coachntt.log
```

---

**Troubleshooting Mastery Achieved!** 🔧

This comprehensive troubleshooting guide provides systematic approaches to diagnosing and resolving CoachNTT.ai issues. Keep this reference handy for quick problem resolution.