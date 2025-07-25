"""
Financial report models.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FinancialReport(Base, UUIDMixin, TimestampMixin):
    """Financial report model."""
    
    __tablename__ = "financial_reports"
    
    ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_period = Column(String(10), nullable=False)
    report_type = Column(String(20), nullable=False)
    announced_at = Column(String, nullable=False)  # ISO datetime string
    source_url = Column(String(512), nullable=True)
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint(
            "fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4', 'FY')",
            name="check_fiscal_period"
        ),
        CheckConstraint(
            "report_type IN ('quarterly', 'annual')",
            name="check_report_type"
        ),
        # Unique constraint for ticker, fiscal_year, fiscal_period
        {"schema": None}  # This allows us to add unique constraint in migration
    )
    
    # Relationships
    stock = relationship("Stock", back_populates="financial_reports")
    line_items = relationship("FinancialReportLineItem", back_populates="report", cascade="all, delete-orphan")


class FinancialReportLineItem(Base):
    """Financial report line items (EAV model for extensibility)."""
    
    __tablename__ = "financial_report_line_items"
    
    report_id = Column(UUID(as_uuid=True), ForeignKey("financial_reports.id"), primary_key=True)
    metric_name = Column(String(100), primary_key=True)
    metric_value = Column(NUMERIC(20, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="JPY")
    period_type = Column(String(10), nullable=True)
    
    # Add check constraint
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('quarterly', 'annual', 'ytd')",
            name="check_period_type"
        ),
    )
    
    # Relationships
    report = relationship("FinancialReport", back_populates="line_items")