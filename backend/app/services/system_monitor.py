"""
System monitoring and status dashboard service.
"""

import asyncio
import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.adapters.registry import registry as data_source_registry
from app.core.cache import cache_manager
from app.core.health import (
    ServiceStatus,
    check_data_sources_health,
    check_database_health,
    check_external_apis_health,
    check_system_resources,
    get_system_health,
)

logger = logging.getLogger(__name__)


class SystemMonitor:
    """System monitoring service with historical data tracking."""

    def __init__(self):
        """Initialize the system monitor."""
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._check_interval = 60  # 1 minute
        self._history_retention_hours = 24
        self._max_history_points = 1440  # 24 hours * 60 minutes

        # In-memory storage for recent health history
        self._health_history: deque = deque(maxlen=self._max_history_points)
        self._service_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._max_history_points)
        )

        # Alert thresholds
        self._alert_thresholds = {
            "response_time_ms": 5000,  # 5 seconds
            "error_rate_percent": 10,  # 10%
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90,
        }

        # Recent alerts
        self._recent_alerts: deque = deque(maxlen=100)

    async def start_monitoring(self) -> None:
        """Start background system monitoring."""
        if self._monitoring_active:
            logger.warning("System monitoring already active")
            return

        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started system monitoring")

    async def stop_monitoring(self) -> None:
        """Stop background system monitoring."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped system monitoring")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                await self._collect_health_metrics()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retrying

    async def _collect_health_metrics(self) -> None:
        """Collect and store health metrics."""
        try:
            # Get comprehensive system health
            health_data = await get_system_health()
            timestamp = datetime.utcnow()

            # Store in history
            health_point = {
                "timestamp": timestamp.isoformat(),
                "status": health_data["status"],
                "duration_ms": health_data.get("health_check_duration_ms", 0),
                "services": {},
            }

            # Extract service-specific metrics
            for service_name, service_data in health_data.get("services", {}).items():
                service_status = service_data.get("status", ServiceStatus.UNKNOWN.value)
                health_point["services"][service_name] = service_status

                # Store service-specific metrics
                service_metric = {
                    "timestamp": timestamp.isoformat(),
                    "status": service_status,
                    "response_time_ms": service_data.get("response_time_ms"),
                    "error": service_data.get("error"),
                }

                # Add service-specific data
                if service_name == "system_resources":
                    service_metric.update(
                        {
                            "cpu_percent": service_data.get("cpu_percent"),
                            "memory_percent": service_data.get("memory_percent"),
                            "disk_percent": service_data.get("disk_percent"),
                        }
                    )
                elif service_name == "data_sources":
                    service_metric.update(
                        {
                            "healthy_count": service_data.get("summary", {}).get(
                                "healthy", 0
                            ),
                            "total_count": service_data.get("summary", {}).get(
                                "total", 0
                            ),
                        }
                    )

                self._service_metrics[service_name].append(service_metric)

            self._health_history.append(health_point)

            # Check for alerts
            await self._check_alerts(health_data, timestamp)

            # Cache recent status for quick access
            await self._cache_current_status(health_data)

        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")

    async def _check_alerts(
        self, health_data: Dict[str, Any], timestamp: datetime
    ) -> None:
        """Check for alert conditions and record them."""
        alerts = []

        # Check overall system status
        if health_data["status"] == ServiceStatus.UNHEALTHY.value:
            alerts.append(
                {
                    "type": "system_unhealthy",
                    "severity": "critical",
                    "message": "System is in unhealthy state",
                    "timestamp": timestamp.isoformat(),
                }
            )
        elif health_data["status"] == ServiceStatus.DEGRADED.value:
            alerts.append(
                {
                    "type": "system_degraded",
                    "severity": "warning",
                    "message": "System is in degraded state",
                    "timestamp": timestamp.isoformat(),
                }
            )

        # Check response time
        duration_ms = health_data.get("health_check_duration_ms", 0)
        if duration_ms > self._alert_thresholds["response_time_ms"]:
            alerts.append(
                {
                    "type": "slow_response",
                    "severity": "warning",
                    "message": f"Health check took {duration_ms:.0f}ms (threshold: {self._alert_thresholds['response_time_ms']}ms)",
                    "timestamp": timestamp.isoformat(),
                    "value": duration_ms,
                }
            )

        # Check system resources
        resources = health_data.get("services", {}).get("system_resources", {})
        if resources.get("cpu_percent", 0) > self._alert_thresholds["cpu_percent"]:
            alerts.append(
                {
                    "type": "high_cpu",
                    "severity": "warning",
                    "message": f"High CPU usage: {resources['cpu_percent']:.1f}%",
                    "timestamp": timestamp.isoformat(),
                    "value": resources["cpu_percent"],
                }
            )

        if (
            resources.get("memory_percent", 0)
            > self._alert_thresholds["memory_percent"]
        ):
            alerts.append(
                {
                    "type": "high_memory",
                    "severity": "warning",
                    "message": f"High memory usage: {resources['memory_percent']:.1f}%",
                    "timestamp": timestamp.isoformat(),
                    "value": resources["memory_percent"],
                }
            )

        if resources.get("disk_percent", 0) > self._alert_thresholds["disk_percent"]:
            alerts.append(
                {
                    "type": "high_disk",
                    "severity": "critical",
                    "message": f"High disk usage: {resources['disk_percent']:.1f}%",
                    "timestamp": timestamp.isoformat(),
                    "value": resources["disk_percent"],
                }
            )

        # Check data sources
        data_sources = health_data.get("services", {}).get("data_sources", {})
        summary = data_sources.get("summary", {})
        if summary.get("unhealthy", 0) > 0:
            alerts.append(
                {
                    "type": "data_sources_unhealthy",
                    "severity": "warning",
                    "message": f"{summary['unhealthy']} data sources are unhealthy",
                    "timestamp": timestamp.isoformat(),
                    "value": summary["unhealthy"],
                }
            )

        # Store alerts
        for alert in alerts:
            self._recent_alerts.append(alert)
            logger.warning(f"Alert: {alert['message']}")

    async def _cache_current_status(self, health_data: Dict[str, Any]) -> None:
        """Cache current system status for quick access."""
        try:
            cache_key = "system:health:current"
            await cache_manager.set(cache_key, health_data, ttl=120)  # 2 minutes TTL
        except Exception as e:
            logger.error(f"Failed to cache system status: {e}")

    async def get_system_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive system dashboard data."""
        try:
            # Get current status (from cache if available)
            current_status = await self._get_cached_status()

            # Get historical data
            history_data = self._get_history_summary()

            # Get recent alerts
            recent_alerts = list(self._recent_alerts)[-10:]  # Last 10 alerts

            # Get data source status
            data_source_status = data_source_registry.get_registry_status()

            return {
                "current_status": current_status,
                "history": history_data,
                "recent_alerts": recent_alerts,
                "data_sources": {
                    "adapters": data_source_status["adapters"],
                    "circuit_breakers": data_source_status["circuit_breakers"],
                    "failover_enabled": data_source_status["failover_enabled"],
                },
                "monitoring": {
                    "active": self._monitoring_active,
                    "check_interval_seconds": self._check_interval,
                    "history_points": len(self._health_history),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get system dashboard: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    async def _get_cached_status(self) -> Optional[Dict[str, Any]]:
        """Get cached system status."""
        try:
            cache_key = "system:health:current"
            cached_status = await cache_manager.get(cache_key)
            if cached_status:
                return cached_status
        except Exception as e:
            logger.error(f"Failed to get cached status: {e}")

        # Fallback to fresh health check
        try:
            return await get_system_health()
        except Exception as e:
            logger.error(f"Failed to get fresh system health: {e}")
            return None

    def _get_history_summary(self) -> Dict[str, Any]:
        """Get summary of historical health data."""
        if not self._health_history:
            return {"points": 0, "time_range": None}

        history_list = list(self._health_history)

        # Calculate uptime percentage
        total_points = len(history_list)
        healthy_points = sum(
            1
            for point in history_list
            if point["status"] == ServiceStatus.HEALTHY.value
        )
        uptime_percentage = (
            (healthy_points / total_points * 100) if total_points > 0 else 0
        )

        # Get time range
        oldest_point = history_list[0]["timestamp"] if history_list else None
        newest_point = history_list[-1]["timestamp"] if history_list else None

        # Calculate average response time
        response_times = [
            point["duration_ms"] for point in history_list if point.get("duration_ms")
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Status distribution
        status_counts = defaultdict(int)
        for point in history_list:
            status_counts[point["status"]] += 1

        return {
            "points": total_points,
            "time_range": {"start": oldest_point, "end": newest_point},
            "uptime_percentage": round(uptime_percentage, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "status_distribution": dict(status_counts),
        }

    async def get_service_metrics(
        self, service_name: str, hours: int = 1
    ) -> Dict[str, Any]:
        """Get metrics for a specific service."""
        if service_name not in self._service_metrics:
            return {"error": f"No metrics available for service: {service_name}"}

        # Get metrics within time range
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        service_history = list(self._service_metrics[service_name])

        filtered_metrics = [
            metric
            for metric in service_history
            if datetime.fromisoformat(metric["timestamp"]) > cutoff_time
        ]

        if not filtered_metrics:
            return {"service": service_name, "metrics": [], "summary": None}

        # Calculate summary statistics
        response_times = [
            m["response_time_ms"] for m in filtered_metrics if m.get("response_time_ms")
        ]
        error_count = sum(1 for m in filtered_metrics if m.get("error"))

        summary = {
            "total_points": len(filtered_metrics),
            "error_count": error_count,
            "error_rate_percent": (error_count / len(filtered_metrics) * 100)
            if filtered_metrics
            else 0,
            "avg_response_time_ms": sum(response_times) / len(response_times)
            if response_times
            else None,
            "max_response_time_ms": max(response_times) if response_times else None,
            "min_response_time_ms": min(response_times) if response_times else None,
        }

        return {
            "service": service_name,
            "time_range_hours": hours,
            "metrics": filtered_metrics,
            "summary": summary,
        }

    def get_alert_thresholds(self) -> Dict[str, Any]:
        """Get current alert thresholds."""
        return self._alert_thresholds.copy()

    def update_alert_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """Update alert thresholds."""
        self._alert_thresholds.update(thresholds)
        logger.info(f"Updated alert thresholds: {thresholds}")


# Global system monitor instance
system_monitor = SystemMonitor()
