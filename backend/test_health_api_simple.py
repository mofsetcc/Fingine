#!/usr/bin/env python3
"""
Simple test for health API endpoints.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

# Import the app
from app.main import app

def test_basic_health_endpoints():
    """Test basic health endpoints that don't require authentication."""
    print("🔍 Testing basic health endpoints...")
    
    client = TestClient(app)
    
    try:
        # Test basic health check
        print("   Testing /api/v1/health...")
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "kessan-backend"
        print("   ✅ Basic health check passed")
        
        # Test liveness check
        print("   Testing /api/v1/health/live...")
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        print("   ✅ Liveness check passed")
        
        # Test readiness check (will fail due to database, but should handle gracefully)
        print("   Testing /api/v1/health/ready...")
        response = client.get("/api/v1/health/ready")
        # Should return 503 due to database not being available
        assert response.status_code == 503
        print("   ✅ Readiness check handled database failure correctly")
        
        # Test system health check
        print("   Testing /api/v1/health/system...")
        response = client.get("/api/v1/health/system")
        # Should return 503 due to unhealthy services
        assert response.status_code == 503
        print("   ✅ System health check handled failures correctly")
        
        # Test data sources health
        print("   Testing /api/v1/health/data-sources...")
        response = client.get("/api/v1/health/data-sources")
        assert response.status_code == 200  # Should be healthy since no adapters registered
        data = response.json()
        assert data["status"] == "healthy"
        print("   ✅ Data sources health check passed")
        
        # Test external APIs health
        print("   Testing /api/v1/health/external-apis...")
        response = client.get("/api/v1/health/external-apis")
        assert response.status_code == 200
        data = response.json()
        # Should be degraded due to Gemini API not configured properly
        assert data["status"] in ["degraded", "unhealthy"]
        print("   ✅ External APIs health check passed")
        
        # Test system resources health
        print("   Testing /api/v1/health/resources...")
        response = client.get("/api/v1/health/resources")
        assert response.status_code == 200
        data = response.json()
        # Should be unknown if psutil not available, or healthy/degraded if available
        assert data["status"] in ["healthy", "degraded", "unhealthy", "unknown"]
        print("   ✅ System resources health check passed")
        
        print("\n✅ All basic health endpoint tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Health endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_authenticated_endpoints_mock():
    """Test authenticated endpoints with mocked authentication."""
    print("\n🔐 Testing authenticated health endpoints with mocked auth...")
    
    client = TestClient(app)
    
    try:
        # Mock the authentication dependency
        with patch('app.api.v1.health.get_current_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = "test_user"
            mock_auth.return_value = mock_user
            
            # Test dashboard endpoint
            print("   Testing /api/v1/health/dashboard...")
            response = client.get(
                "/api/v1/health/dashboard",
                headers={"Authorization": "Bearer test_token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "current_status" in data
            assert "monitoring" in data
            print("   ✅ Dashboard endpoint passed")
            
            # Test alerts endpoint
            print("   Testing /api/v1/health/alerts...")
            response = client.get(
                "/api/v1/health/alerts",
                headers={"Authorization": "Bearer test_token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            assert "count" in data
            print("   ✅ Alerts endpoint passed")
            
            # Test thresholds endpoint
            print("   Testing /api/v1/health/thresholds...")
            response = client.get(
                "/api/v1/health/thresholds",
                headers={"Authorization": "Bearer test_token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "thresholds" in data
            print("   ✅ Thresholds endpoint passed")
        
        print("\n✅ All authenticated endpoint tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Authenticated endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all API tests."""
    print("🚀 Starting health API tests...\n")
    
    # Test basic endpoints
    basic_success = test_basic_health_endpoints()
    
    # Test authenticated endpoints
    auth_success = test_authenticated_endpoints_mock()
    
    # Summary
    print("\n" + "="*50)
    if basic_success and auth_success:
        print("🎉 All API tests passed! Health API endpoints are working correctly.")
        return 0
    else:
        print("💥 Some API tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)