"""
Dependency injection utilities for FastAPI.
"""

from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.schemas.user import User as UserSchema

# Security scheme for JWT tokens
security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials containing JWT token

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify the token
    user_id = verify_token(credentials.credentials, token_type="access")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user (email verified).

    Args:
        current_user: Current authenticated user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is not active (email not verified)
    """
    if not current_user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not verified"
        )

    return current_user


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.

    Args:
        db: Database session
        credentials: Optional HTTP Bearer credentials

    Returns:
        Current user if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        user_id = verify_token(credentials.credentials, token_type="access")
        if user_id is None:
            return None

        user = db.query(User).filter(User.id == UUID(user_id)).first()
        return user
    except Exception:
        return None


def get_refresh_token_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Get user from refresh token for token refresh endpoint.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials containing refresh token

    Returns:
        User associated with the refresh token

    Raises:
        HTTPException: If refresh token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify the refresh token
    user_id = verify_token(credentials.credentials, token_type="refresh")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


class RateLimitDependency:
    """
    Rate limiting dependency for API endpoints.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def __call__(
        self, current_user: Optional[User] = Depends(get_current_user_optional)
    ):
        """
        Check rate limits for the current user or IP.

        Args:
            current_user: Current authenticated user (optional)

        Raises:
            HTTPException: If rate limit is exceeded
        """
        # TODO: Implement rate limiting logic with Redis
        # For now, this is a placeholder
        pass


# Common rate limit instances
rate_limit_auth = RateLimitDependency(
    max_requests=5, window_seconds=60
)  # 5 requests per minute for auth
rate_limit_api = RateLimitDependency(
    max_requests=100, window_seconds=60
)  # 100 requests per minute for API


def require_subscription_tier(required_tier: str):
    """
    Dependency factory to require specific subscription tier.

    Args:
        required_tier: Required subscription tier name

    Returns:
        Dependency function that checks subscription tier
    """

    def check_subscription_tier(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        """
        Check if user has required subscription tier.

        Args:
            current_user: Current authenticated user
            db: Database session

        Returns:
            Current user if subscription tier is sufficient

        Raises:
            HTTPException: If subscription tier is insufficient
        """
        # TODO: Implement subscription tier checking
        # For now, allow all authenticated users
        return current_user

    return check_subscription_tier


def check_api_quota(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> User:
    """
    Check if user has remaining API quota.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Current user if quota is available

    Raises:
        HTTPException: If API quota is exceeded
    """
    # TODO: Implement API quota checking
    # For now, allow all requests
    return current_user


def check_ai_analysis_quota(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> User:
    """
    Check if user has remaining AI analysis quota.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Current user if quota is available

    Raises:
        HTTPException: If AI analysis quota is exceeded
    """
    # TODO: Implement AI analysis quota checking
    # For now, allow all requests
    return current_user


def get_user_by_id(user_id: UUID, db: Session = Depends(get_db)) -> User:
    """
    Get user by ID.

    Args:
        user_id: User ID to lookup
        db: Database session

    Returns:
        User with the specified ID

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


def validate_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Validate that current user is an admin.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if they are an admin

    Raises:
        HTTPException: If user is not an admin
    """
    # TODO: Implement admin role checking
    # For now, assume no admin users exist
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
    )


def get_pagination_params(
    page: int = 1, per_page: int = 20, max_per_page: int = 100
) -> dict:
    """
    Get pagination parameters with validation.

    Args:
        page: Page number (1-based)
        per_page: Items per page
        max_per_page: Maximum items per page allowed

    Returns:
        Dictionary with validated pagination parameters

    Raises:
        HTTPException: If pagination parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater",
        )

    if per_page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Items per page must be 1 or greater",
        )

    if per_page > max_per_page:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Items per page cannot exceed {max_per_page}",
        )

    return {
        "page": page,
        "per_page": per_page,
        "offset": (page - 1) * per_page,
        "limit": per_page,
    }
