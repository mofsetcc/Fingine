"""
Tests for security middleware implementations.
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.core.rate_limiting import RateLimitMiddleware, RateLimiter, RateLimitExceeded
from app.core.input_validation import InputValidationMiddleware, SecurityViolation
from app.core.https_middleware import SecurityHeadersMiddleware, HTTPSRedirectMiddleware
from app.core.jwt_middleware import JWTMiddleware, JWTAuthenticationError


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter(redis_client=None)  # Use in-memory fallback
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self, rate_limiter):
        """Test that requests within limit are allowed."""
        is_allowed, remaining, reset_time = await rate_limiter.is_allowed(
            key="test_user",
            limit=5,
            window_seconds=60
        )
        
        assert is_allowed is True
        assert remaining == 4
        assert reset_time > time.time()
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self, rate_limiter):
        """Test that requests over limit are blocked."""
        # Make requests up to the limit
        for i in range(5):
            is_allowed, _, _ = await rate_limiter.is_allowed(
                key="test_user_2",
                limit=5,
                window_seconds=60
            )
            assert is_allowed is True
        
        # Next request should be blocked
        is_allowed, remaining, _ = await rate_limiter.is_allowed(
            key="test_user_2",
            limit=5,
            window_seconds=60
        )
        
        assert is_allowed is False
        assert remaining == 0


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/auth/login")
        async def auth_endpoint():
            return {"message": "auth"}
        
        app.add_middleware(RateLimitMiddleware)
        return app
    
    def test_rate_limit_headers_added(self, app):
        """Test that rate limit headers are added to responses."""
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_exempt_paths_not_rate_limited(self, app):
        """Test that exempt paths are not rate limited."""
        client = TestClient(app)
        
        # Health endpoint should not be rate limited
        for _ in range(100):  # Make many requests
            response = client.get("/health")
            assert response.status_code == 404  # Endpoint doesn't exist but not rate limited


class TestInputValidationMiddleware:
    """Test input validation middleware."""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"message": "success", "data": data}
        
        app.add_middleware(InputValidationMiddleware)
        return app
    
    def test_valid_input_passes(self, app):
        """Test that valid input passes validation."""
        client = TestClient(app)
        response = client.post("/test", json={"name": "John", "age": 30})
        
        assert response.status_code == 200
    
    def test_sql_injection_blocked(self, app):
        """Test that SQL injection attempts are blocked."""
        client = TestClient(app)
        response = client.post("/test", json={
            "query": "SELECT * FROM users WHERE id = 1; DROP TABLE users;"
        })
        
        assert response.status_code == 400
        assert "security violation" in response.json()["detail"].lower()
    
    def test_xss_blocked(self, app):
        """Test that XSS attempts are blocked."""
        client = TestClient(app)
        response = client.post("/test", json={
            "content": "<script>alert('xss')</script>"
        })
        
        assert response.status_code == 400
        assert "security violation" in response.json()["detail"].lower()


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        app.add_middleware(SecurityHeadersMiddleware)
        return app
    
    def test_security_headers_added(self, app):
        """Test that security headers are added to responses."""
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
    
    def test_server_header_removed(self, app):
        """Test that server header is removed."""
        client = TestClient(app)
        response = client.get("/test")
        
        assert "Server" not in response.headers


class TestJWTMiddleware:
    """Test JWT authentication middleware."""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/api/v1/users/profile")
        async def protected_endpoint(request: Request):
            return {
                "message": "protected",
                "authenticated": getattr(request.state, 'authenticated', False),
                "user_id": getattr(request.state, 'user_id', None)
            }
        
        app.add_middleware(JWTMiddleware)
        return app
    
    def test_public_endpoint_accessible(self, app):
        """Test that public endpoints are accessible without authentication."""
        client = TestClient(app)
        response = client.get("/public")
        
        assert response.status_code == 200
        assert response.json()["message"] == "public"
    
    def test_protected_endpoint_requires_auth(self, app):
        """Test that protected endpoints require authentication."""
        client = TestClient(app)
        response = client.get("/api/v1/users/profile")
        
        assert response.status_code == 401
        assert "authentication" in response.json()["detail"].lower()
    
    @patch('app.core.jwt_middleware.verify_token')
    def test_valid_token_allows_access(self, mock_verify, app):
        """Test that valid token allows access to protected endpoints."""
        mock_verify.return_value = "user123"
        
        client = TestClient(app)
        response = client.get(
            "/api/v1/users/profile",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "user123"