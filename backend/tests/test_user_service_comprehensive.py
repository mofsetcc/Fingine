"""
Comprehensive unit tests for user service business logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4, UUID

from app.services.user_service import (
    UserService,
    UserServiceError,
    UserNotFoundError,
    InvalidPasswordError,
    WeakPasswordError,
    EmailAlreadyExistsError
)
from app.models.user import User, UserProfile, UserOAuthIdentity
from app.schemas.user import UserProfileUpdate


class TestUserService:
    """Test cases for UserService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        email_service = Mock()
        email_service.send_subscription_notification = AsyncMock()
        return email_service
    
    @pytest.fixture
    def user_service(self, mock_db, mock_email_service):
        """UserService instance with mocked dependencies."""
        return UserService(db=mock_db, email_service=mock_email_service)
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="hashed_password",
            email_verified_at="2024-01-01T00:00:00Z",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        user.profile = UserProfile(
            user_id=user_id,
            display_name="Test User",
            timezone="Asia/Tokyo",
            notification_preferences={"email": True},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return user
    
    def test_get_user_profile_success(self, user_service, mock_db, sample_user):
        """Test successful user profile retrieval."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        # Act
        result = user_service.get_user_profile(sample_user.id)
        
        # Assert
        assert result is not None
        mock_db.query.assert_called_once()
    
    def test_get_user_profile_not_found(self, user_service, mock_db):
        """Test user profile retrieval when user not found."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match="User not found"):
            user_service.get_user_profile(user_id)
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_db, sample_user):
        """Test successful user profile update."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        profile_update = UserProfileUpdate(
            display_name="Updated Name",
            timezone="America/New_York"
        )
        
        # Act
        result = await user_service.update_user_profile(sample_user.id, profile_update)
        
        # Assert
        assert sample_user.profile.display_name == "Updated Name"
        assert sample_user.profile.timezone == "America/New_York"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_profile_create_new_profile(self, user_service, mock_db):
        """Test updating user profile when profile doesn't exist."""
        # Arrange
        user_id = uuid4()
        user = User(id=user_id, email="test@example.com")
        user.profile = None  # No existing profile
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        profile_update = UserProfileUpdate(display_name="New User")
        
        # Act
        await user_service.update_user_profile(user_id, profile_update)
        
        # Assert
        mock_db.add.assert_called_once()  # New profile should be added
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_profile_user_not_found(self, user_service, mock_db):
        """Test updating user profile when user not found."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        profile_update = UserProfileUpdate(display_name="Test")
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match="User not found"):
            await user_service.update_user_profile(user_id, profile_update)
    
    @pytest.mark.asyncio
    async def test_update_user_profile_database_error(self, user_service, mock_db, sample_user):
        """Test handling database error during profile update."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.commit.side_effect = Exception("Database error")
        profile_update = UserProfileUpdate(display_name="Test")
        
        # Act & Assert
        with pytest.raises(UserServiceError, match="Failed to update profile"):
            await user_service.update_user_profile(sample_user.id, profile_update)
        
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.validate_password_strength')
    @patch('app.services.user_service.get_password_hash')
    async def test_change_password_success(
        self,
        mock_get_hash,
        mock_validate,
        mock_verify,
        user_service,
        mock_db,
        sample_user
    ):
        """Test successful password change."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_verify.return_value = True
        mock_validate.return_value = (True, [])
        mock_get_hash.return_value = "new_hashed_password"
        
        # Act
        result = await user_service.change_password(
            sample_user.id,
            "current_password",
            "new_strong_password"
        )
        
        # Assert
        assert result is True
        assert sample_user.password_hash == "new_hashed_password"
        mock_verify.assert_called_once_with("current_password", "hashed_password")
        mock_validate.assert_called_once_with("new_strong_password")
        mock_get_hash.assert_called_once_with("new_strong_password")
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.verify_password')
    async def test_change_password_invalid_current(
        self,
        mock_verify,
        user_service,
        mock_db,
        sample_user
    ):
        """Test password change with invalid current password."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_verify.return_value = False
        
        # Act & Assert
        with pytest.raises(InvalidPasswordError, match="Current password is incorrect"):
            await user_service.change_password(
                sample_user.id,
                "wrong_password",
                "new_password"
            )
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.validate_password_strength')
    async def test_change_password_weak_new_password(
        self,
        mock_validate,
        mock_verify,
        user_service,
        mock_db,
        sample_user
    ):
        """Test password change with weak new password."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_verify.return_value = True
        mock_validate.return_value = (False, ["Password too short", "No special characters"])
        
        # Act & Assert
        with pytest.raises(WeakPasswordError) as exc_info:
            await user_service.change_password(
                sample_user.id,
                "current_password",
                "weak"
            )
        
        assert "Password too short" in str(exc_info.value)
        assert "No special characters" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_change_password_oauth_user(self, user_service, mock_db):
        """Test password change for OAuth-only user (no password hash)."""
        # Arrange
        user = User(id=uuid4(), email="oauth@example.com", password_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Act & Assert
        with pytest.raises(InvalidPasswordError, match="User doesn't have a password set"):
            await user_service.change_password(user.id, "current", "new")
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.validate_password_strength')
    @patch('app.services.user_service.get_password_hash')
    async def test_set_password_success(
        self,
        mock_get_hash,
        mock_validate,
        user_service,
        mock_db
    ):
        """Test successful password setting for OAuth user."""
        # Arrange
        user = User(id=uuid4(), email="oauth@example.com", password_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_validate.return_value = (True, [])
        mock_get_hash.return_value = "new_hashed_password"
        
        # Act
        result = await user_service.set_password(user.id, "strong_password")
        
        # Assert
        assert result is True
        assert user.password_hash == "new_hashed_password"
        mock_validate.assert_called_once_with("strong_password")
        mock_get_hash.assert_called_once_with("strong_password")
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.verify_password')
    async def test_change_email_success(
        self,
        mock_verify,
        user_service,
        mock_db,
        sample_user
    ):
        """Test successful email change."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user,  # First call: get user
            None  # Second call: check if new email exists
        ]
        mock_verify.return_value = True
        
        # Act
        result = await user_service.change_email(
            sample_user.id,
            "new@example.com",
            "current_password"
        )
        
        # Assert
        assert result is True
        assert sample_user.email == "new@example.com"
        assert sample_user.email_verified_at is None  # Should be reset
        mock_verify.assert_called_once_with("current_password", "hashed_password")
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_email_already_exists(self, user_service, mock_db, sample_user):
        """Test email change when new email already exists."""
        # Arrange
        existing_user = User(id=uuid4(), email="new@example.com")
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user,  # First call: get user
            existing_user  # Second call: email already exists
        ]
        
        # Act & Assert
        with pytest.raises(EmailAlreadyExistsError, match="Email address already in use"):
            await user_service.change_email(sample_user.id, "new@example.com", "password")
    
    def test_get_user_oauth_identities_success(self, user_service, mock_db, sample_user):
        """Test getting user OAuth identities."""
        # Arrange
        oauth_identity = UserOAuthIdentity(
            provider="google",
            provider_user_id="google_123",
            user_id=sample_user.id,
            created_at=datetime.utcnow()
        )
        mock_db.query.return_value.filter.side_effect = [
            Mock(first=Mock(return_value=sample_user)),  # User query
            Mock(all=Mock(return_value=[oauth_identity]))  # OAuth identities query
        ]
        
        # Act
        result = user_service.get_user_oauth_identities(sample_user.id)
        
        # Assert
        assert len(result) == 1
        assert result[0]["provider"] == "google"
        assert result[0]["provider_user_id"] == "google_123"
        assert "linked_at" in result[0]
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.verify_password')
    async def test_delete_user_account_success(
        self,
        mock_verify,
        user_service,
        mock_db,
        sample_user
    ):
        """Test successful user account deletion."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_verify.return_value = True
        
        # Act
        result = await user_service.delete_user_account(
            sample_user.id,
            "current_password",
            "DELETE"
        )
        
        # Assert
        assert result is True
        mock_verify.assert_called_once_with("current_password", "hashed_password")
        mock_db.delete.assert_called_once_with(sample_user)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_account_invalid_confirmation(self, user_service, mock_db):
        """Test user account deletion with invalid confirmation."""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Confirmation string must be 'DELETE'"):
            await user_service.delete_user_account(user_id, "password", "WRONG")
    
    @pytest.mark.asyncio
    async def test_export_user_data_success(self, user_service, mock_db, sample_user):
        """Test successful user data export."""
        # Arrange
        mock_db.query.return_value.filter.side_effect = [
            Mock(first=Mock(return_value=sample_user)),  # User query
            Mock(all=Mock(return_value=[]))  # OAuth identities query (empty)
        ]
        
        # Act
        result = await user_service.export_user_data(sample_user.id)
        
        # Assert
        assert "user_info" in result
        assert "profile" in result
        assert "oauth_identities" in result
        assert "export_date" in result
        assert result["user_info"]["email"] == "test@example.com"
        assert result["profile"]["display_name"] == "Test User"
    
    def test_get_user_activity_log_placeholder(self, user_service, mock_db, sample_user):
        """Test user activity log (placeholder implementation)."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        # Act
        result = user_service.get_user_activity_log(sample_user.id)
        
        # Assert
        assert result == []  # Currently returns empty list


class TestUserServiceErrorHandling:
    """Test error handling in UserService."""
    
    @pytest.fixture
    def user_service(self):
        """UserService instance with mocked dependencies."""
        mock_db = Mock()
        mock_email_service = Mock()
        return UserService(db=mock_db, email_service=mock_email_service)
    
    def test_user_service_error_inheritance(self):
        """Test that custom exceptions inherit from UserServiceError."""
        assert issubclass(UserNotFoundError, UserServiceError)
        assert issubclass(InvalidPasswordError, UserServiceError)
        assert issubclass(WeakPasswordError, UserServiceError)
        assert issubclass(EmailAlreadyExistsError, UserServiceError)
    
    def test_weak_password_error_with_errors(self):
        """Test WeakPasswordError with error list."""
        errors = ["Password too short", "No special characters"]
        exception = WeakPasswordError(errors)
        
        assert exception.errors == errors
        assert "Password too short" in str(exception)
        assert "No special characters" in str(exception)
    
    @pytest.mark.asyncio
    async def test_email_notification_failure_handling(self, user_service):
        """Test that email notification failures don't break the main operation."""
        # Arrange
        mock_db = user_service.db
        user = User(id=uuid4(), email="test@example.com", password_hash="hash")
        user.profile = UserProfile(user_id=user.id, display_name="Test")
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Mock email service to raise exception
        user_service.email_service.send_subscription_notification.side_effect = Exception("Email failed")
        
        # Act - should not raise exception even if email fails
        await user_service._send_password_changed_notification(user)
        
        # Assert - method should complete without raising exception
        user_service.email_service.send_subscription_notification.assert_called_once()


class TestUserServiceIntegration:
    """Integration-style tests for UserService methods working together."""
    
    @pytest.fixture
    def user_service_with_mocks(self):
        """UserService with properly configured mocks."""
        mock_db = Mock()
        mock_email_service = Mock()
        mock_email_service.send_subscription_notification = AsyncMock()
        return UserService(db=mock_db, email_service=mock_email_service), mock_db, mock_email_service
    
    @pytest.mark.asyncio
    async def test_complete_user_profile_workflow(self, user_service_with_mocks):
        """Test complete workflow of user profile operations."""
        user_service, mock_db, mock_email_service = user_service_with_mocks
        
        # Create user
        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", password_hash="hash")
        user.profile = None
        
        # Mock database responses
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Update profile (should create new profile)
        profile_update = UserProfileUpdate(
            display_name="Test User",
            timezone="America/New_York"
        )
        
        await user_service.update_user_profile(user_id, profile_update)
        
        # Verify profile was created and added to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.validate_password_strength')
    @patch('app.services.user_service.get_password_hash')
    async def test_password_change_with_notification(
        self,
        mock_get_hash,
        mock_validate,
        mock_verify,
        user_service_with_mocks
    ):
        """Test password change includes email notification."""
        user_service, mock_db, mock_email_service = user_service_with_mocks
        
        # Setup
        user = User(id=uuid4(), email="test@example.com", password_hash="old_hash")
        user.profile = UserProfile(user_id=user.id, display_name="Test User")
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_verify.return_value = True
        mock_validate.return_value = (True, [])
        mock_get_hash.return_value = "new_hash"
        
        # Act
        await user_service.change_password(user.id, "old_pass", "new_pass")
        
        # Assert
        mock_email_service.send_subscription_notification.assert_called_once()
        call_args = mock_email_service.send_subscription_notification.call_args
        assert call_args[1]["email"] == "test@example.com"
        assert call_args[1]["notification_type"] == "password_changed"