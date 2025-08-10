"""
Subscription and billing models.
"""

from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Plan(Base, TimestampMixin):
    """Subscription plan model."""

    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_name = Column(String(50), unique=True, nullable=False)
    price_monthly = Column(Integer, nullable=False)  # Price in Japanese Yen
    features = Column(JSONB, nullable=False, default=dict)
    api_quota_daily = Column(Integer, nullable=False, default=10)
    ai_analysis_quota_daily = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base, UUIDMixin, TimestampMixin):
    """User subscription model."""

    __tablename__ = "subscriptions"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    current_period_start = Column(String, nullable=False)  # ISO datetime string
    current_period_end = Column(String, nullable=False)  # ISO datetime string

    # Add check constraint for status
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'cancelled', 'expired')",
            name="check_subscription_status",
        ),
    )

    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")
