# 🚀 Next Session: 2.1.2 MCP Client Integration

## 📋 Session Overview

**Session**: 2.1.2 MCP Client Integration  
**Phase**: 2 - VSCode Extension & Voice Integration  
**Prerequisites**: Session 2.1.1 complete ✅, Extension scaffold ready ✅  
**Focus**: Implement MCP server communication with WebSocket  
**Context Budget**: ~3000 tokens  
**Estimated Output**: ~1000 lines  

## 🎯 Quick Start Command

### Copy this to start the next session:
```
I'm continuing Phase 2 of CoachNTT.ai. Session 2.1.1 (VSCode Extension Scaffold) is complete.

Please review:
1. @.claude/NEXT_SESSION.md (this file)  
2. @.claude/CLAUDE.md (Session 2.1.1 complete ✅)
3. @vscode-extension/src/extension.ts (Main entry point)
4. @vscode-extension/src/commands/index.ts (Command infrastructure)
5. @project-docs/Phase2_Implementation_Cadence.md (Session 2.1.2 requirements)

Ready to start Session 2.1.2: MCP Client Integration.
Note: Extension foundation is ready with safety-first design.
```

## 📚 Context Files to Load

### Essential Files (Load First)
1. **`vscode-extension/src/extension.ts`** - Main extension entry point
2. **`vscode-extension/src/commands/index.ts`** - Command registry to extend
3. **`vscode-extension/src/config/settings.ts`** - Configuration service
4. **`src/api/routers/websocket.py`** - WebSocket endpoint reference
5. **`project-docs/Phase2_Implementation_Cadence.md`** - Session 2.1.2 requirements

### Reference Files (Load as Needed)
- `vscode-extension/package.json` - Extension manifest
- `src/api/dependencies.py` - JWT authentication reference
- `src/api/models/memory.py` - Memory models for MCP tools
- `project-docs/VSCode_Extension_PRD.md` - MCP integration requirements

## ⚠️ Important Session Notes

### Session 2.1.1 Complete - Ready for MCP Integration
**Session 2.1.1 Achievements**:
- ✅ Extension scaffolding with TypeScript strict mode
- ✅ 6 commands registered and working
- ✅ Status bar items with dynamic updates
- ✅ Welcome view in activity bar
- ✅ Logger with automatic abstraction
- ✅ Configuration service with validation
- ✅ F5 debugging environment ready

**Session 2.1.2 Focus**:
- **MCP Client**: Create WebSocket client for MCP server
- **Connection Management**: Retry logic and lifecycle handling
- **Type Safety**: Define MCP tool interfaces
- **Authentication**: JWT token support
- **Event System**: MCP event emitter for real-time updates

## 🏗️ Implementation Strategy

### Session 2.1.2 Deliverables
1. **Create MCPClient service class**
   - WebSocket connection handling
   - Message serialization/deserialization
   - Connection state management
   - Error handling and recovery

2. **Implement WebSocket connection management**
   - Connect/disconnect methods
   - Automatic reconnection with backoff
   - Connection status tracking
   - Heartbeat/ping-pong mechanism

3. **Add connection retry logic with backoff**
   - Exponential backoff algorithm
   - Maximum retry attempts
   - Connection timeout handling
   - User notification on failures

4. **Create type-safe MCP tool wrappers**
   - Define MCP message interfaces
   - Tool request/response types
   - Memory operation interfaces
   - Graph query interfaces

5. **Implement connection status tracking**
   - Real-time status updates
   - Status bar integration
   - Connection health monitoring
   - Error state handling

6. **Add authentication support**
   - JWT token management
   - Token refresh logic
   - Secure credential storage
   - Authentication headers

7. **Create event emitter for MCP events**
   - Event type definitions
   - Event dispatching system
   - Subscriber management
   - Event filtering

8. **Handle connection lifecycle in extension**
   - Initialize on connect command
   - Cleanup on disconnect
   - State persistence
   - Resource management

9. **Add connection commands to palette**
   - Connect with options
   - Force reconnect
   - Connection diagnostics
   - Clear connection cache

10. **Test MCP communication**
    - Mock MCP server tests
    - Connection scenario tests
    - Error handling tests
    - Performance tests

## 🔧 Technical Requirements

### New Files to Create
```
vscode-extension/src/
├── services/
│   ├── mcp-client.ts         # MCP WebSocket client
│   └── connection-manager.ts # Connection lifecycle management
├── types/
│   └── mcp.types.ts          # MCP message type definitions
└── events/
    └── mcp-events.ts         # Event system for MCP updates
```

### Key Dependencies to Add
```json
{
  "dependencies": {
    "ws": "^8.16.0",           // WebSocket client
    "eventemitter3": "^5.0.1", // Event emitter
    "p-retry": "^5.1.2"        // Retry with exponential backoff
  },
  "devDependencies": {
    "@types/ws": "^8.5.10"     // WebSocket types
  }
}
```

## 🛡️ Safety Requirements

### Mandatory Safety Checks
- [ ] All displayed paths must be abstracted in UI
- [ ] Configuration values must not expose secrets
- [ ] Status bar must show abstracted information only
- [ ] Memory content display must maintain abstractions
- [ ] Error messages must not reveal concrete details
- [ ] VPS connection details must be stored securely

## 📊 Success Metrics

### Extension Performance
- **Activation Time**: <50ms impact on VSCode startup
- **Command Response**: <100ms for all commands
- **Memory Usage**: <50MB for base extension
- **TypeScript Compilation**: <5 seconds
- **Test Coverage**: >80% for core functionality

### Development Goals
- **Hot Reload**: Working development environment
- **Debugging**: Breakpoints and inspection working
- **Type Safety**: 100% TypeScript with strict mode
- **Extensibility**: Clear command and provider patterns
- **Documentation**: Inline JSDoc for all public APIs

## 📋 Session Completion Checklist

### Extension Foundation
- [ ] VSCode extension directory created
- [ ] TypeScript and build configuration complete
- [ ] Extension manifest (package.json) configured
- [ ] Base extension activation working
- [ ] Status bar items displaying

### Core Structure
- [ ] Command registration implemented
- [ ] Configuration schema defined
- [ ] Activity bar icon and view created
- [ ] Welcome view provider implemented
- [ ] Output channel for logging ready

### Development Environment
- [ ] Debug configuration working
- [ ] Hot reload functioning
- [ ] Build tasks configured
- [ ] Test suite initialized
- [ ] Extension compiles without errors

### Session Wrap-up
- [ ] All extension files committed to git
- [ ] **Checkpoint**: Extension activates in VSCode
- [ ] Next session planned (Session 2.1.2: MCP Client Integration)
- [ ] Update CLAUDE.md progress tracking

## 🚀 Phase 1 Complete - Ready for Phase 2

### Backend Infrastructure Ready for Extension:

**Complete API System**:
- REST API with 15+ endpoints ready for extension consumption
- WebSocket support for real-time updates
- JWT authentication with flexible token handling
- Safety validation on all endpoints
- Background task management with progress tracking

**VPS Deployment Target**:
- Ubuntu 24.04 server with Docker installed
- 2 vCPU, 8GB RAM, 100GB NVMe SSD
- Ready for backend service deployment
- Will host MCP server and API for extension

**Safety Framework**:
- Zero-tolerance abstraction enforcement
- Safety metrics and scoring system
- Ready to implement in UI components
- Abstraction patterns documented

**Knowledge System**:
- Memory management with clustering
- Knowledge graph with semantic connections
- Intent analysis for intelligent queries
- Vector embeddings with caching

## 📝 Session Completion Protocol

### End-of-Session Requirements
Before committing Session 2.1.1 completion:

1. **Update Session Status**:
   - [ ] Update CLAUDE.md with Session 2.1.1 achievements
   - [ ] Update progress tracking (Week 1-2: 0% → 25%)
   - [ ] Add extension foundation details to architecture

2. **Prepare Next Session**:
   - [ ] Update NEXT_SESSION.md for Session 2.1.2 (MCP Client Integration)
   - [ ] Update quick start command with Session 2.1.1 completion note
   - [ ] Update context files list for MCP integration

3. **Documentation Updates**:
   - [ ] Document extension architecture decisions
   - [ ] Update README with extension development setup
   - [ ] Record TypeScript patterns used

4. **Git Commit**:
   - [ ] Comprehensive commit message with Session 2.1.1 summary
   - [ ] Include all extension foundation files
   - [ ] Tag beginning of Phase 2 implementation

## 📚 Reference: Phase 2 Implementation Cadence

From the Phase2_Implementation_Cadence document:
- **Session 2.1.1**: VSCode Extension Scaffold (Current)
- **Session 2.1.2**: MCP Client Integration (Next)
- **Session 2.1.3**: Memory Tree Provider
- **Session 2.1.4**: WebView Foundation

The extension will connect to the VPS-hosted backend services in later sessions.