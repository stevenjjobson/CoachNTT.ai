"""
API Configuration with safety-first settings.

This module provides centralized configuration for the CoachNTT.ai API,
emphasizing safety validation, abstraction enforcement, and secure defaults.
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional, Set

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API configuration with safety-first defaults."""
    
    model_config = SettingsConfigDict(
        env_prefix="COACHNTT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Reject unknown fields for safety
    )
    
    # Basic API Configuration
    api_title: str = Field(
        default="CoachNTT.ai API",
        description="API title for documentation"
    )
    api_description: str = Field(
        default="Safety-first cognitive coding partner REST API",
        description="API description for documentation"
    )
    api_version: str = Field(
        default="1.0.0",
        description="API version"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="API host address"
    )
    port: int = Field(
        default=8000,
        description="API port",
        ge=1,
        le=65535
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload (development only)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (development only)"
    )
    
    # Security Configuration
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-production"),
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_expiration_minutes: int = Field(
        default=30,
        description="JWT token expiration in minutes",
        ge=5,
        le=1440  # Max 24 hours
    )
    
    # CORS Configuration
    cors_allowed_origins: Set[str] = Field(
        default={"http://localhost:3000", "http://localhost:8080"},
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    cors_allowed_methods: Set[str] = Field(
        default={"GET", "POST", "PUT", "DELETE", "OPTIONS"},
        description="Allowed HTTP methods"
    )
    cors_allowed_headers: Set[str] = Field(
        default={"*"},
        description="Allowed headers in CORS requests"
    )
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute per client",
        ge=1,
        le=1000
    )
    rate_limit_burst_size: int = Field(
        default=10,
        description="Burst size for rate limiting",
        ge=1,
        le=100
    )
    
    # Safety Configuration
    safety_min_score: Decimal = Field(
        default=Decimal("0.8"),
        description="Minimum safety score for content",
        ge=Decimal("0.0"),
        le=Decimal("1.0")
    )
    safety_auto_abstract: bool = Field(
        default=True,
        description="Automatically abstract concrete references"
    )
    safety_validation_enabled: bool = Field(
        default=True,
        description="Enable safety validation on all inputs"
    )
    safety_max_retries: int = Field(
        default=3,
        description="Maximum retries for safety validation",
        ge=1,
        le=10
    )
    
    # Database Configuration
    database_url: SecretStr = Field(
        default=SecretStr("postgresql+asyncpg://ccp_user:change_me@localhost:5432/cognitive_coding_partner"),
        description="PostgreSQL connection URL"
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size",
        ge=5,
        le=100
    )
    database_max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections",
        ge=0,
        le=50
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    log_abstract_content: bool = Field(
        default=True,
        description="Abstract sensitive content in logs"
    )
    
    # Performance Configuration
    max_page_size: int = Field(
        default=100,
        description="Maximum items per page",
        ge=10,
        le=500
    )
    default_page_size: int = Field(
        default=20,
        description="Default items per page",
        ge=10,
        le=100
    )
    request_timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=5,
        le=300
    )
    
    # WebSocket Configuration
    ws_heartbeat_interval: int = Field(
        default=30,
        description="WebSocket heartbeat interval in seconds",
        ge=10,
        le=300
    )
    ws_max_connections: int = Field(
        default=100,
        description="Maximum concurrent WebSocket connections",
        ge=10,
        le=1000
    )
    
    # Feature Flags
    enable_memory_clustering: bool = Field(
        default=True,
        description="Enable memory clustering features"
    )
    enable_intent_analysis: bool = Field(
        default=True,
        description="Enable intent analysis for searches"
    )
    enable_graph_visualization: bool = Field(
        default=True,
        description="Enable knowledge graph visualization"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = {"json", "text"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format: {v}")
        return v.lower()
    
    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        valid_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in valid_algorithms:
            raise ValueError(f"Invalid JWT algorithm: {v}")
        return v
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        url = self.database_url.get_secret_value()
        return url.replace("+asyncpg", "")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not (self.debug or self.reload)
    
    @property
    def cors_allow_all(self) -> bool:
        """Check if CORS allows all origins (development only)."""
        return "*" in self.cors_allowed_origins and not self.is_production


# Global settings instance
_settings: Optional[APISettings] = None


def get_settings() -> APISettings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = APISettings()
    return _settings


def reload_settings() -> APISettings:
    """Reload settings from environment."""
    global _settings
    _settings = APISettings()
    return _settings