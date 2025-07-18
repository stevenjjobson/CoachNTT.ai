# 🚀 Next Session: 2.1.4 WebView Foundation

## 📋 Session Overview

**Session**: 2.1.4 WebView Foundation  
**Phase**: 2 - VSCode Extension & Voice Integration  
**Prerequisites**: Session 2.1.3 complete ✅, Memory tree provider ready ✅  
**Focus**: Create WebView framework for rich UI components  
**Context Budget**: ~2500 tokens  
**Estimated Output**: ~800 lines  

## 🎯 Quick Start Command

### Copy this to start the next session:
```
I'm continuing Phase 2 of CoachNTT.ai. Session 2.1.3 (Memory Tree Provider) is complete.

Please review:
1. @.claude/NEXT_SESSION.md (this file)  
2. @.claude/CLAUDE.md (Session 2.1.3 complete ✅)
3. @vscode-extension/src/providers/memory-tree-provider.ts (Tree provider)
4. @vscode-extension/src/models/memory.model.ts (Memory models)
5. @project-docs/Phase2_Implementation_Cadence.md (Session 2.1.4 requirements)

Ready to start Session 2.1.4: WebView Foundation.
Note: Memory tree is working with search, CRUD operations, and real-time updates.
```

## 📚 Context Files to Load

### Essential Files (Load First)
1. **`vscode-extension/src/extension.ts`** - Extension state for WebView integration
2. **`vscode-extension/src/providers/memory-tree-provider.ts`** - Existing tree provider
3. **`vscode-extension/src/models/memory.model.ts`** - Memory models for WebView display
4. **`vscode-extension/package.json`** - Configuration and commands
5. **`project-docs/Phase2_Implementation_Cadence.md`** - Session 2.1.4 requirements

### Reference Files (Load as Needed)
- `vscode-extension/webpack.config.js` - Build configuration for WebView resources
- `vscode-extension/src/services/mcp-client.ts` - For WebView data fetching
- `vscode-extension/src/utils/logger.ts` - Logging with abstraction
- `project-docs/VSCode_Extension_PRD.md` - WebView requirements

## ⚠️ Important Session Notes

### Session 2.1.3 Complete - Ready for WebView
**Session 2.1.3 Achievements**:
- ✅ Memory models with intent types and tree hierarchy
- ✅ MemoryTreeProvider with three-tier structure
- ✅ Full CRUD operations and bulk import/export
- ✅ Virtual document provider for memory details
- ✅ Search functionality with results view
- ✅ Context menu actions for all operations
- ✅ Real-time WebSocket updates
- ✅ Comprehensive test suite

**Session 2.1.4 Focus**:
- **WebView Manager**: Central service for panel lifecycle
- **Message Protocol**: Type-safe bidirectional communication
- **HTML Templates**: Secure template generation with CSP
- **Theme Support**: Light/dark theme integration
- **State Persistence**: Save/restore WebView state

## 🏗️ Implementation Strategy

### Session 2.1.4 Deliverables
1. **Create WebView panel manager**
   - Panel lifecycle management
   - Multiple panel support
   - Disposal and recovery
   - Active panel tracking

2. **Implement secure WebView communication**
   - Message passing protocol
   - Type-safe message interfaces
   - Request/response pattern
   - Error handling

3. **Add WebView HTML/CSS templates**
   - Base template generation
   - CSP header configuration
   - Resource URI handling
   - Theme detection

4. **Create message passing protocol**
   - Bidirectional messaging
   - Event emitter pattern
   - Message validation
   - Queue management

5. **Implement WebView state persistence**
   - State save/restore
   - Panel recovery
   - View column tracking
   - User preferences

6. **Add theme support (light/dark)**
   - VSCode theme variables
   - Dynamic theme switching
   - Custom CSS variables
   - Accessibility support

7. **Create WebView security policy**
   - Content Security Policy
   - Nonce generation
   - Script validation
   - Resource restrictions

8. **Add resource loading system**
   - Local resource URIs
   - Media file handling
   - CSS/JS bundling
   - Cache management

9. **Test WebView lifecycle**
   - Panel creation/disposal
   - State persistence
   - Message handling
   - Security validation

10. **Document WebView architecture**
    - Architecture overview
    - Message protocol docs
    - Security guidelines
    - Extension points

## 🔧 Technical Requirements

### New Files to Create
```
vscode-extension/
├── src/
│   └── webview/
│       ├── webview-manager.ts         # Central WebView management
│       ├── message-protocol.ts        # Type-safe messaging
│       └── panels/
│           └── memory-detail-panel.ts  # First WebView implementation
│       └── templates/
│           └── base-template.ts        # HTML template generation
└── media/
    └── webview.css                     # WebView styles
```

### Key Implementation Points
- Use vscode.WebviewPanel for panel management
- Implement CSP with nonces for security
- Create reusable base classes for panels
- Support VSCode theme variables
- Handle panel serialization for recovery

## 🛡️ Safety Requirements

### Mandatory Safety Checks
- [ ] All memory content must be abstracted in WebView
- [ ] No concrete paths or IDs in HTML content
- [ ] CSP must prevent external resource loading
- [ ] Message content must be validated
- [ ] Error messages must not reveal concrete details
- [ ] Resource URIs must use vscode-resource scheme

## 📊 Success Metrics

### WebView Performance
- **Panel Creation**: <100ms for initial display
- **Message Round-trip**: <50ms for simple messages
- **Theme Switch**: <100ms for complete update
- **State Recovery**: <200ms after restart
- **Resource Loading**: <50ms for local resources

### Development Goals
- **Reusability**: Base classes for future WebViews
- **Type Safety**: 100% typed message protocol
- **Security**: Strict CSP enforcement
- **Theming**: Full VSCode theme integration
- **Testing**: Mock WebView API for tests

## 📋 Session Completion Checklist

### WebView Foundation
- [ ] WebView manager service created
- [ ] Message protocol implemented
- [ ] Base template system ready
- [ ] Memory detail panel working
- [ ] CSS with theme support added

### Security & State
- [ ] CSP headers configured
- [ ] Nonce generation working
- [ ] State persistence implemented
- [ ] Panel recovery tested
- [ ] Resource loading secure

### Testing & Documentation
- [ ] WebView lifecycle tests
- [ ] Message handling tests
- [ ] Security validation tests
- [ ] Architecture documented
- [ ] Examples provided

### Session Wrap-up
- [ ] All WebView files committed
- [ ] **Checkpoint**: WebView displays custom UI
- [ ] Next session planned (Session 2.2.1: Audio Playback)
- [ ] Update CLAUDE.md progress tracking

## 🚀 Looking Ahead - Week 3-4: Core Features

After WebView foundation, we'll build:

**Session 2.2.1: Audio Playback Service**
- Audio synthesis integration
- Playback controls in status bar
- Queue management
- Volume/speed controls

**Session 2.2.2: Monitoring Dashboard Integration**
- Real-time metrics display
- Sparkline charts
- Alert notifications
- Performance CodeLens

**Session 2.2.3: Unified WebSocket Service**
- Channel multiplexing
- Event aggregation
- Backpressure handling
- Single connection for all features

**Session 2.2.4: Memory Operations & Search**
- "Store Selection as Memory" command
- Semantic search interface
- Memory tagging
- Bulk operations

## 📝 Session Completion Protocol

### End-of-Session Requirements
Before committing Session 2.1.4 completion:

1. **Update Session Status**:
   - [ ] Update CLAUDE.md with Session 2.1.4 achievements
   - [ ] Update progress tracking (Week 1-2: 75% → 100%)
   - [ ] Add WebView components to architecture

2. **Prepare Next Session**:
   - [ ] Update NEXT_SESSION.md for Session 2.2.1 (Audio Playback)
   - [ ] Update quick start command with completion note
   - [ ] Update context files for audio integration

3. **Documentation Updates**:
   - [ ] Document WebView architecture patterns
   - [ ] Update README with WebView features
   - [ ] Record security decisions

4. **Git Commit**:
   - [ ] Comprehensive commit message with WebView summary
   - [ ] Include all WebView foundation files
   - [ ] Tag Week 1-2 completion

## 📚 Reference: Phase 2 Implementation Cadence

From the Phase2_Implementation_Cadence document:
- **Session 2.1.1**: VSCode Extension Scaffold ✅
- **Session 2.1.2**: MCP Client Integration ✅
- **Session 2.1.3**: Memory Tree Provider ✅
- **Session 2.1.4**: WebView Foundation (Current)
- **Session 2.2.1**: Audio Playback Service (Next)

The WebView foundation will enable rich UI for monitoring dashboards and audio controls in future sessions.