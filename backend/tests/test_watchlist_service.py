"""
Tests for watchlist service.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime, date
from decimal import Decimal

from app.services.watchlist_service import WatchlistService
from app.models.watchlist import UserWatchlist
from app.models.stock import Stock, StockPriceHistory
from app.schemas.watchlist import WatchlistStockWithPrice


class TestWatchlistService:
    """Test cases for WatchlistService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def watchlist_service(self, mock_db):
        """Create watchlist service with mocked dependencies."""
        return WatchlistService(mock_db)
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_stock(self):
        """Sample stock object."""
        return Stock(
            ticker="7203",
            company_name_jp="トヨタ自動車株式会社",
            company_name_en="Toyota Motor Corporation",
            sector_jp="輸送用機器",
            is_active=True
        )
    
    @pytest.fixture
    def sample_watchlist_entry(self, sample_user_id):
        """Sample watchlist entry."""
        return UserWatchlist(
            user_id=sample_user_id,
            ticker="7203",
            notes="Great automotive company",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_price_data(self):
        """Sample price history data."""
        return [
            StockPriceHistory(
                ticker="7203",
                date=date.today(),
                open=Decimal("2500.0"),
                high=Decimal("2550.0"),
                low=Decimal("2480.0"),
                close=Decimal("2520.0"),
                volume=1000000
            ),
            StockPriceHistory(
                ticker="7203",
                date=date(2024, 1, 1),
                open=Decimal("2480.0"),
                high=Decimal("2520.0"),
                low=Decimal("2460.0"),
                close=Decimal("2500.0"),
                volume=800000
            )
        ]
    
    @pytest.mark.asyncio
    async def test_get_user_watchlist_with_prices_success(
        self, 
        watchlist_service, 
        sample_user_id, 
        sample_watchlist_entry, 
        sample_stock,
        sample_price_data
    ):
        """Test successful retrieval of user watchlist with prices."""
        # Mock database queries
        watchlist_service.db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = [
            sample_watchlist_entry
        ]
        sample_watchlist_entry.stock = sample_stock
        
        # Mock price data query
        with patch.object(watchlist_service, '_get_current_price_data') as mock_price:
            mock_price.return_value = {
                'current_price': 2520.0,
                'price_change': 20.0,
                'price_change_percent': 0.8,
                'volume_today': 1000000,
                'last_updated': date.today()
            }
            
            result = await watchlist_service.get_user_watchlist_with_prices(sample_user_id)
            
            assert len(result) == 1
            assert result[0].ticker == "7203"
            assert result[0].current_price == 2520.0
            assert result[0].price_change == 20.0
            assert result[0].notes == "Great automotive company"
    
    @pytest.mark.asyncio
    async def test_add_stock_to_watchlist_success(
        self, 
        watchlist_service, 
        sample_user_id, 
        sample_stock
    ):
        """Test successful addition of stock to watchlist."""
        # Mock stock exists
        watchlist_service.db.query.return_value.filter.return_value.first.side_effect = [
            sample_stock,  # Stock exists
            None  # Not in watchlist yet
        ]
        
        # Mock price data
        with patch.object(watchlist_service, '_get_current_price_data') as mock_price:
            mock_price.return_value = {
                'current_price': 2520.0,
                'price_change': 20.0,
                'price_change_percent': 0.8,
                'volume_today': 1000000,
                'last_updated': date.today()
            }
            
            result = await watchlist_service.add_stock_to_watchlist(
                user_id=sample_user_id,
                ticker="7203",
                notes="Investment opportunity"
            )
            
            assert result.ticker == "7203"
            assert result.notes == "Investment opportunity"
            assert result.current_price == 2520.0
            
            # Verify database operations
            watchlist_service.db.add.assert_called_once()
            watchlist_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_stock_to_watchlist_stock_not_found(
        self, 
        watchlist_service, 
        sample_user_id
    ):
        """Test adding non-existent stock to watchlist."""
        # Mock stock doesn't exist
        watchlist_service.db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="Stock with ticker INVALID not found"):
            await watchlist_service.add_stock_to_watchlist(
                user_id=sample_user_id,
                ticker="INVALID"
            )
    
    @pytest.mark.asyncio
    async def test_add_stock_to_watchlist_already_exists(
        self, 
        watchlist_service, 
        sample_user_id, 
        sample_stock,
        sample_watchlist_entry
    ):
        """Test adding stock that's already in watchlist."""
        # Mock stock exists and already in watchlist
        watchlist_service.db.query.return_value.filter.return_value.first.side_effect = [
            sample_stock,  # Stock exists
            sample_watchlist_entry  # Already in watchlist
        ]
        
        with pytest.raises(ValueError, match="Stock 7203 is already in watchlist"):
            await watchlist_service.add_stock_to_watchlist(
                user_id=sample_user_id,
                ticker="7203"
            )
    
    @pytest.mark.asyncio
    async def test_remove_stock_from_watchlist_success(
        self, 
        watchlist_service, 
        sample_user_id, 
        sample_watchlist_entry
    ):
        """Test successful removal of stock from watchlist."""
        # Mock watchlist entry exists
        watchlist_service.db.query.return_value.filter.return_value.first.return_value = sample_watchlist_entry
        
        await watchlist_service.remove_stock_from_watchlist(sample_user_id, "7203")
        
        # Verify database operations
        watchlist_service.db.delete.assert_called_once_with(sample_watchlist_entry)
        watchlist_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_stock_from_watchlist_not_found(
        self, 
        watchlist_service, 
        sample_user_id
    ):
        """Test removing stock that's not in watchlist."""
        # Mock watchlist entry doesn't exist
        watchlist_service.db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="Stock 7203 not found in watchlist"):
            await watchlist_service.remove_stock_from_watchlist(sample_user_id, "7203")
    
    @pytest.mark.asyncio
    async def test_update_watchlist_stock_success(
        self, 
        watchlist_service, 
        sample_user_id, 
        sample_watchlist_entry,
        sample_stock
    ):
        """Test successful update of watchlist stock."""
        # Mock watchlist entry exists
        watchlist_service.db.query.return_value.filter.return_value.first.side_effect = [
            sample_watchlist_entry,  # Watchlist entry exists
            sample_stock  # Stock exists
        ]
        
        # Mock price data
        with patch.object(watchlist_service, '_get_current_price_data') as mock_price:
            mock_price.return_value = {
                'current_price': 2520.0,
                'price_change': 20.0,
                'price_change_percent': 0.8,
                'volume_today': 1000000,
                'last_updated': date.today()
            }
            
            result = await watchlist_service.update_watchlist_stock(
                user_id=sample_user_id,
                ticker="7203",
                notes="Updated notes"
            )
            
            assert result.ticker == "7203"
            assert result.notes == "Updated notes"
            assert sample_watchlist_entry.notes == "Updated notes"
            
            # Verify database operations
            watchlist_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_add_stocks_to_watchlist_mixed_results(
        self, 
        watchlist_service, 
        sample_user_id, 
        sample_stock
    ):
        """Test bulk adding stocks with mixed results."""
        tickers = ["7203", "INVALID", "6758"]
        
        # Mock database responses
        def mock_stock_query(ticker):
            if ticker == "7203":
                return sample_stock
            elif ticker == "6758":
                return Stock(ticker="6758", company_name_jp="ソニー", is_active=True)
            else:
                return None
        
        def mock_watchlist_query(user_id, ticker):
            if ticker == "6758":
                return UserWatchlist(user_id=user_id, ticker=ticker)  # Already exists
            return None
        
        # Setup mock side effects
        watchlist_service.db.query.return_value.filter.return_value.first.side_effect = [
            mock_stock_query("7203"),  # Stock exists
            mock_watchlist_query(sample_user_id, "7203"),  # Not in watchlist
            mock_stock_query("INVALID"),  # Stock doesn't exist
            mock_stock_query("6758"),  # Stock exists
            mock_watchlist_query(sample_user_id, "6758"),  # Already in watchlist
        ]
        
        result = await watchlist_service.bulk_add_stocks_to_watchlist(sample_user_id, tickers)
        
        assert len(result["successful"]) == 1
        assert "7203" in result["successful"]
        assert len(result["failed"]) == 1
        assert result["failed"][0]["ticker"] == "INVALID"
        assert len(result["already_exists"]) == 1
        assert "6758" in result["already_exists"]
    
    @pytest.mark.asyncio
    async def test_get_current_price_data_success(
        self, 
        watchlist_service, 
        sample_price_data
    ):
        """Test successful retrieval of current price data."""
        # Mock price history queries
        watchlist_service.db.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [
            sample_price_data[0],  # Latest price
            sample_price_data[1]   # Previous price
        ]
        
        result = await watchlist_service._get_current_price_data("7203")
        
        assert result["current_price"] == 2520.0
        assert result["price_change"] == 20.0
        assert result["price_change_percent"] == 0.8
        assert result["volume_today"] == 1000000
    
    @pytest.mark.asyncio
    async def test_get_current_price_data_no_data(self, watchlist_service):
        """Test price data retrieval when no data exists."""
        # Mock no price data
        watchlist_service.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        result = await watchlist_service._get_current_price_data("7203")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_current_price_data_exception_handling(self, watchlist_service):
        """Test price data retrieval with database exception."""
        # Mock database exception
        watchlist_service.db.query.side_effect = Exception("Database error")
        
        result = await watchlist_service._get_current_price_data("7203")
        
        assert result == {}