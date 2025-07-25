"""
Unit tests for user service.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.user import User, UserProfile, UserOAuthIdentity
from app.schemas.user import UserProfileUpdate, PasswordChange, EmailChange, AccountDeletion
from app.services.user_service import (
    UserService,
    UserServiceError,
    UserNotFoundError,
    InvalidPasswordError,
    WeakPasswordError,
    EmailAlreadyExistsError
)
from app.services.email_service import EmailService


class TestUserService:
    """Test user service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        email_service = Mock(spec=EmailService)
        email_service.send_subscription_notification = AsyncMock(return_value=True)
        return email_service
    
    @pytest.fixture
    def user_service(self, mock_db, mock_email_service):
        """Create user service with mocked dependencies."""
        return UserService(mock_db, mock_email_service)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
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
    
    def test_get_user_profile_success(self, user_service, mock_db, sample_user):
        """Test successful user profile retrieval."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        result = user_service.get_user_profile(sample_user.id)
        
        assert result.email == sample_user.email
        assert result.profile.display_name == "Test User"
        mock_db.query.assert_called_once()
    
    def test_get_user_profile_not_found(self, user_service, mock_db):
        """Test user profile retrieval with non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(UserNotFoundError):
            user_service.get_user_profile(uuid4())
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_db, sample_user):
        """Test successful user profile update."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        profile_data = UserProfileUpdate(
            display_name="Updated Name",
            timezone="America/New_York"
        )
        
        result = await user_service.update_user_profile(sample_user.id, profile_data)
        
        assert sample_user.profile.display_name == "Updated Name"
        assert sample_user.profile.timezone == "America/New_York"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_profile_create_new(self, user_service, mock_db):
        """Test user profile update creating new profile."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        user.profile = None  # No existing profile
        
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        profile_data = UserProfileUpdate(display_name="New User")
        
        result = await user_service.update_user_profile(user.id, profile_data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_db, sample_user, mock_email_service):
        """Test successful password change."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.commit = Mock()
        
        with patch('app.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            with patch('app.services.user_service.get_password_hash') as mock_hash:
                mock_hash.return_value = "new_hashed_password"
                
                result = await user_service.change_password(
                    sample_user.id,
                    "current_password",
                    "NewStrongPass123!"
                )
                
                assert result is True
                assert sample_user.password_hash == "new_hashed_password"
                mock_db.commit.assert_called_once()
                mock_email_service.send_subscription_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_password_invalid_current(self, user_service, mock_db, sample_user):
        """Test password change with invalid current password."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('app.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = False
            
            with pytest.raises(InvalidPasswordError):
                await user_service.change_password(
                    sample_user.id,
                    "wrong_password",
                    "NewStrongPass123!"
                )
    
    @pytest.mark.asyncio
    async def test_change_password_weak_new_password(self, user_service, mock_db, sample_user):
        """Test password change with weak new password."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('app.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            with pytest.raises(WeakPasswordError) as exc_info:
                await user_service.change_password(
                    sample_user.id,
                    "current_password",
                    "weak"
                )
            
            assert len(exc_info.value.errors) > 0
    
    @pytest.mark.asyncio
    async def test_set_password_success(self, user_service, mock_db, mock_email_service):
        """Test successful password setting for OAuth user."""
        oauth_user = User(
            id=uuid4(),
            email="oauth@example.com",
            password_hash=None,  # OAuth user without password
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        oauth_user.profile = UserProfile(
            user_id=oauth_user.id,
            display_name="OAuth User",
            timezone="Asia/Tokyo",
            notification_preferences={}
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = oauth_user
        mock_db.commit = Mock()
        
        with patch('app.services.user_service.get_password_hash') as mock_hash:
            mock_hash.return_value = "new_hashed_password"
            
            result = await user_service.set_password(oauth_user.id, "NewStrongPass123!")
            
            assert result is True
            assert oauth_user.password_hash == "new_hashed_password"
            mock_db.commit.assert_called_once()
            mock_email_service.send_subscription_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_email_success(self, user_service, mock_db, sample_user, mock_email_service):
        """Test successful email change."""
        mock_db.query.return_value.filter.side_effect = [
            Mock(first=Mock(return_value=sample_user)),  # Find user
            Mock(first=Mock(return_value=None))  # Check email doesn't exist
        ]
        mock_db.commit = Mock()
        
        with patch('app.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            with patch('app.services.auth_service.AuthService') as mock_auth_service:
                mock_auth_service.return_value._send_verification_email = AsyncMock()
                
                result = await user_service.change_email(
                    sample_user.id,
                    "newemail@example.com",
                    "password"
                )
                
                assert result is True
                assert sample_user.email == "newemail@example.com"
                assert sample_user.email_verified_at is None
                mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_email_already_exists(self, user_service, mock_db, sample_user):
        """Test email change with existing email."""
        existing_user = User(id=uuid4(), email="existing@example.com")
        
        mock_db.query.return_value.filter.side_effect = [
            Mock(first=Mock(return_value=sample_user)),  # Find user
            Mock(first=Mock(return_value=existing_user))  # Email already exists
        ]
        
        with pytest.raises(EmailAlreadyExistsError):
            await user_service.change_email(
                sample_user.id,
                "existing@example.com",
                "password"
            )
    
    def test_get_user_oauth_identities_success(self, user_service, mock_db, sample_user):
        """Test getting user OAuth identities."""
        oauth_identities = [
            UserOAuthIdentity(
                provider="google",
                provider_user_id="google_123",
                user_id=sample_user.id,
                created_at=datetime.utcnow()
            ),
            UserOAuthIdentity(
                provider="line",
                provider_user_id="line_456",
                user_id=sample_user.id,
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db.query.return_value.filter.side_effect = [
            Mock(first=Mock(return_value=sample_user)),  # Find user
            Mock(all=Mock(return_value=oauth_identities))  # Get OAuth identities
        ]
        
        result = user_service.get_user_oauth_identities(sample_user.id)
        
        assert len(result) == 2
        assert result[0]["provider"] == "google"
        assert result[1]["provider"] == "line"
    
    @pytest.mark.asyncio
    async def test_delete_user_account_success(self, user_service, mock_db, sample_user, mock_email_service):
        """Test successful user account deletion."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.delete = Mock()
        mock_db.commit = Mock()
        
        with patch('app.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            result = await user_service.delete_user_account(
                sample_user.id,
                "password",
                "DELETE"
            )
            
            assert result is True
            mock_db.delete.assert_called_once_with(sample_user)
            mock_db.commit.assert_called_once()
            mock_email_service.send_subscription_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_account_wrong_confirmation(self, user_service, mock_db, sample_user):
        """Test user account deletion with wrong confirmation."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with pytest.raises(ValueError):
            await user_service.delete_user_account(
                sample_user.id,
                "password",
                "WRONG"
            )
    
    @pytest.mark.asyncio
    async def test_export_user_data_success(self, user_service, mock_db, sample_user):
        """Test successful user data export."""
        oauth_identities = [
            UserOAuthIdentity(
                provider="google",
                provider_user_id="google_123",
                user_id=sample_user.id,
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db.query.return_value.filter.side_effect = [
            Mock(first=Mock(return_value=sample_user)),  # Find user
            Mock(all=Mock(return_value=oauth_identities))  # Get OAuth identities
        ]
        
        result = await user_service.export_user_data(sample_user.id)
        
        assert "user_info" in result
        assert "profile" in result
        assert "oauth_identities" in result
        assert "export_date" in result
        assert result["user_info"]["email"] == sample_user.email
        assert len(result["oauth_identities"]) == 1
    
    def test_get_user_activity_log_success(self, user_service, mock_db, sample_user):
        """Test getting user activity log."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        result = user_service.get_user_activity_log(sample_user.id)
        
        # Currently returns empty list as activity logging is not implemented
        assert result == []
    
    def test_get_user_activity_log_not_found(self, user_service, mock_db):
        """Test getting activity log for non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(UserNotFoundError):
            user_service.get_user_activity_log(uuid4())