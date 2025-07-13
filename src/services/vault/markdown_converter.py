"""
Memory-to-markdown conversion service with safety validation.

Converts abstracted memories to markdown format with frontmatter generation,
tag extraction, and AST analysis integration for code content.
"""

import logging
import time
import re
from typing import Dict, List, Optional, Any, Set
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from .models import MarkdownNote, TemplateType
from ...core.memory.abstract_models import AbstractMemoryEntry, InteractionType
from ...core.validation.validator import SafetyValidator
from ...core.analysis.ast_analyzer import ASTAnalyzer
from ...core.analysis.models import LanguageType

logger = logging.getLogger(__name__)


class MarkdownConverter:
    """
    Converts abstracted memories to markdown format with safety validation.
    
    Provides memory-to-markdown conversion with frontmatter generation,
    tag extraction, and optional AST analysis for code content.
    """
    
    def __init__(
        self,
        safety_validator: SafetyValidator,
        ast_analyzer: Optional[ASTAnalyzer] = None,
        enable_code_analysis: bool = True
    ):
        """
        Initialize markdown converter.
        
        Args:
            safety_validator: Safety validator for content abstraction
            ast_analyzer: AST analyzer for code content enhancement
            enable_code_analysis: Whether to enable code analysis features
        """
        self.safety_validator = safety_validator
        self.ast_analyzer = ast_analyzer
        self.enable_code_analysis = enable_code_analysis
        
        # Statistics
        self._stats = {
            'conversions_performed': 0,
            'code_analyses_performed': 0,
            'safety_validations_passed': 0,
            'safety_validations_failed': 0,
            'total_processing_time_ms': 0,
            'tags_extracted': 0,
            'frontmatter_generated': 0
        }
        
        logger.info("MarkdownConverter initialized")
    
    async def convert_memory_to_markdown(
        self,
        memory: AbstractMemoryEntry,
        template_type: Optional[TemplateType] = None,
        enable_backlinks: bool = True,
        enable_tags: bool = True,
        enable_frontmatter: bool = True
    ) -> Optional[MarkdownNote]:
        """
        Convert memory entry to markdown note.
        
        Args:
            memory: Memory entry to convert
            template_type: Template type for note structure
            enable_backlinks: Whether to generate backlinks
            enable_tags: Whether to extract tags
            enable_frontmatter: Whether to generate frontmatter
            
        Returns:
            Converted markdown note or None if conversion fails
        """
        start_time = time.time()
        
        try:
            # Step 1: Safety validation
            if not await self._validate_memory_safety(memory):
                self._stats['safety_validations_failed'] += 1
                logger.warning(f"Memory {memory.id} failed safety validation")
                return None
            
            self._stats['safety_validations_passed'] += 1
            
            # Step 2: Generate abstracted title
            title_pattern = await self._generate_title_pattern(memory)
            
            # Step 3: Convert content with abstraction
            content = await self._convert_content(memory)
            
            # Step 4: Create base note
            note = MarkdownNote(
                title_pattern=title_pattern,
                content=content,
                template_type=template_type,
                safety_score=memory.metadata.safety_score,
                memory_id=memory.id,
                created_at=memory.created_at,
                updated_at=memory.updated_at
            )
            
            # Step 5: Generate frontmatter if enabled
            if enable_frontmatter:
                note.frontmatter = await self._generate_frontmatter(memory, note)
                self._stats['frontmatter_generated'] += 1
            
            # Step 6: Extract tags if enabled
            if enable_tags:
                note.tags = await self._extract_tags(memory, note)
                self._stats['tags_extracted'] += len(note.tags)
            
            # Step 7: Enhance with code analysis if applicable
            if (self.enable_code_analysis and 
                self.ast_analyzer and 
                await self._is_code_content(memory)):
                
                await self._enhance_with_code_analysis(memory, note)
                self._stats['code_analyses_performed'] += 1
            
            # Step 8: Final safety validation
            final_safety_score = await self._calculate_note_safety_score(note)
            note.safety_score = final_safety_score
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self._stats['conversions_performed'] += 1
            self._stats['total_processing_time_ms'] += processing_time
            
            logger.debug(
                f"Converted memory {memory.id} to note in {processing_time:.1f}ms "
                f"(safety: {note.safety_score:.3f})"
            )
            
            return note
            
        except Exception as e:
            logger.error(f"Memory conversion failed for {memory.id}: {e}")
            return None
    
    async def _validate_memory_safety(self, memory: AbstractMemoryEntry) -> bool:
        """Validate memory meets safety requirements."""
        try:
            # Check safety score
            if memory.metadata.safety_score < Decimal("0.8"):
                return False
            
            # Validate abstracted content
            abstracted_content, concrete_refs = self.safety_validator.auto_abstract_content(
                memory.content
            )
            
            # Should have minimal concrete references
            return len(concrete_refs) == 0
            
        except Exception as e:
            logger.error(f"Safety validation failed for memory {memory.id}: {e}")
            return False
    
    async def _generate_title_pattern(self, memory: AbstractMemoryEntry) -> str:
        """Generate abstracted title pattern for note."""
        try:
            # Use interaction type and metadata to create meaningful title
            interaction_type = memory.interaction_type.value.lower()
            
            # Extract first meaningful words from content for title
            content_words = memory.content.strip().split()[:5]
            content_preview = ' '.join(content_words) if content_words else "content"
            
            # Abstract the preview
            abstracted_preview, _ = self.safety_validator.auto_abstract_content(content_preview)
            
            # Create title pattern based on interaction type
            if memory.interaction_type == InteractionType.QUESTION:
                title_pattern = f"<question_{abstracted_preview.replace(' ', '_').lower()}>"
            elif memory.interaction_type == InteractionType.CODE_ANALYSIS:
                title_pattern = f"<code_analysis_{abstracted_preview.replace(' ', '_').lower()}>"
            elif memory.interaction_type == InteractionType.DOCUMENTATION:
                title_pattern = f"<documentation_{abstracted_preview.replace(' ', '_').lower()}>"
            else:
                title_pattern = f"<{interaction_type}_{abstracted_preview.replace(' ', '_').lower()}>"
            
            # Ensure safe length
            if len(title_pattern) > 80:
                title_pattern = title_pattern[:80] + ">"
            
            return title_pattern
            
        except Exception as e:
            logger.error(f"Title generation failed for memory {memory.id}: {e}")
            return f"<memory_{memory.id.hex[:8]}>"
    
    async def _convert_content(self, memory: AbstractMemoryEntry) -> str:
        """Convert memory content to markdown with abstraction."""
        try:
            # Start with abstracted content
            content = memory.content
            
            # Apply additional markdown formatting based on interaction type
            if memory.interaction_type == InteractionType.CODE_ANALYSIS:
                content = await self._format_code_content(content)
            elif memory.interaction_type == InteractionType.QUESTION:
                content = await self._format_question_content(content)
            elif memory.interaction_type == InteractionType.DOCUMENTATION:
                content = await self._format_documentation_content(content)
            
            # Ensure all concrete references are abstracted
            abstracted_content, _ = self.safety_validator.auto_abstract_content(content)
            
            return abstracted_content
            
        except Exception as e:
            logger.error(f"Content conversion failed for memory {memory.id}: {e}")
            return memory.content
    
    async def _format_code_content(self, content: str) -> str:
        """Format code-related content with proper markdown."""
        # Add code block formatting for code snippets
        lines = content.split('\n')
        formatted_lines = []
        in_code_block = False
        
        for line in lines:
            # Simple heuristic for code detection
            if (line.strip().startswith(('def ', 'class ', 'import ', 'from ')) or
                line.strip().endswith((':')) and not line.strip().startswith('#')):
                
                if not in_code_block:
                    formatted_lines.append('```python')
                    in_code_block = True
                formatted_lines.append(line)
            else:
                if in_code_block:
                    formatted_lines.append('```')
                    in_code_block = False
                formatted_lines.append(line)
        
        if in_code_block:
            formatted_lines.append('```')
        
        return '\n'.join(formatted_lines)
    
    async def _format_question_content(self, content: str) -> str:
        """Format question content with proper structure."""
        # Add question formatting
        if not content.strip().startswith('**Question:**'):
            content = f"**Question:** {content}"
        
        return content
    
    async def _format_documentation_content(self, content: str) -> str:
        """Format documentation content with headers."""
        # Add documentation structure
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip() and not line.startswith('#') and len(line.strip()) > 50:
                # Potential header
                formatted_lines.append(f"## {line.strip()}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    async def _generate_frontmatter(
        self,
        memory: AbstractMemoryEntry,
        note: MarkdownNote
    ) -> Dict[str, Any]:
        """Generate YAML frontmatter for note."""
        try:
            frontmatter = {
                'type': memory.interaction_type.value.lower(),
                'created': memory.created_at.isoformat(),
                'updated': memory.updated_at.isoformat(),
                'safety_score': float(memory.metadata.safety_score),
                'memory_weight': float(memory.weight),
                'cluster_id': str(memory.cluster_id) if memory.cluster_id else None
            }
            
            # Add template information
            if note.template_type:
                frontmatter['template'] = note.template_type.value
            
            # Add abstracted metadata
            if hasattr(memory.metadata, 'context') and memory.metadata.context:
                # Abstract any concrete references in context
                abstracted_context = {}
                for key, value in memory.metadata.context.items():
                    if isinstance(value, str):
                        abs_value, _ = self.safety_validator.auto_abstract_content(value)
                        abstracted_context[key] = abs_value
                    else:
                        abstracted_context[key] = value
                
                frontmatter['context'] = abstracted_context
            
            return frontmatter
            
        except Exception as e:
            logger.error(f"Frontmatter generation failed for memory {memory.id}: {e}")
            return {}
    
    async def _extract_tags(
        self,
        memory: AbstractMemoryEntry,
        note: MarkdownNote
    ) -> Set[str]:
        """Extract tags from memory content and metadata."""
        tags = set()
        
        try:
            # Tag from interaction type
            tags.add(memory.interaction_type.value.lower())
            
            # Extract tags from content using patterns
            content_lower = memory.content.lower()
            
            # Common tag patterns
            tag_patterns = [
                r'#(\w+)',           # Hashtags
                r'@(\w+)',           # At mentions
                r'\btag:(\w+)',      # Explicit tags
                r'\btopic:(\w+)',    # Topic tags
            ]
            
            for pattern in tag_patterns:
                matches = re.findall(pattern, content_lower)
                for match in matches:
                    if len(match) > 2:  # Avoid short tags
                        tags.add(match)
            
            # Add semantic tags based on content
            semantic_tags = await self._extract_semantic_tags(memory.content)
            tags.update(semantic_tags)
            
            # Abstract tag names for safety
            safe_tags = set()
            for tag in tags:
                if len(tag) > 15:  # Potentially concrete
                    abstracted_tag, _ = self.safety_validator.auto_abstract_content(tag)
                    safe_tags.add(abstracted_tag.replace('<', '').replace('>', ''))
                else:
                    safe_tags.add(tag)
            
            return safe_tags
            
        except Exception as e:
            logger.error(f"Tag extraction failed for memory {memory.id}: {e}")
            return set()
    
    async def _extract_semantic_tags(self, content: str) -> Set[str]:
        """Extract semantic tags based on content analysis."""
        tags = set()
        
        # Programming language detection
        if any(keyword in content.lower() for keyword in ['def ', 'class ', 'import ']):
            tags.add('python')
        
        if any(keyword in content.lower() for keyword in ['function ', 'const ', 'let ']):
            tags.add('javascript')
        
        if any(keyword in content.lower() for keyword in ['interface ', 'type ', 'enum ']):
            tags.add('typescript')
        
        # Domain-specific tags
        if any(keyword in content.lower() for keyword in ['database', 'sql', 'query']):
            tags.add('database')
        
        if any(keyword in content.lower() for keyword in ['api', 'endpoint', 'rest']):
            tags.add('api')
        
        if any(keyword in content.lower() for keyword in ['test', 'unittest', 'pytest']):
            tags.add('testing')
        
        return tags
    
    async def _is_code_content(self, memory: AbstractMemoryEntry) -> bool:
        """Determine if memory contains code content."""
        if memory.interaction_type == InteractionType.CODE_ANALYSIS:
            return True
        
        # Check for code patterns in content
        code_indicators = [
            'def ', 'class ', 'import ', 'from ',
            'function ', 'const ', 'let ', 'var ',
            'interface ', 'type ', 'enum ',
            '{', '}', '(', ')', ';'
        ]
        
        content_lower = memory.content.lower()
        code_count = sum(1 for indicator in code_indicators if indicator in content_lower)
        
        return code_count >= 3  # Threshold for code content
    
    async def _enhance_with_code_analysis(
        self,
        memory: AbstractMemoryEntry,
        note: MarkdownNote
    ) -> None:
        """Enhance note with AST analysis insights."""
        try:
            if not self.ast_analyzer:
                return
            
            # Perform AST analysis
            analysis_result = await self.ast_analyzer.analyze_code(
                content=memory.content,
                filename=None
            )
            
            # Add analysis insights to content
            insights = []
            
            if analysis_result.language:
                insights.append(f"**Language:** {analysis_result.language.value}")
            
            if analysis_result.functions:
                insights.append(f"**Functions:** {len(analysis_result.functions)}")
            
            if analysis_result.classes:
                insights.append(f"**Classes:** {len(analysis_result.classes)}")
            
            if analysis_result.design_patterns:
                patterns = [p.pattern_type.value for p in analysis_result.design_patterns]
                insights.append(f"**Patterns:** {', '.join(patterns)}")
            
            if analysis_result.complexity_metrics:
                complexity = analysis_result.complexity_metrics.cyclomatic_complexity
                insights.append(f"**Complexity:** {complexity}")
            
            # Add insights to note content
            if insights:
                analysis_section = "\n\n## Code Analysis\n\n" + "\n".join(insights)
                note.content += analysis_section
            
            # Add code analysis tags
            if analysis_result.language:
                note.tags.add(analysis_result.language.value.lower())
            
            if analysis_result.design_patterns:
                for pattern in analysis_result.design_patterns:
                    note.tags.add(f"pattern_{pattern.pattern_type.value.lower()}")
            
        except Exception as e:
            logger.warning(f"Code analysis enhancement failed for memory {memory.id}: {e}")
    
    async def _calculate_note_safety_score(self, note: MarkdownNote) -> Decimal:
        """Calculate final safety score for note."""
        try:
            # Start with base score
            score = note.safety_score
            
            # Check all note components for safety
            components_to_check = [
                note.title_pattern,
                note.content,
                str(note.frontmatter),
                ' '.join(note.tags),
                ' '.join(note.backlinks)
            ]
            
            total_concrete_refs = 0
            for component in components_to_check:
                if component:
                    _, concrete_refs = self.safety_validator.auto_abstract_content(component)
                    total_concrete_refs += len(concrete_refs)
            
            # Penalize for concrete references
            if total_concrete_refs > 0:
                penalty = Decimal(str(min(0.5, total_concrete_refs * 0.1)))
                score = max(Decimal("0.0"), score - penalty)
            
            return score
            
        except Exception as e:
            logger.error(f"Safety score calculation failed: {e}")
            return Decimal("0.0")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get converter statistics."""
        stats = self._stats.copy()
        
        # Add derived metrics
        if stats['conversions_performed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['conversions_performed']
            )
            stats['safety_pass_rate'] = (
                stats['safety_validations_passed'] / 
                (stats['safety_validations_passed'] + stats['safety_validations_failed'])
            )
            stats['code_analysis_rate'] = (
                stats['code_analyses_performed'] / stats['conversions_performed']
            )
            stats['average_tags_per_note'] = (
                stats['tags_extracted'] / stats['conversions_performed']
            )
        else:
            stats.update({
                'average_processing_time_ms': 0,
                'safety_pass_rate': 1.0,
                'code_analysis_rate': 0.0,
                'average_tags_per_note': 0.0
            })
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down markdown converter...")
        # No special cleanup needed
        logger.info("Markdown converter shutdown completed")