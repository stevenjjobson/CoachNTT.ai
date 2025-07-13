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

## Core Features

### 🔒 Safety & Abstraction Framework
- **Reference Abstraction Engine**: Automatically converts concrete references to safe patterns
- **Multi-Stage Validation Pipeline**: Structure → Abstraction → Safety → Temporal → Consistency
- **Real-Time Safety Metrics**: Quality scoring and monitoring with alerting
- **Database-Level Enforcement**: PostgreSQL triggers preventing unsafe data storage

### 🧠 Intelligence & Memory
- **Temporal Memory System**: Stores complete interaction contexts with time-weighted relevance
- **Obsidian Integration**: Bidirectional synchronization with knowledge base
- **Workflow Automation**: Comprehensive script library for development and testing
- **Quality Enforcement**: Automated checkpoints, documentation generation, and complexity monitoring

## Tech Stack

- **Backend**: Python 3.11+ with FastAPI
- **Database**: PostgreSQL 15+ with pgvector extension
- **Knowledge Base**: Obsidian vault integration
- **Containerization**: Docker & Docker Compose
- **API**: RESTful with WebSocket support

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/stevenjjobson/CoachNTT.ai.git
cd CoachNTT.ai
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the services:
```bash
docker-compose up -d
```

4. Initialize the database:
```bash
./scripts/database/init-database.sh
```

## Project Structure

```
CoachNTT.ai/
├── src/           # Source code
├── scripts/       # Automation scripts
├── vault/         # Obsidian knowledge base
├── docker/        # Docker configuration
├── tests/         # Test suites
├── docs/          # Documentation
└── config/        # Configuration files
```

## Documentation

- [Documentation Guide](DOCUMENTATION_GUIDE.md) - Where to find things
- [Architecture Overview](docs/architecture/system-design.md)
- [Development Guide](docs/development/setup-guide.md)
- [User Guide](docs/user-guide/getting-started.md)

## Contributing

Please read our [Contributing Guide](docs/development/contributing.md) before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Status

✅ **Phase 0 Complete**: Safety Foundation (100%) - Abstraction framework operational  
🚧 **Phase 1 In Progress**: Secure Foundation - Production-ready structure

### Safety Metrics
- **Abstraction Quality Score**: 0.995/1.0 ✅
- **Processing Time**: <1ms average ✅
- **Coverage**: 100% reference detection ✅
- **Validation**: Multi-stage pipeline operational ✅