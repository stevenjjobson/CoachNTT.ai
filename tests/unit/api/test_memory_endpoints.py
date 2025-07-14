"""
Tests for memory API endpoints.

This module tests the memory CRUD operations and search functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from src.api.models.memory import MemoryCreate, MemoryResponse
from src.core.memory.models import MemoryType, AbstractMemoryEntry


class TestMemoryEndpoints:
    """Test memory API endpoints."""
    
    @pytest.fixture
    def sample_memory_create(self):
        """Sample memory creation data."""
        return MemoryCreate(
            memory_type=MemoryType.LEARNING,
            prompt="How to implement rate limiting?",
            content="Rate limiting can be implemented using token bucket algorithm...",
            metadata={"tags": ["rate-limiting", "api"]}
        )
    
    @pytest.fixture
    def sample_memory_entry(self):
        """Sample memory database entry."""
        return AbstractMemoryEntry(
            memory_id=uuid4(),
            memory_type=MemoryType.LEARNING,
            abstracted_prompt="How to implement <rate_limiting>?",
            abstracted_content="<Rate_limiting> can be implemented using <algorithm>...",
            safety_score=Decimal("0.95"),
            temporal_weight=Decimal("0.85"),
            metadata={"tags": ["api", "security"]},
            created_at=datetime.utcnow(),
            accessed_at=datetime.utcnow(),
            access_count=1,
        )
    
    @patch('src.api.routers.memory.get_memory_repository')
    @patch('src.api.dependencies.verify_token')
    def test_create_memory_success(self, mock_verify_token, mock_get_repo, sample_memory_create, sample_memory_entry):
        """Test successful memory creation."""
        # Setup mocks
        mock_verify_token.return_value = {"sub": "user123", "email": "test@example.com"}
        mock_repo = AsyncMock()
        mock_repo.create_memory.return_value = sample_memory_entry
        mock_get_repo.return_value = mock_repo
        
        from fastapi.testclient import TestClient
        from src.api.main import create_application
        
        app = create_application()
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/memories/",
            json=sample_memory_create.model_dump(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions would go here
        # Note: This is a placeholder test structure for Session 4.1a
        # Full implementation will be in the test files
    
    def test_memory_response_model_validation(self, sample_memory_entry):
        """Test memory response model validation."""
        memory_response = MemoryResponse.model_validate(sample_memory_entry)
        
        assert memory_response.memory_id == sample_memory_entry.memory_id
        assert memory_response.memory_type == sample_memory_entry.memory_type
        assert memory_response.abstracted_prompt == sample_memory_entry.abstracted_prompt
        assert memory_response.safety_score == sample_memory_entry.safety_score
        assert memory_response.temporal_weight == sample_memory_entry.temporal_weight
    
    def test_memory_create_validation(self):
        """Test memory creation model validation."""
        # Valid creation
        valid_create = MemoryCreate(
            memory_type="learning",
            prompt="Test prompt",
            content="Test content",
        )
        assert valid_create.memory_type == MemoryType.LEARNING
        
        # Invalid memory type
        with pytest.raises(ValueError):
            MemoryCreate(
                memory_type="invalid_type",
                prompt="Test prompt",
                content="Test content",
            )
        
        # Empty prompt
        with pytest.raises(ValueError):
            MemoryCreate(
                memory_type="learning",
                prompt="",
                content="Test content",
            )
    
    def test_memory_search_model(self):
        """Test memory search model validation."""
        from src.api.models.memory import MemorySearch
        
        search = MemorySearch(
            query="test search",
            memory_types=["learning", "decision"],
            min_safety_score=Decimal("0.8"),
            limit=10,
        )
        
        assert search.query == "test search"
        assert MemoryType.LEARNING in search.memory_types
        assert MemoryType.DECISION in search.memory_types
        assert search.min_safety_score == Decimal("0.8")
        assert search.limit == 10