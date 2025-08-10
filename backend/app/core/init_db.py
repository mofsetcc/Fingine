"""
Database initialization script.
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.subscription import Plan


async def init_db():
    """Initialize database with default data."""
    async with AsyncSessionLocal() as session:
        await create_default_plans(session)
        await session.commit()
        print("✅ Database initialized with default data")


async def create_default_plans(session: AsyncSession):
    """Create default subscription plans."""

    # Check if plans already exist
    result = await session.execute("SELECT COUNT(*) FROM plans")
    count = result.scalar()

    if count > 0:
        print("📋 Subscription plans already exist, skipping...")
        return

    # Create default plans
    plans = [
        Plan(
            plan_name="Free",
            price_monthly=0,
            features={
                "ai_analysis": True,
                "real_time_data": False,
                "advanced_charts": False,
                "api_access": False,
                "priority_support": False,
            },
            api_quota_daily=10,
            ai_analysis_quota_daily=5,
            is_active=True,
        ),
        Plan(
            plan_name="Pro",
            price_monthly=2980,  # 2,980 JPY
            features={
                "ai_analysis": True,
                "real_time_data": True,
                "advanced_charts": True,
                "api_access": True,
                "priority_support": False,
                "watchlist_alerts": True,
                "export_data": True,
            },
            api_quota_daily=100,
            ai_analysis_quota_daily=50,
            is_active=True,
        ),
        Plan(
            plan_name="Business",
            price_monthly=9800,  # 9,800 JPY
            features={
                "ai_analysis": True,
                "real_time_data": True,
                "advanced_charts": True,
                "api_access": True,
                "priority_support": True,
                "watchlist_alerts": True,
                "export_data": True,
                "bulk_analysis": True,
                "custom_reports": True,
                "white_label": True,
            },
            api_quota_daily=1000,
            ai_analysis_quota_daily=500,
            is_active=True,
        ),
    ]

    for plan in plans:
        session.add(plan)
        print(f"📦 Created plan: {plan.plan_name} (¥{plan.price_monthly}/month)")


if __name__ == "__main__":
    asyncio.run(init_db())
