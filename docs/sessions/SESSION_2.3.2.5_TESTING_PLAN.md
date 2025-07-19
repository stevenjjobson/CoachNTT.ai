# Session 2.3.2.5: Testing Foundation Catch-Up Plan

## 🚨 Critical Context

**Current State**: 
- Test Coverage: ~15% (Target: 90%)
- Audio Services: 0 tests
- Voice Command Framework: Specifications only, no implementation
- Risk Level: HIGH - Building voice integration on untested foundations

**Decision**: PAUSE development to establish testing foundation before Session 2.3.3

## 📊 Testing Gap Analysis

### Untested Critical Services

#### Backend (Phase 1)
- [ ] Memory repository operations
- [ ] Safety validation enforcement
- [ ] WebSocket message handling
- [ ] Database transactions
- [ ] API endpoints

#### VSCode Extension (Phase 2)
- [ ] Extension activation
- [ ] MCP client connection
- [ ] Memory tree provider
- [ ] WebView lifecycle
- [ ] Audio services (CRITICAL):
  - AudioCaptureService
  - VoiceActivityDetector
  - AudioPlaybackService

## 🎯 Testing Priorities (Ordered)

### 1. Backend Smoke Tests (30 min)
```bash
# Verify basic functionality
docker-compose up -d
curl http://localhost:8000/health

# Database connectivity
docker-compose exec postgres pg_isready -U coachntt_user -d coachntt_db

# Run existing tests
python -m pytest tests/unit/core/test_safety.py -v
python -m pytest tests/integration/test_memory_lifecycle.py -v
```

### 2. Extension Foundation (1 hour)
```bash
cd vscode-extension

# Set up Jest
npm install --save-dev @types/jest jest ts-jest @vscode/test-electron

# Create jest.config.js
cat > jest.config.js << EOF
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/test/**'
  ]
};
EOF

# Run tests
npm test
```

### 3. Audio Pipeline Tests (2 hours)

#### Voice Activity Detector Tests
```typescript
describe('VoiceActivityDetector', () => {
  it('should detect speech above threshold', async () => {
    const vad = new VoiceActivityDetector();
    const audioData = createTestAudioData(amplitude: 0.8);
    const result = await vad.process(audioData);
    expect(result.isSpeech).toBe(true);
  });

  it('should ignore noise below threshold', async () => {
    const vad = new VoiceActivityDetector();
    const audioData = createTestAudioData(amplitude: 0.1);
    const result = await vad.process(audioData);
    expect(result.isSpeech).toBe(false);
  });
});
```

#### Audio Capture Tests
```typescript
describe('AudioCaptureService', () => {
  it('should capture audio when activated', async () => {
    const mockStream = createMockMediaStream();
    const capture = AudioCaptureService.getInstance();
    
    await capture.startCapture();
    expect(capture.isCapturing()).toBe(true);
    
    const audioData = await capture.stopCapture();
    expect(audioData).toBeDefined();
    expect(audioData.byteLength).toBeGreaterThan(0);
  });
});
```

### 4. WebSocket Integration (1 hour)
```typescript
describe('MCP WebSocket Integration', () => {
  it('should maintain stable connection', async () => {
    const client = MCPClient.getInstance();
    await client.connect();
    
    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    expect(client.isConnected()).toBe(true);
    
    // Test reconnection
    client.disconnect();
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(client.isConnected()).toBe(true); // Should auto-reconnect
  });
});
```

### 5. Critical Path E2E Test (1 hour)
```typescript
describe('Voice Command E2E', () => {
  it('should process voice command end-to-end', async () => {
    // 1. Capture audio
    const audioCapture = AudioCaptureService.getInstance();
    await audioCapture.startCapture();
    
    // 2. Simulate speech
    const testAudio = createTestSpeechAudio('find all functions');
    await audioCapture.processAudio(testAudio);
    
    // 3. Stop and get result
    const capturedAudio = await audioCapture.stopCapture();
    
    // 4. Mock transcription
    const transcription = 'find all functions';
    
    // 5. Process through NLQ
    const nlqParser = new NLQParser();
    const query = await nlqParser.parse(transcription);
    
    expect(query).toBeDefined();
    expect(query.intent.type).toBe('find');
    expect(query.targets).toContainEqual(
      expect.objectContaining({ type: 'function' })
    );
  });
});
```

## 📋 Test Implementation Checklist

### Infrastructure Setup
- [ ] Install Jest and testing dependencies
- [ ] Create jest.config.js
- [ ] Set up test fixtures directory
- [ ] Create mock factories
- [ ] Configure coverage reporting

### Backend Tests
- [ ] API health check
- [ ] Database connection
- [ ] Memory CRUD operations
- [ ] Safety validation
- [ ] WebSocket pub/sub

### Extension Tests
- [ ] Extension activation
- [ ] Command registration
- [ ] Status bar updates
- [ ] Tree view providers
- [ ] WebView lifecycle

### Audio Service Tests
- [ ] Voice Activity Detection
- [ ] Audio capture start/stop
- [ ] Audio encoding to WAV
- [ ] Playback service
- [ ] Error handling

### Integration Tests
- [ ] Extension → Backend flow
- [ ] WebSocket stability
- [ ] Real-time updates
- [ ] Memory synchronization
- [ ] Audio pipeline E2E

## 📊 Success Metrics

### Coverage Targets
- Overall: 60% (minimum before proceeding)
- Critical Path: 80%
- Audio Services: 70%
- Safety Systems: 90%

### Performance Benchmarks
- Extension activation: <2s
- WebSocket connection: <1s
- Audio capture latency: <10ms
- Memory operations: <200ms

## 🚀 Testing Commands

```bash
# Backend tests
cd /path/to/project
python -m pytest tests/ -v --cov=src --cov-report=html

# Extension tests
cd vscode-extension
npm test -- --coverage

# Specific service tests
npm test -- --testNamePattern="AudioCapture"
npm test -- --testNamePattern="MCPClient"
npm test -- --testNamePattern="VoiceCommand"

# Integration tests
npm test -- --testPathPattern="integration"
```

## 📝 Documentation Requirements

### Test Documentation
- [ ] Update README with test commands
- [ ] Document test architecture
- [ ] Create troubleshooting guide
- [ ] Add CI/CD test configuration

### Coverage Reports
- [ ] Generate HTML coverage reports
- [ ] Document coverage gaps
- [ ] Create improvement roadmap
- [ ] Track metrics over time

## 🔄 Next Steps After Testing

1. **Review Results**: Analyze coverage reports and identify remaining gaps
2. **Fix Critical Issues**: Address any failing tests or broken functionality
3. **Document Findings**: Update project documentation with test results
4. **Plan Remediation**: Schedule follow-up testing for remaining gaps
5. **Resume Development**: Proceed to Session 2.3.3 with confidence

## ⚠️ Risk Mitigation

### If Tests Reveal Major Issues
1. **Critical Failures**: Fix immediately before proceeding
2. **Performance Issues**: Profile and optimize
3. **Integration Problems**: Review architecture
4. **Coverage Gaps**: Plan dedicated testing sessions

### Testing Best Practices Going Forward
1. **Test-First Development**: Write tests before implementation
2. **Continuous Testing**: Run tests after each change
3. **Coverage Monitoring**: Track metrics in each session
4. **Integration Focus**: Test connections between components

## 📅 Timeline Estimate

- **Total Time**: 5-6 hours
- **Backend**: 1-2 hours
- **Extension**: 2-3 hours
- **Integration**: 1-2 hours
- **Documentation**: 30 minutes

This testing session is critical for ensuring a stable foundation before proceeding with voice integration. Taking time now will prevent cascading failures and debugging nightmares later.