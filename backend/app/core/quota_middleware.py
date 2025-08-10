"""
Quota enforcement middleware.
"""

import logging
from typing import Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.quota_service import QuotaService

logger = logging.getLogger(__name__)


class QuotaEnforcementMiddleware:
    """Middleware for enforcing API quotas."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Check if this endpoint requires quota enforcement
        if self._should_enforce_quota(request):
            try:
                # Get user from request (assumes authentication middleware has run)
                user = getattr(request.state, "user", None)
                if user:
                    # Get database session
                    db = next(get_db())
                    quota_service = QuotaService(db)

                    # Determine quota type based on endpoint
                    quota_type = self._get_quota_type(request)

                    # Check quota availability
                    has_quota, quota_info = await quota_service.check_quota_available(
                        user.id, quota_type
                    )

                    if not has_quota:
                        # Return quota exceeded response
                        response = JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={
                                "success": False,
                                "error": "Quota exceeded",
                                "message": f"Daily {quota_type} quota exceeded. Upgrade your plan for higher limits.",
                                "quota_info": quota_info,
                            },
                        )
                        await response(scope, receive, send)
                        return

                    # Add quota info to request state for use in endpoints
                    request.state.quota_info = quota_info

                    db.close()

            except Exception as e:
                logger.error(f"Error in quota enforcement middleware: {e}")
                # Continue processing request if quota check fails
                pass

        await self.app(scope, receive, send)

    def _should_enforce_quota(self, request: Request) -> bool:
        """Determine if quota enforcement should be applied to this request."""
        path = request.url.path
        method = request.method

        # Define endpoints that require quota enforcement
        quota_enforced_endpoints = [
            # Stock data endpoints
            ("/api/v1/stocks/search", "GET"),
            ("/api/v1/stocks/", "GET"),  # Pattern for /stocks/{ticker}
            ("/api/v1/stocks/", "POST"),
            # Analysis endpoints
            ("/api/v1/analysis/generate", "POST"),
            ("/api/v1/analysis/", "GET"),  # Pattern for /analysis/{ticker}
            # News endpoints
            ("/api/v1/news/", "GET"),
            ("/api/v1/sentiment/", "GET"),
            # Market data endpoints
            ("/api/v1/market/indices", "GET"),
            ("/api/v1/market/hot-stocks", "GET"),
        ]

        # Check exact matches first
        for endpoint_path, endpoint_method in quota_enforced_endpoints:
            if path == endpoint_path and method == endpoint_method:
                return True

        # Check pattern matches (endpoints with path parameters)
        if method == "GET":
            if (
                path.startswith("/api/v1/stocks/") and len(path.split("/")) == 5
            ):  # /api/v1/stocks/{ticker}
                return True
            if (
                path.startswith("/api/v1/analysis/") and len(path.split("/")) == 5
            ):  # /api/v1/analysis/{ticker}
                return True
            if (
                path.startswith("/api/v1/news/stock/") and len(path.split("/")) == 6
            ):  # /api/v1/news/stock/{ticker}
                return True
            if (
                path.startswith("/api/v1/sentiment/") and len(path.split("/")) == 5
            ):  # /api/v1/sentiment/{ticker}
                return True

        return False

    def _get_quota_type(self, request: Request) -> str:
        """Determine the quota type based on the endpoint."""
        path = request.url.path

        # AI analysis endpoints use ai_analysis quota
        if "/analysis/" in path or path.startswith("/api/v1/analysis"):
            return "ai_analysis"

        # All other endpoints use general API quota
        return "api"


def create_quota_enforcement_middleware():
    """Factory function to create quota enforcement middleware."""

    def middleware(request: Request, call_next: Callable) -> Callable:
        async def dispatch(request: Request) -> Response:
            # Check if this endpoint requires quota enforcement
            if _should_enforce_quota(request):
                try:
                    # Get user from request (assumes authentication middleware has run)
                    user = getattr(request.state, "user", None)
                    if user:
                        # Get database session
                        db = next(get_db())
                        quota_service = QuotaService(db)

                        # Determine quota type based on endpoint
                        quota_type = _get_quota_type(request)

                        # Check quota availability
                        (
                            has_quota,
                            quota_info,
                        ) = await quota_service.check_quota_available(
                            user.id, quota_type
                        )

                        if not has_quota:
                            # Return quota exceeded response
                            return JSONResponse(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                content={
                                    "success": False,
                                    "error": "Quota exceeded",
                                    "message": f"Daily {quota_type} quota exceeded. Upgrade your plan for higher limits.",
                                    "quota_info": quota_info,
                                },
                            )

                        # Add quota info to request state for use in endpoints
                        request.state.quota_info = quota_info

                        db.close()

                except Exception as e:
                    logger.error(f"Error in quota enforcement middleware: {e}")
                    # Continue processing request if quota check fails
                    pass

            response = await call_next(request)
            return response

        return dispatch

    return middleware


def _should_enforce_quota(request: Request) -> bool:
    """Determine if quota enforcement should be applied to this request."""
    path = request.url.path
    method = request.method

    # Define endpoints that require quota enforcement
    quota_enforced_endpoints = [
        # Stock data endpoints
        ("/api/v1/stocks/search", "GET"),
        ("/api/v1/stocks/", "GET"),  # Pattern for /stocks/{ticker}
        ("/api/v1/stocks/", "POST"),
        # Analysis endpoints
        ("/api/v1/analysis/generate", "POST"),
        ("/api/v1/analysis/", "GET"),  # Pattern for /analysis/{ticker}
        # News endpoints
        ("/api/v1/news/", "GET"),
        ("/api/v1/sentiment/", "GET"),
        # Market data endpoints
        ("/api/v1/market/indices", "GET"),
        ("/api/v1/market/hot-stocks", "GET"),
    ]

    # Check exact matches first
    for endpoint_path, endpoint_method in quota_enforced_endpoints:
        if path == endpoint_path and method == endpoint_method:
            return True

    # Check pattern matches (endpoints with path parameters)
    if method == "GET":
        if (
            path.startswith("/api/v1/stocks/") and len(path.split("/")) == 5
        ):  # /api/v1/stocks/{ticker}
            return True
        if (
            path.startswith("/api/v1/analysis/") and len(path.split("/")) == 5
        ):  # /api/v1/analysis/{ticker}
            return True
        if (
            path.startswith("/api/v1/news/stock/") and len(path.split("/")) == 6
        ):  # /api/v1/news/stock/{ticker}
            return True
        if (
            path.startswith("/api/v1/sentiment/") and len(path.split("/")) == 5
        ):  # /api/v1/sentiment/{ticker}
            return True

    return False


def _get_quota_type(request: Request) -> str:
    """Determine the quota type based on the endpoint."""
    path = request.url.path

    # AI analysis endpoints use ai_analysis quota
    if "/analysis/" in path or path.startswith("/api/v1/analysis"):
        return "ai_analysis"

    # All other endpoints use general API quota
    return "api"


# Decorator for manual quota enforcement in endpoints
def enforce_quota(quota_type: str = "api"):
    """Decorator to enforce quota on specific endpoints."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request and current_user from kwargs
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")

            if current_user and db:
                quota_service = QuotaService(db)
                has_quota, quota_info = await quota_service.check_quota_available(
                    current_user.id, quota_type
                )

                if not has_quota:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Quota exceeded",
                            "message": f"Daily {quota_type} quota exceeded. Upgrade your plan for higher limits.",
                            "quota_info": quota_info,
                        },
                    )

                # Record usage after successful request
                try:
                    result = await func(*args, **kwargs)

                    # Record the API usage
                    await quota_service.record_api_usage(
                        user_id=current_user.id,
                        api_provider="internal",
                        endpoint=request.url.path if request else None,
                        request_type=quota_type,
                        status_code=200,
                    )

                    return result

                except Exception as e:
                    # Record failed usage
                    await quota_service.record_api_usage(
                        user_id=current_user.id,
                        api_provider="internal",
                        endpoint=request.url.path if request else None,
                        request_type=quota_type,
                        status_code=500,
                    )
                    raise

            return await func(*args, **kwargs)

        return wrapper

    return decorator
