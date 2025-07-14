# 🚀 CoachNTT.ai Complete Setup Guide

## 📋 Overview

This comprehensive guide will walk you through setting up the complete CoachNTT.ai system - a safety-first AI development assistant featuring temporal memory, knowledge graphs, and automated development workflows.

## 🔧 System Requirements

### Minimum Requirements
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: 3.10 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space minimum, 10GB recommended
- **Docker**: Docker Engine 20.10+ and Docker Compose v2.0+

### Recommended Requirements
- **CPU**: 4+ cores for optimal performance
- **Memory**: 16GB RAM for large knowledge graphs
- **Storage**: SSD with 20GB+ free space
- **Network**: Stable internet connection for embeddings

## 📥 Installation Steps

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/stevenjjobson/CoachNTT.ai.git
cd CoachNTT.ai

# Verify repository structure
ls -la
```

**Expected structure:**
```
CoachNTT.ai/
├── src/                    # Core application code
├── cli/                    # Command-line interface
├── docs/                   # Documentation
├── scripts/               # Automation scripts
├── vault/                 # Knowledge base
├── docker-compose.yml     # Container orchestration
├── requirements.txt       # Python dependencies
└── coachntt.py           # Main CLI entry point
```

### Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Essential Environment Variables:**
```env
# Database Configuration
POSTGRES_USER=ccp_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=cognitive_coding_partner
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Safety Configuration
SAFETY_MIN_SCORE=0.8
ABSTRACTION_PLACEHOLDER_FORMAT=<{name}>
ENABLE_SAFETY_VALIDATION=true

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_CACHE_SIZE=10000
BATCH_SIZE=32

# Development Settings
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Step 3: Python Environment Setup

#### Option A: Using Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Using Conda
```bash
# Create conda environment
conda create -n coachntt python=3.10
conda activate coachntt

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Database Setup

#### Quick Setup with Docker (Recommended)
```bash
# Start database services
docker-compose up -d postgres pgbouncer

# Wait for services to be healthy
docker-compose ps

# Initialize database with safety schema
./scripts/database/init-secure.sh

# Verify database connection
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "SELECT version();"
```

#### Manual PostgreSQL Setup (Advanced)
```bash
# Install PostgreSQL and pgvector extension
sudo apt-get install postgresql-15 postgresql-contrib
sudo -u postgres psql -c "CREATE EXTENSION vector;"

# Create database and user
sudo -u postgres psql -c "CREATE USER ccp_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE cognitive_coding_partner OWNER ccp_user;"

# Run migrations
python -c "
import asyncio
from src.database.migrations import run_migrations
asyncio.run(run_migrations())
"
```

### Step 5: Verify Installation

```bash
# Test database connection
python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://ccp_user:password@localhost:5432/cognitive_coding_partner')
    result = await conn.fetchval('SELECT 1')
    print(f'Database connection: {"✅ Success" if result == 1 else "❌ Failed"}')
    await conn.close()
asyncio.run(test())
"

# Test CLI
python coachntt.py --help

# Test safety validation
python -c "
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
engine = ConcreteAbstractionEngine()
result = engine.process_content('This is a test with /path/to/file')
print(f'Abstraction test: {"✅ Success" if result.safety_score >= 0.8 else "❌ Failed"}')
"
```

## 🚀 First-Time Setup

### 1. Start Core Services

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps
docker-compose logs postgres
docker-compose logs pgbouncer
```

### 2. Initialize Database Schema

```bash
# Run safety-first migrations
python scripts/database/init-secure.sh

# Verify safety tables
python -c "
import asyncio
import asyncpg
async def verify():
    conn = await asyncpg.connect('postgresql://ccp_user:password@localhost:5432/cognitive_coding_partner')
    tables = await conn.fetch(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';\")
    safety_tables = [t['table_name'] for t in tables if 'safety' in t['table_name']]
    print(f'Safety tables: {safety_tables}')
    await conn.close()
asyncio.run(verify())
"
```

### 3. Start API Server

```bash
# Start FastAPI server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Test API endpoints
curl http://localhost:8000/docs
curl http://localhost:8000/health
```

### 4. Test CLI Interface

```bash
# Check system status
python coachntt.py status

# Test memory operations
python coachntt.py memory list

# Test configuration
python coachntt.py config show
```

## 🔍 Development Environment Setup

### 1. Development Tools

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Configure git hooks
cp scripts/git-hooks/pre-commit-docs .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### 2. IDE Configuration

#### VS Code Setup
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.associations": {
        "*.sql": "sql"
    }
}
```

#### PyCharm Setup
```yaml
# PyCharm configuration
interpreter: ./venv/bin/python
code_style: black
linter: flake8
test_runner: pytest
sql_dialect: postgresql
```

### 3. Testing Setup

```bash
# Run basic tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run performance tests
python -m pytest tests/performance/ -v

# Generate coverage report
python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## 📊 Verification Checklist

### ✅ Core Components
- [ ] Python environment activated and dependencies installed
- [ ] PostgreSQL database running with pgvector extension
- [ ] Environment variables configured correctly
- [ ] Safety validation tables created and functional
- [ ] API server starts without errors
- [ ] CLI commands respond correctly

### ✅ Safety Validation
- [ ] Abstraction engine processes content correctly (safety score ≥ 0.8)
- [ ] Database triggers prevent concrete references
- [ ] Memory validation pipeline operational
- [ ] Safety metrics collection active

### ✅ Integration Features
- [ ] Obsidian vault synchronization configured
- [ ] WebSocket connections functional
- [ ] Background task processing operational
- [ ] Authentication middleware active

### ✅ Performance Targets
- [ ] Memory operations complete in <500ms
- [ ] Graph building completes in <1s for 100 nodes
- [ ] API responses average <200ms
- [ ] Embedding cache hit rate >80%

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL status
docker-compose logs postgres

# Verify environment variables
echo $POSTGRES_PASSWORD

# Test direct connection
psql -h localhost -p 5432 -U ccp_user -d cognitive_coding_partner
```

#### Python Import Errors
```bash
# Verify Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

#### Permission Errors
```bash
# Fix Docker permissions
sudo chown -R $USER:$USER data/
sudo chmod -R 755 data/

# Fix script permissions
chmod +x scripts/database/*.sh
chmod +x scripts/development/*.sh
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Monitor database performance
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"
```

### Getting Help

1. **Check Logs**: Always start with `docker-compose logs [service]`
2. **Verify Configuration**: Use `python coachntt.py config show`
3. **Test Components**: Run `python coachntt.py status --detailed`
4. **Review Documentation**: Check `/docs` directory for specific guides
5. **Safety Validation**: Ensure safety score ≥ 0.8 with test scripts

## 🎯 Next Steps

After successful setup:

1. **Explore CLI Commands**: `python coachntt.py --help`
2. **Create First Memory**: `python coachntt.py memory create "Test" "My first memory"`
3. **Build Knowledge Graph**: `python coachntt.py graph build`
4. **Set Up Vault Sync**: Configure Obsidian integration
5. **Review Safety Metrics**: Monitor abstraction quality

## 📚 Additional Resources

- **Configuration Guide**: `vault/02-Setup/Configuration-Guide.md`
- **Usage Guide**: `vault/03-Knowledge/Usage-Guide.md`
- **API Documentation**: `http://localhost:8000/docs`
- **CLI Reference**: `docs/user-guide/cli-commands.md`
- **Architecture Overview**: `vault/03-Knowledge/Architecture-Guide.md`

---

**Setup Complete!** 🎉 

Your CoachNTT.ai system is now ready for cognitive coding assistance with safety-first design and comprehensive memory management.