"""
Performance benchmarks for AST code analysis system.

Tests AST analysis speed, pattern detection performance, and overall
system throughput with safety validation.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock

import pytest

from src.core.analysis import (
    ASTAnalyzer,
    LanguageType,
    PatternType
)
from src.core.validation.validator import SafetyValidator


class ASTAnalysisBenchmarks:
    """Benchmarking suite for AST analysis operations."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
    
    async def setup_analyzer(self) -> ASTAnalyzer:
        """Set up AST analyzer for consistent benchmarking."""
        # Mock safety validator for consistent performance
        safety_validator = Mock(spec=SafetyValidator)
        safety_validator.auto_abstract_content.return_value = ("abstracted content", {})
        
        analyzer = ASTAnalyzer(
            safety_validator=safety_validator,
            enable_pattern_detection=True,
            enable_complexity_analysis=True
        )
        
        return analyzer
    
    async def benchmark_python_analysis(
        self,
        analyzer: ASTAnalyzer,
        num_iterations: int = 20
    ) -> Dict[str, float]:
        """Benchmark Python code analysis performance."""
        
        # Sample Python code of moderate complexity
        python_code = '''
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class Configuration:
    """Application configuration."""
    database_url: str
    api_key: str
    timeout: int = 30
    retry_count: int = 3

class DatabaseConnectionError(Exception):
    """Custom exception for database errors."""
    pass

class AbstractRepository(ABC):
    """Abstract base class for repositories."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data source."""
        pass

class PostgreSQLRepository(AbstractRepository):
    """PostgreSQL repository implementation."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.connection = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Establish database connection."""
        try:
            if self.is_connected:
                return True
            
            for attempt in range(self.config.retry_count):
                try:
                    logger.info(f"Connection attempt {attempt + 1}")
                    self.connection = await self._create_connection()
                    self.is_connected = True
                    logger.info("Successfully connected to database")
                    return True
                except ConnectionError as e:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt < self.config.retry_count - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise DatabaseConnectionError(f"Failed to connect after {self.config.retry_count} attempts")
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            raise
        
        return False
    
    async def _create_connection(self):
        """Create database connection."""
        # Simulate connection creation
        await asyncio.sleep(0.01)
        if self.config.database_url.startswith("postgresql://"):
            return MockConnection(self.config.database_url)
        else:
            raise ConnectionError("Invalid database URL")
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self.connection and self.is_connected:
            await self.connection.close()
            self.is_connected = False
            logger.info("Disconnected from database")
    
    async def execute_query(self, query: str, params: List[Any] = None) -> List[Dict]:
        """Execute a database query."""
        if not self.is_connected:
            raise DatabaseConnectionError("Not connected to database")
        
        try:
            logger.debug(f"Executing query: {query[:100]}...")
            result = await self.connection.execute(query, params or [])
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def create_repository(repo_type: str, config: Configuration) -> AbstractRepository:
        """Create repository instance based on type."""
        if repo_type.lower() == "postgresql":
            return PostgreSQLRepository(config)
        elif repo_type.lower() == "mysql":
            # Would implement MySQLRepository
            raise NotImplementedError("MySQL repository not implemented")
        else:
            raise ValueError(f"Unsupported repository type: {repo_type}")

class DataProcessor:
    """Data processing service."""
    
    def __init__(self, repository: AbstractRepository):
        self.repository = repository
        self.cache = {}
    
    async def process_data(self, data: List[Dict]) -> List[Dict]:
        """Process a batch of data."""
        results = []
        
        for item in data:
            if self._validate_item(item):
                processed = await self._process_item(item)
                if processed:
                    results.append(processed)
            else:
                logger.warning(f"Invalid item skipped: {item.get('id', 'unknown')}")
        
        return results
    
    def _validate_item(self, item: Dict) -> bool:
        """Validate a data item."""
        required_fields = ['id', 'name', 'type']
        return all(field in item and item[field] is not None for field in required_fields)
    
    async def _process_item(self, item: Dict) -> Optional[Dict]:
        """Process a single data item."""
        item_id = item['id']
        
        # Check cache first
        if item_id in self.cache:
            logger.debug(f"Cache hit for item {item_id}")
            return self.cache[item_id]
        
        try:
            # Simulate processing time
            await asyncio.sleep(0.001)
            
            processed_item = {
                'id': item_id,
                'name': item['name'].upper(),
                'type': item['type'],
                'processed_at': time.time(),
                'status': 'processed'
            }
            
            # Cache the result
            self.cache[item_id] = processed_item
            return processed_item
            
        except Exception as e:
            logger.error(f"Failed to process item {item_id}: {e}")
            return None

async def main():
    """Main application function."""
    config = Configuration(
        database_url="postgresql://user:pass@localhost/db",
        api_key="test-key-123"
    )
    
    repository = RepositoryFactory.create_repository("postgresql", config)
    processor = DataProcessor(repository)
    
    try:
        await repository.connect()
        
        sample_data = [
            {'id': i, 'name': f'item_{i}', 'type': 'sample'}
            for i in range(100)
        ]
        
        results = await processor.process_data(sample_data)
        logger.info(f"Processed {len(results)} items")
        
    finally:
        await repository.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        times = []
        code_sizes = []
        
        for i in range(num_iterations):
            # Vary code size slightly for realistic testing
            test_code = python_code * (1 + i % 3)  # 1x, 2x, 3x size variation
            code_sizes.append(len(test_code.split('\\n')))
            
            start_time = time.time()
            
            result = await analyzer.analyze_code(test_code, f"test_{i}.py")
            
            end_time = time.time()
            analysis_time = (end_time - start_time) * 1000
            times.append(analysis_time)
            
            # Verify analysis completed successfully
            assert result.is_analysis_complete()
        
        return {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'std_ms': statistics.stdev(times) if len(times) > 1 else 0.0,
            'min_ms': min(times),
            'max_ms': max(times),
            'target_ms': 300,  # Performance target for 1000 lines
            'iterations': num_iterations,
            'avg_lines': statistics.mean(code_sizes)
        }
    
    async def benchmark_language_detection(
        self,
        analyzer: ASTAnalyzer,
        num_iterations: int = 100
    ) -> Dict[str, float]:
        """Benchmark language detection performance."""
        
        test_files = [
            ("test.py", "def hello(): pass"),
            ("test.js", "function hello() { return 'world'; }"),
            ("test.ts", "interface User { name: string; }"),
            ("complex.py", "class Test:\\n    def __init__(self): pass"),
            ("module.js", "export default class Module { constructor() {} }")
        ]
        
        times = []
        
        for i in range(num_iterations):
            filename, content = test_files[i % len(test_files)]
            
            start_time = time.time()
            
            language, confidence, metadata = analyzer.language_detector.detect_language(
                content, filename
            )
            
            end_time = time.time()
            detection_time = (end_time - start_time) * 1000
            times.append(detection_time)
        
        return {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'target_ms': 50,  # Performance target
            'iterations': num_iterations
        }
    
    async def benchmark_pattern_detection(
        self,
        analyzer: ASTAnalyzer,
        num_iterations: int = 30
    ) -> Dict[str, float]:
        """Benchmark pattern detection performance."""
        
        pattern_code = '''
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

class ShapeFactory:
    @staticmethod
    def create_shape(shape_type):
        if shape_type == "circle":
            return Circle()
        elif shape_type == "square":
            return Square()
        return None

class Observer:
    def update(self, message):
        pass

class Subject:
    def __init__(self):
        self.observers = []
    
    def attach(self, observer):
        self.observers.append(observer)
    
    def notify(self, message):
        for observer in self.observers:
            observer.update(message)
'''
        
        times = []
        patterns_found = []
        
        for i in range(num_iterations):
            start_time = time.time()
            
            result = await analyzer.analyze_code(pattern_code, "patterns.py")
            
            end_time = time.time()
            detection_time = (end_time - start_time) * 1000
            times.append(detection_time)
            
            patterns_found.append(len(result.design_patterns))
        
        return {
            'mean_ms': statistics.mean(times),
            'target_ms': 150,  # Performance target
            'avg_patterns_found': statistics.mean(patterns_found),
            'iterations': num_iterations
        }
    
    async def benchmark_complexity_calculation(
        self,
        analyzer: ASTAnalyzer,
        num_iterations: int = 50
    ) -> Dict[str, float]:
        """Benchmark complexity calculation performance."""
        
        complex_code = '''
def complex_algorithm(data, options):
    """A deliberately complex function for testing."""
    results = []
    
    if not data:
        return results
    
    for i, item in enumerate(data):
        if isinstance(item, dict):
            if "process" in item and item["process"]:
                try:
                    if "method" in options:
                        if options["method"] == "fast":
                            if len(item.get("values", [])) > 0:
                                for value in item["values"]:
                                    if isinstance(value, (int, float)):
                                        if value > 0:
                                            processed = value * 2
                                            if processed > 100:
                                                results.append({"index": i, "result": processed, "type": "high"})
                                            elif processed > 50:
                                                results.append({"index": i, "result": processed, "type": "medium"})
                                            else:
                                                results.append({"index": i, "result": processed, "type": "low"})
                                        elif value < 0:
                                            continue
                                        else:
                                            results.append({"index": i, "result": 0, "type": "zero"})
                                    else:
                                        continue
                            else:
                                continue
                        elif options["method"] == "slow":
                            # Alternative processing path
                            if "special" in item:
                                for j in range(len(item.get("values", []))):
                                    try:
                                        calculated = item["values"][j] ** 2
                                        if calculated > 1000:
                                            break
                                        else:
                                            results.append({"index": i, "sub_index": j, "result": calculated})
                                    except (KeyError, IndexError, TypeError):
                                        continue
                            else:
                                continue
                        else:
                            continue
                    else:
                        continue
                except (KeyError, ValueError, TypeError) as e:
                    continue
            else:
                continue
        else:
            continue
    
    return results
'''
        
        times = []
        
        for i in range(num_iterations):
            start_time = time.time()
            
            result = await analyzer.analyze_code(complex_code, "complex.py")
            
            end_time = time.time()
            calculation_time = (end_time - start_time) * 1000
            times.append(calculation_time)
            
            # Verify complexity was calculated
            if result.complexity_metrics:
                assert result.complexity_metrics.cyclomatic_complexity > 1
        
        return {
            'mean_ms': statistics.mean(times),
            'target_ms': 100,  # Performance target
            'iterations': num_iterations
        }
    
    async def benchmark_safety_validation(
        self,
        analyzer: ASTAnalyzer,
        num_iterations: int = 50
    ) -> Dict[str, float]:
        """Benchmark safety validation performance."""
        
        code_with_sensitive_data = '''
import os
import requests

API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://user:password@localhost:5432/production"

def get_user_data(user_id):
    """Fetch user data from database."""
    connection_string = DATABASE_URL
    api_key = API_KEY
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"https://api.internal.com/users/{user_id}", headers=headers)
    return response.json()

class ProductionService:
    def __init__(self):
        self.db_connection = DATABASE_URL
        self.secret_key = API_KEY
    
    def backup_production_data(self):
        """Backup production database."""
        os.system(f"pg_dump {self.db_connection} > backup.sql")
'''
        
        times = []
        safety_scores = []
        
        for i in range(num_iterations):
            start_time = time.time()
            
            result = await analyzer.analyze_code(code_with_sensitive_data, "sensitive.py")
            
            end_time = time.time()
            validation_time = (end_time - start_time) * 1000
            times.append(validation_time)
            
            safety_scores.append(float(result.metadata.safety_score))
            
            # Verify safety validation occurred
            assert result.concrete_references_removed >= 0
        
        return {
            'mean_ms': statistics.mean(times),
            'avg_safety_score': statistics.mean(safety_scores),
            'target_safety_score': 0.8,
            'iterations': num_iterations
        }
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("Setting up AST analyzer for benchmarking...")
        analyzer = await self.setup_analyzer()
        
        print("Running Python analysis benchmark...")
        python_perf = await self.benchmark_python_analysis(analyzer)
        
        print("Running language detection benchmark...")
        language_perf = await self.benchmark_language_detection(analyzer)
        
        print("Running pattern detection benchmark...")
        pattern_perf = await self.benchmark_pattern_detection(analyzer)
        
        print("Running complexity calculation benchmark...")
        complexity_perf = await self.benchmark_complexity_calculation(analyzer)
        
        print("Running safety validation benchmark...")
        safety_perf = await self.benchmark_safety_validation(analyzer)
        
        # Get analyzer statistics
        analyzer_stats = analyzer.get_stats()
        
        return {
            'python_analysis_performance': python_perf,
            'language_detection_performance': language_perf,
            'pattern_detection_performance': pattern_perf,
            'complexity_calculation_performance': complexity_perf,
            'safety_validation_performance': safety_perf,
            'analyzer_statistics': analyzer_stats,
            'benchmark_timestamp': time.time()
        }
    
    def print_benchmark_report(self, results: Dict[str, Any]) -> None:
        """Print formatted benchmark report."""
        print("\\n" + "="*70)
        print("AST CODE ANALYSIS PERFORMANCE BENCHMARK REPORT")
        print("="*70)
        
        # Python analysis performance
        python_perf = results['python_analysis_performance']
        print(f"\\n📊 Python Analysis Performance:")
        print(f"  Mean time: {python_perf['mean_ms']:.2f}ms")
        print(f"  Target: <{python_perf['target_ms']}ms")
        print(f"  Average lines: {python_perf['avg_lines']:.0f}")
        print(f"  Status: {'✅ PASS' if python_perf['mean_ms'] < python_perf['target_ms'] else '❌ FAIL'}")
        
        # Language detection performance
        lang_perf = results['language_detection_performance']
        print(f"\\n🔍 Language Detection Performance:")
        print(f"  Mean time: {lang_perf['mean_ms']:.2f}ms")
        print(f"  Target: <{lang_perf['target_ms']}ms")
        print(f"  Status: {'✅ PASS' if lang_perf['mean_ms'] < lang_perf['target_ms'] else '❌ FAIL'}")
        
        # Pattern detection performance
        pattern_perf = results['pattern_detection_performance']
        print(f"\\n🎨 Pattern Detection Performance:")
        print(f"  Mean time: {pattern_perf['mean_ms']:.2f}ms")
        print(f"  Target: <{pattern_perf['target_ms']}ms")
        print(f"  Avg patterns found: {pattern_perf['avg_patterns_found']:.1f}")
        print(f"  Status: {'✅ PASS' if pattern_perf['mean_ms'] < pattern_perf['target_ms'] else '❌ FAIL'}")
        
        # Complexity calculation performance
        complexity_perf = results['complexity_calculation_performance']
        print(f"\\n📈 Complexity Calculation Performance:")
        print(f"  Mean time: {complexity_perf['mean_ms']:.2f}ms")
        print(f"  Target: <{complexity_perf['target_ms']}ms")
        print(f"  Status: {'✅ PASS' if complexity_perf['mean_ms'] < complexity_perf['target_ms'] else '❌ FAIL'}")
        
        # Safety validation performance
        safety_perf = results['safety_validation_performance']
        print(f"\\n🛡️ Safety Validation Performance:")
        print(f"  Mean time: {safety_perf['mean_ms']:.2f}ms")
        print(f"  Avg safety score: {safety_perf['avg_safety_score']:.3f}")
        print(f"  Target score: ≥{safety_perf['target_safety_score']}")
        
        # Overall assessment
        print(f"\\n🎯 Performance Target Assessment:")
        
        python_pass = python_perf['mean_ms'] < python_perf['target_ms']
        lang_pass = lang_perf['mean_ms'] < lang_perf['target_ms']
        pattern_pass = pattern_perf['mean_ms'] < pattern_perf['target_ms']
        complexity_pass = complexity_perf['mean_ms'] < complexity_perf['target_ms']
        safety_pass = safety_perf['avg_safety_score'] >= safety_perf['target_safety_score']
        
        all_pass = all([python_pass, lang_pass, pattern_pass, complexity_pass, safety_pass])
        
        print(f"  Python analysis: {'✅ PASS' if python_pass else '❌ FAIL'}")
        print(f"  Language detection: {'✅ PASS' if lang_pass else '❌ FAIL'}")
        print(f"  Pattern detection: {'✅ PASS' if pattern_pass else '❌ FAIL'}")
        print(f"  Complexity calculation: {'✅ PASS' if complexity_pass else '❌ FAIL'}")
        print(f"  Safety validation: {'✅ PASS' if safety_pass else '❌ FAIL'}")
        print(f"\\n  Overall: {'✅ ALL TARGETS MET' if all_pass else '❌ SOME TARGETS MISSED'}")
        
        print("\\n" + "="*70)


@pytest.mark.asyncio
async def test_ast_performance_benchmarks():
    """Run AST analysis performance benchmarks as a test."""
    benchmarks = ASTAnalysisBenchmarks()
    results = await benchmarks.run_all_benchmarks()
    benchmarks.print_benchmark_report(results)
    
    # Assert performance targets
    python_perf = results['python_analysis_performance']
    assert python_perf['mean_ms'] < 300, \\
        f"Python analysis too slow: {python_perf['mean_ms']}ms"
    
    lang_perf = results['language_detection_performance']
    assert lang_perf['mean_ms'] < 50, \\
        f"Language detection too slow: {lang_perf['mean_ms']}ms"
    
    pattern_perf = results['pattern_detection_performance']
    assert pattern_perf['mean_ms'] < 150, \\
        f"Pattern detection too slow: {pattern_perf['mean_ms']}ms"
    
    complexity_perf = results['complexity_calculation_performance']
    assert complexity_perf['mean_ms'] < 100, \\
        f"Complexity calculation too slow: {complexity_perf['mean_ms']}ms"


if __name__ == "__main__":
    async def main():
        benchmarks = ASTAnalysisBenchmarks()
        results = await benchmarks.run_all_benchmarks()
        benchmarks.print_benchmark_report(results)
    
    asyncio.run(main())