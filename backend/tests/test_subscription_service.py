"""
Tests for subscription service.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.schemas.subscription import (
    PlanCreate, PlanUpdate, SubscriptionCreate, SubscriptionUpdate,
    SubscriptionUpgrade, SubscriptionDowngrade, SubscriptionCancel
)
from app.services.subscription_service import SubscriptionService


class TestSubscriptionService:
    """Test subscription service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def subscription_service(self, mock_db):
        """Create subscription service with mocked database."""
        return SubscriptionService(mock_db)
    
    @pytest.fixture
    def sample_plan_data(self):
        """Sample plan creation data."""
        return PlanCreate(
            plan_name="test_plan",
            price_monthly=1000,
            features={"feature1": True, "feature2": False},
            api_quota_daily=50,
            ai_analysis_quota_daily=25,
            is_active=True
        )
    
    @pytest.fixture
    def sample_plan(self):
        """Sample plan model."""
        return Plan(
            id=1,
            plan_name="test_plan",
            price_monthly=1000,
            features={"feature1": True, "feature2": False},
            api_quota_daily=50,
            ai_analysis_quota_daily=25,
            is_active=True
        )
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_subscription(self, sample_user_id, sample_plan):
        """Sample subscription model."""
        now = datetime.utcnow()
        return Subscription(
            id=uuid4(),
            user_id=sample_user_id,
            plan_id=sample_plan.id,
            status="active",
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=30)).isoformat(),
            plan=sample_plan
        )


class TestPlanManagement:
    """Test plan management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_plan_success(self, subscription_service, mock_db, sample_plan_data):
        """Test successful plan creation."""
        # Arrange
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Act
        result = await subscription_service.create_plan(sample_plan_data)
        
        # Assert
        assert result.plan_name == sample_plan_data.plan_name
        assert result.price_monthly == sample_plan_data.price_monthly
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_plan_database_error(self, subscription_service, mock_db, sample_plan_data):
        """Test plan creation with database error."""
        # Arrange
        mock_db.add = Mock()
        mock_db.commit = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = Mock()
        
        # Act & Assert
        with pytest.raises(Exception):
            await subscription_service.create_plan(sample_plan_data)
        
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_plan_success(self, subscription_service, mock_db, sample_plan):
        """Test successful plan retrieval."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_plan
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.get_plan(sample_plan.id)
        
        # Assert
        assert result == sample_plan
        mock_db.query.assert_called_once_with(Plan)
    
    @pytest.mark.asyncio
    async def test_get_plan_not_found(self, subscription_service, mock_db):
        """Test plan retrieval when plan doesn't exist."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.get_plan(999)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_plans_active_only(self, subscription_service, mock_db, sample_plan):
        """Test getting all active plans."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [sample_plan]
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.get_all_plans(active_only=True)
        
        # Assert
        assert result == [sample_plan]
        mock_query.filter.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_plan_success(self, subscription_service, mock_db, sample_plan):
        """Test successful plan update."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_plan
        mock_db.query.return_value = mock_query
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        update_data = PlanUpdate(price_monthly=2000)
        
        # Act
        result = await subscription_service.update_plan(sample_plan.id, update_data)
        
        # Assert
        assert result.price_monthly == 2000
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_plan_not_found(self, subscription_service, mock_db):
        """Test plan update when plan doesn't exist."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        update_data = PlanUpdate(price_monthly=2000)
        
        # Act
        result = await subscription_service.update_plan(999, update_data)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_plan_success(self, subscription_service, mock_db, sample_plan):
        """Test successful plan deletion (deactivation)."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_plan
        mock_query.filter.return_value.count.return_value = 0  # No active subscriptions
        mock_db.query.return_value = mock_query
        mock_db.commit = Mock()
        
        # Act
        result = await subscription_service.delete_plan(sample_plan.id)
        
        # Assert
        assert result is True
        assert sample_plan.is_active is False
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_plan_with_active_subscriptions(self, subscription_service, mock_db, sample_plan):
        """Test plan deletion with active subscriptions."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_plan
        mock_query.filter.return_value.count.return_value = 5  # 5 active subscriptions
        mock_db.query.return_value = mock_query
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete plan with 5 active subscriptions"):
            await subscription_service.delete_plan(sample_plan.id)


class TestSubscriptionManagement:
    """Test subscription management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_subscription_success(self, subscription_service, mock_db, sample_user_id, sample_plan):
        """Test successful subscription creation."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [None, sample_plan]  # No existing subscription, plan exists
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        now = datetime.utcnow()
        subscription_data = SubscriptionCreate(
            user_id=sample_user_id,
            plan_id=sample_plan.id,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30)
        )
        
        # Act
        result = await subscription_service.create_subscription(subscription_data)
        
        # Assert
        assert result.user_id == sample_user_id
        assert result.plan_id == sample_plan.id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_subscription_user_already_has_subscription(self, subscription_service, mock_db, sample_user_id, sample_subscription):
        """Test subscription creation when user already has one."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_subscription
        mock_db.query.return_value = mock_query
        
        now = datetime.utcnow()
        subscription_data = SubscriptionCreate(
            user_id=sample_user_id,
            plan_id=1,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30)
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="User already has a subscription"):
            await subscription_service.create_subscription(subscription_data)
    
    @pytest.mark.asyncio
    async def test_create_subscription_invalid_plan(self, subscription_service, mock_db, sample_user_id):
        """Test subscription creation with invalid plan."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [None, None]  # No existing subscription, no plan
        mock_db.query.return_value = mock_query
        
        now = datetime.utcnow()
        subscription_data = SubscriptionCreate(
            user_id=sample_user_id,
            plan_id=999,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30)
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid or inactive plan"):
            await subscription_service.create_subscription(subscription_data)
    
    @pytest.mark.asyncio
    async def test_get_user_subscription_success(self, subscription_service, mock_db, sample_user_id, sample_subscription):
        """Test successful user subscription retrieval."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_subscription
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.get_user_subscription(sample_user_id)
        
        # Assert
        assert result == sample_subscription
    
    @pytest.mark.asyncio
    async def test_upgrade_subscription_success(self, subscription_service, mock_db, sample_user_id, sample_subscription):
        """Test successful subscription upgrade."""
        # Arrange
        current_plan = Plan(id=1, plan_name="basic", price_monthly=1000, is_active=True)
        new_plan = Plan(id=2, plan_name="pro", price_monthly=2000, is_active=True)
        
        sample_subscription.plan_id = current_plan.id
        
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [sample_subscription, new_plan, current_plan]
        mock_db.query.return_value = mock_query
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        upgrade_data = SubscriptionUpgrade(new_plan_id=new_plan.id)
        
        # Act
        result = await subscription_service.upgrade_subscription(sample_user_id, upgrade_data)
        
        # Assert
        assert result.plan_id == new_plan.id
        assert result.status == "active"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upgrade_subscription_no_existing_subscription(self, subscription_service, mock_db, sample_user_id):
        """Test subscription upgrade when user has no subscription."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        upgrade_data = SubscriptionUpgrade(new_plan_id=2)
        
        # Act & Assert
        with pytest.raises(ValueError, match="User has no active subscription"):
            await subscription_service.upgrade_subscription(sample_user_id, upgrade_data)
    
    @pytest.mark.asyncio
    async def test_upgrade_subscription_not_higher_tier(self, subscription_service, mock_db, sample_user_id, sample_subscription):
        """Test subscription upgrade to same or lower tier."""
        # Arrange
        current_plan = Plan(id=1, plan_name="pro", price_monthly=2000, is_active=True)
        new_plan = Plan(id=2, plan_name="basic", price_monthly=1000, is_active=True)
        
        sample_subscription.plan_id = current_plan.id
        
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [sample_subscription, new_plan, current_plan]
        mock_db.query.return_value = mock_query
        
        upgrade_data = SubscriptionUpgrade(new_plan_id=new_plan.id)
        
        # Act & Assert
        with pytest.raises(ValueError, match="New plan must be higher tier than current plan"):
            await subscription_service.upgrade_subscription(sample_user_id, upgrade_data)
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, subscription_service, mock_db, sample_user_id, sample_subscription):
        """Test successful subscription cancellation."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_subscription
        mock_db.query.return_value = mock_query
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        cancel_data = SubscriptionCancel(
            reason="No longer needed",
            cancel_at_period_end=True
        )
        
        # Act
        result = await subscription_service.cancel_subscription(sample_user_id, cancel_data)
        
        # Assert
        assert result.status == "cancelled"
        mock_db.commit.assert_called_once()


class TestUsageQuotaManagement:
    """Test usage and quota management functionality."""
    
    @pytest.mark.asyncio
    async def test_get_user_usage_quota_with_subscription(self, subscription_service, mock_db, sample_user_id, sample_subscription):
        """Test getting usage quota for user with active subscription."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [sample_subscription, sample_subscription.plan]
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.get_user_usage_quota(sample_user_id)
        
        # Assert
        assert result.api_quota_daily == sample_subscription.plan.api_quota_daily
        assert result.ai_analysis_quota_daily == sample_subscription.plan.ai_analysis_quota_daily
        assert result.api_usage_today == 0  # Mock data
        assert result.ai_analysis_usage_today == 0  # Mock data
    
    @pytest.mark.asyncio
    async def test_get_user_usage_quota_without_subscription(self, subscription_service, mock_db, sample_user_id):
        """Test getting usage quota for user without subscription (free tier)."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.get_user_usage_quota(sample_user_id)
        
        # Assert
        assert result.api_quota_daily == 10  # Free tier default
        assert result.ai_analysis_quota_daily == 5  # Free tier default
    
    @pytest.mark.asyncio
    async def test_check_quota_available_api_quota_available(self, subscription_service, mock_db, sample_user_id):
        """Test quota check when API quota is available."""
        # Arrange
        with patch.object(subscription_service, 'get_user_usage_quota') as mock_get_quota:
            from app.schemas.subscription import UsageQuota
            mock_get_quota.return_value = UsageQuota(
                api_quota_daily=100,
                api_usage_today=50,
                ai_analysis_quota_daily=50,
                ai_analysis_usage_today=25,
                quota_reset_at=datetime.utcnow() + timedelta(hours=12)
            )
            
            # Act
            result = await subscription_service.check_quota_available(sample_user_id, "api")
            
            # Assert
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_quota_available_api_quota_exceeded(self, subscription_service, mock_db, sample_user_id):
        """Test quota check when API quota is exceeded."""
        # Arrange
        with patch.object(subscription_service, 'get_user_usage_quota') as mock_get_quota:
            from app.schemas.subscription import UsageQuota
            mock_get_quota.return_value = UsageQuota(
                api_quota_daily=100,
                api_usage_today=100,  # Quota exceeded
                ai_analysis_quota_daily=50,
                ai_analysis_usage_today=25,
                quota_reset_at=datetime.utcnow() + timedelta(hours=12)
            )
            
            # Act
            result = await subscription_service.check_quota_available(sample_user_id, "api")
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_quota_available_invalid_quota_type(self, subscription_service, mock_db, sample_user_id):
        """Test quota check with invalid quota type."""
        # Act
        result = await subscription_service.check_quota_available(sample_user_id, "invalid_type")
        
        # Assert
        assert result is False


class TestDefaultPlansInitialization:
    """Test default plans initialization functionality."""
    
    @pytest.mark.asyncio
    async def test_initialize_default_plans_success(self, subscription_service, mock_db):
        """Test successful default plans initialization."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []  # No existing plans
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Act
        result = await subscription_service.initialize_default_plans()
        
        # Assert
        assert len(result) == 3  # free, pro, business
        assert mock_db.add.call_count == 3
        assert mock_db.commit.call_count == 3
    
    @pytest.mark.asyncio
    async def test_initialize_default_plans_already_exist(self, subscription_service, mock_db, sample_plan):
        """Test default plans initialization when plans already exist."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [sample_plan]
        mock_db.query.return_value = mock_query
        
        # Act
        result = await subscription_service.initialize_default_plans()
        
        # Assert
        assert result == [sample_plan]
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()