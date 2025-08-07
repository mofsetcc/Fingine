"""
User-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


# User Registration and Authentication Schemas
class UserRegistration(BaseModel):
    """User registration request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    display_name: Optional[str] = Field(None, max_length=50, description="Display name")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginCredentials(BaseModel):
    """User login request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class PasswordReset(BaseModel):
    """Password reset request schema."""
    
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class OAuthLogin(BaseModel):
    """OAuth login request schema."""
    
    provider: str = Field(..., description="OAuth provider (google, line)")
    code: str = Field(..., description="OAuth authorization code")
    redirect_uri: Optional[str] = Field(None, description="OAuth redirect URI")


# Token Schemas
class Token(BaseModel):
    """JWT token response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    
    refresh_token: str = Field(..., description="JWT refresh token")


# User Data Schemas
class UserBase(BaseModel):
    """Base user schema."""
    
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """User creation schema."""
    
    password_hash: str = Field(..., description="Hashed password")
    email_verified_at: Optional[datetime] = Field(None, description="Email verification timestamp")


class UserUpdate(BaseModel):
    """User update schema."""
    
    email: Optional[EmailStr] = Field(None, description="User email address")
    password_hash: Optional[str] = Field(None, description="Hashed password")
    email_verified_at: Optional[datetime] = Field(None, description="Email verification timestamp")


class User(UserBase, UUIDSchema, TimestampSchema):
    """User response schema."""
    
    email_verified_at: Optional[datetime] = Field(None, description="Email verification timestamp")
    
    model_config = {"from_attributes": True}


# User Profile Schemas
class UserProfileBase(BaseModel):
    """Base user profile schema."""
    
    display_name: Optional[str] = Field(None, max_length=50, description="Display name")
    avatar_url: Optional[str] = Field(None, max_length=255, description="Avatar image URL")
    timezone: str = Field(default="Asia/Tokyo", max_length=50, description="User timezone")
    notification_preferences: Dict[str, Any] = Field(default_factory=dict, description="Notification preferences")


class UserProfileCreate(UserProfileBase):
    """User profile creation schema."""
    
    user_id: UUID = Field(..., description="User ID")


class UserProfileUpdate(BaseModel):
    """User profile update schema."""
    
    display_name: Optional[str] = Field(None, max_length=50, description="Display name")
    avatar_url: Optional[str] = Field(None, max_length=255, description="Avatar image URL")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")


class UserProfile(UserProfileBase, TimestampSchema):
    """User profile response schema."""
    
    user_id: UUID = Field(..., description="User ID")
    
    model_config = {"from_attributes": True}


# OAuth Identity Schemas
class UserOAuthIdentityBase(BaseModel):
    """Base OAuth identity schema."""
    
    provider: str = Field(..., max_length=50, description="OAuth provider")
    provider_user_id: str = Field(..., max_length=255, description="Provider user ID")


class UserOAuthIdentityCreate(UserOAuthIdentityBase):
    """OAuth identity creation schema."""
    
    user_id: UUID = Field(..., description="User ID")


class UserOAuthIdentity(UserOAuthIdentityBase, TimestampSchema):
    """OAuth identity response schema."""
    
    user_id: UUID = Field(..., description="User ID")
    
    model_config = {"from_attributes": True}


# Combined User Response Schemas
class UserWithProfile(User):
    """User with profile information."""
    
    profile: Optional[UserProfile] = Field(None, description="User profile")
    oauth_identities: list[UserOAuthIdentity] = Field(default_factory=list, description="OAuth identities")


class UserSummary(BaseModel):
    """User summary for public display."""
    
    id: UUID = Field(..., description="User ID")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    created_at: datetime = Field(..., description="Account creation timestamp")


# Email Verification Schemas
class EmailVerification(BaseModel):
    """Email verification request schema."""
    
    token: str = Field(..., description="Email verification token")


class ResendVerification(BaseModel):
    """Resend verification email schema."""
    
    email: EmailStr = Field(..., description="User email address")


# Additional User Management Schemas
class PasswordChange(BaseModel):
    """Password change request schema."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordSet(BaseModel):
    """Password set request schema for OAuth users."""
    
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class EmailChange(BaseModel):
    """Email change request schema."""
    
    new_email: EmailStr = Field(..., description="New email address")
    password: Optional[str] = Field(None, description="Current password (if user has one)")


class AccountDeletion(BaseModel):
    """Account deletion request schema."""
    
    password: Optional[str] = Field(None, description="Current password (if user has one)")
    confirmation: str = Field(..., description="Confirmation string (must be 'DELETE')")


class UserPreferencesUpdate(BaseModel):
    """User preferences update schema."""
    
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")
    ui_preferences: Optional[Dict[str, Any]] = Field(None, description="UI preferences")
    privacy_preferences: Optional[Dict[str, Any]] = Field(None, description="Privacy preferences")


class UserActivityLog(BaseModel):
    """User activity log entry schema."""
    
    id: UUID
    activity_type: str
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class UserDataExport(BaseModel):
    """User data export schema."""
    
    user_info: Dict[str, Any]
    profile: Dict[str, Any]
    oauth_identities: List[Dict[str, Any]]
    export_date: str


# Authentication Response Schemas
class AuthToken(BaseModel):
    """Authentication token response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class AuthResponse(BaseModel):
    """Authentication response schema."""
    
    user: User
    tokens: AuthToken
    message: str = Field("Authentication successful", description="Response message")


# User Login Schema (fixing the name)
class UserLogin(BaseModel):
    """User login request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Remember login session")


# GDPR Compliance Schemas
class GDPRConsentRequest(BaseModel):
    """GDPR consent request schema."""
    
    purpose: str = Field(..., description="Purpose of data processing")
    consent_given: bool = Field(..., description="Whether consent is given")
    consent_text: str = Field(..., description="Text of consent agreement")


class GDPRDataRequest(BaseModel):
    """GDPR data request schema."""
    
    keep_legal_basis: bool = Field(True, description="Keep data required for legal compliance")
    confirmation: bool = Field(..., description="Confirmation that user understands consequences")


class GDPRConsentStatus(BaseModel):
    """GDPR consent status schema."""
    
    purpose: str = Field(..., description="Purpose of data processing")
    status: str = Field(..., description="Consent status")
    granted_at: Optional[datetime] = Field(None, description="When consent was granted")
    withdrawn_at: Optional[datetime] = Field(None, description="When consent was withdrawn")


class GDPRDataExport(BaseModel):
    """GDPR data export schema."""
    
    personal_information: Dict[str, Any] = Field(..., description="Personal information")
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    consent_records: Dict[str, Any] = Field(..., description="Consent records")
    subscription_data: Dict[str, Any] = Field(..., description="Subscription data")
    usage_data: List[Dict[str, Any]] = Field(..., description="Usage data")
    watchlist_data: List[Dict[str, Any]] = Field(..., description="Watchlist data")
    analysis_history: List[Dict[str, Any]] = Field(..., description="Analysis history")
    export_metadata: Dict[str, Any] = Field(..., description="Export metadata")