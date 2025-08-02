"""
Tests for quota enforcement middleware.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.quota_middleware import (
    _should_enforce_quota,
    _get_quota_type,
    enforce_quota,
    create_quota_enforcement_middleware
)
from app.models.user import User


class TestQuotaMiddlewareHelpers:
    """Test helper functions for quota middleware."""
    
    def test_should_enforce_quota_stock_endpoints(self):
        """Test quota enforcement detection for stock endpoints."""
        # Mock request for stock search
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
        
        # Mock request for specific stock
        request.url.path = "/api/v1/stocks/7203"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
        
        # Mock request for stock POST
        request.url.path = "/api/v1/stocks/"
        request.method = "POST"
        
        assert _should_enforce_quota(request) is True
    
    def test_should_enforce_quota_analysis_endpoints(self):
        """Test quota enforcement detection for analysis endpoints."""
        # Mock request for analysis generation
        request = Mock(spec=Request)
        request.url.path = "/api/v1/analysis/generate"
        request.method = "POST"
        
        assert _should_enforce_quota(request) is True
        
        # Mock request for specific analysis
        request.url.path = "/api/v1/analysis/7203"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
    
    def test_should_enforce_quota_news_endpoints(self):
        """Test quota enforcement detection for news endpoints."""
        # Mock request for news
        request = Mock(spec=Request)
        request.url.path = "/api/v1/news/"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
        
        # Mock request for stock-specific news
        request.url.path = "/api/v1/news/stock/7203"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
        
        # Mock request for sentiment
        request.url.path = "/api/v1/sentiment/7203"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
    
    def test_should_enforce_quota_market_endpoints(self):
        """Test quota enforcement detection for market endpoints."""
        # Mock request for market indices
        request = Mock(spec=Request)
        request.url.path = "/api/v1/market/indices"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
        
        # Mock request for hot stocks
        request.url.path = "/api/v1/market/hot-stocks"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is True
    
    def test_should_enforce_quota_non_enforced_endpoints(self):
        """Test quota enforcement detection for non-enforced endpoints."""
        # Mock request for auth endpoints
        request = Mock(spec=Request)
        request.url.path = "/api/v1/auth/login"
        request.method = "POST"
        
        assert _should_enforce_quota(request) is False
        
        # Mock request for subscription endpoints
        request.url.path = "/api/v1/subscription/plans"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is False
        
        # Mock request for health check
        request.url.path = "/api/v1/health"
        request.method = "GET"
        
        assert _should_enforce_quota(request) is False
    
    def test_get_quota_type_analysis_endpoints(self):
        """Test quota type detection for analysis endpoints."""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/analysis/generate"
        
        assert _get_quota_type(request) == "ai_analysis"
        
        request.url.path = "/api/v1/analysis/7203"
        assert _get_quota_type(request) == "ai_analysis"
    
    def test_get_quota_type_api_endpoints(self):
        """Test quota type detection for general API endpoints."""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        
        assert _get_quota_type(request) == "api"
        
        request.url.path = "/api/v1/news/stock/7203"
        assert _get_quota_type(request) == "api"
        
        request.url.path = "/api/v1/market/indices"
        assert _get_quota_type(request) == "api"


class TestQuotaEnforcementDecorator:
    """Test quota enforcement decorator."""
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        user = Mock(spec=User)
        user.id = uuid4()
        return user
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_request(self):
        """Mock request object."""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        return request
    
    async def test_enforce_quota_decorator_with_quota_available(self, mock_user, mock_db, mock_request):
        """Test quota enforcement decorator when quota is available."""
        
        @enforce_quota("api")
        async def test_endpoint(request=None, current_user=None, db=None):
            return {"success": True, "data": "test"}
        
        with patch('app.core.quota_middleware.QuotaService') as mock_quota_service_class:
            mock_quota_service = Mock()
            mock_quota_service_class.return_value = mock_quota_service
            
            # Mock quota check - user has quota
            mock_quota_service.check_quota_available = AsyncMock(return_value=(
                True,
                {
                    "quota_type": "api",
                    "usage": 5,
                    "limit": 100,
                    "remaining": 95,
                    "reset_at": "2024-01-01T00:00:00Z"
                }
            ))
            
            # Mock usage recording
            mock_quota_service.record_api_usage = AsyncMock()
            
            result = await test_endpoint(
                request=mock_request,
                current_user=mock_user,
                db=mock_db
            )
            
            assert result == {"success": True, "data": "test"}
            mock_quota_service.check_quota_available.assert_called_once_with(mock_user.id, "api")
            mock_quota_service.record_api_usage.assert_called_once()
    
    async def test_enforce_quota_decorator_with_quota_exceeded(self, mock_user, mock_db, mock_request):
        """Test quota enforcement decorator when quota is exceeded."""
        
        @enforce_quota("api")
        async def test_endpoint(request=None, current_user=None, db=None):
            return {"success": True, "data": "test"}
        
        with patch('app.core.quota_middleware.QuotaService') as mock_quota_service_class:
            mock_quota_service = Mock()
            mock_quota_service_class.return_value = mock_quota_service
            
            # Mock quota check - user has no quota
            mock_quota_service.check_quota_available = AsyncMock(return_value=(
                False,
                {
                    "quota_type": "api",
                    "usage": 100,
                    "limit": 100,
                    "remaining": 0,
                    "reset_at": "2024-01-01T00:00:00Z"
                }
            ))
            
            with pytest.raises(HTTPException) as exc_info:
                await test_endpoint(
                    request=mock_request,
                    current_user=mock_user,
                    db=mock_db
                )
            
            assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Quota exceeded" in str(exc_info.value.detail)
            mock_quota_service.check_quota_available.assert_called_once_with(mock_user.id, "api")
    
    async def test_enforce_quota_decorator_with_ai_analysis_quota(self, mock_user, mock_db, mock_request):
        """Test quota enforcement decorator with AI analysis quota type."""
        
        @enforce_quota("ai_analysis")
        async def test_endpoint(request=None, current_user=None, db=None):
            return {"success": True, "data": "analysis"}
        
        with patch('app.core.quota_middleware.QuotaService') as mock_quota_service_class:
            mock_quota_service = Mock()
            mock_quota_service_class.return_value = mock_quota_service
            
            # Mock quota check - user has quota
            mock_quota_service.check_quota_available = AsyncMock(return_value=(
                True,
                {
                    "quota_type": "ai_analysis",
                    "usage": 2,
                    "limit": 50,
                    "remaining": 48,
                    "reset_at": "2024-01-01T00:00:00Z"
                }
            ))
            
            # Mock usage recording
            mock_quota_service.record_api_usage = AsyncMock()
            
            result = await test_endpoint(
                request=mock_request,
                current_user=mock_user,
                db=mock_db
            )
            
            assert result == {"success": True, "data": "analysis"}
            mock_quota_service.check_quota_available.assert_called_once_with(mock_user.id, "ai_analysis")
    
    async def test_enforce_quota_decorator_without_user(self, mock_db, mock_request):
        """Test quota enforcement decorator without authenticated user."""
        
        @enforce_quota("api")
        async def test_endpoint(request=None, current_user=None, db=None):
            return {"success": True, "data": "test"}
        
        # Call without current_user
        result = await test_endpoint(
            request=mock_request,
            current_user=None,
            db=mock_db
        )
        
        # Should proceed without quota check
        assert result == {"success": True, "data": "test"}
    
    async def test_enforce_quota_decorator_with_endpoint_error(self, mock_user, mock_db, mock_request):
        """Test quota enforcement decorator when endpoint raises an error."""
        
        @enforce_quota("api")
        async def test_endpoint(request=None, current_user=None, db=None):
            raise ValueError("Endpoint error")
        
        with patch('app.core.quota_middleware.QuotaService') as mock_quota_service_class:
            mock_quota_service = Mock()
            mock_quota_service_class.return_value = mock_quota_service
            
            # Mock quota check - user has quota
            mock_quota_service.check_quota_available = AsyncMock(return_value=(
                True,
                {
                    "quota_type": "api",
                    "usage": 5,
                    "limit": 100,
                    "remaining": 95,
                    "reset_at": "2024-01-01T00:00:00Z"
                }
            ))
            
            # Mock usage recording
            mock_quota_service.record_api_usage = AsyncMock()
            
            with pytest.raises(ValueError, match="Endpoint error"):
                await test_endpoint(
                    request=mock_request,
                    current_user=mock_user,
                    db=mock_db
                )
            
            # Should still record usage with error status
            mock_quota_service.record_api_usage.assert_called_once()
            call_args = mock_quota_service.record_api_usage.call_args
            assert call_args[1]["status_code"] == 500


class TestQuotaMiddlewareFactory:
    """Test quota middleware factory function."""
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        user = Mock(spec=User)
        user.id = uuid4()
        return user
    
    async def test_middleware_factory_with_quota_available(self, mock_user):
        """Test middleware factory when quota is available."""
        middleware = create_quota_enforcement_middleware()
        
        # Mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        request.method = "GET"
        request.state.user = mock_user
        
        # Mock call_next function
        async def mock_call_next(req):
            return JSONResponse(content={"success": True})
        
        with patch('app.core.quota_middleware.get_db') as mock_get_db, \
             patch('app.core.quota_middleware.QuotaService') as mock_quota_service_class:
            
            # Mock database
            mock_db = Mock()
            mock_get_db.return_value = iter([mock_db])
            
            # Mock quota service
            mock_quota_service = Mock()
            mock_quota_service_class.return_value = mock_quota_service
            mock_quota_service.check_quota_available = AsyncMock(return_value=(
                True,
                {
                    "quota_type": "api",
                    "usage": 5,
                    "limit": 100,
                    "remaining": 95,
                    "reset_at": "2024-01-01T00:00:00Z"
                }
            ))
            
            dispatch = middleware(request, mock_call_next)
            response = await dispatch(request)
            
            assert response.status_code == 200
            mock_quota_service.check_quota_available.assert_called_once_with(mock_user.id, "api")
    
    async def test_middleware_factory_with_quota_exceeded(self, mock_user):
        """Test middleware factory when quota is exceeded."""
        middleware = create_quota_enforcement_middleware()
        
        # Mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        request.method = "GET"
        request.state.user = mock_user
        
        # Mock call_next function
        async def mock_call_next(req):
            return JSONResponse(content={"success": True})
        
        with patch('app.core.quota_middleware.get_db') as mock_get_db, \
             patch('app.core.quota_middleware.QuotaService') as mock_quota_service_class:
            
            # Mock database
            mock_db = Mock()
            mock_get_db.return_value = iter([mock_db])
            
            # Mock quota service
            mock_quota_service = Mock()
            mock_quota_service_class.return_value = mock_quota_service
            mock_quota_service.check_quota_available = AsyncMock(return_value=(
                False,
                {
                    "quota_type": "api",
                    "usage": 100,
                    "limit": 100,
                    "remaining": 0,
                    "reset_at": "2024-01-01T00:00:00Z"
                }
            ))
            
            dispatch = middleware(request, mock_call_next)
            response = await dispatch(request)
            
            assert response.status_code == 429
            mock_quota_service.check_quota_available.assert_called_once_with(mock_user.id, "api")
    
    async def test_middleware_factory_non_enforced_endpoint(self, mock_user):
        """Test middleware factory with non-enforced endpoint."""
        middleware = create_quota_enforcement_middleware()
        
        # Mock request for non-enforced endpoint
        request = Mock(spec=Request)
        request.url.path = "/api/v1/auth/login"
        request.method = "POST"
        request.state.user = mock_user
        
        # Mock call_next function
        async def mock_call_next(req):
            return JSONResponse(content={"success": True})
        
        dispatch = middleware(request, mock_call_next)
        response = await dispatch(request)
        
        # Should proceed without quota check
        assert response.status_code == 200
    
    async def test_middleware_factory_without_user(self):
        """Test middleware factory without authenticated user."""
        middleware = create_quota_enforcement_middleware()
        
        # Mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        request.method = "GET"
        request.state.user = None
        
        # Mock call_next function
        async def mock_call_next(req):
            return JSONResponse(content={"success": True})
        
        dispatch = middleware(request, mock_call_next)
        response = await dispatch(request)
        
        # Should proceed without quota check
        assert response.status_code == 200
    
    async def test_middleware_factory_with_exception(self, mock_user):
        """Test middleware factory when quota check raises exception."""
        middleware = create_quota_enforcement_middleware()
        
        # Mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/stocks/search"
        request.method = "GET"
        request.state.user = mock_user
        
        # Mock call_next function
        async def mock_call_next(req):
            return JSONResponse(content={"success": True})
        
        with patch('app.core.quota_middleware.get_db') as mock_get_db:
            # Mock database to raise exception
            mock_get_db.side_effect = Exception("Database error")
            
            dispatch = middleware(request, mock_call_next)
            response = await dispatch(request)
            
            # Should proceed despite exception (graceful degradation)
            assert response.status_code == 200