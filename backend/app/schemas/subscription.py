"""
Subscription and billing Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


# Plan Schemas
class PlanBase(BaseModel):
    """Base plan schema."""
    
    plan_name: str = Field(..., max_length=50, description="Plan name")
    price_monthly: int = Field(..., ge=0, description="Monthly price in Japanese Yen")
    features: Dict[str, Any] = Field(default_factory=dict, description="Plan features")
    api_quota_daily: int = Field(default=10, ge=0, description="Daily API quota")
    ai_analysis_quota_daily: int = Field(default=5, ge=0, description="Daily AI analysis quota")
    is_active: bool = Field(default=True, description="Whether plan is active")


class PlanCreate(PlanBase):
    """Plan creation schema."""
    pass


class PlanUpdate(BaseModel):
    """Plan update schema."""
    
    plan_name: Optional[str] = Field(None, max_length=50, description="Plan name")
    price_monthly: Optional[int] = Field(None, ge=0, description="Monthly price in Japanese Yen")
    features: Optional[Dict[str, Any]] = Field(None, description="Plan features")
    api_quota_daily: Optional[int] = Field(None, ge=0, description="Daily API quota")
    ai_analysis_quota_daily: Optional[int] = Field(None, ge=0, description="Daily AI analysis quota")
    is_active: Optional[bool] = Field(None, description="Whether plan is active")


class Plan(PlanBase, TimestampSchema):
    """Plan response schema."""
    
    id: int = Field(..., description="Plan ID")
    
    class Config:
        from_attributes = True


# Subscription Schemas
class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    
    plan_id: int = Field(..., description="Plan ID")
    status: Literal["active", "inactive", "cancelled", "expired"] = Field(
        default="active", 
        description="Subscription status"
    )
    current_period_start: datetime = Field(..., description="Current period start")
    current_period_end: datetime = Field(..., description="Current period end")


class SubscriptionCreate(SubscriptionBase):
    """Subscription creation schema."""
    
    user_id: UUID = Field(..., description="User ID")


class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    
    plan_id: Optional[int] = Field(None, description="Plan ID")
    status: Optional[Literal["active", "inactive", "cancelled", "expired"]] = Field(
        None, 
        description="Subscription status"
    )
    current_period_start: Optional[datetime] = Field(None, description="Current period start")
    current_period_end: Optional[datetime] = Field(None, description="Current period end")


class Subscription(SubscriptionBase, UUIDSchema, TimestampSchema):
    """Subscription response schema."""
    
    user_id: UUID = Field(..., description="User ID")
    plan: Optional[Plan] = Field(None, description="Associated plan")
    
    class Config:
        from_attributes = True


# Subscription Management Schemas
class SubscriptionUpgrade(BaseModel):
    """Subscription upgrade request schema."""
    
    new_plan_id: int = Field(..., description="New plan ID")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")


class SubscriptionDowngrade(BaseModel):
    """Subscription downgrade request schema."""
    
    new_plan_id: int = Field(..., description="New plan ID")
    effective_date: Optional[datetime] = Field(None, description="When downgrade takes effect")


class SubscriptionCancel(BaseModel):
    """Subscription cancellation request schema."""
    
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")
    cancel_at_period_end: bool = Field(default=True, description="Cancel at period end or immediately")


# Usage and Quota Schemas
class UsageQuota(BaseModel):
    """User usage quota information."""
    
    api_quota_daily: int = Field(..., description="Daily API quota")
    api_usage_today: int = Field(..., description="API usage today")
    ai_analysis_quota_daily: int = Field(..., description="Daily AI analysis quota")
    ai_analysis_usage_today: int = Field(..., description="AI analysis usage today")
    quota_reset_at: datetime = Field(..., description="When quota resets")


class SubscriptionWithUsage(Subscription):
    """Subscription with usage information."""
    
    usage_quota: UsageQuota = Field(..., description="Current usage and quota")


# Billing Schemas
class BillingInfo(BaseModel):
    """Billing information schema."""
    
    customer_id: Optional[str] = Field(None, description="Payment provider customer ID")
    payment_method_id: Optional[str] = Field(None, description="Default payment method ID")
    billing_email: Optional[str] = Field(None, description="Billing email address")
    tax_id: Optional[str] = Field(None, description="Tax ID number")


class Invoice(BaseModel):
    """Invoice schema."""
    
    id: str = Field(..., description="Invoice ID")
    subscription_id: UUID = Field(..., description="Subscription ID")
    amount: int = Field(..., description="Invoice amount in JPY")
    currency: str = Field(default="JPY", description="Currency")
    status: str = Field(..., description="Invoice status")
    created_at: datetime = Field(..., description="Invoice creation date")
    due_date: datetime = Field(..., description="Invoice due date")
    paid_at: Optional[datetime] = Field(None, description="Payment date")


# Plan Comparison Schema
class PlanComparison(BaseModel):
    """Plan comparison schema for frontend."""
    
    plans: list[Plan] = Field(..., description="Available plans")
    current_plan_id: Optional[int] = Field(None, description="User's current plan ID")
    recommended_plan_id: Optional[int] = Field(None, description="Recommended plan ID")


# Subscription Analytics Schema
class SubscriptionAnalytics(BaseModel):
    """Subscription analytics for admin."""
    
    total_subscribers: int = Field(..., description="Total number of subscribers")
    active_subscribers: int = Field(..., description="Active subscribers")
    monthly_revenue: int = Field(..., description="Monthly revenue in JPY")
    churn_rate: float = Field(..., description="Monthly churn rate")
    plan_distribution: Dict[str, int] = Field(..., description="Subscribers per plan")
    
    class Config:
        from_attributes = True