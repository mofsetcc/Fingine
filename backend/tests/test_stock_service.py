"""
Unit tests for StockService.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.stock_service import StockService
from app.models.stock import Stock, StockPriceHistory, StockDailyMetrics
from app.schemas.stock import (
    StockSearchQuery, StockSearchResponse, StockSearchResult,
    MarketIndex, HotStock, HotStocksResponse, StockDetail,
    PriceHistoryRequest, PriceHistoryResponse, PriceData
)


class TestStockService:
    """Test cases for StockService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def stock_service(self, mock_db):
        """Create StockService instance with mock database."""
        return StockService(mock_db)
    
    @pytest.fixture
    def sample_stock(self):
        """Create sample stock for testing."""
        return Stock(
            ticker="7203",
            company_name_jp="トヨタ自動車",
            company_name_en="Toyota Motor Corporation",
            sector_jp="輸送用機器",
            industry_jp="自動車",
            description="世界最大級の自動車メーカー",
            listing_date=date(1949, 5, 16),
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_price_history(self):
        """Create sample price history data."""
        today = date.today()
        return [
            StockPriceHistory(
                ticker="7203",
                date=today,
                open=Decimal("2500.00"),
                high=Decimal("2550.00"),
                low=Decimal("2480.00"),
                close=Decimal("2520.00"),
                volume=1500000,
                adjusted_close=Decimal("2520.00")
            ),
            StockPriceHistory(
                ticker="7203",
                date=today - timedelta(days=1),
                open=Decimal("2480.00"),
                high=Decimal("2510.00"),
                low=Decimal("2460.00"),
                close=Decimal("2500.00"),
                volume=1200000,
                adjusted_close=Decimal("2500.00")
            )
        ]
    
    @pytest.fixture
    def sample_daily_metrics(self):
        """Create sample daily metrics data."""
        return StockDailyMetrics(
            ticker="7203",
            date=date.today(),
            market_cap=30000000000000,  # 30 trillion yen
            pe_ratio=Decimal("12.5"),
            pb_ratio=Decimal("1.2"),
            dividend_yield=Decimal("0.025"),
            shares_outstanding=3000000000
        )
    
    @pytest.mark.asyncio
    async def test_search_stocks_exact_ticker_match(self, stock_service, mock_db, sample_stock):
        """Test exact ticker match in stock search."""
        # Setup mock
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Mock the complex query result
        mock_result = Mock()
        mock_result.Stock = sample_stock
        mock_result.match_score = 1.0
        mock_query.all.return_value = [mock_result]
        
        mock_db.query.return_value = mock_query
        mock_db.execute.return_value.fetchall.return_value = []
        
        # Mock scalar for total count
        mock_count_query = Mock()
        mock_count_query.filter.return_value = mock_count_query
        mock_count_query.scalar.return_value = 1
        mock_db.query.return_value = mock_count_query
        
        # Test exact ticker search
        query = StockSearchQuery(query="7203", limit=20, include_inactive=False)
        result = await stock_service.search_stocks(query)
        
        # Assertions
        assert isinstance(result, StockSearchResponse)
        assert result.query == "7203"
        assert result.total == 1
        assert len(result.results) == 1
        assert result.results[0].ticker == "7203"
        assert result.results[0].match_score == 1.0
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_search_stocks_company_name_match(self, stock_service, mock_db, sample_stock):
        """Test company name matching in stock search."""
        # Setup mock similar to above but for company name search
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_result = Mock()
        mock_result.Stock = sample_stock
        mock_result.match_score = 0.8
        mock_query.all.return_value = [mock_result]
        
        mock_db.query.return_value = mock_query
        mock_db.execute.return_value.fetchall.return_value = []
        
        # Mock total count
        mock_count_query = Mock()
        mock_count_query.filter.return_value = mock_count_query
        mock_count_query.scalar.return_value = 1
        mock_db.query.return_value = mock_count_query
        
        # Test company name search
        query = StockSearchQuery(query="トヨタ", limit=20, include_inactive=False)
        result = await stock_service.search_stocks(query)
        
        # Assertions
        assert isinstance(result, StockSearchResponse)
        assert result.query == "トヨタ"
        assert len(result.results) == 1
        assert result.results[0].company_name_jp == "トヨタ自動車"
        assert result.results[0].match_score == 0.8
    
    @pytest.mark.asyncio
    async def test_search_stocks_empty_results(self, stock_service, mock_db):
        """Test search with no matching results."""
        # Setup mock for empty results
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.query.return_value = mock_query
        mock_db.execute.return_value.fetchall.return_value = []
        
        # Mock total count
        mock_count_query = Mock()
        mock_count_query.filter.return_value = mock_count_query
        mock_count_query.scalar.return_value = 0
        mock_db.query.return_value = mock_count_query
        
        # Test search with no results
        query = StockSearchQuery(query="NONEXISTENT", limit=20, include_inactive=False)
        result = await stock_service.search_stocks(query)
        
        # Assertions
        assert isinstance(result, StockSearchResponse)
        assert result.query == "NONEXISTENT"
        assert result.total == 0
        assert len(result.results) == 0
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_get_market_indices(self, stock_service):
        """Test market indices retrieval."""
        result = await stock_service.get_market_indices()
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) >= 2  # At least Nikkei and TOPIX
        
        for index in result:
            assert isinstance(index, MarketIndex)
            assert index.name is not None
            assert index.symbol is not None
            assert index.value is not None
            assert index.change is not None
            assert index.change_percent is not None
            assert index.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_hot_stocks_no_data(self, stock_service, mock_db):
        """Test hot stocks with no price data."""
        # Mock empty price data
        mock_db.query.return_value.scalar.return_value = None
        
        result = await stock_service.get_hot_stocks()
        
        # Assertions
        assert isinstance(result, HotStocksResponse)
        assert len(result.gainers) == 0
        assert len(result.losers) == 0
        assert len(result.most_traded) == 0
        assert result.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_hot_stocks_with_data(self, stock_service, mock_db):
        """Test hot stocks with sample data."""
        # Mock price data query
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        mock_db.query.return_value.scalar.side_effect = [today, yesterday]
        
        # Mock price change data
        mock_price_data = [
            Mock(
                ticker="7203",
                company_name_jp="トヨタ自動車",
                current_price=2520.00,
                change=20.00,
                change_percent=0.8,
                volume=1500000
            ),
            Mock(
                ticker="9984",
                company_name_jp="ソフトバンクグループ",
                current_price=5000.00,
                change=-100.00,
                change_percent=-2.0,
                volume=2000000
            )
        ]
        
        mock_db.execute.return_value.fetchall.return_value = mock_price_data
        
        result = await stock_service.get_hot_stocks()
        
        # Assertions
        assert isinstance(result, HotStocksResponse)
        assert isinstance(result.gainers, list)
        assert isinstance(result.losers, list)
        assert isinstance(result.most_traded, list)
        assert result.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_stock_detail_success(self, stock_service, mock_db, sample_stock, sample_price_history, sample_daily_metrics):
        """Test successful stock detail retrieval."""
        # Mock stock query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stock
        
        # Mock price history query
        mock_price_query = Mock()
        mock_price_query.filter.return_value = mock_price_query
        mock_price_query.order_by.return_value = mock_price_query
        mock_price_query.first.return_value = sample_price_history[0]
        
        # Mock metrics query
        mock_metrics_query = Mock()
        mock_metrics_query.filter.return_value = mock_metrics_query
        mock_metrics_query.order_by.return_value = mock_metrics_query
        mock_metrics_query.first.return_value = sample_daily_metrics
        
        # Mock year prices query
        mock_year_query = Mock()
        mock_year_query.filter.return_value = mock_year_query
        mock_year_result = Mock()
        mock_year_result.high_52w = Decimal("2800.00")
        mock_year_result.low_52w = Decimal("2200.00")
        mock_year_result.avg_volume = 1350000
        mock_year_query.first.return_value = mock_year_result
        
        # Setup query return values
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=sample_stock)))),
            mock_price_query,
            mock_metrics_query,
            mock_year_query
        ]
        
        result = await stock_service.get_stock_detail("7203")
        
        # Assertions
        assert isinstance(result, StockDetail)
        assert result.ticker == "7203"
        assert result.company_name_jp == "トヨタ自動車"
        assert result.current_price == Decimal("2520.00")
        assert result.market_cap == 30000000000000
        assert result.pe_ratio == Decimal("12.5")
    
    @pytest.mark.asyncio
    async def test_get_stock_detail_not_found(self, stock_service, mock_db):
        """Test stock detail retrieval for non-existent stock."""
        # Mock empty result
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test should raise HTTPException
        with pytest.raises(Exception):  # HTTPException
            await stock_service.get_stock_detail("9999")
    
    @pytest.mark.asyncio
    async def test_get_price_history_success(self, stock_service, mock_db, sample_stock, sample_price_history):
        """Test successful price history retrieval."""
        # Mock stock existence check
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stock
        
        # Mock price history query
        mock_price_query = Mock()
        mock_price_query.filter.return_value = mock_price_query
        mock_price_query.order_by.return_value = mock_price_query
        mock_price_query.all.return_value = sample_price_history
        
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=sample_stock)))),
            mock_price_query
        ]
        
        request = PriceHistoryRequest(
            ticker="7203",
            period="1m",
            interval="1d"
        )
        
        result = await stock_service.get_price_history(request)
        
        # Assertions
        assert isinstance(result, PriceHistoryResponse)
        assert result.ticker == "7203"
        assert result.period == "1m"
        assert result.interval == "1d"
        assert len(result.data) == 2
        assert result.total_points == 2
        
        # Check price data
        for price_data in result.data:
            assert isinstance(price_data, PriceData)
            assert price_data.ticker == "7203"
            assert price_data.open > 0
            assert price_data.high > 0
            assert price_data.low > 0
            assert price_data.close > 0
            assert price_data.volume > 0
    
    @pytest.mark.asyncio
    async def test_get_price_history_stock_not_found(self, stock_service, mock_db):
        """Test price history retrieval for non-existent stock."""
        # Mock empty result
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        request = PriceHistoryRequest(
            ticker="9999",
            period="1m",
            interval="1d"
        )
        
        # Test should raise HTTPException
        with pytest.raises(Exception):  # HTTPException
            await stock_service.get_price_history(request)
    
    @pytest.mark.asyncio
    async def test_get_price_history_custom_dates(self, stock_service, mock_db, sample_stock, sample_price_history):
        """Test price history with custom date range."""
        # Mock stock existence check
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stock
        
        # Mock price history query
        mock_price_query = Mock()
        mock_price_query.filter.return_value = mock_price_query
        mock_price_query.order_by.return_value = mock_price_query
        mock_price_query.all.return_value = sample_price_history
        
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=sample_stock)))),
            mock_price_query
        ]
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        request = PriceHistoryRequest(
            ticker="7203",
            period="1m",
            interval="1d",
            start_date=start_date,
            end_date=end_date
        )
        
        result = await stock_service.get_price_history(request)
        
        # Assertions
        assert isinstance(result, PriceHistoryResponse)
        assert result.ticker == "7203"
        assert len(result.data) == 2
    
    def test_get_latest_prices(self, stock_service, mock_db):
        """Test latest prices retrieval helper method."""
        # Mock price query result
        mock_price_data = [
            Mock(
                ticker="7203",
                current_price=2520.00,
                volume=1500000,
                change_percent=0.8
            ),
            Mock(
                ticker="9984",
                current_price=5000.00,
                volume=2000000,
                change_percent=-2.0
            )
        ]
        
        mock_db.execute.return_value.fetchall.return_value = mock_price_data
        
        tickers = ["7203", "9984"]
        result = stock_service._get_latest_prices(tickers)
        
        # Assertions
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "7203" in result
        assert "9984" in result
        
        # Check data structure
        for ticker, price_info in result.items():
            assert "current_price" in price_info
            assert "volume" in price_info
            assert "change_percent" in price_info
    
    def test_get_latest_prices_empty_tickers(self, stock_service):
        """Test latest prices with empty ticker list."""
        result = stock_service._get_latest_prices([])
        
        # Should return empty dict
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_search_performance_timing(self, stock_service, mock_db):
        """Test that search includes execution timing."""
        # Setup minimal mock
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.query.return_value = mock_query
        mock_db.execute.return_value.fetchall.return_value = []
        
        # Mock total count
        mock_count_query = Mock()
        mock_count_query.filter.return_value = mock_count_query
        mock_count_query.scalar.return_value = 0
        mock_db.query.return_value = mock_count_query
        
        query = StockSearchQuery(query="test", limit=20, include_inactive=False)
        result = await stock_service.search_stocks(query)
        
        # Should include execution time
        assert result.execution_time_ms >= 0
        assert isinstance(result.execution_time_ms, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])