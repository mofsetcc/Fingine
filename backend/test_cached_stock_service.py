"""
Test for cached stock service demonstrating cache integration.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.services.cached_stock_service import CachedStockService
from app.schemas.stock import StockSearchQuery


async def test_cached_stock_service():
    """Test cached stock service functionality."""
    print("🧪 Testing cached stock service...")
    
    # Mock database session
    mock_db = MagicMock()
    
    # Create service instance
    service = CachedStockService(mock_db)
    
    # Test cache key generation
    query1 = StockSearchQuery(query="Toyota", limit=10, include_inactive=False)
    query2 = StockSearchQuery(query="toyota", limit=10, include_inactive=False)  # Same but lowercase
    query3 = StockSearchQuery(query="Toyota", limit=20, include_inactive=False)  # Different limit
    
    key1 = service._generate_search_cache_key(query1)
    key2 = service._generate_search_cache_key(query2)
    key3 = service._generate_search_cache_key(query3)
    
    print(f"✅ Cache key 1: {key1}")
    print(f"✅ Cache key 2: {key2}")
    print(f"✅ Cache key 3: {key3}")
    
    # Keys 1 and 2 should be the same (case insensitive)
    assert key1 == key2, "Cache keys should be case insensitive"
    print("✅ Cache keys are case insensitive")
    
    # Key 3 should be different (different limit)
    assert key1 != key3, "Cache keys should differ for different parameters"
    print("✅ Cache keys differ for different parameters")
    
    # Test price data fetching
    mock_price = await service._fetch_single_price("7203")
    assert "current_price" in mock_price
    assert "change_percent" in mock_price
    assert "volume" in mock_price
    print(f"✅ Mock price data: {mock_price}")
    
    # Test multiple price fetching
    mock_prices = await service._fetch_multiple_prices(["7203", "6758"])
    assert len(mock_prices) == 2
    assert "7203" in mock_prices
    assert "6758" in mock_prices
    print(f"✅ Mock multiple prices: {len(mock_prices)} tickers")
    
    print("✅ Cached stock service tests completed")


def test_cache_key_generation():
    """Test cache key generation logic."""
    print("\n🧪 Testing cache key generation...")
    
    # Mock database session
    mock_db = MagicMock()
    service = CachedStockService(mock_db)
    
    # Test various search queries
    test_cases = [
        StockSearchQuery(query="Toyota", limit=10, include_inactive=False),
        StockSearchQuery(query="TOYOTA", limit=10, include_inactive=False),
        StockSearchQuery(query="toyota", limit=10, include_inactive=False),
        StockSearchQuery(query="Toyota", limit=20, include_inactive=False),
        StockSearchQuery(query="Toyota", limit=10, include_inactive=True),
        StockSearchQuery(query="7203", limit=10, include_inactive=False),
        StockSearchQuery(query="ソニー", limit=10, include_inactive=False),
    ]
    
    keys = []
    for i, query in enumerate(test_cases):
        key = service._generate_search_cache_key(query)
        keys.append(key)
        print(f"✅ Query {i+1}: '{query.query}' (limit={query.limit}, inactive={query.include_inactive}) -> {key}")
    
    # Check that case variations produce the same key
    assert keys[0] == keys[1] == keys[2], "Case variations should produce same key"
    print("✅ Case insensitive keys verified")
    
    # Check that different parameters produce different keys
    assert keys[0] != keys[3], "Different limits should produce different keys"
    assert keys[0] != keys[4], "Different include_inactive should produce different keys"
    print("✅ Parameter sensitivity verified")
    
    # Check that different queries produce different keys
    assert keys[0] != keys[5], "Different queries should produce different keys"
    assert keys[0] != keys[6], "Different languages should produce different keys"
    print("✅ Query uniqueness verified")


async def main():
    """Run all tests."""
    print("🚀 Starting Cached Stock Service Tests")
    print("=" * 50)
    
    try:
        await test_cached_stock_service()
        test_cache_key_generation()
        
        print("\n" + "=" * 50)
        print("🎉 All cached stock service tests passed!")
        
    except Exception as e:
        print(f"\n❌ Cached stock service tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())