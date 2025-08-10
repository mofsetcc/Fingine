"""
API usage and logging models.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import NUMERIC, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class APIUsageLog(Base):
    """API usage logging model."""

    __tablename__ = "api_usage_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    api_provider = Column(String(50), nullable=False)
    endpoint = Column(String(255), nullable=True)
    request_type = Column(String(50), nullable=True)
    cost_usd = Column(NUMERIC(10, 8), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)
    request_timestamp = Column(String, nullable=False)  # ISO datetime string

    # Relationships
    user = relationship("User", back_populates="api_usage_logs")
