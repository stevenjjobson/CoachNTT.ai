# 🚀 Next Session: 2.3 Intent Engine Foundation

## 📋 Session Overview

**Session**: 2.3 Intent Engine Foundation  
**Prerequisites**: Phase 1 complete ✅, Session 2.2 complete ✅  
**Focus**: Implement intelligent query analysis and connection finding system  
**Context Budget**: ~3000 tokens (clean window available)  
**Estimated Output**: ~1000-1200 lines  

## 🎯 Quick Start Command

### Copy this to start the next session:
```
I'm continuing work on CoachNTT.ai. We completed Phase 1 and Session 2.2.

Please review:
1. @.claude/NEXT_SESSION.md (this file)
2. @.claude/CLAUDE.md (current project state)
3. @project-docs/Implementation_Cadence.md (lines 339-362 for Session 2.3)
4. @src/core/embeddings/service.py (enhanced embedding capabilities)

Ready to start Session 2.3: Intent Engine Foundation.
Note: Session 2.2 (Vector Embeddings) is now complete with advanced sentence-transformer integration.
```

## 📚 Context Files to Load

### Essential Files (Load First)
1. **`.claude/CLAUDE.md`** - Current project state and architecture
2. **`project-docs/Implementation_Cadence.md`** (lines 339-362) - Session 2.3 specifications
3. **`src/core/embeddings/service.py`** - Enhanced embedding service capabilities
4. **`src/core/memory/repository.py`** - Memory system integration points

### Reference Files (Load as Needed)
- `src/core/memory/abstract_models.py` - Memory data structures
- `src/core/embeddings/models.py` - Embedding models and types
- `tests/integration/test_embeddings.py` - Embedding test patterns
- `src/core/validation/validator.py` - Safety validation framework

## ⚠️ Important Session Notes

### Session 2.2 Status: COMPLETE ✅
**Critical**: Session 2.2 (Vector Embeddings Integration) has been fully implemented with advanced sentence-transformer support. This session (2.3) builds on the enhanced embedding capabilities.

**What's Already Done**:
- ✅ EmbeddingService with text/code generation using sentence-transformers
- ✅ Advanced caching layer with LRU eviction and safety validation
- ✅ Enhanced memory creation pipeline with automatic embedding generation
- ✅ Improved clustering algorithms with weighted embedding combination
- ✅ Comprehensive test suite and performance benchmarks

## 🏗️ Implementation Strategy

### Phase 1: Core IntentEngine (40% of session)
1. Create `src/core/intent/engine.py` - Main intent analysis engine
2. Implement query analysis pipeline with safety validation
3. Create confidence scoring system for intent detection
4. Add basic intent classification framework

### Phase 2: Connection Finding (30% of session)
1. Implement semantic similarity connection finder using embeddings
2. Add temporal proximity analysis for related memories
3. Create usage pattern detection for behavioral insights
4. Integrate with existing memory clustering system

### Phase 3: Non-Directive Filtering (20% of session)
1. Implement non-directive filter to respect user autonomy
2. Create explanation generator for transparent reasoning
3. Add learning feedback loop for continuous improvement
4. Ensure safety-first approach throughout intent analysis

### Phase 4: Testing & Integration (10% of session)
1. Write comprehensive intent parsing tests
2. Test confidence calculation accuracy
3. Create integration tests with memory and embedding systems
4. Validate non-directive principle adherence

## 🔧 Technical Requirements

### New Dependencies (Optional)
```toml
# Intent analysis enhancements (if needed)
spacy = "^3.4.0"  # For advanced NLP analysis
scikit-learn = "^1.1.0"  # For pattern detection algorithms
```

### New Files to Create
- `src/core/intent/__init__.py`
- `src/core/intent/engine.py` - Main intent analysis engine
- `src/core/intent/analyzer.py` - Query analysis and classification
- `src/core/intent/models.py` - Intent data models and types
- `src/core/intent/connections.py` - Connection finding algorithms
- `tests/unit/core/intent/` - Unit tests
- `tests/integration/test_intent_engine.py` - Integration tests

### Files to Enhance
- `src/core/memory/repository.py` - Integrate intent-based queries
- `src/core/embeddings/service.py` - Support intent-driven embedding
- `src/core/__init__.py` - Export intent classes
- `src/core/memory/cluster_manager.py` - Intent-aware clustering

## 🛡️ Safety Requirements

### Mandatory Safety Checks
- [ ] All intent analysis must respect user privacy and abstraction (safety score ≥0.8)
- [ ] No concrete references in intent detection or connection finding
- [ ] Non-directive principle strictly enforced (no manipulation or coercion)
- [ ] Transparent reasoning - users understand why connections are suggested
- [ ] Intent learning respects safety boundaries and doesn't leak information
- [ ] Connection algorithms maintain abstraction throughout analysis

## 📊 Performance Targets

### Intent Analysis Performance
- **Target**: <200ms for intent classification
- **Connection Finding**: <500ms for semantic similarity analysis
- **Batch Analysis**: <1s for analyzing 5 queries simultaneously
- **Confidence Calculation**: <100ms for scoring intent matches

### Quality Metrics
- **Intent Accuracy**: >85% correct intent classification
- **Connection Relevance**: >80% of suggested connections rated as useful
- **Non-Directive Compliance**: 100% adherence to non-manipulation principles
- **Safety Validation**: Zero tolerance for concrete reference leakage

## 📋 Session Completion Checklist

### Core Implementation
- [ ] IntentEngine class created and functional
- [ ] Query analysis pipeline working
- [ ] Confidence scoring system implemented
- [ ] Intent classification framework operational
- [ ] Basic intent types defined and tested

### Connection Finding
- [ ] Semantic similarity connection finder implemented
- [ ] Temporal proximity analysis working
- [ ] Usage pattern detection functional
- [ ] Integration with clustering system complete
- [ ] Connection scoring and ranking operational

### Non-Directive Features
- [ ] Non-directive filter implemented and enforced
- [ ] Explanation generator providing transparent reasoning
- [ ] Learning feedback loop functional
- [ ] Safety validation throughout intent analysis
- [ ] User autonomy respect mechanisms validated

### Testing & Validation
- [ ] Unit tests written and passing
- [ ] Integration tests validate functionality
- [ ] Intent parsing accuracy validated
- [ ] Confidence calculation accuracy tested
- [ ] Non-directive principle compliance verified

### Session Wrap-up
- [ ] All code committed to git
- [ ] Performance results documented
- [ ] Next session planned (2.4 AST Code Analysis)
- [ ] Session analysis completed

## 🚀 Previous Achievements (Completed)

### Phase 1: Secure Foundation (100% complete)
- Session 1.1: Safety-First Project Initialization ✅
- Session 1.2: Secure PostgreSQL & pgvector Setup ✅
- Session 1.3: Safety-First Database Schema ✅
- Session 1.4: Abstract Memory Model Implementation ✅

### Phase 2 Progress: Intelligence Layer
- Session 2.1: Time Degradation Algorithm ✅ (implemented in 1.4)
- Session 2.2: Vector Embeddings Integration ✅ (just completed)

**Key Session 2.2 Achievements**:
- Advanced sentence-transformer integration with text/code embedding support
- Intelligent caching system with LRU eviction and safety validation
- Enhanced memory creation pipeline with automatic embedding generation
- Improved clustering algorithms with weighted embedding combination (40/60)
- Comprehensive test suite with performance benchmarks
- All performance targets met (>500ms single, <2s batch, >80% cache hit rate)
- Zero-tolerance safety enforcement maintained throughout