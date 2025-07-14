"""
Main FastAPI application module.

This module creates and configures the FastAPI application with all middleware,
routers, and event handlers for the CoachNTT.ai API.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.abstraction.concrete_engine import ConcreteAbstractionEngine
from ..core.validation.validator import SafetyValidator
from .config import get_settings
from .dependencies import (
    close_db_pool,
    get_db_pool,
    get_safety_validator,
)
from .middleware import (
    AuthenticationMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    SafetyMiddleware,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting CoachNTT.ai API")
    
    # Initialize database pool
    await get_db_pool()
    
    # Initialize core services
    abstraction_engine = ConcreteAbstractionEngine()
    safety_validator = await get_safety_validator()
    
    # Store in app state for middleware
    app.state.abstraction_engine = abstraction_engine
    app.state.safety_validator = safety_validator
    
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CoachNTT.ai API")
    
    # Close database connections
    await close_db_pool()
    
    logger.info("API shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=list(settings.cors_allowed_methods),
        allow_headers=list(settings.cors_allowed_headers),
    )
    
    # Add compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add custom middleware in reverse order (last added is first executed)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    
    # Note: Safety and Logging middleware are not added in Session 4.1a
    # They will be added in Session 4.1b with proper service integration
    
    # Exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with abstracted details."""
        # Abstract error details in production
        if settings.is_production and exc.status_code >= 500:
            detail = "An internal error occurred"
        else:
            detail = str(exc.detail)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": getattr(request.state, "request_id", None),
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with abstracted field names."""
        # Abstract field names in production
        if settings.is_production:
            errors = [
                {
                    "loc": ["<field>"] * len(error["loc"]),
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ]
        else:
            errors = exc.errors()
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "errors": errors,
                "request_id": getattr(request.state, "request_id", None),
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions safely."""
        logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected error occurred",
                "error_code": "INTERNAL_ERROR",
                "request_id": getattr(request.state, "request_id", None),
            }
        )
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "name": settings.api_title,
            "version": settings.api_version,
            "description": settings.api_description,
            "status": "operational",
            "safety_enabled": settings.safety_validation_enabled,
            "rate_limiting_enabled": settings.rate_limit_enabled,
        }
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        # TODO: Add database and service health checks
        return {
            "status": "healthy",
            "service": "api",
        }
    
    # Import and include routers
    from .routers import memory, graph, integration
    
    app.include_router(
        memory.router,
        prefix="/api/v1/memories",
        tags=["Memories"]
    )
    
    app.include_router(
        graph.router,
        prefix="/api/v1/graph",
        tags=["Knowledge Graph"]
    )
    
    app.include_router(
        integration.router,
        prefix="/api/v1/integrations",
        tags=["Integrations"]
    )
    
    return app


def get_application() -> FastAPI:
    """Get configured FastAPI application."""
    app = create_application()
    return app


# Create application instance
app = get_application()