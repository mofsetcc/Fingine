"""
News collection and management service.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from ..adapters.news_adapter import NewsDataAdapter
from ..adapters.registry import registry
from ..models.news import NewsArticle, StockNewsLink
from ..models.stock import Stock
from ..core.database import get_db
from ..core.config import settings
from .news_stock_mapping_service import news_stock_mapping_service

logger = logging.getLogger(__name__)


class NewsCollectionService:
    """
    Service for collecting, processing, and managing news articles.
    Handles hourly news collection scheduling and deduplication.
    """
    
    def __init__(self):
        self.news_adapter: Optional[NewsDataAdapter] = None
        self._collection_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Collection settings
        self.collection_interval = 3600  # 1 hour in seconds
        self.max_articles_per_collection = 100
        self.article_retention_days = 30
        
        # Initialize adapter
        self._initialize_adapter()
    
    def _initialize_adapter(self) -> None:
        """Initialize news data adapter."""
        try:
            config = {
                "news_api_key": settings.NEWS_API_KEY
            }
            
            self.news_adapter = NewsDataAdapter(
                name="primary_news_adapter",
                priority=1,
                config=config
            )
            
            # Register with global registry
            registry.register_adapter(self.news_adapter)
            
            logger.info("News data adapter initialized and registered")
            
        except Exception as e:
            logger.error(f"Failed to initialize news adapter: {e}")
    
    async def start_collection_scheduler(self) -> None:
        """Start the background news collection scheduler."""
        if self._is_running:
            logger.warning("News collection scheduler is already running")
            return
        
        self._is_running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started news collection scheduler")
    
    async def stop_collection_scheduler(self) -> None:
        """Stop the background news collection scheduler."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped news collection scheduler")
    
    async def _collection_loop(self) -> None:
        """Main collection loop that runs every hour."""
        while self._is_running:
            try:
                logger.info("Starting news collection cycle")
                
                # Collect general market news
                await self.collect_general_news()
                
                # Collect stock-specific news for active stocks
                await self.collect_stock_specific_news()
                
                # Clean up old articles
                await self.cleanup_old_articles()
                
                logger.info("Completed news collection cycle")
                
                # Wait for next collection
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in news collection loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def collect_general_news(self) -> int:
        """
        Collect general market news articles.
        
        Returns:
            Number of new articles collected
        """
        if not self.news_adapter:
            logger.error("News adapter not available")
            return 0
        
        try:
            # Define general market keywords
            keywords = [
                "日本株式市場",
                "東京証券取引所",
                "日経平均",
                "TOPIX",
                "株価",
                "決算",
                "業績",
                "投資"
            ]
            
            # Collect articles from last 2 hours to ensure we don't miss any
            start_date = datetime.utcnow() - timedelta(hours=2)
            end_date = datetime.utcnow()
            
            articles = await self.news_adapter.get_news(
                keywords=keywords,
                limit=self.max_articles_per_collection // 2,
                start_date=start_date,
                end_date=end_date
            )
            
            # Store articles in database
            new_articles_count = await self._store_articles(articles)
            
            logger.info(f"Collected {new_articles_count} new general market articles")
            return new_articles_count
            
        except Exception as e:
            logger.error(f"Error collecting general news: {e}")
            return 0
    
    async def collect_stock_specific_news(self) -> int:
        """
        Collect news for specific stocks.
        
        Returns:
            Number of new articles collected
        """
        if not self.news_adapter:
            logger.error("News adapter not available")
            return 0
        
        try:
            # Get active stocks (you might want to limit this to popular stocks)
            async with get_db() as db:
                result = await db.execute(
                    select(Stock)
                    .where(Stock.is_active == True)
                    .limit(50)  # Limit to avoid too many API calls
                )
                stocks = result.scalars().all()
            
            total_new_articles = 0
            
            # Process stocks in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(stocks), batch_size):
                batch = stocks[i:i + batch_size]
                
                # Process batch concurrently
                tasks = []
                for stock in batch:
                    task = self._collect_stock_news(stock)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, int):
                        total_new_articles += result
                    elif isinstance(result, Exception):
                        logger.error(f"Error collecting stock news: {result}")
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            logger.info(f"Collected {total_new_articles} new stock-specific articles")
            return total_new_articles
            
        except Exception as e:
            logger.error(f"Error collecting stock-specific news: {e}")
            return 0
    
    async def _collect_stock_news(self, stock: Stock) -> int:
        """Collect news for a specific stock."""
        try:
            # Use both ticker and company name for search
            keywords = [stock.company_name_jp]
            if stock.company_name_en:
                keywords.append(stock.company_name_en)
            
            start_date = datetime.utcnow() - timedelta(hours=2)
            end_date = datetime.utcnow()
            
            articles = await self.news_adapter.get_news(
                symbol=stock.ticker,
                keywords=keywords,
                limit=10,  # Limit per stock
                start_date=start_date,
                end_date=end_date
            )
            
            # Store articles and create stock-news links
            new_articles_count = await self._store_articles(articles, stock.ticker)
            
            return new_articles_count
            
        except Exception as e:
            logger.error(f"Error collecting news for stock {stock.ticker}: {e}")
            return 0
    
    async def _store_articles(self, articles: List[Dict[str, Any]], ticker: Optional[str] = None) -> int:
        """
        Store articles in database with deduplication.
        
        Args:
            articles: List of article dictionaries
            ticker: Optional ticker to create stock-news link
            
        Returns:
            Number of new articles stored
        """
        if not articles:
            return 0
        
        new_articles_count = 0
        
        try:
            async with get_db() as db:
                for article_data in articles:
                    # Check if article already exists
                    article_url = article_data.get("article_url")
                    if article_url:
                        existing = await db.execute(
                            select(NewsArticle).where(NewsArticle.article_url == article_url)
                        )
                        if existing.scalar_one_or_none():
                            continue  # Skip duplicate
                    
                    # Create new article
                    article = NewsArticle(
                        article_url=article_data.get("article_url"),
                        headline=article_data.get("headline", ""),
                        content_summary=article_data.get("content_summary"),
                        source=article_data.get("source"),
                        author=article_data.get("author"),
                        published_at=article_data.get("published_at", datetime.utcnow().isoformat()),
                        language=article_data.get("language", "ja")
                    )
                    
                    db.add(article)
                    await db.flush()  # Get the article ID
                    
                    # Create stock-news links using mapping service
                    article_text = f"{article.headline} {article.content_summary or ''}"
                    
                    # Use mapping service for automatic stock-news linking
                    try:
                        await news_stock_mapping_service.create_stock_news_links(
                            str(article.id), article_text
                        )
                    except Exception as e:
                        logger.error(f"Error creating stock-news links for article {article.id}: {e}")
                    
                    # If specific ticker provided, ensure it's linked with high relevance
                    if ticker:
                        # Check if stock exists
                        stock_result = await db.execute(
                            select(Stock).where(Stock.ticker == ticker)
                        )
                        stock = stock_result.scalar_one_or_none()
                        
                        if stock:
                            # Check if link already exists
                            existing_link_result = await db.execute(
                                select(StockNewsLink).where(
                                    and_(
                                        StockNewsLink.article_id == article.id,
                                        StockNewsLink.ticker == ticker
                                    )
                                )
                            )
                            existing_link = existing_link_result.scalar_one_or_none()
                            
                            if existing_link:
                                # Update relevance score to ensure high relevance for targeted articles
                                existing_link.relevance_score = max(
                                    float(existing_link.relevance_score),
                                    article_data.get("relevance_score", 0.8)
                                )
                            else:
                                # Create new link with high relevance
                                stock_link = StockNewsLink(
                                    article_id=article.id,
                                    ticker=ticker,
                                    relevance_score=article_data.get("relevance_score", 0.8)
                                )
                                db.add(stock_link)
                    
                    new_articles_count += 1
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error storing articles: {e}")
            await db.rollback()
        
        return new_articles_count
    
    async def cleanup_old_articles(self) -> int:
        """
        Clean up articles older than retention period.
        
        Returns:
            Number of articles deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.article_retention_days)
            
            async with get_db() as db:
                # Find old articles
                result = await db.execute(
                    select(NewsArticle)
                    .where(NewsArticle.created_at < cutoff_date)
                )
                old_articles = result.scalars().all()
                
                deleted_count = len(old_articles)
                
                # Delete old articles (cascade will handle stock_news_link)
                for article in old_articles:
                    await db.delete(article)
                
                await db.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old articles")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {e}")
            return 0
    
    async def get_news_for_stock(
        self,
        ticker: str,
        limit: int = 20,
        min_relevance: float = 0.1,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get news articles for a specific stock using the mapping service.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of articles
            min_relevance: Minimum relevance score threshold
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of news articles with relevance scores
        """
        try:
            return await news_stock_mapping_service.get_news_for_stock(
                ticker=ticker,
                limit=limit,
                min_relevance=min_relevance,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Error getting news for stock {ticker}: {e}")
            return []
    
    async def get_recent_news(
        self,
        limit: int = 50,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent news articles.
        
        Args:
            limit: Maximum number of articles
            hours_back: How many hours back to look
            
        Returns:
            List of recent news articles
        """
        try:
            start_date = datetime.utcnow() - timedelta(hours=hours_back)
            
            async with get_db() as db:
                result = await db.execute(
                    select(NewsArticle)
                    .where(NewsArticle.published_at >= start_date.isoformat())
                    .order_by(desc(NewsArticle.published_at))
                    .limit(limit)
                )
                articles = result.scalars().all()
                
                # Convert to dictionaries
                article_dicts = []
                for article in articles:
                    article_dict = {
                        "id": str(article.id),
                        "headline": article.headline,
                        "content_summary": article.content_summary,
                        "source": article.source,
                        "author": article.author,
                        "published_at": article.published_at,
                        "article_url": article.article_url,
                        "language": article.language,
                        "sentiment_label": article.sentiment_label,
                        "sentiment_score": float(article.sentiment_score) if article.sentiment_score else None
                    }
                    article_dicts.append(article_dict)
                
                return article_dicts
                
        except Exception as e:
            logger.error(f"Error getting recent news: {e}")
            return []
    
    async def force_collection(self) -> Dict[str, int]:
        """
        Force an immediate news collection cycle.
        
        Returns:
            Dictionary with collection statistics
        """
        logger.info("Starting forced news collection")
        
        general_count = await self.collect_general_news()
        stock_count = await self.collect_stock_specific_news()
        cleaned_count = await self.cleanup_old_articles()
        
        stats = {
            "general_articles": general_count,
            "stock_articles": stock_count,
            "cleaned_articles": cleaned_count,
            "total_new_articles": general_count + stock_count
        }
        
        logger.info(f"Forced collection completed: {stats}")
        return stats
    
    async def process_existing_articles_for_mapping(
        self,
        batch_size: int = 100,
        force_refresh: bool = False
    ) -> Dict[str, int]:
        """
        Process existing articles to create stock-news mappings.
        
        Args:
            batch_size: Number of articles to process per batch
            force_refresh: Whether to refresh existing mappings
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            async with get_db() as db:
                # Get articles that need processing
                if force_refresh:
                    # Process all articles
                    result = await db.execute(
                        select(NewsArticle.id).order_by(desc(NewsArticle.created_at))
                    )
                else:
                    # Process articles without stock links
                    result = await db.execute(
                        select(NewsArticle.id)
                        .outerjoin(StockNewsLink)
                        .where(StockNewsLink.article_id.is_(None))
                        .order_by(desc(NewsArticle.created_at))
                    )
                
                article_ids = [str(row[0]) for row in result.all()]
                
                if not article_ids:
                    logger.info("No articles need processing for stock mapping")
                    return {"total_processed": 0, "total_links_created": 0, "errors": 0}
                
                logger.info(f"Processing {len(article_ids)} articles for stock mapping")
                
                # Use mapping service for batch processing
                stats = await news_stock_mapping_service.batch_create_links_for_articles(
                    article_ids, batch_size
                )
                
                return stats
                
        except Exception as e:
            logger.error(f"Error processing existing articles for mapping: {e}")
            return {"total_processed": 0, "total_links_created": 0, "errors": 1}
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """
        Get current status of news collection service.
        
        Returns:
            Dictionary with service status
        """
        adapter_status = None
        if self.news_adapter:
            health_check = await self.news_adapter.get_cached_health_check()
            adapter_status = {
                "status": health_check.status.value,
                "response_time_ms": health_check.response_time_ms,
                "last_check": health_check.last_check.isoformat(),
                "error_message": health_check.error_message
            }
        
        # Get article counts from database
        try:
            async with get_db() as db:
                # Total articles
                total_result = await db.execute(select(NewsArticle))
                total_articles = len(total_result.scalars().all())
                
                # Recent articles (last 24 hours)
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_result = await db.execute(
                    select(NewsArticle)
                    .where(NewsArticle.created_at >= recent_cutoff)
                )
                recent_articles = len(recent_result.scalars().all())
                
        except Exception as e:
            logger.error(f"Error getting article counts: {e}")
            total_articles = 0
            recent_articles = 0
        
        # Get mapping statistics
        mapping_stats = await news_stock_mapping_service.get_mapping_statistics()
        
        return {
            "is_running": self._is_running,
            "collection_interval": self.collection_interval,
            "adapter_status": adapter_status,
            "total_articles": total_articles,
            "recent_articles_24h": recent_articles,
            "max_articles_per_collection": self.max_articles_per_collection,
            "article_retention_days": self.article_retention_days,
            "mapping_statistics": mapping_stats
        }


# Global service instance
news_service = NewsCollectionService()