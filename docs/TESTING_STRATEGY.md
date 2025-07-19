# CoachNTT.ai Testing Strategy

## 🎯 Testing Philosophy

**Core Principle**: Test early, test often, test thoroughly.

After discovering critical test coverage gaps at Session 2.3.2 (~15% coverage vs 90% target), we're implementing a comprehensive testing strategy to ensure system reliability and maintainability.

## 📊 Coverage Targets

### Overall Goals
- **Minimum Coverage**: 80%
- **Target Coverage**: 90%
- **Critical Path Coverage**: 95%
- **Safety Systems**: 100%

### Service-Specific Targets
| Service Category | Current | Target | Priority |
|-----------------|---------|---------|----------|
| Safety/Abstraction | 85% | 100% | CRITICAL |
| Core Backend | 60% | 90% | HIGH |
| Audio Services | 0% | 80% | CRITICAL |
| Voice Commands | 0% | 85% | HIGH |
| WebSocket/MCP | 20% | 90% | HIGH |
| UI/WebViews | 10% | 70% | MEDIUM |

## 🏗️ Testing Architecture

### Test Types

#### 1. Unit Tests
- **Purpose**: Test individual components in isolation
- **Tools**: Jest (TypeScript), pytest (Python)
- **Coverage**: All public methods and functions
- **Mocking**: External dependencies

#### 2. Integration Tests
- **Purpose**: Test component interactions
- **Tools**: Jest + VSCode Test API, pytest-asyncio
- **Coverage**: Critical workflows
- **Focus**: Data flow, API contracts

#### 3. End-to-End Tests
- **Purpose**: Test complete user scenarios
- **Tools**: VSCode Extension Tester, Playwright
- **Coverage**: Critical user paths
- **Environment**: As close to production as possible

#### 4. Performance Tests
- **Purpose**: Ensure response time targets
- **Tools**: Jest performance, Python profiling
- **Metrics**: Latency, throughput, resource usage
- **Targets**: <200ms API, <50ms WebSocket, <10ms audio

## 📋 Session Testing Protocol

### Pre-Session Checklist
```markdown
- [ ] Run smoke tests on dependencies
- [ ] Verify previous session's tests pass
- [ ] Check current coverage metrics
- [ ] Review integration points
```

### During Development
```markdown
- [ ] Write test before implementation (TDD)
- [ ] Run tests after each component
- [ ] Test edge cases and error paths
- [ ] Verify integration points
```

### Post-Session Requirements
```markdown
- [ ] All new code has tests
- [ ] Coverage increased or maintained
- [ ] Integration tests pass
- [ ] Performance benchmarks met
- [ ] Document any test debt
```

## 🧪 Test Infrastructure

### Backend (Python)
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

### Extension (TypeScript)
```json
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: [
    '**/__tests__/**/*.ts',
    '**/?(*.)+(spec|test).ts'
  ],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/test/**'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  }
};
```

## 🔄 Continuous Testing

### Git Hooks
```bash
# .git/hooks/pre-commit
#!/bin/bash
npm test -- --coverage --watchAll=false
if [ $? -ne 0 ]; then
  echo "Tests failed. Commit aborted."
  exit 1
fi
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Backend Tests
        run: |
          python -m pytest --cov
      - name: Extension Tests
        run: |
          cd vscode-extension
          npm test -- --coverage
```

## 🎭 Test Patterns

### Mock Factories
```typescript
// test/factories/audio.factory.ts
export class AudioFactory {
  static createMockStream(): MediaStream {
    return {
      getTracks: () => [],
      // ... mock implementation
    } as unknown as MediaStream;
  }
  
  static createTestAudio(options: AudioOptions): Float32Array {
    // Generate test audio data
  }
}
```

### Test Fixtures
```python
# tests/fixtures/memory_fixtures.py
@pytest.fixture
def sample_memory():
    return Memory(
        content="Test memory content",
        intent_type="exploration",
        safety_score=0.95
    )
```

### Integration Test Helpers
```typescript
// test/helpers/extension.helper.ts
export async function activateExtension(): Promise<vscode.ExtensionContext> {
  const ext = vscode.extensions.getExtension('coachntt.coachntt');
  await ext?.activate();
  return ext?.exports;
}
```

## 📈 Metrics & Reporting

### Coverage Reports
- **Location**: `coverage/` directory
- **Format**: HTML, LCOV, Console
- **Frequency**: Every test run
- **Tracking**: Git-ignored, CI artifacts

### Performance Metrics
```typescript
interface PerformanceTarget {
  operation: string;
  target: number; // milliseconds
  p95: number;    // 95th percentile
  p99: number;    // 99th percentile
}

const targets: PerformanceTarget[] = [
  { operation: 'extension.activate', target: 2000, p95: 2500, p99: 3000 },
  { operation: 'audio.capture', target: 10, p95: 15, p99: 20 },
  { operation: 'websocket.message', target: 50, p95: 75, p99: 100 }
];
```

## 🚨 Critical Path Tests

### 1. Safety System
```python
def test_safety_validation_enforces():
    """Ensure concrete data is always abstracted"""
    unsafe_content = "API_KEY=sk-12345"
    safe_content = validate_and_abstract(unsafe_content)
    assert "sk-12345" not in safe_content
    assert "<placeholder" in safe_content
```

### 2. Audio Pipeline
```typescript
test('audio capture to playback flow', async () => {
  const capture = AudioCaptureService.getInstance();
  const playback = AudioPlaybackService.getInstance();
  
  await capture.startCapture();
  const audio = await capture.stopCapture();
  
  await playback.play(audio);
  expect(playback.isPlaying()).toBe(true);
});
```

### 3. Voice Command Execution
```typescript
test('voice command end-to-end', async () => {
  const command = "find all functions that handle authentication";
  const result = await voiceCommandService.process(command);
  
  expect(result.success).toBe(true);
  expect(result.type).toBe('search');
  expect(result.results).toHaveLength(greaterThan(0));
});
```

## 🔧 Troubleshooting

### Common Test Issues

#### 1. Flaky Tests
- **Symptom**: Tests pass/fail randomly
- **Solution**: Add proper async handling, increase timeouts
- **Prevention**: Avoid time-dependent tests

#### 2. Mock Leakage
- **Symptom**: Tests affect each other
- **Solution**: Reset mocks in afterEach
- **Prevention**: Use isolated test environments

#### 3. Coverage Gaps
- **Symptom**: Untested code paths
- **Solution**: Add edge case tests
- **Prevention**: TDD approach

## 📝 Documentation Standards

### Test Documentation
- Every test file has a description header
- Complex tests have inline comments
- Integration tests document dependencies
- Performance tests specify targets

### Example Test Documentation
```typescript
/**
 * MCPClient WebSocket Integration Tests
 * 
 * Tests the MCP client's ability to maintain stable WebSocket
 * connections with automatic reconnection and message handling.
 * 
 * Dependencies:
 * - Mock WebSocket server
 * - Test authentication tokens
 * 
 * Performance targets:
 * - Connection: <1s
 * - Reconnection: <3s
 * - Message roundtrip: <50ms
 */
describe('MCPClient WebSocket Integration', () => {
  // tests...
});
```

## 🎯 Action Items

### Immediate (Session 2.3.2.5)
1. Set up Jest for VSCode extension
2. Create audio service tests
3. Test WebSocket stability
4. Achieve 60% critical path coverage

### Short-term (Next 3 sessions)
1. Reach 80% overall coverage
2. Implement performance tests
3. Set up CI/CD pipeline
4. Create test dashboards

### Long-term (Phase 2 completion)
1. Achieve 90% coverage target
2. Automated regression suite
3. Load testing infrastructure
4. Continuous monitoring

## 🏆 Success Criteria

A well-tested CoachNTT.ai system will have:
- ✅ 90%+ test coverage
- ✅ <5% test flakiness
- ✅ All performance targets met
- ✅ Automated test execution
- ✅ Clear test documentation
- ✅ Fast feedback loops
- ✅ Confidence in deployments

Remember: **Good tests enable fearless refactoring and confident feature development.**