"""User profile management API endpoints."""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, rate_limit_api
from app.models.user import User
from app.schemas.api_response import APIResponse, SuccessResponse, UpdatedResponse
from app.schemas.user import UserPreferencesUpdate
from app.schemas.user import UserProfile as UserProfileSchema
from app.schemas.user import UserProfileUpdate, UserWithProfile
from app.services.email_service import EmailService
from app.services.user_profile_service import (
    InvalidProfileDataError,
    ProfileError,
    ProfileNotFoundError,
    UserProfileService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_profile_service(db: Session = Depends(get_db)) -> UserProfileService:
    """Get user profile service instance."""
    email_service = EmailService()
    return UserProfileService(db, email_service)


@router.get("/me", response_model=APIResponse[UserWithProfile])
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
) -> APIResponse[UserWithProfile]:
    """
    Get current user's profile information.

    Returns complete user information including profile data.
    """
    try:
        user_with_profile = await profile_service.get_user_with_profile(current_user.id)

        return APIResponse(
            success=True,
            message="User profile retrieved successfully",
            data=user_with_profile,
        )

    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile",
        )


@router.put("/me", response_model=UpdatedResponse[UserProfileSchema])
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
    _: Any = Depends(rate_limit_api),
) -> UpdatedResponse[UserProfileSchema]:
    """
    Update current user's profile.

    - **display_name**: User's display name
    - **timezone**: User's timezone (e.g., 'Asia/Tokyo')
    - **notification_preferences**: Notification preferences object

    Updates the user's profile information.
    """
    try:
        updated_profile = await profile_service.update_user_profile(
            current_user.id, profile_data
        )

        logger.info(f"Profile updated for user: {current_user.email}")

        return UpdatedResponse(
            message="Profile updated successfully", data=updated_profile
        )

    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidProfileDataError as e:
        logger.warning(f"Invalid profile data for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile",
        )


@router.put("/me/preferences", response_model=UpdatedResponse[UserProfileSchema])
async def update_notification_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
    _: Any = Depends(rate_limit_api),
) -> UpdatedResponse[UserProfileSchema]:
    """
    Update user's notification preferences.

    Updates the user's notification preferences including:
    - Email, push, SMS notification settings
    - Specific notification type preferences
    - Quiet hours and digest settings
    """
    try:
        updated_profile = await profile_service.update_notification_preferences(
            current_user.id, preferences
        )

        logger.info(f"Notification preferences updated for user: {current_user.email}")

        return UpdatedResponse(
            message="Notification preferences updated successfully",
            data=updated_profile,
        )

    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences",
        )


@router.post("/me/avatar", response_model=APIResponse[dict])
async def upload_avatar(
    avatar: UploadFile = File(..., description="Avatar image file"),
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
    _: Any = Depends(rate_limit_api),
) -> APIResponse[dict]:
    """
    Upload user avatar image.

    - **avatar**: Image file (JPEG, PNG, GIF, WebP)
    - Maximum file size: 5MB
    - Recommended dimensions: 200x200 pixels

    Uploads and sets the user's avatar image.
    """
    try:
        # Validate file
        if not avatar.content_type or not avatar.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image"
            )

        # Read file data
        avatar_data = await avatar.read()

        # Upload avatar
        avatar_url = await profile_service.upload_avatar(
            current_user.id,
            avatar_data,
            avatar.content_type,
            avatar.filename or "avatar",
        )

        logger.info(f"Avatar uploaded for user: {current_user.email}")

        return APIResponse(
            success=True,
            message="Avatar uploaded successfully",
            data={
                "avatar_url": avatar_url,
                "file_size": len(avatar_data),
                "content_type": avatar.content_type,
            },
        )

    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidProfileDataError as e:
        logger.warning(f"Invalid avatar data for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar",
        )


@router.delete("/me/avatar", response_model=SuccessResponse)
async def delete_avatar(
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
) -> SuccessResponse:
    """
    Delete user's avatar image.

    Removes the user's current avatar image.
    """
    try:
        await profile_service.delete_avatar(current_user.id)

        logger.info(f"Avatar deleted for user: {current_user.email}")

        return SuccessResponse(message="Avatar deleted successfully")

    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found for user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete avatar",
        )


@router.get("/me/activity", response_model=APIResponse[dict])
async def get_user_activity(
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
) -> APIResponse[dict]:
    """
    Get user activity summary.

    Returns recent user activities and statistics including:
    - Recent login activities
    - Profile changes
    - System interactions
    """
    try:
        activity_summary = await profile_service.get_user_activity_summary(
            current_user.id
        )

        return APIResponse(
            success=True,
            message="User activity retrieved successfully",
            data=activity_summary,
        )

    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user activity",
        )


@router.get("/me/export", response_model=APIResponse[dict])
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    profile_service: UserProfileService = Depends(get_profile_service),
    _: Any = Depends(rate_limit_api),
) -> APIResponse[dict]:
    """
    Export user data (GDPR compliance).

    Returns all user data in a structured format including:
    - User account information
    - Profile data
    - Activity history
    - OAuth identities

    This endpoint supports GDPR data portability requirements.
    """
    try:
        user_data = await profile_service.export_user_data(current_user.id)

        logger.info(f"User data exported for: {current_user.email}")

        return APIResponse(
            success=True, message="User data exported successfully", data=user_data
        )

    except ProfileNotFoundError as e:
        logger.warning(f"User not found for export {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data",
        )


@router.get("/timezones", response_model=APIResponse[list])
async def get_supported_timezones() -> APIResponse[list]:
    """
    Get list of supported timezones.

    Returns a list of timezone identifiers that can be used
    for user profile timezone settings.
    """
    try:
        import pytz

        # Get common timezones, prioritizing Japanese and Asian timezones
        common_timezones = [
            "Asia/Tokyo",
            "Asia/Seoul",
            "Asia/Shanghai",
            "Asia/Hong_Kong",
            "Asia/Singapore",
            "Asia/Bangkok",
            "Asia/Jakarta",
            "Asia/Manila",
            "Asia/Kuala_Lumpur",
            "Asia/Taipei",
            "UTC",
            "US/Eastern",
            "US/Central",
            "US/Mountain",
            "US/Pacific",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Europe/Rome",
            "Australia/Sydney",
            "Australia/Melbourne",
        ]

        # Format timezone data
        timezone_data = []
        for tz_name in common_timezones:
            try:
                tz = pytz.timezone(tz_name)
                timezone_data.append(
                    {
                        "id": tz_name,
                        "name": tz_name.replace("_", " "),
                        "offset": str(tz.utcoffset(pytz.datetime.datetime.now())),
                    }
                )
            except Exception:
                continue

        return APIResponse(
            success=True,
            message="Supported timezones retrieved successfully",
            data=timezone_data,
        )

    except Exception as e:
        logger.error(f"Error getting timezones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve timezones",
        )


@router.get("/preferences/template", response_model=APIResponse[dict])
async def get_notification_preferences_template() -> APIResponse[dict]:
    """
    Get notification preferences template.

    Returns the structure and default values for notification preferences
    to help frontend applications build preference forms.
    """
    try:
        template = {
            "email_enabled": {
                "type": "boolean",
                "default": True,
                "description": "Enable email notifications",
            },
            "push_enabled": {
                "type": "boolean",
                "default": True,
                "description": "Enable push notifications",
            },
            "sms_enabled": {
                "type": "boolean",
                "default": False,
                "description": "Enable SMS notifications",
            },
            "price_alerts": {
                "type": "boolean",
                "default": True,
                "description": "Stock price alerts",
            },
            "volume_alerts": {
                "type": "boolean",
                "default": True,
                "description": "Trading volume alerts",
            },
            "earnings_announcements": {
                "type": "boolean",
                "default": True,
                "description": "Earnings announcement notifications",
            },
            "news_alerts": {
                "type": "boolean",
                "default": True,
                "description": "Stock news alerts",
            },
            "ai_analysis_complete": {
                "type": "boolean",
                "default": True,
                "description": "AI analysis completion notifications",
            },
            "system_maintenance": {
                "type": "boolean",
                "default": True,
                "description": "System maintenance notifications",
            },
            "account_updates": {
                "type": "boolean",
                "default": True,
                "description": "Account update notifications",
            },
            "subscription_updates": {
                "type": "boolean",
                "default": True,
                "description": "Subscription update notifications",
            },
            "watchlist_updates": {
                "type": "boolean",
                "default": True,
                "description": "Watchlist update notifications",
            },
            "market_updates": {
                "type": "boolean",
                "default": False,
                "description": "General market update notifications",
            },
            "quiet_hours_enabled": {
                "type": "boolean",
                "default": False,
                "description": "Enable quiet hours (no notifications)",
            },
            "quiet_hours_start": {
                "type": "string",
                "default": "22:00",
                "description": "Quiet hours start time (HH:MM)",
            },
            "quiet_hours_end": {
                "type": "string",
                "default": "08:00",
                "description": "Quiet hours end time (HH:MM)",
            },
            "digest_enabled": {
                "type": "boolean",
                "default": False,
                "description": "Enable daily digest emails",
            },
            "digest_time": {
                "type": "string",
                "default": "09:00",
                "description": "Daily digest email time (HH:MM)",
            },
            "max_notifications_per_hour": {
                "type": "integer",
                "default": 10,
                "description": "Maximum notifications per hour",
            },
        }

        return APIResponse(
            success=True,
            message="Notification preferences template retrieved successfully",
            data=template,
        )

    except Exception as e:
        logger.error(f"Error getting preferences template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences template",
        )
