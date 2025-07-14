"""
Root pytest configuration and shared fixtures for CoachNTT.ai tests.

Provides test database setup, shared fixtures, and utility functions
used across all test modules.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any
from datetime import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
from src.core.validation.validator import SafetyValidator
from src.core.embeddings.service import EmbeddingService
from src.core.intent.engine import IntentEngine
from src.core.memory.repository import SafeMemoryRepository
from src.api.main import app
from src.api.config import Settings


# Test configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_cognitive_coding_partner"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test settings."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        testing=True,
        debug=True,
        safety_validation_enabled=True,
        safety_min_score=0.8,
        rate_limit_enabled=False,
        jwt_secret_key="test-secret-key-for-testing-only",
        api_keys=["test-api-key"],
    )


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
def abstraction_engine() -> ConcreteAbstractionEngine:
    """Provide abstraction engine instance."""
    return ConcreteAbstractionEngine()


@pytest_asyncio.fixture(scope="function")
async def safety_validator() -> SafetyValidator:
    """Provide safety validator instance."""
    validator = SafetyValidator()
    return validator


@pytest_asyncio.fixture(scope="function")
async def embedding_service() -> EmbeddingService:
    """Provide embedding service instance."""
    service = EmbeddingService()
    yield service
    # Clear cache after each test
    service.cache.clear()


@pytest_asyncio.fixture(scope="function") 
async def intent_engine(embedding_service) -> IntentEngine:
    """Provide intent engine instance."""
    engine = IntentEngine(embedding_service=embedding_service)
    return engine


@pytest_asyncio.fixture(scope="function")
async def memory_repository(
    test_db_session,
    abstraction_engine,
    embedding_service,
    intent_engine,
    safety_validator
) -> SafeMemoryRepository:
    """Provide memory repository instance."""
    repo = SafeMemoryRepository(
        db_session=test_db_session,
        abstraction_engine=abstraction_engine,
        embedding_service=embedding_service,
        intent_engine=intent_engine,
        safety_validator=safety_validator,
    )
    return repo


@pytest_asyncio.fixture(scope="function")
async def api_client(test_settings) -> AsyncGenerator[AsyncClient, None]:
    """Provide test API client."""
    # Override settings for testing
    app.state.settings = test_settings
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Sample data fixtures
@pytest.fixture
def sample_memory_data() -> Dict[str, Any]:
    """Provide sample memory data."""
    return {
        "memory_type": "learning",
        "prompt": "Test prompt for learning",
        "content": "This is test content without any concrete references",
        "metadata": {
            "topic": "testing",
            "source": "unit_test",
        }
    }


@pytest.fixture
def sample_unsafe_content() -> str:
    """Provide sample content with concrete references."""
    return """
    Here is a path: /home/user/project/secret.py
    And an email: user@example.com
    With a URL: https://api.example.com/v1/endpoint
    And some credentials: API_KEY=sk-1234567890
    """


@pytest.fixture
def sample_safe_content() -> str:
    """Provide sample safe abstracted content."""
    return """
    This is completely safe content discussing patterns and concepts.
    We can talk about <project_directory> and <user_email> abstractly.
    The <api_endpoint> pattern is useful for REST design.
    Environment variables like <api_credential> should be kept secure.
    """


@pytest.fixture
def sample_code_snippets() -> Dict[str, str]:
    """Provide sample code snippets for testing."""
    return {
        "python": """
def calculate_sum(numbers: List[int]) -> int:
    '''Calculate sum of numbers.'''
    total = 0
    for num in numbers:
        total += num
    return total
""",
        "javascript": """
function calculateSum(numbers) {
    // Calculate sum of numbers
    let total = 0;
    for (const num of numbers) {
        total += num;
    }
    return total;
}
""",
        "typescript": """
function calculateSum(numbers: number[]): number {
    // Calculate sum of numbers
    let total: number = 0;
    for (const num of numbers) {
        total += num;
    }
    return total;
}
"""
    }


@pytest.fixture
def sample_graph_data() -> Dict[str, Any]:
    """Provide sample knowledge graph data."""
    return {
        "nodes": [
            {
                "id": str(uuid.uuid4()),
                "type": "memory",
                "content": "Understanding of testing patterns",
                "metadata": {"topic": "testing"},
                "safety_score": 0.95,
            },
            {
                "id": str(uuid.uuid4()),
                "type": "code",
                "content": "Test utility functions",
                "metadata": {"language": "python"},
                "safety_score": 0.98,
            }
        ],
        "edges": [
            {
                "source": 0,
                "target": 1,
                "type": "relates_to",
                "weight": 0.8,
            }
        ]
    }


# Utility functions
@pytest.fixture
def assert_safety_score():
    """Provide assertion helper for safety scores."""
    def _assert(score: float, min_score: float = 0.8):
        assert score >= min_score, f"Safety score {score} below minimum {min_score}"
    return _assert


@pytest.fixture
def assert_abstraction():
    """Provide assertion helper for abstraction validation."""
    def _assert(content: str, should_contain: list = None, should_not_contain: list = None):
        if should_contain:
            for pattern in should_contain:
                assert pattern in content, f"Expected pattern '{pattern}' not found"
        
        if should_not_contain:
            for pattern in should_not_contain:
                assert pattern not in content, f"Forbidden pattern '{pattern}' found"
    
    return _assert


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "safety: Safety validation tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_api: Requires API server")
    config.addinivalue_line("markers", "requires_docker: Requires Docker")


# Skip markers for CI
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    
    if os.getenv("CI"):
        skip_docker = pytest.mark.skip(reason="Docker not available in CI")
        for item in items:
            if "requires_docker" in item.keywords:
                item.add_marker(skip_docker)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow", 
        action="store_true", 
        default=False, 
        help="run slow tests"
    )
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="run performance tests"
    )