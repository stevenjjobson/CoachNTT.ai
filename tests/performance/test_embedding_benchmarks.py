"""
Performance benchmarks for the embedding system.

Tests embedding generation speed, cache performance, and similarity search improvements.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch

import pytest

from src.core.embeddings import (
    EmbeddingService,
    EmbeddingCache,
    ContentType,
    BatchEmbeddingRequest
)


class EmbeddingBenchmarks:
    """Benchmarking suite for embedding operations."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
    
    async def setup_mock_service(self) -> EmbeddingService:
        """Set up mocked embedding service for consistent benchmarking."""
        with patch('src.core.embeddings.service.SENTENCE_TRANSFORMERS_AVAILABLE', True):
            with patch('src.core.embeddings.service.SentenceTransformer') as mock_st:
                # Mock model that simulates realistic processing time
                mock_model = Mock()
                
                def mock_encode(texts, **kwargs):
                    # Simulate processing time based on text length
                    if isinstance(texts, list):
                        time.sleep(0.01 * len(texts))  # 10ms per text
                        return [[0.1, 0.2, 0.3] for _ in texts]
                    else:
                        time.sleep(0.01)
                        return [[0.1, 0.2, 0.3]]
                
                mock_model.encode = mock_encode
                mock_st.return_value = mock_model
                
                with patch('src.core.embeddings.service.torch') as mock_torch:
                    mock_torch.cuda.is_available.return_value = False
                    
                    cache = EmbeddingCache(max_size=1000)
                    service = EmbeddingService(cache=cache, device='cpu')
                    return service
    
    async def benchmark_single_embedding_generation(
        self, 
        service: EmbeddingService,
        num_iterations: int = 100
    ) -> Dict[str, float]:
        """Benchmark single embedding generation."""
        times = []
        
        for i in range(num_iterations):
            content = f"Test content for iteration {i}"
            
            start_time = time.time()
            await service.generate_embedding(content=content)
            end_time = time.time()
            
            times.append((end_time - start_time) * 1000)  # Convert to ms
        
        return {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'std_ms': statistics.stdev(times) if len(times) > 1 else 0.0,
            'min_ms': min(times),
            'max_ms': max(times),
            'iterations': num_iterations
        }
    
    async def benchmark_batch_embedding_generation(
        self,
        service: EmbeddingService,
        batch_sizes: List[int] = [1, 5, 10, 20, 50]
    ) -> Dict[int, Dict[str, float]]:
        """Benchmark batch embedding generation with different sizes."""
        results = {}
        
        for batch_size in batch_sizes:
            texts = [f"Batch text {i}" for i in range(batch_size)]
            request = BatchEmbeddingRequest(texts=texts)
            
            times = []
            for _ in range(10):  # 10 iterations per batch size
                start_time = time.time()
                await service.generate_batch_embeddings(request)
                end_time = time.time()
                
                times.append((end_time - start_time) * 1000)
            
            results[batch_size] = {
                'mean_total_ms': statistics.mean(times),
                'mean_per_item_ms': statistics.mean(times) / batch_size,
                'throughput_items_per_sec': batch_size / (statistics.mean(times) / 1000),
                'iterations': len(times)
            }
        
        return results
    
    async def benchmark_cache_performance(
        self,
        service: EmbeddingService,
        num_unique_items: int = 100,
        num_accesses: int = 1000
    ) -> Dict[str, Any]:
        """Benchmark cache hit rates and performance."""
        import random
        
        # Generate unique content items
        unique_contents = [f"Unique content {i}" for i in range(num_unique_items)]
        
        # Pre-populate cache with some items
        for content in unique_contents[:50]:  # Cache first 50%
            await service.generate_embedding(content=content)
        
        # Measure cache performance
        cache_hits = 0
        cache_misses = 0
        access_times = []
        
        for _ in range(num_accesses):
            # Randomly select content (with bias toward cached items)
            if random.random() < 0.7:  # 70% chance of accessing cached item
                content = random.choice(unique_contents[:50])
            else:
                content = random.choice(unique_contents[50:])
            
            start_time = time.time()
            result = await service.generate_embedding(content=content)
            end_time = time.time()
            
            access_times.append((end_time - start_time) * 1000)
            
            if result.cache_hit:
                cache_hits += 1
            else:
                cache_misses += 1
        
        return {
            'cache_hit_rate': cache_hits / num_accesses,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'mean_access_time_ms': statistics.mean(access_times),
            'cache_vs_generation_speedup': 'N/A'  # Would need separate measurement
        }
    
    async def benchmark_similarity_search(
        self,
        service: EmbeddingService,
        num_candidates: int = 1000,
        top_k: int = 10
    ) -> Dict[str, float]:
        """Benchmark similarity search performance."""
        # Generate embeddings for candidates
        candidate_embeddings = []
        for i in range(num_candidates):
            # Create varied embeddings for realistic search
            base = [0.1, 0.2, 0.3]
            variation = [x + (i * 0.001) for x in base]
            candidate_embeddings.append(variation)
        
        # Query embedding
        query_embedding = [0.15, 0.25, 0.35]
        
        # Benchmark search
        times = []
        for _ in range(50):  # 50 search iterations
            start_time = time.time()
            results = await service.find_most_similar(
                query_embedding, candidate_embeddings, top_k=top_k
            )
            end_time = time.time()
            
            times.append((end_time - start_time) * 1000)
        
        return {
            'mean_search_time_ms': statistics.mean(times),
            'search_throughput_items_per_ms': num_candidates / statistics.mean(times),
            'candidates_searched': num_candidates,
            'top_k': top_k,
            'iterations': len(times)
        }
    
    async def benchmark_memory_usage(self, service: EmbeddingService) -> Dict[str, Any]:
        """Benchmark memory usage patterns."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate many embeddings
        for i in range(500):
            await service.generate_embedding(f"Memory test content {i}")
        
        # Measure memory after embedding generation
        after_embeddings = process.memory_info().rss / 1024 / 1024  # MB
        
        # Get cache statistics
        cache_stats = service.get_stats()
        
        return {
            'baseline_memory_mb': baseline_memory,
            'after_embeddings_mb': after_embeddings,
            'memory_increase_mb': after_embeddings - baseline_memory,
            'embeddings_generated': cache_stats.get('embeddings_generated', 0),
            'cache_size': cache_stats.get('cache_size', 0),
            'memory_per_embedding_kb': (
                (after_embeddings - baseline_memory) * 1024 / 
                cache_stats.get('embeddings_generated', 1)
            )
        }
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("Setting up embedding service for benchmarking...")
        service = await self.setup_mock_service()
        
        print("Running single embedding generation benchmark...")
        single_perf = await self.benchmark_single_embedding_generation(service)
        
        print("Running batch embedding generation benchmark...")
        batch_perf = await self.benchmark_batch_embedding_generation(service)
        
        print("Running cache performance benchmark...")
        cache_perf = await self.benchmark_cache_performance(service)
        
        print("Running similarity search benchmark...")
        search_perf = await self.benchmark_similarity_search(service)
        
        print("Running memory usage benchmark...")
        memory_perf = await self.benchmark_memory_usage(service)
        
        # Get service statistics
        service_stats = service.get_stats()
        
        return {
            'single_embedding_performance': single_perf,
            'batch_embedding_performance': batch_perf,
            'cache_performance': cache_perf,
            'similarity_search_performance': search_perf,
            'memory_usage': memory_perf,
            'service_statistics': service_stats,
            'benchmark_timestamp': time.time()
        }
    
    def print_benchmark_report(self, results: Dict[str, Any]) -> None:
        """Print formatted benchmark report."""
        print("\n" + "="*60)
        print("EMBEDDING SYSTEM PERFORMANCE BENCHMARK REPORT")
        print("="*60)
        
        # Single embedding performance
        single = results['single_embedding_performance']
        print(f"\n📊 Single Embedding Generation:")
        print(f"  Mean time: {single['mean_ms']:.2f}ms")
        print(f"  Median time: {single['median_ms']:.2f}ms")
        print(f"  Min/Max: {single['min_ms']:.2f}ms / {single['max_ms']:.2f}ms")
        print(f"  Standard deviation: {single['std_ms']:.2f}ms")
        
        # Batch performance
        batch = results['batch_embedding_performance']
        print(f"\n🔄 Batch Embedding Generation:")
        for batch_size, perf in batch.items():
            print(f"  Batch size {batch_size:2d}: "
                  f"{perf['mean_per_item_ms']:.2f}ms/item, "
                  f"{perf['throughput_items_per_sec']:.1f} items/sec")
        
        # Cache performance
        cache = results['cache_performance']
        print(f"\n💾 Cache Performance:")
        print(f"  Hit rate: {cache['cache_hit_rate']:.1%}")
        print(f"  Mean access time: {cache['mean_access_time_ms']:.2f}ms")
        print(f"  Cache hits/misses: {cache['cache_hits']}/{cache['cache_misses']}")
        
        # Search performance
        search = results['similarity_search_performance']
        print(f"\n🔍 Similarity Search:")
        print(f"  Mean search time: {search['mean_search_time_ms']:.2f}ms")
        print(f"  Search throughput: {search['search_throughput_items_per_ms']:.1f} items/ms")
        print(f"  Candidates: {search['candidates_searched']}, Top-K: {search['top_k']}")
        
        # Memory usage
        memory = results['memory_usage']
        print(f"\n💾 Memory Usage:")
        print(f"  Baseline memory: {memory['baseline_memory_mb']:.1f}MB")
        print(f"  After embeddings: {memory['after_embeddings_mb']:.1f}MB")
        print(f"  Memory increase: {memory['memory_increase_mb']:.1f}MB")
        print(f"  Memory per embedding: {memory['memory_per_embedding_kb']:.1f}KB")
        
        # Performance targets assessment
        print(f"\n🎯 Performance Target Assessment:")
        target_single = 500  # ms
        target_batch_10 = 2000  # ms for 10 items
        target_cache_hit = 0.8  # 80%
        
        single_pass = single['mean_ms'] < target_single
        batch_pass = batch.get(10, {}).get('mean_total_ms', float('inf')) < target_batch_10
        cache_pass = cache['cache_hit_rate'] > target_cache_hit
        
        print(f"  Single embedding <500ms: {'✅ PASS' if single_pass else '❌ FAIL'}")
        print(f"  Batch 10 items <2s: {'✅ PASS' if batch_pass else '❌ FAIL'}")
        print(f"  Cache hit rate >80%: {'✅ PASS' if cache_pass else '❌ FAIL'}")
        
        print("\n" + "="*60)


@pytest.mark.asyncio
async def test_performance_benchmarks():
    """Run performance benchmarks as a test."""
    benchmarks = EmbeddingBenchmarks()
    results = await benchmarks.run_all_benchmarks()
    benchmarks.print_benchmark_report(results)
    
    # Assert performance targets
    single_perf = results['single_embedding_performance']
    assert single_perf['mean_ms'] < 500, f"Single embedding too slow: {single_perf['mean_ms']}ms"
    
    batch_perf = results['batch_embedding_performance']
    if 10 in batch_perf:
        assert batch_perf[10]['mean_total_ms'] < 2000, \
            f"Batch 10 too slow: {batch_perf[10]['mean_total_ms']}ms"
    
    cache_perf = results['cache_performance']
    assert cache_perf['cache_hit_rate'] > 0.6, \
        f"Cache hit rate too low: {cache_perf['cache_hit_rate']}"


if __name__ == "__main__":
    async def main():
        benchmarks = EmbeddingBenchmarks()
        results = await benchmarks.run_all_benchmarks()
        benchmarks.print_benchmark_report(results)
    
    asyncio.run(main())