"""
Tests for the alerting system.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.core.alerting import AlertManager, AlertRateLimiter, SystemHealthAlerter
from app.core.exceptions import (
    KessanException,
    ErrorCategory,
    ErrorSeverity,
    DatabaseConnectionException,
    ExternalAPIException,
    BudgetExceededException
)


class TestAlertManager:
    """Test AlertManager functionality."""
    
    @pytest.fixture
    def alert_manager(self):
        """Create AlertManager instance for testing."""
        manager = AlertManager()
        # Mock the webhook URLs for testing
        manager.slack_webhook_url = "https://hooks.slack.com/services/test/webhook"
        manager.pagerduty_integration_key = "test-integration-key"
        return manager
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test AlertManager initialization."""
        assert alert_manager.slack_webhook_url is not None
        assert alert_manager.pagerduty_integration_key is not None
        assert isinstance(alert_manager.rate_limiter, AlertRateLimiter)
        
        # Check alert thresholds
        assert alert_manager.alert_thresholds[ErrorSeverity.LOW] is False
        assert alert_manager.alert_thresholds[ErrorSeverity.MEDIUM] is False
        assert alert_manager.alert_thresholds[ErrorSeverity.HIGH] is True
        assert alert_manager.alert_thresholds[ErrorSeverity.CRITICAL] is True
    
    @pytest.mark.asyncio
    async def test_send_alert_should_not_alert_flag(self, alert_manager):
        """Test that alerts are not sent when should_alert is False."""
        exception = KessanException(
            message="Test error",
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.HIGH,
            should_alert=False  # Should not alert
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack:
            await alert_manager.send_alert(exception)
            mock_slack.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_alert_low_severity_threshold(self, alert_manager):
        """Test that low severity alerts are not sent."""
        exception = KessanException(
            message="Low severity error",
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.LOW,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack:
            await alert_manager.send_alert(exception)
            mock_slack.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_alert_high_severity(self, alert_manager):
        """Test that high severity alerts are sent."""
        exception = KessanException(
            message="High severity error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack, \
             patch.object(alert_manager.rate_limiter, 'should_alert', return_value=True):
            mock_slack.return_value = None
            
            await alert_manager.send_alert(exception)
            mock_slack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_alert_critical_severity_pagerduty(self, alert_manager):
        """Test that critical alerts are sent to both Slack and PagerDuty."""
        exception = KessanException(
            message="Critical error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack, \
             patch.object(alert_manager, '_send_pagerduty_alert') as mock_pagerduty, \
             patch.object(alert_manager.rate_limiter, 'should_alert', return_value=True):
            
            mock_slack.return_value = None
            mock_pagerduty.return_value = None
            
            await alert_manager.send_alert(exception)
            
            mock_slack.assert_called_once()
            mock_pagerduty.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_alert_rate_limited(self, alert_manager):
        """Test that rate-limited alerts are not sent."""
        exception = KessanException(
            message="Rate limited error",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            should_alert=True
        )
        
        with patch.object(alert_manager, '_send_slack_alert') as mock_slack, \
             patch.object(alert_manager.rate_limiter, 'should_alert', return_value=False):
            
            await alert_manager.send_alert(exception)
            mock_slack.assert_not_called()
    
    def test_prepare_alert_data(self, alert_manager):
        """Test alert data preparation."""
        exception = KessanException(
            message="Test error",
            category=ErrorCategory.EXTERNAL_API_ERROR,
            severity=ErrorSeverity.HIGH,
            error_code="TEST_ERROR",
            details={"api": "test_api"},
            should_alert=True
        )
        
        context = {"request_id": "test-request-id"}
        alert_data = alert_manager._prepare_alert_data(exception, context)
        
        assert alert_data["error_id"] == exception.error_id
        assert alert_data["error_code"] == "TEST_ERROR"
        assert alert_data["message"] == "Test error"
        assert alert_data["category"] == "external_api_error"
        assert alert_data["severity"] == "high"
        assert alert_data["service"] == "kessan-api"
        assert alert_data["details"] == {"api": "test_api"}
        assert alert_data["context"] == {"request_id": "test-request-id"}
        assert alert_data["exception_type"] == "KessanException"
        assert "timestamp" in alert_data
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_send_slack_alert_success(self, mock_post, alert_manager):
        """Test successful Slack alert sending."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        alert_data = {
            "error_id": "test-error-id",
            "error_code": "TEST_ERROR",
            "message": "Test error message",
            "category": "system_error",
            "severity": "high",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "test",
            "service": "kessan-api",
            "details": {"key": "value"},
            "context": {"request_id": "test-request"},
            "exception_type": "TestException"
        }
        
        await alert_manager._send_slack_alert(alert_data)
        
        # Verify the request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert call_args[0][0] == alert_manager.slack_webhook_url
        
        # Check payload structure
        payload = call_args[1]["json"]
        assert payload["username"] == "Kessan Alert Bot"
        assert payload["icon_emoji"] == ":warning:"
        assert len(payload["attachments"]) == 1
        
        attachment = payload["attachments"][0]
        assert attachment["color"] == "#ff0000"  # Red for high severity
        assert "HIGH Alert" in attachment["title"]
        assert attachment["text"] == "Test error message"
        
        # Check fields
        fields = {field["title"]: field["value"] for field in attachment["fields"]}
        assert fields["Error ID"] == "test-error-id"
        assert fields["Error Code"] == "TEST_ERROR"
        assert fields["Category"] == "system_error"
        assert fields["Environment"] == "test"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_send_slack_alert_failure(self, mock_post, alert_manager):
        """Test Slack alert sending failure handling."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        alert_data = {
            "error_id": "test-error-id",
            "error_code": "TEST_ERROR",
            "message": "Test error",
            "category": "system_error",
            "severity": "high",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "test",
            "service": "kessan-api",
            "details": {},
            "context": {},
            "exception_type": "TestException"
        }
        
        # Should not raise exception, just log error
        await alert_manager._send_slack_alert(alert_data)
        
        mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_send_pagerduty_alert_success(self, mock_post, alert_manager):
        """Test successful PagerDuty alert sending."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 202
        mock_post.return_value.__aenter__.return_value = mock_response
        
        alert_data = {
            "error_id": "test-error-id",
            "error_code": "TEST_ERROR",
            "message": "Critical error message",
            "category": "system_error",
            "severity": "critical",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "production",
            "service": "kessan-api",
            "details": {"key": "value"},
            "context": {"request_id": "test-request"},
            "exception_type": "TestException"
        }
        
        await alert_manager._send_pagerduty_alert(alert_data)
        
        # Verify the request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert call_args[0][0] == "https://events.pagerduty.com/v2/enqueue"
        
        # Check payload structure
        payload = call_args[1]["json"]
        assert payload["routing_key"] == alert_manager.pagerduty_integration_key
        assert payload["event_action"] == "trigger"
        assert payload["dedup_key"] == f"kessan-TEST_ERROR-test-error-id"
        
        # Check payload details
        assert payload["payload"]["summary"] == "[CRITICAL] Critical error message"
        assert payload["payload"]["source"] == "kessan-api"
        assert payload["payload"]["severity"] == "critical"
        assert payload["payload"]["component"] == "system_error"
        assert payload["payload"]["group"] == "kessan-api"
        assert payload["payload"]["class"] == "TestException"
        
        custom_details = payload["payload"]["custom_details"]
        assert custom_details["error_id"] == "test-error-id"
        assert custom_details["error_code"] == "TEST_ERROR"
        assert custom_details["environment"] == "production"
    
    def test_map_severity_to_pagerduty(self, alert_manager):
        """Test severity mapping to PagerDuty."""
        assert alert_manager._map_severity_to_pagerduty("low") == "info"
        assert alert_manager._map_severity_to_pagerduty("medium") == "warning"
        assert alert_manager._map_severity_to_pagerduty("high") == "error"
        assert alert_manager._map_severity_to_pagerduty("critical") == "critical"
        assert alert_manager._map_severity_to_pagerduty("unknown") == "error"


class TestAlertRateLimiter:
    """Test AlertRateLimiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create AlertRateLimiter instance for testing."""
        return AlertRateLimiter()
    
    @pytest.mark.asyncio
    async def test_should_alert_first_time(self, rate_limiter):
        """Test that first alert is always allowed."""
        result = await rate_limiter.should_alert("test_alert", ErrorSeverity.HIGH)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_alert_within_limit(self, rate_limiter):
        """Test alerts within rate limit are allowed."""
        # HIGH severity allows 2 alerts per 10 minutes
        assert await rate_limiter.should_alert("test_alert", ErrorSeverity.HIGH) is True
        assert await rate_limiter.should_alert("test_alert", ErrorSeverity.HIGH) is True
    
    @pytest.mark.asyncio
    async def test_should_alert_exceeds_limit(self, rate_limiter):
        """Test that alerts exceeding rate limit are blocked."""
        # HIGH severity allows 2 alerts per 10 minutes
        assert await rate_limiter.should_alert("test_alert", ErrorSeverity.HIGH) is True
        assert await rate_limiter.should_alert("test_alert", ErrorSeverity.HIGH) is True
        assert await rate_limiter.should_alert("test_alert", ErrorSeverity.HIGH) is False
    
    @pytest.mark.asyncio
    async def test_should_alert_different_keys(self, rate_limiter):
        """Test that different alert keys are tracked separately."""
        # Different keys should not interfere with each other
        assert await rate_limiter.should_alert("alert_1", ErrorSeverity.HIGH) is True
        assert await rate_limiter.should_alert("alert_2", ErrorSeverity.HIGH) is True
        assert await rate_limiter.should_alert("alert_1", ErrorSeverity.HIGH) is True
        assert await rate_limiter.should_alert("alert_2", ErrorSeverity.HIGH) is True
    
    @pytest.mark.asyncio
    async def test_should_alert_different_severities(self, rate_limiter):
        """Test rate limits for different severities."""
        # CRITICAL allows 1 per 5 minutes
        assert await rate_limiter.should_alert("critical_alert", ErrorSeverity.CRITICAL) is True
        assert await rate_limiter.should_alert("critical_alert", ErrorSeverity.CRITICAL) is False
        
        # MEDIUM allows 3 per 5 minutes
        assert await rate_limiter.should_alert("medium_alert", ErrorSeverity.MEDIUM) is True
        assert await rate_limiter.should_alert("medium_alert", ErrorSeverity.MEDIUM) is True
        assert await rate_limiter.should_alert("medium_alert", ErrorSeverity.MEDIUM) is True
        assert await rate_limiter.should_alert("medium_alert", ErrorSeverity.MEDIUM) is False
    
    def test_clean_old_entries(self, rate_limiter):
        """Test cleaning of old entries."""
        # Add some old entries
        current_time = datetime.now(timezone.utc).timestamp()
        old_time = current_time - 3600  # 1 hour ago
        
        rate_limiter.alert_counts["old_alert"] = [old_time]
        rate_limiter.alert_counts["recent_alert"] = [current_time - 60]  # 1 minute ago
        
        # Clean old entries
        rate_limiter._clean_old_entries(current_time)
        
        # Old alert should be removed, recent should remain
        assert "old_alert" not in rate_limiter.alert_counts
        assert "recent_alert" in rate_limiter.alert_counts


class TestSystemHealthAlerter:
    """Test SystemHealthAlerter functionality."""
    
    @pytest.fixture
    def health_alerter(self):
        """Create SystemHealthAlerter instance for testing."""
        mock_alert_manager = Mock()
        mock_alert_manager.send_alert = AsyncMock()
        return SystemHealthAlerter(mock_alert_manager)
    
    @pytest.mark.asyncio
    async def test_alert_database_connection_failure(self, health_alerter):
        """Test database connection failure alert."""
        error_details = {
            "connection_string": "postgresql://localhost:5432/kessan",
            "error": "Connection refused",
            "retry_count": 3
        }
        
        await health_alerter.alert_database_connection_failure(error_details)
        
        # Verify alert was sent
        health_alerter.alert_manager.send_alert.assert_called_once()
        
        # Check the exception that was created
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        context = call_args[1]
        
        assert isinstance(exception, DatabaseConnectionException)
        assert exception.category == ErrorCategory.SYSTEM_ERROR
        assert exception.severity == ErrorSeverity.CRITICAL
        assert exception.should_alert is True
        assert context == error_details
    
    @pytest.mark.asyncio
    async def test_alert_cache_connection_failure(self, health_alerter):
        """Test cache connection failure alert."""
        error_details = {
            "redis_url": "redis://localhost:6379",
            "error": "Connection timeout",
            "retry_count": 2
        }
        
        await health_alerter.alert_cache_connection_failure(error_details)
        
        # Verify alert was sent
        health_alerter.alert_manager.send_alert.assert_called_once()
        
        # Check the exception
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert exception.category == ErrorCategory.SYSTEM_ERROR
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.should_alert is True
    
    @pytest.mark.asyncio
    async def test_alert_external_api_failure(self, health_alerter):
        """Test external API failure alert."""
        context = {"request_id": "test-request", "retry_count": 1}
        
        await health_alerter.alert_external_api_failure(
            "alpha_vantage", 503, "Service unavailable", context
        )
        
        # Verify alert was sent
        health_alerter.alert_manager.send_alert.assert_called_once()
        
        # Check the exception
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert isinstance(exception, ExternalAPIException)
        assert exception.details["api_name"] == "alpha_vantage"
        assert exception.details["status_code"] == 503
        assert exception.details["error_message"] == "Service unavailable"
        assert exception.should_alert is True
    
    @pytest.mark.asyncio
    async def test_alert_budget_exceeded(self, health_alerter):
        """Test budget exceeded alert."""
        context = {
            "current_usage": 150.0,
            "budget": 100.0,
            "time_period": "daily"
        }
        
        await health_alerter.alert_budget_exceeded("daily", context)
        
        # Verify alert was sent
        health_alerter.alert_manager.send_alert.assert_called_once()
        
        # Check the exception
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert isinstance(exception, BudgetExceededException)
        assert "daily" in exception.message
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.should_alert is True
    
    @pytest.mark.asyncio
    async def test_alert_high_error_rate(self, health_alerter):
        """Test high error rate alert."""
        context = {
            "endpoint": "/api/v1/stocks",
            "error_count": 50,
            "total_requests": 100
        }
        
        await health_alerter.alert_high_error_rate(0.5, 0.1, "5 minutes", context)
        
        # Verify alert was sent
        health_alerter.alert_manager.send_alert.assert_called_once()
        
        # Check the exception
        call_args = health_alerter.alert_manager.send_alert.call_args[0]
        exception = call_args[0]
        
        assert "High error rate detected" in exception.message
        assert "50.00%" in exception.message
        assert "10.00%" in exception.message
        assert exception.details["error_rate"] == 0.5
        assert exception.details["threshold"] == 0.1
        assert exception.details["time_window"] == "5 minutes"
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.should_alert is True


if __name__ == "__main__":
    pytest.main([__file__])