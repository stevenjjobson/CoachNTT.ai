"""
Performance benchmarks for the memory system.

Tests performance characteristics of decay, clustering, and search operations.
"""

import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytest
import asyncpg
import numpy as np

from src.core.memory.abstract_models import InteractionType, MemoryMetadata
from src.core.memory.repository import SafeMemoryRepository
from src.core.memory.cluster_manager import ClusterType


class MemorySystemBenchmarks:
    """Performance benchmarks for memory system operations."""
    
    def __init__(self, repository: SafeMemoryRepository):
        """Initialize benchmarks with repository."""
        self.repository = repository
        self.benchmark_results = {}
    
    async def setup_benchmark_data(self, num_memories: int = 1000) -> List[str]:
        """Create benchmark data with specified number of memories."""
        print(f"Creating {num_memories} benchmark memories...")
        
        memory_ids = []
        session_id = "benchmark-session"
        
        # Template memories for testing
        templates = [
            {
                "prompt": "How do I implement <algorithm> in <language>?",
                "response": "To implement <algorithm> in <language>, follow these steps: 1. Define the function 2. Handle edge cases 3. Implement the logic",
                "type": InteractionType.CODE_GENERATION,
                "tags": ["algorithm", "implementation"]
            },
            {
                "prompt": "Debug this <error_type> in <component>",
                "response": "The <error_type> in <component> is typically caused by <root_cause>. Fix by checking <solution_steps>.",
                "type": InteractionType.DEBUGGING,
                "tags": ["debugging", "error-handling"]
            },
            {
                "prompt": "Explain the concept of <concept> in <domain>",
                "response": "<concept> in <domain> refers to <definition>. It's important because <reasoning>.",
                "type": InteractionType.DOCUMENTATION,
                "tags": ["concepts", "explanation"]
            },
            {
                "prompt": "What's the best approach to solve <problem>?",
                "response": "For <problem>, consider these approaches: 1. <approach1> 2. <approach2> 3. <approach3>. Choose based on <criteria>.",
                "type": InteractionType.PROBLEM_SOLVING,
                "tags": ["problem-solving", "best-practices"]
            }
        ]
        
        start_time = time.time()
        
        for i in range(num_memories):
            template = templates[i % len(templates)]
            
            # Vary the content slightly for each memory
            prompt = template["prompt"].replace("<algorithm>", f"algorithm_{i}")
            prompt = prompt.replace("<language>", f"language_{i % 5}")
            prompt = prompt.replace("<error_type>", f"error_{i}")
            prompt = prompt.replace("<component>", f"component_{i}")
            prompt = prompt.replace("<concept>", f"concept_{i}")
            prompt = prompt.replace("<domain>", f"domain_{i % 3}")
            prompt = prompt.replace("<problem>", f"problem_{i}")
            
            response = template["response"].replace("<algorithm>", f"algorithm_{i}")
            response = response.replace("<language>", f"language_{i % 5}")
            response = response.replace("<root_cause>", f"cause_{i}")
            response = response.replace("<solution_steps>", f"steps_{i}")
            response = response.replace("<definition>", f"definition_{i}")
            response = response.replace("<reasoning>", f"reasoning_{i}")
            response = response.replace("<approach1>", f"approach1_{i}")
            response = response.replace("<approach2>", f"approach2_{i}")
            response = response.replace("<approach3>", f"approach3_{i}")
            response = response.replace("<criteria>", f"criteria_{i}")
            
            metadata = MemoryMetadata(
                tags=template["tags"] + [f"benchmark_{i % 10}"],
                context={"benchmark": True, "index": i}
            )
            
            try:
                # Create memory
                memory = await self.repository.create_memory(
                    prompt=prompt,
                    response=response,
                    metadata=metadata.to_dict()
                )
                
                # Create interaction
                interaction = await self.repository.create_interaction(
                    memory=memory,
                    session_id=session_id,
                    interaction_type=template["type"],
                    metadata=metadata
                )
                
                # Add random embeddings for testing
                await self._add_random_embeddings(interaction.interaction_id)
                
                memory_ids.append(str(interaction.interaction_id))
                
                if (i + 1) % 100 == 0:
                    print(f"Created {i + 1} memories...")
                    
            except Exception as e:
                print(f"Error creating memory {i}: {e}")
                continue
        
        setup_time = time.time() - start_time
        print(f"Setup completed in {setup_time:.2f} seconds")
        print(f"Created {len(memory_ids)} memories successfully")
        
        return memory_ids
    
    async def _add_random_embeddings(self, interaction_id: str):
        """Add random embeddings to an interaction for testing."""
        prompt_embedding = np.random.random(1536).tolist()
        response_embedding = np.random.random(1536).tolist()
        
        async with self.repository.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE public.cognitive_memory
                SET prompt_embedding = $1, response_embedding = $2
                WHERE id = $3
            """, prompt_embedding, response_embedding, interaction_id)
    
    async def benchmark_memory_creation(self, num_operations: int = 100) -> Dict[str, float]:
        """Benchmark memory creation performance."""
        print(f"Benchmarking memory creation ({num_operations} operations)...")
        
        times = []
        
        for i in range(num_operations):
            start_time = time.time()
            
            try:
                memory = await self.repository.create_memory(
                    prompt=f"Benchmark prompt {i} with <placeholder_{i}>",
                    response=f"Benchmark response {i} using <method_{i}>",
                    metadata={"benchmark": True, "iteration": i}
                )
                
                interaction = await self.repository.create_interaction(
                    memory=memory,
                    session_id="benchmark-creation",
                    interaction_type=InteractionType.CODE_GENERATION
                )
                
                end_time = time.time()
                times.append((end_time - start_time) * 1000)  # Convert to milliseconds
                
            except Exception as e:
                print(f"Error in creation benchmark {i}: {e}")
                continue
        
        return {
            "operation": "memory_creation",
            "count": len(times),
            "avg_time_ms": statistics.mean(times),
            "median_time_ms": statistics.median(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    async def benchmark_search_performance(self, memory_ids: List[str], num_searches: int = 50) -> Dict[str, float]:
        """Benchmark search performance."""
        print(f"Benchmarking search performance ({num_searches} searches)...")
        
        search_queries = [
            "algorithm implementation",
            "debugging error handling",
            "concept explanation",
            "problem solving approach",
            "best practices optimization",
            "function definition syntax",
            "memory management techniques",
            "data structure operations",
            "async programming patterns",
            "testing methodology"
        ]
        
        times = []
        result_counts = []
        
        for i in range(num_searches):
            query = search_queries[i % len(search_queries)]
            
            start_time = time.time()
            
            try:
                results = await self.repository.search_with_clustering(
                    query=query,
                    limit=10,
                    min_safety_score=0.8
                )
                
                end_time = time.time()
                times.append((end_time - start_time) * 1000)
                result_counts.append(len(results))
                
            except Exception as e:
                print(f"Error in search benchmark {i}: {e}")
                continue
        
        return {
            "operation": "search",
            "count": len(times),
            "avg_time_ms": statistics.mean(times),
            "median_time_ms": statistics.median(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_results": statistics.mean(result_counts),
            "total_results": sum(result_counts)
        }
    
    async def benchmark_clustering_performance(self, memory_ids: List[str]) -> Dict[str, float]:
        """Benchmark clustering performance."""
        print("Benchmarking clustering performance...")
        
        start_time = time.time()
        
        try:
            # Test auto-clustering
            result = await self.repository.cluster_manager.auto_cluster_memories(
                min_cluster_size=3,
                max_clusters=10,
                interaction_types=[InteractionType.CODE_GENERATION, InteractionType.DEBUGGING]
            )
            
            end_time = time.time()
            clustering_time = (end_time - start_time) * 1000
            
            # Test individual similarity searches
            similarity_times = []
            
            for i in range(min(10, len(memory_ids))):  # Test 10 similarity searches
                memory_id = memory_ids[i]
                
                start_time = time.time()
                similar = await self.repository.cluster_manager.find_similar_memories(
                    memory_id=memory_id,
                    similarity_threshold=0.5,
                    max_results=5
                )
                end_time = time.time()
                
                similarity_times.append((end_time - start_time) * 1000)
            
            return {
                "operation": "clustering",
                "auto_clustering_time_ms": clustering_time,
                "clusters_created": result.clusters_created,
                "memories_clustered": result.memories_clustered,
                "quality_score": result.quality_score,
                "avg_similarity_search_ms": statistics.mean(similarity_times),
                "similarity_searches": len(similarity_times)
            }
            
        except Exception as e:
            print(f"Error in clustering benchmark: {e}")
            return {"operation": "clustering", "error": str(e)}
    
    async def benchmark_decay_performance(self, memory_ids: List[str]) -> Dict[str, float]:
        """Benchmark decay performance."""
        print("Benchmarking decay performance...")
        
        # Age some memories first
        cutoff_time = datetime.utcnow() - timedelta(days=2)
        
        async with self.repository.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE public.cognitive_memory
                SET last_accessed = $1
                WHERE id = ANY($2::uuid[])
            """, cutoff_time, memory_ids[:100])  # Age first 100 memories
        
        start_time = time.time()
        
        try:
            # Test batch decay processing
            analysis = await self.repository.decay_engine.apply_decay_batch(
                batch_size=200,
                max_age_days=1
            )
            
            end_time = time.time()
            
            return {
                "operation": "decay",
                "processing_time_ms": (end_time - start_time) * 1000,
                "memories_processed": analysis.total_processed,
                "memories_changed": len(analysis.weight_changes),
                "memories_removed": len(analysis.removed_memories),
                "avg_decay_percent": analysis.average_decay * 100,
                "db_processing_time_ms": analysis.processing_time_ms
            }
            
        except Exception as e:
            print(f"Error in decay benchmark: {e}")
            return {"operation": "decay", "error": str(e)}
    
    async def benchmark_relationship_performance(self, memory_ids: List[str], num_relationships: int = 100) -> Dict[str, float]:
        """Benchmark relationship creation and querying."""
        print(f"Benchmarking relationship performance ({num_relationships} relationships)...")
        
        # Create relationships
        creation_times = []
        
        for i in range(min(num_relationships, len(memory_ids) - 1)):
            source_id = memory_ids[i]
            target_id = memory_ids[i + 1]
            
            start_time = time.time()
            
            success = await self.repository.create_memory_relationship(
                source_memory_id=source_id,
                target_memory_id=target_id,
                relationship_type="related_topic",
                relationship_strength=0.7,
                is_bidirectional=True
            )
            
            end_time = time.time()
            
            if success:
                creation_times.append((end_time - start_time) * 1000)
        
        # Query relationships
        query_times = []
        
        for i in range(min(20, len(memory_ids))):  # Test 20 relationship queries
            memory_id = memory_ids[i]
            
            start_time = time.time()
            
            relationships = await self.repository.get_memory_relationships(
                memory_id=memory_id,
                min_strength=0.5
            )
            
            end_time = time.time()
            query_times.append((end_time - start_time) * 1000)
        
        return {
            "operation": "relationships",
            "relationships_created": len(creation_times),
            "avg_creation_time_ms": statistics.mean(creation_times) if creation_times else 0,
            "relationship_queries": len(query_times),
            "avg_query_time_ms": statistics.mean(query_times) if query_times else 0,
            "median_creation_time_ms": statistics.median(creation_times) if creation_times else 0,
            "median_query_time_ms": statistics.median(query_times) if query_times else 0
        }
    
    async def run_comprehensive_benchmark(self, num_memories: int = 500) -> Dict[str, Any]:
        """Run comprehensive performance benchmark."""
        print("=" * 60)
        print(f"COMPREHENSIVE MEMORY SYSTEM BENCHMARK")
        print(f"Testing with {num_memories} memories")
        print("=" * 60)
        
        # Setup benchmark data
        memory_ids = await self.setup_benchmark_data(num_memories)
        
        if not memory_ids:
            return {"error": "Failed to create benchmark data"}
        
        # Run all benchmarks
        benchmarks = {}
        
        # Memory creation benchmark
        benchmarks["creation"] = await self.benchmark_memory_creation(50)
        
        # Search benchmark
        benchmarks["search"] = await self.benchmark_search_performance(memory_ids, 25)
        
        # Clustering benchmark
        benchmarks["clustering"] = await self.benchmark_clustering_performance(memory_ids)
        
        # Decay benchmark
        benchmarks["decay"] = await self.benchmark_decay_performance(memory_ids)
        
        # Relationship benchmark
        benchmarks["relationships"] = await self.benchmark_relationship_performance(memory_ids, 50)
        
        # Overall statistics
        benchmarks["summary"] = {
            "total_memories_created": len(memory_ids),
            "benchmark_timestamp": datetime.utcnow().isoformat(),
            "performance_grade": self._calculate_performance_grade(benchmarks)
        }
        
        self.benchmark_results = benchmarks
        return benchmarks
    
    def _calculate_performance_grade(self, benchmarks: Dict[str, Any]) -> str:
        """Calculate overall performance grade."""
        # Simple grading based on key metrics
        grades = []
        
        # Memory creation should be < 100ms average
        if "creation" in benchmarks and "avg_time_ms" in benchmarks["creation"]:
            creation_time = benchmarks["creation"]["avg_time_ms"]
            if creation_time < 50:
                grades.append("A")
            elif creation_time < 100:
                grades.append("B")
            elif creation_time < 200:
                grades.append("C")
            else:
                grades.append("D")
        
        # Search should be < 100ms average
        if "search" in benchmarks and "avg_time_ms" in benchmarks["search"]:
            search_time = benchmarks["search"]["avg_time_ms"]
            if search_time < 50:
                grades.append("A")
            elif search_time < 100:
                grades.append("B")
            elif search_time < 200:
                grades.append("C")
            else:
                grades.append("D")
        
        # Clustering quality should be > 0.7
        if "clustering" in benchmarks and "quality_score" in benchmarks["clustering"]:
            quality = benchmarks["clustering"]["quality_score"]
            if quality > 0.8:
                grades.append("A")
            elif quality > 0.7:
                grades.append("B")
            elif quality > 0.6:
                grades.append("C")
            else:
                grades.append("D")
        
        # Calculate average grade
        grade_values = {"A": 4, "B": 3, "C": 2, "D": 1}
        if grades:
            avg_grade = sum(grade_values[g] for g in grades) / len(grades)
            if avg_grade >= 3.5:
                return "A"
            elif avg_grade >= 2.5:
                return "B"
            elif avg_grade >= 1.5:
                return "C"
            else:
                return "D"
        
        return "N/A"
    
    def print_benchmark_results(self):
        """Print formatted benchmark results."""
        if not self.benchmark_results:
            print("No benchmark results available")
            return
        
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)
        
        for operation, results in self.benchmark_results.items():
            if operation == "summary":
                continue
                
            print(f"\n{operation.upper()} BENCHMARK:")
            print("-" * 30)
            
            for key, value in results.items():
                if isinstance(value, float):
                    if "time_ms" in key:
                        print(f"  {key}: {value:.2f} ms")
                    elif "score" in key or "percent" in key:
                        print(f"  {key}: {value:.3f}")
                    else:
                        print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
        
        if "summary" in self.benchmark_results:
            summary = self.benchmark_results["summary"]
            print(f"\nOVERALL PERFORMANCE GRADE: {summary.get('performance_grade', 'N/A')}")
            print(f"Total memories created: {summary.get('total_memories_created', 0)}")
            print(f"Benchmark timestamp: {summary.get('benchmark_timestamp', 'N/A')}")


@pytest.fixture
async def benchmark_repository():
    """Create repository for benchmarking."""
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="ccp_user",
        password="secure_password_123",
        database="cognitive_coding_partner_test",
        min_size=2,
        max_size=10
    )
    
    repository = SafeMemoryRepository(pool)
    await repository.decay_engine.initialize()
    
    yield repository
    
    await pool.close()


@pytest.mark.asyncio
async def test_memory_system_benchmarks(benchmark_repository):
    """Run memory system benchmarks."""
    benchmarks = MemorySystemBenchmarks(benchmark_repository)
    
    # Run with smaller dataset for testing
    results = await benchmarks.run_comprehensive_benchmark(num_memories=100)
    
    benchmarks.print_benchmark_results()
    
    # Basic assertions
    assert "creation" in results
    assert "search" in results
    assert "clustering" in results
    assert "decay" in results
    assert "relationships" in results
    
    # Performance assertions (these thresholds can be adjusted)
    if "avg_time_ms" in results["creation"]:
        assert results["creation"]["avg_time_ms"] < 500  # Should create memories in < 500ms
    
    if "avg_time_ms" in results["search"]:
        assert results["search"]["avg_time_ms"] < 1000  # Should search in < 1s


if __name__ == "__main__":
    # Run benchmarks directly
    async def main():
        pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            user="ccp_user",
            password="secure_password_123",
            database="cognitive_coding_partner_test",
            min_size=2,
            max_size=10
        )
        
        repository = SafeMemoryRepository(pool)
        await repository.decay_engine.initialize()
        
        benchmarks = MemorySystemBenchmarks(repository)
        await benchmarks.run_comprehensive_benchmark(num_memories=1000)
        benchmarks.print_benchmark_results()
        
        await pool.close()
    
    asyncio.run(main())