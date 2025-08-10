"""
HTTPS enforcement and security headers middleware.
"""

from typing import List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp

from app.core.config import settings


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS connections."""

    def __init__(self, app: ASGIApp, force_https: bool = True):
        super().__init__(app)
        self.force_https = force_https and not settings.DEBUG

    async def dispatch(self, request: Request, call_next) -> Response:
        """Redirect HTTP requests to HTTPS."""

        if self.force_https:
            # Check if request is HTTP
            if request.url.scheme == "http":
                # Build HTTPS URL
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=301)

            # Check X-Forwarded-Proto header (for load balancers)
            forwarded_proto = request.headers.get("X-Forwarded-Proto")
            if forwarded_proto and forwarded_proto.lower() == "http":
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=301)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    def __init__(
        self,
        app: ASGIApp,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        content_type_nosniff: bool = True,
        frame_options: str = "DENY",
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[str] = None,
        csp: Optional[str] = None,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.content_type_nosniff = content_type_nosniff
        self.frame_options = frame_options
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
        self.permissions_policy = (
            permissions_policy or self._default_permissions_policy()
        )
        self.csp = csp or self._default_csp()

    def _default_permissions_policy(self) -> str:
        """Default permissions policy."""
        return (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

    def _default_csp(self) -> str:
        """Default Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.kessan.com wss://api.kessan.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # HTTP Strict Transport Security (HSTS)
        if not settings.DEBUG and request.url.scheme == "https":
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Content Type Options
        if self.content_type_nosniff:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # Frame Options
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options

        # XSS Protection
        if self.xss_protection:
            response.headers["X-XSS-Protection"] = self.xss_protection

        # Referrer Policy
        if self.referrer_policy:
            response.headers["Referrer-Policy"] = self.referrer_policy

        # Permissions Policy
        if self.permissions_policy:
            response.headers["Permissions-Policy"] = self.permissions_policy

        # Content Security Policy
        if self.csp:
            response.headers["Content-Security-Policy"] = self.csp

        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Remove server information
        response.headers.pop("Server", None)

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Basic CSRF protection middleware."""

    def __init__(
        self,
        app: ASGIApp,
        csrf_token_header: str = "X-CSRF-Token",
        exempt_methods: List[str] = None,
        exempt_paths: List[str] = None,
    ):
        super().__init__(app)
        self.csrf_token_header = csrf_token_header
        self.exempt_methods = exempt_methods or ["GET", "HEAD", "OPTIONS", "TRACE"]
        self.exempt_paths = exempt_paths or [
            "/health",
            "/health/detailed",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Check CSRF token for state-changing requests."""

        # Skip CSRF check for exempt methods and paths
        if (
            request.method in self.exempt_methods
            or request.url.path in self.exempt_paths
        ):
            return await call_next(request)

        # For API endpoints, we rely on JWT tokens and SameSite cookies
        # This is a basic implementation - in production, you might want
        # more sophisticated CSRF protection

        # Check for CSRF token in header
        csrf_token = request.headers.get(self.csrf_token_header)

        # For now, we'll be lenient and only log missing CSRF tokens
        # In production, you might want to enforce this more strictly
        if not csrf_token:
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning(
                "Missing CSRF token",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
            )

        return await call_next(request)


def create_security_middleware_stack(app: ASGIApp) -> ASGIApp:
    """Create a stack of security middleware."""

    # Add CSRF protection
    app = CSRFProtectionMiddleware(app)

    # Add security headers
    app = SecurityHeadersMiddleware(app)

    # Add HTTPS enforcement (only in production)
    if not settings.DEBUG:
        app = HTTPSRedirectMiddleware(app, force_https=True)

    return app
