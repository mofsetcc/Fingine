"""
Quota tracking and enforcement service.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text

from app.models.logs import APIUsageLog
from app.models.analysis import AIAnalysisCache
from app.models.subscription import Subscription, Plan
from app.schemas.subscription import UsageQuota
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class QuotaService:
    """Service for tracking and enforcing user quotas."""
    
    def __init__(self, db: Session):
        self.db = db
        self.subscription_service = SubscriptionService(db)
    
    async def get_user_quotas(self, user_id: UUID) -> Dict[str, int]:
        """Get user's daily quotas based on their subscription plan."""
        subscription = await self.subscription_service.get_user_subscription(user_id)
        
        if not subscription or subscription.status != "active":
            # Default to free tier quotas
            return {
                "api_quota_daily": 10,
                "ai_analysis_quota_daily": 5
            }
        
        plan = await self.subscription_service.get_plan(subscription.plan_id)
        return {
            "api_quota_daily": plan.api_quota_daily,
            "ai_analysis_quota_daily": plan.ai_analysis_quota_daily
        }
    
    async def get_user_usage_today(self, user_id: UUID) -> Dict[str, int]:
        """Get user's usage for today."""
        # Get today's date range in UTC
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Query API usage logs for today
        api_usage_count = self.db.query(func.count(APIUsageLog.id)).filter(
            and_(
                APIUsageLog.user_id == user_id,
                func.to_timestamp(APIUsageLog.request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') >= today_start,
                func.to_timestamp(APIUsageLog.request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') < today_end
            )
        ).scalar() or 0
        
        # Query AI analysis cache for today
        ai_analysis_count = self.db.query(func.count(AIAnalysisCache.ticker)).filter(
            and_(
                AIAnalysisCache.created_at >= today_start,
                AIAnalysisCache.created_at < today_end,
                # Join with API usage logs to get user_id
                APIUsageLog.user_id == user_id,
                APIUsageLog.request_type == "ai_analysis"
            )
        ).join(
            APIUsageLog,
            and_(
                func.date(func.to_timestamp(APIUsageLog.request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')) == func.date(AIAnalysisCache.created_at),
                APIUsageLog.request_type == "ai_analysis"
            )
        ).scalar() or 0
        
        return {
            "api_usage_today": api_usage_count,
            "ai_analysis_usage_today": ai_analysis_count
        }
    
    async def get_usage_quota(self, user_id: UUID) -> UsageQuota:
        """Get comprehensive usage and quota information for a user."""
        quotas = await self.get_user_quotas(user_id)
        usage = await self.get_user_usage_today(user_id)
        
        # Calculate when quota resets (next day at midnight UTC)
        now = datetime.now(timezone.utc)
        quota_reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        return UsageQuota(
            api_quota_daily=quotas["api_quota_daily"],
            api_usage_today=usage["api_usage_today"],
            ai_analysis_quota_daily=quotas["ai_analysis_quota_daily"],
            ai_analysis_usage_today=usage["ai_analysis_usage_today"],
            quota_reset_at=quota_reset_at
        )
    
    async def check_quota_available(self, user_id: UUID, quota_type: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if user has quota available for the specified type.
        
        Args:
            user_id: User ID to check quota for
            quota_type: Type of quota to check ('api' or 'ai_analysis')
            
        Returns:
            Tuple of (has_quota_available, quota_info_dict)
        """
        usage_quota = await self.get_usage_quota(user_id)
        
        if quota_type == "api":
            has_quota = usage_quota.api_usage_today < usage_quota.api_quota_daily
            quota_info = {
                "quota_type": "api",
                "usage": usage_quota.api_usage_today,
                "limit": usage_quota.api_quota_daily,
                "remaining": usage_quota.api_quota_daily - usage_quota.api_usage_today,
                "reset_at": usage_quota.quota_reset_at.isoformat()
            }
        elif quota_type == "ai_analysis":
            has_quota = usage_quota.ai_analysis_usage_today < usage_quota.ai_analysis_quota_daily
            quota_info = {
                "quota_type": "ai_analysis",
                "usage": usage_quota.ai_analysis_usage_today,
                "limit": usage_quota.ai_analysis_quota_daily,
                "remaining": usage_quota.ai_analysis_quota_daily - usage_quota.ai_analysis_usage_today,
                "reset_at": usage_quota.quota_reset_at.isoformat()
            }
        else:
            return False, {"error": f"Unknown quota type: {quota_type}"}
        
        return has_quota, quota_info
    
    async def record_api_usage(
        self,
        user_id: Optional[UUID],
        api_provider: str,
        endpoint: Optional[str] = None,
        request_type: Optional[str] = None,
        cost_usd: Optional[float] = None,
        response_time_ms: Optional[int] = None,
        status_code: Optional[int] = None
    ) -> APIUsageLog:
        """Record an API usage event."""
        try:
            usage_log = APIUsageLog(
                user_id=user_id,
                api_provider=api_provider,
                endpoint=endpoint,
                request_type=request_type,
                cost_usd=cost_usd,
                response_time_ms=response_time_ms,
                status_code=status_code,
                request_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.db.add(usage_log)
            self.db.commit()
            self.db.refresh(usage_log)
            
            logger.debug(f"Recorded API usage for user {user_id}: {api_provider}/{endpoint}")
            return usage_log
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record API usage: {e}")
            raise
    
    async def get_quota_usage_summary(self, user_id: UUID, days: int = 7) -> Dict[str, any]:
        """Get quota usage summary for the past N days."""
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days)
        
        # Query daily usage for the period
        daily_usage = self.db.execute(
            text("""
                SELECT 
                    DATE(to_timestamp(request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')) as usage_date,
                    COUNT(*) as api_calls,
                    COUNT(CASE WHEN request_type = 'ai_analysis' THEN 1 END) as ai_analysis_calls,
                    AVG(response_time_ms) as avg_response_time,
                    SUM(cost_usd) as total_cost
                FROM api_usage_logs 
                WHERE user_id = :user_id 
                    AND to_timestamp(request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') >= :start_date
                    AND to_timestamp(request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') < :end_date
                GROUP BY DATE(to_timestamp(request_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))
                ORDER BY usage_date DESC
            """),
            {
                "user_id": str(user_id),
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()
        
        # Get current quotas
        quotas = await self.get_user_quotas(user_id)
        
        # Format response
        usage_by_date = []
        for row in daily_usage:
            usage_by_date.append({
                "date": row.usage_date.isoformat() if row.usage_date else None,
                "api_calls": row.api_calls or 0,
                "ai_analysis_calls": row.ai_analysis_calls or 0,
                "avg_response_time_ms": float(row.avg_response_time) if row.avg_response_time else 0,
                "total_cost_usd": float(row.total_cost) if row.total_cost else 0
            })
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "current_quotas": quotas,
            "usage_by_date": usage_by_date,
            "total_api_calls": sum(day["api_calls"] for day in usage_by_date),
            "total_ai_analysis_calls": sum(day["ai_analysis_calls"] for day in usage_by_date),
            "total_cost_usd": sum(day["total_cost_usd"] for day in usage_by_date)
        }
    
    async def get_quota_exceeded_users(self, quota_type: str = "api") -> list:
        """Get list of users who have exceeded their quotas today."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # This would be a complex query joining users, subscriptions, plans, and usage logs
        # For now, return empty list as this would be used for admin monitoring
        return []


def get_quota_service(db: Session) -> QuotaService:
    """Dependency to get quota service."""
    return QuotaService(db)