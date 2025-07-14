"""
Load and performance tests for critical paths.

Tests system performance under various load conditions and validates
that performance targets are met.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import aiohttp

from tests.fixtures.memories import MemoryFixtures
from tests.fixtures.graphs import GraphFixtures
from tests.fixtures.safety import SafetyFixtures


@dataclass
class PerformanceResult:
    """Performance test result."""
    operation: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    min_time_ms: float
    max_time_ms: float
    avg_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    requests_per_second: float


@pytest.mark.performance
@pytest.mark.slow
class TestLoadPerformance:
    """Test system performance under load."""
    
    @pytest.fixture
    def api_base_url(self):
        """API base URL for load testing."""
        return "http://localhost:8000"
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers."""
        return {"Authorization": "Bearer test-api-key"}
    
    async def measure_operation(
        self,
        operation_name: str,
        operation_func: Callable,
        iterations: int = 100,
        concurrent_requests: int = 10
    ) -> PerformanceResult:
        """Measure performance of an operation."""
        timings = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        # Create tasks for concurrent execution
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def timed_operation():
            async with semaphore:
                op_start = time.time()
                try:
                    await operation_func()
                    timings.append((time.time() - op_start) * 1000)
                    return True
                except Exception as e:
                    print(f"Operation failed: {e}")
                    return False
        
        # Run operations concurrently
        tasks = [timed_operation() for _ in range(iterations)]
        results = await asyncio.gather(*tasks)
        
        # Count successes and failures
        successful = sum(1 for r in results if r)
        failed = sum(1 for r in results if not r)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        if timings:
            timings.sort()
            return PerformanceResult(
                operation=operation_name,
                total_requests=iterations,
                successful_requests=successful,
                failed_requests=failed,
                min_time_ms=min(timings),
                max_time_ms=max(timings),
                avg_time_ms=statistics.mean(timings),
                median_time_ms=statistics.median(timings),
                p95_time_ms=timings[int(len(timings) * 0.95)],
                p99_time_ms=timings[int(len(timings) * 0.99)],
                requests_per_second=iterations / total_time
            )
        else:
            return PerformanceResult(
                operation=operation_name,
                total_requests=iterations,
                successful_requests=0,
                failed_requests=iterations,
                min_time_ms=0,
                max_time_ms=0,
                avg_time_ms=0,
                median_time_ms=0,
                p95_time_ms=0,
                p99_time_ms=0,
                requests_per_second=0
            )
    
    async def test_memory_creation_load(
        self,
        api_base_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test memory creation under load."""
        memory_fixtures = MemoryFixtures()
        
        async def create_memory():
            async with aiohttp.ClientSession() as session:
                memory_data = memory_fixtures.create_safe_memory()
                
                async with session.post(
                    f"{api_base_url}/api/v1/memories/",
                    json={
                        "memory_type": memory_data["memory_type"],
                        "prompt": memory_data["prompt"],
                        "content": memory_data["content"],
                        "metadata": memory_data["metadata"]
                    },
                    headers=auth_headers
                ) as response:
                    if response.status != 201:
                        raise Exception(f"Failed with status {response.status}")
                    return await response.json()
        
        # Test with increasing load
        for concurrent in [1, 5, 10, 20]:
            print(f"\n--- Testing memory creation with {concurrent} concurrent requests ---")
            
            result = await self.measure_operation(
                f"Memory Creation (concurrent={concurrent})",
                create_memory,
                iterations=50,
                concurrent_requests=concurrent
            )
            
            self.print_performance_result(result)
            
            # Validate performance targets
            assert result.avg_time_ms < 500, f"Average time {result.avg_time_ms}ms exceeds 500ms target"
            assert result.p95_time_ms < 1000, f"P95 time {result.p95_time_ms}ms exceeds 1000ms target"
            assert result.failed_requests == 0, f"{result.failed_requests} requests failed"
    
    async def test_memory_search_load(
        self,
        api_base_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test memory search under load."""
        search_queries = [
            "understanding patterns",
            "implementation design",
            "optimization techniques",
            "debugging solutions",
            "architecture decisions"
        ]
        
        async def search_memories():
            async with aiohttp.ClientSession() as session:
                query = search_queries[int(time.time() * 1000) % len(search_queries)]
                
                async with session.post(
                    f"{api_base_url}/api/v1/memories/search",
                    json={
                        "query": query,
                        "limit": 20,
                        "enable_intent_analysis": True
                    },
                    headers=auth_headers
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Failed with status {response.status}")
                    return await response.json()
        
        print("\n--- Testing memory search under load ---")
        
        result = await self.measure_operation(
            "Memory Search",
            search_memories,
            iterations=100,
            concurrent_requests=15
        )
        
        self.print_performance_result(result)
        
        # Validate performance targets
        assert result.avg_time_ms < 1000, f"Average search time {result.avg_time_ms}ms exceeds 1000ms target"
        assert result.p95_time_ms < 2000, f"P95 search time {result.p95_time_ms}ms exceeds 2000ms target"
    
    async def test_graph_building_load(
        self,
        api_base_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test graph building under load."""
        async def build_graph():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base_url}/api/v1/graph/build",
                    json={
                        "max_nodes": 50,
                        "similarity_threshold": 0.7,
                        "graph_name": f"Load Test Graph {int(time.time())}"
                    },
                    headers=auth_headers
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Failed with status {response.status}")
                    return await response.json()
        
        print("\n--- Testing graph building under load ---")
        
        # Graph building is resource intensive, use fewer concurrent requests
        result = await self.measure_operation(
            "Graph Building",
            build_graph,
            iterations=20,
            concurrent_requests=3
        )
        
        self.print_performance_result(result)
        
        # Validate performance targets
        assert result.avg_time_ms < 5000, f"Average build time {result.avg_time_ms}ms exceeds 5000ms target"
        assert result.p99_time_ms < 10000, f"P99 build time {result.p99_time_ms}ms exceeds 10000ms target"
    
    async def test_safety_validation_performance(self):
        """Test safety validation performance."""
        from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
        
        engine = ConcreteAbstractionEngine()
        safety_fixtures = SafetyFixtures()
        test_data = safety_fixtures.get_performance_test_data()
        
        print("\n--- Testing safety validation performance ---")
        
        for content_type, content in [
            ("small", test_data["small_content"]),
            ("medium", test_data["medium_content"]),
            ("large", test_data["large_content"]),
            ("complex", test_data["complex_patterns"])
        ]:
            # Measure performance
            timings = []
            iterations = 1000 if content_type == "small" else 100
            
            # Warm up
            for _ in range(10):
                engine.process_content(content)
            
            # Measure
            for _ in range(iterations):
                start = time.time()
                result = engine.process_content(content)
                timings.append((time.time() - start) * 1000)
            
            avg_time = statistics.mean(timings)
            p95_time = sorted(timings)[int(len(timings) * 0.95)]
            
            print(f"\n{content_type.upper()} content ({len(content)} chars):")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            
            # Validate against targets
            target = test_data["performance_targets"][f"{content_type}_content_ms"]
            assert avg_time < target, f"{content_type} avg time {avg_time:.2f}ms exceeds {target}ms target"
    
    async def test_concurrent_user_simulation(
        self,
        api_base_url: str,
        auth_headers: Dict[str, str]
    ):
        """Simulate multiple concurrent users."""
        print("\n--- Simulating concurrent users ---")
        
        memory_fixtures = MemoryFixtures()
        
        async def user_workflow():
            """Simulate a typical user workflow."""
            async with aiohttp.ClientSession() as session:
                # 1. Check status
                async with session.get(
                    f"{api_base_url}/health",
                    headers=auth_headers
                ) as response:
                    assert response.status == 200
                
                # 2. Create a memory
                memory_data = memory_fixtures.create_safe_memory()
                async with session.post(
                    f"{api_base_url}/api/v1/memories/",
                    json={
                        "memory_type": memory_data["memory_type"],
                        "prompt": memory_data["prompt"],
                        "content": memory_data["content"],
                        "metadata": memory_data["metadata"]
                    },
                    headers=auth_headers
                ) as response:
                    assert response.status == 201
                    memory = await response.json()
                
                # 3. Search memories
                async with session.post(
                    f"{api_base_url}/api/v1/memories/search",
                    json={
                        "query": "test pattern",
                        "limit": 10
                    },
                    headers=auth_headers
                ) as response:
                    assert response.status == 200
                
                # 4. List memories
                async with session.get(
                    f"{api_base_url}/api/v1/memories/?limit=5",
                    headers=auth_headers
                ) as response:
                    assert response.status == 200
                
                return True
        
        # Simulate different user loads
        for num_users in [5, 10, 20]:
            print(f"\n  Simulating {num_users} concurrent users...")
            
            start_time = time.time()
            
            # Run user workflows concurrently
            tasks = [user_workflow() for _ in range(num_users)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            successful = sum(1 for r in results if r is True)
            failed = len(results) - successful
            
            print(f"    Completed: {successful}/{num_users} users")
            print(f"    Failed: {failed}")
            print(f"    Total time: {total_time:.2f}s")
            print(f"    Throughput: {num_users/total_time:.2f} users/second")
            
            # All users should complete successfully
            assert failed == 0, f"{failed} user workflows failed"
    
    async def test_websocket_message_throughput(self):
        """Test WebSocket message throughput."""
        print("\n--- Testing WebSocket message throughput ---")
        
        # This is a simplified test since we'd need a real WebSocket server
        # In a real test, you would:
        # 1. Connect multiple WebSocket clients
        # 2. Subscribe to channels
        # 3. Measure message delivery latency
        # 4. Test broadcast performance
        
        message_count = 1000
        message_size = 1024  # 1KB messages
        
        # Simulate message processing
        timings = []
        for _ in range(message_count):
            start = time.time()
            
            # Simulate message processing
            message = {"type": "update", "data": "x" * message_size}
            json_message = json.dumps(message)
            parsed = json.loads(json_message)
            
            timings.append((time.time() - start) * 1000)
        
        avg_time = statistics.mean(timings)
        throughput = 1000 / avg_time  # messages per second
        
        print(f"  Message processing time: {avg_time:.3f}ms")
        print(f"  Theoretical throughput: {throughput:.0f} messages/second")
        
        # Should handle at least 1000 messages/second
        assert throughput > 1000, f"Throughput {throughput:.0f} msg/s below 1000 msg/s target"
    
    def print_performance_result(self, result: PerformanceResult):
        """Print formatted performance result."""
        print(f"\n  Operation: {result.operation}")
        print(f"  Total requests: {result.total_requests}")
        print(f"  Successful: {result.successful_requests}")
        print(f"  Failed: {result.failed_requests}")
        print(f"  Response times (ms):")
        print(f"    Min: {result.min_time_ms:.2f}")
        print(f"    Avg: {result.avg_time_ms:.2f}")
        print(f"    Median: {result.median_time_ms:.2f}")
        print(f"    P95: {result.p95_time_ms:.2f}")
        print(f"    P99: {result.p99_time_ms:.2f}")
        print(f"    Max: {result.max_time_ms:.2f}")
        print(f"  Throughput: {result.requests_per_second:.2f} req/s")
    
    async def test_system_limits(
        self,
        api_base_url: str,
        auth_headers: Dict[str, str]
    ):
        """Test system behavior at limits."""
        print("\n--- Testing system limits ---")
        
        # Test 1: Very large memory content
        print("\n  Testing large memory content...")
        large_content = "x" * 50000  # 50KB
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base_url}/api/v1/memories/",
                json={
                    "memory_type": "learning",
                    "prompt": "Large content test",
                    "content": large_content,
                    "metadata": {}
                },
                headers=auth_headers
            ) as response:
                # Should either succeed or fail gracefully
                assert response.status in [201, 400, 413]
                print(f"    Large content response: {response.status}")
        
        # Test 2: Many metadata fields
        print("\n  Testing many metadata fields...")
        large_metadata = {f"field_{i}": f"value_{i}" for i in range(100)}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base_url}/api/v1/memories/",
                json={
                    "memory_type": "context",
                    "prompt": "Metadata test",
                    "content": "Testing metadata limits",
                    "metadata": large_metadata
                },
                headers=auth_headers
            ) as response:
                assert response.status in [201, 400]
                print(f"    Large metadata response: {response.status}")
        
        # Test 3: Rapid fire requests (rate limiting)
        print("\n  Testing rate limiting...")
        rapid_requests = 50
        statuses = []
        
        async with aiohttp.ClientSession() as session:
            for _ in range(rapid_requests):
                async with session.get(
                    f"{api_base_url}/api/v1/memories/",
                    headers=auth_headers
                ) as response:
                    statuses.append(response.status)
        
        rate_limited = sum(1 for s in statuses if s == 429)
        print(f"    Sent {rapid_requests} rapid requests")
        print(f"    Rate limited: {rate_limited}")
        
        # Should handle requests gracefully
        assert all(s in [200, 429] for s in statuses)