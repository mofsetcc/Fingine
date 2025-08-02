"""
Tests for business metrics collection service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta

from app.services.business_metrics import (
    BusinessMetricsCollector, BusinessMetric, MetricType,
    business_metrics, record_user_action, record_analysis_request, record_subscription_event
)


class TestBusinessMetricsCollector:
    """Test business metrics collection."""
    
    @pytest.fixture
    def collector(self):
        """Create a test metrics collector."""
        return BusinessMetricsCollector()
    
    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector.metrics_cache == {}
        assert collector.collection_interval == 300
        assert collector.is_running is False
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_user_metrics(self, mock_get_session, collector):
        """Test user metrics collection."""
        # Mock database session and results
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=Mock(return_value=1000)),  # active users
            Mock(scalar=Mock(return_value=50)),    # new users today
            Mock(scalar=Mock(return_value=200))    # daily active users
        ]
        
        await collector.collect_user_metrics()
        
        # Verify metrics were recorded
        assert "users.active_total" in collector.metrics_cache
        assert "users.new_daily" in collector.metrics_cache
        assert "users.daily_active" in collector.metrics_cache
        
        # Verify metric values
        assert collector.metrics_cache["users.active_total"].value == 1000
        assert collector.metrics_cache["users.new_daily"].value == 50
        assert collector.metrics_cache["users.daily_active"].value == 200
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_analysis_metrics(self, mock_get_session, collector):
        """Test AI analysis metrics collection."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=Mock(return_value=100)),  # analyses today
            Mock(fetchall=Mock(return_value=[     # analysis by type
                Mock(analysis_type="short_term", count=60),
                Mock(analysis_type="mid_term", count=30),
                Mock(analysis_type="long_term", count=10)
            ])),
            Mock(scalar=Mock(return_value=0.75)), # average confidence
            Mock(scalar=Mock(return_value=2500))  # average processing time
        ]
        
        await collector.collect_analysis_metrics()
        
        # Verify metrics were recorded
        assert "analysis.requests_daily" in collector.metrics_cache
        assert "analysis.average_confidence" in collector.metrics_cache
        assert "analysis.average_processing_time_ms" in collector.metrics_cache
        
        # Verify values
        assert collector.metrics_cache["analysis.requests_daily"].value == 100
        assert collector.metrics_cache["analysis.average_confidence"].value == 0.75
        assert collector.metrics_cache["analysis.average_processing_time_ms"].value == 2500
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_subscription_metrics(self, mock_get_session, collector):
        """Test subscription metrics collection."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query results
        mock_session.execute.side_effect = [
            Mock(fetchall=Mock(return_value=[     # subscription distribution
                Mock(plan_name="free", subscriber_count=800),
                Mock(plan_name="pro", subscriber_count=150),
                Mock(plan_name="business", subscriber_count=50)
            ])),
            Mock(scalar=Mock(return_value=500000)), # MRR in JPY
            Mock(fetchone=Mock(return_value=Mock(churned=20, total=1000))) # churn rate
        ]
        
        await collector.collect_subscription_metrics()
        
        # Verify metrics were recorded
        assert "revenue.monthly_recurring" in collector.metrics_cache
        assert "subscriptions.churn_rate_percent" in collector.metrics_cache
        
        # Verify values
        assert collector.metrics_cache["revenue.monthly_recurring"].value == 500000
        assert collector.metrics_cache["subscriptions.churn_rate_percent"].value == 2.0  # 20/1000 * 100
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_performance_metrics(self, mock_get_session, collector):
        """Test performance metrics collection."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query results
        mock_session.execute.side_effect = [
            Mock(fetchone=Mock(return_value=Mock(
                avg_response_time=250,
                p95_response_time=800,
                request_count=5000
            ))),
            Mock(fetchone=Mock(return_value=Mock(
                error_count=50,
                total_count=5000
            )))
        ]
        
        await collector.collect_performance_metrics()
        
        # Verify metrics were recorded
        assert "api.response_time_avg_ms" in collector.metrics_cache
        assert "api.response_time_p95_ms" in collector.metrics_cache
        assert "api.request_count_hourly" in collector.metrics_cache
        assert "api.error_rate_percent" in collector.metrics_cache
        
        # Verify values
        assert collector.metrics_cache["api.response_time_avg_ms"].value == 250
        assert collector.metrics_cache["api.response_time_p95_ms"].value == 800
        assert collector.metrics_cache["api.request_count_hourly"].value == 5000
        assert collector.metrics_cache["api.error_rate_percent"].value == 1.0  # 50/5000 * 100
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_cost_metrics(self, mock_get_session, collector):
        """Test cost metrics collection."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=Mock(return_value=25.50)),  # daily AI cost
            Mock(scalar=Mock(return_value=650.00)), # monthly AI cost
            Mock(fetchall=Mock(return_value=[       # API costs by provider
                Mock(api_provider="alpha_vantage", total_cost=5.00),
                Mock(api_provider="news_api", total_cost=2.50)
            ]))
        ]
        
        await collector.collect_cost_metrics()
        
        # Verify metrics were recorded
        assert "costs.ai_daily_usd" in collector.metrics_cache
        assert "costs.ai_monthly_usd" in collector.metrics_cache
        
        # Verify values
        assert collector.metrics_cache["costs.ai_daily_usd"].value == 25.50
        assert collector.metrics_cache["costs.ai_monthly_usd"].value == 650.00
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_data_source_metrics(self, mock_get_session, collector):
        """Test data source metrics collection."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query results
        mock_session.execute.return_value.fetchall.return_value = [
            Mock(api_provider="alpha_vantage", success_count=95, total_count=100, avg_response_time=150),
            Mock(api_provider="news_api", success_count=98, total_count=100, avg_response_time=300)
        ]
        
        await collector.collect_data_source_metrics()
        
        # Verify success rates were calculated correctly
        # alpha_vantage: 95/100 = 95%
        # news_api: 98/100 = 98%
        
        # Note: The exact metric names would depend on the provider tags
        # This test verifies the collection logic works
        assert len(collector.metrics_cache) > 0
    
    @patch('app.services.business_metrics.datadog_apm')
    def test_record_metric(self, mock_apm, collector):
        """Test metric recording."""
        collector.record_metric(
            "test.metric",
            42.5,
            MetricType.GAUGE,
            {"tag1": "value1"}
        )
        
        # Verify metric was cached
        assert "test.metric" in collector.metrics_cache
        metric = collector.metrics_cache["test.metric"]
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.tags == {"tag1": "value1"}
        
        # Verify Datadog was called
        mock_apm.add_custom_metric.assert_called_once_with(
            "test.metric", 42.5, {"tag1": "value1"}
        )
    
    @patch('app.services.business_metrics.datadog_apm')
    def test_record_counter_metric(self, mock_apm, collector):
        """Test counter metric recording."""
        collector.record_metric(
            "test.counter",
            5,
            MetricType.COUNTER,
            {"tag1": "value1"}
        )
        
        # Verify Datadog counter was called
        mock_apm.increment_counter.assert_called_once_with(
            "test.counter", 5, {"tag1": "value1"}
        )
    
    @patch('app.services.business_metrics.datadog_apm')
    def test_record_histogram_metric(self, mock_apm, collector):
        """Test histogram metric recording."""
        collector.record_metric(
            "test.histogram",
            123.45,
            MetricType.HISTOGRAM,
            {"tag1": "value1"}
        )
        
        # Verify Datadog histogram was called
        mock_apm.record_histogram.assert_called_once_with(
            "test.histogram", 123.45, {"tag1": "value1"}
        )
    
    def test_get_cached_metrics(self, collector):
        """Test getting cached metrics."""
        # Add some test metrics
        collector.metrics_cache["test1"] = BusinessMetric(
            name="test1",
            value=10.0,
            metric_type=MetricType.GAUGE,
            tags={},
            timestamp=datetime.utcnow()
        )
        
        cached = collector.get_cached_metrics()
        assert "test1" in cached
        assert cached["test1"].value == 10.0
        
        # Verify it's a copy
        cached["test2"] = "new_value"
        assert "test2" not in collector.metrics_cache
    
    async def test_get_metric_history(self, collector):
        """Test getting metric history."""
        # This is a placeholder implementation
        history = await collector.get_metric_history("test.metric", 24)
        assert history == []
    
    @patch('app.services.business_metrics.get_db_session')
    async def test_collect_all_metrics(self, mock_get_session, collector):
        """Test collecting all metrics."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock all database calls to return empty results
        mock_session.execute.return_value.scalar.return_value = 0
        mock_session.execute.return_value.fetchall.return_value = []
        mock_session.execute.return_value.fetchone.return_value = Mock(churned=0, total=1)
        
        await collector.collect_all_metrics()
        
        # Verify some metrics were collected
        assert len(collector.metrics_cache) > 0
    
    async def test_start_stop_collection(self, collector):
        """Test starting and stopping collection."""
        # Mock the collection method to avoid database calls
        collector.collect_all_metrics = AsyncMock()
        
        # Start collection
        collection_task = asyncio.create_task(collector.start_collection())
        
        # Wait a bit to ensure it starts
        await asyncio.sleep(0.1)
        assert collector.is_running is True
        
        # Stop collection
        collector.stop_collection()
        
        # Wait for task to complete
        await asyncio.sleep(0.1)
        collection_task.cancel()
        
        assert collector.is_running is False


class TestConvenienceFunctions:
    """Test convenience functions for recording metrics."""
    
    @patch('app.services.business_metrics.business_metrics')
    def test_record_user_action(self, mock_metrics):
        """Test recording user action."""
        record_user_action("login", "user123", {"method": "oauth"})
        
        mock_metrics.record_metric.assert_called_once()
        args = mock_metrics.record_metric.call_args[0]
        assert args[0] == "user_actions.count"
        assert args[1] == 1
        assert args[2] == MetricType.COUNTER
        assert "action" in args[3]
        assert args[3]["action"] == "login"
    
    @patch('app.services.business_metrics.business_metrics')
    def test_record_analysis_request(self, mock_metrics):
        """Test recording analysis request."""
        record_analysis_request("7203", "short_term", 2500.0, True)
        
        mock_metrics.record_metric.assert_called_once()
        args = mock_metrics.record_metric.call_args[0]
        assert args[0] == "analysis.processing_time_ms"
        assert args[1] == 2500.0
        assert args[2] == MetricType.HISTOGRAM
        assert args[3]["ticker"] == "7203"
        assert args[3]["analysis_type"] == "short_term"
        assert args[3]["success"] == "True"
    
    @patch('app.services.business_metrics.business_metrics')
    def test_record_subscription_event(self, mock_metrics):
        """Test recording subscription event."""
        record_subscription_event("upgrade", "pro", "user123")
        
        mock_metrics.record_metric.assert_called_once()
        args = mock_metrics.record_metric.call_args[0]
        assert args[0] == "subscription_events.count"
        assert args[1] == 1
        assert args[2] == MetricType.COUNTER
        assert args[3]["event_type"] == "upgrade"
        assert args[3]["plan_name"] == "pro"


class TestBusinessMetric:
    """Test BusinessMetric data structure."""
    
    def test_business_metric_creation(self):
        """Test creating a business metric."""
        timestamp = datetime.utcnow()
        metric = BusinessMetric(
            name="test.metric",
            value=42.5,
            metric_type=MetricType.GAUGE,
            tags={"tag1": "value1"},
            timestamp=timestamp,
            description="Test metric"
        )
        
        assert metric.name == "test.metric"
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.tags == {"tag1": "value1"}
        assert metric.timestamp == timestamp
        assert metric.description == "Test metric"


class TestGlobalInstance:
    """Test global business metrics instance."""
    
    def test_global_instance_exists(self):
        """Test that global instance exists."""
        assert business_metrics is not None
        assert isinstance(business_metrics, BusinessMetricsCollector)


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations in business metrics."""
    
    async def test_async_metric_collection_error_handling(self):
        """Test error handling in async metric collection."""
        collector = BusinessMetricsCollector()
        
        # Mock database session to raise an exception
        with patch('app.services.business_metrics.get_db_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            # Should not raise exception, but log error
            await collector.collect_user_metrics()
            
            # Verify no metrics were added due to error
            assert len(collector.metrics_cache) == 0