"""
User authentication and profile models.
"""

from sqlalchemy import Boolean, Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """User authentication model."""
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    email_verified_at = Column(String, nullable=True)  # ISO datetime string
    
    # GDPR compliance fields
    gdpr_consents = Column(JSONB, nullable=True, default=dict)  # Store consent records
    is_deleted = Column(Boolean, nullable=False, default=False)  # Soft delete flag
    deleted_at = Column(String, nullable=True)  # ISO datetime string
    data_retention_until = Column(String, nullable=True)  # ISO datetime string
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    oauth_identities = relationship("UserOAuthIdentity", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    watchlist = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    api_usage_logs = relationship("APIUsageLog", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def email_verified(self) -> bool:
        """Check if email is verified."""
        return self.email_verified_at is not None


class UserProfile(Base, TimestampMixin):
    """User profile and preferences model."""
    
    __tablename__ = "user_profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    display_name = Column(String(50), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    timezone = Column(String(50), nullable=False, default="Asia/Tokyo")
    notification_preferences = Column(JSONB, nullable=False, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="profile")


class UserOAuthIdentity(Base, TimestampMixin):
    """OAuth identity linking model."""
    
    __tablename__ = "user_oauth_identities"
    
    provider = Column(String(50), primary_key=True)  # 'google', 'line'
    provider_user_id = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="oauth_identities")