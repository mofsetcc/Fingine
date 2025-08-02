"""
Subscription management API endpoints.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.api_response import APIResponse
from app.schemas.subscription import (
    Plan, PlanCreate, PlanUpdate, PlanComparison,
    Subscription, SubscriptionCreate, SubscriptionUpdate,
    SubscriptionUpgrade, SubscriptionDowngrade, SubscriptionCancel,
    SubscriptionWithUsage, UsageQuota, QuotaUsageSummary, QuotaCheckResult
)
from app.services.subscription_service import SubscriptionService
from app.services.quota_service import QuotaService

logger = logging.getLogger(__name__)

router = APIRouter()


# Plan Management Endpoints (Admin only)
@router.post("/plans", response_model=APIResponse[Plan])
async def create_plan(
    plan_data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[Plan]:
    """
    Create a new subscription plan.
    
    Admin only endpoint for creating new subscription plans.
    """
    # TODO: Add admin role check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        service = SubscriptionService(db)
        plan = await service.create_plan(plan_data)
        
        return APIResponse(
            success=True,
            message="Plan created successfully",
            data=plan
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create plan"
        )


@router.get("/plans", response_model=APIResponse[List[Plan]])
async def get_plans(
    active_only: bool = True,
    db: Session = Depends(get_db)
) -> APIResponse[List[Plan]]:
    """
    Get all available subscription plans.
    
    Returns list of subscription plans with features and pricing.
    """
    try:
        service = SubscriptionService(db)
        plans = await service.get_all_plans(active_only=active_only)
        
        return APIResponse(
            success=True,
            message="Plans retrieved successfully",
            data=plans
        )
        
    except Exception as e:
        logger.error(f"Failed to get plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plans"
        )


@router.get("/plans/compare", response_model=APIResponse[PlanComparison])
async def compare_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[PlanComparison]:
    """
    Get plan comparison data for the frontend.
    
    Returns all plans with user's current plan highlighted.
    """
    try:
        service = SubscriptionService(db)
        plans = await service.get_all_plans(active_only=True)
        
        # Get user's current plan
        subscription = await service.get_user_subscription(current_user.id)
        current_plan_id = subscription.plan_id if subscription else None
        
        # Simple recommendation logic (upgrade to next tier)
        recommended_plan_id = None
        if current_plan_id:
            current_plan = await service.get_plan(current_plan_id)
            if current_plan:
                # Find next higher tier plan
                higher_plans = [p for p in plans if p.price_monthly > current_plan.price_monthly]
                if higher_plans:
                    recommended_plan_id = min(higher_plans, key=lambda p: p.price_monthly).id
        else:
            # Recommend pro plan for new users
            pro_plan = next((p for p in plans if p.plan_name == "pro"), None)
            recommended_plan_id = pro_plan.id if pro_plan else None
        
        comparison = PlanComparison(
            plans=plans,
            current_plan_id=current_plan_id,
            recommended_plan_id=recommended_plan_id
        )
        
        return APIResponse(
            success=True,
            message="Plan comparison retrieved successfully",
            data=comparison
        )
        
    except Exception as e:
        logger.error(f"Failed to get plan comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan comparison"
        )


@router.put("/plans/{plan_id}", response_model=APIResponse[Plan])
async def update_plan(
    plan_id: int,
    plan_data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[Plan]:
    """
    Update a subscription plan.
    
    Admin only endpoint for updating subscription plans.
    """
    # TODO: Add admin role check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        service = SubscriptionService(db)
        plan = await service.update_plan(plan_id, plan_data)
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        return APIResponse(
            success=True,
            message="Plan updated successfully",
            data=plan
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update plan"
        )


# User Subscription Endpoints
@router.get("/my-subscription", response_model=APIResponse[SubscriptionWithUsage])
async def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[SubscriptionWithUsage]:
    """
    Get current user's subscription information.
    
    Returns subscription details with usage and quota information.
    """
    try:
        service = SubscriptionService(db)
        subscription = await service.get_subscription_with_usage(current_user.id)
        
        if not subscription:
            # Return default free tier information
            usage_quota = await service.get_user_usage_quota(current_user.id)
            free_plan = await service.get_plan_by_name("free")
            
            if not free_plan:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Default free plan not found"
                )
            
            # Create a mock subscription for free tier users
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            subscription_data = {
                "id": None,
                "user_id": current_user.id,
                "plan_id": free_plan.id,
                "status": "active",
                "current_period_start": now,
                "current_period_end": now + timedelta(days=30),
                "created_at": now,
                "updated_at": now,
                "plan": free_plan,
                "usage_quota": usage_quota
            }
            
            subscription = SubscriptionWithUsage(**subscription_data)
        
        return APIResponse(
            success=True,
            message="Subscription information retrieved successfully",
            data=subscription
        )
        
    except Exception as e:
        logger.error(f"Failed to get subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription information"
        )


@router.get("/usage", response_model=APIResponse[UsageQuota])
async def get_usage_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[UsageQuota]:
    """
    Get current user's usage and quota information.
    
    Returns current usage against daily quotas.
    """
    try:
        service = SubscriptionService(db)
        usage_quota = await service.get_user_usage_quota(current_user.id)
        
        return APIResponse(
            success=True,
            message="Usage quota retrieved successfully",
            data=usage_quota
        )
        
    except Exception as e:
        logger.error(f"Failed to get usage quota for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage quota"
        )


@router.post("/upgrade", response_model=APIResponse[Subscription])
async def upgrade_subscription(
    upgrade_data: SubscriptionUpgrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[Subscription]:
    """
    Upgrade user's subscription to a higher plan.
    
    Immediately upgrades the subscription and extends the billing period.
    """
    try:
        service = SubscriptionService(db)
        subscription = await service.upgrade_subscription(current_user.id, upgrade_data)
        
        return APIResponse(
            success=True,
            message="Subscription upgraded successfully",
            data=subscription
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to upgrade subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade subscription"
        )


@router.post("/downgrade", response_model=APIResponse[Subscription])
async def downgrade_subscription(
    downgrade_data: SubscriptionDowngrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[Subscription]:
    """
    Downgrade user's subscription to a lower plan.
    
    Schedules downgrade for end of current billing period or specified date.
    """
    try:
        service = SubscriptionService(db)
        subscription = await service.downgrade_subscription(current_user.id, downgrade_data)
        
        return APIResponse(
            success=True,
            message="Subscription downgrade scheduled successfully",
            data=subscription
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to downgrade subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to downgrade subscription"
        )


@router.post("/cancel", response_model=APIResponse[Subscription])
async def cancel_subscription(
    cancel_data: SubscriptionCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[Subscription]:
    """
    Cancel user's subscription.
    
    Can cancel immediately or at the end of current billing period.
    """
    try:
        service = SubscriptionService(db)
        subscription = await service.cancel_subscription(current_user.id, cancel_data)
        
        return APIResponse(
            success=True,
            message="Subscription cancelled successfully",
            data=subscription
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to cancel subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


# Utility Endpoints
@router.post("/initialize-plans", response_model=APIResponse[List[Plan]])
async def initialize_default_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[List[Plan]]:
    """
    Initialize default subscription plans.
    
    Admin only endpoint for setting up default plans.
    """
    # TODO: Add admin role check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        service = SubscriptionService(db)
        plans = await service.initialize_default_plans()
        
        return APIResponse(
            success=True,
            message="Default plans initialized successfully",
            data=plans
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize default plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default plans"
        )


# Quota Management Endpoints
@router.get("/quota/check/{quota_type}", response_model=APIResponse[QuotaCheckResult])
async def check_quota_availability(
    quota_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[dict]:
    """
    Check if user has quota available for the specified type.
    
    Args:
        quota_type: Type of quota to check ('api' or 'ai_analysis')
    """
    if quota_type not in ["api", "ai_analysis"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quota type. Must be 'api' or 'ai_analysis'"
        )
    
    try:
        quota_service = QuotaService(db)
        has_quota, quota_info = await quota_service.check_quota_available(
            current_user.id, quota_type
        )
        
        return APIResponse(
            success=True,
            message=f"Quota availability checked for {quota_type}",
            data=QuotaCheckResult(
                has_quota=has_quota,
                quota_info=quota_info
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to check quota for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check quota availability"
        )


@router.get("/quota/summary", response_model=APIResponse[QuotaUsageSummary])
async def get_quota_usage_summary(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[dict]:
    """
    Get quota usage summary for the past N days.
    
    Args:
        days: Number of days to include in summary (default: 7, max: 30)
    """
    if days < 1 or days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter must be between 1 and 30"
        )
    
    try:
        quota_service = QuotaService(db)
        summary = await quota_service.get_quota_usage_summary(current_user.id, days)
        
        return APIResponse(
            success=True,
            message=f"Quota usage summary retrieved for {days} days",
            data=QuotaUsageSummary(**summary)
        )
        
    except Exception as e:
        logger.error(f"Failed to get quota summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota usage summary"
        )


@router.post("/quota/record-usage", response_model=APIResponse[dict])
async def record_api_usage(
    api_provider: str,
    endpoint: str = None,
    request_type: str = None,
    cost_usd: float = None,
    response_time_ms: int = None,
    status_code: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse[dict]:
    """
    Manually record API usage (for testing or external integrations).
    
    This endpoint allows manual recording of API usage events.
    """
    try:
        quota_service = QuotaService(db)
        usage_log = await quota_service.record_api_usage(
            user_id=current_user.id,
            api_provider=api_provider,
            endpoint=endpoint,
            request_type=request_type,
            cost_usd=cost_usd,
            response_time_ms=response_time_ms,
            status_code=status_code
        )
        
        return APIResponse(
            success=True,
            message="API usage recorded successfully",
            data={
                "usage_log_id": usage_log.id,
                "recorded_at": usage_log.request_timestamp
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to record API usage for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record API usage"
        )