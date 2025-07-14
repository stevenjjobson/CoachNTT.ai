"""
Rate limiting middleware using token bucket algorithm.

This middleware implements rate limiting to prevent API abuse and ensure
fair usage across all clients.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import get_settings

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        async with self.lock:
            # Refill tokens based on time passed
            now = time.time()
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
            
            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def get_status(self) -> Tuple[float, float]:
        """Get current bucket status.
        
        Returns:
            Tuple of (available_tokens, seconds_until_next_token)
        """
        async with self.lock:
            # Refill tokens to get current count
            now = time.time()
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            
            current_tokens = min(self.capacity, self.tokens + tokens_to_add)
            
            # Calculate time until next token
            if current_tokens < self.capacity:
                seconds_until_next = (1 - (tokens_to_add % 1)) / self.refill_rate
            else:
                seconds_until_next = 0
            
            return current_tokens, seconds_until_next


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for API rate limiting."""
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.enabled = self.settings.rate_limit_enabled
        
        # Rate limit configuration
        self.requests_per_minute = self.settings.rate_limit_requests_per_minute
        self.burst_size = self.settings.rate_limit_burst_size
        
        # Calculate refill rate (tokens per second)
        self.refill_rate = self.requests_per_minute / 60.0
        
        # Client buckets
        self.client_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.burst_size, self.refill_rate)
        )
        
        # Cleanup task for old buckets
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
        # Paths excluded from rate limiting
        self.excluded_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip if rate limiting is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get or create token bucket for client
        bucket = self.client_buckets[client_id]
        
        # Try to consume a token
        allowed = await bucket.consume()
        
        if not allowed:
            # Get bucket status for headers
            tokens_available, seconds_until_next = await bucket.get_status()
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": str(int(tokens_available)),
                    "X-RateLimit-Reset": str(int(time.time() + seconds_until_next)),
                    "Retry-After": str(int(seconds_until_next) + 1),
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        tokens_available, _ = await bucket.get_status()
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(tokens_available))
        
        # Periodic cleanup of old buckets
        await self._cleanup_old_buckets()
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for client."""
        # Try authenticated user ID first
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("user_id")
            if user_id:
                return f"user:{user_id}"
        
        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"
        
        # Last resort: use a generic identifier
        return "anonymous"
    
    async def _cleanup_old_buckets(self):
        """Remove old token buckets to prevent memory leak."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = now
        
        # Find buckets that haven't been used recently
        stale_threshold = now - (self.cleanup_interval * 2)
        stale_clients = []
        
        for client_id, bucket in self.client_buckets.items():
            if bucket.last_refill < stale_threshold:
                stale_clients.append(client_id)
        
        # Remove stale buckets
        for client_id in stale_clients:
            del self.client_buckets[client_id]
        
        if stale_clients:
            logger.info(f"Cleaned up {len(stale_clients)} stale rate limit buckets")