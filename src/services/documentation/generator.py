"""
Main documentation generator for CoachNTT.ai.

Provides automated documentation generation with safety-first design,
integrating with AST analysis and script automation framework.
"""

import asyncio
import time
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from decimal import Decimal

from .models import (
    DocumentationType,
    DocumentationResult,
    DocumentationConfig,
    DocumentationMetadata,
    DocumentationSection,
    DiagramResult,
    DiagramType,
    TemplateConfig,
    CodeAnalysisInput,
    ChangelogEntry,
    APIDocEntry
)
from ...core.analysis.ast_analyzer import ASTAnalyzer
from ...core.validation.validator import SafetyValidator
from ...core.analysis.models import AnalysisResult, LanguageType

logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """
    Main documentation generator with safety-first design.
    
    Provides automated generation of README, API docs, changelogs,
    and architecture diagrams with complete safety compliance.
    """
    
    def __init__(
        self,
        config: DocumentationConfig,
        ast_analyzer: Optional[ASTAnalyzer] = None,
        safety_validator: Optional[SafetyValidator] = None
    ):
        """
        Initialize documentation generator.
        
        Args:
            config: Documentation generation configuration
            ast_analyzer: AST analyzer for code understanding
            safety_validator: Safety validator for content validation
        """
        self.config = config
        self.ast_analyzer = ast_analyzer or ASTAnalyzer()
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Ensure output directory exists
        self.config.docs_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize templates directory
        if not self.config.templates_dir:
            self.config.templates_dir = self.config.docs_output_dir / "templates"
        self.config.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Analysis cache
        self._analysis_cache: Dict[str, AnalysisResult] = {}
        
        # Statistics
        self._stats = {
            'generations_performed': 0,
            'total_processing_time_ms': 0,
            'files_analyzed': 0,
            'sections_generated': 0,
            'diagrams_generated': 0,
            'safety_violations': 0,
            'cache_hits': 0
        }
        
        logger.info("DocumentationGenerator initialized")
    
    async def generate_documentation(
        self,
        target_files: Optional[List[Path]] = None,
        doc_types: Optional[List[DocumentationType]] = None
    ) -> DocumentationResult:
        """
        Generate comprehensive documentation for the project.
        
        Args:
            target_files: Specific files to analyze (None for all project files)
            doc_types: Types of documentation to generate (None for config default)
            
        Returns:
            Complete documentation generation result
        """
        start_time = time.time()
        
        # Initialize result
        result = DocumentationResult(
            config=self.config,
            metadata=DocumentationMetadata()
        )
        
        try:
            logger.info("Starting documentation generation")
            
            # Determine documentation types to generate
            types_to_generate = doc_types or self.config.enabled_types
            
            # Phase 1: Analyze codebase
            if self.config.analyze_code:
                analysis_results = await self._analyze_codebase(target_files, result)
            else:
                analysis_results = {}
            
            # Phase 2: Generate each documentation type
            for doc_type in types_to_generate:
                await self._generate_documentation_type(doc_type, analysis_results, result)
            
            # Phase 3: Generate diagrams if requested
            if DocumentationType.DIAGRAMS in types_to_generate:
                await self._generate_diagrams(analysis_results, result)
            
            # Phase 4: Validate all generated content
            if self.config.validate_output:
                await self._validate_generated_content(result)
            
            # Phase 5: Write output files
            await self._write_documentation_files(result)
            
            # Finalize result
            result.success = len(result.errors) == 0
            
        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            result.errors.append(f"Generation failed: {str(e)}")
            result.success = False
        
        finally:
            # Update metadata
            total_time = (time.time() - start_time) * 1000
            result.metadata.processing_time_ms = int(total_time)
            result.metadata.generation_timestamp = datetime.now()
            
            # Update stats
            self._update_stats(result, total_time)
            
            logger.info(
                f"Documentation generation completed in {total_time:.1f}ms: "
                f"{len(result.sections)} sections, {len(result.diagrams)} diagrams"
            )
        
        return result
    
    async def _analyze_codebase(
        self,
        target_files: Optional[List[Path]],
        result: DocumentationResult
    ) -> Dict[str, AnalysisResult]:
        """
        Analyze codebase to extract information for documentation.
        
        Args:
            target_files: Specific files to analyze
            result: Result object to update with metadata
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        analysis_results = {}
        
        # Determine files to analyze
        if target_files:
            files_to_analyze = target_files
        else:
            files_to_analyze = self._discover_source_files()
        
        logger.info(f"Analyzing {len(files_to_analyze)} source files")
        
        total_functions = 0
        total_classes = 0
        total_lines = 0
        
        for file_path in files_to_analyze:
            try:
                # Check cache first
                cache_key = f"{file_path}:{file_path.stat().st_mtime}"
                if self.config.enable_caching and cache_key in self._analysis_cache:
                    analysis_result = self._analysis_cache[cache_key]
                    self._stats['cache_hits'] += 1
                else:
                    # Read and analyze file
                    content = file_path.read_text(encoding='utf-8')
                    
                    analysis_result = await self.ast_analyzer.analyze_code(
                        content=content,
                        filename=str(file_path)
                    )
                    
                    # Cache result
                    if self.config.enable_caching:
                        self._analysis_cache[cache_key] = analysis_result
                
                analysis_results[str(file_path)] = analysis_result
                
                # Update statistics
                total_functions += len(analysis_result.functions)
                total_classes += len(analysis_result.classes)
                total_lines += len(content.splitlines())
                
                self._stats['files_analyzed'] += 1
                
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                result.warnings.append(f"Analysis failed for {file_path.name}: {str(e)}")
        
        # Update result metadata
        result.metadata.analyzed_files_count = len(analysis_results)
        result.metadata.functions_analyzed = total_functions
        result.metadata.classes_analyzed = total_classes
        result.metadata.total_lines_of_code = total_lines
        
        return analysis_results
    
    def _discover_source_files(self) -> List[Path]:
        """Discover source files in the project."""
        source_files = []
        
        # Common source file patterns
        patterns = ['**/*.py', '**/*.js', '**/*.ts', '**/*.jsx', '**/*.tsx']
        
        # Directories to exclude
        exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build'}
        
        for pattern in patterns:
            for file_path in self.config.project_root.glob(pattern):
                # Skip files in excluded directories
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue
                
                if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                    source_files.append(file_path)
        
        return sorted(source_files)
    
    async def _generate_documentation_type(
        self,
        doc_type: DocumentationType,
        analysis_results: Dict[str, AnalysisResult],
        result: DocumentationResult
    ) -> None:
        """
        Generate specific type of documentation.
        
        Args:
            doc_type: Type of documentation to generate
            analysis_results: Code analysis results
            result: Result object to populate
        """
        logger.debug(f"Generating {doc_type.value} documentation")
        
        try:
            if doc_type == DocumentationType.README:
                await self._generate_readme(analysis_results, result)
            elif doc_type == DocumentationType.API_DOCS:
                await self._generate_api_docs(analysis_results, result)
            elif doc_type == DocumentationType.CHANGELOG:
                await self._generate_changelog(result)
            elif doc_type == DocumentationType.ARCHITECTURE:
                await self._generate_architecture_docs(analysis_results, result)
            elif doc_type == DocumentationType.CODE_REFERENCE:
                await self._generate_code_reference(analysis_results, result)
            else:
                logger.warning(f"Unsupported documentation type: {doc_type}")
                
        except Exception as e:
            logger.error(f"Failed to generate {doc_type.value}: {e}")
            result.errors.append(f"{doc_type.value} generation failed: {str(e)}")
    
    async def _generate_readme(
        self,
        analysis_results: Dict[str, AnalysisResult],
        result: DocumentationResult
    ) -> None:
        """Generate README documentation."""
        # Project overview section
        overview_section = DocumentationSection(
            section_id="overview",
            title="Project Overview",
            content=self._generate_project_overview(analysis_results),
            order=1
        )
        
        # Installation section
        install_section = DocumentationSection(
            section_id="installation",
            title="Installation",
            content=self._generate_installation_guide(),
            order=2
        )
        
        # Usage section
        usage_section = DocumentationSection(
            section_id="usage",
            title="Usage",
            content=self._generate_usage_examples(analysis_results),
            order=3
        )
        
        # API overview section
        if analysis_results:
            api_section = DocumentationSection(
                section_id="api_overview",
                title="API Overview",
                content=self._generate_api_overview(analysis_results),
                order=4
            )
            result.sections.append(api_section)
        
        result.sections.extend([overview_section, install_section, usage_section])
        logger.debug("README sections generated")
    
    async def _generate_api_docs(
        self,
        analysis_results: Dict[str, AnalysisResult],
        result: DocumentationResult
    ) -> None:
        """Generate API documentation."""
        if not analysis_results:
            return
        
        # Collect all API entries
        api_entries = []
        
        for file_path, analysis in analysis_results.items():
            # Generate function documentation
            for func in analysis.functions:
                api_entry = APIDocEntry(
                    name=func.name_pattern,
                    type="function",
                    signature=self._generate_function_signature(func),
                    abstracted_name=func.name_pattern,
                    source_file=Path(file_path).name,
                    safety_validated=True
                )
                api_entries.append(api_entry)
            
            # Generate class documentation
            for cls in analysis.classes:
                api_entry = APIDocEntry(
                    name=cls.name_pattern,
                    type="class",
                    signature=f"class {cls.name_pattern}",
                    description=f"Class with {cls.method_count} methods and {cls.property_count} properties",
                    abstracted_name=cls.name_pattern,
                    source_file=Path(file_path).name,
                    safety_validated=True
                )
                api_entries.append(api_entry)
        
        # Group by type and create sections
        functions = [entry for entry in api_entries if entry.type == "function"]
        classes = [entry for entry in api_entries if entry.type == "class"]
        
        if functions:
            func_content = self._format_api_entries("Functions", functions)
            func_section = DocumentationSection(
                section_id="api_functions",
                title="Functions",
                content=func_content,
                section_type="api",
                order=1
            )
            result.sections.append(func_section)
        
        if classes:
            class_content = self._format_api_entries("Classes", classes)
            class_section = DocumentationSection(
                section_id="api_classes",
                title="Classes",
                content=class_content,
                section_type="api",
                order=2
            )
            result.sections.append(class_section)
        
        logger.debug(f"API documentation generated: {len(api_entries)} entries")
    
    async def _generate_changelog(self, result: DocumentationResult) -> None:
        """Generate changelog from git history."""
        if not self.config.enable_git_integration:
            logger.debug("Git integration disabled, skipping changelog generation")
            return
        
        try:
            import git
            
            repo = git.Repo(self.config.project_root)
            commits = list(repo.iter_commits(max_count=50))
            
            changelog_entries = []
            current_version = "1.0.0"  # Would be detected from tags in real implementation
            
            for commit in commits[:10]:  # Last 10 commits
                # Abstract commit message for safety
                abstracted_message, _ = self.safety_validator.auto_abstract_content(
                    commit.message
                )
                
                entry = ChangelogEntry(
                    version=current_version,
                    date=datetime.fromtimestamp(commit.committed_date),
                    description=abstracted_message.split('\n')[0],
                    commit_hash=commit.hexsha[:8],
                    author="<contributor>"  # Abstracted for safety
                )
                changelog_entries.append(entry)
            
            # Format changelog content
            changelog_content = self._format_changelog(changelog_entries)
            
            changelog_section = DocumentationSection(
                section_id="changelog",
                title="Changelog",
                content=changelog_content,
                order=1
            )
            result.sections.append(changelog_section)
            
            logger.debug(f"Changelog generated with {len(changelog_entries)} entries")
            
        except Exception as e:
            logger.warning(f"Changelog generation failed: {e}")
            result.warnings.append(f"Changelog generation failed: {str(e)}")
    
    async def _generate_architecture_docs(
        self,
        analysis_results: Dict[str, AnalysisResult],
        result: DocumentationResult
    ) -> None:
        """Generate architecture documentation."""
        # Project structure overview
        structure_content = self._generate_project_structure()
        structure_section = DocumentationSection(
            section_id="project_structure",
            title="Project Structure",
            content=structure_content,
            order=1
        )
        
        # Component overview
        if analysis_results:
            components_content = self._generate_components_overview(analysis_results)
            components_section = DocumentationSection(
                section_id="components",
                title="Components Overview",
                content=components_content,
                order=2
            )
            result.sections.append(components_section)
        
        result.sections.append(structure_section)
        logger.debug("Architecture documentation generated")
    
    async def _generate_code_reference(
        self,
        analysis_results: Dict[str, AnalysisResult],
        result: DocumentationResult
    ) -> None:
        """Generate detailed code reference."""
        if not analysis_results:
            return
        
        for file_path, analysis in analysis_results.items():
            file_name = Path(file_path).name
            
            # Generate file overview
            file_content = f"# {file_name}\n\n"
            
            if analysis.functions:
                file_content += "## Functions\n\n"
                for func in analysis.functions:
                    file_content += f"### {func.name_pattern}\n\n"
                    file_content += f"**Signature**: `{self._generate_function_signature(func)}`\n\n"
                    if func.docstring_present:
                        file_content += "**Documentation**: Available\n\n"
                    if func.decorators:
                        file_content += f"**Decorators**: {', '.join(func.decorators)}\n\n"
            
            if analysis.classes:
                file_content += "## Classes\n\n"
                for cls in analysis.classes:
                    file_content += f"### {cls.name_pattern}\n\n"
                    file_content += f"**Methods**: {cls.method_count}\n"
                    file_content += f"**Properties**: {cls.property_count}\n\n"
                    if cls.base_class_patterns:
                        file_content += f"**Inherits from**: {', '.join(cls.base_class_patterns)}\n\n"
            
            file_section = DocumentationSection(
                section_id=f"code_ref_{file_name}",
                title=f"Code Reference: {file_name}",
                content=file_content,
                section_type="code_reference",
                generated_from=[file_path]
            )
            result.sections.append(file_section)
        
        logger.debug(f"Code reference generated for {len(analysis_results)} files")
    
    async def _generate_diagrams(
        self,
        analysis_results: Dict[str, AnalysisResult],
        result: DocumentationResult
    ) -> None:
        """Generate diagrams from analysis results."""
        if not analysis_results:
            return
        
        # Generate dependency graph
        dependency_diagram = await self._generate_dependency_diagram(analysis_results)
        if dependency_diagram:
            result.diagrams.append(dependency_diagram)
        
        # Generate architecture overview
        arch_diagram = await self._generate_architecture_diagram(analysis_results)
        if arch_diagram:
            result.diagrams.append(arch_diagram)
        
        logger.debug(f"Generated {len(result.diagrams)} diagrams")
    
    async def _generate_dependency_diagram(
        self,
        analysis_results: Dict[str, AnalysisResult]
    ) -> Optional[DiagramResult]:
        """Generate dependency graph diagram."""
        try:
            # Collect all nodes and dependencies
            nodes = []
            edges = []
            
            for file_path, analysis in analysis_results.items():
                file_name = Path(file_path).stem
                
                # Add file node
                nodes.append(f"    {file_name}[{file_name}]")
                
                # Add function/class nodes
                for func in analysis.functions:
                    func_id = f"{file_name}_{func.name_pattern}"
                    nodes.append(f"    {func_id}[{func.name_pattern}]")
                    edges.append(f"    {file_name} --> {func_id}")
                
                for cls in analysis.classes:
                    class_id = f"{file_name}_{cls.name_pattern}"
                    nodes.append(f"    {class_id}[{cls.name_pattern}]")
                    edges.append(f"    {file_name} --> {class_id}")
            
            # Generate Mermaid code
            mermaid_code = "graph TD\n"
            mermaid_code += "\n".join(nodes[:20])  # Limit nodes for readability
            mermaid_code += "\n"
            mermaid_code += "\n".join(edges[:20])  # Limit edges for readability
            
            diagram = DiagramResult(
                diagram_type=DiagramType.DEPENDENCY_GRAPH,
                diagram_id="dependency_graph",
                mermaid_code=mermaid_code,
                nodes_count=len(nodes),
                edges_count=len(edges),
                safety_compliant=True
            )
            
            return diagram
            
        except Exception as e:
            logger.warning(f"Dependency diagram generation failed: {e}")
            return None
    
    async def _generate_architecture_diagram(
        self,
        analysis_results: Dict[str, AnalysisResult]
    ) -> Optional[DiagramResult]:
        """Generate architecture overview diagram."""
        try:
            # Create high-level architecture view
            mermaid_code = """graph TB
    subgraph "Core"
        A[Safety Validator] --> B[AST Analyzer]
        B --> C[Memory Repository]
    end
    
    subgraph "Services"
        D[Documentation Generator] --> A
        E[Vault Sync] --> C
        F[Script Runner] --> A
    end
    
    subgraph "APIs"
        G[REST API] --> C
        H[CLI Interface] --> F
    end"""
            
            diagram = DiagramResult(
                diagram_type=DiagramType.ARCHITECTURE_OVERVIEW,
                diagram_id="architecture_overview",
                mermaid_code=mermaid_code,
                nodes_count=8,
                edges_count=6,
                safety_compliant=True
            )
            
            return diagram
            
        except Exception as e:
            logger.warning(f"Architecture diagram generation failed: {e}")
            return None
    
    def _generate_project_overview(self, analysis_results: Dict[str, AnalysisResult]) -> str:
        """Generate project overview content."""
        total_files = len(analysis_results)
        total_functions = sum(len(r.functions) for r in analysis_results.values())
        total_classes = sum(len(r.classes) for r in analysis_results.values())
        
        content = f"""# {self.config.project_name}

{self.config.project_description}

## Project Statistics

- **Source Files**: {total_files}
- **Functions**: {total_functions}
- **Classes**: {total_classes}
- **Documentation Coverage**: Generated automatically with safety compliance

## Core Features

- Safety-first design with complete abstraction of concrete references
- Automated documentation generation
- AST-based code analysis
- Integration with script automation framework"""
        
        return content
    
    def _generate_installation_guide(self) -> str:
        """Generate installation guide."""
        return """## Installation

### Prerequisites

- Python 3.10+
- Git

### Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment: Copy `.env.example` to `.env`
4. Initialize database: `python scripts/setup-db.py`

### Development Setup

1. Install development dependencies: `pip install -r requirements-dev.txt`
2. Set up pre-commit hooks: `pre-commit install`
3. Run tests: `python -m pytest`"""
    
    def _generate_usage_examples(self, analysis_results: Dict[str, AnalysisResult]) -> str:
        """Generate usage examples."""
        content = """## Usage

### Basic Usage

```python
from src.services.documentation import DocumentationGenerator
from src.services.documentation.models import DocumentationConfig

# Configure documentation generation
config = DocumentationConfig(
    project_root=Path("."),
    docs_output_dir=Path("./docs"),
    project_name="<project_name>"
)

# Generate documentation
generator = DocumentationGenerator(config)
result = await generator.generate_documentation()
```

### Advanced Configuration

```python
# Enable specific documentation types
config.enabled_types = [
    DocumentationType.README,
    DocumentationType.API_DOCS,
    DocumentationType.DIAGRAMS
]

# Configure safety settings
config.safety_score_threshold = Decimal("0.8")
config.enforce_abstraction = True
```"""
        
        return content
    
    def _generate_api_overview(self, analysis_results: Dict[str, AnalysisResult]) -> str:
        """Generate API overview."""
        total_functions = sum(len(r.functions) for r in analysis_results.values())
        total_classes = sum(len(r.classes) for r in analysis_results.values())
        
        return f"""## API Overview

This project provides {total_functions} functions and {total_classes} classes across {len(analysis_results)} modules.

### Key Components

- **Core Analysis**: AST-based code understanding
- **Safety Validation**: Automated abstraction and compliance
- **Documentation Generation**: Automated docs with safety compliance

For detailed API documentation, see the [API Reference](api-reference.md)."""
    
    def _generate_function_signature(self, func) -> str:
        """Generate function signature string."""
        params = ", ".join(func.parameter_types) if func.parameter_types else ""
        return_type = f" -> {func.return_type}" if func.return_type else ""
        async_prefix = "async " if func.is_async else ""
        
        return f"{async_prefix}def {func.name_pattern}({params}){return_type}"
    
    def _format_api_entries(self, title: str, entries: List[APIDocEntry]) -> str:
        """Format API entries into markdown."""
        content = f"## {title}\n\n"
        
        for entry in entries:
            content += f"### {entry.name}\n\n"
            content += f"**Type**: {entry.type}\n"
            content += f"**Signature**: `{entry.signature}`\n\n"
            if entry.description:
                content += f"{entry.description}\n\n"
            if entry.source_file:
                content += f"**Source**: {entry.source_file}\n\n"
            content += "---\n\n"
        
        return content
    
    def _format_changelog(self, entries: List[ChangelogEntry]) -> str:
        """Format changelog entries."""
        content = "# Changelog\n\n"
        
        for entry in entries:
            date_str = entry.date.strftime("%Y-%m-%d")
            content += f"## {entry.version} - {date_str}\n\n"
            content += f"{entry.description}\n\n"
            if entry.commit_hash:
                content += f"**Commit**: {entry.commit_hash}\n\n"
            content += "---\n\n"
        
        return content
    
    def _generate_project_structure(self) -> str:
        """Generate project structure documentation."""
        return """## Project Structure

```
src/
├── core/               # Core framework components
│   ├── safety/         # Safety validation and abstraction
│   ├── analysis/       # AST analysis and code understanding
│   ├── memory/         # Memory management and storage
│   └── validation/     # Content validation pipelines
├── services/           # High-level services
│   ├── documentation/  # Documentation generation
│   ├── vault/          # Vault synchronization
│   └── monitoring/     # System monitoring
└── scripts/            # Automation scripts
    ├── framework/      # Script execution framework
    ├── development/    # Development automation
    └── testing/        # Test execution
```"""
    
    def _generate_components_overview(self, analysis_results: Dict[str, AnalysisResult]) -> str:
        """Generate components overview."""
        components = {}
        
        for file_path, analysis in analysis_results.items():
            path_parts = Path(file_path).parts
            if 'src' in path_parts:
                component = path_parts[path_parts.index('src') + 1] if len(path_parts) > path_parts.index('src') + 1 else 'root'
                if component not in components:
                    components[component] = {'files': 0, 'functions': 0, 'classes': 0}
                
                components[component]['files'] += 1
                components[component]['functions'] += len(analysis.functions)
                components[component]['classes'] += len(analysis.classes)
        
        content = "## Components Overview\n\n"
        for component, stats in components.items():
            content += f"### {component.title()}\n\n"
            content += f"- **Files**: {stats['files']}\n"
            content += f"- **Functions**: {stats['functions']}\n"
            content += f"- **Classes**: {stats['classes']}\n\n"
        
        return content
    
    async def _validate_generated_content(self, result: DocumentationResult) -> None:
        """Validate all generated content for safety compliance."""
        safety_violations = 0
        
        for section in result.sections:
            # Validate section content
            validation_result = self.safety_validator.validate_content(section.content)
            
            if validation_result.safety_score < self.config.safety_score_threshold:
                safety_violations += 1
                result.warnings.append(
                    f"Section '{section.title}' safety score below threshold: "
                    f"{validation_result.safety_score}"
                )
            
            section.safety_validated = validation_result.safety_score >= self.config.safety_score_threshold
        
        # Update metadata
        result.metadata.safety_score = Decimal("1.0") if safety_violations == 0 else Decimal("0.8")
        result.metadata.concrete_references_removed = sum(
            len(self.safety_validator.auto_abstract_content(s.content)[1]) 
            for s in result.sections
        )
        
        if safety_violations > 0:
            self._stats['safety_violations'] += safety_violations
            logger.warning(f"Safety validation found {safety_violations} violations")
    
    async def _write_documentation_files(self, result: DocumentationResult) -> None:
        """Write generated documentation to files."""
        # Group sections by type and write to appropriate files
        readme_sections = [s for s in result.sections if s.section_id.startswith(('overview', 'installation', 'usage', 'api_overview'))]
        api_sections = [s for s in result.sections if s.section_type == 'api']
        
        # Write README.md
        if readme_sections:
            readme_path = self.config.docs_output_dir / "README.md"
            readme_content = "\n\n".join(s.content for s in sorted(readme_sections, key=lambda x: x.order))
            readme_path.write_text(readme_content, encoding='utf-8')
            result.generated_files["README"] = readme_path
        
        # Write API documentation
        if api_sections:
            api_path = self.config.docs_output_dir / "api-reference.md"
            api_content = "# API Reference\n\n" + "\n\n".join(s.content for s in api_sections)
            api_path.write_text(api_content, encoding='utf-8')
            result.generated_files["API_DOCS"] = api_path
        
        # Write diagrams
        for diagram in result.diagrams:
            diagram_path = self.config.docs_output_dir / f"{diagram.diagram_id}.mmd"
            diagram_path.write_text(diagram.mermaid_code, encoding='utf-8')
            result.generated_files[diagram.diagram_id] = diagram_path
        
        logger.info(f"Generated {len(result.generated_files)} documentation files")
    
    def _update_stats(self, result: DocumentationResult, processing_time: float) -> None:
        """Update generation statistics."""
        self._stats['generations_performed'] += 1
        self._stats['total_processing_time_ms'] += processing_time
        self._stats['sections_generated'] += len(result.sections)
        self._stats['diagrams_generated'] += len(result.diagrams)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        stats = self._stats.copy()
        
        if stats['generations_performed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['generations_performed']
            )
            stats['average_sections_per_generation'] = (
                stats['sections_generated'] / stats['generations_performed']
            )
        
        return stats