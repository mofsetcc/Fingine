"""
Tests for structured logging functionality.
"""

import json
import uuid
from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from app.core.logging import StructuredLogger, setup_logging, get_logger


class TestStructuredLogger:
    """Test cases for StructuredLogger class."""
    
    @pytest.fixture
    def logger(self):
        """Create a StructuredLogger instance for testing."""
        return StructuredLogger("test_service")
    
    @pytest.fixture
    def mock_structlog_logger(self):
        """Mock structlog logger."""
        mock_logger = Mock()
        with patch.object(StructuredLogger, '__init__', lambda self, service_name: setattr(self, 'logger', mock_logger) or setattr(self, 'service_name', service_name)):
            yield mock_logger
    
    def test_log_api_request_success(self, logger, mock_structlog_logger):
        """Test logging successful API request."""
        request_data = {
            "request_id": "test-123",
            "method": "GET",
            "endpoint": "/api/v1/stocks/7203",
            "user_id": "user-456",
            "user_agent": "Mozilla/5.0",
            "response_time_ms": 150,
            "status_code": 200,
            "ip_address": "192.168.1.100",
            "request_size": 0,
            "response_size": 1024,
        }
        
        logger.log_api_request(request_data)
        
        # Verify info was called (success case)
        mock_structlog_logger.info.assert_called_once()
        call_args = mock_structlog_logger.info.call_args
        
        assert call_args[0][0] == "api_request_success"
        assert call_args[1]["event_type"] == "api_request"
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["endpoint"] == "/api/v1/stocks/7203"
        assert call_args[1]["status_code"] == 200
        assert call_args[1]["ip_address"] == "192.168.1.0"  # Anonymized
    
    def test_log_api_request_error(self, logger, mock_structlog_logger):
        """Test logging API request error."""
        request_data = {
            "method": "POST",
            "endpoint": "/api/v1/analysis",
            "status_code": 500,
            "error_message": "Internal server error",
            "ip_address": "10.0.0.50",
        }
        
        logger.log_api_request(request_data)
        
        # Verify error was called (error case)
        mock_structlog_logger.error.assert_called_once()
        call_args = mock_structlog_logger.error.call_args
        
        assert call_args[0][0] == "api_request_error"
        assert call_args[1]["status_code"] == 500
        assert call_args[1]["error_message"] == "Internal server error"
        assert call_args[1]["ip_address"] == "10.0.0.0"  # Anonymized
    
    def test_log_ai_analysis_request(self, logger, mock_structlog_logger):
        """Test logging AI analysis request."""
        analysis_data = {
            "request_id": "analysis-789",
            "ticker": "7203",
            "analysis_type": "short_term",
            "model_version": "gemini-pro-1.0",
            "processing_time_ms": 2500,
            "cost_usd": 0.05,
            "cache_hit": False,
            "user_id": "user-123",
            "prompt_tokens": 1500,
            "completion_tokens": 800,
            "confidence_score": 0.85,
        }
        
        logger.log_ai_analysis_request(analysis_data)
        
        mock_structlog_logger.info.assert_called_once()
        call_args = mock_structlog_logger.info.call_args
        
        assert call_args[0][0] == "ai_analysis_request"
        assert call_args[1]["event_type"] == "ai_analysis"
        assert call_args[1]["ticker"] == "7203"
        assert call_args[1]["analysis_type"] == "short_term"
        assert call_args[1]["cost_usd"] == 0.05
        assert call_args[1]["cache_hit"] is False
    
    def test_log_business_event(self, logger, mock_structlog_logger):
        """Test logging business event."""
        event_data = {
            "event_id": "event-456",
            "event_name": "user_registration",
            "event_category": "authentication",
            "user_id": "user-789",
            "session_id": "session-123",
            "subscription_tier": "free",
            "metadata": {"source": "web", "campaign": "organic"},
            "properties": {"registration_method": "email"},
        }
        
        logger.log_business_event(event_data)
        
        mock_structlog_logger.info.assert_called_once()
        call_args = mock_structlog_logger.info.call_args
        
        assert call_args[0][0] == "business_event"
        assert call_args[1]["event_type"] == "business_event"
        assert call_args[1]["event_name"] == "user_registration"
        assert call_args[1]["event_category"] == "authentication"
        assert call_args[1]["user_id"] == "user-789"
        assert call_args[1]["metadata"] == {"source": "web", "campaign": "organic"}
    
    def test_log_error_with_exception(self, logger, mock_structlog_logger):
        """Test logging error with exception."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            error_data = {
                "error_id": "error-123",
                "error_type": "validation_error",
                "error_message": "Invalid input data",
                "error_code": "INVALID_INPUT",
                "user_id": "user-456",
                "request_id": "req-789",
                "endpoint": "/api/v1/stocks",
                "method": "POST",
                "ip_address": "172.16.0.100",
                "context": {"ticker": "INVALID", "field": "ticker"},
            }
            
            logger.log_error(error_data, e)
        
        mock_structlog_logger.error.assert_called_once()
        call_args = mock_structlog_logger.error.call_args
        
        assert call_args[0][0] == "application_error"
        assert call_args[1]["event_type"] == "error"
        assert call_args[1]["error_type"] == "validation_error"
        assert call_args[1]["exception_type"] == "ValueError"
        assert call_args[1]["exception_message"] == "Test error message"
        assert "stack_trace" in call_args[1]
        assert call_args[1]["ip_address"] == "172.16.0.0"  # Anonymized
    
    def test_log_data_source_event_success(self, logger, mock_structlog_logger):
        """Test logging successful data source event."""
        source_data = {
            "source_name": "alpha_vantage",
            "source_type": "stock_prices",
            "operation": "fetch_daily_prices",
            "status": "success",
            "response_time_ms": 800,
            "records_processed": 100,
            "cost_usd": 0.01,
        }
        
        logger.log_data_source_event(source_data)
        
        mock_structlog_logger.info.assert_called_once()
        call_args = mock_structlog_logger.info.call_args
        
        assert call_args[0][0] == "data_source_success"
        assert call_args[1]["event_type"] == "data_source"
        assert call_args[1]["source_name"] == "alpha_vantage"
        assert call_args[1]["status"] == "success"
        assert call_args[1]["records_processed"] == 100
    
    def test_log_data_source_event_error(self, logger, mock_structlog_logger):
        """Test logging data source error event."""
        source_data = {
            "source_name": "yahoo_finance",
            "source_type": "stock_prices",
            "operation": "fetch_daily_prices",
            "status": "error",
            "response_time_ms": 5000,
            "error_message": "API rate limit exceeded",
        }
        
        logger.log_data_source_event(source_data)
        
        mock_structlog_logger.error.assert_called_once()
        call_args = mock_structlog_logger.error.call_args
        
        assert call_args[0][0] == "data_source_error"
        assert call_args[1]["status"] == "error"
        assert call_args[1]["error_message"] == "API rate limit exceeded"
    
    def test_log_performance_metric(self, logger, mock_structlog_logger):
        """Test logging performance metric."""
        metric_data = {
            "metric_name": "api_response_time",
            "metric_value": 150.5,
            "metric_unit": "milliseconds",
            "tags": {"endpoint": "/api/v1/stocks", "method": "GET"},
            "context": {"user_tier": "pro", "cache_hit": False},
        }
        
        logger.log_performance_metric(metric_data)
        
        mock_structlog_logger.info.assert_called_once()
        call_args = mock_structlog_logger.info.call_args
        
        assert call_args[0][0] == "performance_metric"
        assert call_args[1]["event_type"] == "performance_metric"
        assert call_args[1]["metric_name"] == "api_response_time"
        assert call_args[1]["metric_value"] == 150.5
        assert call_args[1]["metric_unit"] == "milliseconds"
    
    @pytest.mark.parametrize("ip_address,expected", [
        ("192.168.1.100", "192.168.1.0"),
        ("10.0.0.50", "10.0.0.0"),
        ("172.16.255.1", "172.16.255.0"),
        ("2001:db8:85a3:8d3:1319:8a2e:370:7348", "2001:db8:85a3:8d3::0"),
        ("::1", "::0"),
        ("invalid-ip", "anonymized"),
        ("", None),
        (None, None),
    ])
    def test_anonymize_ip(self, logger, ip_address, expected):
        """Test IP address anonymization."""
        result = logger._anonymize_ip(ip_address)
        assert result == expected
    
    def test_none_values_filtered(self, logger, mock_structlog_logger):
        """Test that None values are filtered from log entries."""
        request_data = {
            "method": "GET",
            "endpoint": "/api/v1/test",
            "user_id": None,  # Should be filtered out
            "status_code": 200,
            "error_message": None,  # Should be filtered out
        }
        
        logger.log_api_request(request_data)
        
        call_args = mock_structlog_logger.info.call_args[1]
        assert "user_id" not in call_args
        assert "error_message" not in call_args
        assert "method" in call_args
        assert "status_code" in call_args


class TestLoggingSetup:
    """Test cases for logging setup and configuration."""
    
    @patch('app.core.logging.structlog')
    @patch('app.core.logging.logging')
    def test_setup_logging_debug_mode(self, mock_logging, mock_structlog):
        """Test logging setup in debug mode."""
        with patch('app.core.logging.settings') as mock_settings:
            mock_settings.DEBUG = True
            
            setup_logging()
            
            # Verify structlog configuration
            mock_structlog.configure.assert_called_once()
            config_call = mock_structlog.configure.call_args[1]
            
            assert "processors" in config_call
            assert config_call["context_class"] == dict
            assert config_call["cache_logger_on_first_use"] is True
            
            # Verify standard logging configuration
            mock_logging.basicConfig.assert_called_once()
            basic_config_call = mock_logging.basicConfig.call_args[1]
            assert basic_config_call["level"] == mock_logging.DEBUG
    
    @patch('app.core.logging.structlog')
    @patch('app.core.logging.logging')
    def test_setup_logging_production_mode(self, mock_logging, mock_structlog):
        """Test logging setup in production mode."""
        with patch('app.core.logging.settings') as mock_settings:
            mock_settings.DEBUG = False
            
            setup_logging()
            
            # Verify standard logging configuration for production
            mock_logging.basicConfig.assert_called_once()
            basic_config_call = mock_logging.basicConfig.call_args[1]
            assert basic_config_call["level"] == mock_logging.INFO
    
    @patch('app.core.logging.structlog')
    def test_get_logger(self, mock_structlog):
        """Test getting a logger instance."""
        mock_logger = Mock()
        mock_structlog.get_logger.return_value = mock_logger
        
        result = get_logger("test_service")
        
        mock_structlog.get_logger.assert_called_once_with("test_service")
        assert result == mock_logger


class TestGlobalLoggerInstances:
    """Test cases for global logger instances."""
    
    def test_global_logger_instances_exist(self):
        """Test that global logger instances are created."""
        from app.core.logging import api_logger, business_logger, error_logger, performance_logger
        
        assert isinstance(api_logger, StructuredLogger)
        assert isinstance(business_logger, StructuredLogger)
        assert isinstance(error_logger, StructuredLogger)
        assert isinstance(performance_logger, StructuredLogger)
        
        assert api_logger.service_name == "api"
        assert business_logger.service_name == "business"
        assert error_logger.service_name == "error"
        assert performance_logger.service_name == "performance"