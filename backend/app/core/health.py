"""
Database and system health checks.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings


async def check_database_health() -> Dict[str, Any]:
    """Check database connection and basic functionality."""
    try:
        async with AsyncSessionLocal() as session:
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
    """Check Redis connection."""
    try:
        import redis.asyncio as redis
        
        # Parse Redis URL
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Test connection
        await redis_client.ping()
        
        # Test basic operations
        await redis_client.set("health_check", "ok", ex=10)
        value = await redis_client.get("health_check")
        
        await redis_client.close()
        
        return {
            "status": "healthy",
            "redis_url": settings.REDIS_URL.split("@")[1] if "@" in settings.REDIS_URL else settings.REDIS_URL,
            "test_value": value.decode() if value else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status."""
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    
    overall_status = "healthy" if (
        db_health["status"] == "healthy" and 
        redis_health["status"] == "healthy"
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_health,
            "redis": redis_health
        },
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
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