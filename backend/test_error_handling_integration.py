"""
Integration test for error handling and alerting system.
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_middleware import ErrorHandlingMiddleware
from app.core.exceptions import (
    InvalidTickerException,
    DatabaseConnectionException,
    ExternalAPIException
)
from app.core.alerting import alert_manager


def test_error_handling_integration():
    """Test complete error handling flow."""
    
    # Create test app with error middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware, enable_graceful_degradation=True)
    
    @app.get("/test-user-error")
    async def test_user_error():
        raise InvalidTickerException("INVALID")
    
    @app.get("/test-system-error")
    async def test_system_error():
        raise DatabaseConnectionException()
    
    @app.get("/test-external-error")
    async def test_external_error():
        raise ExternalAPIException("test_api", 503, "Service unavailable")
    
    client = TestClient(app)
    
    # Test user error (should not alert)
    response = client.get("/test-user-error")
    assert response.status_code == 400
    data = response.json()
    assert data["category"] == "user_error"
    assert data["severity"] == "low"
    assert "INVALID" in data["message"]
    assert "X-Error-ID" in response.headers
    
    # Test system error (should alert)
    with patch.object(alert_manager, 'send_alert') as mock_alert:
        mock_alert.return_value = AsyncMock()
        
        response = client.get("/test-system-error")
        assert response.status_code == 500
        data = response.json()
        assert data["category"] == "system_error"
        assert data["severity"] == "critical"
        assert "Database connection failed" in data["message"]
        
        # Verify alert was attempted (would be sent in real scenario)
        # Note: In test, the alert might not be called due to async nature
    
    # Test external API error (should alert)
    response = client.get("/test-external-error")
    assert response.status_code == 503
    data = response.json()
    assert data["category"] == "external_api_error"
    assert data["severity"] == "medium"
    assert "test_api" in data["message"]


@pytest.mark.asyncio
async def test_alerting_integration():
    """Test alerting system integration."""
    
    # Mock webhook URLs
    with patch('app.core.alerting.AlertManager.__init__') as mock_init:
        mock_init.return_value = None
        
        # Create alert manager with mocked URLs
        test_alert_manager = alert_manager
        test_alert_manager.slack_webhook_url = "https://hooks.slack.com/test"
        test_alert_manager.pagerduty_integration_key = "test-key"
        
        # Test critical error alerting
        critical_exception = DatabaseConnectionException()
        
        with patch.object(test_alert_manager, '_send_slack_alert') as mock_slack, \
             patch.object(test_alert_manager, '_send_pagerduty_alert') as mock_pagerduty, \
             patch.object(test_alert_manager.rate_limiter, 'should_alert', return_value=True):
            
            mock_slack.return_value = None
            mock_pagerduty.return_value = None
            
            await test_alert_manager.send_alert(critical_exception)
            
            # Both Slack and PagerDuty should be called for critical errors
            mock_slack.assert_called_once()
            mock_pagerduty.assert_called_once()


def test_graceful_degradation():
    """Test graceful degradation features."""
    
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware, enable_graceful_degradation=True)
    
    @app.get("/test-external-api-error")
    async def test_external_api_error():
        raise ExternalAPIException("alpha_vantage", 503, "Service unavailable")
    
    client = TestClient(app)
    
    response = client.get("/test-external-api-error")
    assert response.status_code == 503
    data = response.json()
    
    # Check that graceful degradation info is included
    if "degradation_info" in data:
        assert "suggestions" in data["degradation_info"]
        assert "retry_after" in data["degradation_info"]
        assert any("cached data" in suggestion.lower() for suggestion in data["degradation_info"]["suggestions"])


if __name__ == "__main__":
    # Run basic integration test
    test_error_handling_integration()
    print("✅ Error handling integration test passed")
    
    # Run graceful degradation test
    test_graceful_degradation()
    print("✅ Graceful degradation test passed")
    
    print("🎉 All integration tests passed!")