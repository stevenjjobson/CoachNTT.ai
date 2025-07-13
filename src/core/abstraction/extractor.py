"""
ReferenceExtractor: Identifies concrete references in code and text.
Uses pattern matching and heuristics to detect references that need abstraction.
"""
import re
import logging
from typing import Dict, List, Optional, Pattern, Any
from dataclasses import dataclass

from src.core.safety.models import Reference, ReferenceType


logger = logging.getLogger(__name__)


@dataclass
class ExtractionPattern:
    """A pattern for extracting references."""
    name: str
    pattern: Pattern
    reference_type: ReferenceType
    confidence: float = 1.0
    context_window: int = 50  # characters before/after for context


class ReferenceExtractor:
    """
    Extracts concrete references from content using pattern matching.
    This is a critical component for safety - it must catch all concrete references.
    """
    
    def __init__(self):
        """Initialize the reference extractor with detection patterns."""
        self.patterns = self._initialize_patterns()
        self.custom_patterns: List[ExtractionPattern] = []
        logger.info(f"Initialized ReferenceExtractor with {len(self.patterns)} patterns")
    
    def _initialize_patterns(self) -> Dict[str, List[ExtractionPattern]]:
        """Initialize the detection patterns for different reference types."""
        patterns = {
            'file_paths': self._get_file_path_patterns(),
            'identifiers': self._get_identifier_patterns(),
            'urls': self._get_url_patterns(),
            'network': self._get_network_patterns(),
            'containers': self._get_container_patterns(),
            'config': self._get_config_patterns(),
            'temporal': self._get_temporal_patterns(),
            'secrets': self._get_secret_patterns(),
        }
        return patterns
    
    def _get_file_path_patterns(self) -> List[ExtractionPattern]:
        """Patterns for detecting file paths."""
        return [
            # Unix absolute paths
            ExtractionPattern(
                name="unix_absolute",
                pattern=re.compile(r'\b/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\b'),
                reference_type=ReferenceType.FILE_PATH,
                confidence=0.9
            ),
            # Windows absolute paths
            ExtractionPattern(
                name="windows_absolute",
                pattern=re.compile(r'\b[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]+\b'),
                reference_type=ReferenceType.FILE_PATH,
                confidence=0.95
            ),
            # Home directory paths
            ExtractionPattern(
                name="home_directory",
                pattern=re.compile(r'~[/\\][^\s\'"<>|]+'),
                reference_type=ReferenceType.FILE_PATH,
                confidence=1.0
            ),
            # Relative paths with explicit ./ or ../
            ExtractionPattern(
                name="relative_explicit",
                pattern=re.compile(r'\.{1,2}[/\\][^\s\'"<>|]+'),
                reference_type=ReferenceType.FILE_PATH,
                confidence=0.8
            ),
        ]
    
    def _get_identifier_patterns(self) -> List[ExtractionPattern]:
        """Patterns for detecting identifiers."""
        return [
            # Numeric IDs in assignments or comparisons
            ExtractionPattern(
                name="numeric_id_assignment",
                pattern=re.compile(r'\b(?:id|ID|Id)\s*[=:]\s*(\d+)\b'),
                reference_type=ReferenceType.IDENTIFIER,
                confidence=0.95
            ),
            # UUIDs
            ExtractionPattern(
                name="uuid",
                pattern=re.compile(
                    r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
                ),
                reference_type=ReferenceType.IDENTIFIER,
                confidence=1.0
            ),
            # Numeric IDs in common patterns
            ExtractionPattern(
                name="numeric_id_patterns",
                pattern=re.compile(
                    r'\b(?:user_id|order_id|product_id|customer_id|session_id|transaction_id)'
                    r'\s*[=:]\s*["\']?(\d+)["\']?\b'
                ),
                reference_type=ReferenceType.IDENTIFIER,
                confidence=0.9
            ),
            # Database primary keys
            ExtractionPattern(
                name="db_primary_key",
                pattern=re.compile(r'WHERE\s+id\s*=\s*(\d+)', re.IGNORECASE),
                reference_type=ReferenceType.IDENTIFIER,
                confidence=0.85
            ),
        ]
    
    def _get_url_patterns(self) -> List[ExtractionPattern]:
        """Patterns for detecting URLs."""
        return [
            # HTTP/HTTPS URLs
            ExtractionPattern(
                name="http_url",
                pattern=re.compile(
                    r'https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+'
                ),
                reference_type=ReferenceType.URL,
                confidence=1.0
            ),
            # Database connection strings
            ExtractionPattern(
                name="database_url",
                pattern=re.compile(
                    r'(?:postgresql|mysql|mongodb|redis)://[^\s\'"<>]+'
                ),
                reference_type=ReferenceType.URL,
                confidence=1.0
            ),
            # File URLs
            ExtractionPattern(
                name="file_url",
                pattern=re.compile(r'file://[^\s\'"<>]+'),
                reference_type=ReferenceType.URL,
                confidence=1.0
            ),
        ]
    
    def _get_network_patterns(self) -> List[ExtractionPattern]:
        """Patterns for network-related references."""
        return [
            # IPv4 addresses
            ExtractionPattern(
                name="ipv4",
                pattern=re.compile(
                    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
                    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
                ),
                reference_type=ReferenceType.IP_ADDRESS,
                confidence=0.9
            ),
            # IPv6 addresses (simplified pattern)
            ExtractionPattern(
                name="ipv6",
                pattern=re.compile(
                    r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
                ),
                reference_type=ReferenceType.IP_ADDRESS,
                confidence=0.9
            ),
            # Port numbers with context
            ExtractionPattern(
                name="port_with_colon",
                pattern=re.compile(r'(?:localhost|0\.0\.0\.0|127\.0\.0\.1):(\d{1,5})\b'),
                reference_type=ReferenceType.CONFIG_VALUE,
                confidence=0.8
            ),
        ]
    
    def _get_container_patterns(self) -> List[ExtractionPattern]:
        """Patterns for container-related references."""
        return [
            # Docker container names
            ExtractionPattern(
                name="docker_container",
                pattern=re.compile(
                    r'(?:container_name|--name)\s*[=:]\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]*)["\']?'
                ),
                reference_type=ReferenceType.CONTAINER,
                confidence=0.9
            ),
            # Docker image tags
            ExtractionPattern(
                name="docker_image",
                pattern=re.compile(
                    r'\b[a-zA-Z0-9][a-zA-Z0-9_\-\.]*(?:/[a-zA-Z0-9_\-\.]+)*:[a-zA-Z0-9_\-\.]+\b'
                ),
                reference_type=ReferenceType.CONTAINER,
                confidence=0.85
            ),
            # Container IDs (12-char hex)
            ExtractionPattern(
                name="container_id",
                pattern=re.compile(r'\b[0-9a-f]{12}\b'),
                reference_type=ReferenceType.CONTAINER,
                confidence=0.7
            ),
        ]
    
    def _get_config_patterns(self) -> List[ExtractionPattern]:
        """Patterns for configuration values."""
        return [
            # Environment variables with values
            ExtractionPattern(
                name="env_var_assignment",
                pattern=re.compile(
                    r'\b[A-Z][A-Z0-9_]*\s*=\s*["\']?([^"\'\s]+)["\']?'
                ),
                reference_type=ReferenceType.CONFIG_VALUE,
                confidence=0.7
            ),
            # Configuration keys with specific values
            ExtractionPattern(
                name="config_assignment",
                pattern=re.compile(
                    r'(?:host|port|database|username|server)\s*[=:]\s*["\']?([^"\'\s,}]+)["\']?',
                    re.IGNORECASE
                ),
                reference_type=ReferenceType.CONFIG_VALUE,
                confidence=0.8
            ),
        ]
    
    def _get_temporal_patterns(self) -> List[ExtractionPattern]:
        """Patterns for temporal references."""
        return [
            # ISO 8601 timestamps
            ExtractionPattern(
                name="iso_timestamp",
                pattern=re.compile(
                    r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b'
                ),
                reference_type=ReferenceType.TIMESTAMP,
                confidence=1.0
            ),
            # Unix timestamps (10-digit numbers in specific contexts)
            ExtractionPattern(
                name="unix_timestamp",
                pattern=re.compile(
                    r'(?:timestamp|expires?|created_at|updated_at)\s*[=:]\s*(\d{10})\b',
                    re.IGNORECASE
                ),
                reference_type=ReferenceType.TIMESTAMP,
                confidence=0.9
            ),
        ]
    
    def _get_secret_patterns(self) -> List[ExtractionPattern]:
        """Patterns for secrets and tokens."""
        return [
            # API keys
            ExtractionPattern(
                name="api_key",
                pattern=re.compile(
                    r'(?:api[_\-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
                    re.IGNORECASE
                ),
                reference_type=ReferenceType.TOKEN,
                confidence=0.95
            ),
            # JWT tokens
            ExtractionPattern(
                name="jwt_token",
                pattern=re.compile(
                    r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'
                ),
                reference_type=ReferenceType.TOKEN,
                confidence=1.0
            ),
            # Generic secrets
            ExtractionPattern(
                name="secret",
                pattern=re.compile(
                    r'(?:secret|password|token)\s*[=:]\s*["\']?([^\s"\']{8,})["\']?',
                    re.IGNORECASE
                ),
                reference_type=ReferenceType.TOKEN,
                confidence=0.8
            ),
        ]
    
    def extract_references(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Reference]:
        """
        Extract all concrete references from content.
        
        Args:
            content: The content to analyze
            context: Additional context for extraction
            
        Returns:
            List of detected references
        """
        references = []
        context = context or {}
        
        # Apply all pattern categories
        for category, patterns in self.patterns.items():
            category_refs = self._apply_patterns(content, patterns, category)
            references.extend(category_refs)
        
        # Apply custom patterns if any
        if self.custom_patterns:
            custom_refs = self._apply_patterns(content, self.custom_patterns, "custom")
            references.extend(custom_refs)
        
        # Remove duplicates and overlapping references
        references = self._deduplicate_references(references)
        
        # Sort by position
        references.sort(key=lambda r: r.position[0])
        
        logger.info(f"Extracted {len(references)} references from content")
        return references
    
    def _apply_patterns(
        self, content: str, patterns: List[ExtractionPattern], category: str
    ) -> List[Reference]:
        """Apply a list of patterns to content."""
        references = []
        
        for pattern in patterns:
            matches = pattern.pattern.finditer(content)
            for match in matches:
                # Get the matched value (whole match or first group)
                value = match.group(1) if match.groups() else match.group(0)
                
                # Get context around the match
                start, end = match.span()
                context_start = max(0, start - pattern.context_window)
                context_end = min(len(content), end + pattern.context_window)
                context_text = content[context_start:context_end]
                
                reference = Reference(
                    type=pattern.reference_type,
                    value=value,
                    position=(start, end),
                    context=context_text,
                    confidence=pattern.confidence,
                    detection_rule=f"{category}.{pattern.name}"
                )
                references.append(reference)
        
        return references
    
    def _deduplicate_references(self, references: List[Reference]) -> List[Reference]:
        """Remove duplicate and overlapping references."""
        if not references:
            return []
        
        # Sort by start position and confidence (higher confidence first)
        sorted_refs = sorted(
            references,
            key=lambda r: (r.position[0], -r.confidence)
        )
        
        deduped = []
        last_end = -1
        
        for ref in sorted_refs:
            start, end = ref.position
            # Skip if this reference overlaps with a previous one
            if start >= last_end:
                deduped.append(ref)
                last_end = end
            else:
                logger.debug(
                    f"Skipping overlapping reference: {ref.value} at {ref.position}"
                )
        
        return deduped
    
    def add_custom_pattern(
        self,
        name: str,
        pattern: str,
        reference_type: ReferenceType,
        confidence: float = 0.8
    ) -> None:
        """
        Add a custom extraction pattern.
        
        Args:
            name: Name for the pattern
            pattern: Regular expression pattern
            reference_type: Type of reference this pattern detects
            confidence: Confidence level for matches
        """
        try:
            compiled_pattern = re.compile(pattern)
            extraction_pattern = ExtractionPattern(
                name=f"custom_{name}",
                pattern=compiled_pattern,
                reference_type=reference_type,
                confidence=confidence
            )
            self.custom_patterns.append(extraction_pattern)
            logger.info(f"Added custom pattern: {name}")
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def get_pattern_stats(self) -> Dict[str, int]:
        """Get statistics about loaded patterns."""
        stats = {}
        for category, patterns in self.patterns.items():
            stats[category] = len(patterns)
        stats['custom'] = len(self.custom_patterns)
        stats['total'] = sum(stats.values())
        return stats