"""
Performance alerting rules and monitoring for application health.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.core.alerting import AlertManager, AlertSeverity
from app.core.datadog_apm import datadog_apm
from app.core.logging import get_logger
from app.services.business_metrics import business_metrics

logger = get_logger(__name__)


class AlertCondition(Enum):
    """Types of alert conditions."""

    THRESHOLD_ABOVE = "above"
    THRESHOLD_BELOW = "below"
    PERCENTAGE_CHANGE = "percentage_change"
    RATE_OF_CHANGE = "rate_of_change"
    ANOMALY_DETECTION = "anomaly"


@dataclass
class PerformanceAlert:
    """Performance alert configuration."""

    name: str
    metric_name: str
    condition: AlertCondition
    threshold: float
    severity: AlertSeverity
    description: str
    tags: Dict[str, str]
    cooldown_minutes: int = 15
    evaluation_window_minutes: int = 5
    min_data_points: int = 3
    enabled: bool = True


@dataclass
class AlertState:
    """Current state of an alert."""

    alert: PerformanceAlert
    is_triggered: bool
    last_triggered: Optional[datetime]
    last_resolved: Optional[datetime]
    trigger_count: int
    current_value: Optional[float]
    historical_values: List[float]


class PerformanceAlertManager:
    """Manages performance alerts and monitoring rules."""

    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.alert_states: Dict[str, AlertState] = {}
        self.is_monitoring = False
        self.check_interval = 60  # Check every minute

        # Initialize default alerts
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """Setup default performance alerts."""
        default_alerts = [
            # API Performance Alerts
            PerformanceAlert(
                name="high_api_response_time",
                metric_name="api.response_time_avg_ms",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=1000.0,  # 1 second
                severity=AlertSeverity.WARNING,
                description="API average response time is above 1 second",
                tags={"category": "performance", "component": "api"},
                evaluation_window_minutes=5,
            ),
            PerformanceAlert(
                name="critical_api_response_time",
                metric_name="api.response_time_p95_ms",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=3000.0,  # 3 seconds
                severity=AlertSeverity.CRITICAL,
                description="API P95 response time is above 3 seconds",
                tags={"category": "performance", "component": "api"},
                evaluation_window_minutes=3,
            ),
            PerformanceAlert(
                name="high_error_rate",
                metric_name="api.error_rate_percent",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=5.0,  # 5%
                severity=AlertSeverity.WARNING,
                description="API error rate is above 5%",
                tags={"category": "reliability", "component": "api"},
                evaluation_window_minutes=5,
            ),
            PerformanceAlert(
                name="critical_error_rate",
                metric_name="api.error_rate_percent",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=15.0,  # 15%
                severity=AlertSeverity.CRITICAL,
                description="API error rate is above 15%",
                tags={"category": "reliability", "component": "api"},
                evaluation_window_minutes=3,
            ),
            # AI Analysis Performance Alerts
            PerformanceAlert(
                name="slow_ai_analysis",
                metric_name="analysis.average_processing_time_ms",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=30000.0,  # 30 seconds
                severity=AlertSeverity.WARNING,
                description="AI analysis processing time is above 30 seconds",
                tags={"category": "performance", "component": "ai"},
                evaluation_window_minutes=10,
            ),
            PerformanceAlert(
                name="low_ai_confidence",
                metric_name="analysis.average_confidence",
                condition=AlertCondition.THRESHOLD_BELOW,
                threshold=0.6,  # 60%
                severity=AlertSeverity.WARNING,
                description="AI analysis confidence is below 60%",
                tags={"category": "quality", "component": "ai"},
                evaluation_window_minutes=15,
            ),
            # Cost Alerts
            PerformanceAlert(
                name="high_daily_ai_cost",
                metric_name="costs.ai_daily_usd",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=80.0,  # $80 per day
                severity=AlertSeverity.WARNING,
                description="Daily AI costs are above $80",
                tags={"category": "cost", "component": "ai"},
                evaluation_window_minutes=60,
                cooldown_minutes=240,  # 4 hours cooldown
            ),
            PerformanceAlert(
                name="critical_daily_ai_cost",
                metric_name="costs.ai_daily_usd",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=95.0,  # $95 per day
                severity=AlertSeverity.CRITICAL,
                description="Daily AI costs are above $95 (near budget limit)",
                tags={"category": "cost", "component": "ai"},
                evaluation_window_minutes=30,
                cooldown_minutes=120,  # 2 hours cooldown
            ),
            # Data Source Health Alerts
            PerformanceAlert(
                name="data_source_failure",
                metric_name="data_source.success_rate_percent",
                condition=AlertCondition.THRESHOLD_BELOW,
                threshold=90.0,  # 90%
                severity=AlertSeverity.WARNING,
                description="Data source success rate is below 90%",
                tags={"category": "reliability", "component": "data_source"},
                evaluation_window_minutes=10,
            ),
            PerformanceAlert(
                name="critical_data_source_failure",
                metric_name="data_source.success_rate_percent",
                condition=AlertCondition.THRESHOLD_BELOW,
                threshold=70.0,  # 70%
                severity=AlertSeverity.CRITICAL,
                description="Data source success rate is below 70%",
                tags={"category": "reliability", "component": "data_source"},
                evaluation_window_minutes=5,
            ),
            # User Experience Alerts
            PerformanceAlert(
                name="low_daily_active_users",
                metric_name="users.daily_active",
                condition=AlertCondition.PERCENTAGE_CHANGE,
                threshold=-30.0,  # 30% decrease
                severity=AlertSeverity.WARNING,
                description="Daily active users decreased by more than 30%",
                tags={"category": "engagement", "component": "users"},
                evaluation_window_minutes=60,
                cooldown_minutes=480,  # 8 hours cooldown
            ),
            PerformanceAlert(
                name="high_churn_rate",
                metric_name="subscriptions.churn_rate_percent",
                condition=AlertCondition.THRESHOLD_ABOVE,
                threshold=10.0,  # 10%
                severity=AlertSeverity.WARNING,
                description="Monthly churn rate is above 10%",
                tags={"category": "business", "component": "subscriptions"},
                evaluation_window_minutes=60,
                cooldown_minutes=1440,  # 24 hours cooldown
            ),
        ]

        # Initialize alert states
        for alert in default_alerts:
            self.alert_states[alert.name] = AlertState(
                alert=alert,
                is_triggered=False,
                last_triggered=None,
                last_resolved=None,
                trigger_count=0,
                current_value=None,
                historical_values=[],
            )

    async def start_monitoring(self):
        """Start the performance monitoring loop."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        logger.info("Starting performance alert monitoring")

        while self.is_monitoring:
            try:
                await self.check_all_alerts()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error

    def stop_monitoring(self):
        """Stop the performance monitoring."""
        self.is_monitoring = False
        logger.info("Stopped performance alert monitoring")

    async def check_all_alerts(self):
        """Check all configured alerts."""
        # Get current metrics
        current_metrics = business_metrics.get_cached_metrics()

        for alert_name, alert_state in self.alert_states.items():
            if not alert_state.alert.enabled:
                continue

            try:
                await self.check_alert(alert_state, current_metrics)
            except Exception as e:
                logger.error(f"Error checking alert {alert_name}: {e}")

    async def check_alert(self, alert_state: AlertState, current_metrics: Dict):
        """Check a specific alert condition."""
        alert = alert_state.alert

        # Get current metric value
        metric = current_metrics.get(alert.metric_name)
        if not metric:
            return

        current_value = metric.value
        alert_state.current_value = current_value

        # Update historical values
        alert_state.historical_values.append(current_value)

        # Keep only values within evaluation window
        cutoff_time = datetime.utcnow() - timedelta(
            minutes=alert.evaluation_window_minutes
        )
        # For simplicity, keep last N values (in production, you'd use timestamps)
        max_values = alert.evaluation_window_minutes
        if len(alert_state.historical_values) > max_values:
            alert_state.historical_values = alert_state.historical_values[-max_values:]

        # Check if we have enough data points
        if len(alert_state.historical_values) < alert.min_data_points:
            return

        # Evaluate alert condition
        should_trigger = await self.evaluate_condition(
            alert, alert_state, current_value
        )

        # Check cooldown period
        if alert_state.last_triggered:
            time_since_last = datetime.utcnow() - alert_state.last_triggered
            if time_since_last.total_seconds() < (alert.cooldown_minutes * 60):
                return

        # Handle alert state changes
        if should_trigger and not alert_state.is_triggered:
            await self.trigger_alert(alert_state, current_value)
        elif not should_trigger and alert_state.is_triggered:
            await self.resolve_alert(alert_state, current_value)

    async def evaluate_condition(
        self, alert: PerformanceAlert, alert_state: AlertState, current_value: float
    ) -> bool:
        """Evaluate if alert condition is met."""
        if alert.condition == AlertCondition.THRESHOLD_ABOVE:
            return current_value > alert.threshold

        elif alert.condition == AlertCondition.THRESHOLD_BELOW:
            return current_value < alert.threshold

        elif alert.condition == AlertCondition.PERCENTAGE_CHANGE:
            if len(alert_state.historical_values) < 2:
                return False

            # Compare current value to average of previous values
            previous_avg = sum(alert_state.historical_values[:-1]) / len(
                alert_state.historical_values[:-1]
            )
            if previous_avg == 0:
                return False

            percentage_change = ((current_value - previous_avg) / previous_avg) * 100

            if alert.threshold < 0:  # Negative threshold means decrease
                return percentage_change < alert.threshold
            else:  # Positive threshold means increase
                return percentage_change > alert.threshold

        elif alert.condition == AlertCondition.RATE_OF_CHANGE:
            if len(alert_state.historical_values) < 2:
                return False

            # Calculate rate of change per minute
            time_diff = 1  # Assuming 1 minute intervals
            value_diff = current_value - alert_state.historical_values[-2]
            rate = value_diff / time_diff

            return abs(rate) > alert.threshold

        elif alert.condition == AlertCondition.ANOMALY_DETECTION:
            # Simple anomaly detection using standard deviation
            if len(alert_state.historical_values) < 5:
                return False

            import statistics

            mean = statistics.mean(alert_state.historical_values[:-1])
            stdev = statistics.stdev(alert_state.historical_values[:-1])

            # Consider it an anomaly if current value is more than 2 standard deviations away
            z_score = abs(current_value - mean) / stdev if stdev > 0 else 0
            return z_score > 2.0

        return False

    async def trigger_alert(self, alert_state: AlertState, current_value: float):
        """Trigger an alert."""
        alert = alert_state.alert

        # Update alert state
        alert_state.is_triggered = True
        alert_state.last_triggered = datetime.utcnow()
        alert_state.trigger_count += 1

        # Create alert message
        message = f"{alert.description}\n"
        message += f"Current value: {current_value}\n"
        message += f"Threshold: {alert.threshold}\n"
        message += f"Metric: {alert.metric_name}\n"
        message += f"Tags: {alert.tags}"

        # Send alert
        await self.alert_manager.send_alert(
            title=f"Performance Alert: {alert.name}",
            message=message,
            severity=alert.severity,
            tags=alert.tags,
        )

        # Record metric for alert triggering
        datadog_apm.increment_counter(
            "alerts.triggered",
            1,
            {
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "metric_name": alert.metric_name,
            },
        )

        logger.warning(
            f"Performance alert triggered: {alert.name}",
            current_value=current_value,
            threshold=alert.threshold,
            metric=alert.metric_name,
        )

    async def resolve_alert(self, alert_state: AlertState, current_value: float):
        """Resolve an alert."""
        alert = alert_state.alert

        # Update alert state
        alert_state.is_triggered = False
        alert_state.last_resolved = datetime.utcnow()

        # Create resolution message
        message = f"{alert.description} - RESOLVED\n"
        message += f"Current value: {current_value}\n"
        message += f"Threshold: {alert.threshold}\n"
        message += f"Metric: {alert.metric_name}"

        # Send resolution notification
        await self.alert_manager.send_alert(
            title=f"Performance Alert Resolved: {alert.name}",
            message=message,
            severity=AlertSeverity.INFO,
            tags=alert.tags,
        )

        # Record metric for alert resolution
        datadog_apm.increment_counter(
            "alerts.resolved",
            1,
            {"alert_name": alert.name, "metric_name": alert.metric_name},
        )

        logger.info(
            f"Performance alert resolved: {alert.name}",
            current_value=current_value,
            threshold=alert.threshold,
            metric=alert.metric_name,
        )

    def add_custom_alert(self, alert: PerformanceAlert):
        """Add a custom performance alert."""
        self.alert_states[alert.name] = AlertState(
            alert=alert,
            is_triggered=False,
            last_triggered=None,
            last_resolved=None,
            trigger_count=0,
            current_value=None,
            historical_values=[],
        )

        logger.info(f"Added custom performance alert: {alert.name}")

    def remove_alert(self, alert_name: str):
        """Remove a performance alert."""
        if alert_name in self.alert_states:
            del self.alert_states[alert_name]
            logger.info(f"Removed performance alert: {alert_name}")

    def get_alert_status(self) -> Dict[str, Dict]:
        """Get current status of all alerts."""
        status = {}

        for alert_name, alert_state in self.alert_states.items():
            status[alert_name] = {
                "enabled": alert_state.alert.enabled,
                "is_triggered": alert_state.is_triggered,
                "last_triggered": alert_state.last_triggered.isoformat()
                if alert_state.last_triggered
                else None,
                "last_resolved": alert_state.last_resolved.isoformat()
                if alert_state.last_resolved
                else None,
                "trigger_count": alert_state.trigger_count,
                "current_value": alert_state.current_value,
                "threshold": alert_state.alert.threshold,
                "severity": alert_state.alert.severity.value,
                "description": alert_state.alert.description,
            }

        return status

    def enable_alert(self, alert_name: str):
        """Enable a specific alert."""
        if alert_name in self.alert_states:
            self.alert_states[alert_name].alert.enabled = True
            logger.info(f"Enabled performance alert: {alert_name}")

    def disable_alert(self, alert_name: str):
        """Disable a specific alert."""
        if alert_name in self.alert_states:
            self.alert_states[alert_name].alert.enabled = False
            logger.info(f"Disabled performance alert: {alert_name}")


# Global performance alert manager instance
performance_alerts: Optional[PerformanceAlertManager] = None


def initialize_performance_alerts(alert_manager: AlertManager):
    """Initialize the global performance alert manager."""
    global performance_alerts
    performance_alerts = PerformanceAlertManager(alert_manager)
    return performance_alerts


# Convenience functions for custom alerts
def add_custom_threshold_alert(
    name: str,
    metric_name: str,
    threshold: float,
    above: bool = True,
    severity: AlertSeverity = AlertSeverity.WARNING,
    description: str = None,
):
    """Add a custom threshold-based alert."""
    if not performance_alerts:
        logger.warning("Performance alerts not initialized")
        return

    alert = PerformanceAlert(
        name=name,
        metric_name=metric_name,
        condition=AlertCondition.THRESHOLD_ABOVE
        if above
        else AlertCondition.THRESHOLD_BELOW,
        threshold=threshold,
        severity=severity,
        description=description
        or f"Metric {metric_name} {'above' if above else 'below'} {threshold}",
        tags={"custom": "true", "metric": metric_name},
    )

    performance_alerts.add_custom_alert(alert)


def add_custom_percentage_change_alert(
    name: str,
    metric_name: str,
    percentage_threshold: float,
    severity: AlertSeverity = AlertSeverity.WARNING,
    description: str = None,
):
    """Add a custom percentage change alert."""
    if not performance_alerts:
        logger.warning("Performance alerts not initialized")
        return

    alert = PerformanceAlert(
        name=name,
        metric_name=metric_name,
        condition=AlertCondition.PERCENTAGE_CHANGE,
        threshold=percentage_threshold,
        severity=severity,
        description=description
        or f"Metric {metric_name} changed by {percentage_threshold}%",
        tags={"custom": "true", "metric": metric_name, "type": "percentage_change"},
    )

    performance_alerts.add_custom_alert(alert)
