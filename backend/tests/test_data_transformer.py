"""
Unit tests for DataTransformer and TechnicalIndicatorCalculator.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta
import numpy as np

from app.services.data_transformer import TechnicalIndicatorCalculator, DataTransformer


class TestTechnicalIndicatorCalculator:
    """Test technical indicator calculations."""
    
    def test_sma_calculation(self):
        """Test Simple Moving Average calculation."""
        prices = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        sma_5 = TechnicalIndicatorCalculator.calculate_sma(prices, 5)
        
        # Expected SMA values for 5-period:
        # [14, 16, 18, 20, 22, 24] (starting from 5th element)
        expected = [14.0, 16.0, 18.0, 20.0, 22.0, 24.0]
        
        assert len(sma_5) == 6
        assert sma_5 == expected
    
    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        prices = [10, 12, 14]  # Only 3 prices
        sma_5 = TechnicalIndicatorCalculator.calculate_sma(prices, 5)
        
        assert sma_5 == []
    
    def test_price_momentum_calculation(self):
        """Test price momentum calculation."""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
        momentum = TechnicalIndicatorCalculator.calculate_price_momentum(prices, 5)
        
        # Should have 6 values (11 prices - 5 period)
        assert len(momentum) == 6
        
        # First momentum: (110 - 100) / 100 * 100 = 10%
        assert momentum[0] == 10.0
        
        # All values should be positive (upward trend)
        for value in momentum:
            assert value > 0
    
    def test_price_momentum_insufficient_data(self):
        """Test momentum with insufficient data."""
        prices = [100, 102, 104]  # Only 3 prices, need at least 6 for 5-period momentum
        momentum = TechnicalIndicatorCalculator.calculate_price_momentum(prices, 5)
        
        assert momentum == []
    
    def test_volatility_calculation(self):
        """Test volatility calculation."""
        # Create prices with known volatility
        prices = [100, 105, 95, 110, 90, 115, 85, 120, 80, 125] * 3  # 30 prices
        volatility = TechnicalIndicatorCalculator.calculate_volatility(prices, 20)
        
        # Should have 11 values (30 prices - 20 period + 1)
        assert len(volatility) == 11
        
        # All volatility values should be positive
        for value in volatility:
            assert value >= 0
    
    def test_volatility_insufficient_data(self):
        """Test volatility with insufficient data."""
        prices = [100, 102, 104]  # Only 3 prices, need 20 for 20-period volatility
        volatility = TechnicalIndicatorCalculator.calculate_volatility(prices, 20)
        
        assert volatility == []
    
    def test_support_resistance_calculation(self):
        """Test support and resistance calculation."""
        prices = [95, 100, 105, 98, 102, 107, 96, 101, 106, 99, 103, 108, 97, 104, 109]
        support_resistance = TechnicalIndicatorCalculator.calculate_support_resistance(prices, 10)
        
        assert "support" in support_resistance
        assert "resistance" in support_resistance
        
        # Support should be minimum of last 10 prices
        last_10 = prices[-10:]
        expected_support = min(last_10)
        expected_resistance = max(last_10)
        
        assert support_resistance["support"] == expected_support
        assert support_resistance["resistance"] == expected_resistance
    
    def test_support_resistance_insufficient_data(self):
        """Test support/resistance with insufficient data."""
        prices = [100, 102]  # Only 2 prices
        support_resistance = TechnicalIndicatorCalculator.calculate_support_resistance(prices, 10)
        
        assert support_resistance["support"] == 0.0
        assert support_resistance["resistance"] == 0.0
    
    def test_ema_calculation(self):
        """Test Exponential Moving Average calculation."""
        prices = [22, 22.15, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43, 22.24, 22.29]
        ema_5 = TechnicalIndicatorCalculator.calculate_ema(prices, 5)
        
        # EMA should start with first price and have same length as input
        assert len(ema_5) == len(prices)
        assert ema_5[0] == prices[0]  # First value should be first price
        
        # EMA values should be reasonable (between min and max of prices)
        for value in ema_5:
            assert min(prices) <= value <= max(prices)
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Create price data with clear upward trend
        prices = [44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.85, 47.25, 47.92,
                 46.23, 44.18, 46.57, 47.61, 46.5, 46.23, 46.08, 47.03, 47.74, 46.95]
        
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, 14)
        
        # RSI should be between 0 and 100
        assert len(rsi) > 0
        for value in rsi:
            assert 0 <= value <= 100
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        prices = [10, 12, 14]  # Only 3 prices, need at least 15 for 14-period RSI
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, 14)
        
        assert rsi == []
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation."""
        prices = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
        
        bands = TechnicalIndicatorCalculator.calculate_bollinger_bands(prices, 20)
        
        assert "upper" in bands
        assert "middle" in bands
        assert "lower" in bands
        
        # Should have one value (for the 20th price)
        assert len(bands["upper"]) == 1
        assert len(bands["middle"]) == 1
        assert len(bands["lower"]) == 1
        
        # Upper band should be higher than middle, middle higher than lower
        assert bands["upper"][0] > bands["middle"][0]
        assert bands["middle"][0] > bands["lower"][0]
    
    def test_bollinger_bands_insufficient_data(self):
        """Test Bollinger Bands with insufficient data."""
        prices = [20, 21, 22]  # Only 3 prices, need 20 for 20-period bands
        
        bands = TechnicalIndicatorCalculator.calculate_bollinger_bands(prices, 20)
        
        assert bands["upper"] == []
        assert bands["middle"] == []
        assert bands["lower"] == []
    
    def test_macd_calculation(self):
        """Test MACD calculation."""
        # Create enough price data for MACD calculation
        prices = list(range(50, 100))  # 50 prices from 50 to 99
        
        macd = TechnicalIndicatorCalculator.calculate_macd(prices, 12, 26, 9)
        
        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd
        
        # MACD line should exist
        assert len(macd["macd"]) > 0
        
        # Signal line should be shorter than MACD line
        assert len(macd["signal"]) <= len(macd["macd"])
        
        # Histogram should have same length as signal line
        assert len(macd["histogram"]) == len(macd["signal"])
    
    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data."""
        prices = [20, 21, 22]  # Only 3 prices, need at least 26 for MACD
        
        macd = TechnicalIndicatorCalculator.calculate_macd(prices, 12, 26, 9)
        
        assert macd["macd"] == []
        assert macd["signal"] == []
        assert macd["histogram"] == []


class TestDataTransformer:
    """Test DataTransformer functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def data_transformer(self, mock_db):
        """Create DataTransformer instance with mocked dependencies."""
        with patch('app.services.data_transformer.StockService') as mock_stock_service, \
             patch('app.services.data_transformer.NewsService') as mock_news_service:
            
            transformer = DataTransformer(mock_db)
            transformer.stock_service = Mock()
            transformer.news_service = Mock()
            return transformer
    
    def test_format_price_data(self, data_transformer):
        """Test price data formatting."""
        price_data = [
            {"date": "2024-01-01", "close": 1000, "volume": 100000},
            {"date": "2024-01-02", "close": 1050, "volume": 120000},
            {"date": "2024-01-03", "close": 1020, "volume": 90000}
        ]
        
        formatted = data_transformer._format_price_data(price_data)
        
        assert "最近の株価データ" in formatted
        assert "2024-01-01" in formatted
        assert "¥1000" in formatted
        assert "100,000" in formatted
        assert "前日比" in formatted  # Should show price change
    
    def test_format_price_data_empty(self, data_transformer):
        """Test price data formatting with empty data."""
        formatted = data_transformer._format_price_data([])
        
        assert formatted == "価格データなし"
    
    def test_analyze_financial_trends(self, data_transformer):
        """Test financial trends analysis."""
        financial_data = [
            {
                "fiscal_year": 2024,
                "fiscal_period": "Q1",
                "metrics": {"revenue": 1000000, "net_income": 100000}
            },
            {
                "fiscal_year": 2023,
                "fiscal_period": "Q4", 
                "metrics": {"revenue": 900000, "net_income": 80000}
            }
        ]
        
        analysis = data_transformer._analyze_financial_trends(financial_data)
        
        assert "財務トレンド分析" in analysis
        assert "増収" in analysis  # Revenue increased
        assert "増益" in analysis  # Profit increased
    
    def test_analyze_financial_trends_empty(self, data_transformer):
        """Test financial trends analysis with empty data."""
        analysis = data_transformer._analyze_financial_trends([])
        
        assert analysis == "財務データなし"
    
    def test_analyze_sentiment_trends(self, data_transformer):
        """Test sentiment trends analysis."""
        news_data = [
            {"sentiment_label": "positive"},
            {"sentiment_label": "positive"},
            {"sentiment_label": "negative"},
            {"sentiment_label": "neutral"}
        ]
        
        analysis = data_transformer._analyze_sentiment_trends(news_data)
        
        assert "ニュースセンチメント" in analysis
        assert "ポジティブ" in analysis  # Should be overall positive (50% positive vs 25% negative)
        assert "50.0%" in analysis  # Should show percentage
    
    def test_analyze_sentiment_trends_empty(self, data_transformer):
        """Test sentiment trends analysis with empty data."""
        analysis = data_transformer._analyze_sentiment_trends([])
        
        assert analysis == "ニュースデータなし"
    
    def test_format_recent_news(self, data_transformer):
        """Test recent news formatting."""
        news_data = [
            {
                "headline": "株価上昇のニュース",
                "source": "日経新聞",
                "published_at": "2024-01-01T10:00:00",
                "sentiment_label": "positive"
            },
            {
                "headline": "業績悪化の報告",
                "source": "Reuters",
                "published_at": "2024-01-02T15:00:00",
                "sentiment_label": "negative"
            }
        ]
        
        formatted = data_transformer._format_recent_news(news_data)
        
        assert "最近の関連ニュース" in formatted
        assert "株価上昇のニュース" in formatted
        assert "日経新聞" in formatted
        assert "📈" in formatted  # Positive sentiment emoji
        assert "📉" in formatted  # Negative sentiment emoji
    
    def test_format_recent_news_empty(self, data_transformer):
        """Test recent news formatting with empty data."""
        formatted = data_transformer._format_recent_news([])
        
        assert formatted == "最近のニュースなし"
    
    @pytest.mark.asyncio
    async def test_get_company_name_success(self, data_transformer):
        """Test getting company name successfully."""
        mock_stock = Mock()
        mock_stock.company_name_jp = "トヨタ自動車"
        data_transformer.stock_service.get_stock_by_ticker = AsyncMock(return_value=mock_stock)
        
        company_name = await data_transformer._get_company_name("7203")
        
        assert company_name == "トヨタ自動車"
    
    @pytest.mark.asyncio
    async def test_get_company_name_not_found(self, data_transformer):
        """Test getting company name when stock not found."""
        data_transformer.stock_service.get_stock_by_ticker = AsyncMock(return_value=None)
        
        company_name = await data_transformer._get_company_name("INVALID")
        
        assert company_name == "INVALID"  # Should return ticker as fallback
    
    @pytest.mark.asyncio
    async def test_get_company_name_no_service(self):
        """Test getting company name when no stock service available."""
        transformer = DataTransformer(None)  # No database session
        
        company_name = await transformer._get_company_name("7203")
        
        assert company_name == "7203"  # Should return ticker as fallback
    
    def test_analyze_technical_signals(self, data_transformer):
        """Test technical signals analysis."""
        closes = [100, 102, 104, 106, 108]
        sma_20 = [101, 103, 105]
        sma_50 = [100, 102, 104]
        rsi = [45, 50, 55, 60, 65]
        macd = {"macd": [0.5, 1.0, 1.5], "signal": [0.3, 0.8, 1.2]}
        bollinger = {"upper": [110, 112, 114], "middle": [105, 107, 109], "lower": [100, 102, 104]}
        
        signals = data_transformer._analyze_technical_signals(
            closes, sma_20, sma_50, rsi, macd, bollinger
        )
        
        assert "trend" in signals
        assert "rsi" in signals
        assert "macd" in signals
        assert "bollinger" in signals
        
        # Price above both SMAs should indicate uptrend
        assert "上昇" in signals["trend"]
        
        # RSI of 65 should be neutral
        assert signals["rsi"] == "中立"
        
        # MACD above signal should be buy signal
        assert signals["macd"] == "買いシグナル"
    
    def test_generate_technical_summary(self, data_transformer):
        """Test technical summary generation."""
        current_price = 1000.0
        price_change_1d = 2.5
        rsi = [65]
        signals = {
            "trend": "上昇トレンド",
            "rsi": "中立",
            "macd": "買いシグナル"
        }
        
        summary = data_transformer._generate_technical_summary(
            current_price, price_change_1d, rsi, signals
        )
        
        assert "現在価格: ¥1000.00" in summary
        assert "(+2.50%)" in summary
        assert "トレンド: 上昇トレンド" in summary
        assert "RSI状況: 中立" in summary
        assert "MACD: 買いシグナル" in summary
    
    def test_analyze_momentum_trend(self, data_transformer):
        """Test momentum trend analysis."""
        # Strong upward momentum
        momentum_5 = [8.0, 10.0, 12.0]
        momentum_10 = [5.0, 6.0, 7.0]
        
        trend = data_transformer._analyze_momentum_trend(momentum_5, momentum_10)
        assert trend == "強い上昇モメンタム"
        
        # Weak downward momentum
        momentum_5 = [-2.0, -1.0, -0.5]
        momentum_10 = [-1.0, -0.5, -0.2]
        
        trend = data_transformer._analyze_momentum_trend(momentum_5, momentum_10)
        assert trend == "下降モメンタム"
        
        # Neutral momentum
        momentum_5 = [1.0, -1.0, 0.5]
        momentum_10 = [0.5, -0.5, 0.2]
        
        trend = data_transformer._analyze_momentum_trend(momentum_5, momentum_10)
        assert trend == "モメンタム中立"
    
    def test_calculate_growth_rates(self, data_transformer):
        """Test growth rates calculation."""
        financial_data = [
            {
                "fiscal_year": 2024,
                "fiscal_period": "Q1",
                "metrics": {"revenue": 1000000, "net_income": 100000}
            },
            {
                "fiscal_year": 2023,
                "fiscal_period": "Q4",
                "metrics": {"revenue": 900000, "net_income": 80000}
            },
            {
                "fiscal_year": 2023,
                "fiscal_period": "Q3",
                "metrics": {"revenue": 850000, "net_income": 70000}
            }
        ]
        
        growth_metrics = data_transformer._calculate_growth_rates(financial_data)
        
        assert "revenue_growth" in growth_metrics
        assert "profit_growth" in growth_metrics
        
        # Revenue growth: (1000000 - 900000) / 900000 * 100 = 11.11%
        assert abs(growth_metrics["revenue_growth"]["yoy"] - 11.11) < 0.1
        assert growth_metrics["revenue_growth"]["trend"] == "成長"
        
        # Profit growth: (100000 - 80000) / 80000 * 100 = 25%
        assert growth_metrics["profit_growth"]["yoy"] == 25.0
        assert growth_metrics["profit_growth"]["trend"] == "成長"
    
    def test_calculate_growth_rates_insufficient_data(self, data_transformer):
        """Test growth rates calculation with insufficient data."""
        financial_data = [
            {
                "fiscal_year": 2024,
                "fiscal_period": "Q1",
                "metrics": {"revenue": 1000000}
            }
        ]
        
        growth_metrics = data_transformer._calculate_growth_rates(financial_data)
        
        assert "error" in growth_metrics
    
    def test_generate_growth_summary(self, data_transformer):
        """Test growth summary generation."""
        growth_metrics = {
            "revenue_growth": {"yoy": 15.5, "trend": "成長"},
            "profit_growth": {"yoy": 25.0, "trend": "成長"},
            "growth_consistency": "安定成長"
        }
        
        summary = data_transformer._generate_growth_summary(growth_metrics)
        
        assert "成長分析:" in summary
        assert "売上成長率: 15.5% (成長)" in summary
        assert "利益成長率: 25.0% (成長)" in summary
        assert "成長の安定性: 安定成長" in summary
    
    def test_calculate_valuation_metrics(self, data_transformer):
        """Test valuation metrics calculation."""
        daily_metrics = {
            "pe_ratio": 15.5,
            "pb_ratio": 1.2,
            "market_cap": 1000000000,
            "dividend_yield": 2.5
        }
        
        financial_data = [
            {"metrics": {"net_income": 100000}},
            {"metrics": {"net_income": 80000}}
        ]
        
        valuation = data_transformer._calculate_valuation_metrics(daily_metrics, financial_data)
        
        assert "current" in valuation
        assert "historical" in valuation
        
        assert valuation["current"]["pe_ratio"] == 15.5
        assert valuation["current"]["pb_ratio"] == 1.2
        
        # EPS growth: (100000 - 80000) / 80000 * 100 = 25%
        assert valuation["historical"]["eps_growth"] == 25.0
    
    def test_generate_valuation_summary(self, data_transformer):
        """Test valuation summary generation."""
        valuation_metrics = {
            "current": {
                "pe_ratio": 15.5,
                "pb_ratio": 1.2,
                "dividend_yield": 2.5
            },
            "historical": {
                "eps_growth": 25.0
            }
        }
        
        summary = data_transformer._generate_valuation_summary(valuation_metrics)
        
        assert "バリュエーション分析:" in summary
        assert "PER: 15.5倍" in summary
        assert "PBR: 1.2倍" in summary
        assert "配当利回り: 2.50%" in summary
        assert "EPS成長率: 25.0%" in summary
    
    def test_generate_analysis_summary(self, data_transformer):
        """Test overall analysis summary generation."""
        context = {
            "company_name": "テスト株式会社",
            "ticker": "1234",
            "technical_summary": "現在価格: ¥1000.00 (+2.50%)\nトレンド: 上昇トレンド",
            "momentum_analysis": {
                "momentum_summary": "強い上昇モメンタム"
            },
            "growth_analysis": {
                "growth_summary": "成長分析:\n売上成長率: 15.5% (成長)"
            },
            "news_sentiment": "ニュースセンチメント: ポジティブ (ポジティブ: 60.0%, ネガティブ: 20.0%)"
        }
        
        summary = data_transformer._generate_analysis_summary(context, "comprehensive")
        
        assert "テスト株式会社のcomprehensive分析サマリー:" in summary
        assert "【テクニカル分析】" in summary
        assert "【モメンタム分析】" in summary
        assert "【成長分析】" in summary
        assert "【ニュース・センチメント】" in summary
    
    def test_is_market_hours(self, data_transformer):
        """Test market hours detection."""
        # This is a basic test - in practice would need to mock datetime
        result = data_transformer._is_market_hours()
        assert isinstance(result, bool)


class TestDataTransformationIntegration:
    """Integration tests for data transformation."""
    
    @pytest.mark.asyncio
    async def test_prepare_analysis_context_short_term(self):
        """Test preparing analysis context for short-term analysis."""
        # This would be a more comprehensive integration test
        # that tests the full context preparation flow
        pass
    
    @pytest.mark.asyncio
    async def test_prepare_analysis_context_comprehensive(self):
        """Test preparing analysis context for comprehensive analysis."""
        # This would test the full comprehensive analysis context preparation
        pass


if __name__ == "__main__":
    pytest.main([__file__])