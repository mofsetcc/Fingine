"""
Unit tests for Redis caching layer (without requiring Redis server).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.cache import (
    CacheKeyType,
    CacheTTLPolicy,
    CacheKeyBuilder,
    RedisCache
)


def test_cache_key_builder():
    """Test cache key building functionality."""
    print("🧪 Testing cache key building...")
    
    # Test basic key building
    key = CacheKeyBuilder.build_key(CacheKeyType.STOCK_PRICE, "7203", "2024-01-15")
    assert key == "stock_price:7203:2024-01-15"
    print(f"✅ Basic key: {key}")
    
    # Test stock price key
    key = CacheKeyBuilder.build_stock_price_key("7203", "2024-01-15")
    assert key == "stock_price:7203:2024-01-15"
    print(f"✅ Stock price key: {key}")
    
    # Test stock price key without date
    key = CacheKeyBuilder.build_stock_price_key("7203")
    assert key == "stock_price:7203:latest"
    print(f"✅ Stock price key (latest): {key}")
    
    # Test financial data key
    key = CacheKeyBuilder.build_financial_data_key("7203", "quarterly", "Q3")
    assert key == "financial_data:7203:quarterly:Q3"
    print(f"✅ Financial data key: {key}")
    
    # Test AI analysis key
    key = CacheKeyBuilder.build_ai_analysis_key("7203", "short_term")
    assert key == "ai_analysis:7203:short_term"
    print(f"✅ AI analysis key: {key}")
    
    # Test news key
    key = CacheKeyBuilder.build_news_key("7203", "earnings")
    assert key == "news_data:7203:earnings"
    print(f"✅ News key: {key}")
    
    # Test user session key
    key = CacheKeyBuilder.build_user_session_key("user123")
    assert key == "user_session:user123"
    print(f"✅ User session key: {key}")
    
    # Test API quota key
    key = CacheKeyBuilder.build_api_quota_key("user123", "daily")
    assert key == "api_quota:user123:daily"
    print(f"✅ API quota key: {key}")
    
    # Test market data key
    key = CacheKeyBuilder.build_market_data_key("nikkei", "indices")
    assert key == "market_data:nikkei:indices"
    print(f"✅ Market data key: {key}")


def test_cache_ttl_policies():
    """Test TTL policy functionality."""
    print("\n🧪 Testing TTL policies...")
    
    # Test stock price TTL (5 minutes = 300 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.STOCK_PRICE)
    assert ttl == 300
    print(f"✅ Stock price TTL: {ttl} seconds")
    
    # Test financial data TTL (24 hours = 86400 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.FINANCIAL_DATA)
    assert ttl == 86400
    print(f"✅ Financial data TTL: {ttl} seconds")
    
    # Test news data TTL (1 hour = 3600 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.NEWS_DATA)
    assert ttl == 3600
    print(f"✅ News data TTL: {ttl} seconds")
    
    # Test AI analysis TTL (6 hours = 21600 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.AI_ANALYSIS)
    assert ttl == 21600
    print(f"✅ AI analysis TTL: {ttl} seconds")
    
    # Test user session TTL (30 minutes = 1800 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.USER_SESSION)
    assert ttl == 1800
    print(f"✅ User session TTL: {ttl} seconds")
    
    # Test API quota TTL (24 hours = 86400 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.API_QUOTA)
    assert ttl == 86400
    print(f"✅ API quota TTL: {ttl} seconds")
    
    # Test market data TTL (5 minutes = 300 seconds)
    ttl = CacheTTLPolicy.get_ttl(CacheKeyType.MARKET_DATA)
    assert ttl == 300
    print(f"✅ Market data TTL: {ttl} seconds")


def test_redis_cache_serialization():
    """Test data serialization and deserialization."""
    print("\n🧪 Testing data serialization...")
    
    cache = RedisCache("redis://localhost:6379")
    
    # Test string serialization
    data = "test_string"
    serialized = cache._serialize_data(data)
    deserialized = cache._deserialize_data(serialized)
    assert deserialized == data
    print(f"✅ String serialization: {data}")
    
    # Test integer serialization
    data = 12345
    serialized = cache._serialize_data(data)
    deserialized = cache._deserialize_data(serialized)
    assert deserialized == data
    print(f"✅ Integer serialization: {data}")
    
    # Test boolean serialization
    data = True
    serialized = cache._serialize_data(data)
    deserialized = cache._deserialize_data(serialized)
    assert deserialized == data
    print(f"✅ Boolean serialization: {data}")
    
    # Test dictionary serialization
    data = {
        "ticker": "7203",
        "price": 2500.0,
        "volume": 1000000,
        "metadata": {
            "source": "alpha_vantage",
            "timestamp": "2024-01-15T10:00:00Z"
        }
    }
    serialized = cache._serialize_data(data)
    deserialized = cache._deserialize_data(serialized)
    assert deserialized == data
    print(f"✅ Dictionary serialization: {len(data)} keys")
    
    # Test list serialization
    data = [
        {"ticker": "7203", "price": 2500.0},
        {"ticker": "6758", "price": 15000.0},
        {"ticker": "9984", "price": 3000.0}
    ]
    serialized = cache._serialize_data(data)
    deserialized = cache._deserialize_data(serialized)
    assert deserialized == data
    print(f"✅ List serialization: {len(data)} items")


def test_cache_key_patterns():
    """Test cache key patterns for different data types."""
    print("\n🧪 Testing cache key patterns...")
    
    # Test stock-related keys
    stock_keys = [
        CacheKeyBuilder.build_stock_price_key("7203"),
        CacheKeyBuilder.build_stock_price_key("7203", "2024-01-15"),
        CacheKeyBuilder.build_financial_data_key("7203", "quarterly", "Q3"),
        CacheKeyBuilder.build_ai_analysis_key("7203", "short_term"),
        CacheKeyBuilder.build_news_key("7203", "earnings")
    ]
    
    for key in stock_keys:
        assert "7203" in key
        print(f"✅ Stock key contains ticker: {key}")
    
    # Test user-related keys
    user_keys = [
        CacheKeyBuilder.build_user_session_key("user123"),
        CacheKeyBuilder.build_api_quota_key("user123", "daily")
    ]
    
    for key in user_keys:
        assert "user123" in key
        print(f"✅ User key contains user ID: {key}")
    
    # Test market data keys
    market_key = CacheKeyBuilder.build_market_data_key("nikkei", "indices")
    assert "nikkei" in market_key and "indices" in market_key
    print(f"✅ Market key contains market and type: {market_key}")


def test_cache_configuration():
    """Test cache configuration and initialization."""
    print("\n🧪 Testing cache configuration...")
    
    # Test default Redis URL
    cache = RedisCache()
    assert cache.redis_url is not None
    print(f"✅ Default Redis URL configured")
    
    # Test custom Redis URL
    custom_url = "redis://custom-host:6380"
    cache = RedisCache(custom_url)
    assert cache.redis_url == custom_url
    print(f"✅ Custom Redis URL: {custom_url}")
    
    # Test initial connection state
    assert not cache.is_connected
    print(f"✅ Initial connection state: {cache.is_connected}")


def test_cache_key_type_enum():
    """Test cache key type enumeration."""
    print("\n🧪 Testing cache key type enum...")
    
    # Test all cache key types exist
    expected_types = [
        "stock_price",
        "financial_data", 
        "news_data",
        "ai_analysis",
        "user_session",
        "api_quota",
        "market_data"
    ]
    
    for expected_type in expected_types:
        # Find enum member with this value
        found = False
        for cache_type in CacheKeyType:
            if cache_type.value == expected_type:
                found = True
                break
        assert found, f"Cache type {expected_type} not found"
        print(f"✅ Cache type exists: {expected_type}")


def main():
    """Run all unit tests."""
    print("🚀 Starting Redis Cache Unit Tests")
    print("=" * 50)
    
    try:
        test_cache_key_builder()
        test_cache_ttl_policies()
        test_redis_cache_serialization()
        test_cache_key_patterns()
        test_cache_configuration()
        test_cache_key_type_enum()
        
        print("\n" + "=" * 50)
        print("🎉 All cache unit tests passed!")
        
    except Exception as e:
        print(f"\n❌ Cache unit tests failed: {e}")
        raise


if __name__ == "__main__":
    main()