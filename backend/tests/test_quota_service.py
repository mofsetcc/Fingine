"""
Tests for quota service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.services.quota_service import QuotaService
from app.models.logs import APIUsageLog
from app.models.analysis import AIAnalysisCache
from app.models.subscription import Subscription, Plan
from app.schemas.subscription import UsageQuota


class TestQuotaService:
    """Test cases for QuotaService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def quota_service(self, mock_db):
        """Create quota service instance."""
        return QuotaService(mock_db)
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_plan(self):
        """Sample subscription plan."""
        return Plan(
            id=1,
            plan_name="pro",
            price_monthly=2980,
            api_quota_daily=100,
            ai_analysis_quota_daily=50,
            is_active=True
        )
    
    @pytest.fixture
    def sample_subscription(self, sample_user_id, sample_plan):
        """Sample subscription."""
        return Subscription(
            id=uuid4(),
            user_id=sample_user_id,
            plan_id=sample_plan.id,
            status="active",
            current_period_start=datetime.now(timezone.utc).isoformat(),
            current_period_end=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            plan=sample_plan
        )
    
    async def test_get_user_quotas_with_active_subscription(self, quota_service, sample_user_id, sample_subscription):
        """Test getting user quotas with active subscription."""
        # Mock subscription service
        with patch.object(quota_service.subscription_service, 'get_user_subscription') as mock_get_sub, \
             patch.object(quota_service.subscription_service, 'get_plan') as mock_get_plan:
            
            mock_get_sub.return_value = sample_subscription
            mock_get_plan.return_value = sample_subscription.plan
            
            quotas = await quota_service.get_user_quotas(sample_user_id)
            
            assert quotas["api_quota_daily"] == 100
            assert quotas["ai_analysis_quota_daily"] == 50
            mock_get_sub.assert_called_once_with(sample_user_id)
            mock_get_plan.assert_called_once_with(sample_subscription.plan_id)
    
    async def test_get_user_quotas_without_subscription(self, quota_service, sample_user_id):
        """Test getting user quotas without subscription (free tier)."""
        with patch.object(quota_service.subscription_service, 'get_user_subscription') as mock_get_sub:
            mock_get_sub.return_value = None
            
            quotas = await quota_service.get_user_quotas(sample_user_id)
            
            assert quotas["api_quota_daily"] == 10  # Free tier default
            assert quotas["ai_analysis_quota_daily"] == 5  # Free tier default
            mock_get_sub.assert_called_once_with(sample_user_id)
    
    async def test_get_user_quotas_with_inactive_subscription(self, quota_service, sample_user_id, sample_subscription):
        """Test getting user quotas with inactive subscription."""
        sample_subscription.status = "cancelled"
        
        with patch.object(quota_service.subscription_service, 'get_user_subscription') as mock_get_sub:
            mock_get_sub.return_value = sample_subscription
            
            quotas = await quota_service.get_user_quotas(sample_user_id)
            
            assert quotas["api_quota_daily"] == 10  # Falls back to free tier
            assert quotas["ai_analysis_quota_daily"] == 5
    
    async def test_get_user_usage_today(self, quota_service, sample_user_id, mock_db):
        """Test getting user's usage for today."""
        # Mock database query results
        mock_db.query.return_value.filter.return_value.scalar.return_value = 15  # API usage
        
        # Mock the second query for AI analysis usage
        mock_query_chain = Mock()
        mock_query_chain.join.return_value.scalar.return_value = 3  # AI analysis usage
        mock_db.query.return_value.filter.return_value = mock_query_chain
        
        usage = await quota_service.get_user_usage_today(sample_user_id)
        
        assert usage["api_usage_today"] == 15
        assert usage["ai_analysis_usage_today"] == 3
    
    async def test_get_usage_quota(self, quota_service, sample_user_id):
        """Test getting comprehensive usage quota information."""
        with patch.object(quota_service, 'get_user_quotas') as mock_get_quotas, \
             patch.object(quota_service, 'get_user_usage_today') as mock_get_usage:
            
            mock_get_quotas.return_value = {
                "api_quota_daily": 100,
                "ai_analysis_quota_daily": 50
            }
            mock_get_usage.return_value = {
                "api_usage_today": 25,
                "ai_analysis_usage_today": 10
            }
            
            usage_quota = await quota_service.get_usage_quota(sample_user_id)
            
            assert isinstance(usage_quota, UsageQuota)
            assert usage_quota.api_quota_daily == 100
            assert usage_quota.api_usage_today == 25
            assert usage_quota.ai_analysis_quota_daily == 50
            assert usage_quota.ai_analysis_usage_today == 10
            assert isinstance(usage_quota.quota_reset_at, datetime)
    
    async def test_check_quota_available_api_has_quota(self, quota_service, sample_user_id):
        """Test checking API quota availability when quota is available."""
        with patch.object(quota_service, 'get_usage_quota') as mock_get_usage:
            mock_usage_quota = UsageQuota(
                api_quota_daily=100,
                api_usage_today=50,
                ai_analysis_quota_daily=50,
                ai_analysis_usage_today=10,
                quota_reset_at=datetime.now(timezone.utc) + timedelta(hours=12)
            )
            mock_get_usage.return_value = mock_usage_quota
            
            has_quota, quota_info = await quota_service.check_quota_available(sample_user_id, "api")
            
            assert has_quota is True
            assert quota_info["quota_type"] == "api"
            assert quota_info["usage"] == 50
            assert quota_info["limit"] == 100
            assert quota_info["remaining"] == 50
    
    async def test_check_quota_available_api_no_quota(self, quota_service, sample_user_id):
        """Test checking API quota availability when quota is exceeded."""
        with patch.object(quota_service, 'get_usage_quota') as mock_get_usage:
            mock_usage_quota = UsageQuota(
                api_quota_daily=100,
                api_usage_today=100,  # At limit
                ai_analysis_quota_daily=50,
                ai_analysis_usage_today=10,
                quota_reset_at=datetime.now(timezone.utc) + timedelta(hours=12)
            )
            mock_get_usage.return_value = mock_usage_quota
            
            has_quota, quota_info = await quota_service.check_quota_available(sample_user_id, "api")
            
            assert has_quota is False
            assert quota_info["quota_type"] == "api"
            assert quota_info["usage"] == 100
            assert quota_info["limit"] == 100
            assert quota_info["remaining"] == 0
    
    async def test_check_quota_available_ai_analysis_has_quota(self, quota_service, sample_user_id):
        """Test checking AI analysis quota availability when quota is available."""
        with patch.object(quota_service, 'get_usage_quota') as mock_get_usage:
            mock_usage_quota = UsageQuota(
                api_quota_daily=100,
                api_usage_today=50,
                ai_analysis_quota_daily=50,
                ai_analysis_usage_today=25,
                quota_reset_at=datetime.now(timezone.utc) + timedelta(hours=12)
            )
            mock_get_usage.return_value = mock_usage_quota
            
            has_quota, quota_info = await quota_service.check_quota_available(sample_user_id, "ai_analysis")
            
            assert has_quota is True
            assert quota_info["quota_type"] == "ai_analysis"
            assert quota_info["usage"] == 25
            assert quota_info["limit"] == 50
            assert quota_info["remaining"] == 25
    
    async def test_check_quota_available_invalid_type(self, quota_service, sample_user_id):
        """Test checking quota availability with invalid quota type."""
        with patch.object(quota_service, 'get_usage_quota') as mock_get_usage:
            mock_usage_quota = UsageQuota(
                api_quota_daily=100,
                api_usage_today=50,
                ai_analysis_quota_daily=50,
                ai_analysis_usage_today=25,
                quota_reset_at=datetime.now(timezone.utc) + timedelta(hours=12)
            )
            mock_get_usage.return_value = mock_usage_quota
            
            has_quota, quota_info = await quota_service.check_quota_available(sample_user_id, "invalid_type")
            
            assert has_quota is False
            assert "error" in quota_info
            assert "Unknown quota type" in quota_info["error"]
    
    async def test_record_api_usage(self, quota_service, sample_user_id, mock_db):
        """Test recording API usage."""
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        usage_log = await quota_service.record_api_usage(
            user_id=sample_user_id,
            api_provider="test_provider",
            endpoint="/api/test",
            request_type="api",
            cost_usd=0.001,
            response_time_ms=150,
            status_code=200
        )
        
        assert isinstance(usage_log, APIUsageLog)
        assert usage_log.user_id == sample_user_id
        assert usage_log.api_provider == "test_provider"
        assert usage_log.endpoint == "/api/test"
        assert usage_log.request_type == "api"
        assert usage_log.cost_usd == 0.001
        assert usage_log.response_time_ms == 150
        assert usage_log.status_code == 200
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    async def test_record_api_usage_database_error(self, quota_service, sample_user_id, mock_db):
        """Test recording API usage with database error."""
        mock_db.add = Mock()
        mock_db.commit = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = Mock()
        
        with pytest.raises(Exception, match="Database error"):
            await quota_service.record_api_usage(
                user_id=sample_user_id,
                api_provider="test_provider"
            )
        
        mock_db.rollback.assert_called_once()
    
    async def test_get_quota_usage_summary(self, quota_service, sample_user_id, mock_db):
        """Test getting quota usage summary."""
        # Mock database execute result
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            Mock(
                usage_date=datetime.now(timezone.utc).date(),
                api_calls=25,
                ai_analysis_calls=5,
                avg_response_time=120.5,
                total_cost=0.025
            ),
            Mock(
                usage_date=(datetime.now(timezone.utc) - timedelta(days=1)).date(),
                api_calls=30,
                ai_analysis_calls=8,
                avg_response_time=135.2,
                total_cost=0.032
            )
        ]
        mock_db.execute.return_value = mock_result
        
        with patch.object(quota_service, 'get_user_quotas') as mock_get_quotas:
            mock_get_quotas.return_value = {
                "api_quota_daily": 100,
                "ai_analysis_quota_daily": 50
            }
            
            summary = await quota_service.get_quota_usage_summary(sample_user_id, days=7)
            
            assert summary["period_days"] == 7
            assert "start_date" in summary
            assert "end_date" in summary
            assert summary["current_quotas"]["api_quota_daily"] == 100
            assert summary["current_quotas"]["ai_analysis_quota_daily"] == 50
            assert len(summary["usage_by_date"]) == 2
            assert summary["total_api_calls"] == 55  # 25 + 30
            assert summary["total_ai_analysis_calls"] == 13  # 5 + 8
            assert summary["total_cost_usd"] == 0.057  # 0.025 + 0.032
    
    async def test_get_quota_exceeded_users(self, quota_service):
        """Test getting users who exceeded quotas."""
        # This is a placeholder implementation that returns empty list
        result = await quota_service.get_quota_exceeded_users("api")
        assert result == []
        
        result = await quota_service.get_quota_exceeded_users("ai_analysis")
        assert result == []


@pytest.mark.asyncio
class TestQuotaServiceIntegration:
    """Integration tests for QuotaService with real database operations."""
    
    # These would be actual integration tests with a test database
    # For now, they're placeholders to show the structure
    
    async def test_quota_tracking_end_to_end(self):
        """Test complete quota tracking workflow."""
        # This would test the complete flow:
        # 1. User makes API call
        # 2. Usage is recorded
        # 3. Quota is checked
        # 4. Usage is retrieved correctly
        pass
    
    async def test_quota_reset_behavior(self):
        """Test quota reset at midnight UTC."""
        # This would test that quotas reset properly at midnight
        pass
    
    async def test_concurrent_quota_checks(self):
        """Test quota checking under concurrent load."""
        # This would test race conditions in quota checking
        pass