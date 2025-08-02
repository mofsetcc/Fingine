"""
Integration test for Redis caching layer.
"""

import asyncio
import json
from datetime import datetime

from app.core.cache import cache, cache_manager, CacheKeyType, CacheKeyBuilder
from app.services.cache_service import cache_service


async def test_basic_cache_operations():
    """Test basic cache operations."""
    print("🧪 Testing basic cache operations...")
    
    try:
        # Connect to cache
        await cache.connect()
        print("✅ Connected to Redis")
        
        # Test basic set/get
        test_key = "test:basic_operation"
        test_value = {"message": "Hello, Cache!", "timestamp": datetime.now().isoformat()}
        
        # Set value
        result = await cache.set(test_key, test_value, ttl=60)
        print(f"✅ Set operation: {result}")
        
        # Get value
        retrieved_value = await cache.get(test_key)
        print(f"✅ Get operation: {retrieved_value}")
        
        # Verify values match
        assert retrieved_value == test_value
        print("✅ Values match")
        
        # Test TTL
        ttl = await cache.ttl(test_key)
        print(f"✅ TTL: {ttl} seconds")
        assert ttl > 0 and ttl <= 60
        
        # Test exists
        exists = await cache.exists(test_key)
        print(f"✅ Key exists: {exists}")
        assert exists
        
        # Clean up
        await cache.delete(test_key)
        print("✅ Cleanup completed")
        
    except Exception as e:
        print(f"❌ Basic cache operations failed: {e}")
        raise


async def test_cache_key_building():
    """Test cache key building functionality."""
    print("\n🧪 Testing cache key building...")
    
    try:
        # Test stock price key
        stock_key = CacheKeyBuilder.build_stock_price_key("7203", "2024-01-15")
        expected_key = "stock_price:7203:2024-01-15"
        assert stock_key == expected_key
        print(f"✅ Stock price key: {stock_key}")
        
        # Test financial data key
        financial_key = CacheKeyBuilder.build_financial_data_key("7203", "quarterly", "Q3")
        expected_key = "financial_data:7203:quarterly:Q3"
        assert financial_key == expected_key
        print(f"✅ Financial data key: {financial_key}")
        
        # Test AI analysis key
        ai_key = CacheKeyBuilder.build_ai_analysis_key("7203", "short_term")
        expected_key = "ai_analysis:7203:short_term"
        assert ai_key == expected_key
        print(f"✅ AI analysis key: {ai_key}")
        
        # Test news key
        news_key = CacheKeyBuilder.build_news_key("7203", "earnings")
        expected_key = "news_data:7203:earnings"
        assert news_key == expected_key
        print(f"✅ News key: {news_key}")
        
    except Exception as e:
        print(f"❌ Cache key building failed: {e}")
        raise


async def test_cache_manager_operations():
    """Test cache manager high-level operations."""
    print("\n🧪 Testing cache manager operations...")
    
    try:
        # Test stock price caching
        stock_data = {
            "ticker": "7203",
            "open": 2500.0,
            "high": 2550.0,
            "low": 2480.0,
            "close": 2520.0,
            "volume": 1000000,
            "timestamp": datetime.now().isoformat()
        }
        
        # Set stock price
        result = await cache_manager.set_stock_price("7203", stock_data)
        print(f"✅ Set stock price: {result}")
        assert result
        
        # Get stock price
        retrieved_data = await cache_manager.get_stock_price("7203")
        print(f"✅ Get stock price: {retrieved_data is not None}")
        assert retrieved_data == stock_data
        
        # Test financial data caching
        financial_data = {
            "ticker": "7203",
            "revenue": 30000000000,
            "operating_income": 2500000000,
            "net_income": 2000000000,
            "fiscal_year": 2024,
            "period": "Q3"
        }
        
        # Set financial data
        result = await cache_manager.set_financial_data("7203", "quarterly", "Q3", financial_data)
        print(f"✅ Set financial data: {result}")
        assert result
        
        # Get financial data
        retrieved_data = await cache_manager.get_financial_data("7203", "quarterly", "Q3")
        print(f"✅ Get financial data: {retrieved_data is not None}")
        assert retrieved_data == financial_data
        
        # Test AI analysis caching
        analysis_data = {
            "ticker": "7203",
            "analysis_type": "short_term",
            "rating": "Bullish",
            "confidence": 0.85,
            "key_factors": ["Strong earnings", "Positive sentiment"],
            "generated_at": datetime.now().isoformat()
        }
        
        # Set AI analysis
        result = await cache_manager.set_ai_analysis("7203", "short_term", analysis_data)
        print(f"✅ Set AI analysis: {result}")
        assert result
        
        # Get AI analysis
        retrieved_data = await cache_manager.get_ai_analysis("7203", "short_term")
        print(f"✅ Get AI analysis: {retrieved_data is not None}")
        assert retrieved_data == analysis_data
        
        # Test cache invalidation
        deleted_count = await cache_manager.invalidate_stock_cache("7203")
        print(f"✅ Invalidated cache entries: {deleted_count}")
        
        # Verify data is gone
        retrieved_data = await cache_manager.get_stock_price("7203")
        assert retrieved_data is None
        print("✅ Cache invalidation verified")
        
    except Exception as e:
        print(f"❌ Cache manager operations failed: {e}")
        raise


async def test_cache_service_operations():
    """Test cache service functionality."""
    print("\n🧪 Testing cache service operations...")
    
    try:
        # Test get_or_set functionality
        call_count = 0
        
        async def mock_fetch_function():
            nonlocal call_count
            call_count += 1
            return {
                "data": "fetched_data",
                "call_count": call_count,
                "timestamp": datetime.now().isoformat()
            }
        
        # First call should fetch data
        result1 = await cache_service.get_or_set(
            "test:get_or_set",
            mock_fetch_function,
            CacheKeyType.STOCK_PRICE
        )
        print(f"✅ First call result: {result1['call_count']}")
        assert result1["call_count"] == 1
        
        # Second call should use cache
        result2 = await cache_service.get_or_set(
            "test:get_or_set",
            mock_fetch_function,
            CacheKeyType.STOCK_PRICE
        )
        print(f"✅ Second call result: {result2['call_count']}")
        assert result2["call_count"] == 1  # Should be same as first call (cached)
        
        # Test API quota tracking
        user_id = "test_user_123"
        
        # Track quota usage
        usage1 = await cache_service.track_api_quota(user_id, "daily")
        print(f"✅ First quota usage: {usage1}")
        assert usage1 == 1
        
        usage2 = await cache_service.track_api_quota(user_id, "daily")
        print(f"✅ Second quota usage: {usage2}")
        assert usage2 == 2
        
        # Get quota usage
        current_usage = await cache_service.get_api_quota_usage(user_id, "daily")
        print(f"✅ Current quota usage: {current_usage}")
        assert current_usage == 2
        
        # Reset quota
        reset_result = await cache_service.reset_api_quota(user_id, "daily")
        print(f"✅ Quota reset: {reset_result}")
        assert reset_result
        
        # Verify quota is reset
        usage_after_reset = await cache_service.get_api_quota_usage(user_id, "daily")
        print(f"✅ Usage after reset: {usage_after_reset}")
        assert usage_after_reset == 0
        
        # Clean up
        await cache.delete("test:get_or_set")
        
    except Exception as e:
        print(f"❌ Cache service operations failed: {e}")
        raise


async def test_cache_health_and_stats():
    """Test cache health and statistics."""
    print("\n🧪 Testing cache health and statistics...")
    
    try:
        # Get cache health
        health = await cache_manager.get_cache_health()
        print(f"✅ Cache health status: {health['status']}")
        print(f"✅ Cache connected: {health['connected']}")
        print(f"✅ Memory usage: {health.get('memory_usage', 'N/A')}")
        
        assert health["status"] == "healthy"
        assert health["connected"] is True
        
        # Get cache statistics
        stats = await cache_service.get_cache_statistics()
        print(f"✅ Cache statistics retrieved: {stats['health']['status']}")
        print(f"✅ Key counts: {stats['key_counts']}")
        
        assert "health" in stats
        assert "key_counts" in stats
        assert "timestamp" in stats
        
    except Exception as e:
        print(f"❌ Cache health and stats failed: {e}")
        raise


async def test_ttl_policies():
    """Test TTL policies for different cache types."""
    print("\n🧪 Testing TTL policies...")
    
    try:
        # Test stock price TTL (5 minutes = 300 seconds)
        await cache.set("test:stock_price", "test_data", key_type=CacheKeyType.STOCK_PRICE)
        ttl = await cache.ttl("test:stock_price")
        print(f"✅ Stock price TTL: {ttl} seconds (expected: 300)")
        assert 290 <= ttl <= 300  # Allow for small timing differences
        
        # Test financial data TTL (24 hours = 86400 seconds)
        await cache.set("test:financial", "test_data", key_type=CacheKeyType.FINANCIAL_DATA)
        ttl = await cache.ttl("test:financial")
        print(f"✅ Financial data TTL: {ttl} seconds (expected: 86400)")
        assert 86390 <= ttl <= 86400
        
        # Test news data TTL (1 hour = 3600 seconds)
        await cache.set("test:news", "test_data", key_type=CacheKeyType.NEWS_DATA)
        ttl = await cache.ttl("test:news")
        print(f"✅ News data TTL: {ttl} seconds (expected: 3600)")
        assert 3590 <= ttl <= 3600
        
        # Clean up
        await cache.delete("test:stock_price")
        await cache.delete("test:financial")
        await cache.delete("test:news")
        
    except Exception as e:
        print(f"❌ TTL policies test failed: {e}")
        raise


async def main():
    """Run all cache integration tests."""
    print("🚀 Starting Redis Cache Integration Tests")
    print("=" * 50)
    
    try:
        await test_basic_cache_operations()
        await test_cache_key_building()
        await test_cache_manager_operations()
        await test_cache_service_operations()
        await test_cache_health_and_stats()
        await test_ttl_policies()
        
        print("\n" + "=" * 50)
        print("🎉 All cache integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Cache integration tests failed: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            await cache.disconnect()
            print("✅ Cache connection closed")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())