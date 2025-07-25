"""
AI analysis cache model.
"""

from sqlalchemy import Column, String, Date, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class AIAnalysisCache(Base, TimestampMixin):
    """AI analysis cache model."""
    
    __tablename__ = "ai_analysis_cache"
    
    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    analysis_date = Column(Date, primary_key=True)
    analysis_type = Column(String(50), primary_key=True)
    model_version = Column(String(100), primary_key=True)
    prompt_hash = Column(String(64), nullable=True)
    analysis_result = Column(JSONB, nullable=False)
    confidence_score = Column(NUMERIC(3, 2), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    cost_usd = Column(NUMERIC(10, 8), nullable=True)
    
    # Add check constraint for analysis_type
    __table_args__ = (
        CheckConstraint(
            "analysis_type IN ('short_term', 'mid_term', 'long_term', 'comprehensive')",
            name="check_analysis_type"
        ),
    )
    
    # Relationships
    stock = relationship("Stock", back_populates="ai_analyses")