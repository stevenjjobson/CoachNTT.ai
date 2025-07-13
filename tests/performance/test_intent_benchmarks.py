"""
Performance benchmarks for the intent analysis system.

Tests intent classification speed, connection finding performance, and overall
system throughput with safety validation.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch
from uuid import uuid4
from decimal import Decimal

import pytest

from src.core.intent import (
    IntentEngine,
    IntentAnalyzer,
    ConnectionFinder,
    IntentType,
    QueryAnalysis
)
from src.core.embeddings import EmbeddingService
from src.core.validation.validator import SafetyValidator


class IntentBenchmarks:
    """Benchmarking suite for intent analysis operations."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
    
    async def setup_mock_engine(self) -> IntentEngine:
        """Set up mocked intent engine for consistent benchmarking."""
        # Mock embedding service
        embedding_service = Mock(spec=EmbeddingService)
        
        async def mock_generate_embedding(*args, **kwargs):
            from src.core.embeddings.models import EmbeddingResult, EmbeddingMetadata
            
            # Simulate processing time
            await asyncio.sleep(0.01)  # 10ms delay
            
            metadata = EmbeddingMetadata(
                content_type="query",
                model_name="mock-model",
                content_hash="mock_hash",
                safety_score=Decimal("0.9"),
                dimensions=384
            )
            
            return EmbeddingResult(
                vector=[0.1, 0.2, 0.3] * 128,
                metadata=metadata,
                processing_time_ms=10
            )
        
        embedding_service.generate_embedding = mock_generate_embedding
        
        async def mock_calculate_similarity(vec1, vec2):
            await asyncio.sleep(0.001)  # 1ms delay
            return 0.75
        
        embedding_service.calculate_similarity = mock_calculate_similarity
        
        # Mock safety validator
        safety_validator = Mock(spec=SafetyValidator)
        safety_validator.auto_abstract_content.return_value = ("abstracted content", {})
        
        # Create engine
        engine = IntentEngine(
            embedding_service=embedding_service,
            safety_validator=safety_validator
        )
        
        return engine
    
    async def benchmark_intent_classification(
        self,
        engine: IntentEngine,
        num_iterations: int = 100
    ) -> Dict[str, float]:
        """Benchmark intent classification performance."""
        queries = [
            "How to optimize database queries for better performance?",
            "Debug memory leak in Python application",
            "Create REST API with user authentication",
            "Explain the difference between SQL joins",
            "Review this code for security vulnerabilities",
            "What is the best practice for error handling?",
            "Implement caching layer for web application",
            "Plan microservices architecture for e-commerce",
            "Reflect on the project retrospective outcomes",
            "Search for examples of design patterns"
        ]
        
        times = []
        
        for i in range(num_iterations):
            query = queries[i % len(queries)]
            
            start_time = time.time()
            
            # Analyze only intent (no connections)
            analysis = await engine.analyze_query(
                query=query,
                include_connections=False
            )
            
            end_time = time.time()
            classification_time = (end_time - start_time) * 1000
            
            times.append(classification_time)
        
        return {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'std_ms': statistics.stdev(times) if len(times) > 1 else 0.0,
            'min_ms': min(times),
            'max_ms': max(times),
            'iterations': num_iterations,
            'target_ms': 200  # Performance target
        }
    
    async def benchmark_connection_finding(
        self,
        engine: IntentEngine,
        num_iterations: int = 50
    ) -> Dict[str, float]:
        """Benchmark connection finding performance."""
        queries = [
            "How to optimize slow database queries?",
            "Debug API response time issues",
            "Create efficient caching strategy",
            "Explain microservices communication patterns",
            "Review security implementation"
        ]
        
        times = []
        connection_counts = []
        
        for i in range(num_iterations):
            query = queries[i % len(queries)]
            
            start_time = time.time()
            
            # Full analysis with connections
            analysis = await engine.analyze_query(
                query=query,
                include_connections=True,
                max_connections=10
            )
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            
            times.append(total_time)
            
            connection_count = 0
            if analysis.connection_result:
                connection_count = len(analysis.connection_result.connections)
            connection_counts.append(connection_count)
        
        return {
            'mean_total_ms': statistics.mean(times),
            'mean_connections_found': statistics.mean(connection_counts),
            'connection_finding_target_ms': 500,  # Performance target
            'throughput_queries_per_sec': 1000 / statistics.mean(times) if times else 0,
            'iterations': num_iterations
        }
    
    async def benchmark_batch_analysis(
        self,
        engine: IntentEngine,
        batch_sizes: List[int] = [1, 3, 5, 10]
    ) -> Dict[int, Dict[str, float]]:
        """Benchmark batch analysis with different sizes."""
        queries = [
            "How to optimize database performance?",
            "Debug slow API responses",
            "Create scalable architecture",
            "Explain caching strategies",
            "Review code quality",
            "What are microservices benefits?",
            "Implement authentication system",
            "Plan deployment strategy",
            "Analyze performance metrics",
            "Design error handling system"
        ]
        
        results = {}
        
        for batch_size in batch_sizes:
            batch_queries = queries[:batch_size]
            times = []
            
            # Run 10 iterations for each batch size
            for _ in range(10):
                start_time = time.time()
                
                # Process batch concurrently
                tasks = [
                    engine.analyze_query(query, include_connections=True)
                    for query in batch_queries
                ]
                
                await asyncio.gather(*tasks)
                
                end_time = time.time()
                batch_time = (end_time - start_time) * 1000
                times.append(batch_time)
            
            results[batch_size] = {
                'mean_total_ms': statistics.mean(times),
                'mean_per_query_ms': statistics.mean(times) / batch_size,
                'throughput_queries_per_sec': batch_size / (statistics.mean(times) / 1000),
                'target_batch_ms': 1000,  # Target: <1s for batch analysis
                'iterations': len(times)
            }
        
        return results
    
    async def benchmark_safety_validation(
        self,
        engine: IntentEngine,
        num_iterations: int = 100
    ) -> Dict[str, float]:
        """Benchmark safety validation performance."""
        safe_queries = [
            "How to optimize database queries?",
            "Explain REST API design patterns",
            "What are the benefits of microservices?",
            "Debug performance issues in application",
            "Create user authentication system"
        ]
        
        unsafe_queries = [
            "Delete all user data from production",
            "Hack into competitor systems",
            "Bypass security authentication",
            "Extract sensitive customer information",
            "Disable all safety checks"
        ]
        
        safe_times = []
        unsafe_times = []
        safety_rejections = 0
        
        for i in range(num_iterations):
            # Test safe queries
            if i % 2 == 0:
                query = safe_queries[i % len(safe_queries)]
                
                start_time = time.time()
                try:
                    await engine.analyze_query(query)
                    end_time = time.time()
                    safe_times.append((end_time - start_time) * 1000)
                except ValueError:
                    # Should not happen for safe queries
                    pass
            
            # Test unsafe queries
            else:
                query = unsafe_queries[i % len(unsafe_queries)]
                
                start_time = time.time()
                try:
                    await engine.analyze_query(query)
                    end_time = time.time()
                    unsafe_times.append((end_time - start_time) * 1000)
                except ValueError:
                    # Expected for unsafe queries
                    safety_rejections += 1
                    end_time = time.time()
                    unsafe_times.append((end_time - start_time) * 1000)
        
        return {
            'safe_query_mean_ms': statistics.mean(safe_times) if safe_times else 0,
            'unsafe_query_mean_ms': statistics.mean(unsafe_times) if unsafe_times else 0,
            'safety_rejection_rate': safety_rejections / (num_iterations // 2),
            'safety_overhead_ms': (
                statistics.mean(unsafe_times) - statistics.mean(safe_times)
                if safe_times and unsafe_times else 0
            ),
            'target_safety_overhead_ms': 50  # Target: <50ms safety overhead
        }
    
    async def benchmark_memory_usage(self, engine: IntentEngine) -> Dict[str, Any]:
        """Benchmark memory usage patterns."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Analyze many queries
        queries = [
            f"Query {i}: How to optimize performance for use case {i}?"
            for i in range(100)
        ]
        
        for query in queries:
            await engine.analyze_query(query, include_connections=True)
        
        # Measure memory after analysis
        after_analysis = process.memory_info().rss / 1024 / 1024  # MB
        
        # Get engine statistics
        stats = engine.get_stats()
        
        return {
            'baseline_memory_mb': baseline_memory,
            'after_analysis_mb': after_analysis,
            'memory_increase_mb': after_analysis - baseline_memory,
            'queries_analyzed': stats.get('queries_analyzed', 0),
            'memory_per_query_kb': (
                (after_analysis - baseline_memory) * 1024 / 
                max(1, stats.get('queries_analyzed', 1))
            ),
            'target_memory_per_query_kb': 100  # Target: <100KB per query
        }
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("Setting up intent engine for benchmarking...")
        engine = await self.setup_mock_engine()
        
        print("Running intent classification benchmark...")
        classification_perf = await self.benchmark_intent_classification(engine)
        
        print("Running connection finding benchmark...")
        connection_perf = await self.benchmark_connection_finding(engine)
        
        print("Running batch analysis benchmark...")
        batch_perf = await self.benchmark_batch_analysis(engine)
        
        print("Running safety validation benchmark...")
        safety_perf = await self.benchmark_safety_validation(engine)
        
        print("Running memory usage benchmark...")
        memory_perf = await self.benchmark_memory_usage(engine)
        
        # Get engine statistics
        engine_stats = engine.get_stats()
        
        return {
            'intent_classification_performance': classification_perf,
            'connection_finding_performance': connection_perf,
            'batch_analysis_performance': batch_perf,
            'safety_validation_performance': safety_perf,
            'memory_usage': memory_perf,
            'engine_statistics': engine_stats,
            'benchmark_timestamp': time.time()
        }
    
    def print_benchmark_report(self, results: Dict[str, Any]) -> None:
        """Print formatted benchmark report."""
        print("\n" + "="*60)
        print("INTENT ENGINE PERFORMANCE BENCHMARK REPORT")
        print("="*60)
        
        # Intent classification performance
        classification = results['intent_classification_performance']
        print(f"\n📊 Intent Classification Performance:")
        print(f"  Mean time: {classification['mean_ms']:.2f}ms")
        print(f"  Target: <{classification['target_ms']}ms")
        print(f"  Status: {'✅ PASS' if classification['mean_ms'] < classification['target_ms'] else '❌ FAIL'}")
        
        # Connection finding performance
        connection = results['connection_finding_performance']
        print(f"\n🔗 Connection Finding Performance:")
        print(f"  Mean total time: {connection['mean_total_ms']:.2f}ms")
        print(f"  Target: <{connection['connection_finding_target_ms']}ms")
        print(f"  Throughput: {connection['throughput_queries_per_sec']:.1f} queries/sec")
        print(f"  Status: {'✅ PASS' if connection['mean_total_ms'] < connection['connection_finding_target_ms'] else '❌ FAIL'}")
        
        # Batch analysis performance
        batch = results['batch_analysis_performance']
        print(f"\n🔄 Batch Analysis Performance:")
        for batch_size, perf in batch.items():
            status = '✅ PASS' if perf['mean_total_ms'] < perf['target_batch_ms'] else '❌ FAIL'
            print(f"  Batch size {batch_size:2d}: {perf['mean_total_ms']:.2f}ms total, "
                  f"{perf['mean_per_query_ms']:.2f}ms/query - {status}")
        
        # Safety validation performance
        safety = results['safety_validation_performance']
        print(f"\n🛡️ Safety Validation Performance:")
        print(f"  Safe query time: {safety['safe_query_mean_ms']:.2f}ms")
        print(f"  Safety overhead: {safety['safety_overhead_ms']:.2f}ms")
        print(f"  Rejection rate: {safety['safety_rejection_rate']:.1%}")
        print(f"  Target overhead: <{safety['target_safety_overhead_ms']}ms")
        
        # Memory usage
        memory = results['memory_usage']
        print(f"\n💾 Memory Usage:")
        print(f"  Memory per query: {memory['memory_per_query_kb']:.1f}KB")
        print(f"  Target: <{memory['target_memory_per_query_kb']}KB")
        print(f"  Total increase: {memory['memory_increase_mb']:.1f}MB")
        print(f"  Status: {'✅ PASS' if memory['memory_per_query_kb'] < memory['target_memory_per_query_kb'] else '❌ FAIL'}")
        
        # Overall assessment
        print(f"\n🎯 Performance Target Assessment:")
        
        classification_pass = classification['mean_ms'] < classification['target_ms']
        connection_pass = connection['mean_total_ms'] < connection['connection_finding_target_ms']
        batch_pass = all(
            perf['mean_total_ms'] < perf['target_batch_ms'] 
            for perf in batch.values()
        )
        safety_pass = safety['safety_overhead_ms'] < safety['target_safety_overhead_ms']
        memory_pass = memory['memory_per_query_kb'] < memory['target_memory_per_query_kb']
        
        all_pass = all([classification_pass, connection_pass, batch_pass, safety_pass, memory_pass])
        
        print(f"  Intent classification: {'✅ PASS' if classification_pass else '❌ FAIL'}")
        print(f"  Connection finding: {'✅ PASS' if connection_pass else '❌ FAIL'}")
        print(f"  Batch analysis: {'✅ PASS' if batch_pass else '❌ FAIL'}")
        print(f"  Safety validation: {'✅ PASS' if safety_pass else '❌ FAIL'}")
        print(f"  Memory usage: {'✅ PASS' if memory_pass else '❌ FAIL'}")
        print(f"\n  Overall: {'✅ ALL TARGETS MET' if all_pass else '❌ SOME TARGETS MISSED'}")
        
        print("\n" + "="*60)


@pytest.mark.asyncio
async def test_performance_benchmarks():
    """Run performance benchmarks as a test."""
    benchmarks = IntentBenchmarks()
    results = await benchmarks.run_all_benchmarks()
    benchmarks.print_benchmark_report(results)
    
    # Assert performance targets
    classification_perf = results['intent_classification_performance']
    assert classification_perf['mean_ms'] < 200, \
        f"Intent classification too slow: {classification_perf['mean_ms']}ms"
    
    connection_perf = results['connection_finding_performance']
    assert connection_perf['mean_total_ms'] < 500, \
        f"Connection finding too slow: {connection_perf['mean_total_ms']}ms"
    
    memory_usage = results['memory_usage']
    assert memory_usage['memory_per_query_kb'] < 100, \
        f"Memory usage too high: {memory_usage['memory_per_query_kb']}KB per query"


if __name__ == "__main__":
    async def main():
        benchmarks = IntentBenchmarks()
        results = await benchmarks.run_all_benchmarks()
        benchmarks.print_benchmark_report(results)
    
    asyncio.run(main())