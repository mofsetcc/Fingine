"""
Unit tests for authentication system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    validate_password_strength,
    create_email_verification_token,
    verify_email_verification_token,
    create_password_reset_token,
    verify_password_reset_token
)
from app.models.user import User, UserProfile, UserOAuthIdentity
from app.schemas.user import (
    UserRegistration,
    UserLogin,
    PasswordReset,
    PasswordResetConfirm,
    OAuthLogin
)
from app.services.auth_service import (
    AuthService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    EmailNotVerifiedError,
    UserNotFoundError,
    InvalidTokenError,
    WeakPasswordError
)
from app.services.email_service import EmailService


class TestSecurity:
    """Test security utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)
    
    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        user_id = str(uuid4())
        
        # Test access token
        access_token = create_access_token(user_id)
        verified_user_id = verify_token(access_token, "access")
        assert verified_user_id == user_id
        
        # Test refresh token
        refresh_token = create_refresh_token(user_id)
        verified_user_id = verify_token(refresh_token, "refresh")
        assert verified_user_id == user_id
        
        # Test wrong token type
        assert verify_token(access_token, "refresh") is None
        assert verify_token(refresh_token, "access") is None
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        # Valid password
        is_valid, errors = validate_password_strength("StrongPass123!")
        assert is_valid
        assert len(errors) == 0
        
        # Too short
        is_valid, errors = validate_password_strength("Short1!")
        assert not is_valid
        assert "at least 8 characters" in " ".join(errors)
        
        # No uppercase
        is_valid, errors = validate_password_strength("lowercase123!")
        assert not is_valid
        assert "uppercase letter" in " ".join(errors)
        
        # No lowercase
        is_valid, errors = validate_password_strength("UPPERCASE123!")
        assert not is_valid
        assert "lowercase letter" in " ".join(errors)
        
        # No digit
        is_valid, errors = validate_password_strength("NoDigits!")
        assert not is_valid
        assert "digit" in " ".join(errors)
        
        # No special character
        is_valid, errors = validate_password_strength("NoSpecial123")
        assert not is_valid
        assert "special character" in " ".join(errors)
    
    def test_email_verification_token(self):
        """Test email verification token creation and verification."""
        email = "test@example.com"
        
        token = create_email_verification_token(email)
        verified_email = verify_email_verification_token(token)
        
        assert verified_email == email
        assert verify_email_verification_token("invalid_token") is None
    
    def test_password_reset_token(self):
        """Test password reset token creation and verification."""
        email = "test@example.com"
        
        token = create_password_reset_token(email)
        verified_email = verify_password_reset_token(token)
        
        assert verified_email == email
        assert verify_password_reset_token("invalid_token") is None


class TestAuthService:
    """Test authentication service."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        email_service = Mock(spec=EmailService)
        email_service.send_verification_email = AsyncMock(return_value=True)
        email_service.send_password_reset_email = AsyncMock(return_value=True)
        return email_service
    
    @pytest.fixture
    def auth_service(self, mock_db, mock_email_service):
        """Create auth service with mocked dependencies."""
        return AuthService(mock_db, mock_email_service)
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_db, mock_email_service):
        """Test successful user registration."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing user
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        
        user_data = UserRegistration(
            email="test@example.com",
            password="StrongPass123!",
            display_name="Test User"
        )
        
        with patch('app.services.auth_service.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid4()
            user = await auth_service.register_user(user_data)
        
        assert user.email == "test@example.com"
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        mock_email_service.send_verification_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, auth_service, mock_db):
        """Test registration with existing email."""
        # Mock existing user
        existing_user = User(email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        user_data = UserRegistration(
            email="test@example.com",
            password="StrongPass123!"
        )
        
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register_user(user_data)
    
    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, auth_service, mock_db):
        """Test registration with weak password."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        user_data = UserRegistration(
            email="test@example.com",
            password="weak"
        )
        
        with pytest.raises(WeakPasswordError) as exc_info:
            await auth_service.register_user(user_data)
        
        assert len(exc_info.value.errors) > 0
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_db):
        """Test successful user authentication."""
        # Mock user with verified email
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=get_password_hash("StrongPass123!"),
            email_verified_at=datetime.utcnow()
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.commit = Mock()
        
        credentials = UserLogin(
            email="test@example.com",
            password="StrongPass123!"
        )
        
        auth_response = await auth_service.authenticate_user(credentials)
        
        assert auth_response.user.email == "test@example.com"
        assert auth_response.tokens.access_token is not None
        assert auth_response.tokens.refresh_token is not None
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_db):
        """Test authentication with non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        credentials = UserLogin(
            email="nonexistent@example.com",
            password="password"
        )
        
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(credentials)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_db):
        """Test authentication with wrong password."""
        user = User(
            email="test@example.com",
            password_hash=get_password_hash("correct_password"),
            email_verified_at=datetime.utcnow()
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        credentials = UserLogin(
            email="test@example.com",
            password="wrong_password"
        )
        
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate_user(credentials)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_email_not_verified(self, auth_service, mock_db):
        """Test authentication with unverified email."""
        user = User(
            email="test@example.com",
            password_hash=get_password_hash("StrongPass123!"),
            email_verified_at=None  # Not verified
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        credentials = UserLogin(
            email="test@example.com",
            password="StrongPass123!"
        )
        
        with pytest.raises(EmailNotVerifiedError):
            await auth_service.authenticate_user(credentials)
    
    @pytest.mark.asyncio
    async def test_verify_email_success(self, auth_service, mock_db):
        """Test successful email verification."""
        user = User(
            email="test@example.com",
            email_verified_at=None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.commit = Mock()
        
        # Create valid token
        token = create_email_verification_token("test@example.com")
        
        result = await auth_service.verify_email(token)
        
        assert result is True
        assert user.email_verified_at is not None
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_service):
        """Test email verification with invalid token."""
        with pytest.raises(InvalidTokenError):
            await auth_service.verify_email("invalid_token")
    
    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(self, auth_service, mock_db):
        """Test email verification with non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        token = create_email_verification_token("nonexistent@example.com")
        
        with pytest.raises(UserNotFoundError):
            await auth_service.verify_email(token)
    
    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, auth_service, mock_db, mock_email_service):
        """Test successful password reset request."""
        user = User(email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        reset_data = PasswordReset(email="test@example.com")
        
        result = await auth_service.request_password_reset(reset_data)
        
        assert result is True
        mock_email_service.send_password_reset_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_found(self, auth_service, mock_db, mock_email_service):
        """Test password reset request for non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        reset_data = PasswordReset(email="nonexistent@example.com")
        
        result = await auth_service.request_password_reset(reset_data)
        
        # Should still return True for security
        assert result is True
        mock_email_service.send_password_reset_email.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service, mock_db):
        """Test successful password reset."""
        user = User(
            email="test@example.com",
            password_hash=get_password_hash("old_password")
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.commit = Mock()
        
        token = create_password_reset_token("test@example.com")
        reset_data = PasswordResetConfirm(
            token=token,
            new_password="NewStrongPass123!"
        )
        
        result = await auth_service.reset_password(reset_data)
        
        assert result is True
        assert not verify_password("old_password", user.password_hash)
        assert verify_password("NewStrongPass123!", user.password_hash)
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, auth_service):
        """Test password reset with invalid token."""
        reset_data = PasswordResetConfirm(
            token="invalid_token",
            new_password="NewStrongPass123!"
        )
        
        with pytest.raises(InvalidTokenError):
            await auth_service.reset_password(reset_data)
    
    @pytest.mark.asyncio
    async def test_reset_password_weak_password(self, auth_service, mock_db):
        """Test password reset with weak password."""
        user = User(email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        token = create_password_reset_token("test@example.com")
        reset_data = PasswordResetConfirm(
            token=token,
            new_password="weak"
        )
        
        with pytest.raises(WeakPasswordError):
            await auth_service.reset_password(reset_data)
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service):
        """Test successful token refresh."""
        user = User(
            id=uuid4(),
            email="test@example.com"
        )
        
        token = await auth_service.refresh_token(user)
        
        assert token.access_token is not None
        assert token.token_type == "bearer"
        assert token.expires_in == 30 * 60  # 30 minutes
    
    @pytest.mark.asyncio
    async def test_resend_verification_email_success(self, auth_service, mock_db, mock_email_service):
        """Test successful verification email resend."""
        user = User(
            email="test@example.com",
            email_verified_at=None
        )
        user.profile = UserProfile(display_name="Test User")
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        result = await auth_service.resend_verification_email("test@example.com")
        
        assert result is True
        mock_email_service.send_verification_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resend_verification_email_already_verified(self, auth_service, mock_db, mock_email_service):
        """Test verification email resend for already verified user."""
        user = User(
            email="test@example.com",
            email_verified_at=datetime.utcnow()  # Already verified
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        result = await auth_service.resend_verification_email("test@example.com")
        
        # Should still return True for security
        assert result is True
        mock_email_service.send_verification_email.assert_not_called()


class TestEmailService:
    """Test email service."""
    
    @pytest.fixture
    def email_service(self):
        """Create email service instance."""
        return EmailService()
    
    @pytest.mark.asyncio
    async def test_send_verification_email_development(self, email_service):
        """Test sending verification email in development mode."""
        with patch('app.services.email_service.settings.ENVIRONMENT', 'development'):
            result = await email_service.send_verification_email(
                email="test@example.com",
                token="test_token",
                display_name="Test User"
            )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email_development(self, email_service):
        """Test sending password reset email in development mode."""
        with patch('app.services.email_service.settings.ENVIRONMENT', 'development'):
            result = await email_service.send_password_reset_email(
                email="test@example.com",
                token="test_token",
                display_name="Test User"
            )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_welcome_email_development(self, email_service):
        """Test sending welcome email in development mode."""
        with patch('app.services.email_service.settings.ENVIRONMENT', 'development'):
            result = await email_service.send_welcome_email(
                email="test@example.com",
                display_name="Test User"
            )
        
        assert result is True