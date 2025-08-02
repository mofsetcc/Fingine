#!/usr/bin/env python3
"""
Test subscription models and database schema.
"""

import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_subscription_models():
    """Test subscription models."""
    from app.models.subscription import Plan, Subscription
    
    print("Testing subscription models...")
    
    # Test Plan model
    plan = Plan(
        plan_name="test_plan",
        price_monthly=2980,
        features={"real_time_data": True},
        api_quota_daily=100,
        ai_analysis_quota_daily=50,
        is_active=True
    )
    
    assert plan.plan_name == "test_plan"
    assert plan.price_monthly == 2980
    assert plan.features == {"real_time_data": True}
    assert plan.api_quota_daily == 100
    assert plan.ai_analysis_quota_daily == 50
    assert plan.is_active is True
    print("✓ Plan model works correctly")
    
    # Test Subscription model
    user_id = uuid4()
    now = datetime.utcnow()
    subscription = Subscription(
        user_id=user_id,
        plan_id=1,
        status="active",
        current_period_start=now.isoformat(),
        current_period_end=(now + timedelta(days=30)).isoformat()
    )
    
    assert subscription.user_id == user_id
    assert subscription.plan_id == 1
    assert subscription.status == "active"
    assert subscription.current_period_start == now.isoformat()
    print("✓ Subscription model works correctly")
    
    print("All subscription models work correctly!")


def test_model_relationships():
    """Test model relationships."""
    from app.models.subscription import Plan, Subscription
    
    print("\nTesting model relationships...")
    
    # Test that models have the expected relationships
    assert hasattr(Plan, 'subscriptions')
    assert hasattr(Subscription, 'plan')
    assert hasattr(Subscription, 'user')
    
    print("✓ Model relationships are properly defined")


def test_model_constraints():
    """Test model constraints."""
    from app.models.subscription import Subscription
    
    print("\nTesting model constraints...")
    
    # Test that Subscription model has the status constraint
    table_args = getattr(Subscription, '__table_args__', ())
    
    # Check if there's a check constraint for status
    has_status_constraint = False
    if isinstance(table_args, tuple):
        for arg in table_args:
            if hasattr(arg, 'name') and arg.name == 'check_subscription_status':
                has_status_constraint = True
                break
    
    assert has_status_constraint, "Status check constraint should be defined"
    print("✓ Status check constraint is properly defined")


def main():
    """Run all model tests."""
    print("Running subscription model tests...\n")
    
    try:
        test_subscription_models()
        test_model_relationships()
        test_model_constraints()
        
        print("\n" + "="*50)
        print("🎉 ALL MODEL TESTS PASSED!")
        print("Subscription models are working correctly.")
        print("="*50)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ MODEL TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())