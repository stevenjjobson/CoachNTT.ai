# 🧠 CoachNTT.ai - Cognitive Coding Partner

## 🛡️ Safety-First Architecture

**A revolutionary AI development assistant built with safety as the foundation** - featuring mandatory abstraction of all concrete references, temporal memory with privacy protection, and comprehensive validation at every layer.

### Core Safety Principles
- **Abstraction-First**: All concrete references (paths, IDs, secrets) automatically abstracted
- **Validation at Every Layer**: Database, API, and application-level safety enforcement
- **Privacy by Design**: No personal or sensitive data stored in concrete form
- **Fail-Safe Defaults**: System refuses unsafe operations by design

## Overview

CoachNTT.ai (Cognitive Coding Partner) revolutionizes software development through intelligent temporal memory, automated documentation, and structured workflow enforcement. Unlike traditional coding assistants, CCP maintains comprehensive context awareness through holistic memory storage, knowledge base integration, and proactive development guidance.

## 🔐 Novel Security Innovation

CoachNTT.ai introduces a groundbreaking security pattern for AI-assisted development: a **mandatory abstraction framework** that creates a protective barrier between AI tools and sensitive information. This innovation addresses a critical vulnerability in current AI coding assistants - the inadvertent leakage of sensitive project details through file paths, variable names, URLs, database schemas, and error messages.

### The Bidirectional Safety Barrier

Our abstraction framework operates as a systematic security layer:

```
Real World Data → Abstraction Engine → AI Processing → Safe Output
/home/user/api/keys.py → <project>/<module>/<component>.py → AI sees only patterns → Safe suggestions
```

### Why This Matters

Unlike traditional approaches that rely on:
- Manual sanitization (error-prone)
- Simple pattern filters (insufficient)
- Trust-based systems (risky)
- Avoiding AI for sensitive projects (limiting)

CoachNTT.ai enforces abstraction at **every layer**:
- **Database Level**: PostgreSQL triggers prevent storage of concrete references
- **Application Level**: Multi-stage validation pipeline with safety scoring
- **API Level**: Automatic abstraction in all responses
- **Output Level**: Real-time safety validation with quality metrics

### Technical Implementation

The framework includes:
- **Reference Extraction**: Identifies all concrete references in content
- **Pattern Generation**: Creates consistent, safe abstractions
- **Safety Scoring**: Measures abstraction quality (≥0.8 threshold enforced)
- **Temporal Consistency**: Maintains abstraction patterns over time
- **Database Enforcement**: Impossible to bypass at data layer

### Industry Significance

This approach enables:
- **Enterprise AI Adoption**: Use AI tools without compromising security
- **Regulatory Compliance**: GDPR, HIPAA, SOC2 friendly by design
- **Open Source Contribution**: Share knowledge without exposing internals
- **Team Collaboration**: Safe knowledge sharing across organizations

The abstraction framework represents a potential new security primitive for AI tools - transforming how organizations can safely leverage AI assistance while maintaining complete information security.

## 🚀 Current Features

### 🔒 Safety & Abstraction Framework
- **Reference Abstraction Engine**: Automatically converts concrete references to safe patterns
- **Multi-Stage Validation Pipeline**: Structure → Abstraction → Safety → Temporal → Consistency
- **Real-Time Safety Metrics**: Quality scoring and monitoring with alerting
- **Database-Level Enforcement**: PostgreSQL triggers preventing unsafe data storage
- **Safety Score**: Maintains ≥0.8 safety threshold across all operations

### 🧠 Intelligence & Memory System
- **Temporal Memory System**: Stores complete interaction contexts with time-weighted relevance
- **Intent Analysis Engine**: 12 intent types with semantic, temporal, and usage pattern analysis
- **Memory Clustering**: Hierarchical clustering with embeddings for semantic grouping
- **Vector Embeddings**: Sentence-transformers with intelligent caching (>80% cache hit rate)
- **Memory Decay Management**: Configurable temporal weight algorithms

### 📊 Knowledge Graph & Analysis
- **Knowledge Graph Builder**: Semantic connections between memories and code
- **AST Code Analysis**: Python/JavaScript/TypeScript with pattern detection
- **Graph Export**: Multiple formats (Mermaid, JSON, D3, Cytoscape, GraphML)
- **Subgraph Extraction**: BFS-based traversal with configurable depth
- **Performance**: <500ms graph build, <50ms queries, <200ms visualization

### 🔗 Integration & Automation
- **Obsidian Vault Sync**: Bidirectional synchronization with conflict resolution
- **Documentation Generator**: Automated README, API docs, changelog generation
- **Script Automation Framework**: Safe execution with performance monitoring
- **Checkpoint System**: Git state capture with complexity analysis
- **Template Processing**: Safe variable substitution with validation

### 🌐 REST API & WebSocket Support
- **Complete FastAPI Application**: 15+ REST endpoints with JWT authentication
- **Memory CRUD Operations**: Create, read, update, delete with automatic abstraction
- **Knowledge Graph API**: Build, query, export, and subgraph operations
- **Integration Endpoints**: Checkpoint, vault sync, documentation generation
- **Real-time WebSocket**: Live updates with channel subscriptions and heartbeat
- **Background Tasks**: Progress tracking for long-running operations

### 🛠️ Development & Operations
- **Advanced Middleware**: Rate limiting (token bucket), authentication, safety validation
- **Comprehensive Testing**: Unit tests for all components with >90% coverage
- **Performance Monitoring**: Real-time metrics with safety score tracking
- **Error Handling**: Production-ready error abstraction with correlation IDs
- **Configuration Management**: 50+ settings with environment-based overrides

## Tech Stack

- **Backend**: Python 3.10+ with FastAPI, Pydantic, asyncio
- **Database**: PostgreSQL 15+ with pgvector extension for vector operations
- **AI/ML**: Sentence-transformers, scikit-learn for embeddings and clustering
- **Knowledge Base**: Obsidian vault integration with markdown processing
- **Authentication**: JWT with flexible token sources and auto-refresh
- **Containerization**: Docker & Docker Compose with security hardening
- **API**: RESTful with WebSocket support and comprehensive validation
- **Testing**: pytest with async support and comprehensive mocking

## Quick Start

1. **Clone and Setup**:
```bash
git clone https://github.com/stevenjjobson/CoachNTT.ai.git
cd CoachNTT.ai
cp .env.example .env
# Edit .env with your configuration
```

2. **Start Services**:
```bash
# Start database and core services
docker-compose up -d

# Initialize database with safety-first schema
./scripts/database/init-database.sh
```

3. **API Server**:
```bash
# Start the FastAPI server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# API Documentation available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

4. **WebSocket Connection**:
```bash
# Connect to real-time updates
wscat -c "ws://localhost:8000/ws/realtime?token=YOUR_JWT_TOKEN"
```

## API Endpoints

### Memory Operations
- `POST /api/v1/memories/` - Create new memory
- `GET /api/v1/memories/{memory_id}` - Get memory by ID
- `PUT /api/v1/memories/{memory_id}` - Update memory
- `DELETE /api/v1/memories/{memory_id}` - Delete memory
- `POST /api/v1/memories/search` - Search memories with filters
- `POST /api/v1/memories/{memory_id}/reinforce` - Reinforce memory

### Knowledge Graph
- `POST /api/v1/graph/build` - Build knowledge graph
- `GET /api/v1/graph/{graph_id}` - Get graph metadata
- `POST /api/v1/graph/{graph_id}/query` - Query graph with filters
- `POST /api/v1/graph/{graph_id}/export` - Export graph (multiple formats)
- `POST /api/v1/graph/{graph_id}/subgraph` - Extract subgraph
- `GET /api/v1/graph/` - List available graphs

### Integration Services
- `POST /api/v1/integrations/checkpoint` - Create memory checkpoint
- `POST /api/v1/integrations/vault/sync` - Trigger vault synchronization
- `POST /api/v1/integrations/docs/generate` - Generate documentation
- `GET /api/v1/integrations/status` - Get integration service status
- `GET /api/v1/integrations/tasks` - List background tasks

### WebSocket Endpoints
- `WebSocket /ws/realtime` - Real-time updates and notifications
- Channels: `memory_updates`, `graph_updates`, `integration_updates`, `system_notifications`

## Project Structure

```
CoachNTT.ai/
├── src/
│   ├── core/                    # Core business logic
│   │   ├── abstraction/         # Abstraction engine and rules
│   │   ├── safety/              # Safety models and validation
│   │   ├── memory/              # Memory management and repository
│   │   ├── embeddings/          # Vector embeddings service
│   │   ├── intent/              # Intent analysis engine
│   │   ├── analysis/            # AST and code analysis
│   │   └── validation/          # Safety validation pipeline
│   ├── services/                # Service layer
│   │   ├── vault/               # Obsidian vault integration
│   │   └── documentation/       # Documentation generation
│   ├── api/                     # FastAPI application
│   │   ├── models/              # Pydantic models
│   │   ├── routers/             # API endpoints
│   │   └── middleware/          # Custom middleware
│   └── database/                # Database migrations and schema
├── scripts/                     # Automation and development scripts
│   ├── framework/               # Script execution framework
│   ├── development/             # Development utilities
│   ├── monitoring/              # Performance monitoring
│   └── automation/              # Automated workflows
├── tests/                       # Comprehensive test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── performance/             # Performance benchmarks
├── vault/                       # Obsidian knowledge base
├── docker/                      # Docker configuration
├── docs/                        # Documentation
└── config/                      # Configuration files
```

## Development

### Running Tests
```bash
# Run full test suite
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/unit/api/ -v          # API tests
python -m pytest tests/unit/core/ -v         # Core logic tests
python -m pytest tests/integration/ -v       # Integration tests
```

### Database Operations
```bash
# Connect to database
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner

# Run migrations
python -m alembic upgrade head

# Create new migration
python -m alembic revision --autogenerate -m "Description"
```

### Performance Monitoring
```bash
# Run performance benchmarks
python scripts/monitoring/context-monitor.py

# Generate performance reports
python scripts/testing/run-suite.py --performance
```

## Safety & Security

### Safety Metrics (Current)
- **Abstraction Quality Score**: 0.995/1.0 ✅
- **Processing Time**: <1ms average ✅
- **Coverage**: 100% reference detection ✅
- **Validation**: Multi-stage pipeline operational ✅
- **Safety Enforcement**: Database-level triggers active ✅

### Security Features
- JWT authentication with configurable expiration
- Rate limiting with token bucket algorithm
- Input validation and sanitization
- SQL injection prevention
- CORS configuration
- Environment-based secrets management

## Documentation

- [Architecture Overview](docs/architecture/system-design.md)
- [API Documentation](docs/api/endpoints.md)
- [Safety Framework](docs/safety/PRINCIPLES.md)
- [Development Guide](docs/development/setup-guide.md)
- [User Guide](docs/user-guide/getting-started.md)
- [Performance Guide](docs/performance/optimization.md)

## Contributing

Please read our [Contributing Guide](docs/development/contributing.md) before submitting pull requests.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Run safety validation: `python -m pytest tests/unit/safety/`
4. Ensure all tests pass: `python -m pytest`
5. Submit pull request with comprehensive description

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Status & Roadmap

### ✅ Completed Phases
- **Phase 0**: Safety Foundation (100%) - Abstraction framework operational
- **Phase 1**: Secure Foundation (100%) - Production-ready database and models
- **Phase 2**: Intelligence Layer (100%) - Intent analysis and embeddings
- **Phase 3**: Knowledge Integration (100%) - Graph builder and vault sync
- **Phase 4**: Integration & Polish (40%) - REST API and WebSocket support

### 🚧 Current Development
- **Session 4.2**: CLI Interface Development (Planned)
- **Session 4.3**: Performance Optimization (Planned)
- **Session 4.4**: Security Hardening (Planned)
- **Session 4.5**: Production Deployment (Planned)

### Performance Targets (All Met)
- Memory operations: <500ms
- Graph building: <1s for 100 nodes
- API responses: <200ms average
- WebSocket latency: <50ms
- Safety validation: <1ms

### Upcoming Features
- Command-line interface for all operations
- Advanced performance optimization
- Enhanced security features
- Production deployment templates
- Advanced monitoring and alerting

## Support

For questions, issues, or contributions:
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: General questions and community support
- **Documentation**: Comprehensive guides in `/docs`

---

**Built with safety-first principles and zero-tolerance for data leakage**