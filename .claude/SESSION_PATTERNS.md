# 📊 Session Patterns: Context-Aware Development

## Overview

This document provides patterns and examples for managing context windows effectively during development sessions. Following these patterns prevents context exhaustion and ensures smooth session completion.

## 🎯 Core Pattern: Context-Aware Session Flow

### 1. Session Initialization

```markdown
## Session X.X Context Plan
**Estimated Output**: ~XXXX lines
**Context Budget**: ~XX% of window
**Commit Points**: 
- [ ] Component 1 complete
- [ ] Component 2 complete  
- [ ] Final documentation

Starting implementation...
```

### 2. Progress Tracking

Throughout the session, include natural progress updates:

```markdown
✅ Created migration files (7 files, ~2000 lines)
📊 Context estimate: ~30% used
🎯 Next: Python models...
```

### 3. Checkpoint Decisions

At major milestones:

```markdown
✅ Database migrations complete
💡 Good checkpoint opportunity - shall I commit before continuing?
```

## 📐 Token-to-Code Estimation Ratios

Based on empirical observation:

| Content Type | Lines per 1000 tokens | Notes |
|-------------|----------------------|-------|
| SQL Migrations | 500-800 | Complex schemas use more |
| Python Code | 300-500 | With docstrings and validation |
| Tests | 400-600 | Comprehensive test cases |
| Documentation | 200-300 | Detailed explanations |
| Config Files | 800-1000 | Usually simpler structure |

## 🔄 Example Session with Context Management

### Session 1.3 (What Should Have Happened)

```markdown
User: "Ready to start Session 1.3: Safety-First Database Schema"

Claude: "Starting Session 1.3: Safety-First Database Schema

## Context Plan
**Estimated Output**: ~3000 lines SQL + tests
**Context Budget**: ~70% of window
**Commit Points**:
- [ ] Core migrations complete
- [ ] Tests written
- [ ] Documentation updated

Creating enhanced abstraction schema..."

[After 3 migrations]

"✅ Core abstraction tables created (3 files, ~1500 lines)
📊 Progress: ~25% of budget used
🎯 Next: Memory enhancements and validation functions..."

[After all migrations]

"✅ All 7 migrations complete (5500 lines)
📊 Context estimate: ~60% used
💡 Checkpoint opportunity - recommend committing before tests

This exceeded our initial estimate. Shall I commit the migrations before proceeding?"

User: "Yes, commit then continue"

[Claude commits, then continues with fresh context awareness]
```

## 🚦 Checkpoint Decision Flowchart

```
Major Component Complete?
    ├─ Yes → Check Context %
    │   ├─ <50% → Continue (note milestone)
    │   ├─ 50-70% → Suggest checkpoint
    │   └─ >70% → Strongly recommend checkpoint
    └─ No → Continue working
```

## 📋 Buffer Management Strategy

### Context Allocation

```
Total Context Window: 100%
├─ Implementation: 70%
├─ Buffer for Testing/Fixes: 20%
└─ Documentation/Commit: 10%
```

### Warning Levels

1. **Green (0-50%)**: Normal operation
2. **Yellow (50-70%)**: Consider checkpoints
3. **Orange (70-85%)**: Prioritize essentials
4. **Red (85%+)**: Minimal completion mode

## 🎯 Patterns for Different Session Types

### Pattern A: Large Implementation Session

```markdown
1. Start with realistic estimates
2. Break into 3-4 major components
3. Checkpoint after each component
4. Reserve 30% buffer
```

### Pattern B: Bug Fix/Enhancement Session

```markdown
1. Estimate based on scope analysis
2. Implement fix
3. Write tests
4. Update docs
5. Single checkpoint before final testing
```

### Pattern C: Documentation Session

```markdown
1. Lower token consumption rate
2. Can be more aggressive (80% usage)
3. Checkpoint less frequently
```

## 💡 Anti-Patterns to Avoid

### ❌ The "Just One More Thing" Pattern

```markdown
"✅ Migrations complete (60% used)
Let me just add the Python models too..."
[Runs out of context at 95%]
```

### ❌ The "No Progress Updates" Pattern

```markdown
[Creates 5000 lines without any status updates]
"Oh, we're at 90% context..."
```

### ❌ The "Ignore the Buffer" Pattern

```markdown
"📊 85% used, but I'll finish everything..."
[Can't complete documentation or handle errors]
```

## ✅ Best Practices

1. **Conservative Estimates**: Better to overestimate context needs
2. **Early Checkpoints**: Commit working code even if incomplete
3. **Clear Communication**: Keep user informed of progress
4. **Flexible Planning**: Adapt when estimates prove wrong
5. **Buffer Respect**: Always maintain emergency context reserve

## 📊 Real Session Metrics

From actual sessions:

| Session | Planned Lines | Actual Lines | Context Used | Result |
|---------|--------------|--------------|--------------|---------|
| 0.3 | 2000 | 2500 | 85% | Success |
| 1.2 | 3000 | 3500 | 90% | Success |
| 1.3 | 3000 | 8500 | 99% | Near-crisis |

## 🔄 Recovery Strategies

When approaching context limits:

1. **Immediate Priority**: Ensure code is in working state
2. **Minimal Docs**: Create just enough documentation
3. **Quick Commit**: Save progress immediately
4. **Plan Continuation**: Note what remains for next session

## 📝 Session Template

Copy this for each new session:

```markdown
## Session X.X: [Topic]

### Context Planning
**Estimated Output**: ~XXXX lines
**Component Breakdown**:
- Component 1: ~XXX lines
- Component 2: ~XXX lines
- Tests: ~XXX lines
- Docs: ~XXX lines

**Context Checkpoints**:
- [ ] 25%: ________________
- [ ] 50%: ________________
- [ ] 75%: ________________

### Progress Tracking
- [ ] Component 1 ✅ (actual: ___ lines, ___% used)
- [ ] Component 2 ✅ (actual: ___ lines, ___% used)
- [ ] Tests ✅ (actual: ___ lines, ___% used)
- [ ] Documentation ✅ (actual: ___ lines, ___% used)

### Session Notes
[Add any deviations or learnings here]
```

## 🔄 Section Transition Protocol

When completing a major section (e.g., finishing Phase 1):

1. **Complete Final Session**: Ensure all section goals met
2. **Run Section Analysis**: Use .claude/SESSION_ANALYSIS.md template
3. **Extract Learnings**: Document what worked/didn't work
4. **Update Patterns**: Add new efficient patterns discovered
5. **Plan Next Section**: Apply learnings to upcoming work

### Analysis Triggers
- Completing a phase (0→1, 1→2, etc.)
- Major milestone completion
- After any session requiring >90% context
- When patterns significantly change

## 📁 Structure Alignment Workflow

### Before Creating New Files
1. **Check PRD Location**: 
   - Review PROJECT_STRUCTURE_STATUS.md
   - Find PRD-defined location for file type
   
2. **Decision Point**:
   ```
   Does PRD define location for this file type?
   ├─ Yes → Create in PRD location
   │   └─ Update PROJECT_STRUCTURE_STATUS.md
   └─ No → Consider best location
       ├─ Document decision
       └─ Update structure guide
   ```

3. **Progressive Implementation**:
   - Only create parent directories when needed
   - Don't create empty structure prematurely
   - Document why structure was created

### During Session
- Note any new directories created
- Track deviations from PRD
- Update structure status if significant

### In Section Analysis
- List PRD directories created
- Document any deviations with reasons
- Identify structure needed for next phase

---

Remember: Context awareness is not about restriction, but about sustainable development pace and reliable session completion.