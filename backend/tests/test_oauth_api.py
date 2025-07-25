"""
Integration tests for OAuth API endpoints.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserProfile, UserOAuthIdentity


class TestOAuthAPI:
    """Test OAuth API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service."""
        with patch('app.api.v1.oauth.OAuthService') as mock_service:
            yield mock_service
    
    def test_oauth_providers_endpoint(self, client):
        """Test getting OAuth providers."""
        with patch('app.api.v1.oauth.settings') as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test_google_client"
            mock_settings.LINE_CLIENT_ID = "test_line_client"
            
            response = client.get("/api/v1/oauth/providers")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "google" in data["data"]["supported_providers"]
            assert "line" in data["data"]["supported_providers"]
            assert "providers" in data["data"]
    
    def test_oauth_authorize_google(self, client, mock_oauth_service):
        """Test OAuth authorization initiation for Google."""
        mock_oauth_service.return_value.get_authorization_url.return_value = "https://accounts.google.com/oauth/authorize?..."
        
        response = client.get("/api/v1/oauth/authorize/google")
        
        assert response.status_code == 302
        assert "accounts.google.com" in response.headers["location"]
    
    def test_oauth_authorize_line(self, client, mock_oauth_service):
        """Test OAuth authorization initiation for LINE."""
        mock_oauth_service.return_value.get_authorization_url.return_value = "https://access.line.me/oauth2/authorize?..."
        
        response = client.get("/api/v1/oauth/authorize/line")
        
        assert response.status_code == 302
        assert "access.line.me" in response.headers["location"]
    
    def test_oauth_authorize_invalid_provider(self, client):
        """Test OAuth authorization with invalid provider."""
        response = client.get("/api/v1/oauth/authorize/invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported OAuth provider" in data["detail"]
    
    def test_oauth_callback_success(self, client, mock_oauth_service):
        """Test successful OAuth callback."""
        # Mock OAuth service methods
        mock_oauth_service.return_value.exchange_code_for_token.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token"
        }
        
        # Mock auth service
        with patch('app.api.v1.oauth.AuthService') as mock_auth_service:
            mock_auth_response = Mock()
            mock_auth_response.user.id = str(uuid4())
            mock_auth_response.tokens.access_token = "jwt_access_token"
            mock_auth_response.tokens.refresh_token = "jwt_refresh_token"
            
            mock_auth_service.return_value.oauth_authenticate = AsyncMock(return_value=mock_auth_response)
            
            response = client.get(
                "/api/v1/oauth/callback/google",
                params={
                    "code": "test_auth_code",
                    "state": "test_state"
                }
            )
            
            assert response.status_code == 302
            assert "auth/success" in response.headers["location"]
            assert "access_token=" in response.headers["location"]
    
    def test_oauth_callback_error(self, client):
        """Test OAuth callback with error."""
        response = client.get(
            "/api/v1/oauth/callback/google",
            params={
                "error": "access_denied",
                "error_description": "User denied access"
            }
        )
        
        assert response.status_code == 302
        assert "auth/error" in response.headers["location"]
        assert "error=access_denied" in response.headers["location"]
    
    def test_oauth_callback_missing_code(self, client):
        """Test OAuth callback without authorization code."""
        response = client.get(
            "/api/v1/oauth/callback/google",
            params={"state": "test_state"}
        )
        
        assert response.status_code == 302
        assert "auth/error" in response.headers["location"]
        assert "error=missing_code" in response.headers["location"]
    
    def test_oauth_callback_missing_state(self, client):
        """Test OAuth callback without state parameter."""
        response = client.get(
            "/api/v1/oauth/callback/google",
            params={"code": "test_code"}
        )
        
        assert response.status_code == 302
        assert "auth/error" in response.headers["location"]
        assert "error=missing_state" in response.headers["location"]
    
    def test_link_oauth_account_success(self, client):
        """Test linking OAuth account to existing user."""
        # Mock authenticated user
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z"
            )
            mock_get_user.return_value = mock_user
            
            # Mock OAuth service
            with patch('app.api.v1.oauth.OAuthService') as mock_oauth_service:
                mock_oauth_service.return_value.verify_token.return_value = {
                    "id": "google_123",
                    "email": "test@example.com",
                    "name": "Test User"
                }
                
                # Mock database
                with patch('app.core.database.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing identity
                    mock_db.add = Mock()
                    mock_db.commit = Mock()
                    mock_get_db.return_value = mock_db
                    
                    response = client.post(
                        "/api/v1/oauth/link/google",
                        json={
                            "provider": "google",
                            "access_token": "test_token"
                        },
                        headers={"Authorization": "Bearer test_jwt_token"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "linked successfully" in data["message"]
    
    def test_link_oauth_account_already_linked(self, client):
        """Test linking OAuth account that's already linked to same user."""
        # Mock authenticated user
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z"
            )
            mock_get_user.return_value = mock_user
            
            # Mock OAuth service
            with patch('app.api.v1.oauth.OAuthService') as mock_oauth_service:
                mock_oauth_service.return_value.verify_token.return_value = {
                    "id": "google_123",
                    "email": "test@example.com",
                    "name": "Test User"
                }
                
                # Mock database with existing identity
                with patch('app.core.database.get_db') as mock_get_db:
                    mock_db = Mock()
                    existing_identity = UserOAuthIdentity(
                        provider="google",
                        provider_user_id="google_123",
                        user_id=mock_user.id
                    )
                    mock_db.query.return_value.filter.return_value.first.return_value = existing_identity
                    mock_get_db.return_value = mock_db
                    
                    response = client.post(
                        "/api/v1/oauth/link/google",
                        json={
                            "provider": "google",
                            "access_token": "test_token"
                        },
                        headers={"Authorization": "Bearer test_jwt_token"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "already linked" in data["message"]
    
    def test_link_oauth_account_linked_to_other_user(self, client):
        """Test linking OAuth account that's already linked to another user."""
        # Mock authenticated user
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z"
            )
            mock_get_user.return_value = mock_user
            
            # Mock OAuth service
            with patch('app.api.v1.oauth.OAuthService') as mock_oauth_service:
                mock_oauth_service.return_value.verify_token.return_value = {
                    "id": "google_123",
                    "email": "test@example.com",
                    "name": "Test User"
                }
                
                # Mock database with identity linked to different user
                with patch('app.core.database.get_db') as mock_get_db:
                    mock_db = Mock()
                    existing_identity = UserOAuthIdentity(
                        provider="google",
                        provider_user_id="google_123",
                        user_id=uuid4()  # Different user ID
                    )
                    mock_db.query.return_value.filter.return_value.first.return_value = existing_identity
                    mock_get_db.return_value = mock_db
                    
                    response = client.post(
                        "/api/v1/oauth/link/google",
                        json={
                            "provider": "google",
                            "access_token": "test_token"
                        },
                        headers={"Authorization": "Bearer test_jwt_token"}
                    )
                    
                    assert response.status_code == 409
                    data = response.json()
                    assert "already linked to another user" in data["detail"]
    
    def test_unlink_oauth_account_success(self, client):
        """Test unlinking OAuth account."""
        # Mock authenticated user with password
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z",
                password_hash="hashed_password"  # User has password
            )
            mock_get_user.return_value = mock_user
            
            # Mock database
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = Mock()
                oauth_identity = UserOAuthIdentity(
                    provider="google",
                    provider_user_id="google_123",
                    user_id=mock_user.id
                )
                mock_db.query.return_value.filter.return_value.first.return_value = oauth_identity
                mock_db.delete = Mock()
                mock_db.commit = Mock()
                mock_get_db.return_value = mock_db
                
                response = client.delete(
                    "/api/v1/oauth/unlink/google",
                    headers={"Authorization": "Bearer test_jwt_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "unlinked successfully" in data["message"]
    
    def test_unlink_oauth_account_not_found(self, client):
        """Test unlinking OAuth account that doesn't exist."""
        # Mock authenticated user
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z"
            )
            mock_get_user.return_value = mock_user
            
            # Mock database with no OAuth identity
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.query.return_value.filter.return_value.first.return_value = None
                mock_get_db.return_value = mock_db
                
                response = client.delete(
                    "/api/v1/oauth/unlink/google",
                    headers={"Authorization": "Bearer test_jwt_token"}
                )
                
                assert response.status_code == 404
                data = response.json()
                assert "No google account linked" in data["detail"]
    
    def test_unlink_oauth_account_only_auth_method(self, client):
        """Test unlinking OAuth account when it's the only auth method."""
        # Mock authenticated user without password
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z",
                password_hash=None  # No password
            )
            mock_get_user.return_value = mock_user
            
            # Mock database
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = Mock()
                oauth_identity = UserOAuthIdentity(
                    provider="google",
                    provider_user_id="google_123",
                    user_id=mock_user.id
                )
                mock_db.query.return_value.filter.return_value.first.return_value = oauth_identity
                mock_db.query.return_value.filter.return_value.count.return_value = 0  # No other identities
                mock_get_db.return_value = mock_db
                
                response = client.delete(
                    "/api/v1/oauth/unlink/google",
                    headers={"Authorization": "Bearer test_jwt_token"}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "only authentication method" in data["detail"]
    
    def test_get_linked_oauth_accounts(self, client):
        """Test getting linked OAuth accounts."""
        # Mock authenticated user
        with patch('app.core.deps.get_current_active_user') as mock_get_user:
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                email_verified_at="2024-01-01T00:00:00Z"
            )
            mock_get_user.return_value = mock_user
            
            # Mock database with OAuth identities
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = Mock()
                oauth_identities = [
                    UserOAuthIdentity(
                        provider="google",
                        provider_user_id="google_123",
                        user_id=mock_user.id,
                        created_at="2024-01-01T00:00:00Z"
                    ),
                    UserOAuthIdentity(
                        provider="line",
                        provider_user_id="line_456",
                        user_id=mock_user.id,
                        created_at="2024-01-02T00:00:00Z"
                    )
                ]
                mock_db.query.return_value.filter.return_value.all.return_value = oauth_identities
                mock_get_db.return_value = mock_db
                
                response = client.get(
                    "/api/v1/oauth/linked",
                    headers={"Authorization": "Bearer test_jwt_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2
                assert data["data"][0]["provider"] == "google"
                assert data["data"][1]["provider"] == "line"
    
    def test_oauth_endpoints_require_authentication(self, client):
        """Test that OAuth management endpoints require authentication."""
        # Test link endpoint
        response = client.post(
            "/api/v1/oauth/link/google",
            json={"provider": "google", "access_token": "test_token"}
        )
        assert response.status_code == 401
        
        # Test unlink endpoint
        response = client.delete("/api/v1/oauth/unlink/google")
        assert response.status_code == 401
        
        # Test linked accounts endpoint
        response = client.get("/api/v1/oauth/linked")
        assert response.status_code == 401