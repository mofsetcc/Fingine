"""
Business metrics tracking service for monitoring key performance indicators.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.datadog_apm import datadog_apm
from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of business metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class BusinessMetric:
    """Business metric data structure."""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str]
    timestamp: datetime
    description: Optional[str] = None


class BusinessMetricsCollector:
    """Collects and tracks business metrics for monitoring and alerting."""
    
    def __init__(self):
        self.metrics_cache = {}
        self.collection_interval = 300  # 5 minutes
        self.is_running = False
    
    async def start_collection(self):
        """Start the metrics collection background task."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting business metrics collection")
        
        while self.is_running:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop_collection(self):
        """Stop the metrics collection."""
        self.is_running = False
        logger.info("Stopped business metrics collection")
    
    async def collect_all_metrics(self):
        """Collect all business metrics."""
        try:
            # Collect user metrics
            await self.collect_user_metrics()
            
            # Collect analysis metrics
            await self.collect_analysis_metrics()
            
            # Collect subscription metrics
            await self.collect_subscription_metrics()
            
            # Collect performance metrics
            await self.collect_performance_metrics()
            
            # Collect cost metrics
            await self.collect_cost_metrics()
            
            # Collect data source metrics
            await self.collect_data_source_metrics()
            
            logger.info("Business metrics collection completed")
            
        except Exception as e:
            logger.error(f"Failed to collect business metrics: {e}")
    
    async def collect_user_metrics(self):
        """Collect user-related metrics."""
        try:
            async with get_db_session() as session:
                # Total active users
                active_users_query = text("""
                    SELECT COUNT(*) as count
                    FROM users 
                    WHERE email_verified_at IS NOT NULL
                """)
                result = await session.execute(active_users_query)
                active_users = result.scalar()
                
                self.record_metric(
                    "users.active_total",
                    active_users,
                    MetricType.GAUGE,
                    {"metric_type": "user_count"}
                )
                
                # New users today
                new_users_today_query = text("""
                    SELECT COUNT(*) as count
                    FROM users 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                result = await session.execute(new_users_today_query)
                new_users_today = result.scalar()
                
                self.record_metric(
                    "users.new_daily",
                    new_users_today,
                    MetricType.GAUGE,
                    {"metric_type": "user_growth", "period": "daily"}
                )
                
                # User login activity (last 24 hours)
                login_activity_query = text("""
                    SELECT COUNT(DISTINCT user_id) as unique_users
                    FROM api_usage_logs 
                    WHERE endpoint LIKE '%/auth/login%'
                    AND request_timestamp >= NOW() - INTERVAL '24 hours'
                    AND status_code = 200
                """)
                result = await session.execute(login_activity_query)
                daily_active_users = result.scalar() or 0
                
                self.record_metric(
                    "users.daily_active",
                    daily_active_users,
                    MetricType.GAUGE,
                    {"metric_type": "user_engagement", "period": "daily"}
                )
                
        except Exception as e:
            logger.error(f"Failed to collect user metrics: {e}")
    
    async def collect_analysis_metrics(self):
        """Collect AI analysis-related metrics."""
        try:
            async with get_db_session() as session:
                # Total analyses today
                analyses_today_query = text("""
                    SELECT COUNT(*) as count
                    FROM ai_analysis_cache 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                result = await session.execute(analyses_today_query)
                analyses_today = result.scalar()
                
                self.record_metric(
                    "analysis.requests_daily",
                    analyses_today,
                    MetricType.GAUGE,
                    {"metric_type": "ai_usage", "period": "daily"}
                )
                
                # Analysis by type
                analysis_by_type_query = text("""
                    SELECT 
                        analysis_type,
                        COUNT(*) as count
                    FROM ai_analysis_cache 
                    WHERE DATE(created_at) = CURRENT_DATE
                    GROUP BY analysis_type
                """)
                result = await session.execute(analysis_by_type_query)
                
                for row in result:
                    self.record_metric(
                        "analysis.requests_by_type",
                        row.count,
                        MetricType.GAUGE,
                        {
                            "analysis_type": row.analysis_type,
                            "metric_type": "ai_usage",
                            "period": "daily"
                        }
                    )
                
                # Average confidence score
                avg_confidence_query = text("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM ai_analysis_cache 
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND confidence_score IS NOT NULL
                """)
                result = await session.execute(avg_confidence_query)
                avg_confidence = result.scalar() or 0
                
                self.record_metric(
                    "analysis.average_confidence",
                    float(avg_confidence),
                    MetricType.GAUGE,
                    {"metric_type": "ai_quality", "period": "daily"}
                )
                
                # Average processing time
                avg_processing_time_query = text("""
                    SELECT AVG(processing_time_ms) as avg_time
                    FROM ai_analysis_cache 
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND processing_time_ms IS NOT NULL
                """)
                result = await session.execute(avg_processing_time_query)
                avg_processing_time = result.scalar() or 0
                
                self.record_metric(
                    "analysis.average_processing_time_ms",
                    float(avg_processing_time),
                    MetricType.GAUGE,
                    {"metric_type": "ai_performance", "period": "daily"}
                )
                
        except Exception as e:
            logger.error(f"Failed to collect analysis metrics: {e}")
    
    async def collect_subscription_metrics(self):
        """Collect subscription-related metrics."""
        try:
            async with get_db_session() as session:
                # Subscription distribution
                subscription_dist_query = text("""
                    SELECT 
                        p.plan_name,
                        COUNT(s.id) as subscriber_count
                    FROM subscriptions s
                    JOIN plans p ON s.plan_id = p.id
                    WHERE s.status = 'active'
                    GROUP BY p.plan_name
                """)
                result = await session.execute(subscription_dist_query)
                
                for row in result:
                    self.record_metric(
                        "subscriptions.active_by_plan",
                        row.subscriber_count,
                        MetricType.GAUGE,
                        {
                            "plan_name": row.plan_name,
                            "metric_type": "subscription_distribution"
                        }
                    )
                
                # Monthly recurring revenue (MRR)
                mrr_query = text("""
                    SELECT SUM(p.price_monthly) as mrr
                    FROM subscriptions s
                    JOIN plans p ON s.plan_id = p.id
                    WHERE s.status = 'active'
                """)
                result = await session.execute(mrr_query)
                mrr = result.scalar() or 0
                
                self.record_metric(
                    "revenue.monthly_recurring",
                    float(mrr),
                    MetricType.GAUGE,
                    {"metric_type": "revenue", "currency": "JPY"}
                )
                
                # Churn rate (last 30 days)
                churn_query = text("""
                    SELECT 
                        COUNT(CASE WHEN s.status = 'cancelled' AND s.updated_at >= NOW() - INTERVAL '30 days' THEN 1 END) as churned,
                        COUNT(*) as total
                    FROM subscriptions s
                    WHERE s.created_at <= NOW() - INTERVAL '30 days'
                """)
                result = await session.execute(churn_query)
                row = result.fetchone()
                
                if row and row.total > 0:
                    churn_rate = (row.churned / row.total) * 100
                    self.record_metric(
                        "subscriptions.churn_rate_percent",
                        churn_rate,
                        MetricType.GAUGE,
                        {"metric_type": "subscription_health", "period": "30_days"}
                    )
                
        except Exception as e:
            logger.error(f"Failed to collect subscription metrics: {e}")
    
    async def collect_performance_metrics(self):
        """Collect application performance metrics."""
        try:
            async with get_db_session() as session:
                # API response times (last hour)
                response_times_query = text("""
                    SELECT 
                        AVG(response_time_ms) as avg_response_time,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time,
                        COUNT(*) as request_count
                    FROM api_usage_logs 
                    WHERE request_timestamp >= NOW() - INTERVAL '1 hour'
                """)
                result = await session.execute(response_times_query)
                row = result.fetchone()
                
                if row:
                    self.record_metric(
                        "api.response_time_avg_ms",
                        float(row.avg_response_time or 0),
                        MetricType.GAUGE,
                        {"metric_type": "performance", "period": "hourly"}
                    )
                    
                    self.record_metric(
                        "api.response_time_p95_ms",
                        float(row.p95_response_time or 0),
                        MetricType.GAUGE,
                        {"metric_type": "performance", "period": "hourly"}
                    )
                    
                    self.record_metric(
                        "api.request_count_hourly",
                        row.request_count,
                        MetricType.GAUGE,
                        {"metric_type": "traffic", "period": "hourly"}
                    )
                
                # Error rates (last hour)
                error_rate_query = text("""
                    SELECT 
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
                        COUNT(*) as total_count
                    FROM api_usage_logs 
                    WHERE request_timestamp >= NOW() - INTERVAL '1 hour'
                """)
                result = await session.execute(error_rate_query)
                row = result.fetchone()
                
                if row and row.total_count > 0:
                    error_rate = (row.error_count / row.total_count) * 100
                    self.record_metric(
                        "api.error_rate_percent",
                        error_rate,
                        MetricType.GAUGE,
                        {"metric_type": "reliability", "period": "hourly"}
                    )
                
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
    
    async def collect_cost_metrics(self):
        """Collect cost-related metrics."""
        try:
            async with get_db_session() as session:
                # Daily AI costs
                daily_ai_cost_query = text("""
                    SELECT SUM(cost_usd) as total_cost
                    FROM ai_analysis_cache 
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND cost_usd IS NOT NULL
                """)
                result = await session.execute(daily_ai_cost_query)
                daily_ai_cost = result.scalar() or 0
                
                self.record_metric(
                    "costs.ai_daily_usd",
                    float(daily_ai_cost),
                    MetricType.GAUGE,
                    {"metric_type": "cost", "category": "ai", "period": "daily"}
                )
                
                # Monthly AI costs
                monthly_ai_cost_query = text("""
                    SELECT SUM(cost_usd) as total_cost
                    FROM ai_analysis_cache 
                    WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
                    AND cost_usd IS NOT NULL
                """)
                result = await session.execute(monthly_ai_cost_query)
                monthly_ai_cost = result.scalar() or 0
                
                self.record_metric(
                    "costs.ai_monthly_usd",
                    float(monthly_ai_cost),
                    MetricType.GAUGE,
                    {"metric_type": "cost", "category": "ai", "period": "monthly"}
                )
                
                # API usage costs (external APIs)
                api_cost_query = text("""
                    SELECT 
                        api_provider,
                        SUM(cost_usd) as total_cost
                    FROM api_usage_logs 
                    WHERE DATE(request_timestamp) = CURRENT_DATE
                    AND cost_usd IS NOT NULL
                    GROUP BY api_provider
                """)
                result = await session.execute(api_cost_query)
                
                for row in result:
                    self.record_metric(
                        "costs.api_daily_usd",
                        float(row.total_cost),
                        MetricType.GAUGE,
                        {
                            "metric_type": "cost",
                            "category": "api",
                            "provider": row.api_provider,
                            "period": "daily"
                        }
                    )
                
        except Exception as e:
            logger.error(f"Failed to collect cost metrics: {e}")
    
    async def collect_data_source_metrics(self):
        """Collect data source health and performance metrics."""
        try:
            async with get_db_session() as session:
                # Data source success rates (last hour)
                source_health_query = text("""
                    SELECT 
                        api_provider,
                        COUNT(CASE WHEN status_code < 400 THEN 1 END) as success_count,
                        COUNT(*) as total_count,
                        AVG(response_time_ms) as avg_response_time
                    FROM api_usage_logs 
                    WHERE request_timestamp >= NOW() - INTERVAL '1 hour'
                    AND api_provider IS NOT NULL
                    GROUP BY api_provider
                """)
                result = await session.execute(source_health_query)
                
                for row in result:
                    if row.total_count > 0:
                        success_rate = (row.success_count / row.total_count) * 100
                        
                        self.record_metric(
                            "data_source.success_rate_percent",
                            success_rate,
                            MetricType.GAUGE,
                            {
                                "provider": row.api_provider,
                                "metric_type": "data_source_health",
                                "period": "hourly"
                            }
                        )
                        
                        self.record_metric(
                            "data_source.response_time_avg_ms",
                            float(row.avg_response_time or 0),
                            MetricType.GAUGE,
                            {
                                "provider": row.api_provider,
                                "metric_type": "data_source_performance",
                                "period": "hourly"
                            }
                        )
                
        except Exception as e:
            logger.error(f"Failed to collect data source metrics: {e}")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType, tags: Dict[str, str]):
        """Record a business metric."""
        try:
            # Create metric object
            metric = BusinessMetric(
                name=name,
                value=value,
                metric_type=metric_type,
                tags=tags,
                timestamp=datetime.utcnow()
            )
            
            # Store in cache
            self.metrics_cache[name] = metric
            
            # Send to Datadog
            if metric_type == MetricType.GAUGE:
                datadog_apm.add_custom_metric(name, value, tags)
            elif metric_type == MetricType.COUNTER:
                datadog_apm.increment_counter(name, int(value), tags)
            elif metric_type == MetricType.HISTOGRAM:
                datadog_apm.record_histogram(name, value, tags)
            
            logger.debug(f"Recorded metric: {name} = {value}", tags=tags)
            
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
    
    def get_cached_metrics(self) -> Dict[str, BusinessMetric]:
        """Get cached metrics."""
        return self.metrics_cache.copy()
    
    async def get_metric_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric (if stored in database)."""
        # This would require a metrics storage table for historical data
        # For now, return empty list as we're focusing on real-time metrics
        return []


# Global metrics collector instance
business_metrics = BusinessMetricsCollector()


# Convenience functions for recording common business events
def record_user_action(action: str, user_id: str, metadata: Dict[str, Any] = None):
    """Record a user action metric."""
    business_metrics.record_metric(
        "user_actions.count",
        1,
        MetricType.COUNTER,
        {
            "action": action,
            "user_id": user_id,
            "metric_type": "user_engagement",
            **(metadata or {})
        }
    )


def record_analysis_request(ticker: str, analysis_type: str, processing_time_ms: float, success: bool):
    """Record an AI analysis request metric."""
    business_metrics.record_metric(
        "analysis.processing_time_ms",
        processing_time_ms,
        MetricType.HISTOGRAM,
        {
            "ticker": ticker,
            "analysis_type": analysis_type,
            "success": str(success),
            "metric_type": "ai_performance"
        }
    )


def record_subscription_event(event_type: str, plan_name: str, user_id: str):
    """Record a subscription event metric."""
    business_metrics.record_metric(
        "subscription_events.count",
        1,
        MetricType.COUNTER,
        {
            "event_type": event_type,
            "plan_name": plan_name,
            "user_id": user_id,
            "metric_type": "subscription_activity"
        }
    )