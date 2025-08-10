"""
User profile management API endpoints.
"""

import logging
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, rate_limit_auth
from app.models.user import User
from app.schemas.api_response import APIResponse, SuccessResponse, UpdatedResponse
from app.schemas.user import (
    AccountDeletion,
    EmailChange,
    PasswordChange,
    PasswordSet,
    UserActivityLog,
    UserDataExport,
    UserPreferencesUpdate,
    UserProfile,
    UserProfileUpdate,
    UserWithProfile,
)
from app.services.email_service import EmailService
from app.services.user_service import (
    EmailAlreadyExistsError,
    InvalidPasswordError,
    UserNotFoundError,
    UserService,
    UserServiceError,
    WeakPasswordError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get user service instance."""
    email_service = EmailService()
    return UserService(db, email_service)


@router.get("/profile", response_model=APIResponse[UserWithProfile])
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[UserWithProfile]:
    """
    Get current user's profile information.

    Returns complete user profile including:
    - Basic user information
    - Profile details (display name, avatar, timezone, etc.)
    - Linked OAuth identities
    """
    try:
        user_profile = user_service.get_user_profile(current_user.id)

        return APIResponse(
            success=True,
            message="User profile retrieved successfully",
            data=user_profile,
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile",
        )


@router.put("/profile", response_model=UpdatedResponse[UserProfile])
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> UpdatedResponse[UserProfile]:
    """
    Update current user's profile information.

    - **display_name**: User's display name
    - **avatar_url**: URL to user's avatar image
    - **timezone**: User's timezone (e.g., "Asia/Tokyo")
    - **notification_preferences**: User's notification preferences
    """
    try:
        updated_profile = await user_service.update_user_profile(
            current_user.id, profile_data
        )

        return UpdatedResponse(
            message="Profile updated successfully", data=updated_profile
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
    _: Any = Depends(rate_limit_auth),
) -> SuccessResponse:
    """
    Change user's password.

    - **current_password**: Current password
    - **new_password**: New password (must meet strength requirements)

    Requires current password verification.
    """
    try:
        await user_service.change_password(
            current_user.id, password_data.current_password, password_data.new_password
        )

        return SuccessResponse(message="Password changed successfully")

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet requirements",
                "errors": e.errors,
            },
        )
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )


@router.post("/set-password", response_model=SuccessResponse)
async def set_password(
    password_data: PasswordSet,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
    _: Any = Depends(rate_limit_auth),
) -> SuccessResponse:
    """
    Set password for OAuth-only user.

    - **new_password**: New password (must meet strength requirements)

    For users who registered via OAuth and want to set a password.
    """
    try:
        await user_service.set_password(current_user.id, password_data.new_password)

        return SuccessResponse(message="Password set successfully")

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet requirements",
                "errors": e.errors,
            },
        )
    except Exception as e:
        logger.error(f"Failed to set password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set password",
        )


@router.post("/change-email", response_model=SuccessResponse)
async def change_email(
    email_data: EmailChange,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
    _: Any = Depends(rate_limit_auth),
) -> SuccessResponse:
    """
    Change user's email address.

    - **new_email**: New email address
    - **password**: Current password (required if user has password)

    Sends verification email to new address and notification to old address.
    """
    try:
        await user_service.change_email(
            current_user.id, email_data.new_email, email_data.password
        )

        return SuccessResponse(
            message="Email change initiated. Please verify your new email address."
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to change email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change email",
        )


@router.get("/oauth-identities", response_model=APIResponse[List[dict]])
async def get_oauth_identities(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[List[dict]]:
    """
    Get user's linked OAuth identities.

    Returns list of OAuth providers linked to the user's account.
    """
    try:
        oauth_identities = user_service.get_user_oauth_identities(current_user.id)

        return APIResponse(
            success=True,
            message="OAuth identities retrieved successfully",
            data=oauth_identities,
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Failed to get OAuth identities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OAuth identities",
        )


@router.get("/activity-log", response_model=APIResponse[List[UserActivityLog]])
async def get_activity_log(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[List[UserActivityLog]]:
    """
    Get user's activity log.

    - **limit**: Maximum number of records to return (default: 50, max: 100)
    - **offset**: Number of records to skip (default: 0)

    Returns paginated list of user activities.
    """
    try:
        # Validate parameters
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0

        activity_log = user_service.get_user_activity_log(
            current_user.id, limit=limit, offset=offset
        )

        return APIResponse(
            success=True,
            message="Activity log retrieved successfully",
            data=activity_log,
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Failed to get activity log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity log",
        )


@router.get("/export-data", response_model=APIResponse[UserDataExport])
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[UserDataExport]:
    """
    Export all user data for GDPR compliance.

    Returns complete user data export including:
    - User information
    - Profile data
    - OAuth identities
    - Activity log
    """
    try:
        user_data = await user_service.export_user_data(current_user.id)

        return APIResponse(
            success=True, message="User data exported successfully", data=user_data
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Failed to export user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data",
        )


@router.delete("/account", response_model=SuccessResponse)
async def delete_account(
    deletion_data: AccountDeletion,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
    _: Any = Depends(rate_limit_auth),
) -> SuccessResponse:
    """
    Delete user account and all associated data.

    - **password**: Current password (required if user has password)
    - **confirmation**: Must be exactly "DELETE" to confirm deletion

    This action is irreversible and will delete all user data.
    """
    try:
        await user_service.delete_user_account(
            current_user.id, deletion_data.password, deletion_data.confirmation
        )

        return SuccessResponse(message="Account deleted successfully")

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )


@router.get("/preferences", response_model=APIResponse[dict])
async def get_user_preferences(
    current_user: User = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """
    Get user preferences.

    Returns user's notification, UI, and privacy preferences.
    """
    try:
        preferences = {
            "notification_preferences": current_user.profile.notification_preferences
            if current_user.profile
            else {},
            "ui_preferences": {},  # TODO: Implement UI preferences
            "privacy_preferences": {},  # TODO: Implement privacy preferences
        }

        return APIResponse(
            success=True,
            message="User preferences retrieved successfully",
            data=preferences,
        )

    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences",
        )


@router.put("/preferences", response_model=SuccessResponse)
async def update_user_preferences(
    preferences_data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> SuccessResponse:
    """
    Update user preferences.

    - **notification_preferences**: Notification settings
    - **ui_preferences**: UI/UX preferences
    - **privacy_preferences**: Privacy settings
    """
    try:
        # Update profile with notification preferences
        if preferences_data.notification_preferences is not None:
            profile_update = UserProfileUpdate(
                notification_preferences=preferences_data.notification_preferences
            )
            await user_service.update_user_profile(current_user.id, profile_update)

        # TODO: Implement UI and privacy preferences storage

        return SuccessResponse(message="User preferences updated successfully")

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Failed to update user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences",
        )


@router.get("/subscription", response_model=APIResponse[dict])
async def get_user_subscription(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> APIResponse[dict]:
    """
    Get user's subscription information.

    Returns current subscription plan, usage, and billing information.
    """
    try:
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService(db)
        subscription = await service.get_subscription_with_usage(current_user.id)

        if subscription:
            subscription_info = {
                "plan": subscription.plan.plan_name if subscription.plan else "free",
                "status": subscription.status,
                "usage": {
                    "api_calls_today": subscription.usage_quota.api_usage_today,
                    "ai_analysis_today": subscription.usage_quota.ai_analysis_usage_today,
                },
                "limits": {
                    "api_calls_daily": subscription.usage_quota.api_quota_daily,
                    "ai_analysis_daily": subscription.usage_quota.ai_analysis_quota_daily,
                },
            }
        else:
            # Default free tier for users without subscription
            usage_quota = await service.get_user_usage_quota(current_user.id)
            subscription_info = {
                "plan": "free",
                "status": "active",
                "usage": {
                    "api_calls_today": usage_quota.api_usage_today,
                    "ai_analysis_today": usage_quota.ai_analysis_usage_today,
                },
                "limits": {
                    "api_calls_daily": usage_quota.api_quota_daily,
                    "ai_analysis_daily": usage_quota.ai_analysis_quota_daily,
                },
            }

        return APIResponse(
            success=True,
            message="Subscription information retrieved successfully",
            data=subscription_info,
        )

    except Exception as e:
        logger.error(f"Failed to get subscription info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription information",
        )
