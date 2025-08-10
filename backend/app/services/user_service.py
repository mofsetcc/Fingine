"""
User profile management service.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_password_reset_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
    verify_password_reset_token,
)
from app.models.user import User, UserOAuthIdentity, UserProfile
from app.schemas.user import PasswordChange
from app.schemas.user import User as UserSchema
from app.schemas.user import UserActivityLog, UserPreferencesUpdate
from app.schemas.user import UserProfile as UserProfileSchema
from app.schemas.user import UserProfileUpdate, UserWithProfile
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    """Base exception for user service errors."""

    pass


class UserNotFoundError(UserServiceError):
    """Raised when user is not found."""

    pass


class InvalidPasswordError(UserServiceError):
    """Raised when current password is invalid."""

    pass


class WeakPasswordError(UserServiceError):
    """Raised when new password doesn't meet requirements."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Password validation failed: {', '.join(errors)}")


class EmailAlreadyExistsError(UserServiceError):
    """Raised when trying to change to an email that already exists."""

    pass


class UserService:
    """Service for user profile and account management."""

    def __init__(self, db: Session, email_service: Optional[EmailService] = None):
        self.db = db
        self.email_service = email_service or EmailService()

    def get_user_profile(self, user_id: UUID) -> UserWithProfile:
        """
        Get user profile with all related information.

        Args:
            user_id: User ID

        Returns:
            User with profile information

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        return UserWithProfile.from_orm(user)

    async def update_user_profile(
        self, user_id: UUID, profile_data: UserProfileUpdate
    ) -> UserProfileSchema:
        """
        Update user profile information.

        Args:
            user_id: User ID
            profile_data: Profile update data

        Returns:
            Updated user profile

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Get or create profile
        profile = user.profile
        if not profile:
            profile = UserProfile(
                user_id=user_id, timezone="Asia/Tokyo", notification_preferences={}
            )
            self.db.add(profile)

        # Update profile fields
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(profile)

            logger.info(f"Profile updated for user: {user.email}")

            return UserProfileSchema.from_orm(profile)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update profile for user {user_id}: {e}")
            raise UserServiceError("Failed to update profile")

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            UserNotFoundError: If user not found
            InvalidPasswordError: If current password is invalid
            WeakPasswordError: If new password doesn't meet requirements
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Check if user has a password (OAuth-only users don't)
        if not user.password_hash:
            raise InvalidPasswordError("User doesn't have a password set")

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            logger.warning(f"Invalid current password for user: {user.email}")
            raise InvalidPasswordError("Current password is incorrect")

        # Validate new password strength
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            logger.warning(f"Weak password attempt for user: {user.email}")
            raise WeakPasswordError(errors)

        # Update password
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()

        try:
            self.db.commit()

            logger.info(f"Password changed for user: {user.email}")

            # Send password change notification email
            await self._send_password_changed_notification(user)

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise UserServiceError("Failed to change password")

    async def set_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Set password for OAuth-only user.

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            True if password set successfully

        Raises:
            UserNotFoundError: If user not found
            WeakPasswordError: If password doesn't meet requirements
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Validate password strength
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            logger.warning(f"Weak password attempt for user: {user.email}")
            raise WeakPasswordError(errors)

        # Set password
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()

        try:
            self.db.commit()

            logger.info(f"Password set for OAuth user: {user.email}")

            # Send password set notification email
            await self._send_password_set_notification(user)

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set password for user {user_id}: {e}")
            raise UserServiceError("Failed to set password")

    async def change_email(
        self, user_id: UUID, new_email: str, password: Optional[str] = None
    ) -> bool:
        """
        Change user email address.

        Args:
            user_id: User ID
            new_email: New email address
            password: Current password (required if user has password)

        Returns:
            True if email change initiated successfully

        Raises:
            UserNotFoundError: If user not found
            EmailAlreadyExistsError: If email already exists
            InvalidPasswordError: If password is required but invalid
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Check if new email already exists
        existing_user = (
            self.db.query(User)
            .filter(User.email == new_email, User.id != user_id)
            .first()
        )
        if existing_user:
            raise EmailAlreadyExistsError("Email address already in use")

        # Verify password if user has one
        if user.password_hash:
            if not password:
                raise InvalidPasswordError("Password required to change email")
            if not verify_password(password, user.password_hash):
                raise InvalidPasswordError("Invalid password")

        # Store old email for notification
        old_email = user.email

        # Update email and mark as unverified
        user.email = new_email
        user.email_verified_at = None
        user.updated_at = datetime.utcnow()

        try:
            self.db.commit()

            logger.info(f"Email changed from {old_email} to {new_email}")

            # Send verification email to new address
            from app.services.auth_service import AuthService

            auth_service = AuthService(self.db, self.email_service)
            await auth_service._send_verification_email(user)

            # Send notification to old email
            await self._send_email_changed_notification(old_email, new_email)

            return True

        except IntegrityError:
            self.db.rollback()
            raise EmailAlreadyExistsError("Email address already in use")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to change email for user {user_id}: {e}")
            raise UserServiceError("Failed to change email")

    def get_user_oauth_identities(self, user_id: UUID) -> List[dict]:
        """
        Get user's linked OAuth identities.

        Args:
            user_id: User ID

        Returns:
            List of OAuth identities

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        oauth_identities = (
            self.db.query(UserOAuthIdentity)
            .filter(UserOAuthIdentity.user_id == user_id)
            .all()
        )

        return [
            {
                "provider": identity.provider,
                "provider_user_id": identity.provider_user_id,
                "linked_at": identity.created_at.isoformat(),
            }
            for identity in oauth_identities
        ]

    async def delete_user_account(
        self,
        user_id: UUID,
        password: Optional[str] = None,
        confirmation: str = "DELETE",
    ) -> bool:
        """
        Delete user account and all associated data.

        Args:
            user_id: User ID
            password: Current password (required if user has password)
            confirmation: Confirmation string (must be "DELETE")

        Returns:
            True if account deleted successfully

        Raises:
            UserNotFoundError: If user not found
            InvalidPasswordError: If password is required but invalid
            ValueError: If confirmation string is incorrect
        """
        if confirmation != "DELETE":
            raise ValueError("Confirmation string must be 'DELETE'")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Verify password if user has one
        if user.password_hash:
            if not password:
                raise InvalidPasswordError("Password required to delete account")
            if not verify_password(password, user.password_hash):
                raise InvalidPasswordError("Invalid password")

        try:
            # Store email for notification
            user_email = user.email
            display_name = user.profile.display_name if user.profile else None

            # Delete user (cascade will handle related records)
            self.db.delete(user)
            self.db.commit()

            logger.info(f"User account deleted: {user_email}")

            # Send account deletion confirmation email
            await self._send_account_deleted_notification(user_email, display_name)

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete user account {user_id}: {e}")
            raise UserServiceError("Failed to delete account")

    def get_user_activity_log(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[UserActivityLog]:
        """
        Get user activity log.

        Args:
            user_id: User ID
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of user activity records

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # TODO: Implement user activity logging
        # For now, return empty list
        return []

    async def export_user_data(self, user_id: UUID) -> dict:
        """
        Export all user data for GDPR compliance.

        Args:
            user_id: User ID

        Returns:
            Dictionary containing all user data

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Get OAuth identities
        oauth_identities = self.get_user_oauth_identities(user_id)

        # Compile user data
        user_data = {
            "user_info": {
                "id": str(user.id),
                "email": user.email,
                "email_verified_at": user.email_verified_at.isoformat()
                if user.email_verified_at
                else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            },
            "profile": {
                "display_name": user.profile.display_name if user.profile else None,
                "avatar_url": user.profile.avatar_url if user.profile else None,
                "timezone": user.profile.timezone if user.profile else None,
                "notification_preferences": user.profile.notification_preferences
                if user.profile
                else {},
            },
            "oauth_identities": oauth_identities,
            "export_date": datetime.utcnow().isoformat(),
        }

        logger.info(f"User data exported for: {user.email}")

        return user_data

    async def _send_password_changed_notification(self, user: User) -> None:
        """Send password changed notification email."""
        try:
            await self.email_service.send_subscription_notification(
                email=user.email,
                notification_type="password_changed",
                display_name=user.profile.display_name if user.profile else None,
            )
        except Exception as e:
            logger.error(
                f"Failed to send password changed notification to {user.email}: {e}"
            )

    async def _send_password_set_notification(self, user: User) -> None:
        """Send password set notification email."""
        try:
            await self.email_service.send_subscription_notification(
                email=user.email,
                notification_type="password_set",
                display_name=user.profile.display_name if user.profile else None,
            )
        except Exception as e:
            logger.error(
                f"Failed to send password set notification to {user.email}: {e}"
            )

    async def _send_email_changed_notification(
        self, old_email: str, new_email: str
    ) -> None:
        """Send email changed notification to old email address."""
        try:
            await self.email_service.send_subscription_notification(
                email=old_email, notification_type="email_changed", new_email=new_email
            )
        except Exception as e:
            logger.error(
                f"Failed to send email changed notification to {old_email}: {e}"
            )

    async def _send_account_deleted_notification(
        self, email: str, display_name: Optional[str]
    ) -> None:
        """Send account deletion confirmation email."""
        try:
            await self.email_service.send_subscription_notification(
                email=email,
                notification_type="account_deleted",
                display_name=display_name,
            )
        except Exception as e:
            logger.error(f"Failed to send account deleted notification to {email}: {e}")
