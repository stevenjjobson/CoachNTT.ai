# ⚙️ CoachNTT.ai Configuration Guide

## 📋 Overview

This guide provides comprehensive configuration details for all components of the CoachNTT.ai system. Proper configuration ensures optimal performance, security, and safety validation across all system layers.

## 🔧 Environment Configuration

### Core Environment Variables

Create a `.env` file in the project root with these configurations:

```env
# ================================
# Database Configuration
# ================================

# PostgreSQL Connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=ccp_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=cognitive_coding_partner

# Connection Pool Settings
POSTGRES_MIN_CONNECTIONS=5
POSTGRES_MAX_CONNECTIONS=20
POSTGRES_COMMAND_TIMEOUT=30
POSTGRES_QUERY_TIMEOUT=60

# Database Security
POSTGRES_SSL_MODE=prefer
POSTGRES_SSL_CERT_PATH=
POSTGRES_SSL_KEY_PATH=
POSTGRES_SSL_CA_PATH=

# ================================
# API Server Configuration
# ================================

# Server Settings
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
API_RELOAD=true
API_DEBUG=false

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS=["*"]

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10
RATE_LIMIT_STORAGE_URL=memory://

# ================================
# Authentication & Security
# ================================

# JWT Configuration
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Keys (Optional)
API_KEY_HEADER=X-API-Key
API_KEYS=["your-api-key-1", "your-api-key-2"]

# Session Security
SESSION_SECRET_KEY=your-session-secret-key
SESSION_COOKIE_SECURE=false  # Set to true in production with HTTPS
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax

# ================================
# Safety & Validation Configuration
# ================================

# Safety Framework
SAFETY_MIN_SCORE=0.8
SAFETY_ENFORCEMENT_LEVEL=strict
SAFETY_AUTO_QUARANTINE=true
SAFETY_VALIDATION_TIMEOUT=5.0

# Abstraction Engine
ABSTRACTION_PLACEHOLDER_FORMAT=<{name}>
ABSTRACTION_PATTERN_CACHE_SIZE=1000
ABSTRACTION_MAX_DEPTH=10

# Content Validation
ENABLE_SAFETY_VALIDATION=true
ENABLE_CONTENT_SCANNING=true
CONTENT_MAX_LENGTH=1000000
REFERENCE_DETECTION_STRICT=true

# ================================
# Memory System Configuration
# ================================

# Memory Processing
MEMORY_MAX_BATCH_SIZE=100
MEMORY_PROCESSING_TIMEOUT=30.0
MEMORY_AUTO_CLUSTERING=true
MEMORY_DECAY_ENABLED=true

# Memory Validation
MEMORY_MIN_SAFETY_SCORE=0.8
MEMORY_VALIDATION_STAGES=5
MEMORY_AUTO_ABSTRACTION=true

# Memory Search
SEARCH_MAX_RESULTS=50
SEARCH_DEFAULT_LIMIT=10
SEARCH_MIN_SIMILARITY=0.3
SEARCH_BOOST_RECENT=0.2

# ================================
# Embedding Configuration
# ================================

# Model Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_MAX_LENGTH=512
EMBEDDING_NORMALIZE=true

# Caching
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_SIZE=10000
EMBEDDING_CACHE_TTL=3600
EMBEDDING_CACHE_TYPE=lru

# Batch Processing
EMBEDDING_BATCH_SIZE=32
EMBEDDING_MAX_WORKERS=4
EMBEDDING_TIMEOUT=30.0

# ================================
# Knowledge Graph Configuration
# ================================

# Graph Building
GRAPH_MAX_NODES=1000
GRAPH_MAX_EDGES=5000
GRAPH_SIMILARITY_THRESHOLD=0.7
GRAPH_MIN_WEIGHT=0.1

# Graph Processing
GRAPH_CLUSTERING_ENABLED=true
GRAPH_CENTRALITY_CALCULATION=true
GRAPH_COMMUNITY_DETECTION=true
GRAPH_LAYOUT_ALGORITHM=force_directed

# Graph Export
GRAPH_EXPORT_FORMATS=["mermaid", "json", "d3", "cytoscape", "graphml"]
GRAPH_INCLUDE_METADATA=true
GRAPH_COMPRESS_EXPORT=true

# ================================
# Integration Configuration
# ================================

# Obsidian Vault
VAULT_PATH=./vault
VAULT_SYNC_ENABLED=true
VAULT_BACKUP_ENABLED=true
VAULT_CONFLICT_RESOLUTION=merge

# Template Processing
TEMPLATE_SAFE_MODE=true
TEMPLATE_MAX_RECURSION=10
TEMPLATE_VALIDATION_ENABLED=true

# Documentation Generation
DOCS_OUTPUT_PATH=./docs/generated
DOCS_INCLUDE_DIAGRAMS=true
DOCS_FORMAT=markdown
DOCS_AUTO_UPDATE=true

# ================================
# Performance Configuration
# ================================

# General Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=300.0
BACKGROUND_TASK_TIMEOUT=600.0

# Memory Management
MEMORY_POOL_SIZE=50
MEMORY_POOL_RECYCLE=3600
OBJECT_CACHE_SIZE=1000

# Database Performance
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=0
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# ================================
# Logging Configuration
# ================================

# Log Levels
LOG_LEVEL=INFO
LOG_FORMAT=detailed
LOG_FILE=logs/coachntt.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5

# Component Logging
LOG_DATABASE=INFO
LOG_API=INFO
LOG_SAFETY=WARNING
LOG_MEMORY=INFO
LOG_EMBEDDINGS=INFO

# Security Logging
LOG_SECURITY_EVENTS=true
LOG_AUTHENTICATION=true
LOG_SAFETY_VIOLATIONS=true
AUDIT_LOG_FILE=logs/audit.log

# ================================
# Development Configuration
# ================================

# Development Mode
ENVIRONMENT=development
DEBUG=false
TESTING=false
DEVELOPMENT_MODE=true

# Hot Reload
AUTO_RELOAD=true
RELOAD_DIRS=["src", "cli"]
RELOAD_INCLUDES=["*.py"]

# Development Tools
ENABLE_PROFILING=false
ENABLE_METRICS=true
DEVELOPMENT_SEED_DATA=false
```

## 🗄️ Database Configuration

### PostgreSQL Settings

#### Core Configuration (`postgresql.conf`)
```conf
# Connection Settings
listen_addresses = 'localhost'
port = 5432
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# Safety & Security
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
log_statement = 'all'
log_connections = on
log_disconnections = on

# Performance
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1

# pgvector Configuration
shared_preload_libraries = 'vector'
```

#### Authentication (`pg_hba.conf`)
```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
host    cognitive_coding_partner  ccp_user  172.20.0.0/16       scram-sha-256
```

### Safety Schema Configuration

The database includes safety-first schema with these key features:

#### Safety Tables
- `safety_validation_log`: Tracks all validation events
- `abstraction_quality_metrics`: Quality scoring history
- `reference_patterns`: Known pattern library
- `safety_violations`: Security incident tracking

#### Validation Triggers
```sql
-- Example safety trigger
CREATE OR REPLACE FUNCTION validate_memory_safety()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate safety score
    IF NEW.safety_score < 0.8 THEN
        RAISE EXCEPTION 'Safety score too low: %', NEW.safety_score;
    END IF;
    
    -- Check for concrete references
    IF check_concrete_references(NEW.content) THEN
        RAISE EXCEPTION 'Concrete references detected in content';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## 🌐 API Configuration

### FastAPI Settings

#### Main Configuration (`src/api/config.py`)
```python
from pydantic_settings import BaseSettings
from typing import List, Optional

class APISettings(BaseSettings):
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    debug: bool = False
    
    # Security
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 0
    
    # Safety
    safety_min_score: float = 0.8
    enable_safety_validation: bool = True
    
    # Performance
    max_concurrent_requests: int = 100
    request_timeout: float = 300.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

#### Middleware Configuration
```python
# Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    burst_size=10
)

# Authentication
app.add_middleware(
    JWTAuthenticationMiddleware,
    secret_key=settings.secret_key,
    algorithm=settings.jwt_algorithm
)

# Safety Validation
app.add_middleware(
    SafetyValidationMiddleware,
    min_score=settings.safety_min_score,
    auto_abstraction=True
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

## 🖥️ CLI Configuration

### CLI Settings

Create `~/.coachntt/config.yaml`:

```yaml
# CLI Configuration
api:
  base_url: "http://localhost:8000"
  timeout: 30
  retries: 3
  verify_ssl: true

output:
  format: "table"  # table, json, simple
  colors: true
  progress: true
  verbose: false

memory:
  default_limit: 10
  max_limit: 100
  auto_abstractions: true
  safety_warnings: true

graph:
  default_max_nodes: 100
  similarity_threshold: 0.7
  export_format: "mermaid"
  include_metadata: true

vault:
  path: "./vault"
  auto_sync: false
  backup_enabled: true
  conflict_resolution: "prompt"

cache:
  enabled: true
  ttl: 3600
  max_size: 1000
```

### Environment Variables for CLI
```bash
# CLI-specific environment variables
export COACHNTT_API_URL="http://localhost:8000"
export COACHNTT_CONFIG_PATH="~/.coachntt/config.yaml"
export COACHNTT_CACHE_DIR="~/.coachntt/cache"
export COACHNTT_LOG_LEVEL="INFO"
export COACHNTT_OUTPUT_FORMAT="table"
```

## 🗂️ Vault Integration Configuration

### Obsidian Vault Setup

#### Vault Structure
```
vault/
├── 00-Index/           # Central indexes and navigation
├── 01-Patterns/        # Code patterns and abstractions
├── 02-Setup/           # Setup and configuration guides
├── 03-Knowledge/       # Knowledge base and documentation
├── 04-Scripts/         # Automation scripts and tools
├── 05-Templates/       # Content templates
└── .obsidian/          # Obsidian configuration
```

#### Sync Configuration
```yaml
# vault_sync_config.yaml
sync:
  enabled: true
  direction: "bidirectional"  # to_vault, from_vault, bidirectional
  conflict_resolution: "prompt"  # merge, vault_wins, memory_wins, prompt
  
templates:
  learning: "05-Templates/Learning-Template.md"
  decision: "05-Templates/Decision-Template.md"
  checkpoint: "05-Templates/Checkpoint-Template.md"
  
filters:
  include_patterns: ["*.md"]
  exclude_patterns: [".obsidian/*", "*.tmp"]
  max_file_size: "10MB"
  
safety:
  auto_abstraction: true
  safety_check: true
  min_safety_score: 0.8
```

## 🔒 Security Configuration

### SSL/TLS Configuration

#### Development (Self-Signed)
```bash
# Generate self-signed certificates
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Update environment
SSL_CERT_FILE=cert.pem
SSL_KEY_FILE=key.pem
SSL_ENABLED=true
```

#### Production (Let's Encrypt)
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Update configuration
SSL_CERT_FILE=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_FILE=/etc/letsencrypt/live/your-domain.com/privkey.pem
SSL_ENABLED=true
```

### Authentication Configuration

#### JWT Token Configuration
```python
# JWT Settings
JWT_SECRET_KEY="your-super-secure-jwt-secret-key-at-least-32-characters-long"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Token Sources (in order of precedence)
JWT_TOKEN_SOURCES=[
    "header:Authorization:Bearer",  # Authorization: Bearer <token>
    "query:token",                  # ?token=<token>
    "cookie:access_token"           # Cookie: access_token=<token>
]
```

#### API Key Configuration
```python
# API Key Settings
API_KEY_HEADER="X-API-Key"
API_KEYS=[
    "api-key-1-for-service-a",
    "api-key-2-for-service-b"
]
API_KEY_RATE_LIMIT=1000  # requests per hour
```

## 📊 Performance Configuration

### Memory & Caching
```python
# Memory Management
MEMORY_POOL_SIZE=50
MEMORY_POOL_RECYCLE=3600
OBJECT_CACHE_SIZE=1000
EMBEDDING_CACHE_SIZE=10000

# Redis Cache (Optional)
REDIS_URL="redis://localhost:6379/0"
REDIS_CACHE_TTL=3600
REDIS_MAX_CONNECTIONS=20
```

### Database Performance
```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_memories_safety_score ON memories(safety_score);
CREATE INDEX CONCURRENTLY idx_memories_created_at ON memories(created_at);
CREATE INDEX CONCURRENTLY idx_memories_embedding_gin ON memories USING gin(embedding);

-- Partitioning (for large datasets)
CREATE TABLE memories_2024 PARTITION OF memories
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## 🔍 Monitoring Configuration

### Logging Configuration
```yaml
# logging.yaml
version: 1
disable_existing_loggers: false

formatters:
  detailed:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
  simple:
    format: "%(levelname)s - %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    formatter: simple
    level: INFO
    
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/coachntt.log
    formatter: detailed
    level: DEBUG
    maxBytes: 104857600  # 100MB
    backupCount: 5
    
  audit:
    class: logging.handlers.RotatingFileHandler
    filename: logs/audit.log
    formatter: detailed
    level: WARNING
    maxBytes: 104857600
    backupCount: 10

loggers:
  coachntt:
    level: INFO
    handlers: [console, file]
    propagate: false
    
  coachntt.safety:
    level: WARNING
    handlers: [console, file, audit]
    propagate: false
    
  coachntt.security:
    level: WARNING
    handlers: [audit]
    propagate: false
```

### Metrics Collection
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Safety metrics
SAFETY_VALIDATIONS = Counter('safety_validations_total', 'Total safety validations', ['result'])
SAFETY_SCORE = Histogram('safety_score', 'Safety score distribution')
ABSTRACTION_TIME = Histogram('abstraction_duration_seconds', 'Time spent on abstraction')

# Performance metrics
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
MEMORY_OPERATIONS = Counter('memory_operations_total', 'Memory operations', ['operation'])
GRAPH_BUILD_TIME = Histogram('graph_build_duration_seconds', 'Graph building time')
```

## 🛠️ Development Configuration

### Development Environment
```bash
# Development environment setup
export ENVIRONMENT=development
export DEBUG=true
export LOG_LEVEL=DEBUG
export AUTO_RELOAD=true
export DEVELOPMENT_SEED_DATA=true

# Testing configuration
export TESTING=true
export TEST_DATABASE_URL="postgresql://test_user:test_pass@localhost:5433/test_db"
export PYTEST_PARALLEL=true
export COVERAGE_THRESHOLD=90
```

### Code Quality Tools
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--strict-markers --disable-warnings -v"
```

## 📋 Configuration Validation

### Validation Scripts

```bash
# Validate configuration
python scripts/validate_config.py

# Test database connection
python scripts/test_database.py

# Verify safety settings
python scripts/test_safety.py

# Check API configuration
python scripts/test_api.py
```

### Health Checks
```python
# Health check endpoint
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "safety": await check_safety_system(),
        "embeddings": await check_embedding_service(),
        "vault": await check_vault_sync()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return Response(
        content=json.dumps(checks),
        status_code=status_code,
        media_type="application/json"
    )
```

## 🚀 Production Configuration

### Production Environment Variables
```env
# Production overrides
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
SSL_ENABLED=true
CORS_ORIGINS=["https://your-domain.com"]

# Security hardening
SESSION_COOKIE_SECURE=true
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
RATE_LIMIT_REQUESTS_PER_MINUTE=30
API_KEY_RATE_LIMIT=500

# Performance optimization
DB_POOL_SIZE=50
MEMORY_POOL_SIZE=100
EMBEDDING_CACHE_SIZE=50000
BACKGROUND_TASK_TIMEOUT=300
```

### Docker Production Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
```

---

**Configuration Complete!** 🎉

Your CoachNTT.ai system is now properly configured for optimal performance, security, and safety validation. Adjust settings based on your specific requirements and environment.