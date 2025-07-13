# 🧠 CoachNTT.ai - Cognitive Coding Partner

An advanced AI-powered development assistant with temporal memory, automated documentation, and structured workflow enforcement.

## Overview

CoachNTT.ai (Cognitive Coding Partner) revolutionizes software development through intelligent temporal memory, automated documentation, and structured workflow enforcement. Unlike traditional coding assistants, CCP maintains comprehensive context awareness through holistic memory storage, knowledge base integration, and proactive development guidance.

## Core Features

- **Temporal Memory System**: Stores complete interaction contexts with time-weighted relevance
- **Obsidian Integration**: Bidirectional synchronization with knowledge base
- **Workflow Automation**: Comprehensive script library for development and testing
- **Quality Enforcement**: Automated checkpoints, documentation generation, and complexity monitoring
- **Scalable Architecture**: PostgreSQL-first design with pgvector for semantic search

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

- [Architecture Overview](docs/architecture/system-design.md)
- [Development Guide](docs/development/setup-guide.md)
- [User Guide](docs/user-guide/getting-started.md)

## Contributing

Please read our [Contributing Guide](docs/development/contributing.md) before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Status

🚧 **Active Development** - Phase 1: Foundation Infrastructure