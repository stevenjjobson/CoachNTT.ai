# 📚 Documentation Organization Guide

## Overview

This guide explains the documentation structure for CoachNTT.ai, helping you find and create documentation in the right place.

## 📁 Directory Structure

```
CoachNTT.ai/
├── 📄 Root Level Files
├── 📁 .claude/          → AI Assistant Context
├── 📁 docs/             → Public Documentation
├── 📁 vault/            → Knowledge Base (Obsidian)
├── 📁 project-docs/     → Project Management
└── 📁 templates/        → Reusable Templates
```

## 📍 Where Does Each Document Type Belong?

### Root Directory (`/`)
**Purpose**: Essential project files only  
**Contains**:
- `README.md` - Project introduction and quick start
- `CHANGELOG.md` - Version history and releases
- `LICENSE` - Legal information
- `DOCUMENTATION_GUIDE.md` - This file

**Rule**: If it's not essential for someone discovering the project, it doesn't belong here.

### AI Context (`.claude/`)
**Purpose**: AI assistant working context and session management  
**Contains**:
- `CLAUDE.md` - AI context and current state
- `NEXT_SESSION.md` - Next session preparation
- `SESSION_ANALYSIS.md` - Session retrospectives
- `SESSION_PATTERNS.md` - Context management patterns

**When to use**: Any documentation specifically for AI-assisted development sessions.

### Public Documentation (`docs/`)
**Purpose**: User and developer documentation  
**Structure**:
```
docs/
├── architecture/      → System design, components
├── development/       → Setup guides, contributing
├── safety/           → Safety principles and validation
├── api/              → API references
├── database/         → Schema documentation
└── training/         → Learning modules
```

**When to use**: Documentation intended for users, contributors, or public consumption.

### Knowledge Base (`vault/`)
**Purpose**: Obsidian-based knowledge management  
**Structure**:
```
vault/
├── 00-Safety/        → Safety-first patterns
├── 01-Patterns/      → Reusable code patterns
├── 02-Sessions/      → Detailed session notes
├── 03-Decisions/     → Architecture Decision Records
├── 04-Research/      → Exploration and research
└── 05-Templates/     → Obsidian templates
```

**When to use**: Living documentation, research notes, decision records, pattern library.

### Project Management (`project-docs/`)
**Purpose**: Project planning and management  
**Contains**:
- `Implementation_Cadence.md` - Development phases
- `Program_Requirements.md` - Full requirements
- `Roadmap.md` - Future planning
- `Architecture_Decisions.md` - Major decisions

**When to use**: Project-level planning, requirements, roadmaps.

### Templates (`templates/`)
**Purpose**: Reusable document and code templates  
**Contains**:
- Session planning templates
- Analysis templates
- Code templates
- Documentation templates

**When to use**: Any reusable template for consistency.

## 🎯 Decision Tree: Where to Put New Documentation

```
Is it essential project info (README, LICENSE)?
  └─ Yes → Root directory
  └─ No → Continue...

Is it for AI development sessions?
  └─ Yes → .claude/
  └─ No → Continue...

Is it public-facing documentation?
  └─ Yes → docs/ (choose appropriate subdirectory)
  └─ No → Continue...

Is it a living note, pattern, or research?
  └─ Yes → vault/ (choose appropriate subdirectory)
  └─ No → Continue...

Is it project planning/management?
  └─ Yes → project-docs/
  └─ No → Continue...

Is it a reusable template?
  └─ Yes → templates/
  └─ No → Reconsider the document's purpose
```

## 📝 Document Naming Conventions

### General Rules
1. **Use descriptive names**: `Safety-Validation-Guide.md` not `guide.md`
2. **Use hyphens**: `Session-Analysis.md` not `Session Analysis.md`
3. **Be consistent**: Match existing patterns in the directory

### Specific Conventions
- **Sessions**: `Session-X.Y-Title.md`
- **Patterns**: `Pattern-Name.md`
- **Guides**: `Topic-Guide.md`
- **Templates**: `template-purpose.md`

## 🔄 Document Lifecycle

### Creation
1. Determine correct location (use decision tree)
2. Follow naming conventions
3. Use appropriate template if available
4. Add to relevant index/contents file

### Maintenance
1. Review quarterly for accuracy
2. Move if purpose changes
3. Archive if obsolete (to `vault/99-Archive/`)
4. Update references when moving

### Cross-References
When referencing documents from other locations:
```markdown
<!-- From docs/ to .claude/ -->
See [CLAUDE.md](../.claude/CLAUDE.md) for AI context

<!-- From .claude/ to project-docs/ -->
See [Implementation_Cadence.md](../project-docs/Implementation_Cadence.md)

<!-- Always use relative paths -->
```

## 🚀 Quick Reference

| Document Type | Location | Example |
|--------------|----------|---------|
| Project intro | `/` | README.md |
| AI session info | `.claude/` | NEXT_SESSION.md |
| User guides | `docs/` | docs/development/setup.md |
| Code patterns | `vault/01-Patterns/` | Abstraction-Pattern.md |
| Project plans | `project-docs/` | Roadmap.md |
| Reusable formats | `templates/` | session-template.md |

## 🎓 Best Practices

1. **Don't duplicate**: If similar content exists, link don't copy
2. **Keep it focused**: Each document should have one clear purpose
3. **Update paths**: When moving files, update all references
4. **Use templates**: Consistency helps discovery
5. **Document decisions**: Use vault/03-Decisions/ for ADRs

## 📊 Metrics for Success

Good documentation organization results in:
- ✅ New contributors find information quickly
- ✅ No duplicate content across directories
- ✅ Clear purpose for each location
- ✅ Easy to determine where new docs go
- ✅ Consistent structure as project grows

---

*This guide is the source of truth for documentation organization. When in doubt, refer here.*