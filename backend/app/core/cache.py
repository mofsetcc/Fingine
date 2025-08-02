"""
Redis caching layer implementation.
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import redis.asyncio as redis
from redis.asyncio import Redis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class CacheKeyType(Enum):
    """Cache key types with their TTL policies."""
    STOCK_PRICE = "stock_price"
    FINANCIAL_DATA = "financial_data"
    NEWS_DATA = "news_data"
    AI_ANALYSIS = "ai_analysis"
    USER_SESSION = "user_session"
    API_QUOTA = "api_quota"
    MARKET_DATA = "market_data"


class CacheTTLPolicy:
    """TTL policies for different data types."""
    
    POLICIES = {
        CacheKeyType.STOCK_PRICE: 300,        # 5 minutes
        CacheKeyType.FINANCIAL_DATA: 86400,   # 24 hours
        CacheKeyType.NEWS_DATA: 3600,         # 1 hour
        CacheKeyType.AI_ANALYSIS: 21600,      # 6 hours
        CacheKeyType.USER_SESSION: 1800,      # 30 minutes
        CacheKeyType.API_QUOTA: 86400,        # 24 hours
        CacheKeyType.MARKET_DATA: 300,        # 5 minutes
    }
    
    @classmethod
    def get_ttl(cls, key_type: CacheKeyType) -> int:
        """Get TTL for a specific cache key type."""
        return cls.POLICIES.get(key_type, 3600)  # Default 1 hour


class CacheKeyBuilder:
    """Build standardized cache keys."""
    
    @staticmethod
    def build_key(key_type: CacheKeyType, *args: str) -> str:
        """Build a cache key with consistent format."""
        parts = [key_type.value] + list(args)
        return ":".join(parts)
    
    @staticmethod
    def build_stock_price_key(ticker: str, date: str = None) -> str:
        """Build cache key for stock price data."""
        if date:
            return CacheKeyBuilder.build_key(CacheKeyType.STOCK_PRICE, ticker, date)
        return CacheKeyBuilder.build_key(CacheKeyType.STOCK_PRICE, ticker, "latest")
    
    @staticmethod
    def build_financial_data_key(ticker: str, report_type: str, period: str) -> str:
        """Build cache key for financial data."""
        return CacheKeyBuilder.build_key(
            CacheKeyType.FINANCIAL_DATA, ticker, report_type, period
        )
    
    @staticmethod
    def build_news_key(ticker: str = None, category: str = "general") -> str:
        """Build cache key for news data."""
        if ticker:
            return CacheKeyBuilder.build_key(CacheKeyType.NEWS_DATA, ticker, category)
        return CacheKeyBuilder.build_key(CacheKeyType.NEWS_DATA, category)
    
    @staticmethod
    def build_ai_analysis_key(ticker: str, analysis_type: str) -> str:
        """Build cache key for AI analysis."""
        return CacheKeyBuilder.build_key(
            CacheKeyType.AI_ANALYSIS, ticker, analysis_type
        )
    
    @staticmethod
    def build_user_session_key(user_id: str) -> str:
        """Build cache key for user session."""
        return CacheKeyBuilder.build_key(CacheKeyType.USER_SESSION, user_id)
    
    @staticmethod
    def build_api_quota_key(user_id: str, quota_type: str) -> str:
        """Build cache key for API quota tracking."""
        return CacheKeyBuilder.build_key(CacheKeyType.API_QUOTA, user_id, quota_type)
    
    @staticmethod
    def build_market_data_key(market: str, data_type: str) -> str:
        """Build cache key for market data."""
        return CacheKeyBuilder.build_key(CacheKeyType.MARKET_DATA, market, data_type)


class RedisCache:
    """Redis caching layer with multi-layer support."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding manually
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis connection established", redis_url=self.redis_url)
            
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self._connected = False
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._client is not None
    
    @property
    def redis(self) -> Optional[Redis]:
        """Get the Redis client instance."""
        return self._client
    
    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active."""
        if not self.is_connected:
            await self.connect()
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage."""
        if isinstance(data, (str, int, float, bool)):
            return json.dumps(data).encode('utf-8')
        elif isinstance(data, (dict, list)):
            return json.dumps(data).encode('utf-8')
        else:
            # Use pickle for complex objects
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        key_type: Optional[CacheKeyType] = None
    ) -> bool:
        """Set a value in cache with optional TTL."""
        await self._ensure_connected()
        
        try:
            serialized_value = self._serialize_data(value)
            
            # Determine TTL
            if ttl is None and key_type:
                ttl = CacheTTLPolicy.get_ttl(key_type)
            
            if ttl:
                result = await self._client.setex(key, ttl, serialized_value)
            else:
                result = await self._client.set(key, serialized_value)
            
            logger.debug(
                "Cache set",
                key=key,
                ttl=ttl,
                success=bool(result)
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to set cache", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        await self._ensure_connected()
        
        try:
            data = await self._client.get(key)
            if data is None:
                logger.debug("Cache miss", key=key)
                return None
            
            result = self._deserialize_data(data)
            logger.debug("Cache hit", key=key)
            return result
            
        except Exception as e:
            logger.error("Failed to get cache", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        await self._ensure_connected()
        
        try:
            result = await self._client.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(result))
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to delete cache", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        await self._ensure_connected()
        
        try:
            result = await self._client.exists(key)
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to check cache existence", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key."""
        await self._ensure_connected()
        
        try:
            result = await self._client.expire(key, ttl)
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to set expiration", key=key, ttl=ttl, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        await self._ensure_connected()
        
        try:
            result = await self._client.ttl(key)
            return result
            
        except Exception as e:
            logger.error("Failed to get TTL", key=key, error=str(e))
            return -1
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching a pattern."""
        await self._ensure_connected()
        
        try:
            keys = await self._client.keys(pattern)
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
            
        except Exception as e:
            logger.error("Failed to get keys", pattern=pattern, error=str(e))
            return []
    
    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        await self._ensure_connected()
        
        try:
            keys = await self.keys(pattern)
            if keys:
                result = await self._client.delete(*keys)
                logger.info("Flushed cache pattern", pattern=pattern, count=result)
                return result
            return 0
            
        except Exception as e:
            logger.error("Failed to flush pattern", pattern=pattern, error=str(e))
            return 0
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a numeric value in cache."""
        await self._ensure_connected()
        
        try:
            # Use pipeline for atomic operation
            async with self._client.pipeline() as pipe:
                await pipe.incr(key, amount)
                if ttl:
                    await pipe.expire(key, ttl)
                results = await pipe.execute()
                
            return results[0]
            
        except Exception as e:
            logger.error("Failed to increment", key=key, error=str(e))
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        await self._ensure_connected()
        
        try:
            info = await self._client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {}


# Global cache instance
cache = RedisCache()


class CacheManager:
    """High-level cache management with business logic."""
    
    def __init__(self, cache_client: RedisCache = None):
        self.cache = cache_client or cache
    
    async def get_stock_price(self, ticker: str, date: str = None) -> Optional[Dict[str, Any]]:
        """Get cached stock price data."""
        key = CacheKeyBuilder.build_stock_price_key(ticker, date)
        return await self.cache.get(key)
    
    async def set_stock_price(
        self,
        ticker: str,
        price_data: Dict[str, Any],
        date: str = None
    ) -> bool:
        """Cache stock price data."""
        key = CacheKeyBuilder.build_stock_price_key(ticker, date)
        return await self.cache.set(key, price_data, key_type=CacheKeyType.STOCK_PRICE)
    
    async def get_financial_data(
        self,
        ticker: str,
        report_type: str,
        period: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached financial data."""
        key = CacheKeyBuilder.build_financial_data_key(ticker, report_type, period)
        return await self.cache.get(key)
    
    async def set_financial_data(
        self,
        ticker: str,
        report_type: str,
        period: str,
        financial_data: Dict[str, Any]
    ) -> bool:
        """Cache financial data."""
        key = CacheKeyBuilder.build_financial_data_key(ticker, report_type, period)
        return await self.cache.set(key, financial_data, key_type=CacheKeyType.FINANCIAL_DATA)
    
    async def get_news_data(
        self,
        ticker: str = None,
        category: str = "general"
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached news data."""
        key = CacheKeyBuilder.build_news_key(ticker, category)
        return await self.cache.get(key)
    
    async def set_news_data(
        self,
        news_data: List[Dict[str, Any]],
        ticker: str = None,
        category: str = "general"
    ) -> bool:
        """Cache news data."""
        key = CacheKeyBuilder.build_news_key(ticker, category)
        return await self.cache.set(key, news_data, key_type=CacheKeyType.NEWS_DATA)
    
    async def get_ai_analysis(
        self,
        ticker: str,
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached AI analysis."""
        key = CacheKeyBuilder.build_ai_analysis_key(ticker, analysis_type)
        return await self.cache.get(key)
    
    async def set_ai_analysis(
        self,
        ticker: str,
        analysis_type: str,
        analysis_data: Dict[str, Any]
    ) -> bool:
        """Cache AI analysis."""
        key = CacheKeyBuilder.build_ai_analysis_key(ticker, analysis_type)
        return await self.cache.set(key, analysis_data, key_type=CacheKeyType.AI_ANALYSIS)
    
    async def invalidate_stock_cache(self, ticker: str) -> int:
        """Invalidate all cache entries for a specific stock."""
        patterns = [
            f"stock_price:{ticker}:*",
            f"financial_data:{ticker}:*",
            f"news_data:{ticker}:*",
            f"ai_analysis:{ticker}:*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.flush_pattern(pattern)
            total_deleted += deleted
        
        logger.info("Invalidated stock cache", ticker=ticker, deleted_keys=total_deleted)
        return total_deleted
    
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health status."""
        try:
            stats = await self.cache.get_cache_stats()
            
            # Calculate hit rate
            hits = stats.get("keyspace_hits", 0)
            misses = stats.get("keyspace_misses", 0)
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "status": "healthy" if self.cache.is_connected else "unhealthy",
                "connected": self.cache.is_connected,
                "hit_rate_percent": round(hit_rate, 2),
                "memory_usage": stats.get("used_memory_human", "0B"),
                "total_commands": stats.get("total_commands_processed", 0),
                "uptime_seconds": stats.get("uptime_in_seconds", 0),
                "connected_clients": stats.get("connected_clients", 0)
            }
            
        except Exception as e:
            logger.error("Failed to get cache health", error=str(e))
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


# Global cache manager instance
cache_manager = CacheManager()