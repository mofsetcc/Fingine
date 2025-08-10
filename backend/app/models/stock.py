"""
Stock and market data models.
"""

from sqlalchemy import BigInteger, Boolean, Column, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    """Stock master data model."""

    __tablename__ = "stocks"

    ticker = Column(String(10), primary_key=True)
    company_name_jp = Column(String(255), nullable=False)
    company_name_en = Column(String(255), nullable=True)
    sector_jp = Column(String(100), nullable=True)
    industry_jp = Column(String(100), nullable=True)
    description = Column(String, nullable=True)  # TEXT type
    logo_url = Column(String(255), nullable=True)
    listing_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    daily_metrics = relationship(
        "StockDailyMetrics", back_populates="stock", cascade="all, delete-orphan"
    )
    price_history = relationship(
        "StockPriceHistory", back_populates="stock", cascade="all, delete-orphan"
    )
    financial_reports = relationship(
        "FinancialReport", back_populates="stock", cascade="all, delete-orphan"
    )
    news_links = relationship(
        "StockNewsLink", back_populates="stock", cascade="all, delete-orphan"
    )
    ai_analyses = relationship(
        "AIAnalysisCache", back_populates="stock", cascade="all, delete-orphan"
    )
    watchlist_entries = relationship(
        "UserWatchlist", back_populates="stock", cascade="all, delete-orphan"
    )


class StockDailyMetrics(Base):
    """Daily stock metrics model."""

    __tablename__ = "stock_daily_metrics"

    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    date = Column(Date, primary_key=True)
    market_cap = Column(BigInteger, nullable=True)
    pe_ratio = Column(NUMERIC(10, 2), nullable=True)
    pb_ratio = Column(NUMERIC(10, 2), nullable=True)
    dividend_yield = Column(NUMERIC(5, 4), nullable=True)
    shares_outstanding = Column(BigInteger, nullable=True)

    # Relationships
    stock = relationship("Stock", back_populates="daily_metrics")


class StockPriceHistory(Base):
    """Stock price history (OHLCV) model."""

    __tablename__ = "stock_price_history"

    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    date = Column(Date, primary_key=True)
    open = Column(NUMERIC(14, 4), nullable=False)
    high = Column(NUMERIC(14, 4), nullable=False)
    low = Column(NUMERIC(14, 4), nullable=False)
    close = Column(NUMERIC(14, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    adjusted_close = Column(NUMERIC(14, 4), nullable=True)

    # Relationships
    stock = relationship("Stock", back_populates="price_history")
