"""
News and sentiment models.
"""

from sqlalchemy import Column, String, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class NewsArticle(Base, UUIDMixin, TimestampMixin):
    """News article model."""
    
    __tablename__ = "news_articles"
    
    article_url = Column(String(512), unique=True, nullable=True)
    headline = Column(String, nullable=False)  # TEXT type
    content_summary = Column(String, nullable=True)  # TEXT type
    source = Column(String(100), nullable=True)
    author = Column(String(255), nullable=True)
    published_at = Column(String, nullable=False)  # ISO datetime string
    sentiment_label = Column(String(20), nullable=True)
    sentiment_score = Column(NUMERIC(5, 4), nullable=True)  # -1.0 to 1.0
    language = Column(String(10), nullable=False, default="ja")
    
    # Add check constraint for sentiment_label
    __table_args__ = (
        CheckConstraint(
            "sentiment_label IN ('positive', 'negative', 'neutral')",
            name="check_sentiment_label"
        ),
    )
    
    # Relationships
    stock_links = relationship("StockNewsLink", back_populates="article", cascade="all, delete-orphan")


class StockNewsLink(Base):
    """Stock-news relationship model."""
    
    __tablename__ = "stock_news_link"
    
    article_id = Column(UUID(as_uuid=True), ForeignKey("news_articles.id"), primary_key=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    relevance_score = Column(NUMERIC(3, 2), nullable=False, default=1.0)  # 0.0 to 1.0
    
    # Relationships
    article = relationship("NewsArticle", back_populates="stock_links")
    stock = relationship("Stock", back_populates="news_links")