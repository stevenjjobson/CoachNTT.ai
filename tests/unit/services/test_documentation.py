"""
Unit tests for documentation generation service.

Tests DocumentationGenerator, models, and integration with AST analysis
with safety validation and performance monitoring.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.services.documentation import (
    DocumentationGenerator,
    DocumentationType,
    DocumentationConfig,
    DocumentationResult,
    DocumentationSection,
    DiagramResult,
    DiagramType
)
from src.core.analysis.ast_analyzer import ASTAnalyzer
from src.core.analysis.models import AnalysisResult, LanguageType, FunctionSignature, ClassStructure
from src.core.validation.validator import SafetyValidator


class TestDocumentationModels:
    """Test documentation data models."""
    
    def test_documentation_config_creation(self):
        """Test documentation configuration creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DocumentationConfig(
                project_root=Path(temp_dir),
                docs_output_dir=Path(temp_dir) / "docs",
                project_name="Test Project",
                enabled_types=[DocumentationType.README, DocumentationType.API_DOCS]
            )
            
            assert config.project_name == "Test Project"
            assert DocumentationType.README in config.enabled_types
            assert DocumentationType.API_DOCS in config.enabled_types
            assert config.safety_score_threshold == Decimal("0.8")
            assert config.analyze_code is True
    
    def test_documentation_result_summary(self):
        """Test documentation result summary generation."""
        config = DocumentationConfig(
            project_root=Path("."),
            docs_output_dir=Path("./docs")
        )
        
        result = DocumentationResult(config=config, metadata=Mock())
        result.success = True
        result.sections = [Mock(), Mock()]
        result.diagrams = [Mock()]
        result.generated_files = {"README": Path("./README.md")}
        result.metadata.processing_time_ms = 1500
        result.metadata.safety_score = Decimal("0.95")
        
        summary = result.get_summary()
        
        assert summary['success'] is True
        assert summary['sections_generated'] == 2
        assert summary['diagrams_generated'] == 1
        assert summary['files_generated'] == 1
        assert summary['processing_time_ms'] == 1500
        assert summary['safety_score'] == 0.95
    
    def test_documentation_section_creation(self):
        """Test documentation section creation."""
        section = DocumentationSection(
            section_id="test_section",
            title="Test Section",
            content="# Test Content\n\nThis is a test section.",
            section_type="text",
            order=1
        )
        
        assert section.section_id == "test_section"
        assert section.title == "Test Section"
        assert "Test Content" in section.content
        assert section.section_type == "text"
        assert section.order == 1
        assert section.safety_validated is False
    
    def test_diagram_result_creation(self):
        """Test diagram result creation."""
        diagram = DiagramResult(
            diagram_type=DiagramType.DEPENDENCY_GRAPH,
            diagram_id="test_graph",
            mermaid_code="graph TD\n    A --> B",
            nodes_count=2,
            edges_count=1
        )
        
        assert diagram.diagram_type == DiagramType.DEPENDENCY_GRAPH
        assert diagram.diagram_id == "test_graph"
        assert "graph TD" in diagram.mermaid_code
        assert diagram.nodes_count == 2
        assert diagram.edges_count == 1
        assert diagram.safety_compliant is True


class TestDocumentationGenerator:
    """Test documentation generator functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DocumentationConfig(
                project_root=Path(temp_dir),
                docs_output_dir=Path(temp_dir) / "docs",
                project_name="Test Project",
                enabled_types=[DocumentationType.README],
                analyze_code=True,
                validate_output=True
            )
            return config
    
    @pytest.fixture
    def mock_ast_analyzer(self):
        """Create mock AST analyzer."""
        analyzer = Mock(spec=ASTAnalyzer)
        
        # Create mock analysis result
        analysis_result = AnalysisResult()
        analysis_result.language = LanguageType.PYTHON
        analysis_result.functions = [
            FunctionSignature(
                name_pattern="<test_function>",
                parameter_count=2,
                parameter_types=["str", "int"],
                return_type="bool",
                is_async=False,
                docstring_present=True
            )
        ]
        analysis_result.classes = [
            ClassStructure(
                name_pattern="<test_class>",
                method_count=3,
                property_count=2,
                has_init=True
            )
        ]
        
        analyzer.analyze_code.return_value = analysis_result
        return analyzer
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Create mock safety validator."""
        validator = Mock(spec=SafetyValidator)
        validator.validate_content.return_value = Mock(
            safety_score=0.95,
            violations=[]
        )
        validator.auto_abstract_content.return_value = ("abstracted content", [])
        return validator
    
    def test_generator_initialization(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test generator initialization."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        assert generator.config == mock_config
        assert generator.ast_analyzer == mock_ast_analyzer
        assert generator.safety_validator == mock_safety_validator
        assert generator._stats['generations_performed'] == 0
    
    @pytest.mark.asyncio
    async def test_generate_documentation_success(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test successful documentation generation."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Create a test Python file
        test_file = mock_config.project_root / "test.py"
        test_file.write_text("def test_function():\n    pass\n")
        
        result = await generator.generate_documentation(
            target_files=[test_file],
            doc_types=[DocumentationType.README]
        )
        
        assert result.success is True
        assert len(result.sections) > 0
        assert result.metadata.processing_time_ms > 0
        assert mock_ast_analyzer.analyze_code.called
    
    @pytest.mark.asyncio
    async def test_analyze_codebase(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test codebase analysis."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Create test files
        test_file1 = mock_config.project_root / "test1.py"
        test_file1.write_text("def function1(): pass")
        test_file2 = mock_config.project_root / "test2.py"
        test_file2.write_text("class TestClass: pass")
        
        result = DocumentationResult(config=mock_config, metadata=Mock())
        analysis_results = await generator._analyze_codebase(
            target_files=[test_file1, test_file2],
            result=result
        )
        
        assert len(analysis_results) == 2
        assert str(test_file1) in analysis_results
        assert str(test_file2) in analysis_results
        assert mock_ast_analyzer.analyze_code.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_readme(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test README generation."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Mock analysis results
        analysis_results = {
            "test.py": mock_ast_analyzer.analyze_code.return_value
        }
        
        result = DocumentationResult(config=mock_config, metadata=Mock())
        await generator._generate_readme(analysis_results, result)
        
        assert len(result.sections) >= 3  # Overview, Installation, Usage
        readme_sections = [s for s in result.sections if s.section_id in ['overview', 'installation', 'usage']]
        assert len(readme_sections) >= 3
        
        # Check content
        overview_section = next(s for s in result.sections if s.section_id == 'overview')
        assert mock_config.project_name in overview_section.content
    
    @pytest.mark.asyncio
    async def test_generate_api_docs(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test API documentation generation."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Mock analysis results with functions and classes
        analysis_results = {
            "test.py": mock_ast_analyzer.analyze_code.return_value
        }
        
        result = DocumentationResult(config=mock_config, metadata=Mock())
        await generator._generate_api_docs(analysis_results, result)
        
        # Should have sections for functions and classes
        func_sections = [s for s in result.sections if s.section_id == 'api_functions']
        class_sections = [s for s in result.sections if s.section_id == 'api_classes']
        
        assert len(func_sections) == 1
        assert len(class_sections) == 1
        
        # Check content
        func_section = func_sections[0]
        assert "<test_function>" in func_section.content
        
        class_section = class_sections[0]
        assert "<test_class>" in class_section.content
    
    @pytest.mark.asyncio
    async def test_generate_diagrams(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test diagram generation."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Mock analysis results
        analysis_results = {
            "test.py": mock_ast_analyzer.analyze_code.return_value
        }
        
        result = DocumentationResult(config=mock_config, metadata=Mock())
        await generator._generate_diagrams(analysis_results, result)
        
        assert len(result.diagrams) >= 1
        
        # Check diagram content
        for diagram in result.diagrams:
            assert diagram.mermaid_code != ""
            assert diagram.safety_compliant is True
            assert diagram.diagram_type in [DiagramType.DEPENDENCY_GRAPH, DiagramType.ARCHITECTURE_OVERVIEW]
    
    @pytest.mark.asyncio
    async def test_safety_validation(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test safety validation of generated content."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Create result with sections
        result = DocumentationResult(config=mock_config, metadata=Mock())
        result.sections = [
            DocumentationSection(
                section_id="test",
                title="Test",
                content="Safe content with <abstractions>"
            )
        ]
        
        await generator._validate_generated_content(result)
        
        # Should have validated content
        assert mock_safety_validator.validate_content.called
        assert result.sections[0].safety_validated is True
    
    @pytest.mark.asyncio
    async def test_file_discovery(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test source file discovery."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Create test files
        (mock_config.project_root / "test.py").write_text("# Python file")
        (mock_config.project_root / "test.js").write_text("// JavaScript file")
        (mock_config.project_root / "__pycache__").mkdir()
        (mock_config.project_root / "__pycache__" / "cache.pyc").write_text("cached")
        
        discovered_files = generator._discover_source_files()
        
        # Should find Python and JavaScript files but not cache files
        file_names = [f.name for f in discovered_files]
        assert "test.py" in file_names
        assert "test.js" in file_names
        assert "cache.pyc" not in file_names
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test analysis result caching."""
        mock_config.enable_caching = True
        
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Create test file
        test_file = mock_config.project_root / "test.py"
        test_file.write_text("def test(): pass")
        
        result = DocumentationResult(config=mock_config, metadata=Mock())
        
        # First analysis should call analyzer
        await generator._analyze_codebase([test_file], result)
        assert mock_ast_analyzer.analyze_code.call_count == 1
        
        # Second analysis should use cache
        await generator._analyze_codebase([test_file], result)
        assert mock_ast_analyzer.analyze_code.call_count == 1  # Still 1, used cache
        assert generator._stats['cache_hits'] == 1
    
    def test_function_signature_generation(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test function signature generation."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        func = FunctionSignature(
            name_pattern="<test_func>",
            parameter_count=2,
            parameter_types=["str", "int"],
            return_type="bool",
            is_async=True
        )
        
        signature = generator._generate_function_signature(func)
        
        assert "async def <test_func>" in signature
        assert "str, int" in signature
        assert "-> bool" in signature
    
    def test_stats_tracking(self, mock_config, mock_ast_analyzer, mock_safety_validator):
        """Test statistics tracking."""
        generator = DocumentationGenerator(
            config=mock_config,
            ast_analyzer=mock_ast_analyzer,
            safety_validator=mock_safety_validator
        )
        
        # Simulate generation
        result = DocumentationResult(config=mock_config, metadata=Mock())
        result.sections = [Mock(), Mock()]
        result.diagrams = [Mock()]
        
        generator._update_stats(result, 1500.0)
        
        stats = generator.get_stats()
        assert stats['generations_performed'] == 1
        assert stats['sections_generated'] == 2
        assert stats['diagrams_generated'] == 1
        assert stats['total_processing_time_ms'] == 1500.0


class TestDocumentationIntegration:
    """Integration tests for documentation generation."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_documentation_generation(self):
        """Test complete documentation generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            docs_dir = project_root / "docs"
            
            # Create sample Python file
            sample_file = project_root / "sample.py"
            sample_file.write_text('''
"""Sample module for testing."""

def hello_world(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator class."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        """Subtract second number from first."""
        return a - b
''')
            
            # Configure documentation generation
            config = DocumentationConfig(
                project_root=project_root,
                docs_output_dir=docs_dir,
                project_name="Test Project",
                project_description="A test project for documentation generation",
                enabled_types=[
                    DocumentationType.README,
                    DocumentationType.API_DOCS,
                    DocumentationType.ARCHITECTURE
                ],
                analyze_code=True,
                validate_output=True,
                enable_caching=False  # Disable for predictable testing
            )
            
            # Initialize real components (not mocked for integration test)
            safety_validator = SafetyValidator()
            ast_analyzer = ASTAnalyzer(safety_validator=safety_validator)
            
            generator = DocumentationGenerator(
                config=config,
                ast_analyzer=ast_analyzer,
                safety_validator=safety_validator
            )
            
            # Generate documentation
            result = await generator.generate_documentation(
                target_files=[sample_file]
            )
            
            # Verify results
            assert result.success is True
            assert len(result.sections) > 0
            assert result.metadata.functions_analyzed >= 2  # hello_world, add, subtract
            assert result.metadata.classes_analyzed >= 1   # Calculator
            assert result.metadata.safety_score >= Decimal("0.8")
            
            # Check that sections were generated
            section_ids = [s.section_id for s in result.sections]
            assert any("overview" in sid for sid in section_ids)
            assert any("api" in sid for sid in section_ids)
            
            # Verify safety validation
            for section in result.sections:
                assert section.safety_validated is True
            
            # Check performance
            assert result.total_processing_time_ms > 0
            assert result.total_processing_time_ms < 10000  # Should be under 10 seconds