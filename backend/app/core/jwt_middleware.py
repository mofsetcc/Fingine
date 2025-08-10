"""
JWT authentication middleware for automatic token validation.
"""

from typing import Optional, Set

import structlog
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.security import is_token_expired, refresh_access_token, verify_token

logger = structlog.get_logger(__name__)


class JWTAuthenticationError(HTTPException):
    """JWT authentication error."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class JWTMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token validation and refresh."""

    def __init__(self, app):
        super().__init__(app)

        # Paths that require authentication
        self.protected_paths = {
            "/api/v1/users/profile",
            "/api/v1/users/subscription",
            "/api/v1/analysis/",
            "/api/v1/watchlist/",
        }

        # Paths that are exempt from authentication
        self.exempt_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/password-reset",
            "/api/v1/oauth/",
            "/api/v1/stocks/search",  # Public search
            "/api/v1/market/indices",  # Public market data
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate JWT tokens and handle refresh."""

        # Skip authentication for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Check if path requires authentication
        requires_auth = self._requires_authentication(request.url.path)

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header and requires_auth:
            raise JWTAuthenticationError("Authorization header missing")

        if auth_header:
            try:
                # Extract token
                if not auth_header.startswith("Bearer "):
                    raise JWTAuthenticationError("Invalid authorization header format")

                token = auth_header.split(" ")[1]

                # Verify token
                user_id = verify_token(token, "access")

                if user_id:
                    # Token is valid, add user info to request
                    request.state.user_id = user_id
                    request.state.authenticated = True
                elif is_token_expired(token):
                    # Token is expired, check for refresh token
                    refresh_token = request.headers.get("X-Refresh-Token")

                    if refresh_token:
                        # Try to refresh the token
                        new_tokens = refresh_access_token(refresh_token)

                        if new_tokens:
                            new_access_token, new_refresh_token = new_tokens

                            # Verify the new access token
                            user_id = verify_token(new_access_token, "access")

                            if user_id:
                                request.state.user_id = user_id
                                request.state.authenticated = True

                                # Process the request
                                response = await call_next(request)

                                # Add new tokens to response headers
                                response.headers[
                                    "X-New-Access-Token"
                                ] = new_access_token
                                response.headers[
                                    "X-New-Refresh-Token"
                                ] = new_refresh_token

                                return response

                    if requires_auth:
                        raise JWTAuthenticationError("Token expired")
                else:
                    if requires_auth:
                        raise JWTAuthenticationError("Invalid token")

            except JWTAuthenticationError:
                raise
            except Exception as e:
                logger.error("JWT middleware error", error=str(e))
                if requires_auth:
                    raise JWTAuthenticationError("Authentication failed")

        # Set default authentication state
        if not hasattr(request.state, "authenticated"):
            request.state.authenticated = False
            request.state.user_id = None

        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication."""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False

    def _requires_authentication(self, path: str) -> bool:
        """Check if path requires authentication."""
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False


class OptionalJWTMiddleware(BaseHTTPMiddleware):
    """Middleware for optional JWT authentication (doesn't fail if no token)."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Optionally validate JWT tokens."""

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        # Set default state
        request.state.authenticated = False
        request.state.user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                user_id = verify_token(token, "access")

                if user_id:
                    request.state.user_id = user_id
                    request.state.authenticated = True
            except Exception as e:
                logger.debug("Optional JWT validation failed", error=str(e))
                # Don't fail the request for optional authentication
                pass

        return await call_next(request)


def get_current_user_id(request: Request) -> Optional[str]:
    """Get current user ID from request state."""
    return getattr(request.state, "user_id", None)


def is_authenticated(request: Request) -> bool:
    """Check if request is authenticated."""
    return getattr(request.state, "authenticated", False)


def require_authentication(request: Request) -> str:
    """Require authentication and return user ID."""
    if not is_authenticated(request):
        raise JWTAuthenticationError("Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise JWTAuthenticationError("Invalid authentication state")

    return user_id
