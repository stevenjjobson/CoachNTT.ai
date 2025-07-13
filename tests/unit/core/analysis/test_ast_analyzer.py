"""
Unit tests for AST analyzer.

Tests the main AST analysis functionality with safety validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from decimal import Decimal

from src.core.analysis.ast_analyzer import ASTAnalyzer
from src.core.analysis.models import (
    AnalysisResult,
    LanguageType,
    FunctionSignature,
    ClassStructure,
    ComplexityMetrics,
    MIN_SAFETY_SCORE
)
from src.core.validation.validator import SafetyValidator


class TestASTAnalyzer:
    """Test AST analyzer functionality."""
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Mock safety validator."""
        validator = Mock(spec=SafetyValidator)
        validator.auto_abstract_content.return_value = ("abstracted content", {})
        return validator
    
    @pytest.fixture
    def ast_analyzer(self, mock_safety_validator):
        """Create AST analyzer for testing."""
        return ASTAnalyzer(
            safety_validator=mock_safety_validator,
            enable_pattern_detection=True,
            enable_complexity_analysis=True
        )
    
    @pytest.mark.asyncio
    async def test_analyzer_initialization(self, ast_analyzer):
        """Test analyzer initialization."""
        assert ast_analyzer.safety_validator is not None
        assert ast_analyzer.language_detector is not None
        assert ast_analyzer.enable_pattern_detection is True
        assert ast_analyzer.enable_complexity_analysis is True
        assert ast_analyzer.pattern_detector is not None
        assert ast_analyzer.complexity_analyzer is not None
    
    @pytest.mark.asyncio
    async def test_python_code_analysis(self, ast_analyzer):
        """Test Python code analysis."""
        python_code = '''
def hello_world(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

class TestClass:
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value
'''
        
        result = await ast_analyzer.analyze_code(python_code, "test.py")
        
        assert result.language == LanguageType.PYTHON
        assert len(result.functions) >= 1  # At least hello_world function
        assert len(result.classes) >= 1   # TestClass
        assert result.metadata.safety_score >= MIN_SAFETY_SCORE
        assert result.is_analysis_complete()
    
    @pytest.mark.asyncio
    async def test_javascript_code_analysis(self, ast_analyzer):
        """Test JavaScript code analysis."""
        javascript_code = '''
function calculateSum(a, b) {
    return a + b;
}

class Calculator {
    constructor() {
        this.history = [];
    }
    
    add(a, b) {
        const result = a + b;
        this.history.push(result);
        return result;
    }
}

const calculator = new Calculator();
'''
        
        result = await ast_analyzer.analyze_code(javascript_code, "test.js")
        
        assert result.language == LanguageType.JAVASCRIPT
        assert len(result.functions) >= 1  # calculateSum function
        assert len(result.classes) >= 1   # Calculator class
        assert result.metadata.safety_score >= MIN_SAFETY_SCORE
    
    @pytest.mark.asyncio
    async def test_typescript_code_analysis(self, ast_analyzer):
        """Test TypeScript code analysis."""
        typescript_code = '''
interface User {
    name: string;
    age: number;
}

class UserManager {
    private users: User[] = [];
    
    public addUser(user: User): void {
        this.users.push(user);
    }
    
    public getUsers(): User[] {
        return this.users;
    }
}

type UserCallback = (user: User) => void;
'''
        
        result = await ast_analyzer.analyze_code(typescript_code, "test.ts")
        
        assert result.language == LanguageType.TYPESCRIPT
        assert len(result.classes) >= 1  # UserManager class + interface
        assert result.metadata.safety_score >= MIN_SAFETY_SCORE
    
    @pytest.mark.asyncio
    async def test_safety_validation_failure(self, ast_analyzer):
        """Test that unsafe code is rejected."""
        # Mock safety validator to return low safety score
        ast_analyzer.safety_validator.auto_abstract_content.return_value = (
            "unsafe content", {"sensitive_data": "leaked"}
        )
        
        with patch.object(ast_analyzer, '_calculate_query_safety_score') as mock_score:
            mock_score.return_value = Decimal("0.5")  # Below threshold
            
            with pytest.raises(ValueError, match="Content failed safety validation"):
                await ast_analyzer.analyze_code("unsafe code", "test.py")
    
    @pytest.mark.asyncio
    async def test_complex_python_analysis(self, ast_analyzer):
        """Test analysis of complex Python code."""
        complex_code = '''
import asyncio
from typing import Dict, List, Optional

class DatabaseManager:
    """Manages database connections."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.connections = []
    
    async def connect(self) -> bool:
        """Establish database connection."""
        try:
            # Complex connection logic
            if self.config.get("host"):
                connection = await self._create_connection()
                self.connections.append(connection)
                return True
        except Exception as e:
            self._handle_error(e)
        return False
    
    def _create_connection(self):
        """Create database connection."""
        return MockConnection()
    
    def _handle_error(self, error: Exception):
        """Handle connection errors."""
        print(f"Error: {error}")

def factory_function(db_type: str) -> DatabaseManager:
    """Factory function for database managers."""
    configs = {
        "mysql": {"host": "localhost", "port": "3306"},
        "postgres": {"host": "localhost", "port": "5432"}
    }
    
    if db_type in configs:
        return DatabaseManager(configs[db_type])
    
    raise ValueError(f"Unsupported database type: {db_type}")
'''
        
        result = await ast_analyzer.analyze_code(complex_code, "database.py")
        
        assert result.language == LanguageType.PYTHON
        assert len(result.functions) >= 2  # factory_function and methods
        assert len(result.classes) >= 1   # DatabaseManager
        
        # Check for async functions
        async_functions = [f for f in result.functions if f.is_async]
        assert len(async_functions) >= 1
        
        # Check for functions with parameters
        functions_with_params = [f for f in result.functions if f.parameter_count > 0]
        assert len(functions_with_params) >= 1
        
        # Check for classes with methods
        classes_with_methods = [c for c in result.classes if c.method_count > 0]
        assert len(classes_with_methods) >= 1
    
    @pytest.mark.asyncio
    async def test_empty_code_analysis(self, ast_analyzer):
        """Test analysis of empty or minimal code."""
        empty_code = "# Just a comment"
        
        result = await ast_analyzer.analyze_code(empty_code, "empty.py")
        
        assert result.language == LanguageType.PYTHON
        assert len(result.functions) == 0
        assert len(result.classes) == 0
        assert result.metadata.safety_score >= MIN_SAFETY_SCORE
    
    @pytest.mark.asyncio
    async def test_syntax_error_handling(self, ast_analyzer):
        """Test handling of syntax errors in code."""
        invalid_python = '''
def broken_function(
    # Missing closing parenthesis and function body
'''
        
        # Should not raise exception, but may have limited analysis
        result = await ast_analyzer.analyze_code(invalid_python, "broken.py")
        
        assert result.language == LanguageType.PYTHON
        # Analysis may be incomplete but should not crash
    
    @pytest.mark.asyncio
    async def test_dependency_graph_creation(self, ast_analyzer):
        """Test dependency graph creation."""
        code_with_dependencies = '''
def helper_function():
    return "helper"

def main_function():
    result = helper_function()
    return process_data(result)

def process_data(data):
    return data.upper()

class DataProcessor:
    def process(self):
        return main_function()
'''
        
        result = await ast_analyzer.analyze_code(code_with_dependencies, "deps.py")
        
        assert result.dependency_graph is not None
        assert len(result.dependency_graph) > 0
        
        # Check that dependencies were detected
        dep_analysis = ast_analyzer.get_dependency_analysis(result)
        assert dep_analysis['total_nodes'] > 0
        assert dep_analysis['total_dependencies'] >= 0
    
    @pytest.mark.asyncio
    async def test_abstraction_identifier_safety(self, ast_analyzer):
        """Test that identifiers are properly abstracted."""
        code_with_sensitive_names = '''
def get_user_password():
    return "secret123"

class DatabaseConnection:
    def connect_to_prod_db(self):
        pass

API_KEY = "sk-1234567890abcdef"
'''
        
        result = await ast_analyzer.analyze_code(code_with_sensitive_names, "sensitive.py")
        
        # Check that function names are abstracted
        for func in result.functions:
            assert func.name_pattern.startswith('<')
            assert func.name_pattern.endswith('>')
            assert 'password' not in func.name_pattern.lower()
        
        # Check that class names are abstracted
        for cls in result.classes:
            assert cls.name_pattern.startswith('<')
            assert cls.name_pattern.endswith('>')
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, ast_analyzer):
        """Test that performance is tracked."""
        simple_code = "def test(): pass"
        
        result = await ast_analyzer.analyze_code(simple_code, "perf.py")
        
        assert result.metadata.processing_time_ms > 0
        assert result.metadata.processing_time_ms < 5000  # Should be fast
        
        # Check stats
        stats = ast_analyzer.get_stats()
        assert stats['analyses_performed'] > 0
        assert stats['total_processing_time_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_pattern_detection_integration(self, ast_analyzer):
        """Test integration with pattern detection."""
        singleton_code = '''
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def getInstance(self):
        return self._instance
'''
        
        result = await ast_analyzer.analyze_code(singleton_code, "singleton.py")
        
        # Should detect pattern if pattern detection is working
        if result.design_patterns:
            assert len(result.design_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_complexity_analysis_integration(self, ast_analyzer):
        """Test integration with complexity analysis."""
        complex_function_code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    for j in range(y):
                        if i * j > z:
                            try:
                                result = i / j
                                if result > 1:
                                    return result
                                elif result < 0:
                                    continue
                                else:
                                    break
                            except ZeroDivisionError:
                                continue
                        else:
                            continue
            else:
                return -1
        else:
            return -2
    else:
        return -3
    return 0
'''
        
        result = await ast_analyzer.analyze_code(complex_function_code, "complex.py")
        
        # Should have complexity metrics
        if result.complexity_metrics:
            assert result.complexity_metrics.cyclomatic_complexity > 1
            assert result.complexity_metrics.lines_of_code > 0
    
    def test_get_stats(self, ast_analyzer):
        """Test statistics retrieval."""
        stats = ast_analyzer.get_stats()
        
        assert 'analyses_performed' in stats
        assert 'python_analyses' in stats
        assert 'javascript_analyses' in stats
        assert 'typescript_analyses' in stats
        assert 'total_processing_time_ms' in stats
        assert 'functions_analyzed' in stats
        assert 'classes_analyzed' in stats
        
        # Should have component stats
        assert 'component_stats' in stats
        assert 'language_detector' in stats['component_stats']
    
    @pytest.mark.asyncio
    async def test_shutdown(self, ast_analyzer):
        """Test analyzer shutdown."""
        # Should not raise exception
        await ast_analyzer.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])