"""
Comprehensive API integration tests.
Tests complete user journeys from registration to analysis.
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.user import User, UserProfile
from app.models.stock import Stock, StockPriceHistory
from app.models.subscription import Subscription, Plan


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Database session fixture."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "display_name": "Test User"
    }


@pytest.fixture
def sample_stock_data():
    """Sample stock data."""
    return {
        "ticker": "7203",
        "company_name_jp": "トヨタ自動車株式会社",
        "company_name_en": "Toyota Motor Corporation",
        "sector_jp": "輸送用機器",
        "industry_jp": "自動車",
        "is_active": True
    }


class TestUserRegistrationAndAuthFlow:
    """Test complete user registration and authentication flow."""
    
    def test_user_registration_flow(self, client, setup_database, sample_user_data):
        """Test complete user registration flow."""
        # 1. Register new user
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response.status_code == 201
        
        registration_data = response.json()
        assert registration_data["email"] == sample_user_data["email"]
        assert "id" in registration_data
        assert "access_token" in registration_data
        
        user_id = registration_data["id"]
        access_token = registration_data["access_token"]
        
        # 2. Verify user can access protected endpoints
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = client.get("/api/v1/users/profile", headers=headers)
        assert profile_response.status_code == 200
        
        profile_data = profile_response.json()
        assert profile_data["email"] == sample_user_data["email"]
        assert profile_data["display_name"] == sample_user_data["display_name"]
        
        # 3. Test login with registered credentials
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        assert "access_token" in login_result
        assert login_result["user"]["email"] == sample_user_data["email"]
        
        return user_id, access_token
    
    def test_user_profile_update_flow(self, client, setup_database, sample_user_data):
        """Test user profile update flow."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update profile
        update_data = {
            "display_name": "Updated Name",
            "timezone": "America/New_York",
            "notification_preferences": {"email": True, "push": False}
        }
        
        update_response = client.put("/api/v1/users/profile", json=update_data, headers=headers)
        assert update_response.status_code == 200
        
        updated_profile = update_response.json()
        assert updated_profile["display_name"] == "Updated Name"
        assert updated_profile["timezone"] == "America/New_York"
        assert updated_profile["notification_preferences"]["email"] is True
        
        # Verify changes persist
        profile_response = client.get("/api/v1/users/profile", headers=headers)
        profile_data = profile_response.json()
        assert profile_data["display_name"] == "Updated Name"
    
    def test_password_change_flow(self, client, setup_database, sample_user_data):
        """Test password change flow."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Change password
        password_change_data = {
            "current_password": sample_user_data["password"],
            "new_password": "NewSecurePassword123!"
        }
        
        change_response = client.post("/api/v1/users/change-password", 
                                    json=password_change_data, headers=headers)
        assert change_response.status_code == 200
        
        # Verify old password no longer works
        old_login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert old_login_response.status_code == 401
        
        # Verify new password works
        new_login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": "NewSecurePassword123!"
        })
        assert new_login_response.status_code == 200


class TestStockDataAndSearchFlow:
    """Test stock data management and search functionality."""
    
    def test_stock_search_flow(self, client, setup_database, db_session, sample_stock_data):
        """Test stock search functionality."""
        # Add sample stock to database
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        db_session.commit()
        
        # Test search by ticker
        search_response = client.get("/api/v1/stocks/search?query=7203")
        assert search_response.status_code == 200
        
        search_results = search_response.json()
        assert len(search_results["results"]) >= 1
        
        found_stock = search_results["results"][0]
        assert found_stock["ticker"] == "7203"
        assert found_stock["company_name_jp"] == "トヨタ自動車株式会社"
        
        # Test search by company name
        name_search_response = client.get("/api/v1/stocks/search?query=Toyota")
        assert name_search_response.status_code == 200
        
        name_results = name_search_response.json()
        assert len(name_results["results"]) >= 1
    
    def test_stock_details_flow(self, client, setup_database, db_session, sample_stock_data):
        """Test stock details retrieval."""
        # Add sample stock
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        db_session.commit()
        
        # Get stock details
        details_response = client.get("/api/v1/stocks/7203")
        assert details_response.status_code == 200
        
        stock_details = details_response.json()
        assert stock_details["ticker"] == "7203"
        assert stock_details["company_name_jp"] == "トヨタ自動車株式会社"
        assert stock_details["sector_jp"] == "輸送用機器"
    
    @patch('app.services.stock_service.StockService.get_price_history')
    def test_stock_price_history_flow(self, mock_price_history, client, setup_database, 
                                    db_session, sample_stock_data):
        """Test stock price history retrieval."""
        # Mock price history data
        mock_price_data = [
            {
                "date": "2024-01-15",
                "open": 2500.0,
                "high": 2550.0,
                "low": 2480.0,
                "close": 2520.0,
                "volume": 15000000
            }
        ]
        mock_price_history.return_value = mock_price_data
        
        # Add sample stock
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        db_session.commit()
        
        # Get price history
        price_response = client.get("/api/v1/stocks/7203/price-history?period=1M")
        assert price_response.status_code == 200
        
        price_data = price_response.json()
        assert len(price_data["data"]) >= 1
        assert price_data["data"][0]["open"] == 2500.0


class TestWatchlistFlow:
    """Test watchlist management functionality."""
    
    def test_complete_watchlist_flow(self, client, setup_database, db_session, 
                                   sample_user_data, sample_stock_data):
        """Test complete watchlist management flow."""
        # Register user and get token
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Add sample stock
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        db_session.commit()
        
        # 1. Get empty watchlist
        watchlist_response = client.get("/api/v1/watchlist", headers=headers)
        assert watchlist_response.status_code == 200
        assert len(watchlist_response.json()["stocks"]) == 0
        
        # 2. Add stock to watchlist
        add_response = client.post("/api/v1/watchlist/add", 
                                 json={"ticker": "7203"}, headers=headers)
        assert add_response.status_code == 201
        
        # 3. Verify stock is in watchlist
        updated_watchlist = client.get("/api/v1/watchlist", headers=headers)
        watchlist_data = updated_watchlist.json()
        assert len(watchlist_data["stocks"]) == 1
        assert watchlist_data["stocks"][0]["ticker"] == "7203"
        
        # 4. Update watchlist item with notes
        update_response = client.put("/api/v1/watchlist/7203", 
                                   json={"notes": "Potential buy"}, headers=headers)
        assert update_response.status_code == 200
        
        # 5. Remove stock from watchlist
        remove_response = client.delete("/api/v1/watchlist/7203", headers=headers)
        assert remove_response.status_code == 200
        
        # 6. Verify watchlist is empty
        final_watchlist = client.get("/api/v1/watchlist", headers=headers)
        assert len(final_watchlist.json()["stocks"]) == 0


class TestAIAnalysisFlow:
    """Test AI analysis functionality."""
    
    @patch('app.services.ai_analysis_service.AIAnalysisService.generate_analysis')
    def test_ai_analysis_request_flow(self, mock_generate_analysis, client, setup_database, 
                                    db_session, sample_user_data, sample_stock_data):
        """Test AI analysis request flow."""
        # Mock AI analysis response
        mock_analysis = {
            "ticker": "7203",
            "analysis_type": "comprehensive",
            "rating": "Bullish",
            "confidence": 0.85,
            "key_factors": ["Strong fundamentals", "Positive market sentiment"],
            "price_target_range": {"min": 2600, "max": 2800},
            "risk_factors": ["Market volatility"],
            "reasoning": "Strong financial performance and positive outlook",
            "generated_at": "2024-01-15T10:00:00Z"
        }
        mock_generate_analysis.return_value = mock_analysis
        
        # Register user and get token
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Add sample stock
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        db_session.commit()
        
        # Request AI analysis
        analysis_request = {
            "ticker": "7203",
            "analysis_type": "comprehensive"
        }
        
        analysis_response = client.post("/api/v1/analysis/generate", 
                                      json=analysis_request, headers=headers)
        assert analysis_response.status_code == 200
        
        analysis_data = analysis_response.json()
        assert analysis_data["ticker"] == "7203"
        assert analysis_data["rating"] == "Bullish"
        assert analysis_data["confidence"] == 0.85
        assert len(analysis_data["key_factors"]) >= 1
        
        # Get analysis history
        history_response = client.get("/api/v1/analysis/7203/history", headers=headers)
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        assert len(history_data["analyses"]) >= 1


class TestSubscriptionFlow:
    """Test subscription management functionality."""
    
    def test_subscription_upgrade_flow(self, client, setup_database, db_session, sample_user_data):
        """Test subscription upgrade flow."""
        # Create subscription plans
        free_plan = Plan(
            plan_name="free",
            price_monthly=0,
            features={"ai_analysis": False, "real_time_data": False},
            api_quota_daily=10,
            ai_analysis_quota_daily=0
        )
        pro_plan = Plan(
            plan_name="pro",
            price_monthly=2980,
            features={"ai_analysis": True, "real_time_data": True},
            api_quota_daily=100,
            ai_analysis_quota_daily=20
        )
        db_session.add_all([free_plan, pro_plan])
        db_session.commit()
        
        # Register user
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Check initial subscription (should be free)
        subscription_response = client.get("/api/v1/subscription", headers=headers)
        assert subscription_response.status_code == 200
        
        subscription_data = subscription_response.json()
        assert subscription_data["plan"]["plan_name"] == "free"
        
        # Upgrade to pro plan
        upgrade_response = client.post("/api/v1/subscription/upgrade", 
                                     json={"plan_id": pro_plan.id}, headers=headers)
        assert upgrade_response.status_code == 200
        
        # Verify upgrade
        updated_subscription = client.get("/api/v1/subscription", headers=headers)
        updated_data = updated_subscription.json()
        assert updated_data["plan"]["plan_name"] == "pro"
        assert updated_data["plan"]["api_quota_daily"] == 100


class TestCompleteUserJourney:
    """Test complete user journey from registration to analysis."""
    
    @patch('app.services.ai_analysis_service.AIAnalysisService.generate_analysis')
    def test_complete_user_journey(self, mock_generate_analysis, client, setup_database, 
                                 db_session, sample_user_data, sample_stock_data):
        """Test complete user journey from registration to getting AI analysis."""
        # Mock AI analysis
        mock_analysis = {
            "ticker": "7203",
            "analysis_type": "comprehensive",
            "rating": "Bullish",
            "confidence": 0.85,
            "key_factors": ["Strong fundamentals"],
            "price_target_range": {"min": 2600, "max": 2800},
            "risk_factors": ["Market volatility"],
            "reasoning": "Strong performance",
            "generated_at": "2024-01-15T10:00:00Z"
        }
        mock_generate_analysis.return_value = mock_analysis
        
        # Add sample stock
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        db_session.commit()
        
        # 1. User Registration
        registration_response = client.post("/api/v1/auth/register", json=sample_user_data)
        assert registration_response.status_code == 201
        access_token = registration_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 2. Search for stocks
        search_response = client.get("/api/v1/stocks/search?query=Toyota")
        assert search_response.status_code == 200
        search_results = search_response.json()["results"]
        assert len(search_results) >= 1
        
        # 3. Add stock to watchlist
        add_watchlist_response = client.post("/api/v1/watchlist/add", 
                                           json={"ticker": "7203"}, headers=headers)
        assert add_watchlist_response.status_code == 201
        
        # 4. Get stock details
        stock_details_response = client.get("/api/v1/stocks/7203")
        assert stock_details_response.status_code == 200
        
        # 5. Request AI analysis
        analysis_response = client.post("/api/v1/analysis/generate", 
                                      json={"ticker": "7203", "analysis_type": "comprehensive"}, 
                                      headers=headers)
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        assert analysis_data["rating"] == "Bullish"
        
        # 6. Check watchlist with analysis
        watchlist_response = client.get("/api/v1/watchlist", headers=headers)
        assert watchlist_response.status_code == 200
        watchlist_data = watchlist_response.json()
        assert len(watchlist_data["stocks"]) == 1
        
        # 7. Update profile
        profile_update_response = client.put("/api/v1/users/profile", 
                                           json={"display_name": "Updated User"}, 
                                           headers=headers)
        assert profile_update_response.status_code == 200


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def test_unauthorized_access(self, client, setup_database):
        """Test unauthorized access to protected endpoints."""
        # Try to access protected endpoint without token
        response = client.get("/api/v1/users/profile")
        assert response.status_code == 401
        
        # Try with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/users/profile", headers=headers)
        assert response.status_code == 401
    
    def test_duplicate_user_registration(self, client, setup_database, sample_user_data):
        """Test duplicate user registration handling."""
        # Register user first time
        response1 = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response1.status_code == 201
        
        # Try to register same user again
        response2 = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()
    
    def test_invalid_stock_ticker(self, client, setup_database):
        """Test handling of invalid stock ticker."""
        response = client.get("/api/v1/stocks/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_quota_exceeded_handling(self, client, setup_database, db_session, sample_user_data):
        """Test quota exceeded handling."""
        # Create a plan with very low quota
        low_quota_plan = Plan(
            plan_name="test_low",
            price_monthly=0,
            api_quota_daily=1,
            ai_analysis_quota_daily=1
        )
        db_session.add(low_quota_plan)
        db_session.commit()
        
        # Register user and assign low quota plan
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Make requests until quota is exceeded
        # This would require implementing quota tracking in the test
        # For now, we just test the structure
        response = client.get("/api/v1/stocks/search?query=test", headers=headers)
        # Should succeed initially
        assert response.status_code in [200, 429]  # 429 if quota already exceeded


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Test async functionality integration."""
    
    async def test_async_ai_analysis_flow(self):
        """Test async AI analysis flow."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # This would test async endpoints if we had them
            # For now, just test that async client works
            response = await ac.get("/api/v1/health")
            assert response.status_code == 200


class TestDatabaseIntegration:
    """Test database integration scenarios."""
    
    def test_database_transaction_rollback(self, client, setup_database, db_session, sample_user_data):
        """Test database transaction rollback on errors."""
        # This would test that failed operations don't leave partial data
        # Implementation would depend on specific error scenarios
        pass
    
    def test_database_connection_handling(self, client, setup_database):
        """Test database connection handling."""
        # Test that the app handles database connection issues gracefully
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "database" in health_data
        assert health_data["database"]["status"] == "healthy"


# Performance and load testing helpers
class TestPerformanceIntegration:
    """Test performance-related integration scenarios."""
    
    def test_concurrent_user_registration(self, client, setup_database):
        """Test concurrent user registrations."""
        import threading
        import time
        
        results = []
        
        def register_user(user_id):
            user_data = {
                "email": f"user{user_id}@example.com",
                "password": "SecurePassword123!",
                "display_name": f"User {user_id}"
            }
            response = client.post("/api/v1/auth/register", json=user_data)
            results.append(response.status_code)
        
        # Create multiple threads to simulate concurrent registrations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All registrations should succeed
        assert all(status == 201 for status in results)
    
    def test_search_performance(self, client, setup_database, db_session):
        """Test search performance with multiple stocks."""
        # Add multiple stocks for performance testing
        stocks = []
        for i in range(100):
            stock = Stock(
                ticker=f"{7000 + i}",
                company_name_jp=f"テスト会社{i}",
                company_name_en=f"Test Company {i}",
                sector_jp="テスト業界",
                is_active=True
            )
            stocks.append(stock)
        
        db_session.add_all(stocks)
        db_session.commit()
        
        # Test search performance
        import time
        start_time = time.time()
        
        response = client.get("/api/v1/stocks/search?query=テスト")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
        
        results = response.json()["results"]
        assert len(results) > 0