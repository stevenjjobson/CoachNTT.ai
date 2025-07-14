"""
Dependency injection for API services.

This module provides dependency injection functions for accessing core services
and repositories throughout the API, ensuring proper initialization and cleanup.
"""

import logging
from datetime import datetime, timedelta
from typing import Annotated, AsyncGenerator, Dict, Any, Optional

import asyncpg
from fastapi import Depends, HTTPException, status, WebSocket, WebSocketException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ..core.memory.repository import SafeMemoryRepository
from ..core.intent.engine import IntentEngine
from ..core.embeddings.service import EmbeddingService
from ..core.validation.validator import SafetyValidator
from ..services.vault.graph_builder import KnowledgeGraphBuilder
from ..services.vault.sync_engine import VaultSyncEngine
from ..services.documentation.generator import DocumentationGenerator
from .config import get_settings

logger = logging.getLogger(__name__)

# Security scheme for JWT authentication
security = HTTPBearer()

# Global service instances
_db_pool: Optional[asyncpg.Pool] = None
_memory_repository: Optional[SafeMemoryRepository] = None
_intent_engine: Optional[IntentEngine] = None
_embedding_service: Optional[EmbeddingService] = None
_safety_validator: Optional[SafetyValidator] = None
_graph_builder: Optional[KnowledgeGraphBuilder] = None
_vault_sync: Optional[VaultSyncEngine] = None
_doc_generator: Optional[DocumentationGenerator] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool."""
    global _db_pool
    
    if _db_pool is None:
        settings = get_settings()
        _db_pool = await asyncpg.create_pool(
            settings.database_url.get_secret_value(),
            min_size=5,
            max_size=settings.database_pool_size,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            command_timeout=10.0,
        )
        logger.info("Database pool created")
    
    return _db_pool


async def close_db_pool():
    """Close database connection pool."""
    global _db_pool
    
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database pool closed")


async def get_memory_repository() -> SafeMemoryRepository:
    """Get memory repository instance."""
    global _memory_repository
    
    if _memory_repository is None:
        pool = await get_db_pool()
        _memory_repository = SafeMemoryRepository(pool)
        logger.info("Memory repository initialized")
    
    return _memory_repository


async def get_intent_engine() -> IntentEngine:
    """Get intent engine instance."""
    global _intent_engine
    
    if _intent_engine is None:
        memory_repo = await get_memory_repository()
        _intent_engine = IntentEngine(memory_repo)
        logger.info("Intent engine initialized")
    
    return _intent_engine


async def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance."""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        logger.info("Embedding service initialized")
    
    return _embedding_service


async def get_safety_validator() -> SafetyValidator:
    """Get safety validator instance."""
    global _safety_validator
    
    if _safety_validator is None:
        settings = get_settings()
        _safety_validator = SafetyValidator(
            min_safety_score=float(settings.safety_min_score)
        )
        logger.info("Safety validator initialized")
    
    return _safety_validator


async def get_graph_builder() -> KnowledgeGraphBuilder:
    """Get knowledge graph builder instance."""
    global _graph_builder
    
    if _graph_builder is None:
        memory_repo = await get_memory_repository()
        embedding_service = await get_embedding_service()
        _graph_builder = KnowledgeGraphBuilder(memory_repo, embedding_service)
        logger.info("Graph builder initialized")
    
    return _graph_builder


async def get_vault_sync_engine() -> VaultSyncEngine:
    """Get vault sync engine instance."""
    global _vault_sync
    
    if _vault_sync is None:
        from pathlib import Path
        from ...services.vault.models import VaultSyncConfig
        
        memory_repo = await get_memory_repository()
        safety_validator = await get_safety_validator()
        
        # Create config with default vault path
        config = VaultSyncConfig(
            vault_path=Path("vault"),
            enable_templates=True,
            enable_backlinks=True,
            enable_tag_extraction=True
        )
        
        _vault_sync = VaultSyncEngine(
            config=config,
            memory_repository=memory_repo,
            safety_validator=safety_validator
        )
        logger.info("Vault sync engine initialized")
    
    return _vault_sync


async def get_documentation_generator() -> DocumentationGenerator:
    """Get documentation generator instance."""
    global _doc_generator
    
    if _doc_generator is None:
        from pathlib import Path
        from ...services.documentation.models import DocumentationConfig
        
        safety_validator = await get_safety_validator()
        
        # Create config with default settings
        config = DocumentationConfig(
            project_root=Path("."),
            output_directory=Path("./docs"),
            enable_api_docs=True,
            enable_diagrams=True
        )
        
        _doc_generator = DocumentationGenerator(
            config=config,
            safety_validator=safety_validator
        )
        logger.info("Documentation generator initialized")
    
    return _doc_generator


async def get_knowledge_graph_builder() -> KnowledgeGraphBuilder:
    """Get knowledge graph builder instance."""
    global _graph_builder
    
    if _graph_builder is None:
        memory_repo = await get_memory_repository()
        embedding_service = await get_embedding_service()
        safety_validator = await get_safety_validator()
        
        _graph_builder = KnowledgeGraphBuilder(
            memory_repository=memory_repo,
            embedding_service=embedding_service,
            safety_validator=safety_validator
        )
        logger.info("Knowledge graph builder initialized")
    
    return _graph_builder


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    settings = get_settings()
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return payload."""
    settings = get_settings()
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check expiration
        if "exp" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing expiration",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_payload: Annotated[Dict[str, Any], Depends(verify_token)]
) -> Dict[str, Any]:
    """Get current authenticated user from token."""
    # Extract user information from token payload
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # In a real application, you might fetch user details from database
    # For now, return the token payload as user info
    return {
        "user_id": user_id,
        "email": token_payload.get("email"),
        "is_active": token_payload.get("is_active", True),
        "permissions": token_payload.get("permissions", []),
    }


# Optional dependency for authenticated endpoints
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]


# Pagination dependencies
async def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
) -> Dict[str, int]:
    """Get pagination parameters."""
    settings = get_settings()
    
    # Validate page number
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1"
        )
    
    # Validate and constrain page size
    if page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be >= 1"
        )
    
    # Apply maximum page size constraint
    actual_max = min(max_page_size, settings.max_page_size)
    if page_size > actual_max:
        page_size = actual_max
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    return {
        "page": page,
        "page_size": page_size,
        "offset": offset,
        "limit": page_size,
    }


# Type alias for pagination parameters
PaginationParams = Annotated[Dict[str, int], Depends(get_pagination_params)]


# WebSocket authentication functions
async def verify_websocket_token(websocket: WebSocket, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Verify JWT token for WebSocket connections."""
    settings = get_settings()
    
    try:
        # Try to get token from different sources
        auth_token = None
        
        if token:
            # Token provided as parameter
            auth_token = token
        else:
            # Try to get token from query parameters
            auth_token = websocket.query_params.get("token")
        
        if not auth_token:
            # Try to get token from headers
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                auth_token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not auth_token:
            logger.warning("No token provided for WebSocket connection")
            return None
        
        # Verify the token
        payload = jwt.decode(
            auth_token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check expiration
        if "exp" not in payload:
            logger.warning("WebSocket token missing expiration")
            return None
        
        # Check if token is expired
        exp_timestamp = payload["exp"]
        current_timestamp = datetime.utcnow().timestamp()
        
        if exp_timestamp < current_timestamp:
            logger.warning("WebSocket token expired")
            return None
        
        logger.debug(f"WebSocket authentication successful for user {payload.get('sub', 'unknown')}")
        return payload
        
    except JWTError as e:
        logger.warning(f"WebSocket JWT verification failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        return None


async def get_websocket_user(
    websocket: WebSocket,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """Get authenticated user for WebSocket connections."""
    payload = await verify_websocket_token(websocket, token)
    
    if not payload:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
    
    user_id = payload.get("sub")
    if not user_id:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
    
    # Return user information from token payload
    return {
        "sub": user_id,
        "user_id": user_id,
        "email": payload.get("email"),
        "is_active": payload.get("is_active", True),
        "permissions": payload.get("permissions", []),
        "exp": payload.get("exp"),
    }


# WebSocket authentication dependency
WebSocketUser = Annotated[Dict[str, Any], Depends(get_websocket_user)]