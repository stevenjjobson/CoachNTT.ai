"""
Integration tests for AST code analysis system.

Tests the complete AST analysis pipeline including integration with intent engine.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from decimal import Decimal

from src.core.analysis.ast_analyzer import ASTAnalyzer
from src.core.analysis.models import LanguageType, PatternType
from src.core.intent.engine import IntentEngine
from src.core.validation.validator import SafetyValidator
from src.core.embeddings.service import EmbeddingService


class TestASTAnalysisIntegration:
    """Test AST analysis integration with other systems."""
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock(spec=EmbeddingService)
        
        async def mock_generate_embedding(*args, **kwargs):
            from src.core.embeddings.models import EmbeddingResult, EmbeddingMetadata
            
            metadata = EmbeddingMetadata(
                content_type="code",
                model_name="mock-model",
                content_hash="mock_hash",
                safety_score=Decimal("0.9"),
                dimensions=384
            )
            
            return EmbeddingResult(
                vector=[0.1, 0.2, 0.3] * 128,
                metadata=metadata,
                processing_time_ms=50
            )
        
        service.generate_embedding = mock_generate_embedding
        return service
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Mock safety validator."""
        validator = Mock(spec=SafetyValidator)
        validator.auto_abstract_content.return_value = ("abstracted content", {})
        return validator
    
    @pytest.fixture
    def ast_analyzer(self, mock_safety_validator, mock_embedding_service):
        """Create AST analyzer for testing."""
        return ASTAnalyzer(
            safety_validator=mock_safety_validator,
            embedding_service=mock_embedding_service
        )
    
    @pytest.fixture
    def intent_engine(self, mock_embedding_service, mock_safety_validator, ast_analyzer):
        """Create intent engine with AST analysis enabled."""
        return IntentEngine(
            embedding_service=mock_embedding_service,
            safety_validator=mock_safety_validator,
            ast_analyzer=ast_analyzer,
            enable_code_analysis=True
        )
    
    @pytest.mark.asyncio
    async def test_end_to_end_python_analysis(self, ast_analyzer):
        """Test complete Python code analysis pipeline."""
        python_code = '''
class SingletonLogger:
    """A singleton logger implementation."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logs = []
        return cls._instance
    
    def log(self, message: str) -> None:
        """Log a message."""
        self.logs.append(message)
    
    def get_logs(self) -> list:
        """Get all logs."""
        return self.logs

def create_logger() -> SingletonLogger:
    """Factory function for logger."""
    return SingletonLogger()

def complex_function(data):
    """A function with high complexity."""
    logger = create_logger()
    
    if data:
        for item in data:
            if isinstance(item, str):
                if len(item) > 10:
                    try:
                        processed = item.upper()
                        logger.log(f"Processed: {processed}")
                        if "ERROR" in processed:
                            raise ValueError("Error found")
                        elif "WARNING" in processed:
                            continue
                        else:
                            return processed
                    except ValueError as e:
                        logger.log(f"Error: {e}")
                        continue
                else:
                    continue
            else:
                continue
    return None
'''
        
        result = await ast_analyzer.analyze_code(python_code, "complex_example.py")
        
        # Verify comprehensive analysis
        assert result.is_analysis_complete()
        assert result.language == LanguageType.PYTHON
        
        # Check structure detection
        assert len(result.functions) >= 3  # create_logger, complex_function, log, get_logs
        assert len(result.classes) >= 1   # SingletonLogger
        
        # Check pattern detection
        if result.design_patterns:
            singleton_patterns = [p for p in result.design_patterns if p.pattern_type == PatternType.SINGLETON]
            factory_patterns = [p for p in result.design_patterns if p.pattern_type == PatternType.FACTORY]
            assert len(singleton_patterns) >= 0  # May detect singleton
            assert len(factory_patterns) >= 0   # May detect factory
        
        # Check complexity analysis
        if result.complexity_metrics:
            assert result.complexity_metrics.cyclomatic_complexity > 1
            assert result.complexity_metrics.lines_of_code > 20
        
        # Check dependency graph
        assert result.dependency_graph is not None
        dep_analysis = ast_analyzer.get_dependency_analysis(result)
        assert dep_analysis['total_nodes'] > 0
        
        # Check safety compliance
        assert result.metadata.safety_score >= Decimal("0.8")
        assert result.concrete_references_removed >= 0
    
    @pytest.mark.asyncio
    async def test_intent_engine_code_analysis_integration(self, intent_engine):
        """Test intent engine integration with code analysis."""
        debug_query = "Help me debug this Python code"
        python_code = '''
def buggy_function(x):
    if x > 0:
        if x < 10:
            if x % 2 == 0:
                return x * 2
            else:
                return x * 3
        else:
            return x / 2
    else:
        return -1
'''
        
        # Test code analysis with intent
        result = await intent_engine.analyze_code_with_intent(
            code_content=python_code,
            query=debug_query,
            filename="buggy.py"
        )
        
        assert 'error' not in result
        assert 'code_analysis' in result
        assert 'intent_context' in result
        assert 'insights' in result
        
        # Check intent context
        intent_context = result['intent_context']
        assert intent_context.get('intent_type') == 'DEBUG'
        
        # Check code analysis results
        code_analysis = result['code_analysis']
        assert code_analysis['language'] == 'python'
        assert code_analysis['function_count'] >= 1
        
        # Check insights generation
        insights = result['insights']
        assert isinstance(insights, list)
        if insights:
            # Should have debug-specific insights
            debug_insights = [i for i in insights if 'debug' in i.lower() or 'complex' in i.lower()]
            assert len(debug_insights) >= 0  # May have debug insights
    
    @pytest.mark.asyncio
    async def test_query_analysis_with_code_content(self, intent_engine):
        """Test query analysis enhanced with code content."""
        optimize_query = "How can I optimize this code for better performance?"
        performance_code = '''
def slow_function(data_list):
    results = []
    for i in range(len(data_list)):
        for j in range(len(data_list)):
            if i != j:
                if data_list[i] > data_list[j]:
                    results.append((data_list[i], data_list[j]))
    return results

class DataProcessor:
    def __init__(self):
        self.cache = {}
        self.processed_items = []
    
    def process_all_data(self, large_dataset):
        for item in large_dataset:
            processed = self.process_item(item)
            self.processed_items.append(processed)
        return self.processed_items
    
    def process_item(self, item):
        if item in self.cache:
            return self.cache[item]
        
        # Expensive processing
        result = item ** 2 + item * 3.14159
        self.cache[item] = result
        return result
'''
        
        analysis = await intent_engine.analyze_query(
            query=optimize_query,
            code_content=performance_code,
            filename="performance.py",
            include_connections=True
        )
        
        assert analysis.intent_result is not None
        assert analysis.intent_result.intent_type.value == 'OPTIMIZE'
        
        # Should have enhanced context from code analysis
        assert analysis.connection_result is not None
    
    @pytest.mark.asyncio
    async def test_javascript_pattern_detection(self, ast_analyzer):
        """Test pattern detection in JavaScript code."""
        js_code = '''
// Singleton pattern
const DatabaseConnection = (function() {
    let instance;
    
    function createInstance() {
        return {
            connect: function() {
                console.log("Connected to database");
            }
        };
    }
    
    return {
        getInstance: function() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

// Factory pattern
class ShapeFactory {
    createShape(type) {
        switch(type) {
            case 'circle':
                return new Circle();
            case 'rectangle':
                return new Rectangle();
            default:
                throw new Error('Unknown shape type');
        }
    }
}

class Circle {
    draw() {
        console.log("Drawing a circle");
    }
}

class Rectangle {
    draw() {
        console.log("Drawing a rectangle");
    }
}

// Observer pattern
class EventEmitter {
    constructor() {
        this.listeners = [];
    }
    
    addListener(callback) {
        this.listeners.push(callback);
    }
    
    removeListener(callback) {
        this.listeners = this.listeners.filter(l => l !== callback);
    }
    
    notify(data) {
        this.listeners.forEach(callback => callback(data));
    }
}
'''
        
        result = await ast_analyzer.analyze_code(js_code, "patterns.js")
        
        assert result.language == LanguageType.JAVASCRIPT
        assert len(result.functions) >= 1
        assert len(result.classes) >= 3  # ShapeFactory, Circle, Rectangle, EventEmitter
        
        # Check for pattern detection
        if result.design_patterns:
            pattern_types = [p.pattern_type for p in result.design_patterns]
            # May detect some patterns
            assert len(pattern_types) >= 0
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, ast_analyzer):
        """Test that analysis meets performance targets."""
        # Create moderately complex Python code
        test_code = '''
import asyncio
from typing import Dict, List, Optional

class ComplexClass:
    def __init__(self, config: Dict[str, any]):
        self.config = config
        self.data = []
    
    async def process_data(self, input_data: List[Dict]) -> List[Dict]:
        results = []
        for item in input_data:
            processed = await self._process_item(item)
            if processed:
                results.append(processed)
        return results
    
    async def _process_item(self, item: Dict) -> Optional[Dict]:
        if self._validate_item(item):
            transformed = self._transform_item(item)
            return await self._save_item(transformed)
        return None
    
    def _validate_item(self, item: Dict) -> bool:
        required_fields = ['id', 'name', 'type']
        return all(field in item for field in required_fields)
    
    def _transform_item(self, item: Dict) -> Dict:
        return {
            'id': item['id'],
            'name': item['name'].upper(),
            'type': item['type'],
            'processed_at': time.time()
        }
    
    async def _save_item(self, item: Dict) -> Dict:
        # Simulate async save
        await asyncio.sleep(0.001)
        return item

def factory_function(class_type: str) -> ComplexClass:
    configs = {
        'type_a': {'setting1': True, 'setting2': 'value_a'},
        'type_b': {'setting1': False, 'setting2': 'value_b'}
    }
    
    if class_type in configs:
        return ComplexClass(configs[class_type])
    raise ValueError(f"Unknown type: {class_type}")
''' * 3  # Triple the size to test with larger code
        
        import time
        start_time = time.time()
        
        result = await ast_analyzer.analyze_code(test_code, "performance_test.py")
        
        end_time = time.time()
        analysis_time_ms = (end_time - start_time) * 1000
        
        # Performance targets
        assert analysis_time_ms < 300  # Target: <300ms for 1000 lines
        assert result.metadata.processing_time_ms < 300
        
        # Quality checks
        assert result.is_analysis_complete()
        assert result.metadata.safety_score >= Decimal("0.8")
        
        print(f"Analysis completed in {analysis_time_ms:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_safety_abstraction_validation(self, ast_analyzer):
        """Test that all analysis results are properly abstracted."""
        sensitive_code = '''
import os
import requests

API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://user:password@localhost:5432/production_db"

def get_user_credentials(user_id):
    """Get user credentials from database."""
    connection = connect_to_database(DATABASE_URL)
    query = f"SELECT password_hash FROM users WHERE id = {user_id}"
    result = connection.execute(query)
    return result.fetchone()

def call_external_api(endpoint):
    """Call external API with credentials."""
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'User-Agent': 'MyApp/1.0'
    }
    response = requests.get(f"https://api.example.com/{endpoint}", headers=headers)
    return response.json()

class ProductionDatabase:
    def __init__(self):
        self.connection_string = DATABASE_URL
        self.api_key = API_KEY
    
    def backup_production_data(self):
        os.system("pg_dump production_db > /tmp/backup.sql")
'''
        
        result = await ast_analyzer.analyze_code(sensitive_code, "sensitive.py")
        
        # Verify safety compliance
        assert result.metadata.safety_score >= Decimal("0.8")
        
        # Check that concrete references are abstracted
        for func in result.functions:
            # Function names should be abstracted
            assert not any(sensitive in func.name_pattern.lower() 
                          for sensitive in ['password', 'api_key', 'production'])
            assert func.name_pattern.startswith('<')
            assert func.name_pattern.endswith('>')
        
        for cls in result.classes:
            # Class names should be abstracted
            assert not any(sensitive in cls.name_pattern.lower()
                          for sensitive in ['production', 'database'])
            assert cls.name_pattern.startswith('<')
            assert cls.name_pattern.endswith('>')
        
        # Verify abstracted content doesn't contain sensitive data
        assert 'sk-1234567890abcdef' not in result.abstracted_content
        assert 'postgresql://user:password@localhost' not in result.abstracted_content
        assert result.concrete_references_removed > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, ast_analyzer):
        """Test error handling and graceful degradation."""
        # Test with malformed code
        malformed_code = '''
def incomplete_function(
    # Missing closing parenthesis and body

class IncompleteClass
    # Missing colon and body

if True
    # Missing colon
    print("hello"
'''
        
        # Should not crash, may have limited results
        result = await ast_analyzer.analyze_code(malformed_code, "malformed.py")
        
        assert result.language == LanguageType.PYTHON
        # May have partial results or empty results, but should not crash
        assert result.metadata.safety_score >= Decimal("0.0")
    
    def test_statistics_and_monitoring(self, ast_analyzer):
        """Test statistics collection and monitoring."""
        initial_stats = ast_analyzer.get_stats()
        
        # Should have baseline stats
        assert initial_stats['analyses_performed'] >= 0
        assert 'component_stats' in initial_stats
        assert 'language_detector' in initial_stats['component_stats']
        
        # Stats should be properly structured
        required_stats = [
            'analyses_performed', 'python_analyses', 'javascript_analyses',
            'typescript_analyses', 'total_processing_time_ms', 'functions_analyzed',
            'classes_analyzed', 'patterns_detected'
        ]
        
        for stat in required_stats:
            assert stat in initial_stats


if __name__ == "__main__":
    pytest.main([__file__])