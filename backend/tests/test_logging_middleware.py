"""
Tests for logging middleware functionality.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.core.logging_middleware import LoggingMiddleware, BusinessEventLogger


class TestLoggingMiddleware:
    """Test cases for LoggingMiddleware class."""
    
    @pytest.fixture
    def app(self):
        """Create a FastAPI app with logging middleware."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "ok"}
        
        app.add_middleware(LoggingMiddleware, exclude_paths=["/health"])
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    @patch('app.core.logging_middleware.api_logger')
    def test_successful_request_logging(self, mock_api_logger, client):
        """Test logging of successful API request."""
        response = client.get("/test", headers={"User-Agent": "test-client"})
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Verify API request was logged
        mock_api_logger.log_api_request.assert_called_once()
        mock_api_logger.log_api_response.assert_called_once()
        
        # Check request log data
        request_call_args = mock_api_logger.log_api_request.call_args[0][0]
        assert request_call_args["method"] == "GET"
        assert request_call_args["endpoint"] == "/test"
        assert request_call_args["status_code"] == 200
        assert request_call_args["user_agent"] == "test-client"
        assert "request_id" in request_call_args
        assert "response_time_ms" in request_call_args
        
        # Check response log data
        response_call_args = mock_api_logger.log_api_response.call_args[0][0]
        assert response_call_args["status_code"] == 200
        assert "response_time_ms" in response_call_args
        assert "request_id" in response_call_args
    
    @patch('app.core.logging_middleware.api_logger')
    def test_error_request_logging(self, mock_api_logger, client):
        """Test logging of error API request."""
        with pytest.raises(ValueError):
            client.get("/error")
        
        # Verify API request was logged with error
        mock_api_logger.log_api_request.assert_called_once()
        
        # Check error log data
        request_call_args = mock_api_logger.log_api_request.call_args[0][0]
        assert request_call_args["method"] == "GET"
        assert request_call_args["endpoint"] == "/error"
        assert request_call_args["status_code"] == 500
        assert "error_message" in request_call_args
    
    @patch('app.core.logging_middleware.api_logger')
    def test_excluded_path_not_logged(self, mock_api_logger, client):
        """Test that excluded paths are not logged."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Verify no logging occurred
        mock_api_logger.log_api_request.assert_not_called()
        mock_api_logger.log_api_response.assert_not_called()
    
    def test_get_client_ip_forwarded_for(self):
        """Test extracting client IP from X-Forwarded-For header."""
        middleware = LoggingMiddleware(None)
        
        # Mock request with X-Forwarded-For header
        request = Mock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.1, 192.0.2.1"
        }
        
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_real_ip(self):
        """Test extracting client IP from X-Real-IP header."""
        middleware = LoggingMiddleware(None)
        
        # Mock request with X-Real-IP header
        request = Mock()
        request.headers = {"X-Real-IP": "203.0.113.5"}
        
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.5"
    
    def test_get_client_ip_direct(self):
        """Test extracting client IP directly from request."""
        middleware = LoggingMiddleware(None)
        
        # Mock request with direct client
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.100"
    
    def test_get_client_ip_unknown(self):
        """Test handling unknown client IP."""
        middleware = LoggingMiddleware(None)
        
        # Mock request with no IP information
        request = Mock()
        request.headers = {}
        request.client = None
        
        ip = middleware._get_client_ip(request)
        assert ip == "unknown"
    
    @pytest.mark.asyncio
    async def test_extract_request_data(self):
        """Test extracting request data."""
        middleware = LoggingMiddleware(None)
        
        # Mock request
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/analysis"
        request.query_params = {"ticker": "7203"}
        request.headers = {
            "user-agent": "Mozilla/5.0",
            "referer": "https://example.com",
            "content-type": "application/json"
        }
        request.state = Mock()
        request.state.user_id = "user-123"
        
        # Mock body method
        async def mock_body():
            return b'{"test": "data"}'
        request.body = mock_body
        
        with patch.object(middleware, '_get_client_ip', return_value="192.168.1.100"):
            data = await middleware._extract_request_data(request, "req-123")
        
        assert data["request_id"] == "req-123"
        assert data["method"] == "POST"
        assert data["endpoint"] == "/api/v1/analysis"
        assert data["query_params"] == {"ticker": "7203"}
        assert data["user_id"] == "user-123"
        assert data["ip_address"] == "192.168.1.100"
        assert data["user_agent"] == "Mozilla/5.0"
        assert data["referer"] == "https://example.com"
        assert data["content_type"] == "application/json"
        assert data["request_size"] == 16  # Length of '{"test": "data"}'
    
    def test_extract_response_data(self):
        """Test extracting response data."""
        middleware = LoggingMiddleware(None)
        
        # Mock response
        response = Mock()
        response.status_code = 200
        response.headers = {
            "content-length": "1024",
            "content-type": "application/json",
            "X-Cache-Hit": "true"
        }
        
        data = middleware._extract_response_data(response, "req-123", 150)
        
        assert data["request_id"] == "req-123"
        assert data["status_code"] == 200
        assert data["response_time_ms"] == 150
        assert data["response_size_bytes"] == 1024
        assert data["content_type"] == "application/json"
        assert data["cache_hit"] is True


class TestBusinessEventLogger:
    """Test cases for BusinessEventLogger class."""
    
    @patch('app.core.logging.business_logger')
    def test_log_user_registration(self, mock_business_logger):
        """Test logging user registration event."""
        BusinessEventLogger.log_user_registration(
            user_id="user-123",
            registration_method="email",
            metadata={"source": "web", "campaign": "organic"}
        )
        
        mock_business_logger.log_business_event.assert_called_once()
        call_args = mock_business_logger.log_business_event.call_args[0][0]
        
        assert call_args["event_name"] == "user_registration"
        assert call_args["event_category"] == "authentication"
        assert call_args["user_id"] == "user-123"
        assert call_args["properties"]["registration_method"] == "email"
        assert call_args["metadata"]["source"] == "web"
    
    @patch('app.core.logging.business_logger')
    def test_log_user_login(self, mock_business_logger):
        """Test logging user login event."""
        BusinessEventLogger.log_user_login(
            user_id="user-456",
            login_method="oauth_google",
            success=True,
            metadata={"ip_country": "JP"}
        )
        
        mock_business_logger.log_business_event.assert_called_once()
        call_args = mock_business_logger.log_business_event.call_args[0][0]
        
        assert call_args["event_name"] == "user_login"
        assert call_args["event_category"] == "authentication"
        assert call_args["user_id"] == "user-456"
        assert call_args["properties"]["login_method"] == "oauth_google"
        assert call_args["properties"]["success"] is True
        assert call_args["metadata"]["ip_country"] == "JP"
    
    @patch('app.core.logging.business_logger')
    def test_log_stock_analysis_request(self, mock_business_logger):
        """Test logging stock analysis request event."""
        BusinessEventLogger.log_stock_analysis_request(
            user_id="user-789",
            ticker="7203",
            analysis_type="comprehensive",
            metadata={"subscription_tier": "pro"}
        )
        
        mock_business_logger.log_business_event.assert_called_once()
        call_args = mock_business_logger.log_business_event.call_args[0][0]
        
        assert call_args["event_name"] == "stock_analysis_request"
        assert call_args["event_category"] == "analysis"
        assert call_args["user_id"] == "user-789"
        assert call_args["properties"]["ticker"] == "7203"
        assert call_args["properties"]["analysis_type"] == "comprehensive"
        assert call_args["metadata"]["subscription_tier"] == "pro"
    
    @patch('app.core.logging.business_logger')
    def test_log_subscription_change(self, mock_business_logger):
        """Test logging subscription change event."""
        BusinessEventLogger.log_subscription_change(
            user_id="user-101",
            old_plan="free",
            new_plan="pro",
            metadata={"payment_method": "credit_card"}
        )
        
        mock_business_logger.log_business_event.assert_called_once()
        call_args = mock_business_logger.log_business_event.call_args[0][0]
        
        assert call_args["event_name"] == "subscription_change"
        assert call_args["event_category"] == "billing"
        assert call_args["user_id"] == "user-101"
        assert call_args["properties"]["old_plan"] == "free"
        assert call_args["properties"]["new_plan"] == "pro"
        assert call_args["metadata"]["payment_method"] == "credit_card"
    
    @patch('app.core.logging.business_logger')
    def test_log_watchlist_action(self, mock_business_logger):
        """Test logging watchlist action event."""
        BusinessEventLogger.log_watchlist_action(
            user_id="user-202",
            action="add",
            ticker="6758",
            metadata={"source": "search_results"}
        )
        
        mock_business_logger.log_business_event.assert_called_once()
        call_args = mock_business_logger.log_business_event.call_args[0][0]
        
        assert call_args["event_name"] == "watchlist_action"
        assert call_args["event_category"] == "user_interaction"
        assert call_args["user_id"] == "user-202"
        assert call_args["properties"]["action"] == "add"
        assert call_args["properties"]["ticker"] == "6758"
        assert call_args["metadata"]["source"] == "search_results"
    
    @patch('app.core.logging.business_logger')
    def test_log_quota_exceeded(self, mock_business_logger):
        """Test logging quota exceeded event."""
        BusinessEventLogger.log_quota_exceeded(
            user_id="user-303",
            quota_type="api_calls",
            current_usage=11,
            limit=10,
            metadata={"subscription_tier": "free"}
        )
        
        mock_business_logger.log_business_event.assert_called_once()
        call_args = mock_business_logger.log_business_event.call_args[0][0]
        
        assert call_args["event_name"] == "quota_exceeded"
        assert call_args["event_category"] == "system"
        assert call_args["user_id"] == "user-303"
        assert call_args["properties"]["quota_type"] == "api_calls"
        assert call_args["properties"]["current_usage"] == 11
        assert call_args["properties"]["limit"] == 10
        assert call_args["metadata"]["subscription_tier"] == "free"