"""
Health check endpoints for monitoring.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import registry as data_source_registry
from app.core.database import check_database_health, get_database_stats, get_db
from app.core.deps import get_current_user
from app.core.health import (
    ServiceStatus,
    check_data_sources_health,
    check_external_apis_health,
    check_system_resources,
    get_system_health,
)
from app.models.user import User
from app.services.database_monitor import db_monitor

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint for load balancers."""
    return {"status": "healthy", "service": "kessan-backend"}


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": "2025-01-28T10:00:00Z"}


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check critical dependencies
        db_health = await check_database_health()

        if db_health["status"] != "healthy":
            raise HTTPException(status_code=503, detail="Database not ready")

        return {"status": "ready", "timestamp": "2025-01-28T10:00:00Z"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@router.get("/health/database")
async def database_health():
    """Database health check endpoint."""
    health_status = await check_database_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@router.get("/health/detailed")
async def detailed_health_check(current_user: User = Depends(get_current_user)):
    """Detailed health check with database metrics (admin only)."""
    # Only allow admin users to access detailed metrics
    # For now, we'll allow any authenticated user

    try:
        # Get database health
        db_health = await check_database_health()

        # Get monitoring metrics
        monitoring_metrics = await db_monitor.check_performance_metrics()

        # Get database statistics
        db_stats = await get_database_stats()

        return {
            "status": "healthy",
            "timestamp": monitoring_metrics.get("timestamp"),
            "database_health": db_health,
            "monitoring_metrics": monitoring_metrics,
            "database_stats": db_stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/health/performance")
async def performance_metrics(current_user: User = Depends(get_current_user)):
    """Get database performance metrics."""
    try:
        metrics = await db_monitor.check_performance_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/health/recommendations")
async def optimization_recommendations(current_user: User = Depends(get_current_user)):
    """Get database optimization recommendations."""
    try:
        recommendations = await db_monitor.get_optimization_recommendations()
        return {"recommendations": recommendations, "count": len(recommendations)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get recommendations: {str(e)}"
        )


@router.get("/health/system")
async def system_health_check():
    """Comprehensive system health check."""
    try:
        health_status = await get_system_health()

        # Return appropriate HTTP status code
        if health_status["status"] == ServiceStatus.UNHEALTHY.value:
            raise HTTPException(status_code=503, detail=health_status)
        elif health_status["status"] == ServiceStatus.DEGRADED.value:
            # Still return 200 for degraded status but include warning
            health_status["warning"] = "System is running in degraded mode"

        return health_status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/health/data-sources")
async def data_sources_health():
    """Check health of all data source adapters."""
    try:
        health_status = await check_data_sources_health()

        if health_status["status"] == ServiceStatus.UNHEALTHY.value:
            raise HTTPException(status_code=503, detail=health_status)

        return health_status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Data sources health check failed: {str(e)}"
        )


@router.get("/health/external-apis")
async def external_apis_health():
    """Check health of external API dependencies."""
    try:
        health_status = await check_external_apis_health()
        return health_status
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"External APIs health check failed: {str(e)}"
        )


@router.get("/health/resources")
async def system_resources_health():
    """Check system resource usage."""
    try:
        health_status = await check_system_resources()
        return health_status
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"System resources check failed: {str(e)}"
        )


@router.post("/health/data-sources/{adapter_name}/reset-circuit-breaker")
async def reset_adapter_circuit_breaker(
    adapter_name: str, current_user: User = Depends(get_current_user)
):
    """Reset circuit breaker for a specific data source adapter."""
    try:
        success = data_source_registry.reset_circuit_breaker(adapter_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker for adapter '{adapter_name}' was not open or adapter not found",
            )

        return {
            "status": "success",
            "message": f"Circuit breaker reset for adapter '{adapter_name}'",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset circuit breaker: {str(e)}"
        )


@router.post("/health/data-sources/{adapter_name}/enable")
async def enable_adapter(
    adapter_name: str, current_user: User = Depends(get_current_user)
):
    """Enable a specific data source adapter."""
    try:
        adapter = data_source_registry.get_adapter(adapter_name)

        if not adapter:
            raise HTTPException(
                status_code=404, detail=f"Adapter '{adapter_name}' not found"
            )

        adapter.enable()

        return {"status": "success", "message": f"Adapter '{adapter_name}' enabled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to enable adapter: {str(e)}"
        )


@router.post("/health/data-sources/{adapter_name}/disable")
async def disable_adapter(
    adapter_name: str, current_user: User = Depends(get_current_user)
):
    """Disable a specific data source adapter."""
    try:
        adapter = data_source_registry.get_adapter(adapter_name)

        if not adapter:
            raise HTTPException(
                status_code=404, detail=f"Adapter '{adapter_name}' not found"
            )

        adapter.disable()

        return {"status": "success", "message": f"Adapter '{adapter_name}' disabled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to disable adapter: {str(e)}"
        )


@router.get("/health/dashboard")
async def system_dashboard(current_user: User = Depends(get_current_user)):
    """Get comprehensive system status dashboard."""
    try:
        from app.services.system_monitor import system_monitor

        dashboard_data = await system_monitor.get_system_dashboard()
        return dashboard_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system dashboard: {str(e)}"
        )


@router.get("/health/metrics/{service_name}")
async def service_metrics(
    service_name: str,
    hours: int = Query(1, ge=1, le=24, description="Hours of history to retrieve"),
    current_user: User = Depends(get_current_user),
):
    """Get metrics for a specific service."""
    try:
        from app.services.system_monitor import system_monitor

        metrics = await system_monitor.get_service_metrics(service_name, hours)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get service metrics: {str(e)}"
        )


@router.get("/health/alerts")
async def recent_alerts(
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of alerts to return"
    ),
    current_user: User = Depends(get_current_user),
):
    """Get recent system alerts."""
    try:
        from app.services.system_monitor import system_monitor

        dashboard_data = await system_monitor.get_system_dashboard()
        alerts = dashboard_data.get("recent_alerts", [])
        return {"alerts": alerts[-limit:], "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/health/thresholds")
async def get_alert_thresholds(current_user: User = Depends(get_current_user)):
    """Get current alert thresholds."""
    try:
        from app.services.system_monitor import system_monitor

        thresholds = system_monitor.get_alert_thresholds()
        return {"thresholds": thresholds}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get alert thresholds: {str(e)}"
        )


@router.put("/health/thresholds")
async def update_alert_thresholds(
    thresholds: dict, current_user: User = Depends(get_current_user)
):
    """Update alert thresholds."""
    try:
        from app.services.system_monitor import system_monitor

        system_monitor.update_alert_thresholds(thresholds)
        return {
            "status": "success",
            "message": "Alert thresholds updated",
            "thresholds": system_monitor.get_alert_thresholds(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update alert thresholds: {str(e)}"
        )


@router.post("/health/monitoring/start")
async def start_monitoring(current_user: User = Depends(get_current_user)):
    """Start system monitoring."""
    try:
        from app.services.system_monitor import system_monitor

        await system_monitor.start_monitoring()
        return {"status": "success", "message": "System monitoring started"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/health/monitoring/stop")
async def stop_monitoring(current_user: User = Depends(get_current_user)):
    """Stop system monitoring."""
    try:
        from app.services.system_monitor import system_monitor

        await system_monitor.stop_monitoring()
        return {"status": "success", "message": "System monitoring stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop monitoring: {str(e)}"
        )


@router.post("/health/maintenance")
async def run_maintenance(current_user: User = Depends(get_current_user)):
    """Run database maintenance tasks (admin only)."""
    try:
        results = await db_monitor.run_maintenance_tasks()
        return {"status": "completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Maintenance failed: {str(e)}")
