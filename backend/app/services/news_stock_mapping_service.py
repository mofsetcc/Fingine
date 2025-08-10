"""
News-stock relationship mapping service.

This service handles automatic linking of news articles to stocks based on
ticker symbols and company names, with relevance scoring.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.database import get_db
from ..models.news import NewsArticle, StockNewsLink
from ..models.stock import Stock

logger = logging.getLogger(__name__)


class NewsStockMappingService:
    """
    Service for creating and managing relationships between news articles and stocks.

    This service provides:
    - Automatic stock-news linking based on ticker and company names
    - Relevance scoring for news articles
    - News filtering by stock ticker
    - Batch processing for efficient mapping
    """

    def __init__(self):
        # Minimum relevance score threshold for creating links
        self.min_relevance_threshold = 0.1

        # Cache for stock information to avoid repeated database queries
        self._stock_cache: Dict[str, Stock] = {}
        self._cache_last_updated: Optional[datetime] = None
        self._cache_ttl_seconds = 3600  # 1 hour

        # Japanese text processing patterns
        self._japanese_company_suffixes = [
            "株式会社",
            "㈱",
            "有限会社",
            "㈲",
            "合同会社",
            "合資会社",
            "合名会社",
            "Corporation",
            "Corp",
            "Inc",
            "Ltd",
            "Limited",
            "Co",
            "Company",
        ]

        # Common financial keywords that boost relevance
        self._financial_keywords = [
            "決算",
            "業績",
            "売上",
            "利益",
            "損失",
            "株価",
            "配当",
            "増収",
            "減収",
            "earnings",
            "revenue",
            "profit",
            "loss",
            "dividend",
            "stock",
            "share",
        ]

    async def refresh_stock_cache(self) -> None:
        """Refresh the internal stock cache."""
        try:
            async with get_db() as db:
                result = await db.execute(select(Stock).where(Stock.is_active == True))
                stocks = result.scalars().all()

                self._stock_cache = {stock.ticker: stock for stock in stocks}
                self._cache_last_updated = datetime.utcnow()

                logger.info(
                    f"Refreshed stock cache with {len(self._stock_cache)} active stocks"
                )

        except Exception as e:
            logger.error(f"Error refreshing stock cache: {e}")

    async def _ensure_stock_cache(self) -> None:
        """Ensure stock cache is fresh."""
        if (
            self._cache_last_updated is None
            or (datetime.utcnow() - self._cache_last_updated).total_seconds()
            > self._cache_ttl_seconds
        ):
            await self.refresh_stock_cache()

    async def create_stock_news_links(
        self, article_id: str, article_text: str, force_refresh: bool = False
    ) -> List[Dict[str, any]]:
        """
        Create stock-news links for a given article.

        Args:
            article_id: UUID of the news article
            article_text: Combined headline and content for analysis
            force_refresh: Whether to force refresh of existing links

        Returns:
            List of created stock links with relevance scores
        """
        await self._ensure_stock_cache()

        try:
            async with get_db() as db:
                # Check if links already exist
                if not force_refresh:
                    existing_links = await db.execute(
                        select(StockNewsLink).where(
                            StockNewsLink.article_id == article_id
                        )
                    )
                    if existing_links.scalars().first():
                        logger.debug(f"Links already exist for article {article_id}")
                        return []

                # Find potential stock matches
                stock_matches = self._find_stock_matches(article_text)

                created_links = []
                for ticker, relevance_score in stock_matches:
                    if relevance_score >= self.min_relevance_threshold:
                        # Create stock-news link
                        link = StockNewsLink(
                            article_id=article_id,
                            ticker=ticker,
                            relevance_score=relevance_score,
                        )

                        db.add(link)
                        created_links.append(
                            {
                                "ticker": ticker,
                                "relevance_score": relevance_score,
                                "company_name": self._stock_cache[
                                    ticker
                                ].company_name_jp,
                            }
                        )

                await db.commit()

                logger.info(
                    f"Created {len(created_links)} stock links for article {article_id}"
                )
                return created_links

        except Exception as e:
            logger.error(
                f"Error creating stock-news links for article {article_id}: {e}"
            )
            return []

    def _find_stock_matches(self, article_text: str) -> List[Tuple[str, float]]:
        """
        Find stock matches in article text with relevance scores.

        Args:
            article_text: Text to analyze for stock mentions

        Returns:
            List of (ticker, relevance_score) tuples
        """
        article_text_lower = article_text.lower()
        matches = []

        for ticker, stock in self._stock_cache.items():
            relevance_score = self._calculate_relevance_score(
                article_text_lower, ticker, stock
            )

            if relevance_score > 0:
                matches.append((ticker, relevance_score))

        # Sort by relevance score descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def _calculate_relevance_score(
        self, article_text_lower: str, ticker: str, stock: Stock
    ) -> float:
        """
        Calculate relevance score for a stock-article pair.

        Args:
            article_text_lower: Lowercase article text
            ticker: Stock ticker symbol
            stock: Stock object

        Returns:
            Relevance score between 0.0 and 1.0
        """
        score = 0.0

        # Direct ticker mention (highest weight)
        if ticker.lower() in article_text_lower:
            score += 0.4

            # Bonus for ticker in context (e.g., "7203.T", "(7203)")
            ticker_patterns = [
                f"{ticker.lower()}.t",  # Tokyo Stock Exchange format
                f"({ticker.lower()})",  # Parenthetical format
                f"[{ticker.lower()}]",  # Bracket format
                f"#{ticker.lower()}",  # Hash tag format
            ]

            for pattern in ticker_patterns:
                if pattern in article_text_lower:
                    score += 0.1
                    break

        # Japanese company name mention
        if stock.company_name_jp:
            company_name_variations = self._generate_company_name_variations(
                stock.company_name_jp
            )

            for variation in company_name_variations:
                if variation.lower() in article_text_lower:
                    score += 0.3
                    break

        # English company name mention
        if stock.company_name_en:
            company_name_variations = self._generate_company_name_variations(
                stock.company_name_en
            )

            for variation in company_name_variations:
                if variation.lower() in article_text_lower:
                    score += 0.25
                    break

        # Financial keywords boost (if stock is mentioned)
        if score > 0:
            financial_keyword_count = sum(
                1
                for keyword in self._financial_keywords
                if keyword.lower() in article_text_lower
            )

            # Add up to 0.2 bonus for financial keywords
            score += min(financial_keyword_count * 0.05, 0.2)

        # Sector/industry context boost
        if score > 0 and stock.sector_jp:
            sector_keywords = self._get_sector_keywords(stock.sector_jp)
            for keyword in sector_keywords:
                if keyword.lower() in article_text_lower:
                    score += 0.1
                    break

        # Normalize score to 0-1 range
        return min(score, 1.0)

    def _generate_company_name_variations(self, company_name: str) -> List[str]:
        """
        Generate variations of company name for matching.

        Args:
            company_name: Original company name

        Returns:
            List of name variations
        """
        variations = [company_name]

        # Remove common suffixes
        name_without_suffix = company_name
        for suffix in self._japanese_company_suffixes:
            if company_name.endswith(suffix):
                name_without_suffix = company_name[: -len(suffix)].strip()
                variations.append(name_without_suffix)
                break

        # Add abbreviated forms
        if len(name_without_suffix) > 4:
            # For Japanese companies, try first few characters
            variations.append(name_without_suffix[:3])
            variations.append(name_without_suffix[:4])

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for variation in variations:
            if variation and variation not in seen:
                seen.add(variation)
                unique_variations.append(variation)

        return unique_variations

    def _get_sector_keywords(self, sector: str) -> List[str]:
        """
        Get relevant keywords for a sector.

        Args:
            sector: Sector name in Japanese

        Returns:
            List of relevant keywords
        """
        sector_keywords_map = {
            "自動車": ["自動車", "車", "automobile", "automotive", "car"],
            "電機": ["電機", "電子", "electronics", "electrical"],
            "銀行": ["銀行", "金融", "bank", "banking", "financial"],
            "小売": ["小売", "retail", "店舗", "store"],
            "製薬": ["製薬", "薬", "pharmaceutical", "drug", "medicine"],
            "通信": ["通信", "telecom", "telecommunications", "mobile"],
            "不動産": ["不動産", "real estate", "property", "建設"],
            "エネルギー": ["エネルギー", "energy", "電力", "power", "oil", "gas"],
        }

        return sector_keywords_map.get(sector, [])

    async def batch_create_links_for_articles(
        self, article_ids: List[str], batch_size: int = 50
    ) -> Dict[str, int]:
        """
        Create stock-news links for multiple articles in batches.

        Args:
            article_ids: List of article IDs to process
            batch_size: Number of articles to process per batch

        Returns:
            Dictionary with processing statistics
        """
        await self._ensure_stock_cache()

        total_processed = 0
        total_links_created = 0
        errors = 0

        try:
            # Process articles in batches
            for i in range(0, len(article_ids), batch_size):
                batch_ids = article_ids[i : i + batch_size]

                async with get_db() as db:
                    # Get articles with their text content
                    result = await db.execute(
                        select(NewsArticle).where(NewsArticle.id.in_(batch_ids))
                    )
                    articles = result.scalars().all()

                    for article in articles:
                        try:
                            article_text = (
                                f"{article.headline} {article.content_summary or ''}"
                            )
                            links = await self.create_stock_news_links(
                                str(article.id), article_text
                            )
                            total_links_created += len(links)
                            total_processed += 1

                        except Exception as e:
                            logger.error(f"Error processing article {article.id}: {e}")
                            errors += 1

                logger.info(
                    f"Processed batch {i//batch_size + 1}: {len(batch_ids)} articles"
                )

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            errors += 1

        stats = {
            "total_processed": total_processed,
            "total_links_created": total_links_created,
            "errors": errors,
            "success_rate": total_processed / len(article_ids) if article_ids else 0,
        }

        logger.info(f"Batch processing completed: {stats}")
        return stats

    async def get_news_for_stock(
        self,
        ticker: str,
        limit: int = 20,
        min_relevance: float = 0.1,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, any]]:
        """
        Get news articles for a specific stock with filtering.

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of articles to return
            min_relevance: Minimum relevance score threshold
            start_date: Start date filter
            end_date: End date filter

        Returns:
            List of news articles with relevance scores
        """
        try:
            async with get_db() as db:
                query = (
                    select(NewsArticle, StockNewsLink.relevance_score)
                    .join(StockNewsLink)
                    .where(
                        and_(
                            StockNewsLink.ticker == ticker,
                            StockNewsLink.relevance_score >= min_relevance,
                        )
                    )
                    .order_by(desc(NewsArticle.published_at))
                )

                # Add date filters if provided
                if start_date:
                    query = query.where(
                        NewsArticle.published_at >= start_date.isoformat()
                    )
                if end_date:
                    query = query.where(
                        NewsArticle.published_at <= end_date.isoformat()
                    )

                query = query.limit(limit)

                result = await db.execute(query)
                rows = result.all()

                articles = []
                for article, relevance_score in rows:
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
                        "sentiment_score": float(article.sentiment_score)
                        if article.sentiment_score
                        else None,
                        "relevance_score": float(relevance_score),
                    }
                    articles.append(article_dict)

                return articles

        except Exception as e:
            logger.error(f"Error getting news for stock {ticker}: {e}")
            return []

    async def get_stocks_mentioned_in_article(
        self, article_id: str, min_relevance: float = 0.1
    ) -> List[Dict[str, any]]:
        """
        Get stocks mentioned in a specific article.

        Args:
            article_id: Article ID
            min_relevance: Minimum relevance score threshold

        Returns:
            List of stocks with relevance scores
        """
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(Stock, StockNewsLink.relevance_score)
                    .join(StockNewsLink)
                    .where(
                        and_(
                            StockNewsLink.article_id == article_id,
                            StockNewsLink.relevance_score >= min_relevance,
                        )
                    )
                    .order_by(desc(StockNewsLink.relevance_score))
                )

                stocks = []
                for stock, relevance_score in result.all():
                    stock_dict = {
                        "ticker": stock.ticker,
                        "company_name_jp": stock.company_name_jp,
                        "company_name_en": stock.company_name_en,
                        "sector_jp": stock.sector_jp,
                        "industry_jp": stock.industry_jp,
                        "relevance_score": float(relevance_score),
                    }
                    stocks.append(stock_dict)

                return stocks

        except Exception as e:
            logger.error(f"Error getting stocks for article {article_id}: {e}")
            return []

    async def update_relevance_scores(
        self, article_id: str, force_recalculate: bool = False
    ) -> int:
        """
        Update relevance scores for an article's stock links.

        Args:
            article_id: Article ID
            force_recalculate: Whether to recalculate all scores

        Returns:
            Number of updated links
        """
        try:
            async with get_db() as db:
                # Get article and its current links
                article_result = await db.execute(
                    select(NewsArticle)
                    .options(selectinload(NewsArticle.stock_links))
                    .where(NewsArticle.id == article_id)
                )
                article = article_result.scalar_one_or_none()

                if not article:
                    logger.warning(f"Article {article_id} not found")
                    return 0

                article_text = f"{article.headline} {article.content_summary or ''}"
                await self._ensure_stock_cache()

                updated_count = 0

                for link in article.stock_links:
                    if link.ticker in self._stock_cache:
                        stock = self._stock_cache[link.ticker]
                        new_score = self._calculate_relevance_score(
                            article_text.lower(), link.ticker, stock
                        )

                        if (
                            force_recalculate
                            or abs(float(link.relevance_score) - new_score) > 0.1
                        ):
                            link.relevance_score = new_score
                            updated_count += 1

                await db.commit()

                logger.info(
                    f"Updated {updated_count} relevance scores for article {article_id}"
                )
                return updated_count

        except Exception as e:
            logger.error(
                f"Error updating relevance scores for article {article_id}: {e}"
            )
            return 0

    async def get_mapping_statistics(self) -> Dict[str, any]:
        """
        Get statistics about news-stock mappings.

        Returns:
            Dictionary with mapping statistics
        """
        try:
            async with get_db() as db:
                # Total articles
                total_articles_result = await db.execute(
                    select(func.count(NewsArticle.id))
                )
                total_articles = total_articles_result.scalar()

                # Articles with stock links
                linked_articles_result = await db.execute(
                    select(func.count(func.distinct(StockNewsLink.article_id)))
                )
                linked_articles = linked_articles_result.scalar()

                # Total stock links
                total_links_result = await db.execute(
                    select(func.count(StockNewsLink.article_id))
                )
                total_links = total_links_result.scalar()

                # Average relevance score
                avg_relevance_result = await db.execute(
                    select(func.avg(StockNewsLink.relevance_score))
                )
                avg_relevance = avg_relevance_result.scalar()

                # Top stocks by news count
                top_stocks_result = await db.execute(
                    select(
                        StockNewsLink.ticker,
                        func.count(StockNewsLink.article_id).label("news_count"),
                    )
                    .group_by(StockNewsLink.ticker)
                    .order_by(desc("news_count"))
                    .limit(10)
                )
                top_stocks = [
                    {"ticker": ticker, "news_count": count}
                    for ticker, count in top_stocks_result.all()
                ]

                return {
                    "total_articles": total_articles,
                    "linked_articles": linked_articles,
                    "linking_rate": linked_articles / total_articles
                    if total_articles > 0
                    else 0,
                    "total_links": total_links,
                    "avg_links_per_article": total_links / linked_articles
                    if linked_articles > 0
                    else 0,
                    "avg_relevance_score": float(avg_relevance) if avg_relevance else 0,
                    "top_stocks_by_news": top_stocks,
                    "cache_size": len(self._stock_cache),
                    "cache_last_updated": self._cache_last_updated.isoformat()
                    if self._cache_last_updated
                    else None,
                }

        except Exception as e:
            logger.error(f"Error getting mapping statistics: {e}")
            return {}


# Global service instance
news_stock_mapping_service = NewsStockMappingService()
