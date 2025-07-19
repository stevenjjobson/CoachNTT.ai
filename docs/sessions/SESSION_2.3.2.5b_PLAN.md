# Session 2.3.2.5b: TypeScript Test Fixes

## Session Overview

**Goal**: Fix TypeScript compilation errors preventing 320+ tests from running and add basic abstraction safety tests.

**Context**: Session 2.3.2.5 successfully created a comprehensive test suite with 320+ tests for audio services and MCP client. However, these tests cannot run due to TypeScript compilation errors. This session takes a pragmatic approach to fix what's broken rather than building complex temporal testing infrastructure.

## Success Criteria

- [ ] All TypeScript compilation errors resolved
- [ ] All 320 existing tests pass
- [ ] 15-20 abstraction safety tests added
- [ ] 60%+ code coverage on critical paths achieved
- [ ] Ready to proceed to Session 2.3.3 (Voice Integration)

## Implementation Plan

### Phase 1: Fix TypeScript Compilation (2 hours)

#### 1.1 Install Missing Dependencies
```bash
cd vscode-extension
npm install --save-dev uuid @types/uuid @types/ws
```

#### 1.2 Create Missing Mock Files
```typescript
// src/__mocks__/managed-webview-panel.ts
export class ManagedWebviewPanel {
  panel: any = {
    webview: {
      html: '',
      postMessage: jest.fn(),
      asWebviewUri: jest.fn(uri => uri),
      onDidReceiveMessage: jest.fn()
    },
    title: '',
    reveal: jest.fn(),
    dispose: jest.fn()
  };
  
  constructor() {}
}
```

#### 1.3 Fix Service Constructor Patterns
Make ExtensionContext optional for testing:
```typescript
// Example pattern for services
class AudioService {
  constructor(private context?: vscode.ExtensionContext) {
    this.context = context || createMockExtensionContext();
  }
}
```

#### 1.4 Fix Model Exports
Add missing exports to audio-queue.ts:
- Export AudioQueueItem interface
- Export any other missing types

### Phase 2: Get Tests Running (2 hours)

#### 2.1 Incremental Test Fixes
1. Start with voice-command tests (simpler, fewer dependencies)
2. Fix audio service tests next
3. Finally fix MCP client tests
4. Run all tests together

#### 2.2 Common Fixes Needed
- Replace `it` with `test` to match existing pattern
- Fix singleton access patterns
- Update mock implementations
- Handle missing type definitions

### Phase 3: Add Abstraction Safety Tests (1 hour)

#### 3.1 Create Basic Abstraction Tests
```typescript
// src/__tests__/core/abstraction-safety.test.ts
describe('Abstraction Safety', () => {
  const abstractionTests = [
    // Paths
    { input: '/home/user/project/src/file.ts', expected: '<project>/src/file.ts' },
    { input: 'C:\\Users\\Dev\\project\\file.ts', expected: '<project>/file.ts' },
    
    // API Endpoints
    { input: 'https://api.elevenlabs.io/v1/synthesis', expected: '<api_endpoint>/synthesis' },
    { input: 'ws://localhost:8000/mcp', expected: '<websocket_endpoint>' },
    { input: 'http://localhost:3000/api', expected: '<api_endpoint>' },
    
    // Service Names
    { input: 'AudioPlaybackService', expected: '<audio_service>' },
    { input: 'VoiceActivityDetector', expected: '<vad_service>' },
    { input: 'MCPClient', expected: '<mcp_client>' },
    
    // Sensitive Data
    { input: 'sk-1234567890abcdef', expected: '<api_key>' },
    { input: 'Bearer eyJhbGciOiJIUzI1NiIs...', expected: 'Bearer <auth_token>' },
    
    // Dates (TRA Fix - Preserve)
    { input: '2025-07-18', expected: '2025-07-18' },
    { input: 'July 18, 2025', expected: 'July 18, 2025' },
    { input: 'on 2025-07-18 at 10:00', expected: 'on 2025-07-18 at 10:00' }
  ];

  test.each(abstractionTests)('abstracts $input correctly', ({ input, expected }) => {
    const result = abstractionEngine.process(input);
    expect(result).toBe(expected);
  });
});
```

### Phase 4: Verify and Document (1 hour)

#### 4.1 Run Full Test Suite
```bash
npm test -- --coverage
```

#### 4.2 Generate Coverage Report
```bash
npm test -- --coverage --coverageReporters=text-lcov > coverage.lcov
```

#### 4.3 Document Results
- Update SESSION_2.3.2.5b_RESULTS.md
- Note any remaining issues
- Prepare for Session 2.3.3

## Risk Mitigation

### If Compilation Errors Persist
1. Use `@ts-ignore` sparingly as temporary measure
2. Focus on getting subset of tests running first
3. Document complex issues for later resolution

### If Tests Reveal Bugs
1. Fix critical bugs that block testing
2. Document non-critical bugs for future sessions
3. Prioritize test stability over feature completeness

## Time Estimates

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 | 2 hours | TypeScript compiles |
| Phase 2 | 2 hours | 320 tests pass |
| Phase 3 | 1 hour | Abstraction tests added |
| Phase 4 | 1 hour | Coverage report |
| **Total** | **6 hours** | **All tests passing** |

## Next Steps

After successful completion:
1. Commit all fixes with detailed message
2. Update Living Documents
3. Proceed to Session 2.3.3 (Voice-to-Text Integration)

## Key Principle

"The best test suite is one that actually runs." Focus on pragmatic fixes over perfect architecture.