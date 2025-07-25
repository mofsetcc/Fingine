"""Health check API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.health import HealthChecker
from app.schemas.api_response import APIResponse

router = APIRouter()


@router.get("/", response_model=APIResponse[dict])
async def health_check(db: Session = Depends(get_db)) -> APIResponse[dict]:
    """
    Health check endpoint.
    
    Returns the health status of the application and its dependencies.
    """
    health_checker = HealthChecker(db)
    health_status = await health_checker.check_health()
    
    return APIResponse(
        success=health_status["status"] == "healthy",
        message=f"Application is {health_status['status']}",
        data=health_status
    )


@router.get("/ready", response_model=APIResponse[dict])
async def readiness_check(db: Session = Depends(get_db)) -> APIResponse[dict]:
    """
    Readiness check endpoint.
    
    Returns whether the application is ready to serve requests.
    """
    health_checker = HealthChecker(db)
    readiness_status = await health_checker.check_readiness()
    
    return APIResponse(
        success=readiness_status["ready"],
        message="Application readiness check",
        data=readiness_status
    )


@router.get("/live", response_model=APIResponse[dict])
async def liveness_check() -> APIResponse[dict]:
    """
    Liveness check endpoint.
    
    Returns whether the application is alive and running.
    """
    return APIResponse(
        success=True,
        message="Application is alive",
        data={
            "status": "alive",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )