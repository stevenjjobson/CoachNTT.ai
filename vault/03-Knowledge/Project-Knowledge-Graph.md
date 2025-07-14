# 🕸️ CoachNTT.ai Project Knowledge Graph

## 📋 Overview

This document provides a comprehensive visual representation of the CoachNTT.ai system architecture, component relationships, and data flow patterns. The knowledge graph reveals the interconnected nature of the cognitive coding partner system and helps understand how different components work together to provide safety-first AI assistance.

## 🏗️ System Architecture Graph

### High-Level System Components

```mermaid
graph TB
    %% Core User Interfaces
    CLI[CLI Interface<br/>coachntt.py] --> API[REST API Server<br/>FastAPI]
    WEB[Web Interface<br/>Future] --> API
    OBSIDIAN[Obsidian Vault<br/>Knowledge Base] --> VAULT_SYNC[Vault Sync Engine]
    
    %% API Layer
    API --> AUTH[Authentication<br/>JWT/API Keys]
    API --> MIDDLEWARE[Middleware Stack<br/>Rate Limiting, Safety]
    API --> WEBSOCKET[WebSocket<br/>Real-time Updates]
    
    %% Core Business Logic
    API --> MEMORY_SERVICE[Memory Service]
    API --> GRAPH_SERVICE[Graph Service]
    API --> INTEGRATION_SERVICE[Integration Service]
    
    %% Memory Management
    MEMORY_SERVICE --> MEMORY_REPO[Memory Repository]
    MEMORY_SERVICE --> INTENT_ENGINE[Intent Analysis Engine]
    MEMORY_SERVICE --> EMBEDDING_SERVICE[Embedding Service]
    MEMORY_SERVICE --> VALIDATION[Safety Validation Pipeline]
    
    %% Knowledge Graph System
    GRAPH_SERVICE --> GRAPH_BUILDER[Knowledge Graph Builder]
    GRAPH_SERVICE --> GRAPH_EXPORTER[Graph Exporters]
    GRAPH_SERVICE --> GRAPH_QUERY[Graph Query Engine]
    
    %% Integration Services
    INTEGRATION_SERVICE --> VAULT_SYNC
    INTEGRATION_SERVICE --> DOC_GENERATOR[Documentation Generator]
    INTEGRATION_SERVICE --> CHECKPOINT[Checkpoint System]
    
    %% Core Foundation
    MEMORY_REPO --> ABSTRACTION[Abstraction Engine]
    MEMORY_REPO --> CLUSTERING[Memory Clustering]
    MEMORY_REPO --> DECAY[Temporal Decay Engine]
    
    %% Safety Framework
    VALIDATION --> SAFETY_METRICS[Safety Metrics Collector]
    VALIDATION --> QUALITY_SCORER[Quality Scorer]
    ABSTRACTION --> PATTERN_GENERATOR[Pattern Generator]
    ABSTRACTION --> REFERENCE_EXTRACTOR[Reference Extractor]
    
    %% Data Layer
    MEMORY_REPO --> DATABASE[(PostgreSQL + pgvector<br/>Safety-First Schema)]
    EMBEDDING_SERVICE --> CACHE[LRU Cache<br/>Embeddings]
    GRAPH_BUILDER --> DATABASE
    
    %% Analysis Components
    INTENT_ENGINE --> CONNECTION_FINDER[Connection Finder]
    GRAPH_BUILDER --> AST_ANALYZER[AST Code Analyzer]
    DOC_GENERATOR --> AST_ANALYZER
    
    %% External Integrations
    VAULT_SYNC --> TEMPLATE_PROCESSOR[Template Processor]
    VAULT_SYNC --> CONFLICT_RESOLVER[Conflict Resolver]
    CHECKPOINT --> GIT[Git Integration]
    
    %% Output Formats
    GRAPH_EXPORTER --> MERMAID[Mermaid Diagrams]
    GRAPH_EXPORTER --> JSON[JSON Export]
    GRAPH_EXPORTER --> D3[D3.js Format]
    GRAPH_EXPORTER --> CYTOSCAPE[Cytoscape Format]
    GRAPH_EXPORTER --> GRAPHML[GraphML Format]
    
    %% Styling
    classDef userInterface fill:#e1f5fe
    classDef apiLayer fill:#f3e5f5
    classDef coreLogic fill:#e8f5e8
    classDef dataLayer fill:#fff3e0
    classDef safetyLayer fill:#ffebee
    classDef integrationLayer fill:#f1f8e9
    
    class CLI,WEB,OBSIDIAN userInterface
    class API,AUTH,MIDDLEWARE,WEBSOCKET apiLayer
    class MEMORY_SERVICE,GRAPH_SERVICE,INTEGRATION_SERVICE,MEMORY_REPO,INTENT_ENGINE,GRAPH_BUILDER coreLogic
    class DATABASE,CACHE dataLayer
    class VALIDATION,ABSTRACTION,SAFETY_METRICS,QUALITY_SCORER,PATTERN_GENERATOR,REFERENCE_EXTRACTOR safetyLayer
    class VAULT_SYNC,DOC_GENERATOR,CHECKPOINT,TEMPLATE_PROCESSOR,CONFLICT_RESOLVER integrationLayer
```

## 🧠 Memory System Architecture

### Memory Processing Pipeline

```mermaid
graph TD
    %% Input Sources
    USER_INPUT[User Input<br/>CLI/API] --> CONTENT_VALIDATION[Content Validation]
    CODE_ANALYSIS[Code Analysis<br/>AST Parser] --> CONTENT_VALIDATION
    VAULT_IMPORT[Vault Import<br/>Markdown] --> CONTENT_VALIDATION
    
    %% Validation Pipeline
    CONTENT_VALIDATION --> STRUCTURE_CHECK[Structure Validation]
    STRUCTURE_CHECK --> ABSTRACTION_PROC[Abstraction Processing]
    ABSTRACTION_PROC --> SAFETY_CHECK[Safety Validation]
    SAFETY_CHECK --> TEMPORAL_PROC[Temporal Processing]
    TEMPORAL_PROC --> CONSISTENCY_CHECK[Consistency Validation]
    
    %% Processing Components
    ABSTRACTION_PROC --> REF_EXTRACT[Reference Extractor]
    ABSTRACTION_PROC --> PATTERN_GEN[Pattern Generator]
    SAFETY_CHECK --> QUALITY_SCORE[Quality Scorer]
    SAFETY_CHECK --> METRICS_COLLECT[Metrics Collector]
    
    %% Memory Enhancement
    CONSISTENCY_CHECK --> INTENT_ANALYSIS[Intent Analysis]
    INTENT_ANALYSIS --> EMBEDDING_GEN[Embedding Generation]
    EMBEDDING_GEN --> CLUSTERING_PROC[Clustering Process]
    CLUSTERING_PROC --> RELATIONSHIP_BUILD[Relationship Building]
    
    %% Storage and Retrieval
    RELATIONSHIP_BUILD --> MEMORY_STORE[(Memory Storage<br/>PostgreSQL)]
    MEMORY_STORE --> MEMORY_SEARCH[Memory Search Engine]
    MEMORY_STORE --> GRAPH_INTEGRATION[Graph Integration]
    
    %% Temporal Management
    MEMORY_STORE --> DECAY_ENGINE[Decay Engine]
    DECAY_ENGINE --> TEMPORAL_WEIGHTS[Temporal Weighting]
    TEMPORAL_WEIGHTS --> RELEVANCE_CALC[Relevance Calculation]
    
    %% Output and Access
    MEMORY_SEARCH --> RESULT_RANKING[Result Ranking]
    RESULT_RANKING --> SAFETY_FILTER[Safety Filtering]
    SAFETY_FILTER --> USER_OUTPUT[User Output<br/>Abstracted]
    
    %% Styling
    classDef input fill:#e3f2fd
    classDef validation fill:#ffebee
    classDef processing fill:#e8f5e8
    classDef storage fill:#fff3e0
    classDef output fill:#f3e5f5
    
    class USER_INPUT,CODE_ANALYSIS,VAULT_IMPORT input
    class CONTENT_VALIDATION,STRUCTURE_CHECK,ABSTRACTION_PROC,SAFETY_CHECK,TEMPORAL_PROC,CONSISTENCY_CHECK validation
    class INTENT_ANALYSIS,EMBEDDING_GEN,CLUSTERING_PROC,RELATIONSHIP_BUILD processing
    class MEMORY_STORE,DECAY_ENGINE,TEMPORAL_WEIGHTS storage
    class MEMORY_SEARCH,RESULT_RANKING,SAFETY_FILTER,USER_OUTPUT output
```

## 🕸️ Knowledge Graph System

### Graph Building and Query Flow

```mermaid
graph LR
    %% Input Sources
    MEMORIES[(Memory Database)] --> NODE_EXTRACT[Node Extraction]
    CODE_BASE[Code Base<br/>AST Analysis] --> NODE_EXTRACT
    
    %% Node Processing
    NODE_EXTRACT --> NODE_CLEAN[Node Cleaning]
    NODE_CLEAN --> NODE_EMBED[Node Embedding]
    NODE_EMBED --> NODE_VALIDATE[Node Validation]
    
    %% Edge Generation
    NODE_VALIDATE --> SIMILARITY_CALC[Similarity Calculation]
    SIMILARITY_CALC --> EDGE_WEIGHT[Edge Weighting]
    EDGE_WEIGHT --> TEMPORAL_WEIGHT[Temporal Weighting]
    TEMPORAL_WEIGHT --> EDGE_FILTER[Edge Filtering]
    
    %% Graph Assembly
    EDGE_FILTER --> GRAPH_BUILD[Graph Assembly]
    GRAPH_BUILD --> CLUSTER_DETECT[Cluster Detection]
    CLUSTER_DETECT --> CENTRALITY_CALC[Centrality Calculation]
    CENTRALITY_CALC --> COMMUNITY_DETECT[Community Detection]
    
    %% Graph Storage
    COMMUNITY_DETECT --> GRAPH_STORE[(Graph Storage)]
    GRAPH_STORE --> METADATA_GEN[Metadata Generation]
    
    %% Query Processing
    USER_QUERY[User Query] --> QUERY_PARSE[Query Parsing]
    QUERY_PARSE --> PATTERN_MATCH[Pattern Matching]
    PATTERN_MATCH --> FILTER_APPLY[Filter Application]
    FILTER_APPLY --> GRAPH_STORE
    
    %% Subgraph Extraction
    GRAPH_STORE --> SUBGRAPH_EXTRACT[Subgraph Extraction]
    SUBGRAPH_EXTRACT --> TRAVERSAL[Graph Traversal<br/>BFS/DFS]
    TRAVERSAL --> RESULT_FILTER[Result Filtering]
    
    %% Export Processing
    RESULT_FILTER --> EXPORT_PREP[Export Preparation]
    EXPORT_PREP --> FORMAT_SELECT{Export Format}
    
    %% Output Formats
    FORMAT_SELECT -->|Mermaid| MERMAID_GEN[Mermaid Generator]
    FORMAT_SELECT -->|JSON| JSON_GEN[JSON Generator]
    FORMAT_SELECT -->|D3| D3_GEN[D3.js Generator]
    FORMAT_SELECT -->|Cytoscape| CYTO_GEN[Cytoscape Generator]
    FORMAT_SELECT -->|GraphML| GRAPHML_GEN[GraphML Generator]
    
    %% Final Output
    MERMAID_GEN --> OUTPUT[Graph Output]
    JSON_GEN --> OUTPUT
    D3_GEN --> OUTPUT
    CYTO_GEN --> OUTPUT
    GRAPHML_GEN --> OUTPUT
    
    %% Styling
    classDef input fill:#e3f2fd
    classDef processing fill:#e8f5e8
    classDef storage fill:#fff3e0
    classDef query fill:#f3e5f5
    classDef export fill:#e1f5fe
    
    class MEMORIES,CODE_BASE,USER_QUERY input
    class NODE_EXTRACT,NODE_CLEAN,NODE_EMBED,SIMILARITY_CALC,EDGE_WEIGHT,GRAPH_BUILD processing
    class GRAPH_STORE storage
    class QUERY_PARSE,PATTERN_MATCH,FILTER_APPLY,SUBGRAPH_EXTRACT query
    class FORMAT_SELECT,MERMAID_GEN,JSON_GEN,D3_GEN,CYTO_GEN,GRAPHML_GEN,OUTPUT export
```

## 🔗 Integration System Architecture

### Vault Synchronization Flow

```mermaid
graph TD
    %% Sync Triggers
    USER_TRIGGER[User Command<br/>sync vault] --> SYNC_ENGINE[Vault Sync Engine]
    AUTOMATED[Automated Sync<br/>Schedule/Hooks] --> SYNC_ENGINE
    API_TRIGGER[API Request<br/>Integration Endpoint] --> SYNC_ENGINE
    
    %% Direction Selection
    SYNC_ENGINE --> DIRECTION{Sync Direction}
    DIRECTION -->|to-vault| TO_VAULT[Memory → Vault]
    DIRECTION -->|from-vault| FROM_VAULT[Vault → Memory]
    DIRECTION -->|bidirectional| BOTH[Bidirectional Sync]
    
    %% Memory to Vault Flow
    TO_VAULT --> MEMORY_FETCH[Fetch Memories]
    MEMORY_FETCH --> TEMPLATE_SELECT[Template Selection]
    TEMPLATE_SELECT --> MARKDOWN_CONVERT[Markdown Conversion]
    MARKDOWN_CONVERT --> FRONTMATTER_GEN[Frontmatter Generation]
    FRONTMATTER_GEN --> VAULT_WRITE[Write to Vault]
    
    %% Vault to Memory Flow
    FROM_VAULT --> VAULT_SCAN[Scan Vault Files]
    VAULT_SCAN --> MARKDOWN_PARSE[Parse Markdown]
    MARKDOWN_PARSE --> FRONTMATTER_EXTRACT[Extract Frontmatter]
    FRONTMATTER_EXTRACT --> CONTENT_EXTRACT[Extract Content]
    CONTENT_EXTRACT --> MEMORY_CREATE[Create Memory]
    
    %% Bidirectional Flow
    BOTH --> CONFLICT_DETECT[Conflict Detection]
    CONFLICT_DETECT --> CONFLICT_RESOLVE[Conflict Resolution]
    CONFLICT_RESOLVE --> TO_VAULT
    CONFLICT_RESOLVE --> FROM_VAULT
    
    %% Safety and Validation
    MARKDOWN_CONVERT --> SAFETY_CHECK[Safety Validation]
    MEMORY_CREATE --> SAFETY_CHECK
    SAFETY_CHECK --> ABSTRACTION_APPLY[Apply Abstraction]
    
    %% Template Processing
    TEMPLATE_SELECT --> TEMPLATE_PROC[Template Processor]
    TEMPLATE_PROC --> VAR_SUBSTITUTE[Variable Substitution]
    VAR_SUBSTITUTE --> TEMPLATE_VALIDATE[Template Validation]
    
    %% Output and Reporting
    VAULT_WRITE --> SYNC_REPORT[Sync Report]
    MEMORY_CREATE --> SYNC_REPORT
    SYNC_REPORT --> STATUS_UPDATE[Status Update]
    STATUS_UPDATE --> USER_FEEDBACK[User Feedback]
    
    %% Styling
    classDef trigger fill:#e3f2fd
    classDef processing fill:#e8f5e8
    classDef safety fill:#ffebee
    classDef output fill:#f3e5f5
    
    class USER_TRIGGER,AUTOMATED,API_TRIGGER trigger
    class SYNC_ENGINE,MEMORY_FETCH,TEMPLATE_SELECT,MARKDOWN_CONVERT,VAULT_SCAN,CONFLICT_DETECT processing
    class SAFETY_CHECK,ABSTRACTION_APPLY,TEMPLATE_VALIDATE safety
    class SYNC_REPORT,STATUS_UPDATE,USER_FEEDBACK output
```

## 🏛️ API Architecture

### Request Processing Flow

```mermaid
graph TD
    %% Request Entry
    CLIENT[Client Request<br/>CLI/Web/API] --> LOAD_BALANCER[Load Balancer<br/>Future]
    LOAD_BALANCER --> FASTAPI[FastAPI Application]
    
    %% Middleware Stack
    FASTAPI --> CORS_MW[CORS Middleware]
    CORS_MW --> RATE_LIMIT_MW[Rate Limiting<br/>Token Bucket]
    RATE_LIMIT_MW --> AUTH_MW[Authentication<br/>JWT/API Key]
    AUTH_MW --> SAFETY_MW[Safety Middleware]
    SAFETY_MW --> LOGGING_MW[Logging Middleware]
    
    %% Request Routing
    LOGGING_MW --> ROUTER{Route Handler}
    ROUTER -->|/memories| MEMORY_ROUTER[Memory Router]
    ROUTER -->|/graph| GRAPH_ROUTER[Graph Router]
    ROUTER -->|/integration| INTEGRATION_ROUTER[Integration Router]
    ROUTER -->|/ws| WEBSOCKET_HANDLER[WebSocket Handler]
    
    %% Memory Operations
    MEMORY_ROUTER --> MEMORY_ENDPOINT[Memory Endpoint]
    MEMORY_ENDPOINT --> MEMORY_SERVICE[Memory Service]
    MEMORY_SERVICE --> MEMORY_VALIDATION[Memory Validation]
    MEMORY_VALIDATION --> MEMORY_PROCESSING[Memory Processing]
    
    %% Graph Operations
    GRAPH_ROUTER --> GRAPH_ENDPOINT[Graph Endpoint]
    GRAPH_ENDPOINT --> GRAPH_SERVICE[Graph Service]
    GRAPH_SERVICE --> GRAPH_VALIDATION[Graph Validation]
    GRAPH_VALIDATION --> GRAPH_PROCESSING[Graph Processing]
    
    %% Integration Operations
    INTEGRATION_ROUTER --> INTEGRATION_ENDPOINT[Integration Endpoint]
    INTEGRATION_ENDPOINT --> INTEGRATION_SERVICE[Integration Service]
    INTEGRATION_SERVICE --> BACKGROUND_TASK[Background Task Queue]
    
    %% WebSocket Handling
    WEBSOCKET_HANDLER --> WS_AUTH[WebSocket Auth]
    WS_AUTH --> CHANNEL_MGMT[Channel Management]
    CHANNEL_MGMT --> EVENT_BROADCAST[Event Broadcasting]
    
    %% Data Processing
    MEMORY_PROCESSING --> DATABASE_OPS[Database Operations]
    GRAPH_PROCESSING --> DATABASE_OPS
    DATABASE_OPS --> SAFETY_VALIDATION[Safety Validation]
    SAFETY_VALIDATION --> RESULT_FORMATTING[Result Formatting]
    
    %% Response Generation
    RESULT_FORMATTING --> RESPONSE_MIDDLEWARE[Response Middleware]
    RESPONSE_MIDDLEWARE --> SAFETY_FILTER[Safety Filtering]
    SAFETY_FILTER --> CLIENT_RESPONSE[Client Response]
    
    %% Background Tasks
    BACKGROUND_TASK --> TASK_QUEUE[Task Queue]
    TASK_QUEUE --> TASK_WORKER[Task Worker]
    TASK_WORKER --> TASK_RESULT[Task Result]
    TASK_RESULT --> EVENT_BROADCAST
    
    %% Error Handling
    MEMORY_PROCESSING --> ERROR_HANDLER[Error Handler]
    GRAPH_PROCESSING --> ERROR_HANDLER
    ERROR_HANDLER --> ERROR_RESPONSE[Error Response]
    ERROR_RESPONSE --> CLIENT_RESPONSE
    
    %% Styling
    classDef entry fill:#e3f2fd
    classDef middleware fill:#f3e5f5
    classDef routing fill:#e8f5e8
    classDef processing fill:#fff3e0
    classDef output fill:#e1f5fe
    
    class CLIENT,LOAD_BALANCER,FASTAPI entry
    class CORS_MW,RATE_LIMIT_MW,AUTH_MW,SAFETY_MW,LOGGING_MW middleware
    class ROUTER,MEMORY_ROUTER,GRAPH_ROUTER,INTEGRATION_ROUTER,WEBSOCKET_HANDLER routing
    class MEMORY_SERVICE,GRAPH_SERVICE,INTEGRATION_SERVICE,DATABASE_OPS processing
    class RESULT_FORMATTING,CLIENT_RESPONSE,ERROR_RESPONSE output
```

## 🛡️ Safety Framework Architecture

### Safety Validation Pipeline

```mermaid
graph TD
    %% Input Content
    CONTENT_INPUT[Content Input<br/>Any Source] --> CONTENT_SCAN[Content Scanning]
    
    %% Initial Validation
    CONTENT_SCAN --> STRUCTURE_VAL[Structure Validation]
    STRUCTURE_VAL --> LENGTH_CHECK[Length Validation]
    LENGTH_CHECK --> ENCODING_CHECK[Encoding Validation]
    
    %% Reference Detection
    ENCODING_CHECK --> REF_DETECTOR[Reference Detector]
    REF_DETECTOR --> PATTERN_MATCH[Pattern Matching]
    PATTERN_MATCH --> CONTEXT_ANALYSIS[Context Analysis]
    
    %% Abstraction Process
    CONTEXT_ANALYSIS --> ABSTRACTION_ENGINE[Abstraction Engine]
    ABSTRACTION_ENGINE --> REF_EXTRACTOR[Reference Extractor]
    REF_EXTRACTOR --> PATTERN_GENERATOR[Pattern Generator]
    PATTERN_GENERATOR --> ABSTRACTION_RULES[Abstraction Rules]
    
    %% Quality Assessment
    ABSTRACTION_RULES --> QUALITY_SCORER[Quality Scorer]
    QUALITY_SCORER --> SAFETY_METRICS[Safety Metrics]
    SAFETY_METRICS --> SCORE_CALC[Score Calculation]
    
    %% Validation Gates
    SCORE_CALC --> SAFETY_GATE{Safety Score ≥ 0.8?}
    SAFETY_GATE -->|Yes| TEMPORAL_VAL[Temporal Validation]
    SAFETY_GATE -->|No| QUARANTINE[Quarantine Content]
    
    %% Temporal Processing
    TEMPORAL_VAL --> CONSISTENCY_CHECK[Consistency Check]
    CONSISTENCY_CHECK --> RELATIONSHIP_VAL[Relationship Validation]
    RELATIONSHIP_VAL --> FINAL_VALIDATION[Final Validation]
    
    %% Output Processing
    FINAL_VALIDATION --> SAFE_STORAGE[Safe Storage]
    QUARANTINE --> MANUAL_REVIEW[Manual Review Queue]
    MANUAL_REVIEW --> CORRECTIVE_ACTION[Corrective Action]
    
    %% Monitoring and Metrics
    SAFETY_METRICS --> METRICS_COLLECTOR[Metrics Collector]
    METRICS_COLLECTOR --> ALERT_SYSTEM[Alert System]
    ALERT_SYSTEM --> NOTIFICATION[Safety Notifications]
    
    %% Continuous Improvement
    SAFE_STORAGE --> FEEDBACK_LOOP[Feedback Loop]
    CORRECTIVE_ACTION --> RULE_UPDATES[Rule Updates]
    RULE_UPDATES --> ABSTRACTION_RULES
    
    %% Database Enforcement
    SAFE_STORAGE --> DB_TRIGGERS[Database Triggers]
    DB_TRIGGERS --> ROW_LEVEL_SECURITY[Row Level Security]
    ROW_LEVEL_SECURITY --> AUDIT_LOGGING[Audit Logging]
    
    %% Styling
    classDef input fill:#e3f2fd
    classDef validation fill:#ffebee
    classDef processing fill:#e8f5e8
    classDef storage fill:#fff3e0
    classDef monitoring fill:#f3e5f5
    
    class CONTENT_INPUT,CONTENT_SCAN input
    class STRUCTURE_VAL,LENGTH_CHECK,ENCODING_CHECK,REF_DETECTOR,SAFETY_GATE validation
    class ABSTRACTION_ENGINE,REF_EXTRACTOR,PATTERN_GENERATOR,QUALITY_SCORER processing
    class SAFE_STORAGE,DB_TRIGGERS,ROW_LEVEL_SECURITY storage
    class METRICS_COLLECTOR,ALERT_SYSTEM,FEEDBACK_LOOP monitoring
```

## 🔄 CLI Command Architecture

### CLI Command Flow and Structure

```mermaid
graph TD
    %% Entry Point
    USER_CMD[User Command<br/>python coachntt.py] --> CLI_PARSER[CLI Parser<br/>Click Framework]
    
    %% Command Groups
    CLI_PARSER --> CMD_GROUPS{Command Groups}
    CMD_GROUPS -->|status| STATUS_CMD[Status Commands]
    CMD_GROUPS -->|memory| MEMORY_CMD[Memory Commands]
    CMD_GROUPS -->|graph| GRAPH_CMD[Graph Commands]
    CMD_GROUPS -->|sync| SYNC_CMD[Sync Commands]
    CMD_GROUPS -->|docs| DOCS_CMD[Docs Commands]
    CMD_GROUPS -->|checkpoint| CHECKPOINT_CMD[Checkpoint Commands]
    CMD_GROUPS -->|interactive| INTERACTIVE_CMD[Interactive Mode]
    CMD_GROUPS -->|config| CONFIG_CMD[Config Commands]
    
    %% Status Commands
    STATUS_CMD --> STATUS_CHECK[System Status Check]
    STATUS_CHECK --> API_HEALTH[API Health Check]
    STATUS_CHECK --> DB_HEALTH[Database Health]
    STATUS_CHECK --> SAFETY_HEALTH[Safety System Health]
    
    %% Memory Commands
    MEMORY_CMD --> MEMORY_OPS{Memory Operations}
    MEMORY_OPS -->|list| MEMORY_LIST[List Memories]
    MEMORY_OPS -->|create| MEMORY_CREATE[Create Memory]
    MEMORY_OPS -->|search| MEMORY_SEARCH[Search Memories]
    MEMORY_OPS -->|show| MEMORY_SHOW[Show Memory]
    MEMORY_OPS -->|update| MEMORY_UPDATE[Update Memory]
    MEMORY_OPS -->|delete| MEMORY_DELETE[Delete Memory]
    MEMORY_OPS -->|export| MEMORY_EXPORT[Export Memories]
    
    %% Graph Commands
    GRAPH_CMD --> GRAPH_OPS{Graph Operations}
    GRAPH_OPS -->|build| GRAPH_BUILD[Build Graph]
    GRAPH_OPS -->|list| GRAPH_LIST[List Graphs]
    GRAPH_OPS -->|show| GRAPH_SHOW[Show Graph]
    GRAPH_OPS -->|query| GRAPH_QUERY[Query Graph]
    GRAPH_OPS -->|export| GRAPH_EXPORT[Export Graph]
    GRAPH_OPS -->|subgraph| GRAPH_SUBGRAPH[Extract Subgraph]
    GRAPH_OPS -->|delete| GRAPH_DELETE[Delete Graph]
    
    %% Common Processing
    MEMORY_LIST --> CLI_ENGINE[CLI Engine]
    MEMORY_CREATE --> CLI_ENGINE
    GRAPH_BUILD --> CLI_ENGINE
    STATUS_CHECK --> CLI_ENGINE
    
    %% API Communication
    CLI_ENGINE --> HTTP_CLIENT[HTTP Client<br/>httpx]
    HTTP_CLIENT --> API_REQUEST[API Request]
    API_REQUEST --> AUTH_HEADER[Auth Headers]
    AUTH_HEADER --> API_SERVER[API Server]
    
    %% Response Processing
    API_SERVER --> RESPONSE_HANDLER[Response Handler]
    RESPONSE_HANDLER --> ERROR_HANDLER[Error Handler]
    ERROR_HANDLER --> OUTPUT_FORMATTER[Output Formatter]
    
    %% Output Formats
    OUTPUT_FORMATTER --> FORMAT_SELECT{Output Format}
    FORMAT_SELECT -->|table| TABLE_OUTPUT[Rich Table]
    FORMAT_SELECT -->|json| JSON_OUTPUT[JSON Output]
    FORMAT_SELECT -->|simple| TEXT_OUTPUT[Simple Text]
    
    %% Progress and Feedback
    CLI_ENGINE --> PROGRESS_BAR[Progress Indicators]
    OUTPUT_FORMATTER --> SUCCESS_MSG[Success Messages]
    ERROR_HANDLER --> ERROR_MSG[Error Messages]
    
    %% Interactive Mode
    INTERACTIVE_CMD --> READLINE_INIT[Readline Init]
    READLINE_INIT --> TAB_COMPLETION[Tab Completion]
    TAB_COMPLETION --> COMMAND_HISTORY[Command History]
    COMMAND_HISTORY --> INTERACTIVE_LOOP[Interactive Loop]
    
    %% Configuration
    CONFIG_CMD --> CONFIG_OPS{Config Operations}
    CONFIG_OPS -->|show| CONFIG_SHOW[Show Config]
    CONFIG_OPS -->|set| CONFIG_SET[Set Config]
    CONFIG_OPS -->|list| CONFIG_LIST[List Settings]
    CONFIG_OPS -->|reset| CONFIG_RESET[Reset Config]
    
    %% Styling
    classDef entry fill:#e3f2fd
    classDef commands fill:#e8f5e8
    classDef processing fill:#fff3e0
    classDef output fill:#f3e5f5
    classDef config fill:#e1f5fe
    
    class USER_CMD,CLI_PARSER entry
    class STATUS_CMD,MEMORY_CMD,GRAPH_CMD,SYNC_CMD,DOCS_CMD,CHECKPOINT_CMD,INTERACTIVE_CMD,CONFIG_CMD commands
    class CLI_ENGINE,HTTP_CLIENT,RESPONSE_HANDLER processing
    class OUTPUT_FORMATTER,TABLE_OUTPUT,JSON_OUTPUT,TEXT_OUTPUT,SUCCESS_MSG,ERROR_MSG output
    class CONFIG_SHOW,CONFIG_SET,CONFIG_LIST,CONFIG_RESET config
```

## 📊 Component Relationship Matrix

### System Dependencies and Interactions

| Component | Depends On | Provides To | Safety Level | Performance Impact |
|-----------|------------|-------------|--------------|-------------------|
| **CLI Interface** | API Server, Config | User Commands | High | Low |
| **REST API** | Database, Safety Framework | CLI, Web Interface | Critical | Medium |
| **Memory Repository** | Database, Validation | Memory Service | Critical | High |
| **Knowledge Graph** | Memory Repository, Embeddings | Graph Service | High | Medium |
| **Safety Framework** | Abstraction Engine, Metrics | All Components | Critical | Low |
| **Embedding Service** | Cache, Models | Memory/Graph Systems | Medium | High |
| **Vault Sync** | Template Processor, Safety | Integration Service | High | Medium |
| **WebSocket Server** | Authentication, Channels | Real-time Updates | Medium | Low |
| **Background Tasks** | Queue System, Services | Async Processing | Medium | Variable |

### Data Flow Paths

```mermaid
graph LR
    %% Primary Data Flows
    USER[User Input] --> CLI[CLI Interface]
    CLI --> API[REST API]
    API --> MEMORY[Memory System]
    MEMORY --> DB[(Database)]
    
    %% Secondary Flows
    MEMORY --> GRAPH[Knowledge Graph]
    GRAPH --> EXPORT[Export Formats]
    MEMORY --> VAULT[Vault Sync]
    VAULT --> OBSIDIAN[Obsidian]
    
    %% Safety Flows
    ALL_INPUT[All Input] --> SAFETY[Safety Framework]
    SAFETY --> VALIDATION[Validation Pipeline]
    VALIDATION --> SAFE_STORAGE[Safe Storage]
    
    %% Real-time Flows
    API --> WEBSOCKET[WebSocket]
    WEBSOCKET --> CLIENTS[Connected Clients]
    BACKGROUND[Background Tasks] --> WEBSOCKET
    
    %% Analysis Flows
    CODE[Code Analysis] --> AST[AST Parser]
    AST --> MEMORY
    AST --> DOCS[Documentation]
    
    %% Styling
    classDef userFlow fill:#e3f2fd
    classDef dataFlow fill:#e8f5e8
    classDef safetyFlow fill:#ffebee
    classDef realTimeFlow fill:#f3e5f5
    
    class USER,CLI,API userFlow
    class MEMORY,GRAPH,VAULT,DB dataFlow
    class ALL_INPUT,SAFETY,VALIDATION,SAFE_STORAGE safetyFlow
    class WEBSOCKET,CLIENTS,BACKGROUND realTimeFlow
```

## 🚀 Performance Characteristics

### System Performance Profile

| Component | Response Time | Throughput | Resource Usage | Scalability |
|-----------|---------------|------------|----------------|-------------|
| **Memory CRUD** | <500ms | 100 ops/sec | Medium CPU | Horizontal |
| **Graph Building** | <1s (100 nodes) | 10 graphs/min | High CPU/Memory | Vertical |
| **Graph Queries** | <100ms | 1000 queries/sec | Low CPU | Horizontal |
| **Embedding Generation** | <200ms (batch) | 500 items/min | High CPU | Horizontal |
| **Safety Validation** | <1ms | 10000 checks/sec | Low CPU | Horizontal |
| **Vault Sync** | <2s | 50 files/min | Medium I/O | I/O Bound |
| **API Responses** | <200ms avg | 1000 req/sec | Low CPU | Horizontal |
| **WebSocket** | <50ms latency | 1000 connections | Low CPU | Connection Pool |

### Optimization Opportunities

```mermaid
graph TD
    %% Performance Bottlenecks
    BOTTLENECKS[Performance Bottlenecks] --> EMBEDDING[Embedding Generation]
    BOTTLENECKS --> GRAPH_BUILD[Graph Building]
    BOTTLENECKS --> DB_QUERIES[Database Queries]
    BOTTLENECKS --> LARGE_SYNC[Large Vault Sync]
    
    %% Optimization Strategies
    EMBEDDING --> CACHE_OPT[Cache Optimization]
    EMBEDDING --> BATCH_PROC[Batch Processing]
    EMBEDDING --> MODEL_OPT[Model Optimization]
    
    GRAPH_BUILD --> PARALLEL_PROC[Parallel Processing]
    GRAPH_BUILD --> INCREMENTAL[Incremental Updates]
    GRAPH_BUILD --> MEMORY_OPT[Memory Optimization]
    
    DB_QUERIES --> INDEX_OPT[Index Optimization]
    DB_QUERIES --> QUERY_OPT[Query Optimization]
    DB_QUERIES --> CONNECTION_POOL[Connection Pooling]
    
    LARGE_SYNC --> STREAMING[Streaming Processing]
    LARGE_SYNC --> COMPRESSION[Compression]
    LARGE_SYNC --> PARALLEL_SYNC[Parallel Sync]
    
    %% Implementation Priority
    CACHE_OPT --> HIGH_PRIORITY[High Priority]
    INDEX_OPT --> HIGH_PRIORITY
    BATCH_PROC --> MEDIUM_PRIORITY[Medium Priority]
    PARALLEL_PROC --> MEDIUM_PRIORITY
    STREAMING --> LOW_PRIORITY[Low Priority]
    COMPRESSION --> LOW_PRIORITY
    
    %% Styling
    classDef bottleneck fill:#ffebee
    classDef optimization fill:#e8f5e8
    classDef priority fill:#f3e5f5
    
    class BOTTLENECKS,EMBEDDING,GRAPH_BUILD,DB_QUERIES,LARGE_SYNC bottleneck
    class CACHE_OPT,BATCH_PROC,PARALLEL_PROC,INDEX_OPT,STREAMING optimization
    class HIGH_PRIORITY,MEDIUM_PRIORITY,LOW_PRIORITY priority
```

## 🔮 Future Architecture Evolution

### Planned Enhancements

```mermaid
graph TD
    %% Current State
    CURRENT[Current Architecture<br/>Phase 4 Complete] --> OPTIMIZATION[Phase 5: Optimization]
    
    %% Phase 5: Performance & Scalability
    OPTIMIZATION --> CACHING[Advanced Caching<br/>Redis Integration]
    OPTIMIZATION --> MONITORING[Performance Monitoring<br/>Metrics & Alerts]
    OPTIMIZATION --> SCALING[Horizontal Scaling<br/>Load Balancing]
    
    %% Phase 6: Advanced Features
    OPTIMIZATION --> ADVANCED[Phase 6: Advanced Features]
    ADVANCED --> ML_INSIGHTS[ML-Based Insights<br/>Pattern Recognition]
    ADVANCED --> COLLABORATIVE[Collaborative Features<br/>Team Integration]
    ADVANCED --> WORKFLOW[Advanced Workflows<br/>Automation Engine]
    
    %% Phase 7: Enterprise
    ADVANCED --> ENTERPRISE[Phase 7: Enterprise]
    ENTERPRISE --> SECURITY[Enterprise Security<br/>SSO, RBAC]
    ENTERPRISE --> COMPLIANCE[Compliance Features<br/>Audit, Governance]
    ENTERPRISE --> DEPLOYMENT[Production Deployment<br/>K8s, Cloud]
    
    %% Future Integrations
    ENTERPRISE --> INTEGRATIONS[Extended Integrations]
    INTEGRATIONS --> IDE_PLUGINS[IDE Plugins<br/>VS Code, IntelliJ]
    INTEGRATIONS --> CICD[CI/CD Integration<br/>GitHub Actions]
    INTEGRATIONS --> EXTERNAL_AI[External AI APIs<br/>OpenAI, Anthropic]
    
    %% Styling
    classDef current fill:#e8f5e8
    classDef optimization fill:#e3f2fd
    classDef advanced fill:#f3e5f5
    classDef enterprise fill:#fff3e0
    classDef future fill:#e1f5fe
    
    class CURRENT current
    class OPTIMIZATION,CACHING,MONITORING,SCALING optimization
    class ADVANCED,ML_INSIGHTS,COLLABORATIVE,WORKFLOW advanced
    class ENTERPRISE,SECURITY,COMPLIANCE,DEPLOYMENT enterprise
    class INTEGRATIONS,IDE_PLUGINS,CICD,EXTERNAL_AI future
```

---

**Knowledge Graph Complete!** 🕸️

This comprehensive visualization reveals the intricate relationships and data flows within the CoachNTT.ai system, helping you understand how each component contributes to the overall cognitive coding assistance experience.