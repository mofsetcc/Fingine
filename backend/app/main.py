"""
Main FastAPI application entry point for Project Kessan.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.logging_middleware import LoggingMiddleware
from app.core.error_middleware import ErrorHandlingMiddleware
from app.core.rate_limiting import RateLimitMiddleware
from app.core.input_validation import InputValidationMiddleware
from app.core.https_middleware import SecurityHeadersMiddleware, HTTPSRedirectMiddleware
from app.core.jwt_middleware import JWTMiddleware
from app.api.v1 import api_router

# Set up structured logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title="Project Kessan API",
    description="AI-Powered Japanese Stock Trend Analysis Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add security middleware (order matters - most specific first)

# HTTPS enforcement (only in production)
if not settings.DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware, force_https=True)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-New-Access-Token", "X-New-Refresh-Token", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Input validation middleware
app.add_middleware(InputValidationMiddleware)

# JWT authentication middleware
app.add_middleware(JWTMiddleware)

# Error handling middleware
app.add_middleware(
    ErrorHandlingMiddleware,
    enable_graceful_degradation=settings.ENABLE_GRACEFUL_DEGRADATION
)

# Logging middleware (should be last to capture all request/response data)
app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health", "/health/detailed", "/docs", "/redoc", "/openapi.json"]
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    import structlog
    logger = structlog.get_logger(__name__)
    
    # Initialize cache
    from app.core.cache import cache
    try:
        await cache.connect()
        logger.info("Redis cache connected successfully")
    except Exception as e:
        # Log error but don't fail startup - cache is not critical
        logger.warning("Failed to connect to Redis cache", error=str(e))
    
    # Initialize Datadog APM
    from app.core.datadog_apm import datadog_apm
    if datadog_apm.enabled:
        logger.info("Datadog APM initialized", service=datadog_apm.service_name)
    
    # Initialize business metrics collection
    from app.services.business_metrics import business_metrics
    import asyncio
    asyncio.create_task(business_metrics.start_collection())
    logger.info("Business metrics collection started")
    
    # Initialize performance alerts
    from app.core.alerting import alert_manager
    from app.core.performance_alerts import initialize_performance_alerts
    performance_alert_manager = initialize_performance_alerts(alert_manager)
    asyncio.create_task(performance_alert_manager.start_monitoring())
    logger.info("Performance alert monitoring started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    import structlog
    logger = structlog.get_logger(__name__)
    
    # Stop monitoring services
    from app.services.business_metrics import business_metrics
    from app.core.performance_alerts import performance_alerts
    
    business_metrics.stop_collection()
    if performance_alerts:
        performance_alerts.stop_monitoring()
    
    logger.info("Monitoring services stopped")
    
    # Disconnect cache
    from app.core.cache import cache
    try:
        await cache.disconnect()
    except Exception:
        pass  # Ignore errors during shutdown


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "Project Kessan API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "kessan-api",
        "version": "1.0.0"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database and Redis."""
    from app.core.health import get_system_health
    return await get_system_health()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )