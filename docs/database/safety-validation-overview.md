# Safety Validation Overview

## Core Principle
Every piece of data entering the database must have concrete references abstracted with placeholders.

## Key Components

### 1. Database Layer (PostgreSQL)
- **Migrations 002-010**: Comprehensive safety enforcement
- **Validation Functions**: `safety.validate_*` functions for all content types
- **Triggers**: Automatic validation before any insert/update
- **Minimum Safety Score**: 0.8 required for all validated content

### 2. Python Layer
- **AbstractMemoryEntry**: Core model with mandatory validation
- **SafeInteraction**: Links to validated memories only
- **MemoryValidator**: Detects and abstracts concrete references
- **SafeMemoryRepository**: Database operations with built-in validation

## Validation Pipeline
1. Content enters system
2. Concrete references detected (paths, IPs, credentials, etc.)
3. Automatic abstraction with placeholders (`<file_path>`, `<ip_address>`)
4. Safety score calculation
5. Storage only if score >= 0.8

## Testing
Run comprehensive test suite:
```bash
psql -U ccp_user -d cognitive_coding_partner -f scripts/database/test-abstraction-enforcement.sql
```

## Key Tables
- `safety.memory_abstractions`: Core abstracted content
- `public.cognitive_memory`: Validated memories only
- `safety.quarantine`: Failed content for review

All concrete references are automatically rejected at the database level.