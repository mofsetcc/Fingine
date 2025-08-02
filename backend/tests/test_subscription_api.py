"""
Tests for subscription API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.schemas.subscription import UsageQuota, SubscriptionWithUsage


class TestSubscriptionAPI:
    """Test subscription API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return User(
            id=uuid4(),
            email="test@example.com",
            email_verified=True
        )
    
    @pytest.fixture
    def mock_plan(self):
        """Mock subscription plan."""
        return Plan(
            id=1,
            plan_name="pro",
            price_monthly=2980,
            features={"real_time_data": True, "advanced_analysis": True},
            api_quota_daily=100,
            ai_analysis_quota_daily=50,
            is_active=True
        )
    
    @pytest.fixture
    def mock_subscription(self, mock_user, mock_plan):
        """Mock user subscription."""
        now = datetime.utcnow()
        return Subscription(
            id=uuid4(),
            user_id=mock_user.id,
            plan_id=mock_plan.id,
            status="active",
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=30)).isoformat(),
            plan=mock_plan
        )
    
    @pytest.fixture
    def mock_usage_quota(self):
        """Mock usage quota."""
        return UsageQuota(
            api_quota_daily=100,
            api_usage_today=25,
            ai_analysis_quota_daily=50,
            ai_analysis_usage_today=10,
            quota_reset_at=datetime.utcnow() + timedelta(hours=12)
        )


class TestPlanEndpoints:
    """Test plan management endpoints."""
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_get_plans_success(self, mock_service_class, mock_get_user, client, mock_user, mock_plan):
        """Test successful plans retrieval."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.get_all_plans = AsyncMock(return_value=[mock_plan])
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/subscription/plans")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["plan_name"] == "pro"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_get_plans_error(self, mock_service_class, mock_get_user, client, mock_user):
        """Test plans retrieval with service error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.get_all_plans = AsyncMock(side_effect=Exception("Database error"))
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/subscription/plans")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_compare_plans_success(self, mock_service_class, mock_get_user, client, mock_user, mock_plan, mock_subscription):
        """Test successful plan comparison."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.get_all_plans = AsyncMock(return_value=[mock_plan])
        mock_service.get_user_subscription = AsyncMock(return_value=mock_subscription)
        mock_service.get_plan = AsyncMock(return_value=mock_plan)
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/subscription/plans/compare")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "plans" in data["data"]
        assert "current_plan_id" in data["data"]
        assert "recommended_plan_id" in data["data"]
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_create_plan_success(self, mock_service_class, mock_get_user, client, mock_user, mock_plan):
        """Test successful plan creation."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.create_plan = AsyncMock(return_value=mock_plan)
        mock_service_class.return_value = mock_service
        
        plan_data = {
            "plan_name": "test_plan",
            "price_monthly": 1500,
            "features": {"feature1": True},
            "api_quota_daily": 75,
            "ai_analysis_quota_daily": 30,
            "is_active": True
        }
        
        # Act
        response = client.post("/api/v1/subscription/plans", json=plan_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["plan_name"] == "pro"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_create_plan_validation_error(self, mock_service_class, mock_get_user, client, mock_user):
        """Test plan creation with validation error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.create_plan = AsyncMock(side_effect=ValueError("Plan name already exists"))
        mock_service_class.return_value = mock_service
        
        plan_data = {
            "plan_name": "existing_plan",
            "price_monthly": 1500,
            "features": {},
            "api_quota_daily": 75,
            "ai_analysis_quota_daily": 30
        }
        
        # Act
        response = client.post("/api/v1/subscription/plans", json=plan_data)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_update_plan_success(self, mock_service_class, mock_get_user, client, mock_user, mock_plan):
        """Test successful plan update."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.update_plan = AsyncMock(return_value=mock_plan)
        mock_service_class.return_value = mock_service
        
        update_data = {"price_monthly": 3500}
        
        # Act
        response = client.put("/api/v1/subscription/plans/1", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_update_plan_not_found(self, mock_service_class, mock_get_user, client, mock_user):
        """Test plan update when plan doesn't exist."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.update_plan = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service
        
        update_data = {"price_monthly": 3500}
        
        # Act
        response = client.put("/api/v1/subscription/plans/999", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUserSubscriptionEndpoints:
    """Test user subscription endpoints."""
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_get_my_subscription_with_subscription(self, mock_service_class, mock_get_user, client, mock_user, mock_subscription, mock_usage_quota):
        """Test getting user's subscription when they have one."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        
        subscription_with_usage = SubscriptionWithUsage(
            id=mock_subscription.id,
            user_id=mock_subscription.user_id,
            plan_id=mock_subscription.plan_id,
            status=mock_subscription.status,
            current_period_start=datetime.fromisoformat(mock_subscription.current_period_start),
            current_period_end=datetime.fromisoformat(mock_subscription.current_period_end),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            plan=mock_subscription.plan,
            usage_quota=mock_usage_quota
        )
        
        mock_service.get_subscription_with_usage = AsyncMock(return_value=subscription_with_usage)
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/subscription/my-subscription")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "active"
        assert data["data"]["plan"]["plan_name"] == "pro"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_get_my_subscription_without_subscription(self, mock_service_class, mock_get_user, client, mock_user, mock_usage_quota):
        """Test getting user's subscription when they don't have one (free tier)."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.get_subscription_with_usage = AsyncMock(return_value=None)
        mock_service.get_user_usage_quota = AsyncMock(return_value=mock_usage_quota)
        
        free_plan = Plan(
            id=1,
            plan_name="free",
            price_monthly=0,
            features={},
            api_quota_daily=10,
            ai_analysis_quota_daily=5,
            is_active=True
        )
        mock_service.get_plan_by_name = AsyncMock(return_value=free_plan)
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/subscription/my-subscription")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["plan"]["plan_name"] == "free"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_get_usage_quota_success(self, mock_service_class, mock_get_user, client, mock_user, mock_usage_quota):
        """Test successful usage quota retrieval."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.get_user_usage_quota = AsyncMock(return_value=mock_usage_quota)
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.get("/api/v1/subscription/usage")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["api_quota_daily"] == 100
        assert data["data"]["api_usage_today"] == 25
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_upgrade_subscription_success(self, mock_service_class, mock_get_user, client, mock_user, mock_subscription):
        """Test successful subscription upgrade."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.upgrade_subscription = AsyncMock(return_value=mock_subscription)
        mock_service_class.return_value = mock_service
        
        upgrade_data = {"new_plan_id": 2}
        
        # Act
        response = client.post("/api/v1/subscription/upgrade", json=upgrade_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Subscription upgraded successfully"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_upgrade_subscription_validation_error(self, mock_service_class, mock_get_user, client, mock_user):
        """Test subscription upgrade with validation error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.upgrade_subscription = AsyncMock(side_effect=ValueError("New plan must be higher tier"))
        mock_service_class.return_value = mock_service
        
        upgrade_data = {"new_plan_id": 1}
        
        # Act
        response = client.post("/api/v1/subscription/upgrade", json=upgrade_data)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_downgrade_subscription_success(self, mock_service_class, mock_get_user, client, mock_user, mock_subscription):
        """Test successful subscription downgrade."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.downgrade_subscription = AsyncMock(return_value=mock_subscription)
        mock_service_class.return_value = mock_service
        
        downgrade_data = {"new_plan_id": 1}
        
        # Act
        response = client.post("/api/v1/subscription/downgrade", json=downgrade_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Subscription downgrade scheduled successfully"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_cancel_subscription_success(self, mock_service_class, mock_get_user, client, mock_user, mock_subscription):
        """Test successful subscription cancellation."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.cancel_subscription = AsyncMock(return_value=mock_subscription)
        mock_service_class.return_value = mock_service
        
        cancel_data = {
            "reason": "No longer needed",
            "cancel_at_period_end": True
        }
        
        # Act
        response = client.post("/api/v1/subscription/cancel", json=cancel_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Subscription cancelled successfully"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_cancel_subscription_no_subscription(self, mock_service_class, mock_get_user, client, mock_user):
        """Test subscription cancellation when user has no subscription."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.cancel_subscription = AsyncMock(side_effect=ValueError("User has no active subscription"))
        mock_service_class.return_value = mock_service
        
        cancel_data = {
            "reason": "No longer needed",
            "cancel_at_period_end": True
        }
        
        # Act
        response = client.post("/api/v1/subscription/cancel", json=cancel_data)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUtilityEndpoints:
    """Test utility endpoints."""
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_initialize_default_plans_success(self, mock_service_class, mock_get_user, client, mock_user):
        """Test successful default plans initialization."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        
        default_plans = [
            Plan(id=1, plan_name="free", price_monthly=0, features={}, api_quota_daily=10, ai_analysis_quota_daily=5, is_active=True),
            Plan(id=2, plan_name="pro", price_monthly=2980, features={"real_time_data": True}, api_quota_daily=100, ai_analysis_quota_daily=50, is_active=True),
            Plan(id=3, plan_name="business", price_monthly=9800, features={"real_time_data": True, "api_access": True}, api_quota_daily=1000, ai_analysis_quota_daily=200, is_active=True)
        ]
        
        mock_service.initialize_default_plans = AsyncMock(return_value=default_plans)
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/subscription/initialize-plans")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3
        assert data["data"][0]["plan_name"] == "free"
        assert data["data"][1]["plan_name"] == "pro"
        assert data["data"][2]["plan_name"] == "business"
    
    @patch('app.api.v1.subscription.get_current_active_user')
    @patch('app.services.subscription_service.SubscriptionService')
    def test_initialize_default_plans_error(self, mock_service_class, mock_get_user, client, mock_user):
        """Test default plans initialization with error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_service = Mock()
        mock_service.initialize_default_plans = AsyncMock(side_effect=Exception("Database error"))
        mock_service_class.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/subscription/initialize-plans")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAuthenticationRequired:
    """Test that endpoints require authentication."""
    
    def test_endpoints_require_authentication(self, client):
        """Test that subscription endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/subscription/plans"),
            ("GET", "/api/v1/subscription/plans/compare"),
            ("GET", "/api/v1/subscription/my-subscription"),
            ("GET", "/api/v1/subscription/usage"),
            ("POST", "/api/v1/subscription/upgrade"),
            ("POST", "/api/v1/subscription/downgrade"),
            ("POST", "/api/v1/subscription/cancel"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            
            # Should return 401 or 403 for unauthenticated requests
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]