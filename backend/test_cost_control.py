"""
Test cost control and budget management functionality.
"""

import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_cost_manager_budget_tracking():
    """Test daily and monthly budget tracking."""
    from app.services.cost_manager import CostManager
    
    # Mock database session
    mock_db = Mock()
    cost_manager = CostManager(mock_db)
    
    # Test budget initialization
    assert hasattr(cost_manager, 'daily_budget')
    assert hasattr(cost_manager, 'monthly_budget')
    assert hasattr(cost_manager, 'emergency_buffer')
    
    # Test cost estimation by analysis type
    short_cost = cost_manager.estimate_analysis_cost("short_term")
    mid_cost = cost_manager.estimate_analysis_cost("mid_term")
    long_cost = cost_manager.estimate_analysis_cost("long_term")
    comprehensive_cost = cost_manager.estimate_analysis_cost("comprehensive")
    
    # Verify costs increase with complexity
    assert short_cost < mid_cost < long_cost < comprehensive_cost
    
    # Test complexity multipliers
    low_cost = cost_manager.estimate_analysis_cost("short_term", "low")
    high_cost = cost_manager.estimate_analysis_cost("short_term", "high")
    assert low_cost < short_cost < high_cost
    
    print("✓ Budget tracking and cost estimation works")

def test_intelligent_caching():
    """Test intelligent caching based on market hours and data freshness."""
    from app.services.cost_manager import CostManager
    
    cost_manager = CostManager()
    
    # Test cache thresholds for different market conditions
    market_hours_time = datetime(2024, 1, 15, 10, 0, 0)  # Monday 10 AM
    after_hours_time = datetime(2024, 1, 15, 18, 0, 0)   # Monday 6 PM
    weekend_time = datetime(2024, 1, 13, 10, 0, 0)       # Saturday 10 AM
    
    # Test market hours threshold
    threshold = cost_manager._get_cache_threshold(market_hours_time)
    assert threshold == 300  # 5 minutes during market hours
    
    # Test after hours threshold
    threshold = cost_manager._get_cache_threshold(after_hours_time)
    assert threshold == 1800  # 30 minutes after hours
    
    # Test weekend threshold
    threshold = cost_manager._get_cache_threshold(weekend_time)
    assert threshold == 3600  # 1 hour on weekends
    
    # Test high-cost analysis threshold
    threshold = cost_manager._get_cache_threshold(market_hours_time, 0.02)  # High cost
    assert threshold == 300  # Should be min of market hours (300) and high cost (900)
    
    print("✓ Intelligent caching based on market conditions works")

async def test_budget_enforcement():
    """Test budget enforcement and cost control."""
    from app.services.cost_manager import CostManager
    
    # Mock database session
    mock_db = Mock()
    cost_manager = CostManager(mock_db)
    
    # Mock daily usage query to return high usage
    mock_db.query.return_value.filter.return_value.scalar.return_value = 95.0  # $95 used
    cost_manager.daily_budget = 100.0  # $100 daily budget
    
    # Test that small cost is allowed
    can_afford_small = await cost_manager.can_afford(2.0)  # $2 request
    assert can_afford_small == True
    
    # Test that large cost is rejected
    can_afford_large = await cost_manager.can_afford(10.0)  # $10 request would exceed budget
    assert can_afford_large == False
    
    print("✓ Budget enforcement works correctly")

async def test_cache_policy():
    """Test cache policy based on cost and time."""
    from app.services.cost_manager import CostManager
    
    cost_manager = CostManager()
    
    # Test recent analysis should use cache
    recent_time = datetime.now() - timedelta(minutes=2)
    should_cache = await cost_manager.should_use_cache("7203", recent_time)
    assert should_cache == True
    
    # Test old analysis should not use cache
    old_time = datetime.now() - timedelta(hours=2)
    should_cache = await cost_manager.should_use_cache("7203", old_time)
    assert should_cache == False
    
    print("✓ Cache policy based on time works correctly")

def test_intelligent_cache_manager():
    """Test intelligent cache manager functionality."""
    from app.services.cost_manager import IntelligentCacheManager
    
    cache_manager = IntelligentCacheManager()
    
    # Test cache TTL calculation
    base_ttl = cache_manager.get_cache_ttl("stock_prices")
    assert base_ttl == 300  # 5 minutes for stock prices
    
    # Test TTL adjustment for high volatility
    high_vol_ttl = cache_manager.get_cache_ttl("stock_prices", {"volatility": "high"})
    assert high_vol_ttl == 150  # Half the base TTL
    
    # Test TTL adjustment for low volatility
    low_vol_ttl = cache_manager.get_cache_ttl("stock_prices", {"volatility": "low"})
    assert low_vol_ttl == 450  # 1.5x the base TTL
    
    # Test cache invalidation triggers
    should_invalidate = cache_manager.should_invalidate_cache(
        "analysis_data", 
        datetime.now(),
        ["earnings_announcement"]
    )
    assert should_invalidate == True
    
    should_not_invalidate = cache_manager.should_invalidate_cache(
        "analysis_data",
        datetime.now(),
        ["minor_news"]
    )
    assert should_not_invalidate == False
    
    print("✓ Intelligent cache manager works correctly")

async def test_usage_statistics():
    """Test usage statistics and budget alerts."""
    from app.services.cost_manager import CostManager
    
    # Mock database session
    mock_db = Mock()
    cost_manager = CostManager(mock_db)
    
    # Mock the _get_daily_usage and _get_monthly_usage methods directly
    with patch.object(cost_manager, '_get_daily_usage', new=AsyncMock(return_value=75.0)):
        with patch.object(cost_manager, '_get_monthly_usage', new=AsyncMock(return_value=1800.0)):
            
            cost_manager.daily_budget = 100.0
            cost_manager.monthly_budget = 2500.0
            
            # Test usage statistics
            stats = await cost_manager.get_usage_stats()
            
            assert stats["daily_usage"] == 75.0
            assert stats["daily_budget"] == 100.0
            assert stats["daily_remaining"] == 25.0
            assert stats["daily_usage_percent"] == 75.0
            
            assert stats["monthly_usage"] == 1800.0
            assert stats["monthly_budget"] == 2500.0
            assert stats["monthly_remaining"] == 700.0
            assert stats["monthly_usage_percent"] == 72.0
            
            # Test budget alerts
            alerts = await cost_manager.get_budget_alerts()
            
            # Should have warning alert for daily usage (75% used)
            assert len(alerts) > 0
            warning_alert = next((a for a in alerts if a["type"] == "warning"), None)
            assert warning_alert is not None
            assert "75%" in warning_alert["message"]
    
    print("✓ Usage statistics and budget alerts work correctly")

def test_cost_estimation_accuracy():
    """Test cost estimation accuracy for different scenarios."""
    from app.services.cost_manager import CostManager
    
    cost_manager = CostManager()
    
    # Test base costs
    base_costs = {
        "short_term": 0.005,
        "mid_term": 0.008,
        "long_term": 0.012,
        "comprehensive": 0.020
    }
    
    for analysis_type, expected_base in base_costs.items():
        estimated = cost_manager.estimate_analysis_cost(analysis_type, "medium")
        assert estimated == expected_base
    
    # Test complexity multipliers
    complexity_multipliers = {
        "low": 0.7,
        "medium": 1.0,
        "high": 1.5,
        "very_high": 2.0
    }
    
    base_cost = cost_manager.estimate_analysis_cost("short_term", "medium")
    
    for complexity, multiplier in complexity_multipliers.items():
        estimated = cost_manager.estimate_analysis_cost("short_term", complexity)
        expected = base_cost * multiplier
        assert abs(estimated - expected) < 0.0001
    
    print("✓ Cost estimation accuracy is correct")

if __name__ == "__main__":
    print("Testing Cost Control and Budget Management...")
    
    import asyncio
    
    async def run_async_tests():
        await test_budget_enforcement()
        await test_cache_policy()
        await test_usage_statistics()
    
    try:
        test_cost_manager_budget_tracking()
        test_intelligent_caching()
        test_intelligent_cache_manager()
        test_cost_estimation_accuracy()
        
        # Run async tests
        asyncio.run(run_async_tests())
        
        print("\n✅ All cost control tests passed! Budget management is working correctly.")
        print("\nImplemented cost control features:")
        print("- ✓ Daily and monthly budget tracking")
        print("- ✓ Intelligent caching based on market hours and data freshness")
        print("- ✓ Cost estimation for LLM API calls")
        print("- ✓ Budget enforcement and cost control")
        print("- ✓ Usage statistics and budget alerts")
        print("- ✓ Cache policy management")
        print("- ✓ Market-aware cache thresholds")
        print("- ✓ Emergency buffer protection")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()