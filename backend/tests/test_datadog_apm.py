"""
Tests for Datadog APM integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from datetime import datetime

from app.core.datadog_apm import DatadogAPM, datadog_apm, trace_function, trace_ai_analysis, trace_data_source


class TestDatadogAPM:
    """Test Datadog APM integration."""
    
    def test_should_enable_apm_production(self):
        """Test APM is enabled in production environment."""
        with patch('app.core.datadog_apm.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            apm = DatadogAPM()
            assert apm._should_enable_apm() is True
    
    def test_should_enable_apm_staging(self):
        """Test APM is enabled in staging environment."""
        with patch('app.core.datadog_apm.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "staging"
            apm = DatadogAPM()
            assert apm._should_enable_apm() is True
    
    def test_should_disable_apm_development(self):
        """Test APM is disabled in development by default."""
        with patch('app.core.datadog_apm.settings') as mock_settings, \
             patch('app.core.datadog_apm.os.getenv') as mock_getenv, \
             patch('app.core.datadog_apm.os.path.exists') as mock_exists:
            
            mock_settings.ENVIRONMENT = "development"
            mock_getenv.return_value = ""
            mock_exists.return_value = False
            
            apm = DatadogAPM()
            assert apm._should_enable_apm() is False
    
    @patch('app.core.datadog_apm.patch_all')
    @patch('app.core.datadog_apm.patch_fastapi')
    @patch('app.core.datadog_apm.tracer')
    @patch('app.core.datadog_apm.config')
    def test_configure_datadog(self, mock_config, mock_tracer, mock_patch_fastapi, mock_patch_all):
        """Test Datadog configuration setup."""
        with patch('app.core.datadog_apm.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            
            apm = DatadogAPM()
            
            # Verify patching was called
            mock_patch_all.assert_called_once()
            mock_patch_fastapi.assert_called_once()
            
            # Verify tracer tags were set
            mock_tracer.set_tags.assert_called_once()
    
    @patch('app.core.datadog_apm.tracer')
    def test_trace_function_decorator_async(self, mock_tracer):
        """Test function tracing decorator for async functions."""
        mock_span = Mock()
        mock_tracer.trace.return_value.__enter__.return_value = mock_span
        
        apm = DatadogAPM()
        apm.enabled = True
        
        @apm.trace_function("test.operation")
        async def test_async_function():
            return "success"
        
        # Test successful execution
        result = asyncio.run(test_async_function())
        assert result == "success"
        
        mock_tracer.trace.assert_called_once()
        mock_span.set_tag.assert_any_call("function.success", True)
    
    @patch('app.core.datadog_apm.tracer')
    def test_trace_function_decorator_sync(self, mock_tracer):
        """Test function tracing decorator for sync functions."""
        mock_span = Mock()
        mock_tracer.trace.return_value.__enter__.return_value = mock_span
        
        apm = DatadogAPM()
        apm.enabled = True
        
        @apm.trace_function("test.operation")
        def test_sync_function():
            return "success"
        
        # Test successful execution
        result = test_sync_function()
        assert result == "success"
        
        mock_tracer.trace.assert_called_once()
        mock_span.set_tag.assert_any_call("function.success", True)
    
    @patch('app.core.datadog_apm.tracer')
    def test_trace_function_error_handling(self, mock_tracer):
        """Test function tracing handles errors correctly."""
        mock_span = Mock()
        mock_tracer.trace.return_value.__enter__.return_value = mock_span
        
        apm = DatadogAPM()
        apm.enabled = True
        
        @apm.trace_function("test.operation")
        def test_error_function():
            raise ValueError("Test error")
        
        # Test error handling
        with pytest.raises(ValueError):
            test_error_function()
        
        mock_span.set_error.assert_called_once()
        mock_span.set_tag.assert_any_call("function.success", False)
    
    def test_trace_operation_context_manager(self):
        """Test trace operation context manager."""
        apm = DatadogAPM()
        apm.enabled = False  # Test disabled case
        
        with apm.trace_operation("test.operation", tag1="value1") as span:
            assert span is None
    
    @patch('app.core.datadog_apm.tracer')
    def test_trace_ai_analysis_decorator(self, mock_tracer):
        """Test AI analysis tracing decorator."""
        mock_span = Mock()
        mock_tracer.trace.return_value.__enter__.return_value = mock_span
        
        apm = DatadogAPM()
        apm.enabled = True
        
        @apm.trace_ai_analysis("7203", "short_term", "gemini-1.0")
        async def test_ai_function():
            return {
                "confidence": 0.85,
                "cache_hit": False,
                "cost_usd": 0.05
            }
        
        result = asyncio.run(test_ai_function())
        
        # Verify AI-specific tags were set
        mock_span.set_tag.assert_any_call("ai.ticker", "7203")
        mock_span.set_tag.assert_any_call("ai.analysis_type", "short_term")
        mock_span.set_tag.assert_any_call("ai.model_version", "gemini-1.0")
        mock_span.set_tag.assert_any_call("ai.confidence_score", 0.85)
        mock_span.set_tag.assert_any_call("ai.cache_hit", False)
        mock_span.set_tag.assert_any_call("ai.cost_usd", 0.05)
    
    @patch('app.core.datadog_apm.tracer')
    def test_trace_data_source_decorator(self, mock_tracer):
        """Test data source tracing decorator."""
        mock_span = Mock()
        mock_tracer.trace.return_value.__enter__.return_value = mock_span
        
        apm = DatadogAPM()
        apm.enabled = True
        
        @apm.trace_data_source("alpha_vantage", "fetch_prices")
        async def test_data_source_function():
            return {"data": [1, 2, 3, 4, 5]}
        
        result = asyncio.run(test_data_source_function())
        
        # Verify data source tags were set
        mock_span.set_tag.assert_any_call("data_source.name", "alpha_vantage")
        mock_span.set_tag.assert_any_call("data_source.operation", "fetch_prices")
        mock_span.set_tag.assert_any_call("data_source.records_count", 5)
    
    @patch('datadog.statsd')
    def test_add_custom_metric(self, mock_statsd):
        """Test adding custom metrics."""
        apm = DatadogAPM()
        apm.enabled = True
        
        apm.add_custom_metric("test.metric", 42.5, {"tag1": "value1"})
        
        mock_statsd.gauge.assert_called_once()
        args, kwargs = mock_statsd.gauge.call_args
        assert args[0] == "kessan.test.metric"
        assert args[1] == 42.5
        assert "tag1:value1" in kwargs["tags"]
    
    @patch('datadog.statsd')
    def test_increment_counter(self, mock_statsd):
        """Test incrementing counter metrics."""
        apm = DatadogAPM()
        apm.enabled = True
        
        apm.increment_counter("test.counter", 5, {"tag1": "value1"})
        
        mock_statsd.increment.assert_called_once()
        args, kwargs = mock_statsd.increment.call_args
        assert args[0] == "kessan.test.counter"
        assert args[1] == 5
        assert "tag1:value1" in kwargs["tags"]
    
    @patch('datadog.statsd')
    def test_record_histogram(self, mock_statsd):
        """Test recording histogram metrics."""
        apm = DatadogAPM()
        apm.enabled = True
        
        apm.record_histogram("test.histogram", 123.45, {"tag1": "value1"})
        
        mock_statsd.histogram.assert_called_once()
        args, kwargs = mock_statsd.histogram.call_args
        assert args[0] == "kessan.test.histogram"
        assert args[1] == 123.45
        assert "tag1:value1" in kwargs["tags"]
    
    def test_disabled_apm_no_operations(self):
        """Test that disabled APM doesn't perform operations."""
        apm = DatadogAPM()
        apm.enabled = False
        
        # These should not raise exceptions or perform operations
        apm.add_custom_metric("test.metric", 42.5)
        apm.increment_counter("test.counter", 1)
        apm.record_histogram("test.histogram", 123.45)


class TestConvenienceDecorators:
    """Test convenience decorator functions."""
    
    @patch('app.core.datadog_apm.datadog_apm')
    def test_trace_function_convenience(self, mock_apm):
        """Test trace_function convenience decorator."""
        mock_apm.trace_function.return_value = lambda f: f
        
        @trace_function("test.operation")
        def test_function():
            return "test"
        
        mock_apm.trace_function.assert_called_once_with("test.operation", None, None)
    
    @patch('app.core.datadog_apm.datadog_apm')
    def test_trace_ai_analysis_convenience(self, mock_apm):
        """Test trace_ai_analysis convenience decorator."""
        mock_apm.trace_ai_analysis.return_value = lambda f: f
        
        @trace_ai_analysis("7203", "short_term", "gemini-1.0")
        def test_function():
            return "test"
        
        mock_apm.trace_ai_analysis.assert_called_once_with("7203", "short_term", "gemini-1.0")
    
    @patch('app.core.datadog_apm.datadog_apm')
    def test_trace_data_source_convenience(self, mock_apm):
        """Test trace_data_source convenience decorator."""
        mock_apm.trace_data_source.return_value = lambda f: f
        
        @trace_data_source("alpha_vantage", "fetch_prices")
        def test_function():
            return "test"
        
        mock_apm.trace_data_source.assert_called_once_with("alpha_vantage", "fetch_prices")


@pytest.fixture
def mock_datadog_environment():
    """Mock environment for Datadog testing."""
    with patch.dict('os.environ', {
        'DD_SERVICE': 'test-service',
        'DD_ENV': 'test',
        'DD_VERSION': '1.0.0',
        'DD_TRACE_ENABLED': 'true'
    }):
        yield


class TestDatadogIntegration:
    """Integration tests for Datadog APM."""
    
    def test_global_apm_instance(self):
        """Test that global APM instance is created."""
        assert datadog_apm is not None
        assert isinstance(datadog_apm, DatadogAPM)
    
    @patch('app.core.datadog_apm.tracer')
    def test_real_function_tracing(self, mock_tracer):
        """Test real function tracing with global instance."""
        mock_span = Mock()
        mock_tracer.trace.return_value.__enter__.return_value = mock_span
        
        # Enable APM for testing
        datadog_apm.enabled = True
        
        @trace_function("integration.test")
        def test_integration_function(x, y):
            return x + y
        
        result = test_integration_function(2, 3)
        assert result == 5
        
        # Verify tracing was called
        mock_tracer.trace.assert_called()
        mock_span.set_tag.assert_called()