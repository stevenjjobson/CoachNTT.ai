"""
Tests for API foundation components.

This module tests the basic API setup, configuration, and middleware.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.config import APISettings, get_settings
from src.api.main import create_application


class TestAPIFoundation:
    """Test API foundation setup."""
    
    def test_api_settings_defaults(self):
        """Test API settings have correct defaults."""
        settings = APISettings()
        
        assert settings.api_title == "CoachNTT.ai API"
        assert settings.api_version == "1.0.0"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.safety_min_score == 0.8
        assert settings.rate_limit_enabled is True
        assert settings.safety_auto_abstract is True
    
    def test_api_settings_environment_override(self, monkeypatch):
        """Test API settings can be overridden by environment variables."""
        monkeypatch.setenv("COACHNTT_API_TITLE", "Test API")
        monkeypatch.setenv("COACHNTT_PORT", "9000")
        monkeypatch.setenv("COACHNTT_SAFETY_MIN_SCORE", "0.9")
        
        settings = APISettings()
        
        assert settings.api_title == "Test API"
        assert settings.port == 9000
        assert settings.safety_min_score == 0.9
    
    @patch('src.api.dependencies.get_db_pool')
    def test_app_creation(self, mock_get_db_pool):
        """Test FastAPI application can be created."""
        mock_get_db_pool.return_value = AsyncMock()
        
        app = create_application()
        
        assert app.title == "CoachNTT.ai API"
        assert app.version == "1.0.0"
        assert "/api/v1/memories" in [route.path for route in app.routes]
    
    @patch('src.api.dependencies.get_db_pool')
    @patch('src.api.dependencies.get_safety_validator')
    def test_root_endpoint(self, mock_get_safety_validator, mock_get_db_pool):
        """Test root endpoint returns correct information."""
        mock_get_db_pool.return_value = AsyncMock()
        mock_get_safety_validator.return_value = AsyncMock()
        
        app = create_application()
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CoachNTT.ai API"
        assert data["status"] == "operational"
        assert "safety_enabled" in data
        assert "rate_limiting_enabled" in data
    
    @patch('src.api.dependencies.get_db_pool')
    @patch('src.api.dependencies.get_safety_validator')
    def test_health_endpoint(self, mock_get_safety_validator, mock_get_db_pool):
        """Test health check endpoint."""
        mock_get_db_pool.return_value = AsyncMock()
        mock_get_safety_validator.return_value = AsyncMock()
        
        app = create_application()
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api"
    
    def test_cors_middleware_configured(self):
        """Test CORS middleware is properly configured."""
        settings = get_settings()
        
        assert "http://localhost:3000" in settings.cors_allowed_origins
        assert "http://localhost:8080" in settings.cors_allowed_origins
        assert settings.cors_allow_credentials is True
        assert "GET" in settings.cors_allowed_methods
        assert "POST" in settings.cors_allowed_methods
    
    def test_rate_limiting_config(self):
        """Test rate limiting configuration."""
        settings = get_settings()
        
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_requests_per_minute == 60
        assert settings.rate_limit_burst_size == 10
    
    def test_safety_config(self):
        """Test safety configuration."""
        settings = get_settings()
        
        assert settings.safety_validation_enabled is True
        assert settings.safety_auto_abstract is True
        assert settings.safety_min_score == 0.8
        assert settings.safety_max_retries == 3