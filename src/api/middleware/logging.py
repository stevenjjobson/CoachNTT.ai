"""
Logging middleware with automatic content abstraction.

This middleware logs all requests and responses while ensuring sensitive
information is automatically abstracted for safety.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...core.abstraction.concrete_engine import ConcreteAbstractionEngine
from ..config import get_settings

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request/response logging with abstraction."""
    
    def __init__(self, app, abstraction_engine: Optional[ConcreteAbstractionEngine] = None):
        super().__init__(app)
        self.settings = get_settings()
        self.abstraction_engine = abstraction_engine
        self.abstract_logs = self.settings.log_abstract_content
        
        # Paths to exclude from detailed logging
        self.excluded_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        
        # Headers to always exclude from logs
        self.excluded_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with comprehensive logging."""
        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Skip detailed logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Log request
        await self._log_request(request, request_id)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        await self._log_response(response, request_id, duration_ms)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request with abstraction."""
        try:
            # Build log entry
            log_entry = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": self._abstract_dict(dict(request.query_params)),
                "client_host": self._abstract_ip(request.client.host) if request.client else None,
                "headers": self._filter_headers(dict(request.headers)),
            }
            
            # Add user info if authenticated
            if hasattr(request.state, "user"):
                log_entry["user_id"] = request.state.user.get("user_id")
            
            # Log request body for certain methods
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await self._get_request_body(request)
                if body:
                    log_entry["body_preview"] = self._abstract_body(body)
            
            # Log based on format setting
            if self.settings.log_format == "json":
                logger.info(json.dumps({
                    "event": "api_request",
                    **log_entry
                }))
            else:
                logger.info(
                    f"API Request: {request.method} {request.url.path} "
                    f"[{request_id}] from {log_entry['client_host']}"
                )
                
        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")
    
    async def _log_response(self, response: Response, request_id: str, duration_ms: float):
        """Log outgoing response with abstraction."""
        try:
            # Build log entry
            log_entry = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "headers": self._filter_headers(dict(response.headers)),
            }
            
            # Add response size if available
            if "content-length" in response.headers:
                log_entry["response_size"] = int(response.headers["content-length"])
            
            # Log based on format setting
            if self.settings.log_format == "json":
                logger.info(json.dumps({
                    "event": "api_response",
                    **log_entry
                }))
            else:
                logger.info(
                    f"API Response: {response.status_code} "
                    f"[{request_id}] in {duration_ms:.2f}ms"
                )
                
        except Exception as e:
            logger.error(f"Error logging response: {str(e)}")
    
    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract request body for logging."""
        try:
            if not hasattr(request, "_body"):
                request._body = await request.body()
            
            if request._body:
                return json.loads(request._body)
            return None
            
        except Exception:
            return None
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter sensitive headers."""
        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in self.excluded_headers:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered
    
    def _abstract_ip(self, ip: str) -> str:
        """Abstract IP address for privacy."""
        if not self.abstract_logs or not ip:
            return ip
        
        # Keep first two octets for general location
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.***"
        return "***REDACTED***"
    
    def _abstract_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Abstract dictionary values."""
        if not self.abstract_logs or not self.abstraction_engine:
            return data
        
        abstracted = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.abstraction_engine.abstract(value)
                abstracted[key] = result.abstracted_content
            else:
                abstracted[key] = value
        
        return abstracted
    
    def _abstract_body(self, body: Any, max_length: int = 200) -> str:
        """Create abstracted preview of request body."""
        try:
            if not body:
                return "empty"
            
            # Convert to string
            body_str = json.dumps(body) if not isinstance(body, str) else body
            
            # Truncate if too long
            if len(body_str) > max_length:
                body_str = body_str[:max_length] + "..."
            
            # Abstract if enabled
            if self.abstract_logs and self.abstraction_engine:
                result = self.abstraction_engine.abstract(body_str)
                return result.abstracted_content
            
            return body_str
            
        except Exception:
            return "***ERROR ABSTRACTING BODY***"