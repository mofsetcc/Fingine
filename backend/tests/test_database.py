"""
Database model tests.
"""

import pytest
from datetime import datetime, date
from uuid import uuid4

from app.models.user import User, UserProfile
from app.models.subscription import Plan, Subscription
from app.models.stock import Stock, StockPriceHistory
from app.models.financial import FinancialReport, FinancialReportLineItem


def test_user_model():
    """Test User model creation."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password"
    )
    
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_password"
    assert user.email_verified_at is None


def test_user_profile_model():
    """Test UserProfile model creation."""
    user_id = uuid4()
    profile = UserProfile(
        user_id=user_id,
        display_name="Test User",
        timezone="Asia/Tokyo",
        notification_preferences={"email": True}
    )
    
    assert profile.user_id == user_id
    assert profile.display_name == "Test User"
    assert profile.timezone == "Asia/Tokyo"
    assert profile.notification_preferences == {"email": True}


def test_plan_model():
    """Test Plan model creation."""
    plan = Plan(
        plan_name="Pro",
        price_monthly=2980,
        features={"real_time_data": True},
        api_quota_daily=100,
        ai_analysis_quota_daily=50
    )
    
    assert plan.plan_name == "Pro"
    assert plan.price_monthly == 2980
    assert plan.features == {"real_time_data": True}
    assert plan.api_quota_daily == 100
    assert plan.ai_analysis_quota_daily == 50
    assert plan.is_active is True


def test_stock_model():
    """Test Stock model creation."""
    stock = Stock(
        ticker="7203",
        company_name_jp="トヨタ自動車",
        company_name_en="Toyota Motor Corporation",
        sector_jp="自動車・輸送機器",
        industry_jp="自動車"
    )
    
    assert stock.ticker == "7203"
    assert stock.company_name_jp == "トヨタ自動車"
    assert stock.company_name_en == "Toyota Motor Corporation"
    assert stock.sector_jp == "自動車・輸送機器"
    assert stock.industry_jp == "自動車"
    assert stock.is_active is True


def test_stock_price_history_model():
    """Test StockPriceHistory model creation."""
    price_data = StockPriceHistory(
        ticker="7203",
        date=date(2025, 1, 23),
        open=2500.0,
        high=2550.0,
        low=2480.0,
        close=2530.0,
        volume=1000000
    )
    
    assert price_data.ticker == "7203"
    assert price_data.date == date(2025, 1, 23)
    assert price_data.open == 2500.0
    assert price_data.high == 2550.0
    assert price_data.low == 2480.0
    assert price_data.close == 2530.0
    assert price_data.volume == 1000000


def test_financial_report_model():
    """Test FinancialReport model creation."""
    report = FinancialReport(
        ticker="7203",
        fiscal_year=2024,
        fiscal_period="Q4",
        report_type="quarterly",
        announced_at="2025-01-23T10:00:00Z"
    )
    
    assert report.ticker == "7203"
    assert report.fiscal_year == 2024
    assert report.fiscal_period == "Q4"
    assert report.report_type == "quarterly"
    assert report.announced_at == "2025-01-23T10:00:00Z"


def test_financial_report_line_item_model():
    """Test FinancialReportLineItem model creation."""
    report_id = uuid4()
    line_item = FinancialReportLineItem(
        report_id=report_id,
        metric_name="revenue",
        metric_value=1000000000.00,
        unit="JPY",
        period_type="quarterly"
    )
    
    assert line_item.report_id == report_id
    assert line_item.metric_name == "revenue"
    assert line_item.metric_value == 1000000000.00
    assert line_item.unit == "JPY"
    assert line_item.period_type == "quarterly"