"""
Authentication middleware for API security.

This middleware provides JWT-based authentication with flexible token sources
and automatic token refresh capabilities.
"""

import logging
from typing import Optional, Set

from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import get_settings

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication with multiple token sources."""
    
    def __init__(
        self,
        app,
        public_paths: Optional[Set[str]] = None,
        token_sources: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.settings = get_settings()
        
        # Paths that don't require authentication
        self.public_paths = public_paths or {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        }
        
        # Token sources in order of preference
        self.token_sources = token_sources or {
            "header",  # Authorization: Bearer <token>
            "cookie",  # auth_token cookie
            "query",   # ?token=<token>
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication."""
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract token from various sources
        token = await self._extract_token(request)
        
        if not token:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "error_code": "AUTH_REQUIRED"
                }
            )
        
        # Verify token
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key.get_secret_value(),
                algorithms=[self.settings.jwt_algorithm]
            )
            
            # Add user info to request state
            request.state.user = {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "permissions": payload.get("permissions", []),
                "is_active": payload.get("is_active", True),
            }
            
            # Check if user is active
            if not request.state.user["is_active"]:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "User account is inactive",
                        "error_code": "USER_INACTIVE"
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Optionally refresh token if close to expiration
            if self._should_refresh_token(payload):
                new_token = self._create_refresh_token(payload)
                response.headers["X-Auth-Token-Refresh"] = new_token
            
            return response
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid or expired token",
                    "error_code": "INVALID_TOKEN"
                }
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Authentication error",
                    "error_code": "AUTH_ERROR"
                }
            )
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public."""
        # Exact match
        if path in self.public_paths:
            return True
        
        # Prefix match for versioned APIs
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        
        return False
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Extract token from various sources."""
        token = None
        
        # Try header first (Authorization: Bearer <token>)
        if "header" in self.token_sources:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                if token:
                    return token
        
        # Try cookie
        if "cookie" in self.token_sources:
            token = request.cookies.get("auth_token")
            if token:
                return token
        
        # Try query parameter
        if "query" in self.token_sources:
            token = request.query_params.get("token")
            if token:
                return token
        
        return None
    
    def _should_refresh_token(self, payload: dict) -> bool:
        """Check if token should be refreshed."""
        # Don't refresh if no expiration
        if "exp" not in payload:
            return False
        
        # Refresh if less than 50% of lifetime remaining
        from datetime import datetime
        
        exp_timestamp = payload["exp"]
        iat_timestamp = payload.get("iat", 0)
        
        if iat_timestamp == 0:
            return False
        
        current_timestamp = datetime.utcnow().timestamp()
        total_lifetime = exp_timestamp - iat_timestamp
        remaining_lifetime = exp_timestamp - current_timestamp
        
        return remaining_lifetime < (total_lifetime * 0.5)
    
    def _create_refresh_token(self, old_payload: dict) -> str:
        """Create a refreshed token with updated expiration."""
        from datetime import datetime, timedelta
        
        # Copy payload and update expiration
        new_payload = old_payload.copy()
        new_payload["exp"] = datetime.utcnow() + timedelta(
            minutes=self.settings.jwt_expiration_minutes
        )
        new_payload["iat"] = datetime.utcnow()
        
        # Encode new token
        return jwt.encode(
            new_payload,
            self.settings.jwt_secret_key.get_secret_value(),
            algorithm=self.settings.jwt_algorithm
        )