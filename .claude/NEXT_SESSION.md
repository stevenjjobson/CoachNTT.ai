# 🚀 Next Session: 2.2.1 Audio Playback Service

## 📋 Session Overview

**Session**: 2.2.1 Audio Playback Service  
**Phase**: 2 - VSCode Extension & Voice Integration  
**Prerequisites**: Session 2.1.4 complete ✅, WebView foundation ready ✅  
**Focus**: Implement audio synthesis and playback controls  
**Context Budget**: ~3000 tokens  
**Estimated Output**: ~1200 lines  

## 🎯 Quick Start Command

### Copy this to start the next session:
```
I'm continuing Phase 2 of CoachNTT.ai. Session 2.1.4 (WebView Foundation) is complete.

Please review:
1. @.claude/NEXT_SESSION.md (this file)  
2. @.claude/CLAUDE.md (Session 2.1.4 complete ✅)
3. @vscode-extension/src/webview/webview-manager.ts (WebView manager)
4. @vscode-extension/src/webview/panels/memory-detail-panel.ts (Example panel)
5. @project-docs/Phase2_Implementation_Cadence.md (Session 2.2.1 requirements)

Ready to start Session 2.2.1: Audio Playback Service.
Note: WebView foundation is working with CSP security, message protocol, and theme support.
```

## 📚 Context Files to Load

### Essential Files (Load First)
1. **`vscode-extension/src/extension.ts`** - Extension state for audio service integration
2. **`vscode-extension/src/webview/webview-manager.ts`** - For audio player WebView
3. **`vscode-extension/package.json`** - Configuration and new commands
4. **`project-docs/Phase2_Implementation_Cadence.md`** - Session 2.2.1 requirements
5. **`vscode-extension/src/services/mcp-client.ts`** - For audio synthesis API calls

### Reference Files (Load as Needed)
- `vscode-extension/src/webview/message-protocol.ts` - For audio control messages
- `vscode-extension/src/webview/templates/base-template.ts` - For audio player UI
- `vscode-extension/media/webview.css` - Base styles for audio player
- `vscode-extension/src/config/settings.ts` - For audio preferences

## ⚠️ Important Session Notes

### Session 2.1.4 Complete - WebView Ready
**Session 2.1.4 Achievements**:
- ✅ WebView manager with panel lifecycle management
- ✅ Type-safe message protocol for bidirectional communication
- ✅ Secure HTML templates with CSP and nonces
- ✅ Memory detail panel with real-time updates
- ✅ Theme support with VSCode CSS variables
- ✅ Resource loading system with vscode-resource URIs
- ✅ State persistence for panel recovery
- ✅ Comprehensive test suite and documentation

**Session 2.2.1 Focus**:
- **AudioPlaybackService**: Central service for audio queue management
- **Audio WebView Player**: Rich UI controls in WebView panel
- **Status Bar Controls**: Quick playback controls
- **Audio Queue**: Manage multiple audio items
- **Volume/Speed Controls**: User preferences
- **Audio Caching**: Performance optimization

## 🏗️ Implementation Strategy

### Session 2.2.1 Deliverables
1. **Create AudioPlaybackService class**
   - Audio queue management
   - Playback state tracking
   - Event emission for UI updates
   - Integration with MCP audio synthesis

2. **Implement audio queue management**
   - Queue data structure
   - Add/remove/reorder items
   - Priority handling
   - Persistence across sessions

3. **Add playback controls in status bar**
   - Play/pause button
   - Skip forward/back
   - Current track indicator
   - Volume indicator

4. **Create audio WebView player**
   - Full playback controls
   - Queue visualization
   - Waveform display (optional)
   - Progress tracking

5. **Implement volume and speed controls**
   - User preferences
   - Keyboard shortcuts
   - Saved settings
   - Real-time adjustment

6. **Add audio caching system**
   - Cache synthesized audio
   - LRU eviction policy
   - Size limits
   - Cache invalidation

7. **Create audio format conversion**
   - Support multiple formats
   - Quality settings
   - Compression options
   - Streaming support

8. **Implement pause/resume/skip**
   - State management
   - Smooth transitions
   - Queue navigation
   - Error recovery

9. **Add audio progress tracking**
   - Current position
   - Total duration
   - Seek functionality
   - Progress events

10. **Test cross-platform audio**
    - Windows audio APIs
    - macOS audio APIs
    - Linux audio APIs
    - Fallback strategies

## 🔧 Technical Requirements

### New Files to Create
```
vscode-extension/
├── src/
│   └── services/
│       └── audio-playback-service.ts   # Central audio service
│   └── webview/
│       └── audio-player/
│           ├── audio-player-panel.ts   # WebView panel for audio
│           └── audio-queue-view.ts     # Queue visualization
│   └── models/
│       └── audio-queue.ts              # Audio queue data structures
│   └── utils/
│       └── audio-cache.ts              # Audio caching utilities
└── media/
    ├── audio-player.css                # Audio player styles
    └── audio-player.js                 # Audio player client logic
```

### Key Implementation Points
- Use Web Audio API in WebView for playback
- Handle audio synthesis via MCP backend
- Implement robust error handling
- Support keyboard shortcuts
- Ensure accessibility compliance

## 🛡️ Safety Requirements

### Mandatory Safety Checks
- [ ] All audio metadata must be abstracted
- [ ] No concrete file paths in audio queue
- [ ] Audio URLs must use vscode-resource scheme
- [ ] Error messages must not reveal system details
- [ ] Cache paths must be abstracted
- [ ] User preferences must be sanitized

## 📊 Success Metrics

### Audio Performance
- **Playback Start**: <100ms from click
- **Queue Operations**: <50ms for add/remove
- **Seek Response**: <100ms for position change
- **Cache Hit Rate**: >80% for repeated audio
- **Memory Usage**: <50MB for audio cache

### Development Goals
- **Modularity**: Reusable audio components
- **Extensibility**: Easy to add new audio sources
- **Reliability**: Graceful error handling
- **Performance**: Smooth playback without stuttering
- **Accessibility**: Full keyboard/screen reader support

## 📋 Session Completion Checklist

### Audio Service
- [ ] AudioPlaybackService created
- [ ] Queue management implemented
- [ ] Status bar controls working
- [ ] WebView player functional
- [ ] Volume/speed controls added

### Integration & Features
- [ ] MCP audio synthesis integrated
- [ ] Caching system working
- [ ] Cross-platform tested
- [ ] Keyboard shortcuts added
- [ ] Settings persistence implemented

### Testing & Documentation
- [ ] Audio service tests
- [ ] WebView player tests
- [ ] Cross-platform tests
- [ ] Performance benchmarks
- [ ] User documentation

### Session Wrap-up
- [ ] All audio files committed
- [ ] **Checkpoint**: Can play synthesized audio
- [ ] Next session planned (Session 2.2.2: Monitoring Dashboard)
- [ ] Update CLAUDE.md progress tracking

## 🚀 Looking Ahead - Week 3-4: Core Features

After audio playback, we'll build:

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
Before committing Session 2.2.1 completion:

1. **Update Session Status**:
   - [ ] Update CLAUDE.md with Session 2.2.1 achievements
   - [ ] Update progress tracking (Week 3-4: 0% → 25%)
   - [ ] Add audio components to architecture

2. **Prepare Next Session**:
   - [ ] Update NEXT_SESSION.md for Session 2.2.2 (Monitoring Dashboard)
   - [ ] Update quick start command with completion note
   - [ ] Update context files for monitoring integration

3. **Documentation Updates**:
   - [ ] Document audio architecture patterns
   - [ ] Update README with audio features
   - [ ] Record performance benchmarks

4. **Git Commit**:
   - [ ] Comprehensive commit message with audio summary
   - [ ] Include all audio service files
   - [ ] Tag audio playback milestone

## 📚 Reference: Phase 2 Implementation Cadence

From the Phase2_Implementation_Cadence document:
- **Session 2.1.1**: VSCode Extension Scaffold ✅
- **Session 2.1.2**: MCP Client Integration ✅
- **Session 2.1.3**: Memory Tree Provider ✅
- **Session 2.1.4**: WebView Foundation ✅
- **Session 2.2.1**: Audio Playback Service (Current)
- **Session 2.2.2**: Monitoring Dashboard Integration (Next)

The audio playback service will be essential for the voice integration features in Week 5.