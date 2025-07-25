"""Tests for user profile service."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.services.user_profile_service import (
    UserProfileService,
    ProfileError,
    ProfileNotFoundError,
    InvalidProfileDataError
)
from app.models.user import User, UserProfile, UserActivity, UserOAuthIdentity
from app.schemas.user import UserProfileUpdate
from app.services.email_service import EmailService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    return Mock(spec=EmailService)


@pytest.fixture
def profile_service(mock_db, mock_email_service):
    """Create profile service instance."""
    return UserProfileService(mock_db, mock_email_service)


@pytest.fixture
def sample_user():
    """Create sample user."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.email_verified_at = datetime.utcnow()
    return user


@pytest.fixture
def sample_profile():
    """Create sample user profile."""
    profile = Mock(spec=UserProfile)
    profile.user_id = uuid4()
    profile.display_name = "Test User"
    profile.avatar_url = None
    profile.timezone = "Asia/Tokyo"
    profile.notification_preferences = {
        "email_enabled": True,
        "push_enabled": True,
        "price_alerts": True
    }
    profile.created_at = datetime.utcnow()
    profile.updated_at = datetime.utcnow()
    return profile


class TestUserProfileService:
    """Test user profile service."""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, profile_service, mock_db, sample_profile):
        """Test successful profile retrieval."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        # Act
        result = await profile_service.get_user_profile(user_id)
        
        # Assert
        assert result is not None
        mock_db.query.assert_called_once_with(UserProfile)

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, profile_service, mock_db):
        """Test profile not found error."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ProfileNotFoundError):
            await profile_service.get_user_profile(user_id)

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, profile_service, mock_db, sample_profile):
        """Test successful profile update."""
        # Arrange
        user_id = uuid4()
        profile_data = UserProfileUpdate(
            display_name="Updated Name",
            timezone="US/Pacific"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        with patch.object(profile_service, '_is_valid_timezone', return_value=True):
            # Act
            result = await profile_service.update_user_profile(user_id, profile_data)
            
            # Assert
            assert result is not None
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(sample_profile)

    @pytest.mark.asyncio
    async def test_update_user_profile_invalid_timezone(self, profile_service, mock_db, sample_profile):
        """Test profile update with invalid timezone."""
        # Arrange
        user_id = uuid4()
        profile_data = UserProfileUpdate(timezone="Invalid/Timezone")
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        with patch.object(profile_service, '_is_valid_timezone', return_value=False):
            # Act & Assert
            with pytest.raises(InvalidProfileDataError):
                await profile_service.update_user_profile(user_id, profile_data)

    @pytest.mark.asyncio
    async def test_update_user_profile_not_found(self, profile_service, mock_db):
        """Test profile update when profile not found."""
        # Arrange
        user_id = uuid4()
        profile_data = UserProfileUpdate(display_name="Test")
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ProfileNotFoundError):
            await profile_service.update_user_profile(user_id, profile_data)

    @pytest.mark.asyncio
    async def test_update_user_profile_integrity_error(self, profile_service, mock_db, sample_profile):
        """Test profile update with database integrity error."""
        # Arrange
        user_id = uuid4()
        profile_data = UserProfileUpdate(display_name="Test")
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        mock_db.commit.side_effect = IntegrityError("test", "test", "test")
        
        # Act & Assert
        with pytest.raises(InvalidProfileDataError):
            await profile_service.update_user_profile(user_id, profile_data)
        
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_with_profile_success(self, profile_service, mock_db, sample_user):
        """Test successful user with profile retrieval."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        # Act
        result = await profile_service.get_user_with_profile(user_id)
        
        # Assert
        assert result is not None
        mock_db.query.assert_called_once_with(User)

    @pytest.mark.asyncio
    async def test_get_user_with_profile_not_found(self, profile_service, mock_db):
        """Test user with profile not found."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ProfileNotFoundError):
            await profile_service.get_user_with_profile(user_id)

    @pytest.mark.asyncio
    async def test_update_notification_preferences_success(self, profile_service, mock_db, sample_profile):
        """Test successful notification preferences update."""
        # Arrange
        user_id = uuid4()
        preferences = {
            "email_enabled": False,
            "push_enabled": True,
            "price_alerts": False
        }
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        # Act
        result = await profile_service.update_notification_preferences(user_id, preferences)
        
        # Assert
        assert result is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(sample_profile)

    @pytest.mark.asyncio
    async def test_update_notification_preferences_not_found(self, profile_service, mock_db):
        """Test notification preferences update when profile not found."""
        # Arrange
        user_id = uuid4()
        preferences = {"email_enabled": False}
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ProfileNotFoundError):
            await profile_service.update_notification_preferences(user_id, preferences)

    @pytest.mark.asyncio
    async def test_upload_avatar_success(self, profile_service, mock_db, sample_profile):
        """Test successful avatar upload."""
        # Arrange
        user_id = uuid4()
        avatar_data = b"fake_image_data"
        content_type = "image/jpeg"
        filename = "avatar.jpg"
        expected_url = "https://storage.kessan.com/avatars/test.jpg"
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        with patch.object(profile_service, '_is_valid_image', return_value=True), \
             patch.object(profile_service, '_upload_to_storage', return_value=expected_url):
            
            # Act
            result = await profile_service.upload_avatar(user_id, avatar_data, content_type, filename)
            
            # Assert
            assert result == expected_url
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_image(self, profile_service, mock_db, sample_profile):
        """Test avatar upload with invalid image."""
        # Arrange
        user_id = uuid4()
        avatar_data = b"invalid_data"
        content_type = "text/plain"
        filename = "test.txt"
        
        with patch.object(profile_service, '_is_valid_image', return_value=False):
            # Act & Assert
            with pytest.raises(InvalidProfileDataError):
                await profile_service.upload_avatar(user_id, avatar_data, content_type, filename)

    @pytest.mark.asyncio
    async def test_upload_avatar_profile_not_found(self, profile_service, mock_db):
        """Test avatar upload when profile not found."""
        # Arrange
        user_id = uuid4()
        avatar_data = b"fake_image_data"
        content_type = "image/jpeg"
        filename = "avatar.jpg"
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(profile_service, '_is_valid_image', return_value=True):
            # Act & Assert
            with pytest.raises(ProfileNotFoundError):
                await profile_service.upload_avatar(user_id, avatar_data, content_type, filename)

    @pytest.mark.asyncio
    async def test_delete_avatar_success(self, profile_service, mock_db, sample_profile):
        """Test successful avatar deletion."""
        # Arrange
        user_id = uuid4()
        sample_profile.avatar_url = "https://storage.kessan.com/avatars/test.jpg"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        with patch.object(profile_service, '_delete_from_storage', return_value=True):
            # Act
            result = await profile_service.delete_avatar(user_id)
            
            # Assert
            assert result is True
            assert sample_profile.avatar_url is None
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_avatar_no_avatar(self, profile_service, mock_db, sample_profile):
        """Test avatar deletion when no avatar exists."""
        # Arrange
        user_id = uuid4()
        sample_profile.avatar_url = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_profile
        
        # Act
        result = await profile_service.delete_avatar(user_id)
        
        # Assert
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_avatar_not_found(self, profile_service, mock_db):
        """Test avatar deletion when profile not found."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ProfileNotFoundError):
            await profile_service.delete_avatar(user_id)

    @pytest.mark.asyncio
    async def test_get_user_activity_summary_success(self, profile_service, mock_db):
        """Test successful user activity summary retrieval."""
        # Arrange
        user_id = uuid4()
        
        # Mock activities
        mock_activities = [
            Mock(
                activity_type="login_success",
                created_at=datetime.utcnow(),
                ip_address="192.168.1.1",
                metadata={}
            )
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_activities
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        # Act
        result = await profile_service.get_user_activity_summary(user_id)
        
        # Assert
        assert "recent_activities" in result
        assert "total_activities" in result
        assert "login_count" in result
        assert result["total_activities"] == 5

    @pytest.mark.asyncio
    async def test_get_user_activity_summary_error(self, profile_service, mock_db):
        """Test user activity summary with database error."""
        # Arrange
        user_id = uuid4()
        mock_db.query.side_effect = Exception("Database error")
        
        # Act
        result = await profile_service.get_user_activity_summary(user_id)
        
        # Assert
        assert result["recent_activities"] == []
        assert result["total_activities"] == 0
        assert result["login_count"] == 0

    @pytest.mark.asyncio
    async def test_export_user_data_success(self, profile_service, mock_db, sample_user, sample_profile):
        """Test successful user data export."""
        # Arrange
        user_id = uuid4()
        sample_user.profile = sample_profile
        
        mock_activities = [
            Mock(
                activity_type="login_success",
                created_at=datetime.utcnow(),
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata={}
            )
        ]
        
        mock_oauth_identities = [
            Mock(
                provider="google",
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            mock_activities,
            mock_oauth_identities
        ]
        
        # Act
        result = await profile_service.export_user_data(user_id)
        
        # Assert
        assert "user" in result
        assert "profile" in result
        assert "activities" in result
        assert "oauth_identities" in result
        assert "export_timestamp" in result
        assert result["user"]["email"] == sample_user.email

    @pytest.mark.asyncio
    async def test_export_user_data_not_found(self, profile_service, mock_db):
        """Test user data export when user not found."""
        # Arrange
        user_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ProfileNotFoundError):
            await profile_service.export_user_data(user_id)

    def test_is_valid_timezone_valid(self, profile_service):
        """Test timezone validation with valid timezone."""
        # Act & Assert
        assert profile_service._is_valid_timezone("Asia/Tokyo") is True
        assert profile_service._is_valid_timezone("UTC") is True
        assert profile_service._is_valid_timezone("US/Pacific") is True

    def test_is_valid_timezone_invalid(self, profile_service):
        """Test timezone validation with invalid timezone."""
        # Act & Assert
        assert profile_service._is_valid_timezone("Invalid/Timezone") is False
        assert profile_service._is_valid_timezone("") is False

    def test_validate_notification_preferences_valid(self, profile_service):
        """Test notification preferences validation with valid data."""
        # Arrange
        preferences = {
            "email_enabled": True,
            "push_enabled": False,
            "price_alerts": True,
            "max_notifications_per_hour": 5
        }
        
        # Act
        result = profile_service._validate_notification_preferences(preferences)
        
        # Assert
        assert result["email_enabled"] is True
        assert result["push_enabled"] is False
        assert result["price_alerts"] is True
        assert result["max_notifications_per_hour"] == 5

    def test_validate_notification_preferences_invalid_types(self, profile_service):
        """Test notification preferences validation with invalid types."""
        # Arrange
        preferences = {
            "email_enabled": "true",  # Should be boolean
            "max_notifications_per_hour": "5",  # Should be integer
            "unknown_key": "value"  # Unknown key
        }
        
        # Act
        result = profile_service._validate_notification_preferences(preferences)
        
        # Assert
        assert "email_enabled" not in result  # Invalid type excluded
        assert "max_notifications_per_hour" not in result  # Invalid type excluded
        assert "unknown_key" not in result  # Unknown key excluded

    def test_is_valid_image_jpeg(self, profile_service):
        """Test image validation with valid JPEG."""
        # Arrange
        jpeg_data = b'\xff\xd8\xff\xe0' + b'0' * 1000  # JPEG header + data
        
        # Act & Assert
        assert profile_service._is_valid_image(jpeg_data, "image/jpeg") is True

    def test_is_valid_image_png(self, profile_service):
        """Test image validation with valid PNG."""
        # Arrange
        png_data = b'\x89PNG\r\n\x1a\n' + b'0' * 1000  # PNG header + data
        
        # Act & Assert
        assert profile_service._is_valid_image(png_data, "image/png") is True

    def test_is_valid_image_invalid_type(self, profile_service):
        """Test image validation with invalid content type."""
        # Arrange
        data = b'some data'
        
        # Act & Assert
        assert profile_service._is_valid_image(data, "text/plain") is False

    def test_is_valid_image_too_large(self, profile_service):
        """Test image validation with file too large."""
        # Arrange
        large_data = b'0' * (6 * 1024 * 1024)  # 6MB (over 5MB limit)
        
        # Act & Assert
        assert profile_service._is_valid_image(large_data, "image/jpeg") is False

    def test_is_valid_image_invalid_header(self, profile_service):
        """Test image validation with invalid header."""
        # Arrange
        invalid_jpeg = b'invalid header' + b'0' * 1000
        
        # Act & Assert
        assert profile_service._is_valid_image(invalid_jpeg, "image/jpeg") is False

    @pytest.mark.asyncio
    async def test_upload_to_storage(self, profile_service):
        """Test storage upload functionality."""
        # Arrange
        user_id = uuid4()
        image_data = b'\xff\xd8\xff\xe0' + b'0' * 1000
        content_type = "image/jpeg"
        filename = "test.jpg"
        
        # Act
        result = await profile_service._upload_to_storage(user_id, image_data, content_type, filename)
        
        # Assert
        assert result.startswith("https://storage.kessan.com/avatars/")
        assert str(user_id) in result
        assert result.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_delete_from_storage(self, profile_service):
        """Test storage deletion functionality."""
        # Arrange
        avatar_url = "https://storage.kessan.com/avatars/test.jpg"
        
        # Act
        result = await profile_service._delete_from_storage(avatar_url)
        
        # Assert
        assert result is True