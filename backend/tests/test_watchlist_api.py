"""
Tests for watchlist API endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime, date

from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.schemas.watchlist import WatchlistStockWithPrice


class TestWatchlistAPI:
    """Test cases for watchlist API endpoints."""
    
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
            email_verified_at=datetime.utcnow().isoformat()
        )
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers."""
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def sample_watchlist_stock(self, mock_user):
        """Sample watchlist stock with price data."""
        return WatchlistStockWithPrice(
            id=None,
            user_id=mock_user.id,
            ticker="7203",
            notes="Great automotive company",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            stock=None,
            current_price=2520.0,
            price_change=20.0,
            price_change_percent=0.8,
            volume_today=1000000,
            last_updated=date.today(),
            price_alert_triggered=False,
            volume_alert_triggered=False
        )
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.get_user_watchlist_with_prices')
    def test_get_user_watchlist_success(
        self, 
        mock_get_watchlist, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_watchlist_stock
    ):
        """Test successful retrieval of user watchlist."""
        mock_get_user.return_value = mock_user
        mock_get_watchlist.return_value = [sample_watchlist_stock]
        
        response = client.get("/api/v1/watchlist/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "7203"
        assert data[0]["current_price"] == 2520.0
        assert data[0]["notes"] == "Great automotive company"
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.get_user_watchlist_with_prices')
    def test_get_user_watchlist_empty(
        self, 
        mock_get_watchlist, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test retrieval of empty watchlist."""
        mock_get_user.return_value = mock_user
        mock_get_watchlist.return_value = []
        
        response = client.get("/api/v1/watchlist/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.add_stock_to_watchlist')
    def test_add_stock_to_watchlist_success(
        self, 
        mock_add_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_watchlist_stock
    ):
        """Test successful addition of stock to watchlist."""
        mock_get_user.return_value = mock_user
        mock_add_stock.return_value = sample_watchlist_stock
        
        request_data = {
            "ticker": "7203",
            "notes": "Great automotive company"
        }
        
        response = client.post("/api/v1/watchlist/", json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "7203"
        assert data["notes"] == "Great automotive company"
        
        mock_add_stock.assert_called_once_with(
            user_id=mock_user.id,
            ticker="7203",
            notes="Great automotive company"
        )
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.add_stock_to_watchlist')
    def test_add_stock_to_watchlist_already_exists(
        self, 
        mock_add_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test adding stock that already exists in watchlist."""
        mock_get_user.return_value = mock_user
        mock_add_stock.side_effect = ValueError("Stock 7203 is already in watchlist")
        
        request_data = {
            "ticker": "7203",
            "notes": "Great automotive company"
        }
        
        response = client.post("/api/v1/watchlist/", json=request_data, headers=auth_headers)
        
        assert response.status_code == 422
        data = response.json()
        assert "already in watchlist" in data["detail"]
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.update_watchlist_stock')
    def test_update_watchlist_stock_success(
        self, 
        mock_update_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_watchlist_stock
    ):
        """Test successful update of watchlist stock."""
        mock_get_user.return_value = mock_user
        updated_stock = sample_watchlist_stock.copy()
        updated_stock.notes = "Updated notes"
        mock_update_stock.return_value = updated_stock
        
        request_data = {
            "notes": "Updated notes"
        }
        
        response = client.put("/api/v1/watchlist/7203", json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "7203"
        assert data["notes"] == "Updated notes"
        
        mock_update_stock.assert_called_once_with(
            user_id=mock_user.id,
            ticker="7203",
            notes="Updated notes"
        )
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.remove_stock_from_watchlist')
    def test_remove_stock_from_watchlist_success(
        self, 
        mock_remove_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test successful removal of stock from watchlist."""
        mock_get_user.return_value = mock_user
        mock_remove_stock.return_value = None
        
        response = client.delete("/api/v1/watchlist/7203", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Stock removed from watchlist"
        
        mock_remove_stock.assert_called_once_with(
            user_id=mock_user.id,
            ticker="7203"
        )
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.remove_stock_from_watchlist')
    def test_remove_stock_from_watchlist_not_found(
        self, 
        mock_remove_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test removing stock that's not in watchlist."""
        mock_get_user.return_value = mock_user
        mock_remove_stock.side_effect = ValueError("Stock 7203 not found in watchlist")
        
        response = client.delete("/api/v1/watchlist/7203", headers=auth_headers)
        
        assert response.status_code == 422
        data = response.json()
        assert "not found in watchlist" in data["detail"]
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.get_watchlist_stock')
    def test_get_watchlist_stock_success(
        self, 
        mock_get_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_watchlist_stock
    ):
        """Test successful retrieval of specific watchlist stock."""
        mock_get_user.return_value = mock_user
        mock_get_stock.return_value = sample_watchlist_stock
        
        response = client.get("/api/v1/watchlist/7203", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "7203"
        assert data["current_price"] == 2520.0
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.get_watchlist_stock')
    def test_get_watchlist_stock_not_found(
        self, 
        mock_get_stock, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test retrieval of non-existent watchlist stock."""
        mock_get_user.return_value = mock_user
        mock_get_stock.return_value = None
        
        response = client.get("/api/v1/watchlist/7203", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Stock not found in watchlist"
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.bulk_add_stocks_to_watchlist')
    def test_bulk_add_stocks_success(
        self, 
        mock_bulk_add, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test successful bulk addition of stocks."""
        mock_get_user.return_value = mock_user
        mock_bulk_add.return_value = {
            "successful": ["7203", "6758"],
            "failed": [],
            "already_exists": []
        }
        
        request_data = ["7203", "6758"]
        
        response = client.post("/api/v1/watchlist/bulk-add", json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["successful"]) == 2
        assert "7203" in data["successful"]
        assert "6758" in data["successful"]
    
    @patch('app.core.deps.get_current_user')
    @patch('app.services.watchlist_service.WatchlistService.bulk_remove_stocks_from_watchlist')
    def test_bulk_remove_stocks_success(
        self, 
        mock_bulk_remove, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test successful bulk removal of stocks."""
        mock_get_user.return_value = mock_user
        mock_bulk_remove.return_value = {
            "successful": ["7203"],
            "not_found": ["6758"]
        }
        
        request_data = ["7203", "6758"]
        
        response = client.delete("/api/v1/watchlist/bulk-remove", json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["successful"]) == 1
        assert "7203" in data["successful"]
        assert len(data["not_found"]) == 1
        assert "6758" in data["not_found"]
    
    def test_get_watchlist_unauthorized(self, client):
        """Test accessing watchlist without authentication."""
        response = client.get("/api/v1/watchlist/")
        
        assert response.status_code == 401
    
    def test_add_stock_invalid_data(self, client, auth_headers):
        """Test adding stock with invalid data."""
        request_data = {
            "ticker": "",  # Empty ticker
            "notes": "Some notes"
        }
        
        response = client.post("/api/v1/watchlist/", json=request_data, headers=auth_headers)
        
        assert response.status_code == 422