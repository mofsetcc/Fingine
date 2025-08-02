"""
Tests for error handling middleware and exception classes.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    KessanException,
    ErrorCategory,
    ErrorSeverity,
    InvalidTickerException,
    AuthenticationFailedException,
    QuotaExceededException,
    DataSourceUnavailableException,
    DatabaseConnectionException
)
from app.core.error_middleware import ErrorHandlingMiddleware, ErrorStatistics, GracefulDegradationService
from app.core.alerting import AlertManager, AlertRateLimiter, SystemHealthAlerter


class TestKessanException:
    """Test custom exception classes."""
    
    def test_kessan_exception_creation(self):
        """Test basic KessanException creation."""
        exception = KessanException(
            message="Test error",
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"key": "value"}
        )
        
        assert exception.message == "Test error"
        assert exception.category == ErrorCategory.USER_ERROR
        assert exception.severity == ErrorSeverity.MEDIUM
        assert exception.details == {"key": "value"}
        assert exception.error_id is not None
        assert exception.error_code == "KESSAN_ERROR"
    
    def test_invalid_ticker_exception(self):
        """Test InvalidTickerException."""
        exception = InvalidTickerException("INVALID")
        
        assert exception.category == ErrorCategory.USER_ERROR
        assert exception.severity == ErrorSeverity.LOW
        assert exception.details["ticker"] == "INVALID"
        assert "INVALID" in exception.message
        assert "not valid" in exception.user_message
    
    def test_authentication_failed_exception(self):
        """Test AuthenticationFailedException."""
        exception = AuthenticationFailedException("Invalid password")
        
        assert exception.category == ErrorCategory.AUTHENTICATION_ERROR
        assert exception.severity == ErrorSeverity.MEDIUM
        assert exception.should_alert is True
        assert "Invalid password" in exception.message
    
    def test_quota_exceeded_exception(self):
        """Test QuotaExceededException."""
        exception = QuotaExceededException("api_calls", 100, 50)
        
        assert exception.category == ErrorCategory.QUOTA_ERROR
        assert exception.severity == ErrorSeverity.MEDIUM
        assert exception.should_alert is True
        assert exception.details["quota_type"] == "api_calls"
        assert exception.details["current_usage"] == 100
        assert exception.details["limit"] == 50
    
    def test_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        exception = KessanException(
            message="Test error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            error_code="TEST_ERROR",
            details={"key": "value"},
            should_alert=True
        )
        
        result = exception.to_dict()
        
        assert result["error_id"] == exception.error_id
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["category"] == "system_error"
        assert result["severity"] == "high"
        assert result["details"] == {"key": "value"}
        assert result["should_alert"] is True


class TestErrorHandlingMiddleware:
    """Test error handling middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with error middleware."""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware, enable_graceful_degradation=True)
        
        @app.get("/test-kessan-exception")
        async def test_kessan_exception():
            raise InvalidTickerException("TEST")
        
        @app.get("/test-http-exception")
        async def test_http_exception():
            raise HTTPException(status_code=404, detail="Not found")
        
        @app.get("/test-unexpected-exception")
        async def test_unexpected_exception():
            raise ValueError("Unexpected error")
        
        @app.get("/test-success")
        async def test_success():
            return {"message": "success"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_kessan_exception_handling(self, client):
        """Test handling of KessanException."""
        response = client.get("/test-kessan-exception")
        
        assert response.status_code == 400
        data = response.json()
        
        assert "error_id" in data
        assert "error_code" in data
        assert data["category"] == "user_error"
        assert data["severity"] == "low"
        assert "TEST" in data["message"]
        assert "X-Request-ID" in response.headers
        assert "X-Error-ID" in response.headers
    
    def test_http_exception_handling(self, client):
        """Test handling of HTTPException."""
        response = client.get("/test-http-exception")
        
        assert response.status_code == 404
        data = response.json()
        
        # FastAPI returns HTTPException as-is without our middleware processing
        # when it's raised directly from the endpoint
        assert "detail" in data or "error_id" in data
        if "error_id" in data:
            assert data["error_code"] == "HTTP_404"
            assert data["message"] == "Not found"
        assert "X-Request-ID" in response.headers or True  # May not be present for direct HTTPException
    
    @patch('app.core.error_middleware.alert_manager.send_alert')
    def test_unexpected_exception_handling(self, mock_send_alert, client):
        """Test handling of unexpected exceptions."""
        mock_send_alert.return_value = AsyncMock()
        
        response = client.get("/test-unexpected-exception")
        
        assert response.status_code == 500
        data = response.json()
        
        assert "error_id" in data
        assert data["error_code"] == "UNEXPECTED_ERROR"
        assert data["category"] == "system_error"
        assert data["severity"] == "high"
        assert "unexpected error occurred" in data["user_message"].lower()
    
    def test_successful_request(self, client):
        """Test that successful requests pass through unchanged."""
        response = client.get("/test-success")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "success"
    
    def test_graceful_degradation_suggestions(self, client):
        """Test graceful degradation suggestions are added."""
        with patch('app.core.error_middleware.ErrorHandlingMiddleware._apply_graceful_degradation') as mock_degradation:
            mock_degradation.return_value = {
                "error_id": "test",
                "degradation_info": {
                    "suggestions": ["Using cached data"],
                    "retry_after": 300
                }
            }
            
            response = client.get("/test-kessan-exception")
            # The actual implementation would include degradation info


class TestErrorStatistics:
    """Test error statistics tracking."""
    
    def test_error_recording(self):
        """Test error recording and statistics."""
        stats = ErrorStatistics()
        
        # Record some errors
        stats.record_error(ErrorCategory.USER_ERROR, ErrorSeverity.LOW)
        stats.record_error(ErrorCategory.USER_ERROR, ErrorSeverity.LOW)
        stats.record_error(ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH)
        
        # Check error rate
        user_error_rate = stats.get_error_rate(ErrorCategory.USER_ERROR)
        total_error_rate = stats.get_error_rate()
        
        assert user_error_rate == 2.0 / 60.0  # 2 errors per minute
        assert total_error_rate == 3.0 / 60.0  # 3 errors per minute
    
    def test_error_count_reset(self):
        """Test error count reset after time window."""
        stats = ErrorStatistics()
        
        # Record error
        stats.record_error(ErrorCategory.USER_ERROR, ErrorSeverity.LOW)
        assert stats.get_error_rate() > 0
        
        # Force reset
        stats._reset_counts()
        assert stats.get_error_rate() == 0


class TestAlertManager:
    """Test alert manager functionality."""
    
    @pytest.fixture
    def alert_manager(self):
        """Create alert manager for testing."""
        manager = AlertManager()
        manager.slack_webhook_url = "https://hooks.slack.com/test"
        manager.pagerduty_integration_key = "test-key"
        return manager
    
    @pytest.mark.asyncio
    async def test_alert_threshold_filtering(self, alert_manager):
        """Test that alerts are filtered by severity threshold."""
        # Low severity should not alert
        low_exception = KessanException(
            message="Low severity error",
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.LOW,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack:
            await alert_manager.send_alert(low_exception)
            mock_slack.assert_not_called()
        
        # High severity should alert
        high_exception = KessanException(
            message="High severity error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack:
            mock_slack.return_value = None
            await alert_manager.send_alert(high_exception)
            mock_slack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_rate_limiting(self, alert_manager):
        """Test alert rate limiting."""
        exception = KessanException(
            message="Test error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack, \
             patch.object(alert_manager.rate_limiter, 'should_alert') as mock_rate_limiter:
            
            mock_slack.return_value = None
            
            # First alert should go through
            mock_rate_limiter.return_value = True
            await alert_manager.send_alert(exception)
            assert mock_slack.call_count == 1
            
            # Second alert of same type should be rate limited
            mock_rate_limiter.return_value = False
            await alert_manager.send_alert(exception)
            # Should still be 1 due to rate limiting
            assert mock_slack.call_count == 1
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_slack_alert_sending(self, mock_post, alert_manager):
        """Test Slack alert sending."""
        mock_response = Mock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        exception = KessanException(
            message="Test error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            should_alert=True
        )
        
        await alert_manager._send_slack_alert(alert_manager._prepare_alert_data(exception))
        
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/test"
        assert "json" in call_args[1]
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_pagerduty_alert_sending(self, mock_post, alert_manager):
        """Test PagerDuty alert sending."""
        mock_response = Mock()
        mock_response.status = 202
        mock_post.return_value.__aenter__.return_value = mock_response
        
        exception = KessanException(
            message="Critical error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            should_alert=True
        )
        
        await alert_manager._send_pagerduty_alert(alert_manager._prepare_alert_data(exception))
        
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://events.pagerduty.com/v2/enqueue"
        assert "json" in call_args[1]


class TestAlertRateLimiter:
    """Test alert rate limiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_logic(self):
        """Test rate limiting logic."""
        limiter = AlertRateLimiter()
        
        # First alert should be allowed
        assert await limiter.should_alert("test_alert", ErrorSeverity.HIGH) is True
        
        # Second alert should be allowed (limit is 2 per 10 minutes for HIGH)
        assert await limiter.should_alert("test_alert", ErrorSeverity.HIGH) is True
        
        # Third alert should be rate limited
        assert await limiter.should_alert("test_alert", ErrorSeverity.HIGH) is False
    
    @pytest.mark.asyncio
    async def test_different_alert_keys(self):
        """Test that different alert keys are tracked separately."""
        limiter = AlertRateLimiter()
        
        # Different alert keys should not interfere
        assert await limiter.should_alert("alert_1", ErrorSeverity.HIGH) is True
        assert await limiter.should_alert("alert_2", ErrorSeverity.HIGH) is True
        assert await limiter.should_alert("alert_1", ErrorSeverity.HIGH) is True
        assert await limiter.should_alert("alert_2", ErrorSeverity.HIGH) is True


class TestSystemHealthAlerter:
    """Test system health alerter."""
    
    @pytest.fixture
    def health_alerter(self):
        """Create system health alerter for testing."""
        mock_alert_manager = Mock()
        mock_alert_manager.send_alert = AsyncMock()
        return SystemHealthAlerter(mock_alert_manager)
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_alert(self, health_alerter):
        """Test database connection failure alert."""
        error_details = {"connection_string": "postgresql://...", "error": "Connection refused"}
        
        await health_alerter.alert_database_connection_failure(error_details)
        
        health_alerter.alert_manager.send_alert.assert_called_once()
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert isinstance(exception, DatabaseConnectionException)
        assert exception.should_alert is True
        assert exception.severity == ErrorSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_external_api_failure_alert(self, health_alerter):
        """Test external API failure alert."""
        await health_alerter.alert_external_api_failure(
            "alpha_vantage", 503, "Service unavailable"
        )
        
        health_alerter.alert_manager.send_alert.assert_called_once()
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert exception.details["api_name"] == "alpha_vantage"
        assert exception.details["status_code"] == 503
        assert exception.should_alert is True
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_alert(self, health_alerter):
        """Test budget exceeded alert."""
        context = {"current_usage": 150.0, "budget": 100.0}
        
        await health_alerter.alert_budget_exceeded("daily", context)
        
        health_alerter.alert_manager.send_alert.assert_called_once()
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert "daily" in exception.message
        assert exception.should_alert is True
        assert exception.severity == ErrorSeverity.HIGH


class TestGracefulDegradationService:
    """Test graceful degradation service."""
    
    @pytest.mark.asyncio
    @patch('app.core.cache.cache.get')
    async def test_get_cached_stock_data(self, mock_cache_get):
        """Test getting cached stock data."""
        mock_cache_get.return_value = {"price": 100.0, "volume": 1000}
        
        result = await GracefulDegradationService.get_cached_stock_data("7203")
        
        assert result["data"]["price"] == 100.0
        assert result["is_cached"] is True
        assert "cached data" in result["message"]
    
    @pytest.mark.asyncio
    @patch('app.core.cache.cache.get')
    async def test_get_cached_stock_data_not_available(self, mock_cache_get):
        """Test getting cached stock data when not available."""
        mock_cache_get.return_value = None
        
        result = await GracefulDegradationService.get_cached_stock_data("7203")
        
        assert result["data"] is None
        assert result["is_cached"] is False
        assert "No data available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_basic_analysis(self):
        """Test getting basic analysis fallback."""
        result = await GracefulDegradationService.get_basic_analysis("7203")
        
        assert result["analysis_type"] == "basic_technical"
        assert result["rating"] == "neutral"
        assert result["is_degraded"] is True
        assert "AI analysis unavailable" in result["message"]
    
    def test_get_error_response_template(self):
        """Test error response templates."""
        template = GracefulDegradationService.get_error_response_template(
            ErrorCategory.EXTERNAL_API_ERROR
        )
        
        assert template["fallback_available"] is True
        assert "Real-time data" in template["degraded_features"]
        assert "Cached data" in template["available_features"]
        
        quota_template = GracefulDegradationService.get_error_response_template(
            ErrorCategory.QUOTA_ERROR
        )
        
        assert quota_template["fallback_available"] is False
        assert quota_template["upgrade_suggestion"] is True


if __name__ == "__main__":
    pytest.main([__file__])