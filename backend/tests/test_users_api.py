"""
Integration tests for user management API endpoints.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient

from app.models.user import User, UserProfile


class TestUsersAPI:
    """Test user management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            email_verified_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        user.profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            timezone="Asia/Tokyo",
            notification_preferences={},
            updated_at=datetime.utcnow()
        )
        return user
    
    def test_get_user_profile_success(self, client, mock_user):
        """Test successful user profile retrieval."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.get_user_profile.return_value = mock_user
                
                response = client.get(
                    "/api/v1/users/profile",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["email"] == mock_user.email
    
    def test_get_user_profile_unauthorized(self, client):
        """Test user profile retrieval without authentication."""
        response = client.get("/api/v1/users/profile")
        
        assert response.status_code == 401
    
    def test_update_user_profile_success(self, client, mock_user):
        """Test successful user profile update."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                updated_profile = UserProfile(
                    user_id=mock_user.id,
                    display_name="Updated Name",
                    timezone="America/New_York",
                    notification_preferences={},
                    updated_at=datetime.utcnow()
                )
                mock_service.return_value.update_user_profile = AsyncMock(return_value=updated_profile)
                
                response = client.put(
                    "/api/v1/users/profile",
                    json={
                        "display_name": "Updated Name",
                        "timezone": "America/New_York"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["display_name"] == "Updated Name"
    
    def test_change_password_success(self, client, mock_user):
        """Test successful password change."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.change_password = AsyncMock(return_value=True)
                
                response = client.post(
                    "/api/v1/users/change-password",
                    json={
                        "current_password": "current_password",
                        "new_password": "NewStrongPass123!"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "changed successfully" in data["message"]
    
    def test_change_password_invalid_current(self, client, mock_user):
        """Test password change with invalid current password."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                from app.services.user_service import InvalidPasswordError
                mock_service.return_value.change_password = AsyncMock(
                    side_effect=InvalidPasswordError("Current password is incorrect")
                )
                
                response = client.post(
                    "/api/v1/users/change-password",
                    json={
                        "current_password": "wrong_password",
                        "new_password": "NewStrongPass123!"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "Current password is incorrect" in data["detail"]
    
    def test_change_password_weak_new_password(self, client, mock_user):
        """Test password change with weak new password."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                from app.services.user_service import WeakPasswordError
                mock_service.return_value.change_password = AsyncMock(
                    side_effect=WeakPasswordError(["Password too short"])
                )
                
                response = client.post(
                    "/api/v1/users/change-password",
                    json={
                        "current_password": "current_password",
                        "new_password": "weak"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "Password does not meet requirements" in data["detail"]["message"]
                assert "Password too short" in data["detail"]["errors"]
    
    def test_set_password_success(self, client, mock_user):
        """Test successful password setting for OAuth user."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.set_password = AsyncMock(return_value=True)
                
                response = client.post(
                    "/api/v1/users/set-password",
                    json={"new_password": "NewStrongPass123!"},
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "set successfully" in data["message"]
    
    def test_change_email_success(self, client, mock_user):
        """Test successful email change."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.change_email = AsyncMock(return_value=True)
                
                response = client.post(
                    "/api/v1/users/change-email",
                    json={
                        "new_email": "newemail@example.com",
                        "password": "current_password"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "Email change initiated" in data["message"]
    
    def test_change_email_already_exists(self, client, mock_user):
        """Test email change with existing email."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                from app.services.user_service import EmailAlreadyExistsError
                mock_service.return_value.change_email = AsyncMock(
                    side_effect=EmailAlreadyExistsError("Email address already in use")
                )
                
                response = client.post(
                    "/api/v1/users/change-email",
                    json={
                        "new_email": "existing@example.com",
                        "password": "current_password"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 409
                data = response.json()
                assert "already in use" in data["detail"]
    
    def test_get_oauth_identities_success(self, client, mock_user):
        """Test getting OAuth identities."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                oauth_identities = [
                    {
                        "provider": "google",
                        "provider_user_id": "google_123",
                        "linked_at": "2024-01-01T00:00:00"
                    }
                ]
                mock_service.return_value.get_user_oauth_identities.return_value = oauth_identities
                
                response = client.get(
                    "/api/v1/users/oauth-identities",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 1
                assert data["data"][0]["provider"] == "google"
    
    def test_get_activity_log_success(self, client, mock_user):
        """Test getting user activity log."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.get_user_activity_log.return_value = []
                
                response = client.get(
                    "/api/v1/users/activity-log?limit=10&offset=0",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"] == []
    
    def test_get_activity_log_invalid_params(self, client, mock_user):
        """Test activity log with invalid parameters."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.get_user_activity_log.return_value = []
                
                # Test with limit > 100 (should be capped to 100)
                response = client.get(
                    "/api/v1/users/activity-log?limit=200",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                # Verify service was called with capped limit
                mock_service.return_value.get_user_activity_log.assert_called_with(
                    mock_user.id, limit=100, offset=0
                )
    
    def test_export_user_data_success(self, client, mock_user):
        """Test user data export."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                export_data = {
                    "user_info": {"email": mock_user.email},
                    "profile": {"display_name": "Test User"},
                    "oauth_identities": [],
                    "export_date": "2024-01-01T00:00:00"
                }
                mock_service.return_value.export_user_data = AsyncMock(return_value=export_data)
                
                response = client.get(
                    "/api/v1/users/export-data",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["user_info"]["email"] == mock_user.email
    
    def test_delete_account_success(self, client, mock_user):
        """Test successful account deletion."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.delete_user_account = AsyncMock(return_value=True)
                
                response = client.delete(
                    "/api/v1/users/account",
                    json={
                        "password": "current_password",
                        "confirmation": "DELETE"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "deleted successfully" in data["message"]
    
    def test_delete_account_wrong_confirmation(self, client, mock_user):
        """Test account deletion with wrong confirmation."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.delete_user_account = AsyncMock(
                    side_effect=ValueError("Confirmation string must be 'DELETE'")
                )
                
                response = client.delete(
                    "/api/v1/users/account",
                    json={
                        "password": "current_password",
                        "confirmation": "WRONG"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "Confirmation string must be 'DELETE'" in data["detail"]
    
    def test_get_user_preferences_success(self, client, mock_user):
        """Test getting user preferences."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            response = client.get(
                "/api/v1/users/preferences",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "notification_preferences" in data["data"]
            assert "ui_preferences" in data["data"]
            assert "privacy_preferences" in data["data"]
    
    def test_update_user_preferences_success(self, client, mock_user):
        """Test updating user preferences."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('app.api.v1.users.UserService') as mock_service:
                mock_service.return_value.update_user_profile = AsyncMock(return_value=mock_user.profile)
                
                response = client.put(
                    "/api/v1/users/preferences",
                    json={
                        "notification_preferences": {
                            "email_notifications": True,
                            "push_notifications": False
                        }
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "updated successfully" in data["message"]
    
    def test_get_user_subscription_success(self, client, mock_user):
        """Test getting user subscription information."""
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            response = client.get(
                "/api/v1/users/subscription",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["plan"] == "free"
            assert "usage" in data["data"]
            assert "limits" in data["data"]
    
    def test_endpoints_require_authentication(self, client):
        """Test that all user endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/users/profile"),
            ("PUT", "/api/v1/users/profile"),
            ("POST", "/api/v1/users/change-password"),
            ("POST", "/api/v1/users/set-password"),
            ("POST", "/api/v1/users/change-email"),
            ("GET", "/api/v1/users/oauth-identities"),
            ("GET", "/api/v1/users/activity-log"),
            ("GET", "/api/v1/users/export-data"),
            ("DELETE", "/api/v1/users/account"),
            ("GET", "/api/v1/users/preferences"),
            ("PUT", "/api/v1/users/preferences"),
            ("GET", "/api/v1/users/subscription")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint, json={})
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"