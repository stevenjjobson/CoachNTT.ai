# 🎯 Next Session: 2.3.1 Voice Command Framework

## 📋 Session Overview
- **Session**: 2.3.1
- **Title**: Voice Command Framework
- **Duration**: 1.5-2 hours
- **Complexity**: Medium-High
- **Prerequisites**: Sessions 2.1-2.2 complete ✅, Core features ready ✅

## 🎯 Primary Goals
1. Create voice command grammar and parser
2. Implement command recognition system
3. Build voice-to-action mapping framework
4. Create natural language understanding (NLU) service
5. Integrate with existing extension commands

## 📁 Files to Create/Modify
1. **vscode-extension/src/types/voice-command.types.ts** (~150 lines)
   - Voice command interfaces
   - Grammar definitions
   - Recognition results
   
2. **vscode-extension/src/services/voice-command-service.ts** (~400 lines)
   - Command grammar parser
   - Intent recognition
   - Action mapping
   - Context management
   
3. **vscode-extension/src/services/nlu-service.ts** (~300 lines)
   - Natural language processing
   - Entity extraction
   - Confidence scoring
   - Fallback handling
   
4. **vscode-extension/src/providers/voice-command-provider.ts** (~200 lines)
   - Command registration
   - Dynamic command loading
   - Help system integration
   
5. **vscode-extension/src/webview/voice-command/voice-command-panel.ts** (~300 lines)
   - Voice command testing UI
   - Real-time feedback
   - Command history
   
6. **vscode-extension/media/voice-command.css** (~150 lines)
   - Command panel styling
   - Feedback animations
   
7. **vscode-extension/media/voice-command.js** (~200 lines)
   - Client-side command handling
   - Visual feedback

## 🔍 Technical Requirements
### Command Grammar
- Simple commands: "open file", "go to line"
- Complex commands: "create function named X with parameters Y"
- Contextual commands: "fix this error", "explain this code"
- Multi-step commands: "refactor this and run tests"

### Recognition Features
- Intent classification
- Entity extraction (file names, line numbers, etc.)
- Confidence scoring
- Ambiguity resolution
- Context awareness

### Integration Points
- Map to existing VSCode commands
- Custom CoachNTT commands
- Multi-command sequences
- Undo/redo support

## 📝 Implementation Plan
### Part 1: Command Grammar
```typescript
interface VoiceCommand {
    pattern: string | RegExp;
    intent: CommandIntent;
    entities: EntityDefinition[];
    action: CommandAction;
    examples: string[];
}
```

### Part 2: Recognition Pipeline
```typescript
export class VoiceCommandService {
    public async recognize(transcript: string): Promise<RecognitionResult> {
        // Tokenization
        // Intent matching
        // Entity extraction
        // Confidence scoring
        // Action resolution
    }
}
```

### Part 3: NLU Integration
- Fuzzy matching for variations
- Synonym handling
- Common misspellings
- Context-based disambiguation

## ⚡ Performance Targets
- Recognition: <100ms for simple commands
- Complex parsing: <300ms
- Action execution: <50ms overhead
- Memory: <10MB for grammar/models

## 🧪 Testing Requirements
1. Test command recognition accuracy
2. Verify entity extraction
3. Test ambiguous inputs
4. Validate action execution
5. Test error handling

## 📚 Key Concepts
- **Intent**: The purpose of a voice command
- **Entity**: Specific values extracted from commands
- **Confidence**: How certain the recognition is
- **Context**: Current editor state affecting commands
- **Action**: The VSCode command(s) to execute

## 🔗 Integration Points
- AudioCaptureService for voice input
- VSCode command API
- Extension command registry
- Code analysis for context
- Memory system for learning

## 📦 Deliverables
1. ✅ Voice command grammar with 20+ commands
2. ✅ Recognition system with >90% accuracy
3. ✅ NLU service for natural variations
4. ✅ Testing UI for command development
5. ✅ Integration with existing commands

## 🚨 Safety Considerations
- Confirm destructive actions
- Sanitize file paths and inputs
- Limit command scope
- Audit command history
- Prevent command injection

## 💡 Innovation Opportunities
- Learn user's command patterns
- Suggest command shortcuts
- Multi-language support
- Custom command creation
- Voice macros

## 🔄 State Management
```typescript
interface CommandState {
    history: CommandHistoryEntry[];
    context: CommandContext;
    activeCommands: Map<string, CommandExecution>;
    preferences: UserPreferences;
}
```

## 📈 Success Metrics
- Recognition accuracy >90%
- Response time <300ms total
- User adoption rate
- Command success rate
- Error recovery rate

## 🎓 Learning Resources
- [VSCode Command API](https://code.visualstudio.com/api/references/commands)
- [Natural Language Understanding](https://www.nltk.org/)
- [Speech Command Datasets](https://github.com/tensorflow/docs/blob/master/site/en/r1/tutorials/sequences/audio_recognition.md)
- [Grammar Design Patterns](https://www.w3.org/TR/speech-grammar/)

## ✅ Pre-Session Checklist
- [ ] Review VSCode command list
- [ ] Design command grammar
- [ ] Plan entity types
- [ ] Consider edge cases
- [ ] Review voice input integration

## 🚀 Quick Start
```bash
# Continue from Session 2.2.4
cd vscode-extension

# Create voice command structure
mkdir -p src/services
mkdir -p src/providers
mkdir -p src/webview/voice-command

# Create type definitions
touch src/types/voice-command.types.ts

# Start development
npm run watch
```

## 📝 Context for Next Session
After completing the voice command framework, Session 2.3.2 will implement speech-to-text integration, connecting the Web Speech API with the command recognition system for real-time voice control.

**Note**: Session 2.2.4 successfully implemented:
- Advanced code analysis with AST parsing and pattern detection
- CodeLens integration with inline complexity indicators
- Living Documents (.CoachNTT) with automatic abstraction
- Integration between documents, memories, and code analysis

The infrastructure is ready for voice command context awareness with Living Documents providing persistent project knowledge.