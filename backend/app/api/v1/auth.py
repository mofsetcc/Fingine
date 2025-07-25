"""
Authentication API endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    get_current_user,
    get_current_active_user,
    get_refresh_token_user,
    rate_limit_auth
)
from app.models.user import User
from app.schemas.user import (
    UserRegistration,
    UserLogin,
    AuthResponse,
    AuthToken,
    User as UserSchema,
    UserWithProfile,
    PasswordReset,
    PasswordResetConfirm,
    OAuthLogin
)
from app.schemas.api_response import (
    APIResponse,
    SuccessResponse,
    CreatedResponse
)
from app.services.auth_service import (
    AuthService,
    AuthenticationError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    EmailNotVerifiedError,
    UserNotFoundError,
    InvalidTokenError,
    WeakPasswordError
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance."""
    email_service = EmailService()
    return AuthService(db, email_service)


@router.post("/register", response_model=CreatedResponse[UserSchema])
async def register(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
    _: Any = Depends(rate_limit_auth)
) -> CreatedResponse[UserSchema]:
    """
    Register a new user.
    
    - **email**: Valid email address
    - **password**: Password meeting strength requirements
    - **display_name**: Optional display name
    
    Returns the created user and sends a verification email.
    """
    try:
        user = await auth_service.register_user(user_data)
        
        # Send welcome email in background
        background_tasks.add_task(
            auth_service.email_service.send_welcome_email,
            user.email,
            user_data.display_name
        )
        
        logger.info(f"User registered successfully: {user.email}")
        
        return CreatedResponse(
            message="User registered successfully. Please check your email for verification.",
            data=user,
            resource_id=str(user.id)
        )
        
    except UserAlreadyExistsError as e:
        logger.warning(f"Registration failed - user exists: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except WeakPasswordError as e:
        logger.warning(f"Registration failed - weak password: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet requirements",
                "errors": e.errors
            }
        )
    except Exception as e:
        logger.error(f"Registration failed with unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=APIResponse[AuthResponse])
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
    _: Any = Depends(rate_limit_auth)
) -> APIResponse[AuthResponse]:
    """
    Authenticate user and return access tokens.
    
    - **email**: User email address
    - **password**: User password
    - **remember_me**: Optional flag for extended session
    
    Returns user information and JWT tokens.
    """
    try:
        auth_response = await auth_service.authenticate_user(credentials)
        
        logger.info(f"User logged in successfully: {credentials.email}")
        
        return APIResponse(
            success=True,
            message="Login successful",
            data=auth_response
        )
        
    except InvalidCredentialsError as e:
        logger.warning(f"Login failed - invalid credentials: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except EmailNotVerifiedError as e:
        logger.warning(f"Login failed - email not verified: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login failed with unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/oauth/{provider}", response_model=APIResponse[AuthResponse])
async def oauth_login(
    provider: str,
    oauth_data: OAuthLogin,
    auth_service: AuthService = Depends(get_auth_service),
    _: Any = Depends(rate_limit_auth)
) -> APIResponse[AuthResponse]:
    """
    Authenticate user via OAuth provider.
    
    - **provider**: OAuth provider (google, line)
    - **access_token**: OAuth access token
    
    Returns user information and JWT tokens.
    """
    # Validate provider
    if provider not in ["google", "line"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
    
    # Set provider in oauth_data
    oauth_data.provider = provider
    
    try:
        auth_response = await auth_service.oauth_authenticate(oauth_data)
        
        logger.info(f"OAuth login successful: {provider}")
        
        return APIResponse(
            success=True,
            message="OAuth authentication successful",
            data=auth_response
        )
        
    except InvalidCredentialsError as e:
        logger.warning(f"OAuth login failed: {provider}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"OAuth login failed with unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed. Please try again."
        )


@router.post("/refresh", response_model=APIResponse[AuthToken])
async def refresh_token(
    current_user: User = Depends(get_refresh_token_user)
) -> APIResponse[AuthToken]:
    """
    Refresh access token using refresh token.
    
    Requires a valid refresh token in the Authorization header.
    
    Returns a new access token.
    """
    try:
        auth_service = AuthService(None, None)  # No DB or email service needed for token refresh
        token = await auth_service.refresh_token(current_user)
        
        logger.info(f"Token refreshed for user: {current_user.email}")
        
        return APIResponse(
            success=True,
            message="Token refreshed successfully",
            data=token
        )
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please try again."
        )


@router.post("/verify-email", response_model=SuccessResponse)
async def verify_email(
    token: str,
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse:
    """
    Verify user email address.
    
    - **token**: Email verification token from email
    
    Marks the user's email as verified.
    """
    try:
        await auth_service.verify_email(token)
        
        logger.info("Email verified successfully")
        
        return SuccessResponse(
            message="Email verified successfully"
        )
        
    except InvalidTokenError as e:
        logger.warning("Email verification failed - invalid token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except UserNotFoundError as e:
        logger.warning("Email verification failed - user not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed. Please try again."
        )


@router.post("/resend-verification", response_model=SuccessResponse)
async def resend_verification(
    email: str,
    auth_service: AuthService = Depends(get_auth_service),
    _: Any = Depends(rate_limit_auth)
) -> SuccessResponse:
    """
    Resend email verification.
    
    - **email**: User email address
    
    Sends a new verification email if the user exists and is not verified.
    """
    try:
        await auth_service.resend_verification_email(email)
        
        logger.info(f"Verification email resent: {email}")
        
        return SuccessResponse(
            message="If the email exists and is not verified, a verification email has been sent."
        )
        
    except Exception as e:
        logger.error(f"Resend verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email. Please try again."
        )


@router.post("/password-reset", response_model=SuccessResponse)
async def request_password_reset(
    reset_data: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service),
    _: Any = Depends(rate_limit_auth)
) -> SuccessResponse:
    """
    Request password reset.
    
    - **email**: User email address
    
    Sends a password reset email if the user exists.
    """
    try:
        await auth_service.request_password_reset(reset_data)
        
        logger.info(f"Password reset requested: {reset_data.email}")
        
        return SuccessResponse(
            message="If the email exists, a password reset email has been sent."
        )
        
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request. Please try again."
        )


@router.post("/password-reset/confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service),
    _: Any = Depends(rate_limit_auth)
) -> SuccessResponse:
    """
    Confirm password reset with new password.
    
    - **token**: Password reset token from email
    - **new_password**: New password meeting strength requirements
    
    Resets the user's password.
    """
    try:
        await auth_service.reset_password(reset_data)
        
        logger.info("Password reset successfully")
        
        return SuccessResponse(
            message="Password reset successfully"
        )
        
    except InvalidTokenError as e:
        logger.warning("Password reset failed - invalid token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except UserNotFoundError as e:
        logger.warning("Password reset failed - user not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except WeakPasswordError as e:
        logger.warning("Password reset failed - weak password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet requirements",
                "errors": e.errors
            }
        )
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed. Please try again."
        )


@router.get("/me", response_model=APIResponse[UserWithProfile])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[UserWithProfile]:
    """
    Get current user information.
    
    Requires authentication. Returns user profile information.
    """
    try:
        # Convert to schema with profile
        user_with_profile = UserWithProfile.from_orm(current_user)
        
        return APIResponse(
            success=True,
            message="User information retrieved successfully",
            data=user_with_profile
        )
        
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse:
    """
    Logout user.
    
    Requires authentication. In a stateless JWT system, this is mainly
    for logging purposes. Clients should discard their tokens.
    """
    try:
        logger.info(f"User logged out: {current_user.email}")
        
        return SuccessResponse(
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/check-email", response_model=APIResponse[dict])
async def check_email_availability(
    email: str,
    db: Session = Depends(get_db)
) -> APIResponse[dict]:
    """
    Check if email is available for registration.
    
    - **email**: Email address to check
    
    Returns availability status.
    """
    try:
        from app.models.user import User
        
        existing_user = db.query(User).filter(User.email == email).first()
        is_available = existing_user is None
        
        return APIResponse(
            success=True,
            message="Email availability checked",
            data={
                "email": email,
                "available": is_available
            }
        )
        
    except Exception as e:
        logger.error(f"Email check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check email availability"
        )