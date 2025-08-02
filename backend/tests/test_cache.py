"""
Tests for Redis caching layer.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import (
    RedisCache,
    CacheManager,
    CacheKeyType,
    CacheTTLPolicy,
    CacheKeyBuilder,
    cache_manager
)


class TestCacheKeyBuilder:
    """Test cache key building functionality."""
    
    def test_build_key(self):
        """Test basic key building."""
        key = CacheKeyBuilder.build_key(CacheKeyType.STOCK_PRICE, "7203", "2024-01-15")
        assert key == "stock_price:7203:2024-01-15"
    
    def test_build_stock_price_key(self):
        """Test stock price key building."""
        # With date
        key = CacheKeyBuilder.build_stock_price_key("7203", "2024-01-15")
        assert key == "stock_price:7203:2024-01-15"
        
        # Without date (latest)
        key = CacheKeyBuilder.build_stock_price_key("7203")
        assert key == "stock_price:7203:latest"
    
    def test_build_financial_data_key(self):
        """Test financial data key building."""
        key = CacheKeyBuilder.build_financial_data_key("7203", "quarterly", "Q3")
        assert key == "financial_data:7203:quarterly:Q3"
    
    def test_build_news_key(self):
        """Test news key building."""
        # With ticker
        key = CacheKeyBuilder.build_news_key("7203", "earnings")
        assert key == "news_data:7203:earnings"
        
        # Without ticker
        key = CacheKeyBuilder.build_news_key(category="market")
        assert key == "news_data:market"
    
    def test_build_ai_analysis_key(self):
        """Test AI analysis key building."""
        key = CacheKeyBuilder.build_ai_analysis_key("7203", "short_term")
        assert key == "ai_analysis:7203:short_term"
    
    def test_build_user_session_key(self):
        """Test user session key building."""
        key = CacheKeyBuilder.build_user_session_key("user123")
        assert key == "user_session:user123"
    
    def test_build_api_quota_key(self):
        """Test API quota key building."""
        key = CacheKeyBuilder.build_api_quota_key("user123", "daily")
        assert key == "api_quota:user123:daily"
    
    def test_build_market_data_key(self):
        """Test market data key building."""
        key = CacheKeyBuilder.build_market_data_key("nikkei", "indices")
        assert key == "market_data:nikkei:indices"


class TestCacheTTLPolicy:
    """Test TTL policy functionality."""
    
    def test_get_ttl_stock_price(self):
        """Test TTL for stock price data."""
        ttl = CacheTTLPolicy.get_ttl(CacheKeyType.STOCK_PRICE)
        assert ttl == 300  # 5 minutes
    
    def test_get_ttl_financial_data(self):
        """Test TTL for financial data."""
        ttl = CacheTTLPolicy.get_ttl(CacheKeyType.FINANCIAL_DATA)
        assert ttl == 86400  # 24 hours
    
    def test_get_ttl_news_data(self):
        """Test TTL for news data."""
        ttl = CacheTTLPolicy.get_ttl(CacheKeyType.NEWS_DATA)
        assert ttl == 3600  # 1 hour
    
    def test_get_ttl_ai_analysis(self):
        """Test TTL for AI analysis."""
        ttl = CacheTTLPolicy.get_ttl(CacheKeyType.AI_ANALYSIS)
        assert ttl == 21600  # 6 hours
    
    def test_get_ttl_default(self):
        """Test default TTL for unknown types."""
        # Create a mock enum value that's not in policies
        mock_type = MagicMock()
        mock_type.value = "unknown_type"
        ttl = CacheTTLPolicy.get_ttl(mock_type)
        assert ttl == 3600  # Default 1 hour


@pytest.fixture
async def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.ping.return_value = True
    client.set.return_value = True
    client.setex.return_value = True
    client.get.return_value = None
    client.delete.return_value = 1
    client.exists.return_value = True
    client.expire.return_value = True
    client.ttl.return_value = 300
    client.keys.return_value = []
    client.incr.return_value = 1
    client.info.return_value = {
        "connected_clients": 1,
        "used_memory": 1024,
        "used_memory_human": "1K",
        "keyspace_hits": 100,
        "keyspace_misses": 50,
        "total_commands_processed": 1000,
        "uptime_in_seconds": 3600
    }
    
    # Mock pipeline
    pipeline_mock = AsyncMock()
    pipeline_mock.incr.return_value = None
    pipeline_mock.expire.return_value = None
    pipeline_mock.execute.return_value = [5, True]
    pipeline_mock.__aenter__.return_value = pipeline_mock
    pipeline_mock.__aexit__.return_value = None
    client.pipeline.return_value = pipeline_mock
    
    return client


@pytest.fixture
async def redis_cache(mock_redis_client):
    """Create a Redis cache instance with mocked client."""
    cache = RedisCache("redis://localhost:6379")
    
    with patch('redis.asyncio.from_url', return_value=mock_redis_client):
        await cache.connect()
        cache._client = mock_redis_client
        cache._connected = True
        yield cache
        await cache.disconnect()


class TestRedisCache:
    """Test Redis cache functionality."""
    
    async def test_connect_success(self, mock_redis_client):
        """Test successful Redis connection."""
        cache = RedisCache("redis://localhost:6379")
        
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            await cache.connect()
            assert cache.is_connected
            mock_redis_client.ping.assert_called_once()
    
    async def test_connect_failure(self):
        """Test Redis connection failure."""
        cache = RedisCache("redis://localhost:6379")
        
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_from_url.return_value = mock_client
            
            with pytest.raises(Exception):
                await cache.connect()
            assert not cache.is_connected
    
    async def test_set_string_value(self, redis_cache, mock_redis_client):
        """Test setting string value."""
        result = await redis_cache.set("test_key", "test_value", ttl=300)
        assert result is True
        mock_redis_client.setex.assert_called_once()
    
    async def test_set_dict_value(self, redis_cache, mock_redis_client):
        """Test setting dictionary value."""
        test_data = {"key": "value", "number": 123}
        result = await redis_cache.set("test_key", test_data, ttl=300)
        assert result is True
        mock_redis_client.setex.assert_called_once()
    
    async def test_set_with_key_type(self, redis_cache, mock_redis_client):
        """Test setting value with key type for automatic TTL."""
        result = await redis_cache.set(
            "test_key", 
            "test_value", 
            key_type=CacheKeyType.STOCK_PRICE
        )
        assert result is True
        # Should use TTL from policy (300 seconds for stock price)
        mock_redis_client.setex.assert_called_once()
        args = mock_redis_client.setex.call_args[0]
        assert args[1] == 300  # TTL should be 300 seconds
    
    async def test_get_existing_value(self, redis_cache, mock_redis_client):
        """Test getting existing value."""
        test_data = {"key": "value"}
        mock_redis_client.get.return_value = json.dumps(test_data).encode('utf-8')
        
        result = await redis_cache.get("test_key")
        assert result == test_data
        mock_redis_client.get.assert_called_once_with("test_key")
    
    async def test_get_nonexistent_value(self, redis_cache, mock_redis_client):
        """Test getting non-existent value."""
        mock_redis_client.get.return_value = None
        
        result = await redis_cache.get("nonexistent_key")
        assert result is None
    
    async def test_delete_key(self, redis_cache, mock_redis_client):
        """Test deleting a key."""
        result = await redis_cache.delete("test_key")
        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")
    
    async def test_exists_key(self, redis_cache, mock_redis_client):
        """Test checking if key exists."""
        result = await redis_cache.exists("test_key")
        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")
    
    async def test_expire_key(self, redis_cache, mock_redis_client):
        """Test setting expiration for a key."""
        result = await redis_cache.expire("test_key", 300)
        assert result is True
        mock_redis_client.expire.assert_called_once_with("test_key", 300)
    
    async def test_ttl_key(self, redis_cache, mock_redis_client):
        """Test getting TTL for a key."""
        result = await redis_cache.ttl("test_key")
        assert result == 300
        mock_redis_client.ttl.assert_called_once_with("test_key")
    
    async def test_keys_pattern(self, redis_cache, mock_redis_client):
        """Test getting keys by pattern."""
        mock_redis_client.keys.return_value = [b"key1", b"key2"]
        
        result = await redis_cache.keys("test_*")
        assert result == ["key1", "key2"]
        mock_redis_client.keys.assert_called_once_with("test_*")
    
    async def test_flush_pattern(self, redis_cache, mock_redis_client):
        """Test flushing keys by pattern."""
        mock_redis_client.keys.return_value = [b"key1", b"key2"]
        mock_redis_client.delete.return_value = 2
        
        result = await redis_cache.flush_pattern("test_*")
        assert result == 2
        mock_redis_client.keys.assert_called_once_with("test_*")
        mock_redis_client.delete.assert_called_once_with("key1", "key2")
    
    async def test_increment(self, redis_cache, mock_redis_client):
        """Test incrementing a value."""
        result = await redis_cache.increment("counter", 1, ttl=300)
        assert result == 5  # From mock pipeline execute result
        
        # Verify pipeline was used
        mock_redis_client.pipeline.assert_called_once()
    
    async def test_get_cache_stats(self, redis_cache, mock_redis_client):
        """Test getting cache statistics."""
        stats = await redis_cache.get_cache_stats()
        
        assert stats["connected_clients"] == 1
        assert stats["used_memory"] == 1024
        assert stats["used_memory_human"] == "1K"
        assert stats["keyspace_hits"] == 100
        assert stats["keyspace_misses"] == 50
        mock_redis_client.info.assert_called_once()
    
    async def test_serialize_deserialize_data(self, redis_cache):
        """Test data serialization and deserialization."""
        # Test simple data types
        assert redis_cache._deserialize_data(redis_cache._serialize_data("test")) == "test"
        assert redis_cache._deserialize_data(redis_cache._serialize_data(123)) == 123
        assert redis_cache._deserialize_data(redis_cache._serialize_data(True)) == True
        
        # Test complex data types
        test_dict = {"key": "value", "number": 123, "list": [1, 2, 3]}
        serialized = redis_cache._serialize_data(test_dict)
        deserialized = redis_cache._deserialize_data(serialized)
        assert deserialized == test_dict
        
        test_list = [1, "two", {"three": 3}]
        serialized = redis_cache._serialize_data(test_list)
        deserialized = redis_cache._deserialize_data(serialized)
        assert deserialized == test_list


@pytest.fixture
async def cache_manager_instance(redis_cache):
    """Create a cache manager instance with mocked Redis cache."""
    return CacheManager(redis_cache)


class TestCacheManager:
    """Test cache manager functionality."""
    
    async def test_get_set_stock_price(self, cache_manager_instance, mock_redis_client):
        """Test getting and setting stock price data."""
        # Test setting
        price_data = {
            "ticker": "7203",
            "open": 2500.0,
            "high": 2550.0,
            "low": 2480.0,
            "close": 2520.0,
            "volume": 1000000
        }
        
        result = await cache_manager_instance.set_stock_price("7203", price_data)
        assert result is True
        
        # Test getting
        mock_redis_client.get.return_value = json.dumps(price_data).encode('utf-8')
        retrieved_data = await cache_manager_instance.get_stock_price("7203")
        assert retrieved_data == price_data
    
    async def test_get_set_financial_data(self, cache_manager_instance, mock_redis_client):
        """Test getting and setting financial data."""
        financial_data = {
            "ticker": "7203",
            "revenue": 30000000000,
            "operating_income": 2500000000,
            "net_income": 2000000000
        }
        
        result = await cache_manager_instance.set_financial_data(
            "7203", "quarterly", "Q3", financial_data
        )
        assert result is True
        
        # Test getting
        mock_redis_client.get.return_value = json.dumps(financial_data).encode('utf-8')
        retrieved_data = await cache_manager_instance.get_financial_data(
            "7203", "quarterly", "Q3"
        )
        assert retrieved_data == financial_data
    
    async def test_get_set_news_data(self, cache_manager_instance, mock_redis_client):
        """Test getting and setting news data."""
        news_data = [
            {
                "headline": "Toyota reports strong Q3 earnings",
                "sentiment": "positive",
                "published_at": "2024-01-15T10:00:00Z"
            }
        ]
        
        result = await cache_manager_instance.set_news_data(news_data, "7203", "earnings")
        assert result is True
        
        # Test getting
        mock_redis_client.get.return_value = json.dumps(news_data).encode('utf-8')
        retrieved_data = await cache_manager_instance.get_news_data("7203", "earnings")
        assert retrieved_data == news_data
    
    async def test_get_set_ai_analysis(self, cache_manager_instance, mock_redis_client):
        """Test getting and setting AI analysis data."""
        analysis_data = {
            "ticker": "7203",
            "analysis_type": "short_term",
            "rating": "Bullish",
            "confidence": 0.85,
            "key_factors": ["Strong earnings", "Positive sentiment"],
            "generated_at": "2024-01-15T10:00:00Z"
        }
        
        result = await cache_manager_instance.set_ai_analysis(
            "7203", "short_term", analysis_data
        )
        assert result is True
        
        # Test getting
        mock_redis_client.get.return_value = json.dumps(analysis_data).encode('utf-8')
        retrieved_data = await cache_manager_instance.get_ai_analysis("7203", "short_term")
        assert retrieved_data == analysis_data
    
    async def test_invalidate_stock_cache(self, cache_manager_instance, mock_redis_client):
        """Test invalidating all cache entries for a stock."""
        # Mock keys method to return some keys
        mock_redis_client.keys.side_effect = [
            [b"stock_price:7203:latest"],  # First pattern
            [b"financial_data:7203:quarterly:Q3"],  # Second pattern
            [],  # Third pattern (no keys)
            [b"ai_analysis:7203:short_term"]  # Fourth pattern
        ]
        mock_redis_client.delete.return_value = 1
        
        result = await cache_manager_instance.invalidate_stock_cache("7203")
        assert result == 3  # Total deleted keys
        
        # Verify all patterns were checked
        assert mock_redis_client.keys.call_count == 4
    
    async def test_get_cache_health_healthy(self, cache_manager_instance, mock_redis_client):
        """Test getting cache health when healthy."""
        health = await cache_manager_instance.get_cache_health()
        
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["hit_rate_percent"] == 66.67  # 100/(100+50) * 100
        assert health["memory_usage"] == "1K"
        assert health["total_commands"] == 1000
        assert health["uptime_seconds"] == 3600
        assert health["connected_clients"] == 1
    
    async def test_get_cache_health_unhealthy(self, mock_redis_client):
        """Test getting cache health when unhealthy."""
        cache = RedisCache("redis://localhost:6379")
        cache._connected = False
        cache_manager_instance = CacheManager(cache)
        
        health = await cache_manager_instance.get_cache_health()
        
        assert health["status"] == "unhealthy"
        assert health["connected"] is False


class TestCacheIntegration:
    """Integration tests for cache functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_manager_global_instance(self):
        """Test that global cache manager instance is available."""
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)
    
    async def test_cache_error_handling(self, redis_cache, mock_redis_client):
        """Test cache error handling doesn't break application."""
        # Simulate Redis error
        mock_redis_client.get.side_effect = Exception("Redis connection lost")
        
        # Should return None instead of raising exception
        result = await redis_cache.get("test_key")
        assert result is None
        
        # Should return False instead of raising exception
        result = await redis_cache.set("test_key", "value")
        assert result is False
    
    async def test_cache_ttl_policies_applied(self, redis_cache, mock_redis_client):
        """Test that TTL policies are correctly applied."""
        # Test stock price TTL (5 minutes = 300 seconds)
        await redis_cache.set("test", "value", key_type=CacheKeyType.STOCK_PRICE)
        args = mock_redis_client.setex.call_args[0]
        assert args[1] == 300
        
        # Test financial data TTL (24 hours = 86400 seconds)
        await redis_cache.set("test", "value", key_type=CacheKeyType.FINANCIAL_DATA)
        args = mock_redis_client.setex.call_args[0]
        assert args[1] == 86400
        
        # Test news data TTL (1 hour = 3600 seconds)
        await redis_cache.set("test", "value", key_type=CacheKeyType.NEWS_DATA)
        args = mock_redis_client.setex.call_args[0]
        assert args[1] == 3600