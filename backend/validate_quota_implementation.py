#!/usr/bin/env python3
"""
Simple validation script to check quota implementation without database dependencies.
"""

import sys
from unittest.mock import Mock

def test_quota_middleware_helpers():
    """Test quota middleware helper functions."""
    print("🔧 Testing Quota Middleware Helpers")
    print("=" * 50)
    
    try:
        # Import the helper functions directly
        sys.path.append('.')
        from app.core.quota_middleware import _should_enforce_quota, _get_quota_type
        
        # Test should_enforce_quota
        print("1️⃣ Testing quota enforcement detection...")
        
        # Test enforced endpoints
        request = Mock()
        request.url.path = "/api/v1/stocks/search"
        request.method = "GET"
        assert _should_enforce_quota(request) is True
        
        request.url.path = "/api/v1/analysis/generate"
        request.method = "POST"
        assert _should_enforce_quota(request) is True
        
        request.url.path = "/api/v1/stocks/7203"
        request.method = "GET"
        assert _should_enforce_quota(request) is True
        
        # Test non-enforced endpoints
        request.url.path = "/api/v1/auth/login"
        request.method = "POST"
        assert _should_enforce_quota(request) is False
        
        request.url.path = "/api/v1/subscription/plans"
        request.method = "GET"
        assert _should_enforce_quota(request) is False
        
        print("   ✅ Quota enforcement detection works")
        
        # Test quota type detection
        print("2️⃣ Testing quota type detection...")
        
        request.url.path = "/api/v1/analysis/generate"
        assert _get_quota_type(request) == "ai_analysis"
        
        request.url.path = "/api/v1/stocks/search"
        assert _get_quota_type(request) == "api"
        
        request.url.path = "/api/v1/news/stock/7203"
        assert _get_quota_type(request) == "api"
        
        print("   ✅ Quota type detection works")
        
        print("\n🎉 All middleware helper tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quota_schemas():
    """Test quota-related schemas."""
    print("\n📋 Testing Quota Schemas")
    print("=" * 50)
    
    try:
        from app.schemas.subscription import UsageQuota, QuotaUsageSummary, DailyUsage, QuotaCheckResult
        from datetime import datetime, timezone
        
        # Test UsageQuota schema
        print("1️⃣ Testing UsageQuota schema...")
        usage_quota = UsageQuota(
            api_quota_daily=100,
            api_usage_today=25,
            ai_analysis_quota_daily=50,
            ai_analysis_usage_today=10,
            quota_reset_at=datetime.now(timezone.utc)
        )
        assert usage_quota.api_quota_daily == 100
        assert usage_quota.api_usage_today == 25
        print("   ✅ UsageQuota schema works")
        
        # Test DailyUsage schema
        print("2️⃣ Testing DailyUsage schema...")
        daily_usage = DailyUsage(
            date="2024-01-01",
            api_calls=50,
            ai_analysis_calls=10,
            avg_response_time_ms=120.5,
            total_cost_usd=0.025
        )
        assert daily_usage.api_calls == 50
        assert daily_usage.ai_analysis_calls == 10
        print("   ✅ DailyUsage schema works")
        
        # Test QuotaCheckResult schema
        print("3️⃣ Testing QuotaCheckResult schema...")
        quota_check = QuotaCheckResult(
            has_quota=True,
            quota_info={
                "quota_type": "api",
                "usage": 25,
                "limit": 100,
                "remaining": 75
            }
        )
        assert quota_check.has_quota is True
        assert quota_check.quota_info["quota_type"] == "api"
        print("   ✅ QuotaCheckResult schema works")
        
        print("\n🎉 All schema tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quota_service_structure():
    """Test quota service structure without database."""
    print("\n🔧 Testing Quota Service Structure")
    print("=" * 50)
    
    try:
        from app.services.quota_service import QuotaService
        from unittest.mock import Mock
        
        # Create mock database
        mock_db = Mock()
        
        # Create quota service instance
        quota_service = QuotaService(mock_db)
        
        # Check that service has required methods
        required_methods = [
            'get_user_quotas',
            'get_user_usage_today',
            'get_usage_quota',
            'check_quota_available',
            'record_api_usage',
            'get_quota_usage_summary'
        ]
        
        print("1️⃣ Checking required methods...")
        for method_name in required_methods:
            assert hasattr(quota_service, method_name), f"Missing method: {method_name}"
            method = getattr(quota_service, method_name)
            assert callable(method), f"Method {method_name} is not callable"
        
        print("   ✅ All required methods present")
        
        # Check that service has subscription service
        print("2️⃣ Checking service dependencies...")
        assert hasattr(quota_service, 'subscription_service')
        assert hasattr(quota_service, 'db')
        print("   ✅ Service dependencies correct")
        
        print("\n🎉 Quota service structure test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Service structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints_structure():
    """Test that quota API endpoints are properly structured."""
    print("\n🌐 Testing API Endpoints Structure")
    print("=" * 50)
    
    try:
        # Check that quota endpoints exist in subscription API
        with open('app/api/v1/subscription.py', 'r') as f:
            content = f.read()
        
        required_endpoints = [
            '@router.get("/quota/check/{quota_type}"',
            '@router.get("/quota/summary"',
            '@router.post("/quota/record-usage"'
        ]
        
        print("1️⃣ Checking quota endpoints...")
        for endpoint in required_endpoints:
            assert endpoint in content, f"Missing endpoint: {endpoint}"
        
        print("   ✅ All quota endpoints present")
        
        # Check imports
        print("2️⃣ Checking imports...")
        required_imports = [
            'from app.services.quota_service import QuotaService',
            'QuotaUsageSummary',
            'QuotaCheckResult'
        ]
        
        for import_item in required_imports:
            assert import_item in content, f"Missing import: {import_item}"
        
        print("   ✅ All required imports present")
        
        print("\n🎉 API endpoints structure test passed!")
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend_component_structure():
    """Test that frontend quota component is properly structured."""
    print("\n⚛️  Testing Frontend Component Structure")
    print("=" * 50)
    
    try:
        # Check that QuotaUsageDisplay component exists
        with open('../frontend/src/components/QuotaUsageDisplay.tsx', 'r') as f:
            content = f.read()
        
        required_elements = [
            'interface UsageQuota',
            'interface QuotaUsageSummary',
            'export const QuotaUsageDisplay',
            'LinearProgress',
            'getUsagePercentage',
            'formatTimeUntilReset'
        ]
        
        print("1️⃣ Checking component structure...")
        for element in required_elements:
            assert element in content, f"Missing element: {element}"
        
        print("   ✅ Component structure correct")
        
        # Check API calls
        print("2️⃣ Checking API integration...")
        api_calls = [
            '/api/v1/subscription/usage',
            '/api/v1/subscription/quota/summary'
        ]
        
        for api_call in api_calls:
            assert api_call in content, f"Missing API call: {api_call}"
        
        print("   ✅ API integration present")
        
        print("\n🎉 Frontend component test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Frontend component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Quota Implementation Validation")
    print("=" * 60)
    
    tests = [
        test_quota_middleware_helpers,
        test_quota_schemas,
        test_quota_service_structure,
        test_api_endpoints_structure,
        test_frontend_component_structure
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All quota implementation validation tests passed!")
        sys.exit(0)
    else:
        print("❌ Some validation tests failed!")
        sys.exit(1)