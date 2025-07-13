"""
Data models for vault synchronization system.

Defines all data structures for memory-to-markdown conversion,
template processing, and conflict resolution with safety validation.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class ConflictStrategy(Enum):
    """Strategy for handling sync conflicts."""
    MEMORY_WINS = "memory_wins"        # Memory content takes precedence
    VAULT_WINS = "vault_wins"          # Vault content takes precedence  
    SAFE_MERGE = "safe_merge"          # Attempt safe merge with validation
    USER_PROMPT = "user_prompt"        # Prompt user for resolution
    SKIP_CONFLICTED = "skip_conflicted" # Skip conflicted items


class TemplateType(Enum):
    """Types of note templates available."""
    CHECKPOINT = "checkpoint"          # Memory snapshot template
    LEARNING = "learning"             # Knowledge capture template
    DECISION = "decision"             # Decision tracking template
    CUSTOM = "custom"                 # User-defined template


class SyncDirection(Enum):
    """Direction of synchronization."""
    MEMORY_TO_VAULT = "memory_to_vault"
    VAULT_TO_MEMORY = "vault_to_memory"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class VaultSyncConfig:
    """Configuration for vault synchronization."""
    vault_path: Path
    enable_backlinks: bool = True
    enable_templates: bool = True
    template_directory: Optional[Path] = None
    conflict_strategy: ConflictStrategy = ConflictStrategy.SAFE_MERGE
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    max_note_size_kb: int = 100
    enable_tag_extraction: bool = True
    enable_frontmatter: bool = True
    safety_score_threshold: Decimal = Decimal("0.8")
    batch_size: int = 50
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.vault_path.exists():
            self.vault_path.mkdir(parents=True, exist_ok=True)
        
        if self.template_directory and not self.template_directory.exists():
            self.template_directory.mkdir(parents=True, exist_ok=True)


@dataclass
class VaultMetadata:
    """Metadata for vault synchronization tracking."""
    last_sync_timestamp: datetime
    memory_count: int
    notes_created: int
    notes_updated: int
    conflicts_detected: int
    safety_violations: int
    average_safety_score: Decimal
    sync_duration_ms: int
    
    @classmethod
    def create_empty(cls) -> 'VaultMetadata':
        """Create empty metadata instance."""
        return cls(
            last_sync_timestamp=datetime.now(),
            memory_count=0,
            notes_created=0,
            notes_updated=0,
            conflicts_detected=0,
            safety_violations=0,
            average_safety_score=Decimal("1.0"),
            sync_duration_ms=0
        )


@dataclass
class MarkdownNote:
    """Represents a markdown note with abstracted content."""
    title_pattern: str                    # Abstracted note title
    content: str                         # Abstracted markdown content
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    backlinks: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    template_type: Optional[TemplateType] = None
    safety_score: Decimal = Decimal("1.0")
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    memory_id: Optional[UUID] = None
    file_path: Optional[Path] = None
    
    def get_filename(self) -> str:
        """Generate safe filename from title pattern."""
        # Replace unsafe characters for filesystem
        safe_title = self.title_pattern.replace('<', '').replace('>', '')
        safe_title = safe_title.replace('/', '_').replace('\\', '_')
        safe_title = safe_title.replace('|', '_').replace(':', '_')
        safe_title = safe_title.replace('*', '_').replace('?', '_')
        safe_title = safe_title.replace('"', '_').replace('&', '_')
        
        # Limit length and add timestamp for uniqueness
        timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
        safe_title = safe_title[:50]  # Limit length
        
        return f"{timestamp}_{safe_title}.md"
    
    def get_full_markdown(self) -> str:
        """Generate complete markdown with frontmatter."""
        lines = []
        
        # Add frontmatter if enabled
        if self.frontmatter:
            lines.append("---")
            for key, value in self.frontmatter.items():
                if isinstance(value, list):
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
                elif isinstance(value, datetime):
                    lines.append(f"{key}: {value.isoformat()}")
                else:
                    lines.append(f"{key}: {value}")
            lines.append("---")
            lines.append("")
        
        # Add title
        lines.append(f"# {self.title_pattern}")
        lines.append("")
        
        # Add tags if present
        if self.tags:
            tag_line = " ".join([f"#{tag}" for tag in sorted(self.tags)])
            lines.append(f"Tags: {tag_line}")
            lines.append("")
        
        # Add main content
        lines.append(self.content)
        
        # Add backlinks if present
        if self.backlinks:
            lines.append("")
            lines.append("## Related Notes")
            lines.append("")
            for backlink in self.backlinks:
                lines.append(f"- [[{backlink}]]")
        
        return "\n".join(lines)
    
    def is_safe_for_export(self) -> bool:
        """Check if note is safe for vault export."""
        return self.safety_score >= Decimal("0.8")
    
    def get_content_hash(self) -> str:
        """Generate hash of content for change detection."""
        import hashlib
        content_for_hash = f"{self.title_pattern}{self.content}{sorted(self.tags)}"
        return hashlib.sha256(content_for_hash.encode()).hexdigest()[:16]


@dataclass
class SyncResult:
    """Result of vault synchronization operation."""
    success: bool
    notes_processed: int = 0
    notes_created: int = 0
    notes_updated: int = 0
    notes_skipped: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    safety_violations: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    average_safety_score: Decimal = Decimal("1.0")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of sync operation."""
        if self.notes_processed == 0:
            return 1.0
        return (self.notes_created + self.notes_updated) / self.notes_processed
    
    @property
    def conflict_rate(self) -> float:
        """Calculate conflict rate."""
        if self.notes_processed == 0:
            return 0.0
        return self.conflicts_detected / self.notes_processed
    
    def add_error(self, error: str) -> None:
        """Add error message to result."""
        self.errors.append(error)
        if self.success and len(self.errors) > 0:
            self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add warning message to result."""
        self.warnings.append(warning)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            'success': self.success,
            'success_rate': self.success_rate,
            'conflict_rate': self.conflict_rate,
            'notes_processed': self.notes_processed,
            'notes_created': self.notes_created,
            'notes_updated': self.notes_updated,
            'conflicts_detected': self.conflicts_detected,
            'safety_violations': self.safety_violations,
            'processing_time_ms': self.processing_time_ms,
            'average_safety_score': float(self.average_safety_score),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


@dataclass
class ConflictInfo:
    """Information about a synchronization conflict."""
    conflict_id: UUID = field(default_factory=uuid4)
    memory_id: UUID = None
    vault_file_path: Path = None
    conflict_type: str = "content_mismatch"
    memory_content: str = ""
    vault_content: str = ""
    memory_updated_at: datetime = None
    vault_updated_at: datetime = None
    resolution_strategy: Optional[ConflictStrategy] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_note: str = ""
    
    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of conflict for analysis."""
        return {
            'conflict_id': str(self.conflict_id),
            'conflict_type': self.conflict_type,
            'memory_newer': self.memory_updated_at > self.vault_updated_at if both_dates_exist(self.memory_updated_at, self.vault_updated_at) else None,
            'content_size_diff': len(self.memory_content) - len(self.vault_content),
            'resolved': self.resolved,
            'resolution_strategy': self.resolution_strategy.value if self.resolution_strategy else None
        }


@dataclass
class TemplateVariable:
    """Represents a template variable with safety constraints."""
    name: str
    value: Any
    is_safe: bool = True
    pattern_type: str = "generic"
    
    def get_safe_value(self) -> str:
        """Get safely abstracted value for template substitution."""
        if not self.is_safe:
            return f"<{self.pattern_type}>"
        
        # Convert value to safe string representation
        if isinstance(self.value, (str, int, float, bool)):
            return str(self.value)
        elif isinstance(self.value, datetime):
            return self.value.isoformat()
        elif isinstance(self.value, (list, tuple)):
            return ", ".join([str(item) for item in self.value])
        else:
            return f"<{type(self.value).__name__.lower()}>"


@dataclass
class BacklinkInfo:
    """Information about backlinks between notes."""
    source_pattern: str
    target_pattern: str
    link_type: str = "related"
    strength: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_markdown_link(self) -> str:
        """Generate markdown link format."""
        return f"[[{self.target_pattern}]]"


def both_dates_exist(date1: Optional[datetime], date2: Optional[datetime]) -> bool:
    """Helper function to check if both dates exist."""
    return date1 is not None and date2 is not None


# Performance tracking
@dataclass
class PerformanceMetrics:
    """Performance metrics for vault operations."""
    conversion_time_ms: float = 0.0
    template_processing_time_ms: float = 0.0
    conflict_detection_time_ms: float = 0.0
    backlink_resolution_time_ms: float = 0.0
    total_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    
    def meets_targets(self) -> bool:
        """Check if performance meets targets."""
        return (
            self.conversion_time_ms < 500 and
            self.template_processing_time_ms < 200 and
            self.conflict_detection_time_ms < 300 and
            self.backlink_resolution_time_ms < 100
        )