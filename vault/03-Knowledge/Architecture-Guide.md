# 🏛️ CoachNTT.ai Architecture Guide

## 📋 Overview

This comprehensive architecture guide explains the design principles, system structure, and data flow patterns of CoachNTT.ai - a safety-first cognitive coding partner. The system implements a layered architecture with mandatory abstraction, temporal memory management, and comprehensive validation at every layer.

## 🎯 Design Principles

### Core Architectural Principles

1. **Safety-First Design**
   - Mandatory abstraction of all concrete references
   - Validation at every layer (input, processing, storage, output)
   - Zero-tolerance for data leakage
   - Fail-safe defaults in all operations

2. **Layered Architecture**
   - Clear separation of concerns
   - Well-defined interfaces between layers
   - Dependency injection for testability
   - Modular component design

3. **Temporal Awareness**
   - Time-weighted relevance calculations
   - Memory decay algorithms
   - Temporal relationship tracking
   - Context-aware processing

4. **Cognitive Enhancement**
   - Intent analysis and pattern recognition
   - Semantic similarity and clustering
   - Knowledge graph construction
   - Automated insight generation

5. **Integration-Centric**
   - Multiple interface options (CLI, API, WebSocket)
   - External system integrations (Obsidian, Git)
   - Extensible plugin architecture
   - Standardized data formats

## 🏗️ System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│   CLI Interface │   REST API      │   WebSocket Server      │
│   (coachntt.py) │   (FastAPI)     │   (Real-time Updates)   │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Memory Service  │ Graph Service   │ Integration Service     │
│ - CRUD Ops      │ - Building      │ - Vault Sync           │
│ - Search        │ - Querying      │ - Documentation        │
│ - Validation    │ - Export        │ - Checkpoints          │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Safety Framework│ Intent Engine   │ Memory Management       │
│ - Abstraction   │ - Analysis      │ - Repository           │
│ - Validation    │ - Connections   │ - Clustering           │
│ - Quality Score │ - Pattern Rec   │ - Decay Engine         │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Database Layer  │ Embedding Svc   │ External Integrations   │
│ - PostgreSQL    │ - Transformers  │ - Obsidian Vault       │
│ - pgvector      │ - Cache (LRU)   │ - Git Integration      │
│ - Safety Schema │ - Batch Process │ - File System          │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Component Interaction Model

The system follows a request-response pattern with event-driven updates:

1. **Synchronous Path**: CLI → API → Services → Database
2. **Asynchronous Path**: Background Tasks → WebSocket → Clients
3. **Safety Path**: All operations → Safety Framework → Validation
4. **Integration Path**: Services → External Systems → Sync Engine

## 🛡️ Safety Framework Architecture

### Safety-First Design Pattern

The safety framework is the cornerstone of CoachNTT.ai, ensuring no concrete references escape the system:

```
┌─────────────────────────────────────────────────────────────┐
│                   Input Validation Layer                    │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Structure Check │ Length Limit    │ Encoding Validation     │
│ - Format Valid  │ - Size Limits   │ - UTF-8 Compliance     │
│ - Schema Check  │ - Content Scan  │ - Character Filtering   │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                 Reference Detection Layer                   │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Pattern Matching│ Context Analysis│ Semantic Analysis       │
│ - Regex Rules   │ - Surroundings  │ - Intent Recognition   │
│ - Known Patterns│ - Relationships │ - Usage Patterns       │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                  Abstraction Engine Layer                   │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Reference Extract│ Pattern Generate│ Rule Application       │
│ - Concrete IDs  │ - Safe Patterns │ - Type-specific Rules  │
│ - Paths/URLs    │ - Placeholders  │ - Context Awareness    │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   Quality Assessment Layer                  │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Safety Scoring  │ Quality Metrics │ Compliance Check       │
│ - Score ≥ 0.8   │ - Completeness  │ - Policy Adherence     │
│ - Risk Level    │ - Consistency   │ - Standard Compliance  │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Safety Enforcement Mechanisms

1. **Database-Level Enforcement**
   ```sql
   -- Example safety trigger
   CREATE OR REPLACE FUNCTION validate_content_safety()
   RETURNS TRIGGER AS $$
   BEGIN
       -- Check safety score threshold
       IF NEW.safety_score < 0.8 THEN
           RAISE EXCEPTION 'Content safety score too low: %', NEW.safety_score;
       END IF;
       
       -- Validate no concrete references
       IF check_concrete_references(NEW.content) THEN
           RAISE EXCEPTION 'Concrete references detected';
       END IF;
       
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;
   ```

2. **Application-Level Validation**
   ```python
   class SafetyValidator:
       def validate(self, content: str) -> ValidationResult:
           # Multi-stage validation pipeline
           result = self.structure_validation(content)
           result = self.abstraction_validation(result)
           result = self.safety_scoring(result)
           result = self.temporal_validation(result)
           result = self.consistency_validation(result)
           return result
   ```

3. **API Middleware Enforcement**
   ```python
   class SafetyMiddleware:
       async def __call__(self, request: Request, call_next):
           # Pre-process request
           await self.validate_input(request)
           response = await call_next(request)
           # Post-process response
           await self.validate_output(response)
           return response
   ```

## 🧠 Memory System Architecture

### Memory Processing Pipeline

The memory system implements a sophisticated pipeline for content processing and storage:

```
Input Content → Validation → Abstraction → Enhancement → Storage → Retrieval
      ↓             ↓            ↓            ↓          ↓         ↓
   Structure    Reference    Intent        Embedding   Database  Search
   Validation   Detection    Analysis      Generation  Storage   Engine
                                               ↓
                                          Clustering
                                               ↓
                                         Relationship
                                          Building
```

### Memory Repository Design

```python
class SafeMemoryRepository:
    """
    Central repository implementing safety-first memory management
    with comprehensive validation and abstraction enforcement.
    """
    
    def __init__(self, validator: SafetyValidator, embeddings: EmbeddingService):
        self.validator = validator
        self.embeddings = embeddings
        self.cluster_manager = MemoryClusterManager()
        self.decay_engine = MemoryDecayEngine()
    
    async def create_memory(self, memory_data: CreateMemoryRequest) -> Memory:
        # 1. Validate structure and safety
        validation_result = await self.validator.validate(memory_data.content)
        if validation_result.safety_score < 0.8:
            raise SafetyViolationError(f"Safety score too low: {validation_result.safety_score}")
        
        # 2. Apply abstraction
        abstracted_content = await self.abstraction_engine.process(memory_data.content)
        
        # 3. Generate embeddings
        embedding = await self.embeddings.generate(abstracted_content.content)
        
        # 4. Analyze intent
        intent = await self.intent_engine.analyze(memory_data.prompt, abstracted_content.content)
        
        # 5. Create memory with temporal context
        memory = Memory(
            content=abstracted_content.content,
            embedding=embedding,
            intent=intent,
            safety_score=validation_result.safety_score,
            created_at=datetime.utcnow()
        )
        
        # 6. Store and cluster
        stored_memory = await self.store(memory)
        await self.cluster_manager.update_clusters(stored_memory)
        
        return stored_memory
```

### Temporal Memory Management

The system implements sophisticated temporal awareness:

1. **Decay Functions**
   ```python
   def calculate_temporal_weight(created_at: datetime, decay_rate: float = 0.1) -> float:
       """Calculate time-based relevance weight using exponential decay."""
       days_old = (datetime.utcnow() - created_at).days
       return math.exp(-decay_rate * days_old)
   ```

2. **Relevance Scoring**
   ```python
   def calculate_relevance(
       semantic_score: float,
       temporal_weight: float,
       usage_frequency: int,
       reinforcement_count: int
   ) -> float:
       """Multi-factor relevance calculation."""
       return (
           semantic_score * 0.4 +
           temporal_weight * 0.3 +
           math.log(usage_frequency + 1) * 0.2 +
           math.log(reinforcement_count + 1) * 0.1
       )
   ```

## 🕸️ Knowledge Graph Architecture

### Graph Construction Pipeline

The knowledge graph system builds semantic networks from memory and code data:

```
Data Sources → Node Extraction → Edge Generation → Graph Assembly → Query Engine
     ↓              ↓               ↓               ↓              ↓
  Memories      Content        Similarity     Community        Pattern
  Code Base     Analysis       Calculation    Detection        Matching
  Documents     Embedding      Weighting      Centrality       Filtering
                Validation     Filtering      Calculation      Export
```

### Graph Data Model

```python
@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    content: str  # Abstracted content
    node_type: NodeType  # memory, code, concept
    embedding: List[float]
    metadata: Dict[str, Any]
    safety_score: float
    centrality_score: float
    created_at: datetime

@dataclass
class GraphEdge:
    """Represents a relationship between nodes."""
    source_id: str
    target_id: str
    edge_type: EdgeType  # semantic, temporal, structural
    weight: float
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]

class KnowledgeGraph:
    """Main knowledge graph implementation."""
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency_matrix: scipy.sparse.csr_matrix = None
    
    async def build_from_memories(
        self,
        memories: List[Memory],
        similarity_threshold: float = 0.7
    ) -> None:
        """Build graph from memory collection."""
        # Extract nodes
        for memory in memories:
            node = self._create_node_from_memory(memory)
            self.nodes[node.id] = node
        
        # Generate edges
        for i, node1 in enumerate(self.nodes.values()):
            for j, node2 in enumerate(list(self.nodes.values())[i+1:], i+1):
                similarity = self._calculate_similarity(node1, node2)
                if similarity >= similarity_threshold:
                    edge = GraphEdge(
                        source_id=node1.id,
                        target_id=node2.id,
                        edge_type=EdgeType.SEMANTIC,
                        weight=similarity,
                        confidence=self._calculate_confidence(node1, node2),
                        created_at=datetime.utcnow()
                    )
                    self.edges.append(edge)
        
        # Calculate graph metrics
        await self._calculate_centrality()
        await self._detect_communities()
```

### Graph Query Engine

```python
class GraphQueryEngine:
    """Advanced graph querying with pattern matching."""
    
    async def query(
        self,
        graph: KnowledgeGraph,
        query: GraphQuery
    ) -> GraphQueryResult:
        """Execute complex graph query."""
        
        # 1. Parse query pattern
        pattern_nodes = self._parse_pattern_nodes(query.pattern)
        pattern_edges = self._parse_pattern_edges(query.pattern)
        
        # 2. Find matching nodes
        candidate_nodes = await self._find_candidate_nodes(
            graph, pattern_nodes, query.filters
        )
        
        # 3. Apply structural filters
        if pattern_edges:
            candidate_nodes = await self._apply_structural_filters(
                graph, candidate_nodes, pattern_edges
            )
        
        # 4. Rank results
        ranked_results = await self._rank_results(
            candidate_nodes, query.ranking_criteria
        )
        
        # 5. Extract subgraph if requested
        if query.include_subgraph:
            subgraph = await self._extract_subgraph(
                graph, ranked_results[:query.max_results]
            )
            return GraphQueryResult(nodes=ranked_results, subgraph=subgraph)
        
        return GraphQueryResult(nodes=ranked_results[:query.max_results])
```

## 🌐 API Architecture

### REST API Design

The API follows RESTful principles with comprehensive safety integration:

```python
# FastAPI Application Structure
app = FastAPI(
    title="CoachNTT.ai API",
    description="Cognitive Coding Partner API with Safety-First Design",
    version="1.0.0"
)

# Middleware Stack (order matters)
app.add_middleware(CORSMiddleware, ...)           # CORS handling
app.add_middleware(RateLimitMiddleware, ...)      # Rate limiting
app.add_middleware(AuthenticationMiddleware, ...) # JWT/API key auth
app.add_middleware(SafetyValidationMiddleware, ...)# Safety enforcement
app.add_middleware(LoggingMiddleware, ...)        # Request/response logging

# Router Registration
app.include_router(memory_router, prefix="/api/v1/memories")
app.include_router(graph_router, prefix="/api/v1/graph")
app.include_router(integration_router, prefix="/api/v1/integrations")
app.include_router(websocket_router, prefix="/ws")
```

### Request Processing Flow

```python
class MemoryEndpoint:
    """Example endpoint implementation with safety integration."""
    
    def __init__(
        self,
        memory_service: MemoryService,
        safety_validator: SafetyValidator
    ):
        self.memory_service = memory_service
        self.safety_validator = safety_validator
    
    @app.post("/api/v1/memories/")
    async def create_memory(
        self,
        request: CreateMemoryRequest,
        current_user: User = Depends(get_current_user)
    ) -> MemoryResponse:
        """Create new memory with comprehensive validation."""
        
        # 1. Validate request structure
        await self._validate_request(request)
        
        # 2. Apply safety validation
        safety_result = await self.safety_validator.validate(request.content)
        if safety_result.safety_score < 0.8:
            raise HTTPException(
                status_code=400,
                detail=f"Content safety validation failed: {safety_result.safety_score}"
            )
        
        # 3. Process through service layer
        memory = await self.memory_service.create_memory(
            request, user_id=current_user.id
        )
        
        # 4. Prepare safe response
        response = await self._prepare_safe_response(memory)
        
        # 5. Log operation
        await self._log_operation("memory_created", memory.id, current_user.id)
        
        return response
```

### WebSocket Architecture

Real-time updates use WebSocket connections with channel-based subscriptions:

```python
class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.channel_subscriptions: Dict[str, Set[str]] = defaultdict(set)
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Establish WebSocket connection with authentication."""
        await websocket.accept()
        
        # Authenticate connection
        token = await self._get_token_from_websocket(websocket)
        user = await self._authenticate_token(token)
        
        self.active_connections[client_id] = websocket
        
        # Send welcome message
        await self._send_message(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "available_channels": ["memory_updates", "graph_updates", "system_notifications"]
        })
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all subscribers of a channel."""
        subscribers = self.channel_subscriptions.get(channel, set())
        
        for client_id in subscribers:
            if client_id in self.active_connections:
                await self._send_safe_message(client_id, {
                    "channel": channel,
                    "payload": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
```

## 🔗 Integration Architecture

### Vault Synchronization Engine

The vault sync system provides bidirectional integration with Obsidian:

```python
class VaultSyncEngine:
    """Bidirectional synchronization with Obsidian vault."""
    
    def __init__(
        self,
        vault_path: Path,
        template_processor: TemplateProcessor,
        conflict_resolver: ConflictResolver,
        safety_validator: SafetyValidator
    ):
        self.vault_path = vault_path
        self.template_processor = template_processor
        self.conflict_resolver = conflict_resolver
        self.safety_validator = safety_validator
    
    async def sync_bidirectional(
        self,
        max_memories: int = 100,
        template_type: Optional[str] = None
    ) -> SyncResult:
        """Perform bidirectional synchronization."""
        
        # 1. Scan for conflicts
        conflicts = await self._detect_conflicts()
        
        # 2. Resolve conflicts
        for conflict in conflicts:
            resolution = await self.conflict_resolver.resolve(conflict)
            await self._apply_resolution(resolution)
        
        # 3. Sync memories to vault
        to_vault_result = await self._sync_memories_to_vault(
            max_memories, template_type
        )
        
        # 4. Sync vault to memories
        from_vault_result = await self._sync_vault_to_memories()
        
        # 5. Generate sync report
        return SyncResult(
            to_vault=to_vault_result,
            from_vault=from_vault_result,
            conflicts_resolved=len(conflicts),
            timestamp=datetime.utcnow()
        )
```

### Template Processing System

```python
class TemplateProcessor:
    """Safe template processing with variable substitution."""
    
    def __init__(self, safety_validator: SafetyValidator):
        self.safety_validator = safety_validator
        self.template_cache: Dict[str, Template] = {}
    
    async def process_template(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> ProcessedTemplate:
        """Process template with safety validation."""
        
        # 1. Load and validate template
        template = await self._load_template(template_name)
        await self._validate_template_safety(template)
        
        # 2. Validate variables
        safe_variables = await self._validate_variables(variables)
        
        # 3. Perform substitution
        result = template.substitute(safe_variables)
        
        # 4. Final safety check
        safety_result = await self.safety_validator.validate(result)
        if safety_result.safety_score < 0.8:
            raise TemplateSafetyError(
                f"Template output failed safety validation: {safety_result.safety_score}"
            )
        
        return ProcessedTemplate(
            content=result,
            template_name=template_name,
            variables_used=list(safe_variables.keys()),
            safety_score=safety_result.safety_score
        )
```

## 🚀 Performance Architecture

### Caching Strategy

Multi-level caching improves system performance:

```python
class CachingStrategy:
    """Multi-level caching implementation."""
    
    def __init__(self):
        # L1: In-memory LRU cache
        self.memory_cache = LRUCache(maxsize=1000)
        
        # L2: Embedding cache
        self.embedding_cache = EmbeddingCache(maxsize=10000)
        
        # L3: Query result cache
        self.query_cache = TTLCache(maxsize=5000, ttl=3600)
        
        # L4: Graph cache
        self.graph_cache = GraphCache(maxsize=100)
    
    async def get_cached_embedding(self, content: str) -> Optional[List[float]]:
        """Get embedding from cache with fallback."""
        # Check L1 cache
        cached = self.memory_cache.get(f"embedding:{hash(content)}")
        if cached:
            return cached
        
        # Check L2 embedding cache
        cached = await self.embedding_cache.get(content)
        if cached:
            self.memory_cache[f"embedding:{hash(content)}"] = cached
            return cached
        
        return None
```

### Database Optimization

Strategic indexing and query optimization:

```sql
-- Performance indexes for memory operations
CREATE INDEX CONCURRENTLY idx_memories_safety_score ON memories(safety_score) WHERE safety_score >= 0.8;
CREATE INDEX CONCURRENTLY idx_memories_created_at_desc ON memories(created_at DESC);
CREATE INDEX CONCURRENTLY idx_memories_memory_type ON memories(memory_type);
CREATE INDEX CONCURRENTLY idx_memories_embedding_cosine ON memories USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_memories_type_safety_created ON memories(memory_type, safety_score, created_at DESC);
CREATE INDEX CONCURRENTLY idx_memories_user_created ON memories(user_id, created_at DESC);

-- Partitioning for temporal data
CREATE TABLE memories_2024 PARTITION OF memories
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Query optimization views
CREATE MATERIALIZED VIEW memory_statistics AS
SELECT 
    memory_type,
    COUNT(*) as count,
    AVG(safety_score) as avg_safety_score,
    MAX(created_at) as latest_created
FROM memories 
WHERE safety_score >= 0.8
GROUP BY memory_type;
```

## 📊 Monitoring and Observability

### Metrics Collection

Comprehensive system monitoring:

```python
class MetricsCollector:
    """System metrics collection and reporting."""
    
    def __init__(self):
        # Performance metrics
        self.request_duration = Histogram(
            'request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        # Safety metrics
        self.safety_validations = Counter(
            'safety_validations_total',
            'Total safety validations',
            ['result']
        )
        
        # Memory metrics
        self.memory_operations = Counter(
            'memory_operations_total',
            'Memory operations',
            ['operation', 'status']
        )
        
        # Graph metrics
        self.graph_build_time = Histogram(
            'graph_build_duration_seconds',
            'Graph building time'
        )
    
    def record_safety_validation(self, result: str, score: float):
        """Record safety validation metrics."""
        self.safety_validations.labels(result=result).inc()
        
        # Record detailed metrics
        self.safety_score_histogram.observe(score)
        
        if score < 0.8:
            self.safety_violations.inc()
            logger.warning(f"Safety violation detected: score={score}")
```

### Health Checks

Multi-layer health monitoring:

```python
class HealthChecker:
    """Comprehensive system health checking."""
    
    async def check_system_health(self) -> HealthStatus:
        """Perform comprehensive health check."""
        checks = {
            'database': await self._check_database(),
            'safety_system': await self._check_safety_system(),
            'embedding_service': await self._check_embedding_service(),
            'vault_sync': await self._check_vault_sync(),
            'cache_systems': await self._check_cache_systems(),
            'external_integrations': await self._check_external_integrations()
        }
        
        # Calculate overall health
        healthy_count = sum(1 for status in checks.values() if status.healthy)
        overall_healthy = healthy_count == len(checks)
        
        return HealthStatus(
            healthy=overall_healthy,
            checks=checks,
            timestamp=datetime.utcnow(),
            version=__version__
        )
```

## 🔮 Future Architecture Considerations

### Scalability Patterns

Planned architectural evolution:

1. **Horizontal Scaling**
   - Microservices decomposition
   - Container orchestration (Kubernetes)
   - Load balancing strategies
   - Database sharding

2. **Performance Optimization**
   - Advanced caching layers (Redis Cluster)
   - Async processing pipelines
   - GraphQL for flexible queries
   - CDN integration for static assets

3. **Enhanced Security**
   - Zero-trust network model
   - Advanced threat detection
   - Compliance automation
   - Audit trail optimization

4. **AI/ML Integration**
   - Model serving infrastructure
   - A/B testing framework
   - Real-time model updates
   - Federated learning support

### Extensibility Framework

```python
class PluginManager:
    """Framework for extending system functionality."""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[Callable]] = defaultdict(list)
    
    async def register_plugin(self, plugin: Plugin) -> None:
        """Register new plugin with safety validation."""
        # Validate plugin safety
        await self._validate_plugin_safety(plugin)
        
        # Register hooks
        for hook_name, callback in plugin.hooks.items():
            self.hooks[hook_name].append(callback)
        
        self.plugins[plugin.name] = plugin
    
    async def execute_hook(self, hook_name: str, context: dict) -> dict:
        """Execute all callbacks for a hook."""
        for callback in self.hooks.get(hook_name, []):
            context = await callback(context)
            
            # Validate hook output safety
            if 'content' in context:
                safety_result = await self.safety_validator.validate(context['content'])
                if safety_result.safety_score < 0.8:
                    raise PluginSafetyError(f"Plugin output failed safety validation")
        
        return context
```

---

**Architecture Mastery Achieved!** 🏛️

This comprehensive architecture guide provides the foundation for understanding, extending, and optimizing the CoachNTT.ai system. The safety-first design ensures reliable, secure, and scalable cognitive coding assistance.