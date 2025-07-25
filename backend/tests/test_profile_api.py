"""Tests for user profile API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from io import BytesIO

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.user_profile_service import (
    ProfileNotFoundError,
    InvalidProfileDataError,
    ProfileError
)
from app.schemas.user import UserProfile, UserWithProfile
from app.models.user import User


client = TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock current user."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_profile_data():
    """Mock profile data."""
    return {
        "user_id": str(uuid4()),
        "display_name": "Test User",
        "avatar_url": None,
        "timezone": "Asia/Tokyo",
        "notification_preferences": {
            "email_enabled": True,
            "push_enabled": True,
            "price_alerts": True
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_user_with_profile():
    """Mock user with profile data."""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
        "email_verified_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "profile": {
            "display_name": "Test User",
            "avatar_url": None,
            "timezone": "Asia/Tokyo",
            "notification_preferences": {
                "email_enabled": True,
                "push_enabled": True
            }
        }
    }


class TestProfileAPI:
    """Test profile API endpoints."""

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_get_current_user_profile_success(self, mock_get_service, mock_get_user, mock_current_user, mock_user_with_profile):
        """Test successful profile retrieval."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_service = Mock()
        mock_service.get_user_with_profile = AsyncMock(return_value=mock_user_with_profile)
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/profile/me")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "User profile retrieved successfully"
        assert "data" in data

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_get_current_user_profile_not_found(self, mock_get_service, mock_get_user, mock_current_user):
        """Test profile retrieval when profile not found."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_service = Mock()
        mock_service.get_user_with_profile = AsyncMock(side_effect=ProfileNotFoundError("Profile not found"))
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/profile/me")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Profile not found"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_update_current_user_profile_success(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user, mock_profile_data):
        """Test successful profile update."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        mock_service.update_user_profile = AsyncMock(return_value=mock_profile_data)
        mock_get_service.return_value = mock_service
        
        update_data = {
            "display_name": "Updated Name",
            "timezone": "US/Pacific"
        }
        
        # Act
        response = client.put("/api/v1/profile/me", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Profile updated successfully"
        assert "data" in data

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_update_current_user_profile_invalid_data(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user):
        """Test profile update with invalid data."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        mock_service.update_user_profile = AsyncMock(side_effect=InvalidProfileDataError("Invalid timezone"))
        mock_get_service.return_value = mock_service
        
        update_data = {
            "timezone": "Invalid/Timezone"
        }
        
        # Act
        response = client.put("/api/v1/profile/me", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Invalid timezone"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_update_notification_preferences_success(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user, mock_profile_data):
        """Test successful notification preferences update."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        mock_service.update_notification_preferences = AsyncMock(return_value=mock_profile_data)
        mock_get_service.return_value = mock_service
        
        preferences = {
            "email_enabled": False,
            "push_enabled": True,
            "price_alerts": False
        }
        
        # Act
        response = client.put("/api/v1/profile/me/preferences", json=preferences)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Notification preferences updated successfully"
        assert "data" in data

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_upload_avatar_success(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user):
        """Test successful avatar upload."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        expected_url = "https://storage.kessan.com/avatars/test.jpg"
        mock_service.upload_avatar = AsyncMock(return_value=expected_url)
        mock_get_service.return_value = mock_service
        
        # Create fake image file
        image_data = b'\xff\xd8\xff\xe0' + b'0' * 1000  # JPEG header + data
        files = {
            "avatar": ("test.jpg", BytesIO(image_data), "image/jpeg")
        }
        
        # Act
        response = client.post("/api/v1/profile/me/avatar", files=files)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Avatar uploaded successfully"
        assert data["data"]["avatar_url"] == expected_url

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_upload_avatar_invalid_file_type(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user):
        """Test avatar upload with invalid file type."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_get_service.return_value = Mock()
        
        # Create fake text file
        text_data = b'This is not an image'
        files = {
            "avatar": ("test.txt", BytesIO(text_data), "text/plain")
        }
        
        # Act
        response = client.post("/api/v1/profile/me/avatar", files=files)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "File must be an image"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_upload_avatar_invalid_image_data(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user):
        """Test avatar upload with invalid image data."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        mock_service.upload_avatar = AsyncMock(side_effect=InvalidProfileDataError("Invalid image format or size"))
        mock_get_service.return_value = mock_service
        
        # Create fake image file
        image_data = b'invalid image data'
        files = {
            "avatar": ("test.jpg", BytesIO(image_data), "image/jpeg")
        }
        
        # Act
        response = client.post("/api/v1/profile/me/avatar", files=files)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Invalid image format or size"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_delete_avatar_success(self, mock_get_service, mock_get_user, mock_current_user):
        """Test successful avatar deletion."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_service = Mock()
        mock_service.delete_avatar = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.delete("/api/v1/profile/me/avatar")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Avatar deleted successfully"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_delete_avatar_not_found(self, mock_get_service, mock_get_user, mock_current_user):
        """Test avatar deletion when profile not found."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_service = Mock()
        mock_service.delete_avatar = AsyncMock(side_effect=ProfileNotFoundError("User profile not found"))
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.delete("/api/v1/profile/me/avatar")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "User profile not found"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_get_user_activity_success(self, mock_get_service, mock_get_user, mock_current_user):
        """Test successful user activity retrieval."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_service = Mock()
        activity_data = {
            "recent_activities": [
                {
                    "type": "login_success",
                    "timestamp": datetime.utcnow().isoformat(),
                    "ip_address": "192.168.1.1",
                    "metadata": {}
                }
            ],
            "total_activities": 5,
            "login_count": 3
        }
        mock_service.get_user_activity_summary = AsyncMock(return_value=activity_data)
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/profile/me/activity")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "User activity retrieved successfully"
        assert data["data"]["total_activities"] == 5
        assert data["data"]["login_count"] == 3

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_export_user_data_success(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user):
        """Test successful user data export."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        export_data = {
            "user": {
                "id": str(mock_current_user.id),
                "email": mock_current_user.email,
                "created_at": datetime.utcnow().isoformat()
            },
            "profile": {
                "display_name": "Test User",
                "timezone": "Asia/Tokyo"
            },
            "activities": [],
            "oauth_identities": [],
            "export_timestamp": datetime.utcnow().isoformat()
        }
        mock_service.export_user_data = AsyncMock(return_value=export_data)
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/profile/me/export")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "User data exported successfully"
        assert data["data"]["user"]["email"] == mock_current_user.email

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_export_user_data_not_found(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user):
        """Test user data export when user not found."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        mock_service.export_user_data = AsyncMock(side_effect=ProfileNotFoundError("User not found"))
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/profile/me/export")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "User not found"

    def test_get_supported_timezones_success(self):
        """Test successful timezone list retrieval."""
        # Act
        response = client.get("/api/v1/profile/timezones")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Supported timezones retrieved successfully"
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        
        # Check that Asia/Tokyo is in the list (prioritized for Japanese platform)
        timezone_ids = [tz["id"] for tz in data["data"]]
        assert "Asia/Tokyo" in timezone_ids

    def test_get_notification_preferences_template_success(self):
        """Test successful notification preferences template retrieval."""
        # Act
        response = client.get("/api/v1/profile/preferences/template")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Notification preferences template retrieved successfully"
        assert isinstance(data["data"], dict)
        
        # Check that expected preference keys are present
        template = data["data"]
        expected_keys = [
            "email_enabled",
            "push_enabled",
            "price_alerts",
            "volume_alerts",
            "earnings_announcements",
            "news_alerts"
        ]
        
        for key in expected_keys:
            assert key in template
            assert "type" in template[key]
            assert "default" in template[key]
            assert "description" in template[key]

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_api_error_handling(self, mock_get_service, mock_get_user, mock_current_user):
        """Test API error handling for unexpected errors."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_service = Mock()
        mock_service.get_user_with_profile = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/profile/me")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"] == "Failed to retrieve user profile"

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    @patch('app.api.v1.profile.rate_limit_api')
    def test_rate_limiting_applied(self, mock_rate_limit, mock_get_service, mock_get_user, mock_current_user, mock_profile_data):
        """Test that rate limiting is applied to appropriate endpoints."""
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_rate_limit.return_value = None
        mock_service = Mock()
        mock_service.update_user_profile = AsyncMock(return_value=mock_profile_data)
        mock_get_service.return_value = mock_service
        
        update_data = {"display_name": "Test"}
        
        # Act
        response = client.put("/api/v1/profile/me", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_rate_limit.assert_called_once()

    @patch('app.api.v1.profile.get_current_active_user')
    @patch('app.api.v1.profile.get_profile_service')
    def test_authentication_required(self, mock_get_service, mock_get_user):
        """Test that authentication is required for profile endpoints."""
        # Arrange
        mock_get_user.side_effect = Exception("Authentication required")
        
        # Act
        response = client.get("/api/v1/profile/me")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR