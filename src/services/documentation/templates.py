"""
Template system for documentation generation with safety validation.

Provides configurable templates for different documentation types
with safety-first design and variable substitution.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from string import Template

from .models import TemplateConfig, DocumentationType
from ...core.validation.validator import SafetyValidator

logger = logging.getLogger(__name__)


@dataclass
class TemplateVariable:
    """Template variable definition with validation."""
    
    name: str
    description: str
    required: bool = True
    default_value: Any = None
    validation_pattern: Optional[str] = None
    abstract_value: bool = True  # Whether value should be abstracted for safety


class DocumentationTemplateManager:
    """
    Template manager for documentation generation with safety validation.
    
    Provides template loading, variable substitution, and safety validation
    for all generated documentation content.
    """
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        """
        Initialize template manager.
        
        Args:
            safety_validator: Safety validator for content validation
        """
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Built-in templates
        self._builtin_templates = self._load_builtin_templates()
        
        # Custom templates
        self._custom_templates: Dict[str, TemplateConfig] = {}
        
        logger.info("DocumentationTemplateManager initialized")
    
    def _load_builtin_templates(self) -> Dict[str, str]:
        """Load built-in documentation templates."""
        return {
            'readme_overview': self._get_readme_overview_template(),
            'readme_installation': self._get_readme_installation_template(),
            'readme_usage': self._get_readme_usage_template(),
            'api_function': self._get_api_function_template(),
            'api_class': self._get_api_class_template(),
            'changelog_entry': self._get_changelog_entry_template(),
            'architecture_overview': self._get_architecture_overview_template(),
            'project_structure': self._get_project_structure_template()
        }
    
    def register_template(self, template_config: TemplateConfig) -> None:
        """
        Register a custom template.
        
        Args:
            template_config: Template configuration to register
        """
        # Validate template content for safety
        if template_config.template_content:
            validation_result = self.safety_validator.validate_content(
                template_config.template_content
            )
            
            if validation_result.safety_score < 0.8:
                raise ValueError(
                    f"Template '{template_config.template_name}' failed safety validation "
                    f"(score: {validation_result.safety_score})"
                )
        
        self._custom_templates[template_config.template_name] = template_config
        logger.info(f"Registered custom template: {template_config.template_name}")
    
    def render_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
        validate_safety: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Render template with variable substitution and safety validation.
        
        Args:
            template_name: Name of template to render
            variables: Variables to substitute in template
            validate_safety: Whether to validate rendered content for safety
            
        Returns:
            Tuple of (rendered_content, warnings)
            
        Raises:
            ValueError: If template not found or validation fails
        """
        # Get template content
        template_content = self._get_template_content(template_name)
        
        # Get template config if it's a custom template
        template_config = self._custom_templates.get(template_name)
        
        # Validate and prepare variables
        prepared_variables = self._prepare_variables(
            variables, template_config, template_name
        )
        
        # Perform variable substitution
        try:
            template = Template(template_content)
            rendered_content = template.safe_substitute(**prepared_variables)
            
        except Exception as e:
            raise ValueError(f"Template rendering failed for '{template_name}': {e}")
        
        warnings = []
        
        # Validate safety of rendered content
        if validate_safety:
            validation_result = self.safety_validator.validate_content(rendered_content)
            
            if validation_result.safety_score < 0.8:
                warnings.append(
                    f"Rendered template '{template_name}' has low safety score: "
                    f"{validation_result.safety_score}"
                )
            
            if validation_result.violations:
                warnings.extend([
                    f"Safety violation in template '{template_name}': {violation}"
                    for violation in validation_result.violations
                ])
        
        # Apply additional abstraction if needed
        if template_config and template_config.require_abstraction:
            rendered_content, concrete_refs = self.safety_validator.auto_abstract_content(
                rendered_content
            )
            if concrete_refs:
                warnings.append(
                    f"Applied automatic abstraction to {len(concrete_refs)} references"
                )
        
        logger.debug(f"Rendered template '{template_name}' with {len(variables)} variables")
        
        return rendered_content, warnings
    
    def _get_template_content(self, template_name: str) -> str:
        """Get template content by name."""
        # Check custom templates first
        if template_name in self._custom_templates:
            config = self._custom_templates[template_name]
            if config.template_content:
                return config.template_content
            elif config.template_path and config.template_path.exists():
                return config.template_path.read_text(encoding='utf-8')
        
        # Check built-in templates
        if template_name in self._builtin_templates:
            return self._builtin_templates[template_name]
        
        raise ValueError(f"Template not found: {template_name}")
    
    def _prepare_variables(
        self,
        variables: Dict[str, Any],
        template_config: Optional[TemplateConfig],
        template_name: str
    ) -> Dict[str, Any]:
        """Prepare and validate template variables."""
        prepared = {}
        
        # Apply safety abstraction to variables if needed
        for key, value in variables.items():
            if isinstance(value, str):
                # Check if this variable should be abstracted
                should_abstract = True
                if template_config:
                    # Check template-specific variable configuration
                    should_abstract = template_config.variables.get(f"{key}_abstract", True)
                
                if should_abstract:
                    abstracted_value, _ = self.safety_validator.auto_abstract_content(str(value))
                    prepared[key] = abstracted_value
                else:
                    prepared[key] = value
            else:
                prepared[key] = value
        
        # Add default template variables
        prepared.update({
            'template_name': template_name,
            'generation_timestamp': '${generation_timestamp}',
            'safety_notice': 'Generated with safety-first design and abstraction compliance'
        })
        
        return prepared
    
    def get_template_variables(self, template_name: str) -> List[TemplateVariable]:
        """Get list of variables used by a template."""
        template_content = self._get_template_content(template_name)
        
        # Extract variable names from template
        variable_pattern = r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(variable_pattern, template_content)
        
        variable_names = set()
        for match in matches:
            # Handle both ${var} and $var formats
            var_name = match[0] if match[0] else match[1]
            if var_name:
                variable_names.add(var_name)
        
        # Create TemplateVariable objects
        variables = []
        for var_name in sorted(variable_names):
            variables.append(TemplateVariable(
                name=var_name,
                description=f"Template variable: {var_name}",
                required=True,
                abstract_value=True
            ))
        
        return variables
    
    def validate_template(self, template_name: str) -> List[str]:
        """
        Validate template for safety and correctness.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        try:
            template_content = self._get_template_content(template_name)
            
            # Check safety of template content
            validation_result = self.safety_validator.validate_content(template_content)
            
            if validation_result.safety_score < 0.8:
                issues.append(
                    f"Template safety score too low: {validation_result.safety_score}"
                )
            
            if validation_result.violations:
                issues.extend([
                    f"Safety violation: {violation}"
                    for violation in validation_result.violations
                ])
            
            # Check for template syntax errors
            try:
                Template(template_content)
            except Exception as e:
                issues.append(f"Template syntax error: {e}")
            
        except Exception as e:
            issues.append(f"Template validation failed: {e}")
        
        return issues
    
    # Built-in template definitions
    
    def _get_readme_overview_template(self) -> str:
        """README overview section template."""
        return """# ${project_name}

${project_description}

## 📊 Project Statistics

- **Source Files**: ${total_files}
- **Functions**: ${total_functions}  
- **Classes**: ${total_classes}
- **Documentation Coverage**: ${documentation_coverage}%

## 🛡️ Safety Features

- Safety-first design with complete abstraction of concrete references
- Automated content validation and safety scoring
- Zero-tolerance policy for concrete reference exposure
- Comprehensive safety testing and validation

## 🏗️ Architecture

${architecture_overview}

---
*${safety_notice}*
"""
    
    def _get_readme_installation_template(self) -> str:
        """README installation section template."""
        return """## 🚀 Installation

### Prerequisites

- Python ${python_version}+
- Git
- ${additional_requirements}

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd ${project_directory}
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize system**
   ```bash
   ${setup_command}
   ```

### Development Setup

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

3. **Run tests**
   ```bash
   ${test_command}
   ```

### Verification

```bash
${verification_command}
```

---
*${safety_notice}*
"""
    
    def _get_readme_usage_template(self) -> str:
        """README usage section template."""
        return """## 💡 Usage

### Basic Usage

```python
from ${main_module} import ${main_class}

# Initialize with safety configuration
${usage_example}
```

### Configuration

```python
# Configure safety settings
config = {
    'safety_score_threshold': ${safety_threshold},
    'enable_abstraction': True,
    'validate_output': True
}
```

### Advanced Features

#### ${feature_1_name}
```python
${feature_1_example}
```

#### ${feature_2_name}
```python
${feature_2_example}
```

### Safety Considerations

- All concrete references are automatically abstracted
- Content undergoes safety validation before processing
- Minimum safety score of ${safety_threshold} enforced
- See [Safety Documentation](${safety_docs_link}) for details

---
*${safety_notice}*
"""
    
    def _get_api_function_template(self) -> str:
        """API function documentation template."""
        return """### ${function_name}

**Signature**: `${function_signature}`

${function_description}

#### Parameters

${parameters_table}

#### Returns

${return_description}

#### Safety Notes

- Input parameters are validated for safety compliance
- Output is abstracted to remove concrete references
- Safety score: ${safety_score}

#### Example

```python
${usage_example}
```

---
"""
    
    def _get_api_class_template(self) -> str:
        """API class documentation template."""
        return """### ${class_name}

${class_description}

#### Class Information

- **Methods**: ${method_count}
- **Properties**: ${property_count}
- **Inheritance**: ${inheritance_info}
- **Safety Validated**: ✅

#### Methods

${methods_documentation}

#### Usage

```python
${class_usage_example}
```

---
"""
    
    def _get_changelog_entry_template(self) -> str:
        """Changelog entry template."""
        return """## ${version} - ${date}

${description}

### ${change_type}

${changes_list}

${breaking_changes_section}

**Commit**: ${commit_hash}  
**Safety Score**: ${safety_score}

---
"""
    
    def _get_architecture_overview_template(self) -> str:
        """Architecture overview template."""
        return """## 🏗️ Architecture Overview

### System Design

${system_description}

### Core Components

${components_list}

### Data Flow

${data_flow_description}

### Safety Architecture

- **Abstraction Layer**: All concrete references processed through abstraction engine
- **Validation Pipeline**: Multi-stage content validation with safety scoring
- **Safety Enforcement**: Database-level and application-level safety constraints

### Performance Characteristics

- **Analysis Speed**: ${analysis_performance}
- **Memory Usage**: ${memory_usage}
- **Scalability**: ${scalability_info}

---
*${safety_notice}*
"""
    
    def _get_project_structure_template(self) -> str:
        """Project structure template."""
        return """## 📁 Project Structure

```
${project_structure_tree}
```

### Directory Overview

${directory_descriptions}

### Key Files

${key_files_list}

### Configuration Files

${config_files_list}

---
*${safety_notice}*
"""
    
    def list_available_templates(self) -> List[str]:
        """Get list of all available templates."""
        builtin_templates = list(self._builtin_templates.keys())
        custom_templates = list(self._custom_templates.keys())
        
        return sorted(builtin_templates + custom_templates)
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get detailed information about a template."""
        if template_name not in self.list_available_templates():
            raise ValueError(f"Template not found: {template_name}")
        
        template_content = self._get_template_content(template_name)
        variables = self.get_template_variables(template_name)
        validation_issues = self.validate_template(template_name)
        
        is_custom = template_name in self._custom_templates
        config = self._custom_templates.get(template_name) if is_custom else None
        
        return {
            'name': template_name,
            'type': 'custom' if is_custom else 'builtin',
            'content_length': len(template_content),
            'variables_count': len(variables),
            'variables': [var.name for var in variables],
            'validation_issues': validation_issues,
            'is_valid': len(validation_issues) == 0,
            'safety_validated': True,
            'config': config
        }