"""
User watchlist model.
"""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class UserWatchlist(Base, TimestampMixin):
    """User stock watchlist model."""

    __tablename__ = "user_watchlists"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    notes = Column(String, nullable=True)  # TEXT type

    # Note: added_at is handled by TimestampMixin.created_at

    # Relationships
    user = relationship("User", back_populates="watchlist")
    stock = relationship("Stock", back_populates="watchlist_entries")
