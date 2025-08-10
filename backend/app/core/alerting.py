"""
Alerting system for critical errors and system events.
Supports Slack and PagerDuty integration.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from app.core.config import settings
from app.core.exceptions import ErrorSeverity, KessanException

logger = structlog.get_logger(__name__)


class AlertManager:
    """Manages alerts for critical system events and errors."""

    def __init__(self):
        self.slack_webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", None)
        self.pagerduty_integration_key = getattr(
            settings, "PAGERDUTY_INTEGRATION_KEY", None
        )
        self.alert_thresholds = {
            ErrorSeverity.LOW: False,
            ErrorSeverity.MEDIUM: False,
            ErrorSeverity.HIGH: True,
            ErrorSeverity.CRITICAL: True,
        }
        self.rate_limiter = AlertRateLimiter()

    async def send_alert(
        self, exception: KessanException, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send alert for exception if it meets criteria."""
        if not exception.should_alert:
            return

        if not self.alert_thresholds.get(exception.severity, False):
            return

        # Check rate limiting
        alert_key = f"{exception.__class__.__name__}:{exception.error_code}"
        if not await self.rate_limiter.should_alert(alert_key, exception.severity):
            logger.info(
                "Alert rate limited",
                alert_key=alert_key,
                severity=exception.severity.value,
            )
            return

        # Prepare alert data
        alert_data = self._prepare_alert_data(exception, context)

        # Send alerts concurrently
        tasks = []

        if self.slack_webhook_url:
            tasks.append(self._send_slack_alert(alert_data))

        if (
            self.pagerduty_integration_key
            and exception.severity == ErrorSeverity.CRITICAL
        ):
            tasks.append(self._send_pagerduty_alert(alert_data))

        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(
                    "Alerts sent", error_id=exception.error_id, alert_count=len(tasks)
                )
            except Exception as e:
                logger.error(
                    "Failed to send alerts", error=str(e), error_id=exception.error_id
                )

    def _prepare_alert_data(
        self, exception: KessanException, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare alert data from exception."""
        return {
            "error_id": exception.error_id,
            "error_code": exception.error_code,
            "message": exception.message,
            "category": exception.category.value,
            "severity": exception.severity.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": settings.ENVIRONMENT,
            "service": "kessan-api",
            "details": exception.details,
            "context": context or {},
            "exception_type": exception.__class__.__name__,
        }

    async def _send_slack_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to Slack."""
        try:
            # Determine color based on severity
            color_map = {
                "low": "#36a64f",  # Green
                "medium": "#ff9500",  # Orange
                "high": "#ff0000",  # Red
                "critical": "#8B0000",  # Dark Red
            }

            color = color_map.get(alert_data["severity"], "#ff0000")

            # Build Slack message
            slack_message = {
                "username": "Kessan Alert Bot",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 {alert_data['severity'].upper()} Alert",
                        "title_link": f"https://app.datadoghq.com/logs?query=error_id:{alert_data['error_id']}",
                        "text": alert_data["message"],
                        "fields": [
                            {
                                "title": "Error ID",
                                "value": alert_data["error_id"],
                                "short": True,
                            },
                            {
                                "title": "Error Code",
                                "value": alert_data["error_code"],
                                "short": True,
                            },
                            {
                                "title": "Category",
                                "value": alert_data["category"],
                                "short": True,
                            },
                            {
                                "title": "Environment",
                                "value": alert_data["environment"],
                                "short": True,
                            },
                            {
                                "title": "Service",
                                "value": alert_data["service"],
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": alert_data["timestamp"],
                                "short": True,
                            },
                        ],
                        "footer": "Project Kessan",
                        "ts": int(datetime.now(timezone.utc).timestamp()),
                    }
                ],
            }

            # Add details if present
            if alert_data.get("details"):
                details_text = "\n".join(
                    [f"• {k}: {v}" for k, v in alert_data["details"].items()]
                )
                slack_message["attachments"][0]["fields"].append(
                    {
                        "title": "Details",
                        "value": f"```{details_text}```",
                        "short": False,
                    }
                )

            # Add context if present
            if alert_data.get("context"):
                context_text = "\n".join(
                    [f"• {k}: {v}" for k, v in alert_data["context"].items()]
                )
                slack_message["attachments"][0]["fields"].append(
                    {
                        "title": "Context",
                        "value": f"```{context_text}```",
                        "short": False,
                    }
                )

            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook_url,
                    json=slack_message,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        logger.error(
                            "Failed to send Slack alert",
                            status_code=response.status,
                            response_text=await response.text(),
                        )
                    else:
                        logger.info(
                            "Slack alert sent successfully",
                            error_id=alert_data["error_id"],
                        )

        except Exception as e:
            logger.error(
                "Exception sending Slack alert",
                error=str(e),
                error_id=alert_data["error_id"],
            )

    async def _send_pagerduty_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to PagerDuty."""
        try:
            # Build PagerDuty event
            pagerduty_event = {
                "routing_key": self.pagerduty_integration_key,
                "event_action": "trigger",
                "dedup_key": f"kessan-{alert_data['error_code']}-{alert_data['error_id']}",
                "payload": {
                    "summary": f"[{alert_data['severity'].upper()}] {alert_data['message']}",
                    "source": alert_data["service"],
                    "severity": self._map_severity_to_pagerduty(alert_data["severity"]),
                    "component": alert_data["category"],
                    "group": "kessan-api",
                    "class": alert_data["exception_type"],
                    "custom_details": {
                        "error_id": alert_data["error_id"],
                        "error_code": alert_data["error_code"],
                        "environment": alert_data["environment"],
                        "timestamp": alert_data["timestamp"],
                        "details": alert_data.get("details", {}),
                        "context": alert_data.get("context", {}),
                    },
                },
                "client": "Kessan API",
                "client_url": f"https://app.datadoghq.com/logs?query=error_id:{alert_data['error_id']}",
            }

            # Send to PagerDuty
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=pagerduty_event,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 202:
                        logger.error(
                            "Failed to send PagerDuty alert",
                            status_code=response.status,
                            response_text=await response.text(),
                        )
                    else:
                        logger.info(
                            "PagerDuty alert sent successfully",
                            error_id=alert_data["error_id"],
                        )

        except Exception as e:
            logger.error(
                "Exception sending PagerDuty alert",
                error=str(e),
                error_id=alert_data["error_id"],
            )

    def _map_severity_to_pagerduty(self, severity: str) -> str:
        """Map internal severity to PagerDuty severity."""
        mapping = {
            "low": "info",
            "medium": "warning",
            "high": "error",
            "critical": "critical",
        }
        return mapping.get(severity, "error")


class AlertRateLimiter:
    """Rate limiter for alerts to prevent spam."""

    def __init__(self):
        self.alert_counts = {}
        self.rate_limits = {
            ErrorSeverity.LOW: {"count": 5, "window": 300},  # 5 per 5 minutes
            ErrorSeverity.MEDIUM: {"count": 3, "window": 300},  # 3 per 5 minutes
            ErrorSeverity.HIGH: {"count": 2, "window": 600},  # 2 per 10 minutes
            ErrorSeverity.CRITICAL: {"count": 1, "window": 300},  # 1 per 5 minutes
        }

    async def should_alert(self, alert_key: str, severity: ErrorSeverity) -> bool:
        """Check if alert should be sent based on rate limits."""
        now = datetime.now(timezone.utc).timestamp()
        rate_limit = self.rate_limits.get(severity, {"count": 1, "window": 300})

        # Clean old entries
        self._clean_old_entries(now)

        # Check current count for this alert key
        if alert_key not in self.alert_counts:
            self.alert_counts[alert_key] = []

        # Count alerts within the time window
        window_start = now - rate_limit["window"]
        recent_alerts = [
            timestamp
            for timestamp in self.alert_counts[alert_key]
            if timestamp > window_start
        ]

        # Check if we're within the rate limit
        if len(recent_alerts) >= rate_limit["count"]:
            return False

        # Add this alert to the count
        self.alert_counts[alert_key].append(now)
        return True

    def _clean_old_entries(self, current_time: float) -> None:
        """Clean old entries from alert counts."""
        max_window = max(limit["window"] for limit in self.rate_limits.values())
        cutoff_time = current_time - max_window

        for alert_key in list(self.alert_counts.keys()):
            self.alert_counts[alert_key] = [
                timestamp
                for timestamp in self.alert_counts[alert_key]
                if timestamp > cutoff_time
            ]

            # Remove empty entries
            if not self.alert_counts[alert_key]:
                del self.alert_counts[alert_key]


class SystemHealthAlerter:
    """Specialized alerter for system health events."""

    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager

    async def alert_database_connection_failure(
        self, error_details: Dict[str, Any]
    ) -> None:
        """Alert for database connection failures."""
        from app.core.exceptions import DatabaseConnectionException

        exception = DatabaseConnectionException(
            context=error_details, should_alert=True
        )
        await self.alert_manager.send_alert(exception, error_details)

    async def alert_cache_connection_failure(
        self, error_details: Dict[str, Any]
    ) -> None:
        """Alert for cache connection failures."""
        from app.core.exceptions import CacheConnectionException

        exception = CacheConnectionException(context=error_details, should_alert=True)
        await self.alert_manager.send_alert(exception, error_details)

    async def alert_external_api_failure(
        self,
        api_name: str,
        status_code: int,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Alert for external API failures."""
        from app.core.exceptions import ExternalAPIException

        exception = ExternalAPIException(
            api_name=api_name,
            status_code=status_code,
            error_message=error_message,
            context=context or {},
            should_alert=True,
        )
        await self.alert_manager.send_alert(exception, context)

    async def alert_budget_exceeded(
        self, budget_type: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Alert for budget exceeded events."""
        from app.core.exceptions import BudgetExceededException

        exception = BudgetExceededException(
            budget_type=budget_type, context=context or {}, should_alert=True
        )
        await self.alert_manager.send_alert(exception, context)

    async def alert_high_error_rate(
        self,
        error_rate: float,
        threshold: float,
        time_window: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Alert for high error rates."""
        from app.core.exceptions import ErrorCategory, ErrorSeverity, KessanException

        exception = KessanException(
            message=f"High error rate detected: {error_rate:.2%} (threshold: {threshold:.2%}) in {time_window}",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            details={
                "error_rate": error_rate,
                "threshold": threshold,
                "time_window": time_window,
            },
            user_message="System experiencing high error rates",
            should_alert=True,
            context=context or {},
        )
        await self.alert_manager.send_alert(exception, context)


# Global alert manager instance
alert_manager = AlertManager()
system_health_alerter = SystemHealthAlerter(alert_manager)
