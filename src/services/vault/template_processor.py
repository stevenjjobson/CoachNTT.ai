"""
Template processing system for vault synchronization.

Provides template-based note generation with variable substitution,
checkpoint, learning, and decision templates with safety validation.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from .models import MarkdownNote, TemplateType, TemplateVariable
from ...core.validation.validator import SafetyValidator

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """
    Processes templates for vault notes with safety-first variable substitution.
    
    Provides checkpoint, learning, and decision templates with safe variable
    replacement and validation.
    """
    
    def __init__(
        self,
        template_directory: Optional[Path] = None,
        safety_validator: Optional[SafetyValidator] = None
    ):
        """
        Initialize template processor.
        
        Args:
            template_directory: Directory containing template files
            safety_validator: Safety validator for content abstraction
        """
        self.template_directory = template_directory
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Built-in templates
        self._builtin_templates = {
            TemplateType.CHECKPOINT: self._get_checkpoint_template(),
            TemplateType.LEARNING: self._get_learning_template(),
            TemplateType.DECISION: self._get_decision_template()
        }
        
        # Statistics
        self._stats = {
            'templates_applied': 0,
            'variables_substituted': 0,
            'safety_validations': 0,
            'template_errors': 0,
            'total_processing_time_ms': 0,
            'template_usage': {
                'checkpoint': 0,
                'learning': 0,
                'decision': 0,
                'custom': 0
            }
        }
        
        logger.info("TemplateProcessor initialized")
    
    async def apply_template(
        self,
        note: MarkdownNote,
        template_type: TemplateType,
        variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Apply template to markdown note.
        
        Args:
            note: Note to apply template to
            template_type: Type of template to apply
            variables: Additional variables for substitution
            
        Returns:
            Whether template application succeeded
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Applying {template_type.value} template to note {note.title_pattern}")
            
            # Get template content
            template_content = await self._get_template_content(template_type)
            if not template_content:
                logger.error(f"Template {template_type.value} not found")
                self._stats['template_errors'] += 1
                return False
            
            # Prepare variables for substitution
            template_variables = await self._prepare_template_variables(note, variables)
            
            # Perform variable substitution
            processed_content = await self._substitute_variables(
                template_content, template_variables
            )
            
            # Validate safety
            if not await self._validate_template_safety(processed_content):
                logger.warning(f"Template {template_type.value} failed safety validation")
                self._stats['template_errors'] += 1
                return False
            
            # Apply processed template to note
            note.content = processed_content
            note.template_type = template_type
            
            # Update frontmatter with template information
            note.frontmatter['template_applied'] = template_type.value
            note.frontmatter['template_applied_at'] = datetime.now().isoformat()
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self._stats['templates_applied'] += 1
            self._stats['template_usage'][template_type.value] += 1
            self._stats['total_processing_time_ms'] += processing_time
            
            logger.debug(f"Template applied successfully in {processing_time:.1f}ms")
            return True
            
        except Exception as e:
            logger.error(f"Template application failed: {e}")
            self._stats['template_errors'] += 1
            return False
    
    async def _get_template_content(self, template_type: TemplateType) -> Optional[str]:
        """Get template content by type."""
        try:
            # Try built-in templates first
            if template_type in self._builtin_templates:
                return self._builtin_templates[template_type]
            
            # Try loading from template directory
            if self.template_directory and self.template_directory.exists():
                template_file = self.template_directory / f"{template_type.value}.md"
                if template_file.exists():
                    return template_file.read_text(encoding='utf-8')
            
            logger.warning(f"Template {template_type.value} not found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load template {template_type.value}: {e}")
            return None
    
    async def _prepare_template_variables(
        self,
        note: MarkdownNote,
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, TemplateVariable]:
        """Prepare variables for template substitution."""
        variables = {}
        
        try:
            # Standard note variables
            variables['title'] = TemplateVariable(
                name='title',
                value=note.title_pattern,
                is_safe=True,
                pattern_type='title'
            )
            
            variables['content'] = TemplateVariable(
                name='content',
                value=note.content,
                is_safe=True,
                pattern_type='content'
            )
            
            variables['created_date'] = TemplateVariable(
                name='created_date',
                value=note.created_at.strftime('%Y-%m-%d'),
                is_safe=True,
                pattern_type='date'
            )
            
            variables['created_time'] = TemplateVariable(
                name='created_time',
                value=note.created_at.strftime('%H:%M:%S'),
                is_safe=True,
                pattern_type='time'
            )
            
            variables['safety_score'] = TemplateVariable(
                name='safety_score',
                value=float(note.safety_score),
                is_safe=True,
                pattern_type='score'
            )
            
            variables['tags'] = TemplateVariable(
                name='tags',
                value=list(note.tags),
                is_safe=True,
                pattern_type='tags'
            )
            
            # Memory-specific variables
            if note.memory_id:
                variables['memory_id'] = TemplateVariable(
                    name='memory_id',
                    value=f"<memory_{str(note.memory_id)[:8]}>",
                    is_safe=True,
                    pattern_type='identifier'
                )
            
            # Add custom variables with safety validation
            if custom_variables:
                for name, value in custom_variables.items():
                    safe_value, concrete_refs = self.safety_validator.auto_abstract_content(str(value))
                    is_safe = len(concrete_refs) == 0
                    
                    variables[name] = TemplateVariable(
                        name=name,
                        value=safe_value if is_safe else value,
                        is_safe=is_safe,
                        pattern_type='custom'
                    )
            
            return variables
            
        except Exception as e:
            logger.error(f"Failed to prepare template variables: {e}")
            return {}
    
    async def _substitute_variables(
        self,
        template_content: str,
        variables: Dict[str, TemplateVariable]
    ) -> str:
        """Perform safe variable substitution in template."""
        try:
            processed_content = template_content
            substitutions_made = 0
            
            # Replace variables in format {{variable_name}}
            for var_name, var_obj in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                
                if placeholder in processed_content:
                    safe_value = var_obj.get_safe_value()
                    processed_content = processed_content.replace(placeholder, safe_value)
                    substitutions_made += 1
            
            # Handle conditional blocks {{#if variable}}...{{/if}}
            processed_content = await self._process_conditional_blocks(
                processed_content, variables
            )
            
            # Handle list iterations {{#each tags}}...{{/each}}
            processed_content = await self._process_list_iterations(
                processed_content, variables
            )
            
            self._stats['variables_substituted'] += substitutions_made
            
            logger.debug(f"Made {substitutions_made} variable substitutions")
            return processed_content
            
        except Exception as e:
            logger.error(f"Variable substitution failed: {e}")
            return template_content
    
    async def _process_conditional_blocks(
        self,
        content: str,
        variables: Dict[str, TemplateVariable]
    ) -> str:
        """Process conditional blocks in template."""
        import re
        
        # Simple conditional processing: {{#if variable}}content{{/if}}
        pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
        
        def replace_conditional(match):
            var_name = match.group(1)
            block_content = match.group(2)
            
            if var_name in variables:
                var_value = variables[var_name].value
                # Include block if variable has truthy value
                if var_value and str(var_value).lower() not in ['false', '0', '', 'none']:
                    return block_content
            
            return ""  # Remove block if condition not met
        
        return re.sub(pattern, replace_conditional, content, flags=re.DOTALL)
    
    async def _process_list_iterations(
        self,
        content: str,
        variables: Dict[str, TemplateVariable]
    ) -> str:
        """Process list iterations in template."""
        import re
        
        # Simple list processing: {{#each variable}}content{{/each}}
        pattern = r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}'
        
        def replace_iteration(match):
            var_name = match.group(1)
            item_template = match.group(2)
            
            if var_name in variables:
                var_value = variables[var_name].value
                if isinstance(var_value, (list, tuple)):
                    items = []
                    for item in var_value:
                        item_content = item_template.replace('{{this}}', str(item))
                        items.append(item_content)
                    return '\n'.join(items)
                else:
                    # Single item
                    return item_template.replace('{{this}}', str(var_value))
            
            return ""  # Remove block if variable not found
        
        return re.sub(pattern, replace_iteration, content, flags=re.DOTALL)
    
    async def _validate_template_safety(self, content: str) -> bool:
        """Validate processed template for safety."""
        try:
            # Use safety validator to check processed content
            abstracted_content, concrete_refs = self.safety_validator.auto_abstract_content(content)
            
            self._stats['safety_validations'] += 1
            
            # Should have no concrete references after processing
            return len(concrete_refs) == 0
            
        except Exception as e:
            logger.error(f"Template safety validation failed: {e}")
            return False
    
    def _get_checkpoint_template(self) -> str:
        """Get built-in checkpoint template."""
        return """# {{title}}

## Checkpoint Summary

**Date:** {{created_date}} {{created_time}}  
**Safety Score:** {{safety_score}}  
**Memory ID:** {{memory_id}}

## Content Snapshot

{{content}}

{{#if tags}}
## Tags
{{#each tags}}
- #{{this}}
{{/each}}
{{/if}}

## Context

This is a checkpoint snapshot capturing the current state of development or analysis. The content has been abstracted for safety while preserving semantic meaning.

**Template Applied:** checkpoint  
**Generated:** {{created_date}} {{created_time}}

---

*This note was generated automatically from abstracted memory content.*"""
    
    def _get_learning_template(self) -> str:
        """Get built-in learning template."""
        return """# {{title}}

## Learning Objective

**Captured:** {{created_date}} {{created_time}}  
**Safety Score:** {{safety_score}}

## Key Insights

{{content}}

{{#if tags}}
## Topics Covered
{{#each tags}}
- {{this}}
{{/each}}
{{/if}}

## Learning Notes

- **What was learned:** Core concepts and patterns identified
- **How it applies:** Practical applications and use cases
- **Next steps:** Areas for further exploration

## Knowledge Integration

This learning note captures abstracted knowledge patterns that can be referenced and built upon in future work.

**Template Applied:** learning  
**Generated:** {{created_date}} {{created_time}}

---

*This note represents abstracted learning content for safe knowledge management.*"""
    
    def _get_decision_template(self) -> str:
        """Get built-in decision template."""
        return """# {{title}}

## Decision Context

**Date:** {{created_date}} {{created_time}}  
**Safety Score:** {{safety_score}}

## Background

{{content}}

## Decision Points

- **Options considered:** Multiple approaches evaluated
- **Criteria used:** Safety, performance, maintainability
- **Stakeholders:** Development team and safety requirements

## Rationale

The decision was made based on abstracted analysis that prioritizes:
1. Safety-first principles
2. Code quality and maintainability  
3. Performance requirements
4. Integration capabilities

{{#if tags}}
## Related Areas
{{#each tags}}
- {{this}}
{{/each}}
{{/if}}

## Implementation Notes

Key implementation considerations have been documented with concrete references abstracted for safety.

**Template Applied:** decision  
**Generated:** {{created_date}} {{created_time}}

---

*This note captures decision-making context with abstracted implementation details.*"""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get template processor statistics."""
        stats = self._stats.copy()
        
        # Add derived metrics
        if stats['templates_applied'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['templates_applied']
            )
            stats['average_substitutions_per_template'] = (
                stats['variables_substituted'] / stats['templates_applied']
            )
            stats['template_success_rate'] = (
                1.0 - (stats['template_errors'] / 
                      (stats['templates_applied'] + stats['template_errors']))
            )
        else:
            stats.update({
                'average_processing_time_ms': 0,
                'average_substitutions_per_template': 0,
                'template_success_rate': 1.0
            })
        
        # Add template usage percentages
        total_usage = sum(stats['template_usage'].values())
        if total_usage > 0:
            stats['template_usage_percentages'] = {
                template: (count / total_usage) * 100
                for template, count in stats['template_usage'].items()
            }
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down template processor...")
        # No special cleanup needed
        logger.info("Template processor shutdown completed")