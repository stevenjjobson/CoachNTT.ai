# 🧠 CoachNTT.ai - AI Context & Session Management

## 🎯 Project Overview
**What**: Cognitive Coding Partner - AI development assistant with temporal memory  
**Core Feature**: Safety-first abstraction of all concrete references  
**Tech Stack**: Python 3.10+, PostgreSQL with pgvector, FastAPI  
**Status**: Phase 1 - Secure Foundation (In Progress)

## 📍 Current State (Updated: 2025-01-13)

### ✅ Completed Sessions
- **Session 0.1**: Core Safety Principles & Architecture
  - Created safety documentation (docs/safety/PRINCIPLES.md, docs/safety/PATTERNS.md, docs/safety/VALIDATION.md)
  - Implemented abstraction engine with 4 core components
  - Set up PostgreSQL + pgvector in Docker
  - Created comprehensive test suite
  - Database migration: `000_safety_foundation.sql`

- **Session 0.2**: Safety Database Schema
  - Created validation triggers to enforce abstraction at DB level
  - Implemented row-level security (RLS) policies
  - Added advanced check constraints for safety
  - Created temporal safety functions
  - Enhanced audit logging with comprehensive triggers
  - Database migration: `001_safety_enforcement.sql`
  - Created SQL and Python test suites

- **Session 0.3**: Reference Abstraction Framework
  - Enhanced abstraction rules for all reference types (variables, APIs, cloud, etc.)
  - Created comprehensive memory validation pipeline with 5 stages
  - Built safety metrics collection with real-time monitoring
  - Implemented abstraction quality scorer with 6 quality dimensions
  - Added comprehensive test suite with integration tests
  - All components tested and working: safety score 0.995, processing <1ms

- **Session 1.1**: Safety-First Project Initialization
  - Created production-ready project structure with safety built-in
  - Enhanced all configuration files with safety-first approach
  - Updated README.md with safety principles prominent
  - Added comprehensive security dependencies and tooling
  - Initialized vault with safety templates and structure
  - Configured pre-commit hooks for safety validation
  - All infrastructure ready for Phase 1 continuation

- **Session 1.2**: Secure PostgreSQL & pgvector Setup
  - Created security-hardened PostgreSQL Dockerfile with comprehensive protection
  - Enhanced docker-compose.yml with advanced security configurations
  - Built safety-first database schema with safety tables created FIRST
  - Implemented comprehensive validation triggers preventing concrete references
  - Configured secure PgBouncer connection pooling with monitoring
  - Created AES-256 encrypted backup/restore system with safety validation
  - Established comprehensive audit logging with real-time security monitoring
  - Built 25-test safety enforcement validation suite
  - Database infrastructure now production-ready with zero-tolerance safety enforcement

- **Session 1.3**: Safety-First Database Schema
  - Created 7 SQL migrations (004-010) implementing comprehensive safety enforcement
  - Built Python memory models with mandatory abstraction validation
  - Created 75-test validation suite ensuring zero-tolerance for concrete references
  - Implemented advanced validation functions for all content types
  - Added real-time safety scoring system with automatic quarantine
  - Created abstraction quality assurance with 6 quality dimensions
  - Built 30+ specialized indexes for safety-aware performance
  - Set up automatic detection system for continuous monitoring
  - All components enforce minimum safety score of 0.8

- **Session 1.4**: Abstract Memory Model Implementation
  - Enhanced memory models with advanced decay algorithms and clustering
  - Created MemoryDecayEngine with configurable temporal weight management
  - Built MemoryClusterManager for semantic grouping using vector embeddings
  - Enhanced SafeMemoryRepository with clustering and temporal relationships
  - Implemented hierarchical clustering with safety enforcement
  - Added cluster-aware search with boosted ranking
  - Created comprehensive integration tests (300+ lines)
  - Built performance benchmarks with grading system
  - All features maintain zero-tolerance safety requirements (min 0.8 score)

- **Session 2.2**: Vector Embeddings Integration
  - Implemented advanced EmbeddingService using sentence-transformers
  - Created intelligent caching layer with LRU eviction and safety validation
  - Enhanced memory creation pipeline with automatic embedding generation
  - Improved clustering algorithms with weighted embedding combination (40/60)
  - Added content type detection (text, code, documentation) for model selection
  - Built comprehensive test suite including unit, integration, and performance tests
  - Achieved all performance targets (<500ms single, <2s batch, >80% cache hit rate)
  - Maintained zero-tolerance safety enforcement throughout embedding pipeline

- **Session 2.3**: Intent Engine Foundation
  - Built complete intent analysis and connection finding system (3,824 lines)
  - Implemented IntentEngine with 12 intent types (Question, Command, Debug, Optimize, etc.)
  - Created ConnectionFinder with semantic, temporal, and usage pattern analysis
  - Added non-directive filtering ensuring 100% user autonomy compliance
  - Enhanced memory repository with intent-aware search capabilities
  - Integrated with existing embedding service for semantic similarity analysis
  - Built comprehensive test suite (1,347 lines) with performance benchmarks
  - Achieved all performance targets (<200ms intent, <500ms connections)
  - Maintained safety-first design with mandatory abstraction (≥0.8 safety score)

- **Session 2.4**: AST Code Analysis
  - Built comprehensive AST analysis system for code understanding and pattern detection (~950 lines)
  - Implemented ASTAnalyzer with language detection (Python, JavaScript, TypeScript)
  - Created PatternDetector for design patterns (Singleton, Factory, Observer)
  - Added ComplexityAnalyzer with cyclomatic and cognitive complexity metrics
  - Built dependency graph builder for code relationship analysis
  - Integrated AST analysis with IntentEngine for context-aware code insights
  - Created comprehensive test suite with unit, integration, and performance tests
  - Achieved all performance targets (<300ms Python analysis, <50ms language detection)
  - Maintained safety-first design with complete abstraction of concrete references

- **Session 3.1**: Obsidian Vault Sync
  - Built comprehensive vault synchronization system with memory-to-markdown conversion (~850 lines)
  - Implemented VaultSyncEngine with bidirectional sync capabilities and conflict resolution
  - Created MarkdownConverter with frontmatter generation, tag extraction, and AST analysis integration
  - Built TemplateProcessor with checkpoint, learning, and decision templates with safe variable substitution
  - Added ConflictResolver with multiple resolution strategies (safe merge, memory wins, vault wins)
  - Integrated with existing memory repository, AST analyzer, and intent engine
  - Created comprehensive test suite with unit and integration tests using mock filesystem
  - Enhanced memory repository with vault sync tracking and status management
  - Achieved all performance targets (<500ms conversion, <300ms conflict detection, <100ms backlinks)
  - Maintained zero-tolerance safety with complete abstraction of concrete references in vault content

- **Session 3.2**: Script Automation Framework
  - Built comprehensive script automation framework with safety-first design (~2,450 lines)
  - Implemented ScriptRunner with dependency validation, performance monitoring, and safety checks
  - Created safety-first logging system with automatic content abstraction and compliance tracking
  - Built checkpoint script for git state capture with complexity analysis and safety validation
  - Added safe rollback system with multi-level validation and automatic backup creation
  - Implemented real-time context monitoring with system performance and safety score tracking
  - Created automated vault sync integration with existing VaultSyncEngine
  - Built comprehensive test execution framework with coverage reporting and safety validation
  - Enhanced dependency management with psutil and gitpython for system operations
  - Achieved all performance targets (<2s script execution, <5s checkpoint analysis, <10s vault automation)
  - Maintained zero-tolerance safety with complete abstraction in all script outputs

- **Session 3.3**: Documentation Generator
  - Built comprehensive documentation generation system with AST integration (~1,200 lines)
  - Implemented DocumentationGenerator with safety-first design and template system
  - Created automated README, API docs, and changelog generation from code analysis
  - Added Mermaid diagram generation for architecture and dependency visualization
  - Built documentation coverage calculator and safety validation reporting
  - Integrated with existing AST analyzer for deep code understanding
  - Created comprehensive template system with variable substitution and safety validation
  - Added Git hook integration for automated documentation updates on commits
  - Built script automation integration for command-line documentation generation
  - Achieved all performance targets (<300ms code analysis, <200ms README generation, <500ms API docs)
  - Maintained zero-tolerance safety with complete abstraction in all generated documentation

- **Session 3.4**: Knowledge Graph Builder
  - Built comprehensive knowledge graph system with semantic connections (~1,800 lines)
  - Implemented KnowledgeGraphBuilder with node extraction from memories and code
  - Created GraphNode and GraphEdge models with safety-first validation
  - Added semantic similarity edge detection using embeddings (threshold: 0.7)
  - Implemented temporal weighting system with exponential decay
  - Built graph query system with filtering and traversal capabilities
  - Created multiple export formats: Mermaid diagrams, JSON (standard/D3/Cytoscape), GraphML
  - Integrated with DocumentationGenerator for automated graph documentation
  - Added performance optimizations: embedding cache, batch processing, sparse representation
  - Achieved all performance targets (<500ms graph build, <50ms queries, <200ms visualization)
  - Maintained zero-tolerance safety with complete abstraction in graph content

- **Session 4.1a**: REST API Foundation & Memory Operations
  - Created complete FastAPI application foundation with safety-first design (16 files, ~2,681 lines)
  - Implemented comprehensive configuration system with 50+ settings and pydantic-settings
  - Built JWT authentication middleware with flexible token sources and auto-refresh
  - Created advanced middleware stack: rate limiting (token bucket), authentication, safety validation
  - Established dependency injection system for all services with async connection management
  - Implemented memory CRUD endpoints with automatic abstraction and safety validation
  - Added memory search with intent analysis integration and relevance scoring
  - Created memory clustering and reinforcement endpoints with background processing
  - Built comprehensive Pydantic models for all request/response validation
  - Implemented production-ready error handling with abstracted details and request correlation
  - Added unit tests for API foundation and memory endpoints with mock validation
  - Achieved safety-first design with zero-tolerance for concrete references in API responses

- **Session 4.1b**: Knowledge Graph & Integration APIs with WebSocket Support
  - Implemented complete knowledge graph API with 15 REST endpoints and WebSocket support (8 files, ~580 lines)
  - Created comprehensive graph operations: build, query, export (Mermaid/JSON/GraphML), subgraph extraction
  - Built integration APIs for checkpoint creation, vault synchronization, and documentation generation
  - Implemented real-time WebSocket connections with JWT authentication and channel subscriptions
  - Added connection management with heartbeat monitoring and event broadcasting system
  - Created background task management for long-running operations with progress tracking
  - Built integration status monitoring with service health checks and performance metrics
  - Enhanced dependency injection with WebSocket authentication and service configurations
  - Added comprehensive unit tests for graph, integration, and WebSocket functionality
  - Achieved all performance targets: graph build <1s, queries <100ms, WebSocket <50ms
  - Maintained zero-tolerance safety enforcement with complete abstraction in all responses

- **Session 4.2a**: CLI Foundation with Immediate Usability
  - Created comprehensive CLI user guide documenting all planned functionality (600+ lines)
  - Built CLI framework extending existing script infrastructure (cli/ directory structure)
  - Implemented CLIEngine with async API communication and safety-first design
  - Created status command with system health checks and detailed diagnostics
  - Implemented memory list and show commands with safety abstraction
  - Built rich output formatting with table, JSON, and simple text modes
  - Added comprehensive help system with examples and troubleshooting guidance
  - Established living documentation for CLI interface coordination
  - Created main CLI entry point (coachntt.py) with command routing and error handling
  - Achieved immediate usability: users can run basic commands after installation

- **Session 4.2b**: CLI Memory Management Operations
  - Enhanced CLIEngine with 5 new methods for complete memory management (create, update, delete, search, export)
  - Implemented memory create command with type selection, metadata support, and intent specification
  - Built advanced memory search with semantic similarity, intent analysis, and comprehensive filtering
  - Created memory export in 3 formats: JSON (structured), CSV (analysis), Markdown (documentation)
  - Added memory update command for modifying existing memories with validation
  - Implemented safe memory deletion with confirmation prompts and detailed previews
  - Enhanced input validation with comprehensive error handling and troubleshooting guidance
  - Added progress indicators and real-time feedback for all long-running operations
  - Updated CLI user guide with 7 new commands and real-world usage examples
  - Achieved complete memory management: all API memory operations accessible via CLI

- **Session 4.2c**: CLI Knowledge Graph Operations
  - Enhanced CLIEngine with 6 new graph methods for comprehensive graph management (build, query, export, list, delete, subgraph)
  - Implemented graph build command with memory and code analysis integration, similarity thresholds, and customizable parameters
  - Built advanced graph query system with semantic pattern matching, node/edge filtering, and multiple output formats
  - Created graph export functionality in 5 formats: Mermaid, JSON, D3, Cytoscape, GraphML with filtering and metadata options
  - Added subgraph extraction for focused exploration around specific nodes with depth and weight controls
  - Implemented comprehensive graph management (list, show, delete) with safety confirmations and detailed metadata display
  - Enhanced CLI with progress indicators, real-time feedback, and comprehensive error handling for all graph operations
  - Added Mermaid diagram generation for visual graph representation in query and subgraph commands
  - Updated CLI user guide with 7 new graph commands, real-world examples, and complete feature documentation
  - Achieved complete knowledge graph CLI integration: all graph API operations accessible with rich formatting and safety validation

- **Session 4.2d**: CLI Integration & Interactive Mode
  - Enhanced CLIEngine with 3 new integration methods for complete external service integration (sync_vault, generate_docs, create_checkpoint)
  - Implemented comprehensive vault synchronization with bidirectional sync, template support, dry-run mode, and conflict resolution
  - Built automated documentation generation supporting 5 doc types (readme, api, architecture, changelog, coverage) with diagram support
  - Created development checkpoint system with git state capture, code analysis integration, and memory filtering
  - Implemented interactive CLI mode with tab completion, command history, and built-in help system using readline
  - Built comprehensive configuration management with file/environment variable support, validation, and reset capabilities
  - Created 5 new command groups (sync, docs, checkpoint, interactive, config) with 8 total new commands
  - Updated CLI user guide with complete documentation for all 21 commands across 8 command groups
  - Enhanced main CLI entry point to reflect complete feature availability and Phase 4 completion
  - Achieved complete CLI interface: all major CoachNTT.ai functionality accessible via command line with safety-first design

- **Session 4.3**: Testing Suite Completion
  - Created comprehensive testing infrastructure with pytest configuration, shared fixtures, and coverage reporting
  - Built extensive test fixtures for memories, graphs, and safety validation with abstracted data and edge cases
  - Implemented safety validation tests with 100% coverage of abstraction enforcement and unsafe pattern detection
  - Created integration tests for memory lifecycle, CLI commands, API endpoints, and WebSocket functionality
  - Built end-to-end user scenario tests covering complete workflows from learning to production
  - Implemented performance and load tests validating response times, throughput, and system limits
  - Set up GitHub Actions CI/CD pipeline with matrix testing, coverage reporting, and quality gates
  - Enhanced pre-commit configuration with exclusion patterns, CI integration, and additional code quality tools
  - Created comprehensive test strategy documentation with coverage requirements and best practices
  - Achieved >90% code coverage with zero-tolerance safety validation and complete test automation

### 🏗️ Architecture Summary
```
src/
├── core/
│   ├── abstraction/
│   │   ├── engine.py          # AbstractionEngine base class
│   │   ├── concrete_engine.py # Main implementation
│   │   ├── extractor.py       # ReferenceExtractor
│   │   ├── generator.py       # PatternGenerator
│   │   └── rules.py           # AbstractionRules for all types
│   ├── safety/
│   │   └── models.py          # Core data models
│   ├── validation/
│   │   ├── validator.py       # SafetyValidator
│   │   ├── memory_validator.py # MemoryValidationPipeline
│   │   └── quality_scorer.py  # AbstractionQualityScorer
│   ├── metrics/
│   │   └── safety_metrics.py  # SafetyMetricsCollector
│   ├── embeddings/
│   │   ├── service.py         # EmbeddingService with sentence-transformers
│   │   ├── cache.py           # LRU cache with safety validation
│   │   └── models.py          # Embedding data models and types
│   ├── intent/
│   │   ├── engine.py          # IntentEngine with query analysis pipeline
│   │   ├── analyzer.py        # IntentAnalyzer with pattern recognition
│   │   ├── connections.py     # ConnectionFinder for relationship discovery
│   │   └── models.py          # Intent data models and types
│   ├── analysis/
│   │   ├── ast_analyzer.py    # ASTAnalyzer with comprehensive code analysis
│   │   ├── language_detector.py # LanguageDetector for Python/JS/TS
│   │   ├── pattern_detector.py # PatternDetector for design patterns
│   │   ├── complexity_analyzer.py # ComplexityAnalyzer for quality metrics
│   │   └── models.py          # AST analysis data models and types
│   └── memory/
│       ├── abstract_models.py # Core memory models with validation
│       ├── validator.py       # Memory validation service
│       ├── repository.py      # Safe memory repository with vault sync integration
│       ├── cluster_manager.py # Enhanced clustering with embeddings
│       └── decay_engine.py    # Temporal decay management
├── services/
│   ├── vault/
│   │   ├── sync_engine.py     # VaultSyncEngine for bidirectional synchronization
│   │   ├── markdown_converter.py # Memory-to-markdown conversion with safety
│   │   ├── template_processor.py # Template system with variable substitution
│   │   ├── conflict_resolver.py # Conflict detection and resolution strategies
│   │   ├── models.py          # Vault sync data models and enums
│   │   ├── graph_builder.py   # KnowledgeGraphBuilder for semantic connections
│   │   ├── graph_models.py    # Graph data models (nodes, edges, queries)
│   │   └── graph_exporters.py # Export formats (Mermaid, JSON, GraphML)
│   └── documentation/
│       ├── generator.py       # DocumentationGenerator with AST integration
│       ├── models.py          # Documentation data models and types
│       └── templates.py       # Template system with safety validation
├── api/
│   ├── __init__.py            # API module exports
│   ├── main.py                # FastAPI application with lifespan management and WebSocket support
│   ├── config.py              # Comprehensive API configuration (50+ settings)
│   ├── dependencies.py       # Dependency injection, JWT authentication, and WebSocket auth
│   ├── middleware/
│   │   ├── __init__.py        # Middleware exports
│   │   ├── authentication.py  # JWT middleware with flexible token sources
│   │   ├── safety.py          # Safety validation with automatic abstraction
│   │   ├── logging.py         # Request/response logging with content abstraction
│   │   └── rate_limiting.py   # Token bucket rate limiting per client
│   ├── models/
│   │   ├── __init__.py        # Model exports
│   │   ├── common.py          # Shared models (pagination, errors, responses)
│   │   ├── memory.py          # Memory operation models with validation
│   │   ├── graph.py           # Knowledge graph models (build, query, export, subgraph)
│   │   └── integration.py     # Integration models (checkpoint, vault sync, docs generation)
│   └── routers/
│       ├── __init__.py        # Router exports
│       ├── memory.py          # Memory CRUD endpoints with intent analysis
│       ├── graph.py           # Knowledge graph endpoints with export formats
│       ├── integration.py     # Integration endpoints with background task management
│       └── websocket.py       # WebSocket endpoints with real-time updates
cli/
├── __init__.py                # CLI module exports and version info
├── core.py                    # CLIEngine with async API communication and complete integration methods
├── utils.py                   # Output formatting, progress indicators, and safety validation utilities
└── commands/
    ├── __init__.py            # Command registry and exports (8 command groups)
    ├── status.py              # System health and connectivity commands
    ├── memory.py              # Complete memory management operations (7 commands)
    ├── graph.py               # Knowledge graph operations (7 commands)
    ├── integration.py         # Integration commands: vault sync, docs generation, checkpoints
    ├── interactive.py         # Interactive CLI mode with tab completion and history
    └── config.py              # Configuration management with file/environment support
scripts/
├── framework/
│   ├── __init__.py            # Framework module exports
│   ├── config.py              # Configuration management with environment support
│   ├── logger.py              # Safety-first logging with content abstraction
│   └── runner.py              # Script execution engine with monitoring
├── development/
│   ├── checkpoint.sh          # Git state capture with complexity analysis
│   └── rollback.py            # Safe rollback with validation and backup
├── monitoring/
│   └── context-monitor.py     # Real-time performance and safety monitoring
├── automation/
│   ├── vault-sync.py          # Automated vault synchronization integration
│   └── generate-docs.py       # Automated documentation generation script
├── testing/
│   └── run-suite.py           # Comprehensive test execution and reporting
└── git-hooks/
    └── pre-commit-docs        # Git hook for automated documentation updates
coachntt.py                    # Main CLI entry point with command routing and help system
tests/
├── __init__.py                # Test module initialization
├── conftest.py                # Root pytest configuration with shared fixtures and database setup
├── pytest.ini                # Comprehensive pytest configuration with coverage and markers
├── fixtures/
│   ├── __init__.py            # Fixture module exports
│   ├── memories.py            # Memory test fixtures with safe/unsafe content and edge cases
│   ├── graphs.py              # Graph test fixtures (simple, complex, hierarchical, disconnected)
│   └── safety.py              # Safety validation fixtures with unsafe patterns and performance data
├── unit/
│   ├── __init__.py            # Unit test module
│   ├── core/                  # Core component unit tests
│   ├── api/                   # API layer unit tests
│   ├── services/              # Service layer unit tests
│   └── scripts/               # Script framework unit tests
├── integration/
│   ├── __init__.py            # Integration test module
│   ├── test_memory_lifecycle.py # Complete memory lifecycle and clustering tests
│   ├── test_cli_commands.py   # CLI command integration with output validation
│   ├── test_api_endpoints.py  # API endpoint tests with authentication and validation
│   ├── test_websocket.py      # WebSocket connection and real-time update tests
│   └── test_vault_sync.py     # Vault synchronization integration tests
├── e2e/
│   ├── __init__.py            # E2E test module
│   └── test_user_scenarios.py # Complete user workflows (learning, debugging, decision-making)
├── performance/
│   ├── __init__.py            # Performance test module
│   └── test_load.py           # Load and performance tests with concurrency validation
└── safety/
    ├── __init__.py            # Safety test module
    └── test_abstraction_enforcement.py # Safety validation and abstraction enforcement tests
.github/workflows/
└── test.yml                   # GitHub Actions CI/CD pipeline with matrix testing and coverage
.pre-commit-config.yaml        # Enhanced pre-commit hooks with exclusions and CI integration
```

### 🔑 Key Design Decisions
1. **Mandatory Abstraction**: All concrete references must be abstracted (min score 0.8)
2. **Placeholder Format**: `<placeholder_name>` (configurable)
3. **Multi-stage Validation**: Input → Abstraction → Storage → Retrieval
4. **Database Enforcement**: Safety rules enforced at PostgreSQL level

### 🚀 Quick Start Commands
```bash
# Start development environment
./scripts/start-dev.sh

# Run tests
./run_tests.py

# Connect to database
docker-compose exec postgres psql -U ccp_user -d cognitive_coding_partner
```

## 📋 Next Session Plan

**For detailed session preparation, see:** [NEXT_SESSION.md](.claude/NEXT_SESSION.md)

### Quick Summary: Session 4.4 Monitoring & Observability
- **Prerequisites**: Session 4.3 complete ✅, Testing Suite ready ✅
- **Focus**: Implement comprehensive monitoring, observability, health checks, and performance tracking
- **Context Budget**: ~2000 tokens (clean window available)
- **Estimated Output**: ~800-1000 lines

**Note**: Session 4.3 (Testing Suite Completion) was completed with comprehensive test infrastructure, >90% coverage, CI/CD pipeline, and complete test automation with safety validation.

## 📁 Pre-Session Structure Check

Before creating new files or directories:
1. **Check PRD Structure**: Review PROJECT_STRUCTURE_STATUS.md
2. **Verify Location**: Ensure files go in PRD-defined locations
3. **Document Deviations**: If diverging from PRD, document why
4. **Update Tracker**: Mark newly created structure in status doc

## 📊 Progress Tracking
- Phase 0: Safety Foundation [▓▓▓▓▓▓] 100% (3/3 sessions) ✅
- Phase 1: Secure Foundation [▓▓▓▓▓▓] 100% (4/4 sessions) ✅
- Phase 2: Intelligence Layer [▓▓▓▓▓▓] 100% (4/4 sessions) ✅
- Phase 3: Knowledge Integration [▓▓▓▓▓▓] 100% (4/4 sessions) ✅
- Phase 4: Integration & Polish [▓▓▓▓▓▓] 100% (7/7 sessions: 4.1a ✅, 4.1b ✅, 4.2a ✅, 4.2b ✅, 4.2c ✅, 4.2d ✅, 4.3 ✅)

## 📊 Context Management Protocol

### Session Start Protocol
When starting a session, I will provide:
- **Estimated Output**: Expected lines of code/documentation
- **Context Budget**: Percentage allocation of available window
- **Commit Points**: Clear checkpoints for saving progress

### Progress Indicators
- ✅ **Component Complete**: Major task finished
- 📊 **Context Update**: Current usage estimate
- 🎯 **Next Target**: What's coming next
- 💡 **Checkpoint Opportunity**: Good time to commit

### Context Estimation Guidelines
- **SQL Migrations**: ~500-800 lines per 1000 tokens
- **Python Code**: ~300-500 lines per 1000 tokens
- **Tests**: ~400-600 lines per 1000 tokens
- **Documentation**: ~200-300 lines per 1000 tokens

### Checkpoint Triggers
- **60% Usage**: Suggest commit checkpoint
- **80% Usage**: Switch to essential completion mode
- **Major Component**: Always suggest checkpoint opportunity

## ⚠️ Important Notes
- **Context Window**: Keep initial load under 3000 tokens
- **Progressive Loading**: Start minimal, load files as needed
- **Safety First**: Every feature must support abstraction from the start
- **No Retrofitting**: Build safety into foundation, not added later
- **Session Completion**: Always update NEXT_SESSION.md before final commit

## 📝 Session Completion Protocol

### Mandatory End-of-Session Tasks
Before committing session completion, **ALWAYS** complete these steps:

1. **Update Session Status**:
   - [ ] Update CLAUDE.md with current session achievements
   - [ ] Update progress tracking percentage
   - [ ] Add new components to architecture summary

2. **Prepare Next Session**:
   - [ ] Update NEXT_SESSION.md for next session number and focus
   - [ ] Update quick start command with current session completion note
   - [ ] Update context files list for next session requirements
   - [ ] Update prerequisites to include current session as complete

3. **Documentation Updates**:
   - [ ] Document new capabilities and integration points
   - [ ] Update performance benchmarks if applicable
   - [ ] Record any architectural decisions or deviations

4. **Git Commit Requirements**:
   - [ ] Comprehensive commit message with session summary
   - [ ] Include performance results and component overview
   - [ ] Tag major achievements and integrations
   - [ ] Follow established commit message format

### Commit Message Template
```
[Session X.Y]: [Session Name] with [key achievement]

## Summary
- [Primary achievement 1]
- [Primary achievement 2]
- [Primary achievement 3]

## [Component Category] ([lines] lines):
- [Component 1]: [description]
- [Component 2]: [description]

## Key Features
- [Feature 1 with performance metric]
- [Feature 2 with safety compliance]
- [Feature 3 with integration point]

## Testing & Validation
- [Test coverage details]
- [Performance validation results]
- [Safety compliance verification]

## Next Session Preparation
- Updated NEXT_SESSION.md for Session [X.Y+1]
- [Any specific preparation notes]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**This protocol ensures**:
- ✅ Consistent session transitions
- ✅ Complete project state tracking
- ✅ Ready-to-start next session preparation
- ✅ Comprehensive development history