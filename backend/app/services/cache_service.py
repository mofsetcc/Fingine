"""
Cache service for integrating caching with business logic.
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional

import structlog

from app.core.cache import CacheKeyBuilder, CacheKeyType, cache_manager

logger = structlog.get_logger(__name__)


class CacheService:
    """Service for managing cache operations with business logic."""

    def __init__(self):
        self.cache_manager = cache_manager

    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        key_type: Optional[CacheKeyType] = None,
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get data from cache or fetch and cache it if not found.

        Args:
            key: Cache key
            fetch_func: Async function to fetch data if not in cache
            key_type: Cache key type for TTL policy
            ttl: Custom TTL in seconds

        Returns:
            Cached or freshly fetched data
        """
        try:
            # Try to get from cache first
            cached_data = await self.cache_manager.cache.get(key)
            if cached_data is not None:
                logger.debug("Cache hit", key=key)
                return cached_data

            # Cache miss - fetch data
            logger.debug("Cache miss, fetching data", key=key)
            data = await fetch_func()

            # Cache the fetched data
            if data is not None:
                await self.cache_manager.cache.set(
                    key, data, ttl=ttl, key_type=key_type
                )
                logger.debug("Data cached", key=key)

            return data

        except Exception as e:
            logger.error("Cache operation failed", key=key, error=str(e))
            # Fall back to fetching data directly
            return await fetch_func()

    async def invalidate_stock_data(self, ticker: str) -> int:
        """Invalidate all cached data for a specific stock."""
        return await self.cache_manager.invalidate_stock_cache(ticker)

    async def get_stock_price_cached(
        self,
        ticker: str,
        fetch_func: Callable[[], Awaitable[Dict[str, Any]]],
        date: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Get stock price with caching."""
        key = CacheKeyBuilder.build_stock_price_key(ticker, date)
        return await self.get_or_set(key, fetch_func, CacheKeyType.STOCK_PRICE)

    async def get_financial_data_cached(
        self,
        ticker: str,
        report_type: str,
        period: str,
        fetch_func: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Get financial data with caching."""
        key = CacheKeyBuilder.build_financial_data_key(ticker, report_type, period)
        return await self.get_or_set(key, fetch_func, CacheKeyType.FINANCIAL_DATA)

    async def get_news_data_cached(
        self,
        fetch_func: Callable[[], Awaitable[List[Dict[str, Any]]]],
        ticker: str = None,
        category: str = "general",
    ) -> Optional[List[Dict[str, Any]]]:
        """Get news data with caching."""
        key = CacheKeyBuilder.build_news_key(ticker, category)
        return await self.get_or_set(key, fetch_func, CacheKeyType.NEWS_DATA)

    async def get_ai_analysis_cached(
        self,
        ticker: str,
        analysis_type: str,
        fetch_func: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Get AI analysis with caching."""
        key = CacheKeyBuilder.build_ai_analysis_key(ticker, analysis_type)
        return await self.get_or_set(key, fetch_func, CacheKeyType.AI_ANALYSIS)

    async def get_market_data_cached(
        self,
        market: str,
        data_type: str,
        fetch_func: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Get market data with caching."""
        key = CacheKeyBuilder.build_market_data_key(market, data_type)
        return await self.get_or_set(key, fetch_func, CacheKeyType.MARKET_DATA)

    async def track_api_quota(self, user_id: str, quota_type: str = "daily") -> int:
        """Track and increment API quota usage."""
        key = CacheKeyBuilder.build_api_quota_key(user_id, quota_type)

        # Determine TTL based on quota type
        ttl = 86400 if quota_type == "daily" else 2592000  # 24h or 30 days

        try:
            current_usage = await self.cache_manager.cache.increment(key, 1, ttl)
            logger.debug(
                "API quota tracked",
                user_id=user_id,
                quota_type=quota_type,
                usage=current_usage,
            )
            return current_usage
        except Exception as e:
            logger.error("Failed to track API quota", user_id=user_id, error=str(e))
            return 0

    async def get_api_quota_usage(self, user_id: str, quota_type: str = "daily") -> int:
        """Get current API quota usage."""
        key = CacheKeyBuilder.build_api_quota_key(user_id, quota_type)

        try:
            usage = await self.cache_manager.cache.get(key)
            return usage if usage is not None else 0
        except Exception as e:
            logger.error("Failed to get API quota usage", user_id=user_id, error=str(e))
            return 0

    async def reset_api_quota(self, user_id: str, quota_type: str = "daily") -> bool:
        """Reset API quota usage."""
        key = CacheKeyBuilder.build_api_quota_key(user_id, quota_type)

        try:
            result = await self.cache_manager.cache.delete(key)
            logger.info("API quota reset", user_id=user_id, quota_type=quota_type)
            return result
        except Exception as e:
            logger.error("Failed to reset API quota", user_id=user_id, error=str(e))
            return False

    async def cache_user_session(
        self, user_id: str, session_data: Dict[str, Any]
    ) -> bool:
        """Cache user session data."""
        key = CacheKeyBuilder.build_user_session_key(user_id)

        try:
            result = await self.cache_manager.cache.set(
                key, session_data, key_type=CacheKeyType.USER_SESSION
            )
            logger.debug("User session cached", user_id=user_id)
            return result
        except Exception as e:
            logger.error("Failed to cache user session", user_id=user_id, error=str(e))
            return False

    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user session data."""
        key = CacheKeyBuilder.build_user_session_key(user_id)

        try:
            session_data = await self.cache_manager.cache.get(key)
            if session_data:
                logger.debug("User session retrieved", user_id=user_id)
            return session_data
        except Exception as e:
            logger.error("Failed to get user session", user_id=user_id, error=str(e))
            return None

    async def invalidate_user_session(self, user_id: str) -> bool:
        """Invalidate user session cache."""
        key = CacheKeyBuilder.build_user_session_key(user_id)

        try:
            result = await self.cache_manager.cache.delete(key)
            logger.info("User session invalidated", user_id=user_id)
            return result
        except Exception as e:
            logger.error(
                "Failed to invalidate user session", user_id=user_id, error=str(e)
            )
            return False

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            health = await self.cache_manager.get_cache_health()

            # Get key counts by type
            key_counts = {}
            for cache_type in CacheKeyType:
                pattern = f"{cache_type.value}:*"
                keys = await self.cache_manager.cache.keys(pattern)
                key_counts[cache_type.value] = len(keys)

            return {
                "health": health,
                "key_counts": key_counts,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get cache statistics", error=str(e))
            return {
                "health": {"status": "unhealthy", "error": str(e)},
                "key_counts": {},
                "timestamp": datetime.utcnow().isoformat(),
            }


def cache_result(
    key_func: Callable[..., str],
    key_type: Optional[CacheKeyType] = None,
    ttl: Optional[int] = None,
):
    """
    Decorator to cache function results.

    Args:
        key_func: Function to generate cache key from function arguments
        key_type: Cache key type for TTL policy
        ttl: Custom TTL in seconds
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = key_func(*args, **kwargs)

            # Create cache service instance
            cache_service = CacheService()

            # Define fetch function
            async def fetch_func():
                return await func(*args, **kwargs)

            # Get or set cached result
            return await cache_service.get_or_set(cache_key, fetch_func, key_type, ttl)

        return wrapper

    return decorator


# Global cache service instance
cache_service = CacheService()
