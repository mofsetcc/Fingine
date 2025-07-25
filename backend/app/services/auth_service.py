"""
Authentication service for user registration, login, and management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    create_password_reset_token,
    verify_email_verification_token,
    verify_password_reset_token,
    validate_password_strength
)
from app.models.user import User, UserProfile, UserOAuthIdentity
from app.schemas.user import (
    UserRegistration,
    UserLogin,
    AuthResponse,
    AuthToken,
    User as UserSchema,
    UserWithProfile,
    PasswordReset,
    PasswordResetConfirm,
    OAuthLogin
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class UserAlreadyExistsError(AuthenticationError):
    """Raised when trying to register a user that already exists."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""
    pass


class EmailNotVerifiedError(AuthenticationError):
    """Raised when user tries to login with unverified email."""
    pass


class UserNotFoundError(AuthenticationError):
    """Raised when user is not found."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid or expired."""
    pass


class WeakPasswordError(AuthenticationError):
    """Raised when password doesn't meet strength requirements."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Password validation failed: {', '.join(errors)}")


class AuthService:
    """Service for handling user authentication operations."""
    
    def __init__(self, db: Session, email_service: EmailService):
        self.db = db
        self.email_service = email_service
    
    async def register_user(self, user_data: UserRegistration) -> UserSchema:
        """
        Register a new user with email verification.
        
        Args:
            user_data: User registration data
            
        Returns:
            Created user
            
        Raises:
            UserAlreadyExistsError: If user with email already exists
            WeakPasswordError: If password doesn't meet requirements
        """
        logger.info(f"Attempting to register user with email: {user_data.email}")
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Registration attempt for existing email: {user_data.email}")
            raise UserAlreadyExistsError("User with this email already exists")
        
        # Validate password strength
        is_valid, errors = validate_password_strength(user_data.password)
        if not is_valid:
            logger.warning(f"Weak password attempt for email: {user_data.email}")
            raise WeakPasswordError(errors)
        
        # Hash password
        password_hash = get_password_hash(user_data.password)
        
        # Create user
        user = User(
            id=uuid4(),
            email=user_data.email,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            self.db.add(user)
            self.db.flush()  # Flush to get the user ID
            
            # Create user profile
            profile = UserProfile(
                user_id=user.id,
                display_name=user_data.display_name,
                timezone="Asia/Tokyo",
                notification_preferences={},
                updated_at=datetime.utcnow()
            )
            
            self.db.add(profile)
            self.db.commit()
            
            logger.info(f"User registered successfully: {user.email}")
            
            # Send verification email
            await self._send_verification_email(user)
            
            return UserSchema.from_orm(user)
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during registration: {e}")
            raise UserAlreadyExistsError("User with this email already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error during registration: {e}")
            raise
    
    async def authenticate_user(self, credentials: UserLogin) -> AuthResponse:
        """
        Authenticate user and return tokens.
        
        Args:
            credentials: User login credentials
            
        Returns:
            Authentication response with user and tokens
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            EmailNotVerifiedError: If email is not verified
        """
        logger.info(f"Authentication attempt for email: {credentials.email}")
        
        # Get user by email
        user = self.db.query(User).filter(User.email == credentials.email).first()
        if not user:
            logger.warning(f"Authentication failed - user not found: {credentials.email}")
            raise InvalidCredentialsError("Invalid email or password")
        
        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            logger.warning(f"Authentication failed - invalid password: {credentials.email}")
            raise InvalidCredentialsError("Invalid email or password")
        
        # Check if email is verified
        if not user.email_verified_at:
            logger.warning(f"Authentication failed - email not verified: {credentials.email}")
            raise EmailNotVerifiedError("Please verify your email before logging in")
        
        # Update last login
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Create tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        
        tokens = AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
        
        logger.info(f"User authenticated successfully: {credentials.email}")
        
        return AuthResponse(
            user=UserSchema.from_orm(user),
            tokens=tokens,
            message="Authentication successful"
        )
    
    async def oauth_authenticate(self, oauth_data: OAuthLogin) -> AuthResponse:
        """
        Authenticate user via OAuth provider.
        
        Args:
            oauth_data: OAuth authentication data
            
        Returns:
            Authentication response with user and tokens
            
        Raises:
            InvalidCredentialsError: If OAuth token is invalid
        """
        logger.info(f"OAuth authentication attempt with provider: {oauth_data.provider}")
        
        # Verify OAuth token and get user info
        user_info = await self._verify_oauth_token(oauth_data.provider, oauth_data.access_token)
        if not user_info:
            logger.warning(f"OAuth authentication failed - invalid token: {oauth_data.provider}")
            raise InvalidCredentialsError("Invalid OAuth token")
        
        # Check if OAuth identity exists
        oauth_identity = self.db.query(UserOAuthIdentity).filter(
            UserOAuthIdentity.provider == oauth_data.provider,
            UserOAuthIdentity.provider_user_id == user_info["id"]
        ).first()
        
        if oauth_identity:
            # Existing OAuth user
            user = self.db.query(User).filter(User.id == oauth_identity.user_id).first()
            logger.info(f"Existing OAuth user authenticated: {user.email}")
        else:
            # New OAuth user - check if email exists
            user = self.db.query(User).filter(User.email == user_info["email"]).first()
            
            if user:
                # Link OAuth identity to existing user
                oauth_identity = UserOAuthIdentity(
                    provider=oauth_data.provider,
                    provider_user_id=user_info["id"],
                    user_id=user.id,
                    created_at=datetime.utcnow()
                )
                self.db.add(oauth_identity)
                logger.info(f"OAuth identity linked to existing user: {user.email}")
            else:
                # Create new user
                user = User(
                    id=uuid4(),
                    email=user_info["email"],
                    password_hash=None,  # OAuth users don't have passwords
                    email_verified_at=datetime.utcnow(),  # OAuth emails are pre-verified
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.db.add(user)
                self.db.flush()
                
                # Create user profile
                profile = UserProfile(
                    user_id=user.id,
                    display_name=user_info.get("name"),
                    avatar_url=user_info.get("picture"),
                    timezone="Asia/Tokyo",
                    notification_preferences={},
                    updated_at=datetime.utcnow()
                )
                
                self.db.add(profile)
                
                # Create OAuth identity
                oauth_identity = UserOAuthIdentity(
                    provider=oauth_data.provider,
                    provider_user_id=user_info["id"],
                    user_id=user.id,
                    created_at=datetime.utcnow()
                )
                
                self.db.add(oauth_identity)
                logger.info(f"New OAuth user created: {user.email}")
        
        self.db.commit()
        
        # Create tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        
        tokens = AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
        
        return AuthResponse(
            user=UserSchema.from_orm(user),
            tokens=tokens,
            message="OAuth authentication successful"
        )
    
    async def refresh_token(self, user: User) -> AuthToken:
        """
        Refresh access token using refresh token.
        
        Args:
            user: User from refresh token
            
        Returns:
            New access token
        """
        logger.info(f"Token refresh for user: {user.email}")
        
        # Create new access token
        access_token = create_access_token(subject=str(user.id))
        
        return AuthToken(
            access_token=access_token,
            refresh_token="",  # Don't return refresh token in refresh response
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
    
    async def verify_email(self, token: str) -> bool:
        """
        Verify user email with verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            True if verification successful
            
        Raises:
            InvalidTokenError: If token is invalid or expired
            UserNotFoundError: If user not found
        """
        logger.info("Email verification attempt")
        
        # Verify token
        email = verify_email_verification_token(token)
        if not email:
            logger.warning("Email verification failed - invalid token")
            raise InvalidTokenError("Invalid or expired verification token")
        
        # Get user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Email verification failed - user not found: {email}")
            raise UserNotFoundError("User not found")
        
        # Mark email as verified
        user.email_verified_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Email verified successfully: {email}")
        return True
    
    async def request_password_reset(self, email_data: PasswordReset) -> bool:
        """
        Request password reset for user.
        
        Args:
            email_data: Password reset request data
            
        Returns:
            True if reset email sent (always returns True for security)
        """
        logger.info(f"Password reset requested for: {email_data.email}")
        
        # Get user by email
        user = self.db.query(User).filter(User.email == email_data.email).first()
        if user:
            # Send password reset email
            await self._send_password_reset_email(user)
            logger.info(f"Password reset email sent: {email_data.email}")
        else:
            logger.warning(f"Password reset requested for non-existent user: {email_data.email}")
        
        # Always return True for security (don't reveal if email exists)
        return True
    
    async def reset_password(self, reset_data: PasswordResetConfirm) -> bool:
        """
        Reset user password with reset token.
        
        Args:
            reset_data: Password reset confirmation data
            
        Returns:
            True if password reset successful
            
        Raises:
            InvalidTokenError: If token is invalid or expired
            UserNotFoundError: If user not found
            WeakPasswordError: If new password doesn't meet requirements
        """
        logger.info("Password reset attempt")
        
        # Verify token
        email = verify_password_reset_token(reset_data.token)
        if not email:
            logger.warning("Password reset failed - invalid token")
            raise InvalidTokenError("Invalid or expired reset token")
        
        # Get user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Password reset failed - user not found: {email}")
            raise UserNotFoundError("User not found")
        
        # Validate new password strength
        is_valid, errors = validate_password_strength(reset_data.new_password)
        if not is_valid:
            logger.warning(f"Password reset failed - weak password: {email}")
            raise WeakPasswordError(errors)
        
        # Update password
        user.password_hash = get_password_hash(reset_data.new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Password reset successfully: {email}")
        return True
    
    async def resend_verification_email(self, email: str) -> bool:
        """
        Resend email verification.
        
        Args:
            email: User email address
            
        Returns:
            True if verification email sent (always returns True for security)
        """
        logger.info(f"Resend verification email requested for: {email}")
        
        # Get user by email
        user = self.db.query(User).filter(User.email == email).first()
        if user and not user.email_verified_at:
            # Send verification email
            await self._send_verification_email(user)
            logger.info(f"Verification email resent: {email}")
        else:
            logger.warning(f"Resend verification requested for verified or non-existent user: {email}")
        
        # Always return True for security
        return True
    
    async def _send_verification_email(self, user: User) -> None:
        """
        Send email verification email to user.
        
        Args:
            user: User to send verification email to
        """
        try:
            verification_token = create_email_verification_token(user.email)
            await self.email_service.send_verification_email(
                email=user.email,
                token=verification_token,
                display_name=user.profile.display_name if user.profile else None
            )
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")
    
    async def _send_password_reset_email(self, user: User) -> None:
        """
        Send password reset email to user.
        
        Args:
            user: User to send password reset email to
        """
        try:
            reset_token = create_password_reset_token(user.email)
            await self.email_service.send_password_reset_email(
                email=user.email,
                token=reset_token,
                display_name=user.profile.display_name if user.profile else None
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")
    
    async def _verify_oauth_token(self, provider: str, access_token: str) -> Optional[dict]:
        """
        Verify OAuth token and get user information.
        
        Args:
            provider: OAuth provider name
            access_token: OAuth access token
            
        Returns:
            User information dict if token is valid, None otherwise
        """
        try:
            from app.services.oauth_service import OAuthService, InvalidTokenError, ProviderError
            
            oauth_service = OAuthService()
            user_info = await oauth_service.verify_token(provider, access_token)
            
            logger.info(f"OAuth token verified successfully for {provider}")
            return user_info
            
        except InvalidTokenError:
            logger.warning(f"Invalid OAuth token for {provider}")
            return None
        except ProviderError as e:
            logger.error(f"OAuth provider error for {provider}: {e}")
            return None
        except ValueError as e:
            logger.warning(f"Unsupported OAuth provider: {provider}")
            return None
        except Exception as e:
            logger.error(f"Unexpected OAuth error for {provider}: {e}")
            return None