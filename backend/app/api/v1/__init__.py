"""API v1 package."""

from fastapi import APIRouter

from app.api.v1 import (
    analysis,
    auth,
    gdpr,
    health,
    oauth,
    profile,
    stocks,
    subscription,
    users,
    watchlist,
)

api_router = APIRouter()

# Include routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["ai-analysis"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(
    subscription.router, prefix="/subscription", tags=["subscription"]
)
api_router.include_router(gdpr.router, prefix="/gdpr", tags=["gdpr"])
