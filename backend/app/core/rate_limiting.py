"""
Rate limiting middleware and utilities for API endpoints.
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.cache import cache
from app.core.config import settings


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or cache.redis
        self.fallback_storage: Dict[str, deque] = defaultdict(deque)

    async def is_allowed(
        self, key: str, limit: int, window_seconds: int, identifier: str = "default"
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed based on rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            identifier: Additional identifier for different rate limit types

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        now = time.time()
        redis_key = f"rate_limit:{identifier}:{key}"

        try:
            # Use Redis for distributed rate limiting
            if self.redis:
                return await self._redis_sliding_window(
                    redis_key, limit, window_seconds, now
                )
            else:
                # Fallback to in-memory rate limiting
                return self._memory_sliding_window(
                    redis_key, limit, window_seconds, now
                )
        except Exception:
            # If Redis fails, use in-memory fallback
            return self._memory_sliding_window(redis_key, limit, window_seconds, now)

    async def _redis_sliding_window(
        self, key: str, limit: int, window_seconds: int, now: float
    ) -> Tuple[bool, int, int]:
        """Redis-based sliding window rate limiting."""
        pipe = self.redis.pipeline()

        # Remove expired entries
        pipe.zremrangebyscore(key, 0, now - window_seconds)

        # Count current requests
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiration
        pipe.expire(key, window_seconds + 1)

        results = await pipe.execute()
        current_requests = results[1]

        if current_requests < limit:
            remaining = limit - current_requests - 1
            reset_time = int(now + window_seconds)
            return True, remaining, reset_time
        else:
            # Remove the request we just added since it's not allowed
            await self.redis.zrem(key, str(now))
            remaining = 0
            reset_time = int(now + window_seconds)
            return False, remaining, reset_time

    def _memory_sliding_window(
        self, key: str, limit: int, window_seconds: int, now: float
    ) -> Tuple[bool, int, int]:
        """In-memory sliding window rate limiting (fallback)."""
        requests = self.fallback_storage[key]

        # Remove expired requests
        while requests and requests[0] <= now - window_seconds:
            requests.popleft()

        if len(requests) < limit:
            requests.append(now)
            remaining = limit - len(requests)
            reset_time = int(now + window_seconds)
            return True, remaining, reset_time
        else:
            remaining = 0
            reset_time = int(now + window_seconds)
            return False, remaining, reset_time


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

        # Rate limit configurations
        self.rate_limits = {
            "default": {"limit": settings.RATE_LIMIT_PER_MINUTE, "window": 60},
            "auth": {"limit": 10, "window": 60},  # Stricter for auth endpoints
            "analysis": {"limit": 20, "window": 60},  # Moderate for analysis
            "search": {"limit": 100, "window": 60},  # Higher for search
        }

        # Exempt paths from rate limiting
        self.exempt_paths = {
            "/health",
            "/health/detailed",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting to incoming requests."""

        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Determine rate limit type based on path
        rate_limit_type = self._get_rate_limit_type(request.url.path)
        rate_config = self.rate_limits.get(rate_limit_type, self.rate_limits["default"])

        # Get client identifier (IP address or user ID)
        client_id = self._get_client_identifier(request)

        # Check rate limit
        is_allowed, remaining, reset_time = await self.rate_limiter.is_allowed(
            key=client_id,
            limit=rate_config["limit"],
            window_seconds=rate_config["window"],
            identifier=rate_limit_type,
        )

        if not is_allowed:
            retry_after = reset_time - int(time.time())
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after=retry_after,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_config["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_rate_limit_type(self, path: str) -> str:
        """Determine rate limit type based on request path."""
        if "/auth/" in path or "/oauth/" in path:
            return "auth"
        elif "/analysis/" in path:
            return "analysis"
        elif "/search" in path or "/stocks/search" in path:
            return "search"
        else:
            return "default"

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from app.core.security import verify_token

            token = auth_header.split(" ")[1]
            user_id = verify_token(token)
            if user_id:
                return f"user:{user_id}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in case of multiple proxies
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request, limit: int, window_seconds: int = 60, identifier: str = "api"
) -> None:
    """
    Dependency function to check rate limits in specific endpoints.

    Args:
        request: FastAPI request object
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds
        identifier: Rate limit identifier

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    # Get client identifier
    middleware = RateLimitMiddleware(None)
    client_id = middleware._get_client_identifier(request)

    # Check rate limit
    is_allowed, remaining, reset_time = await rate_limiter.is_allowed(
        key=client_id, limit=limit, window_seconds=window_seconds, identifier=identifier
    )

    if not is_allowed:
        retry_after = reset_time - int(time.time())
        raise RateLimitExceeded(
            detail=f"Rate limit exceeded for {identifier}. Try again in {retry_after} seconds.",
            retry_after=retry_after,
        )


# Rate limiting decorators for specific use cases
def rate_limit(limit: int, window_seconds: int = 60, identifier: str = "api"):
    """
    Decorator for rate limiting specific endpoints.

    Args:
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds
        identifier: Rate limit identifier
    """

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            await check_rate_limit(request, limit, window_seconds, identifier)
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


class IPWhitelist:
    """IP address whitelist for bypassing rate limits."""

    def __init__(self):
        self.whitelist = set()
        # Add common internal/monitoring IPs
        self.whitelist.update(
            ["127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        )

    def add_ip(self, ip_address: str):
        """Add IP address to whitelist."""
        self.whitelist.add(ip_address)

    def remove_ip(self, ip_address: str):
        """Remove IP address from whitelist."""
        self.whitelist.discard(ip_address)

    def is_whitelisted(self, ip_address: str) -> bool:
        """Check if IP address is whitelisted."""
        return ip_address in self.whitelist


# Global IP whitelist instance
ip_whitelist = IPWhitelist()
