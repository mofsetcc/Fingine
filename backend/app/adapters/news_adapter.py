"""
News data adapter for collecting news articles from various sources.
"""

import asyncio
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from ..core.config import settings
from .base import CostInfo, HealthCheck, HealthStatus, NewsAdapter, RateLimitInfo

logger = logging.getLogger(__name__)


class NewsDataAdapter(NewsAdapter):
    """
    News data adapter that aggregates news from multiple sources including
    News API and RSS feeds from Japanese financial sources.
    """

    def __init__(
        self,
        name: str = "news_data_adapter",
        priority: int = 100,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, priority, config)

        # Configuration
        self.news_api_key = config.get("news_api_key") or settings.NEWS_API_KEY
        self.news_api_base_url = "https://newsapi.org/v2"

        # RSS feed sources for Japanese financial news
        self.rss_sources = [
            {
                "name": "Nikkei",
                "url": "https://www.nikkei.com/rss/",
                "language": "ja",
                "priority": 1,
            },
            {
                "name": "Reuters Japan",
                "url": "https://feeds.reuters.com/reuters/JPdomesticNews",
                "language": "ja",
                "priority": 2,
            },
            {
                "name": "Yahoo Finance Japan",
                "url": "https://news.yahoo.co.jp/rss/topics/business.xml",
                "language": "ja",
                "priority": 3,
            },
            {
                "name": "Kabutan",
                "url": "https://kabutan.jp/rss/",
                "language": "ja",
                "priority": 4,
            },
        ]

        # Rate limiting
        self.news_api_rate_limit = {
            "requests_per_minute": 5,
            "requests_per_hour": 100,
            "requests_per_day": 1000,
        }

        # Deduplication cache
        self._seen_articles: Set[str] = set()
        self._article_cache_ttl = 86400  # 24 hours

        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "Project Kessan News Aggregator/1.0"},
            )
        return self._session

    async def health_check(self) -> HealthCheck:
        """Check health of news data sources."""
        start_time = datetime.utcnow()

        try:
            # Test News API if available
            if self.news_api_key:
                await self._test_news_api()

            # Test RSS feeds
            await self._test_rss_feeds()

            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                metadata={
                    "sources_tested": len(self.rss_sources)
                    + (1 if self.news_api_key else 0)
                },
            )

        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"News adapter health check failed: {e}")

            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error_message=str(e),
            )

    async def _test_news_api(self) -> None:
        """Test News API connectivity."""
        session = await self._get_session()

        url = f"{self.news_api_base_url}/everything"
        params = {"q": "Japan stock market", "pageSize": 1, "apiKey": self.news_api_key}

        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"News API returned status {response.status}")

            data = await response.json()
            if data.get("status") != "ok":
                raise Exception(
                    f"News API error: {data.get('message', 'Unknown error')}"
                )

    async def _test_rss_feeds(self) -> None:
        """Test RSS feed connectivity."""
        session = await self._get_session()

        # Test first RSS source
        if self.rss_sources:
            source = self.rss_sources[0]
            async with session.get(source["url"]) as response:
                if response.status != 200:
                    raise Exception(
                        f"RSS feed {source['name']} returned status {response.status}"
                    )

    async def get_rate_limit_info(self) -> RateLimitInfo:
        """Get rate limit information."""
        # This is a simplified implementation
        # In production, you'd track actual usage
        return RateLimitInfo(
            requests_per_minute=self.news_api_rate_limit["requests_per_minute"],
            requests_per_hour=self.news_api_rate_limit["requests_per_hour"],
            requests_per_day=self.news_api_rate_limit["requests_per_day"],
            current_usage={"minute": 0, "hour": 0, "day": 0},
            reset_times={
                "minute": datetime.utcnow() + timedelta(minutes=1),
                "hour": datetime.utcnow() + timedelta(hours=1),
                "day": datetime.utcnow() + timedelta(days=1),
            },
        )

    async def get_cost_info(self) -> CostInfo:
        """Get cost information."""
        # News API pricing: $0.0001 per request for paid tier
        # RSS feeds are free
        return CostInfo(
            cost_per_request=0.0001 if self.news_api_key else 0.0,
            currency="USD",
            monthly_budget=100.0,
            current_monthly_usage=0.0,
        )

    async def get_news(
        self,
        symbol: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get news articles from multiple sources.

        Args:
            symbol: Stock symbol to filter news (e.g., "7203" for Toyota)
            keywords: Additional keywords to search for
            limit: Maximum number of articles to return
            start_date: Start date for news articles
            end_date: End date for news articles

        Returns:
            List of news articles with standardized format
        """
        all_articles = []

        try:
            # Collect from News API if available
            if self.news_api_key:
                news_api_articles = await self._get_news_api_articles(
                    symbol, keywords, limit // 2, start_date, end_date
                )
                all_articles.extend(news_api_articles)

            # Collect from RSS feeds
            rss_articles = await self._get_rss_articles(
                symbol, keywords, limit - len(all_articles), start_date, end_date
            )
            all_articles.extend(rss_articles)

            # Deduplicate articles
            deduplicated_articles = self._deduplicate_articles(all_articles)

            # Score relevance
            scored_articles = self._score_relevance(
                deduplicated_articles, symbol, keywords
            )

            # Sort by relevance and date, then limit
            sorted_articles = sorted(
                scored_articles,
                key=lambda x: (x.get("relevance_score", 0), x.get("published_at", "")),
                reverse=True,
            )

            return sorted_articles[:limit]

        except Exception as e:
            logger.error(f"Error collecting news: {e}")
            return []

    async def _get_news_api_articles(
        self,
        symbol: Optional[str],
        keywords: Optional[List[str]],
        limit: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Get articles from News API."""
        session = await self._get_session()

        # Build query
        query_parts = []

        if symbol:
            # Add company name lookup for symbol
            company_name = await self._get_company_name_for_symbol(symbol)
            if company_name:
                query_parts.append(f'"{company_name}"')
            query_parts.append(f'"{symbol}"')

        if keywords:
            query_parts.extend([f'"{keyword}"' for keyword in keywords])

        if not query_parts:
            query_parts = ["Japan stock market", "Tokyo Stock Exchange"]

        query = " OR ".join(query_parts)

        # API parameters
        params = {
            "q": query,
            "language": "ja",
            "sortBy": "publishedAt",
            "pageSize": min(limit, 100),
            "apiKey": self.news_api_key,
        }

        if start_date:
            params["from"] = start_date.isoformat()
        if end_date:
            params["to"] = end_date.isoformat()

        url = f"{self.news_api_base_url}/everything"

        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"News API returned status {response.status}")
                    return []

                data = await response.json()

                if data.get("status") != "ok":
                    logger.error(f"News API error: {data.get('message')}")
                    return []

                articles = []
                for article in data.get("articles", []):
                    normalized_article = self._normalize_news_api_article(article)
                    if normalized_article:
                        articles.append(normalized_article)

                return articles

        except Exception as e:
            logger.error(f"Error fetching from News API: {e}")
            return []

    async def _get_rss_articles(
        self,
        symbol: Optional[str],
        keywords: Optional[List[str]],
        limit: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Get articles from RSS feeds."""
        all_articles = []

        # Process RSS feeds concurrently
        tasks = []
        for source in self.rss_sources:
            task = self._process_rss_source(
                source, symbol, keywords, start_date, end_date
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"RSS processing error: {result}")

        # Sort by date and limit
        sorted_articles = sorted(
            all_articles, key=lambda x: x.get("published_at", ""), reverse=True
        )

        return sorted_articles[:limit]

    async def _process_rss_source(
        self,
        source: Dict[str, Any],
        symbol: Optional[str],
        keywords: Optional[List[str]],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Process a single RSS source."""
        try:
            session = await self._get_session()

            async with session.get(source["url"]) as response:
                if response.status != 200:
                    logger.warning(
                        f"RSS source {source['name']} returned status {response.status}"
                    )
                    return []

                content = await response.text()

                # Parse RSS feed using XML parser
                try:
                    root = ET.fromstring(content)
                    articles = []

                    # Handle both RSS and Atom feeds
                    items = root.findall(".//item") or root.findall(
                        ".//{http://www.w3.org/2005/Atom}entry"
                    )

                    for item in items:
                        article = self._normalize_rss_article_xml(item, source)
                        if article and self._filter_article(
                            article, symbol, keywords, start_date, end_date
                        ):
                            articles.append(article)

                    return articles

                except ET.ParseError as e:
                    logger.error(f"Error parsing RSS feed from {source['name']}: {e}")
                    return []

        except Exception as e:
            logger.error(f"Error processing RSS source {source['name']}: {e}")
            return []

    def _normalize_news_api_article(
        self, article: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize News API article to standard format."""
        try:
            return {
                "id": self._generate_article_id(article.get("url", "")),
                "headline": article.get("title", ""),
                "content_summary": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "author": article.get("author"),
                "published_at": article.get("publishedAt", ""),
                "article_url": article.get("url"),
                "language": "ja",
                "source_type": "news_api",
            }
        except Exception as e:
            logger.error(f"Error normalizing News API article: {e}")
            return None

    def _normalize_rss_article_xml(
        self, item: ET.Element, source: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize RSS article from XML element to standard format."""
        try:
            # Extract title
            title_elem = item.find("title")
            if title_elem is None:
                title_elem = item.find(".//{http://www.w3.org/2005/Atom}title")
            headline = title_elem.text if title_elem is not None else ""

            # Extract description/summary
            desc_elem = item.find("description")
            if desc_elem is None:
                desc_elem = item.find("summary")
            if desc_elem is None:
                desc_elem = item.find(".//{http://www.w3.org/2005/Atom}summary")
            if desc_elem is None:
                desc_elem = item.find(".//{http://www.w3.org/2005/Atom}content")

            content_summary = ""
            if desc_elem is not None:
                content_summary = self._clean_html(desc_elem.text or "")

            # Extract link
            link_elem = item.find("link")
            if link_elem is None:
                link_elem = item.find(".//{http://www.w3.org/2005/Atom}link")

            if link_elem is not None:
                # Handle both RSS and Atom link formats
                if link_elem.text:
                    article_url = link_elem.text
                else:
                    article_url = link_elem.get("href", "")
            else:
                article_url = ""

            # Extract published date
            pub_elem = item.find("pubDate")
            if pub_elem is None:
                pub_elem = item.find("published")
            if pub_elem is None:
                pub_elem = item.find(".//{http://www.w3.org/2005/Atom}published")
            if pub_elem is None:
                pub_elem = item.find(".//{http://www.w3.org/2005/Atom}updated")

            published_at = ""
            if pub_elem is not None:
                published_at = pub_elem.text or ""

            # Extract author
            author_elem = item.find("author")
            if author_elem is None:
                author_elem = item.find(
                    "dc:creator", {"dc": "http://purl.org/dc/elements/1.1/"}
                )
            if author_elem is None:
                author_elem = item.find(
                    ".//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name"
                )

            author = author_elem.text if author_elem is not None else None

            if not headline or not article_url:
                return None

            return {
                "id": self._generate_article_id(article_url),
                "headline": headline,
                "content_summary": content_summary,
                "source": source["name"],
                "author": author,
                "published_at": published_at,
                "article_url": article_url,
                "language": source["language"],
                "source_type": "rss",
            }
        except Exception as e:
            logger.error(f"Error normalizing RSS article: {e}")
            return None

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract text."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(strip=True)

        # Limit length
        if len(text) > 500:
            text = text[:497] + "..."

        return text

    def _generate_article_id(self, url: str) -> str:
        """Generate unique ID for article based on URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _filter_article(
        self,
        article: Dict[str, Any],
        symbol: Optional[str],
        keywords: Optional[List[str]],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> bool:
        """Filter article based on criteria."""
        # Date filtering
        if start_date or end_date:
            try:
                article_date = datetime.fromisoformat(
                    article.get("published_at", "").replace("Z", "+00:00")
                )
                if start_date and article_date < start_date:
                    return False
                if end_date and article_date > end_date:
                    return False
            except (ValueError, TypeError):
                # If we can't parse the date, include the article
                pass

        # Content filtering
        content = f"{article.get('headline', '')} {article.get('content_summary', '')}".lower()

        # Symbol filtering
        if symbol:
            if symbol.lower() not in content:
                # Try to find company name
                company_name = self._get_company_name_for_symbol_sync(symbol)
                if company_name and company_name.lower() not in content:
                    return False

        # Keyword filtering
        if keywords:
            found_keyword = False
            for keyword in keywords:
                if keyword.lower() in content:
                    found_keyword = True
                    break
            if not found_keyword:
                return False

        return True

    def _deduplicate_articles(
        self, articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on content similarity."""
        seen_ids = set()
        seen_headlines = set()
        deduplicated = []

        for article in articles:
            article_id = article.get("id")
            headline = article.get("headline", "").strip().lower()

            # Skip if we've seen this exact ID or very similar headline
            if article_id in seen_ids:
                continue

            # Check for similar headlines (simple approach)
            is_duplicate = False
            for seen_headline in seen_headlines:
                if self._calculate_similarity(headline, seen_headline) > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_ids.add(article_id)
                seen_headlines.add(headline)
                deduplicated.append(article)

        return deduplicated

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts."""
        if not text1 or not text2:
            return 0.0

        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _score_relevance(
        self,
        articles: List[Dict[str, Any]],
        symbol: Optional[str],
        keywords: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Score articles for relevance."""
        for article in articles:
            score = 0.0
            content = f"{article.get('headline', '')} {article.get('content_summary', '')}".lower()

            # Base score for source priority
            source_name = article.get("source", "").lower()
            if "nikkei" in source_name:
                score += 0.3
            elif "reuters" in source_name:
                score += 0.25
            elif "yahoo" in source_name:
                score += 0.2
            else:
                score += 0.1

            # Symbol relevance
            if symbol:
                if symbol.lower() in content:
                    score += 0.4

                company_name = self._get_company_name_for_symbol_sync(symbol)
                if company_name and company_name.lower() in content:
                    score += 0.3

            # Keyword relevance
            if keywords:
                for keyword in keywords:
                    if keyword.lower() in content:
                        score += 0.2

            # Recency bonus (articles from last 24 hours get bonus)
            try:
                article_date = datetime.fromisoformat(
                    article.get("published_at", "").replace("Z", "+00:00")
                )
                hours_old = (
                    datetime.utcnow() - article_date.replace(tzinfo=None)
                ).total_seconds() / 3600
                if hours_old < 24:
                    score += 0.1 * (1 - hours_old / 24)
            except (ValueError, TypeError):
                pass

            article["relevance_score"] = min(score, 1.0)

        return articles

    async def _get_company_name_for_symbol(self, symbol: str) -> Optional[str]:
        """Get company name for stock symbol (async version)."""
        # This would typically query the database
        # For now, return a simple mapping for common symbols
        symbol_to_name = {
            "7203": "トヨタ自動車",
            "6758": "ソニーグループ",
            "9984": "ソフトバンクグループ",
            "8306": "三菱UFJフィナンシャル・グループ",
        }
        return symbol_to_name.get(symbol)

    def _get_company_name_for_symbol_sync(self, symbol: str) -> Optional[str]:
        """Get company name for stock symbol (sync version)."""
        symbol_to_name = {
            "7203": "トヨタ自動車",
            "6758": "ソニーグループ",
            "9984": "ソフトバンクグループ",
            "8306": "三菱UFJフィナンシャル・グループ",
        }
        return symbol_to_name.get(symbol)

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, "_session") and self._session and not self._session.closed:
            # Note: This is not ideal but necessary for cleanup
            # In production, always call close() explicitly
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._session.close())
            except:
                pass
