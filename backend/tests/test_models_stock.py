"""
Comprehensive unit tests for stock models.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.models.stock import Stock, StockDailyMetrics, StockPriceHistory


class TestStockModel:
    """Test cases for Stock model."""
    
    def test_stock_creation_with_required_fields(self):
        """Test creating a stock with only required fields."""
        stock = Stock(
            ticker="7203",
            company_name_jp="トヨタ自動車株式会社"
        )
        
        assert stock.ticker == "7203"
        assert stock.company_name_jp == "トヨタ自動車株式会社"
        assert stock.company_name_en is None
        assert stock.sector_jp is None
        assert stock.industry_jp is None
        assert stock.description is None
        assert stock.logo_url is None
        assert stock.listing_date is None
        # Default values are set by database, not at model creation
        assert hasattr(stock, 'is_active')
        assert hasattr(stock, 'created_at')
        assert hasattr(stock, 'updated_at')
    
    def test_stock_creation_with_all_fields(self):
        """Test creating a stock with all fields."""
        listing_date = date(1949, 5, 16)
        stock = Stock(
            ticker="7203",
            company_name_jp="トヨタ自動車株式会社",
            company_name_en="Toyota Motor Corporation",
            sector_jp="輸送用機器",
            industry_jp="自動車",
            description="世界最大級の自動車メーカー",
            logo_url="https://example.com/toyota_logo.png",
            listing_date=listing_date,
            is_active=True
        )
        
        assert stock.ticker == "7203"
        assert stock.company_name_jp == "トヨタ自動車株式会社"
        assert stock.company_name_en == "Toyota Motor Corporation"
        assert stock.sector_jp == "輸送用機器"
        assert stock.industry_jp == "自動車"
        assert stock.description == "世界最大級の自動車メーカー"
        assert stock.logo_url == "https://example.com/toyota_logo.png"
        assert stock.listing_date == listing_date
        assert stock.is_active is True
    
    def test_stock_ticker_primary_key(self):
        """Test that ticker is the primary key."""
        primary_keys = [col.name for col in Stock.__table__.primary_key.columns]
        assert "ticker" in primary_keys
        assert len(primary_keys) == 1
    
    def test_stock_field_constraints(self):
        """Test stock field constraints."""
        ticker_col = Stock.__table__.columns['ticker']
        company_name_jp_col = Stock.__table__.columns['company_name_jp']
        is_active_col = Stock.__table__.columns['is_active']
        
        assert ticker_col.type.length == 10
        assert ticker_col.primary_key is True
        assert company_name_jp_col.type.length == 255
        assert company_name_jp_col.nullable is False
        assert is_active_col.default.arg is True
    
    def test_stock_relationships_defined(self):
        """Test that stock relationships are properly defined."""
        stock = Stock(ticker="7203", company_name_jp="トヨタ自動車")
        
        # Check that relationship attributes exist
        assert hasattr(stock, 'daily_metrics')
        assert hasattr(stock, 'price_history')
        assert hasattr(stock, 'financial_reports')
        assert hasattr(stock, 'news_links')
        assert hasattr(stock, 'ai_analyses')
        assert hasattr(stock, 'watchlist_entries')
    
    def test_stock_inactive_flag(self):
        """Test setting stock as inactive."""
        stock = Stock(
            ticker="DELISTED",
            company_name_jp="上場廃止会社",
            is_active=False
        )
        
        assert stock.is_active is False


class TestStockDailyMetricsModel:
    """Test cases for StockDailyMetrics model."""
    
    def test_daily_metrics_creation_with_required_fields(self):
        """Test creating daily metrics with only required fields."""
        metrics_date = date(2024, 1, 15)
        metrics = StockDailyMetrics(
            ticker="7203",
            date=metrics_date
        )
        
        assert metrics.ticker == "7203"
        assert metrics.date == metrics_date
        assert metrics.market_cap is None
        assert metrics.pe_ratio is None
        assert metrics.pb_ratio is None
        assert metrics.dividend_yield is None
        assert metrics.shares_outstanding is None
    
    def test_daily_metrics_creation_with_all_fields(self):
        """Test creating daily metrics with all fields."""
        metrics_date = date(2024, 1, 15)
        metrics = StockDailyMetrics(
            ticker="7203",
            date=metrics_date,
            market_cap=35000000000000,  # 35 trillion yen
            pe_ratio=Decimal("12.5"),
            pb_ratio=Decimal("1.2"),
            dividend_yield=Decimal("0.0275"),  # 2.75%
            shares_outstanding=14700000000  # 14.7 billion shares
        )
        
        assert metrics.ticker == "7203"
        assert metrics.date == metrics_date
        assert metrics.market_cap == 35000000000000
        assert metrics.pe_ratio == Decimal("12.5")
        assert metrics.pb_ratio == Decimal("1.2")
        assert metrics.dividend_yield == Decimal("0.0275")
        assert metrics.shares_outstanding == 14700000000
    
    def test_daily_metrics_composite_primary_key(self):
        """Test that daily metrics uses composite primary key."""
        primary_keys = [col.name for col in StockDailyMetrics.__table__.primary_key.columns]
        assert "ticker" in primary_keys
        assert "date" in primary_keys
        assert len(primary_keys) == 2
    
    def test_daily_metrics_decimal_precision(self):
        """Test decimal field precision for financial ratios."""
        pe_ratio_col = StockDailyMetrics.__table__.columns['pe_ratio']
        pb_ratio_col = StockDailyMetrics.__table__.columns['pb_ratio']
        dividend_yield_col = StockDailyMetrics.__table__.columns['dividend_yield']
        
        # Check precision and scale for NUMERIC fields
        assert pe_ratio_col.type.precision == 10
        assert pe_ratio_col.type.scale == 2
        assert pb_ratio_col.type.precision == 10
        assert pb_ratio_col.type.scale == 2
        assert dividend_yield_col.type.precision == 5
        assert dividend_yield_col.type.scale == 4
    
    def test_daily_metrics_foreign_key_relationship(self):
        """Test foreign key relationship to stock."""
        metrics = StockDailyMetrics(ticker="7203", date=date(2024, 1, 15))
        assert hasattr(metrics, 'stock')


class TestStockPriceHistoryModel:
    """Test cases for StockPriceHistory model."""
    
    def test_price_history_creation_with_required_fields(self):
        """Test creating price history with required fields."""
        price_date = date(2024, 1, 15)
        price_history = StockPriceHistory(
            ticker="7203",
            date=price_date,
            open=Decimal("2500.0"),
            high=Decimal("2550.0"),
            low=Decimal("2480.0"),
            close=Decimal("2520.0"),
            volume=15000000
        )
        
        assert price_history.ticker == "7203"
        assert price_history.date == price_date
        assert price_history.open == Decimal("2500.0")
        assert price_history.high == Decimal("2550.0")
        assert price_history.low == Decimal("2480.0")
        assert price_history.close == Decimal("2520.0")
        assert price_history.volume == 15000000
        assert price_history.adjusted_close is None
    
    def test_price_history_creation_with_adjusted_close(self):
        """Test creating price history with adjusted close."""
        price_date = date(2024, 1, 15)
        price_history = StockPriceHistory(
            ticker="7203",
            date=price_date,
            open=Decimal("2500.0"),
            high=Decimal("2550.0"),
            low=Decimal("2480.0"),
            close=Decimal("2520.0"),
            volume=15000000,
            adjusted_close=Decimal("2515.0")
        )
        
        assert price_history.adjusted_close == Decimal("2515.0")
    
    def test_price_history_composite_primary_key(self):
        """Test that price history uses composite primary key."""
        primary_keys = [col.name for col in StockPriceHistory.__table__.primary_key.columns]
        assert "ticker" in primary_keys
        assert "date" in primary_keys
        assert len(primary_keys) == 2
    
    def test_price_history_decimal_precision(self):
        """Test decimal field precision for price data."""
        open_col = StockPriceHistory.__table__.columns['open']
        high_col = StockPriceHistory.__table__.columns['high']
        low_col = StockPriceHistory.__table__.columns['low']
        close_col = StockPriceHistory.__table__.columns['close']
        adjusted_close_col = StockPriceHistory.__table__.columns['adjusted_close']
        
        # Check precision and scale for NUMERIC fields (14,4)
        for col in [open_col, high_col, low_col, close_col, adjusted_close_col]:
            assert col.type.precision == 14
            assert col.type.scale == 4
    
    def test_price_history_field_constraints(self):
        """Test price history field constraints."""
        open_col = StockPriceHistory.__table__.columns['open']
        volume_col = StockPriceHistory.__table__.columns['volume']
        adjusted_close_col = StockPriceHistory.__table__.columns['adjusted_close']
        
        assert open_col.nullable is False
        assert volume_col.nullable is False
        assert adjusted_close_col.nullable is True
    
    def test_price_history_ohlcv_validation(self):
        """Test OHLCV data logical validation."""
        price_date = date(2024, 1, 15)
        
        # Valid OHLCV data
        valid_price = StockPriceHistory(
            ticker="7203",
            date=price_date,
            open=Decimal("2500.0"),
            high=Decimal("2550.0"),  # High >= Open, Close
            low=Decimal("2480.0"),   # Low <= Open, Close
            close=Decimal("2520.0"),
            volume=15000000
        )
        
        assert valid_price.high >= valid_price.open
        assert valid_price.high >= valid_price.close
        assert valid_price.low <= valid_price.open
        assert valid_price.low <= valid_price.close
        assert valid_price.volume > 0
    
    def test_price_history_foreign_key_relationship(self):
        """Test foreign key relationship to stock."""
        price_history = StockPriceHistory(
            ticker="7203",
            date=date(2024, 1, 15),
            open=Decimal("2500.0"),
            high=Decimal("2550.0"),
            low=Decimal("2480.0"),
            close=Decimal("2520.0"),
            volume=15000000
        )
        assert hasattr(price_history, 'stock')


class TestStockModelIntegration:
    """Integration tests for stock models working together."""
    
    def test_stock_with_daily_metrics(self):
        """Test stock with associated daily metrics."""
        stock = Stock(ticker="7203", company_name_jp="トヨタ自動車")
        metrics = StockDailyMetrics(
            ticker="7203",
            date=date(2024, 1, 15),
            market_cap=35000000000000,
            pe_ratio=Decimal("12.5")
        )
        
        assert metrics.ticker == stock.ticker
    
    def test_stock_with_price_history(self):
        """Test stock with associated price history."""
        stock = Stock(ticker="7203", company_name_jp="トヨタ自動車")
        price = StockPriceHistory(
            ticker="7203",
            date=date(2024, 1, 15),
            open=Decimal("2500.0"),
            high=Decimal("2550.0"),
            low=Decimal("2480.0"),
            close=Decimal("2520.0"),
            volume=15000000
        )
        
        assert price.ticker == stock.ticker
    
    def test_stock_model_table_names(self):
        """Test that all stock models have correct table names."""
        assert Stock.__tablename__ == "stocks"
        assert StockDailyMetrics.__tablename__ == "stock_daily_metrics"
        assert StockPriceHistory.__tablename__ == "stock_price_history"


@pytest.fixture
def sample_stock():
    """Fixture providing a sample stock for testing."""
    return Stock(
        ticker="7203",
        company_name_jp="トヨタ自動車株式会社",
        company_name_en="Toyota Motor Corporation",
        sector_jp="輸送用機器",
        industry_jp="自動車",
        is_active=True
    )


@pytest.fixture
def sample_daily_metrics():
    """Fixture providing sample daily metrics for testing."""
    return StockDailyMetrics(
        ticker="7203",
        date=date(2024, 1, 15),
        market_cap=35000000000000,
        pe_ratio=Decimal("12.5"),
        pb_ratio=Decimal("1.2"),
        dividend_yield=Decimal("0.0275"),
        shares_outstanding=14700000000
    )


@pytest.fixture
def sample_price_history():
    """Fixture providing sample price history for testing."""
    return StockPriceHistory(
        ticker="7203",
        date=date(2024, 1, 15),
        open=Decimal("2500.0"),
        high=Decimal("2550.0"),
        low=Decimal("2480.0"),
        close=Decimal("2520.0"),
        volume=15000000,
        adjusted_close=Decimal("2515.0")
    )


class TestStockModelFixtures:
    """Test the fixtures work correctly."""
    
    def test_sample_stock_fixture(self, sample_stock):
        """Test sample stock fixture."""
        assert sample_stock.ticker == "7203"
        assert sample_stock.company_name_jp == "トヨタ自動車株式会社"
        assert sample_stock.company_name_en == "Toyota Motor Corporation"
        assert sample_stock.is_active is True
    
    def test_sample_daily_metrics_fixture(self, sample_daily_metrics):
        """Test sample daily metrics fixture."""
        assert sample_daily_metrics.ticker == "7203"
        assert sample_daily_metrics.market_cap == 35000000000000
        assert sample_daily_metrics.pe_ratio == Decimal("12.5")
    
    def test_sample_price_history_fixture(self, sample_price_history):
        """Test sample price history fixture."""
        assert sample_price_history.ticker == "7203"
        assert sample_price_history.open == Decimal("2500.0")
        assert sample_price_history.volume == 15000000