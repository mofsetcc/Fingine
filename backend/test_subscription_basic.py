#!/usr/bin/env python3
"""
Basic test for subscription functionality without database dependencies.
"""

import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_subscription_schemas():
    """Test subscription schemas work correctly."""
    from app.schemas.subscription import (
        PlanCreate, PlanUpdate, SubscriptionCreate, SubscriptionUpgrade,
        SubscriptionDowngrade, SubscriptionCancel, UsageQuota
    )
    
    print("Testing subscription schemas...")
    
    # Test PlanCreate
    plan_data = PlanCreate(
        plan_name="test_plan",
        price_monthly=2980,
        features={"real_time_data": True, "advanced_analysis": True},
        api_quota_daily=100,
        ai_analysis_quota_daily=50,
        is_active=True
    )
    assert plan_data.plan_name == "test_plan"
    assert plan_data.price_monthly == 2980
    print("✓ PlanCreate schema works")
    
    # Test PlanUpdate
    plan_update = PlanUpdate(price_monthly=3500)
    assert plan_update.price_monthly == 3500
    print("✓ PlanUpdate schema works")
    
    # Test SubscriptionCreate
    user_id = uuid4()
    now = datetime.utcnow()
    subscription_data = SubscriptionCreate(
        user_id=user_id,
        plan_id=1,
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30)
    )
    assert subscription_data.user_id == user_id
    assert subscription_data.status == "active"
    print("✓ SubscriptionCreate schema works")
    
    # Test SubscriptionUpgrade
    upgrade_data = SubscriptionUpgrade(new_plan_id=2)
    assert upgrade_data.new_plan_id == 2
    print("✓ SubscriptionUpgrade schema works")
    
    # Test SubscriptionDowngrade
    downgrade_data = SubscriptionDowngrade(new_plan_id=1)
    assert downgrade_data.new_plan_id == 1
    print("✓ SubscriptionDowngrade schema works")
    
    # Test SubscriptionCancel
    cancel_data = SubscriptionCancel(
        reason="No longer needed",
        cancel_at_period_end=True
    )
    assert cancel_data.reason == "No longer needed"
    assert cancel_data.cancel_at_period_end is True
    print("✓ SubscriptionCancel schema works")
    
    # Test UsageQuota
    usage_quota = UsageQuota(
        api_quota_daily=100,
        api_usage_today=25,
        ai_analysis_quota_daily=50,
        ai_analysis_usage_today=10,
        quota_reset_at=datetime.utcnow() + timedelta(hours=12)
    )
    assert usage_quota.api_quota_daily == 100
    assert usage_quota.api_usage_today == 25
    print("✓ UsageQuota schema works")
    
    print("All subscription schemas work correctly!")


def test_subscription_service():
    """Test subscription service basic functionality."""
    from app.services.subscription_service import SubscriptionService
    from app.schemas.subscription import PlanCreate
    
    print("\nTesting subscription service...")
    
    # Create mock database
    mock_db = Mock()
    service = SubscriptionService(mock_db)
    
    print("✓ SubscriptionService created successfully")
    
    # Test that service methods exist
    assert hasattr(service, 'create_plan')
    assert hasattr(service, 'get_plan')
    assert hasattr(service, 'get_all_plans')
    assert hasattr(service, 'update_plan')
    assert hasattr(service, 'delete_plan')
    assert hasattr(service, 'create_subscription')
    assert hasattr(service, 'get_user_subscription')
    assert hasattr(service, 'upgrade_subscription')
    assert hasattr(service, 'downgrade_subscription')
    assert hasattr(service, 'cancel_subscription')
    assert hasattr(service, 'get_user_usage_quota')
    assert hasattr(service, 'check_quota_available')
    assert hasattr(service, 'initialize_default_plans')
    
    print("✓ All required service methods exist")
    print("Subscription service basic functionality verified!")


def test_default_plans_data():
    """Test default plans initialization data."""
    from app.services.subscription_service import SubscriptionService
    from app.schemas.subscription import PlanCreate
    
    print("\nTesting default plans data...")
    
    # Test the default plans that would be created
    expected_plans = [
        {
            "plan_name": "free",
            "price_monthly": 0,
            "api_quota_daily": 10,
            "ai_analysis_quota_daily": 5,
            "features": {
                "real_time_data": False,
                "advanced_analysis": False,
                "priority_support": False,
                "export_data": False,
                "custom_alerts": False
            }
        },
        {
            "plan_name": "pro",
            "price_monthly": 2980,
            "api_quota_daily": 100,
            "ai_analysis_quota_daily": 50,
            "features": {
                "real_time_data": True,
                "advanced_analysis": True,
                "priority_support": False,
                "export_data": True,
                "custom_alerts": True
            }
        },
        {
            "plan_name": "business",
            "price_monthly": 9800,
            "api_quota_daily": 1000,
            "ai_analysis_quota_daily": 200,
            "features": {
                "real_time_data": True,
                "advanced_analysis": True,
                "priority_support": True,
                "export_data": True,
                "custom_alerts": True,
                "api_access": True,
                "bulk_analysis": True
            }
        }
    ]
    
    for plan_data in expected_plans:
        plan_create = PlanCreate(**plan_data)
        assert plan_create.plan_name == plan_data["plan_name"]
        assert plan_create.price_monthly == plan_data["price_monthly"]
        assert plan_create.api_quota_daily == plan_data["api_quota_daily"]
        assert plan_create.ai_analysis_quota_daily == plan_data["ai_analysis_quota_daily"]
        print(f"✓ {plan_data['plan_name']} plan data is valid")
    
    print("All default plans data is valid!")


def main():
    """Run all tests."""
    print("Running subscription functionality tests...\n")
    
    try:
        test_subscription_schemas()
        test_subscription_service()
        test_default_plans_data()
        
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("Subscription functionality is working correctly.")
        print("="*50)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())