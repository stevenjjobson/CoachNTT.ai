# 🚀 Phase 2 Context: VSCode Extension & Voice Integration

## 📋 Phase Overview

**Phase**: 2 - VSCode Extension & Voice Integration  
**Duration**: 6 weeks (15 sessions)  
**Outcome**: Rich IDE integration with voice capabilities and VPS deployment  

## 🎯 Core Objectives

### 1. VSCode Extension Development
- Build comprehensive TypeScript-based extension
- Create rich UI with tree views and WebView panels
- Implement real-time connection to backend services
- Maintain zero-tolerance safety in all UI components

### 2. Voice Integration
- Natural language command processing
- Voice synthesis for responses
- Conversational monitoring interface
- Accessibility-first design

### 3. Backend Deployment
- Deploy Phase 1 services to Ubuntu 24.04 VPS
- Configure secure HTTPS endpoints
- Set up monitoring infrastructure
- Enable remote development workflow

### 4. Unified Experience
- Seamless integration of all CoachNTT.ai features
- Local development with remote backend option
- Performance optimization for real-time features
- Complete safety abstraction in UI layer

## 🏗️ Architecture Decisions

### Extension Architecture
```
VSCode Extension (TypeScript)
    ↓
MCP Client (WebSocket)
    ↓
Backend API (FastAPI on VPS)
    ↓
PostgreSQL + Services
```

### Technology Stack
- **Language**: TypeScript with strict mode
- **Build**: Webpack for bundling
- **UI**: VSCode TreeView + WebView
- **Communication**: WebSocket for real-time
- **Voice**: Web Speech API + ElevenLabs/Local TTS
- **Testing**: Jest + VSCode test framework

### Safety Implementation
- All paths abstracted in UI display
- Secure credential storage using VSCode SecretStorage
- WebView Content Security Policy
- Abstracted error messages
- No concrete references in logs

## 📦 VPS Deployment Integration

### Server Details
- **OS**: Ubuntu 24.04 LTS
- **Specs**: 2 vCPU, 8GB RAM, 100GB NVMe SSD
- **Access**: SSH root@`<vps_ip>` (145.79.0.118)
- **Docker**: Pre-installed
- **Purpose**: Host production backend services

### Deployment Stages
1. **Local Development** (Sessions 2.1.x - 2.2.x)
   - Extension connects to local backend
   - Rapid iteration and testing
   
2. **VPS Integration** (Sessions 2.3.x - 2.4.x)
   - Deploy backend to VPS
   - Configure HTTPS with Let's Encrypt
   - Test remote connections
   
3. **Production Release** (Session 2.4.3)
   - Final deployment configuration
   - Performance optimization
   - Security hardening

### Connection Configuration
```typescript
// Development
const API_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000' 
  : 'https://<domain>';

// WebSocket
const WS_URL = process.env.NODE_ENV === 'development'
  ? 'ws://localhost:8000/ws'
  : 'wss://<domain>/ws';
```

## 🔌 Integration Points

### With Phase 1 Components
- **REST API**: All endpoints available for extension
- **WebSocket**: Real-time updates and progress
- **Memory System**: Full CRUD operations
- **Knowledge Graph**: Query and visualization
- **Safety Framework**: Validation at every layer

### New Phase 2 Components
- **Voice Commands**: 50+ natural language operations
- **Audio Playback**: Memory content synthesis
- **Monitoring UI**: Real-time metrics in IDE
- **Unified WebSocket**: Multiplexed channels

## 📊 Success Metrics

### Performance Targets
- Extension activation: <50ms
- Command execution: <100ms
- WebSocket latency: <30ms
- Voice recognition: <500ms
- Memory tree load: <200ms for 1000 items

### Quality Requirements
- TypeScript coverage: 100%
- Test coverage: >90%
- Accessibility: WCAG 2.1 AA
- Safety score: ≥0.8 for all content
- Zero concrete references in UI

## 🛡️ Safety-First UI Design

### Abstraction Requirements
1. **File Paths**: Always show as `<project>/<module>/<file>`
2. **URLs**: Display as `<api_endpoint>` or `<service_url>`
3. **IDs**: Show as `<identifier>` or semantic names
4. **Errors**: Abstract stack traces and paths
5. **Configs**: Never show actual values, only types

### Security Measures
- VSCode SecretStorage for credentials
- Content Security Policy for WebViews
- Input sanitization for all user data
- Rate limiting on API calls
- Encrypted storage for sensitive settings

## 📅 Session Progression

### Week 1-2: Foundation (4 sessions)
- 2.1.1: VSCode Extension Scaffold ← **Starting Here**
- 2.1.2: MCP Client Integration
- 2.1.3: Memory Tree Provider
- 2.1.4: WebView Foundation

### Week 3-4: Core Features (4 sessions)
- 2.2.1: Audio Playback Service
- 2.2.2: Monitoring Dashboard Integration
- 2.2.3: Unified WebSocket Service
- 2.2.4: Memory Operations & Search

### Week 5: Voice Integration (4 sessions)
- 2.3.1: Voice Command Framework
- 2.3.2: Natural Language Queries
- 2.3.3: Voice Synthesis Integration
- 2.3.4: Conversational Monitoring

### Week 6: Polish & Advanced (3 sessions)
- 2.4.1: Performance Optimization
- 2.4.2: Advanced Monitoring Features
- 2.4.3: Testing & Production Readiness

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- VSCode latest stable
- Git for version control
- Access to VPS (provided)

### Development Setup
```bash
# Clone repository
git clone <repository>

# Navigate to extension directory
cd vscode-extension

# Install dependencies
npm install

# Open in VSCode
code .

# Press F5 to launch extension development host
```

### First Session Goals
1. Create extension foundation
2. Implement basic activation
3. Add status bar items
4. Create activity view
5. Set up development environment

## 📝 Key Considerations

### User Experience
- Progressive disclosure of features
- Intuitive voice commands
- Clear visual feedback
- Accessible to all users

### Developer Experience  
- Hot reload for rapid iteration
- Comprehensive logging
- Clear error messages
- Extensive documentation

### Production Readiness
- Performance monitoring
- Error tracking
- Update mechanism
- Telemetry (with consent)

---

This context document guides Phase 2 development, ensuring alignment with Phase 1 achievements while building toward the comprehensive VSCode extension with voice capabilities and VPS deployment.