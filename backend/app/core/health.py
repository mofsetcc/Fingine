"""
Comprehensive system health checks and monitoring.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.config import settings
from app.adapters.registry import registry as data_source_registry


async def check_database_health() -> Dict[str, Any]:
    """Check database connection and basic functionality."""
    try:
        async with get_db_session() as session:
            # Test basic connection
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            
            # Test table existence
            result = await session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            
            # Test plans table (should have default data)
            result = await session.execute(text("SELECT COUNT(*) FROM plans"))
            plans_count = result.scalar()
            
            return {
                "status": "healthy",
                "database_url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "hidden",
                "tables_count": table_count,
                "plans_count": plans_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connection using the cache manager."""
    try:
        from app.core.cache import cache_manager
        return await cache_manager.get_cache_health()
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


class ServiceStatus(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


async def check_data_sources_health() -> Dict[str, Any]:
    """Check health of all registered data sources."""
    try:
        registry_status = data_source_registry.get_registry_status()
        
        # Count healthy vs unhealthy adapters
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        total_count = len(registry_status["adapters"])
        
        adapter_details = {}
        
        for adapter_name, adapter_info in registry_status["adapters"].items():
            health_status = adapter_info["health_status"]
            adapter_details[adapter_name] = {
                "status": health_status,
                "type": adapter_info["type"],
                "enabled": adapter_info["enabled"],
                "last_check": adapter_info["last_health_check"],
                "response_time_ms": adapter_info["response_time_ms"],
                "error": adapter_info["error_message"]
            }
            
            if health_status == "healthy":
                healthy_count += 1
            elif health_status == "degraded":
                degraded_count += 1
            elif health_status == "unhealthy":
                unhealthy_count += 1
        
        # Determine overall data sources status
        if unhealthy_count == 0 and degraded_count == 0:
            overall_status = ServiceStatus.HEALTHY.value
        elif unhealthy_count == 0 and degraded_count > 0:
            overall_status = ServiceStatus.DEGRADED.value
        elif unhealthy_count < total_count / 2:  # Less than half unhealthy
            overall_status = ServiceStatus.DEGRADED.value
        else:
            overall_status = ServiceStatus.UNHEALTHY.value
        
        return {
            "status": overall_status,
            "summary": {
                "total": total_count,
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count
            },
            "adapters": adapter_details,
            "circuit_breakers": registry_status["circuit_breakers"],
            "failover_enabled": registry_status["failover_enabled"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": ServiceStatus.UNHEALTHY.value,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def check_external_apis_health() -> Dict[str, Any]:
    """Check health of external API dependencies."""
    try:
        # Test key external services
        external_services = {}
        
        # Check Google Gemini API (if configured)
        try:
            import google.generativeai as genai
            if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
                # Simple test to check if API is accessible
                start_time = time.time()
                # We'll just check if we can initialize the client
                model = genai.GenerativeModel('gemini-pro')
                response_time = (time.time() - start_time) * 1000
                
                external_services["gemini_api"] = {
                    "status": ServiceStatus.HEALTHY.value,
                    "response_time_ms": response_time,
                    "last_check": datetime.utcnow().isoformat()
                }
            else:
                external_services["gemini_api"] = {
                    "status": ServiceStatus.UNKNOWN.value,
                    "error": "API key not configured",
                    "last_check": datetime.utcnow().isoformat()
                }
        except Exception as e:
            external_services["gemini_api"] = {
                "status": ServiceStatus.UNHEALTHY.value,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        # Determine overall external APIs status
        statuses = [service["status"] for service in external_services.values()]
        if all(status == ServiceStatus.HEALTHY.value for status in statuses):
            overall_status = ServiceStatus.HEALTHY.value
        elif any(status == ServiceStatus.UNHEALTHY.value for status in statuses):
            overall_status = ServiceStatus.DEGRADED.value
        else:
            overall_status = ServiceStatus.DEGRADED.value
        
        return {
            "status": overall_status,
            "services": external_services,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": ServiceStatus.UNHEALTHY.value,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage."""
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Determine status based on resource usage
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            status = ServiceStatus.UNHEALTHY.value
        elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 80:
            status = ServiceStatus.DEGRADED.value
        else:
            status = ServiceStatus.HEALTHY.value
        
        return {
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_free_gb": disk.free / (1024**3),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ImportError:
        # psutil not available
        return {
            "status": ServiceStatus.UNKNOWN.value,
            "error": "psutil not available for system monitoring",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": ServiceStatus.UNHEALTHY.value,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status."""
    start_time = time.time()
    
    # Run all health checks concurrently
    db_health, redis_health, data_sources_health, external_apis_health, system_resources = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_data_sources_health(),
        check_external_apis_health(),
        check_system_resources(),
        return_exceptions=True
    )
    
    # Handle any exceptions from health checks
    services = {}
    
    if isinstance(db_health, Exception):
        services["database"] = {"status": ServiceStatus.UNHEALTHY.value, "error": str(db_health)}
    else:
        services["database"] = db_health
    
    if isinstance(redis_health, Exception):
        services["redis"] = {"status": ServiceStatus.UNHEALTHY.value, "error": str(redis_health)}
    else:
        services["redis"] = redis_health
    
    if isinstance(data_sources_health, Exception):
        services["data_sources"] = {"status": ServiceStatus.UNHEALTHY.value, "error": str(data_sources_health)}
    else:
        services["data_sources"] = data_sources_health
    
    if isinstance(external_apis_health, Exception):
        services["external_apis"] = {"status": ServiceStatus.UNHEALTHY.value, "error": str(external_apis_health)}
    else:
        services["external_apis"] = external_apis_health
    
    if isinstance(system_resources, Exception):
        services["system_resources"] = {"status": ServiceStatus.UNKNOWN.value, "error": str(system_resources)}
    else:
        services["system_resources"] = system_resources
    
    # Determine overall system status
    service_statuses = [service.get("status", ServiceStatus.UNKNOWN.value) for service in services.values()]
    
    if all(status == ServiceStatus.HEALTHY.value for status in service_statuses):
        overall_status = ServiceStatus.HEALTHY.value
    elif any(status == ServiceStatus.UNHEALTHY.value for status in service_statuses):
        overall_status = ServiceStatus.UNHEALTHY.value
    else:
        overall_status = ServiceStatus.DEGRADED.value
    
    total_time = (time.time() - start_time) * 1000
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "health_check_duration_ms": total_time,
        "services": services,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "version": getattr(settings, 'VERSION', 'unknown')
    }


if __name__ == "__main__":
    async def main():
        health = await get_system_health()
        print(f"System Status: {health['status']}")
        print(f"Database: {health['services']['database']['status']}")
        print(f"Redis: {health['services']['redis']['status']}")
        
        if health["status"] == "unhealthy":
            print("\n❌ System is unhealthy!")
            if health['services']['database']['status'] == 'unhealthy':
                print(f"Database Error: {health['services']['database'].get('error')}")
            if health['services']['redis']['status'] == 'unhealthy':
                print(f"Redis Error: {health['services']['redis'].get('error')}")
        else:
            print("\n✅ All systems healthy!")
    
    asyncio.run(main())