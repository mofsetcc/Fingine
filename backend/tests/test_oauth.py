"""
Unit tests for OAuth functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

import httpx

from app.services.oauth_service import (
    GoogleOAuthService,
    LineOAuthService,
    OAuthService,
    OAuthError,
    InvalidTokenError,
    ProviderError
)


class TestGoogleOAuthService:
    """Test Google OAuth service."""
    
    @pytest.fixture
    def google_service(self):
        """Create Google OAuth service instance."""
        with patch('app.services.oauth_service.settings') as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"
            mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"
            return GoogleOAuthService()
    
    def test_get_authorization_url(self, google_service):
        """Test Google authorization URL generation."""
        url = google_service.get_authorization_url("test_state")
        
        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=test_client_id" in url
        assert "state=test_state" in url
        assert "scope=openid+email+profile" in url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, google_service):
        """Test successful code exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await google_service.exchange_code_for_token("test_code")
            
            assert result["access_token"] == "test_access_token"
            assert result["refresh_token"] == "test_refresh_token"
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_error(self, google_service):
        """Test code exchange with error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(ProviderError):
                await google_service.exchange_code_for_token("invalid_code")
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, google_service):
        """Test successful token verification."""
        # Mock token info response
        token_info_response = Mock()
        token_info_response.status_code = 200
        token_info_response.json.return_value = {
            "audience": "test_client_id",
            "scope": "openid email profile",
            "expires_in": 3600
        }
        
        # Mock user info response
        userinfo_response = Mock()
        userinfo_response.status_code = 200
        userinfo_response.json.return_value = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg",
            "verified_email": True
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[token_info_response, userinfo_response]
            )
            
            result = await google_service.verify_token("test_access_token")
            
            assert result["id"] == "123456789"
            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"
            assert result["verified_email"] is True
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, google_service):
        """Test token verification with invalid token."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(InvalidTokenError):
                await google_service.verify_token("invalid_token")
    
    @pytest.mark.asyncio
    async def test_verify_token_wrong_audience(self, google_service):
        """Test token verification with wrong audience."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audience": "wrong_client_id",
            "scope": "openid email profile"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(InvalidTokenError):
                await google_service.verify_token("test_token")
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, google_service):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await google_service.refresh_token("test_refresh_token")
            
            assert result["access_token"] == "new_access_token"


class TestLineOAuthService:
    """Test LINE OAuth service."""
    
    @pytest.fixture
    def line_service(self):
        """Create LINE OAuth service instance."""
        with patch('app.services.oauth_service.settings') as mock_settings:
            mock_settings.LINE_CLIENT_ID = "test_line_client_id"
            mock_settings.LINE_CLIENT_SECRET = "test_line_client_secret"
            mock_settings.LINE_REDIRECT_URI = "http://localhost:8000/callback"
            return LineOAuthService()
    
    def test_get_authorization_url(self, line_service):
        """Test LINE authorization URL generation."""
        url = line_service.get_authorization_url("test_state")
        
        assert "access.line.me/oauth2/v2.1/authorize" in url
        assert "client_id=test_line_client_id" in url
        assert "state=test_state" in url
        assert "scope=profile+openid+email" in url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, line_service):
        """Test successful LINE code exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_line_access_token",
            "refresh_token": "test_line_refresh_token",
            "expires_in": 2592000,
            "token_type": "Bearer"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await line_service.exchange_code_for_token("test_code")
            
            assert result["access_token"] == "test_line_access_token"
            assert result["refresh_token"] == "test_line_refresh_token"
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, line_service):
        """Test successful LINE token verification."""
        # Mock token verification response
        verify_response = Mock()
        verify_response.status_code = 200
        verify_response.json.return_value = {
            "client_id": "test_line_client_id",
            "expires_in": 2592000,
            "scope": "profile openid email"
        }
        
        # Mock profile response
        profile_response = Mock()
        profile_response.status_code = 200
        profile_response.json.return_value = {
            "userId": "line_user_123",
            "displayName": "LINE User",
            "pictureUrl": "https://profile.line-scdn.net/photo.jpg",
            "statusMessage": "Hello LINE!"
        }
        
        # Mock email response (optional)
        email_response = Mock()
        email_response.status_code = 200
        email_response.json.return_value = {
            "email": "lineuser@example.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[verify_response, profile_response, email_response]
            )
            
            result = await line_service.verify_token("test_access_token")
            
            assert result["id"] == "line_user_123"
            assert result["name"] == "LINE User"
            assert result["email"] == "lineuser@example.com"
            assert result["picture"] == "https://profile.line-scdn.net/photo.jpg"
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, line_service):
        """Test LINE token verification with invalid token."""
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(InvalidTokenError):
                await line_service.verify_token("invalid_token")


class TestOAuthService:
    """Test main OAuth service."""
    
    @pytest.fixture
    def oauth_service(self):
        """Create OAuth service instance."""
        return OAuthService()
    
    def test_get_provider_google(self, oauth_service):
        """Test getting Google provider."""
        provider = oauth_service.get_provider("google")
        assert isinstance(provider, GoogleOAuthService)
    
    def test_get_provider_line(self, oauth_service):
        """Test getting LINE provider."""
        provider = oauth_service.get_provider("line")
        assert isinstance(provider, LineOAuthService)
    
    def test_get_provider_invalid(self, oauth_service):
        """Test getting invalid provider."""
        with pytest.raises(ValueError):
            oauth_service.get_provider("invalid_provider")
    
    def test_get_supported_providers(self, oauth_service):
        """Test getting supported providers list."""
        providers = oauth_service.get_supported_providers()
        assert "google" in providers
        assert "line" in providers
        assert len(providers) == 2
    
    def test_get_authorization_url(self, oauth_service):
        """Test getting authorization URL through main service."""
        with patch.object(oauth_service.google, 'get_authorization_url') as mock_method:
            mock_method.return_value = "https://test.url"
            
            url = oauth_service.get_authorization_url("google", "test_state")
            
            assert url == "https://test.url"
            mock_method.assert_called_once_with("test_state")
    
    @pytest.mark.asyncio
    async def test_verify_token(self, oauth_service):
        """Test token verification through main service."""
        with patch.object(oauth_service.google, 'verify_token') as mock_method:
            mock_method.return_value = {"id": "123", "email": "test@example.com"}
            
            result = await oauth_service.verify_token("google", "test_token")
            
            assert result["id"] == "123"
            assert result["email"] == "test@example.com"
            mock_method.assert_called_once_with("test_token")


class TestOAuthIntegration:
    """Test OAuth integration with authentication service."""
    
    @pytest.mark.asyncio
    async def test_oauth_authentication_new_user(self):
        """Test OAuth authentication creating new user."""
        from app.services.auth_service import AuthService
        from app.schemas.user import OAuthLogin
        
        # Mock dependencies
        mock_db = Mock()
        mock_email_service = Mock()
        
        # Mock OAuth service
        with patch('app.services.auth_service.OAuthService') as mock_oauth_service:
            mock_oauth_service.return_value.verify_token.return_value = {
                "id": "google_123",
                "email": "newuser@example.com",
                "name": "New User",
                "picture": "https://example.com/photo.jpg"
            }
            
            # Mock database queries
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                None,  # No existing OAuth identity
                None   # No existing user with email
            ]
            mock_db.flush = Mock()
            mock_db.commit = Mock()
            
            auth_service = AuthService(mock_db, mock_email_service)
            
            oauth_login = OAuthLogin(
                provider="google",
                access_token="test_token"
            )
            
            with patch('app.services.auth_service.uuid4') as mock_uuid:
                mock_uuid.return_value = uuid4()
                
                result = await auth_service.oauth_authenticate(oauth_login)
                
                assert result.user.email == "newuser@example.com"
                assert result.tokens.access_token is not None
                mock_db.add.assert_called()
                mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_oauth_authentication_existing_user(self):
        """Test OAuth authentication with existing user."""
        from app.services.auth_service import AuthService
        from app.schemas.user import OAuthLogin
        from app.models.user import User, UserOAuthIdentity
        
        # Mock dependencies
        mock_db = Mock()
        mock_email_service = Mock()
        
        # Create mock existing user
        existing_user = User(
            id=uuid4(),
            email="existing@example.com",
            email_verified_at="2024-01-01T00:00:00Z"
        )
        
        # Create mock OAuth identity
        oauth_identity = UserOAuthIdentity(
            provider="google",
            provider_user_id="google_123",
            user_id=existing_user.id
        )
        
        # Mock OAuth service
        with patch('app.services.auth_service.OAuthService') as mock_oauth_service:
            mock_oauth_service.return_value.verify_token.return_value = {
                "id": "google_123",
                "email": "existing@example.com",
                "name": "Existing User"
            }
            
            # Mock database queries
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                oauth_identity,  # Existing OAuth identity
                existing_user    # Existing user
            ]
            mock_db.commit = Mock()
            
            auth_service = AuthService(mock_db, mock_email_service)
            
            oauth_login = OAuthLogin(
                provider="google",
                access_token="test_token"
            )
            
            result = await auth_service.oauth_authenticate(oauth_login)
            
            assert result.user.email == "existing@example.com"
            assert result.tokens.access_token is not None
            mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_oauth_authentication_invalid_token(self):
        """Test OAuth authentication with invalid token."""
        from app.services.auth_service import AuthService, InvalidCredentialsError
        from app.schemas.user import OAuthLogin
        
        # Mock dependencies
        mock_db = Mock()
        mock_email_service = Mock()
        
        # Mock OAuth service to return None (invalid token)
        with patch('app.services.auth_service.OAuthService') as mock_oauth_service:
            mock_oauth_service.return_value.verify_token.return_value = None
            
            auth_service = AuthService(mock_db, mock_email_service)
            
            oauth_login = OAuthLogin(
                provider="google",
                access_token="invalid_token"
            )
            
            with pytest.raises(InvalidCredentialsError):
                await auth_service.oauth_authenticate(oauth_login)