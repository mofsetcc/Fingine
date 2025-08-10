"""
Subscription management service.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.schemas.subscription import (
    PlanCreate,
    PlanUpdate,
    SubscriptionCancel,
    SubscriptionCreate,
    SubscriptionDowngrade,
    SubscriptionUpdate,
    SubscriptionUpgrade,
    SubscriptionWithUsage,
    UsageQuota,
)

# from app.core.database import get_db  # Import only when needed

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions and plans."""

    def __init__(self, db: Session):
        self.db = db

    # Plan Management
    async def create_plan(self, plan_data: PlanCreate) -> Plan:
        """Create a new subscription plan."""
        try:
            plan = Plan(**plan_data.dict())
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)

            logger.info(f"Created new plan: {plan.plan_name} (ID: {plan.id})")
            return plan

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create plan: {e}")
            raise

    async def get_plan(self, plan_id: int) -> Optional[Plan]:
        """Get a plan by ID."""
        return self.db.query(Plan).filter(Plan.id == plan_id).first()

    async def get_plan_by_name(self, plan_name: str) -> Optional[Plan]:
        """Get a plan by name."""
        return self.db.query(Plan).filter(Plan.plan_name == plan_name).first()

    async def get_all_plans(self, active_only: bool = True) -> List[Plan]:
        """Get all subscription plans."""
        query = self.db.query(Plan)
        if active_only:
            query = query.filter(Plan.is_active == True)
        return query.order_by(Plan.price_monthly).all()

    async def update_plan(self, plan_id: int, plan_data: PlanUpdate) -> Optional[Plan]:
        """Update a subscription plan."""
        try:
            plan = await self.get_plan(plan_id)
            if not plan:
                return None

            update_data = plan_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(plan, field, value)

            self.db.commit()
            self.db.refresh(plan)

            logger.info(f"Updated plan: {plan.plan_name} (ID: {plan.id})")
            return plan

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update plan {plan_id}: {e}")
            raise

    async def delete_plan(self, plan_id: int) -> bool:
        """Soft delete a plan by marking it inactive."""
        try:
            plan = await self.get_plan(plan_id)
            if not plan:
                return False

            # Check if plan has active subscriptions
            active_subscriptions = (
                self.db.query(Subscription)
                .filter(
                    and_(
                        Subscription.plan_id == plan_id, Subscription.status == "active"
                    )
                )
                .count()
            )

            if active_subscriptions > 0:
                raise ValueError(
                    f"Cannot delete plan with {active_subscriptions} active subscriptions"
                )

            plan.is_active = False
            self.db.commit()

            logger.info(f"Deactivated plan: {plan.plan_name} (ID: {plan.id})")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            raise

    # Subscription Management
    async def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription for a user."""
        try:
            # Check if user already has a subscription
            existing = await self.get_user_subscription(subscription_data.user_id)
            if existing:
                raise ValueError("User already has a subscription")

            # Verify plan exists
            plan = await self.get_plan(subscription_data.plan_id)
            if not plan or not plan.is_active:
                raise ValueError("Invalid or inactive plan")

            subscription = Subscription(
                user_id=subscription_data.user_id,
                plan_id=subscription_data.plan_id,
                status=subscription_data.status,
                current_period_start=subscription_data.current_period_start.isoformat(),
                current_period_end=subscription_data.current_period_end.isoformat(),
            )

            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Created subscription for user {subscription_data.user_id} with plan {subscription_data.plan_id}"
            )
            return subscription

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create subscription: {e}")
            raise

    async def get_user_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """Get user's current subscription."""
        return (
            self.db.query(Subscription).filter(Subscription.user_id == user_id).first()
        )

    async def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID."""
        return (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )

    async def update_subscription(
        self, subscription_id: UUID, subscription_data: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update a subscription."""
        try:
            subscription = await self.get_subscription(subscription_id)
            if not subscription:
                return None

            update_data = subscription_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field in ["current_period_start", "current_period_end"] and value:
                    setattr(subscription, field, value.isoformat())
                else:
                    setattr(subscription, field, value)

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(f"Updated subscription {subscription_id}")
            return subscription

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update subscription {subscription_id}: {e}")
            raise

    async def upgrade_subscription(
        self, user_id: UUID, upgrade_data: SubscriptionUpgrade
    ) -> Subscription:
        """Upgrade user's subscription to a higher plan."""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                raise ValueError("User has no active subscription")

            new_plan = await self.get_plan(upgrade_data.new_plan_id)
            if not new_plan or not new_plan.is_active:
                raise ValueError("Invalid or inactive plan")

            current_plan = await self.get_plan(subscription.plan_id)
            if new_plan.price_monthly <= current_plan.price_monthly:
                raise ValueError("New plan must be higher tier than current plan")

            # Update subscription immediately
            subscription.plan_id = upgrade_data.new_plan_id
            subscription.status = "active"

            # Extend current period by one month from now
            now = datetime.utcnow()
            subscription.current_period_start = now.isoformat()
            subscription.current_period_end = (now + timedelta(days=30)).isoformat()

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Upgraded subscription for user {user_id} to plan {upgrade_data.new_plan_id}"
            )
            return subscription

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upgrade subscription for user {user_id}: {e}")
            raise

    async def downgrade_subscription(
        self, user_id: UUID, downgrade_data: SubscriptionDowngrade
    ) -> Subscription:
        """Downgrade user's subscription to a lower plan."""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                raise ValueError("User has no active subscription")

            new_plan = await self.get_plan(downgrade_data.new_plan_id)
            if not new_plan or not new_plan.is_active:
                raise ValueError("Invalid or inactive plan")

            current_plan = await self.get_plan(subscription.plan_id)
            if new_plan.price_monthly >= current_plan.price_monthly:
                raise ValueError("New plan must be lower tier than current plan")

            # Schedule downgrade for end of current period or specified date
            effective_date = downgrade_data.effective_date or datetime.fromisoformat(
                subscription.current_period_end
            )

            if effective_date <= datetime.utcnow():
                # Apply immediately
                subscription.plan_id = downgrade_data.new_plan_id
            else:
                # Store pending downgrade (would need additional table in production)
                logger.info(
                    f"Scheduled downgrade for user {user_id} effective {effective_date}"
                )

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Downgraded subscription for user {user_id} to plan {downgrade_data.new_plan_id}"
            )
            return subscription

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to downgrade subscription for user {user_id}: {e}")
            raise

    async def cancel_subscription(
        self, user_id: UUID, cancel_data: SubscriptionCancel
    ) -> Subscription:
        """Cancel user's subscription."""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                raise ValueError("User has no active subscription")

            if cancel_data.cancel_at_period_end:
                # Cancel at end of current period
                subscription.status = "cancelled"
            else:
                # Cancel immediately
                subscription.status = "cancelled"
                subscription.current_period_end = datetime.utcnow().isoformat()

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Cancelled subscription for user {user_id}, reason: {cancel_data.reason}"
            )
            return subscription

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cancel subscription for user {user_id}: {e}")
            raise

    # Usage and Quota Management
    async def get_user_usage_quota(self, user_id: UUID) -> UsageQuota:
        """Get user's current usage and quota information."""
        # Import here to avoid circular imports
        from app.services.quota_service import QuotaService

        quota_service = QuotaService(self.db)
        return await quota_service.get_usage_quota(user_id)

    async def check_quota_available(self, user_id: UUID, quota_type: str) -> bool:
        """Check if user has quota available for the specified type."""
        # Import here to avoid circular imports
        from app.services.quota_service import QuotaService

        quota_service = QuotaService(self.db)
        has_quota, _ = await quota_service.check_quota_available(user_id, quota_type)
        return has_quota

    # Utility Methods
    async def get_subscription_with_usage(
        self, user_id: UUID
    ) -> Optional[SubscriptionWithUsage]:
        """Get subscription with usage information."""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return None

        usage_quota = await self.get_user_usage_quota(user_id)

        # Convert to SubscriptionWithUsage
        subscription_dict = {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "current_period_start": datetime.fromisoformat(
                subscription.current_period_start
            ),
            "current_period_end": datetime.fromisoformat(
                subscription.current_period_end
            ),
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
            "plan": subscription.plan,
            "usage_quota": usage_quota,
        }

        return SubscriptionWithUsage(**subscription_dict)

    async def initialize_default_plans(self) -> List[Plan]:
        """Initialize default subscription plans if they don't exist."""
        try:
            existing_plans = await self.get_all_plans(active_only=False)
            if existing_plans:
                logger.info("Default plans already exist, skipping initialization")
                return existing_plans

            default_plans = [
                PlanCreate(
                    plan_name="free",
                    price_monthly=0,
                    features={
                        "real_time_data": False,
                        "advanced_analysis": False,
                        "priority_support": False,
                        "export_data": False,
                        "custom_alerts": False,
                    },
                    api_quota_daily=10,
                    ai_analysis_quota_daily=5,
                    is_active=True,
                ),
                PlanCreate(
                    plan_name="pro",
                    price_monthly=2980,  # 2,980 JPY
                    features={
                        "real_time_data": True,
                        "advanced_analysis": True,
                        "priority_support": False,
                        "export_data": True,
                        "custom_alerts": True,
                    },
                    api_quota_daily=100,
                    ai_analysis_quota_daily=50,
                    is_active=True,
                ),
                PlanCreate(
                    plan_name="business",
                    price_monthly=9800,  # 9,800 JPY
                    features={
                        "real_time_data": True,
                        "advanced_analysis": True,
                        "priority_support": True,
                        "export_data": True,
                        "custom_alerts": True,
                        "api_access": True,
                        "bulk_analysis": True,
                    },
                    api_quota_daily=1000,
                    ai_analysis_quota_daily=200,
                    is_active=True,
                ),
            ]

            created_plans = []
            for plan_data in default_plans:
                plan = await self.create_plan(plan_data)
                created_plans.append(plan)

            logger.info(f"Initialized {len(created_plans)} default plans")
            return created_plans

        except Exception as e:
            logger.error(f"Failed to initialize default plans: {e}")
            raise


def get_subscription_service(db: Session) -> SubscriptionService:
    """Dependency to get subscription service."""
    return SubscriptionService(db)
