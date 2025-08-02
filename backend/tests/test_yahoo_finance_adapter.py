"""Tests for Yahoo Finance Japan adapter."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
import json

from app.adapters.yahoo_finance_adapter import YahooFinanceJapanAdapter
from app.adapters.base import (
    HealthStatus,
    RateLimitExceededError,
    DataSourceUnavailableError,
    InvalidDataError
)


class TestYahooFinanceJapanAdapter:
    """Test cases for YahooFinanceJapanAdapter."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            "timeout": 30,
            "max_retries": 2,
            "retry_delay": 0.1,  # Short delay for tests
            "delay_minutes": 15,
            "requests_per_minute": 30,
            "requests_per_hour": 1000
        }
    
    @pytest.fixture
    def adapter(self, config):
        """Create Yahoo Finance adapter instance."""
        return YahooFinanceJapanAdapter(config=config)
    
    @pytest.fixture
    def mock_chart_response(self):
        """Mock Yahoo Finance chart response."""
        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "JPY",
                            "symbol": "7203.T",
                            "regularMarketPrice": 2500.0,
                            "previousClose": 2480.0,
                            "regularMarketOpen": 2490.0,
                            "regularMarketDayHigh": 2520.0,
                            "regularMarketDayLow": 2470.0,
                            "regularMarketVolume": 15000000,
                            "regularMarketTime": 1642204800,  # 2022-01-15 00:00:00
                            "marketState": "REGULAR"
                        },
                        "timestamp": [1642204800],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [2490.0],
                                    "high": [2520.0],
                                    "low": [2470.0],
                                    "close": [2500.0],
                                    "volume": [15000000]
                                }
                            ]
                        }
                    }
                ],
                "error": None
            }
        }
    
    @pytest.fixture
    def mock_historical_response(self):
        """Mock Yahoo Finance historical data response."""
        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "JPY",
                            "symbol": "7203.T"
                        },
                        "timestamp": [1642204800, 1642118400, 1642032000],  # 3 days
                        "indicators": {
                            "quote": [
                                {
                                    "open": [2490.0, 2470.0, 2450.0],
                                    "high": [2520.0, 2500.0, 2480.0],
                                    "low": [2470.0, 2450.0, 2430.0],
                                    "close": [2500.0, 2480.0, 2460.0],
                                    "volume": [15000000, 14000000, 13000000]
                                }
                            ],
                            "adjclose": [
                                {
                                    "adjclose": [2500.0, 2480.0, 2460.0]
                                }
                            ]
                        }
                    }
                ],
                "error": None
            }
        }
    
    @pytest.fixture
    def mock_search_response(self):
        """Mock Yahoo Finance search response."""
        return {
            "quotes": [
                {
                    "symbol": "7203.T",
                    "shortname": "Toyota Motor Corp",
                    "longname": "Toyota Motor Corporation",
                    "quoteType": "EQUITY",
                    "exchange": "JPX",
                    "market": "jp_market",
                    "currency": "JPY",
                    "score": 1.0
                },
                {
                    "symbol": "TM",
                    "shortname": "Toyota Motor Corp ADR",
                    "longname": "Toyota Motor Corporation ADR",
                    "quoteType": "EQUITY",
                    "exchange": "NYQ",
                    "market": "us_market",
                    "currency": "USD",
                    "score": 0.8
                }
            ]
        }
    
    def test_init_with_config(self, config):
        """Test initialization with configuration."""
        adapter = YahooFinanceJapanAdapter(config=config)
        
        assert adapter.timeout == 30
        assert adapter.max_retries == 2
        assert adapter.retry_delay == 0.1
        assert adapter.delay_minutes == 15
        assert adapter.requests_per_minute == 30
        assert adapter.requests_per_hour == 1000
    
    def test_init_default_config(self):
        """Test initialization with default configuration."""
        adapter = YahooFinanceJapanAdapter()
        
        assert adapter.timeout == 30
        assert adapter.max_retries == 3
        assert adapter.retry_delay == 1
        assert adapter.delay_minutes == 15
        assert adapter.requests_per_minute == 30
        assert adapter.requests_per_hour == 1000
        assert adapter.priority == 20  # Lower priority than Alpha Vantage
    
    def test_normalize_symbol(self, adapter):
        """Test symbol normalization."""
        # Japanese stocks
        assert adapter._normalize_symbol("7203.T") == "7203.T"
        assert adapter._normalize_symbol("7203.TYO") == "7203.T"
        assert adapter._normalize_symbol("7203") == "7203.T"
        
        # US stocks
        assert adapter._normalize_symbol("AAPL") == "AAPL"
        assert adapter._normalize_symbol("aapl") == "AAPL"
    
    def test_parse_chart_data(self, adapter, mock_chart_response):
        """Test parsing chart data from API response."""
        result = adapter._parse_chart_data(mock_chart_response, "7203.T")
        
        assert result["symbol"] == "7203.T"
        assert result["price"] == 2500.0
        assert result["open"] == 2490.0
        assert result["high"] == 2520.0
        assert result["low"] == 2470.0
        assert result["volume"] == 15000000
        assert result["previous_close"] == 2480.0
        assert result["change"] == 20.0  # 2500 - 2480
        assert result["change_percent"] == pytest.approx(0.806, rel=1e-2)  # (20/2480)*100
        assert result["currency"] == "JPY"
        assert result["market_status"] == "open"
        assert result["data_delay_minutes"] == 15
        assert "timestamp" in result
        assert "trading_day" in result
    
    def test_parse_chart_data_us_stock(self, adapter):
        """Test parsing chart data for US stock."""
        us_response = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "symbol": "AAPL",
                            "regularMarketPrice": 150.0,
                            "previousClose": 148.0,
                            "regularMarketVolume": 50000000,
                            "marketState": "CLOSED"
                        }
                    }
                ]
            }
        }
        
        result = adapter._parse_chart_data(us_response, "AAPL")
        
        assert result["symbol"] == "AAPL"
        assert result["currency"] == "USD"
        assert result["market_status"] == "closed"
    
    def test_parse_chart_data_invalid(self, adapter):
        """Test parsing invalid chart data."""
        invalid_response = {"chart": {"result": []}}
        
        with pytest.raises(InvalidDataError, match="No chart data found"):
            adapter._parse_chart_data(invalid_response, "7203.T")
    
    def test_parse_historical_data(self, adapter, mock_historical_response):
        """Test parsing historical data."""
        result = adapter._parse_historical_data(mock_historical_response, "7203.T")
        
        assert len(result) == 3
        
        # Check first record (should be sorted by date, newest first)
        first_record = result[0]
        assert first_record["symbol"] == "7203.T"
        assert first_record["open"] == 2490.0
        assert first_record["high"] == 2520.0
        assert first_record["low"] == 2470.0
        assert first_record["close"] == 2500.0
        assert first_record["volume"] == 15000000
        assert first_record["adjusted_close"] == 2500.0
        assert "date" in first_record
    
    def test_parse_historical_data_no_adjclose(self, adapter):
        """Test parsing historical data without adjusted close."""
        response_no_adjclose = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1642204800],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [2490.0],
                                    "high": [2520.0],
                                    "low": [2470.0],
                                    "close": [2500.0],
                                    "volume": [15000000]
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        result = adapter._parse_historical_data(response_no_adjclose, "7203.T")
        
        assert len(result) == 1
        assert result[0]["adjusted_close"] == 2500.0  # Should use close price
    
    def test_parse_historical_data_invalid(self, adapter):
        """Test parsing invalid historical data."""
        invalid_response = {"chart": {"result": []}}
        
        with pytest.raises(InvalidDataError, match="No chart data found"):
            adapter._parse_historical_data(invalid_response, "7203.T")
    
    def test_update_request_counts(self, adapter):
        """Test request count tracking."""
        initial_minute = adapter._request_count_minute
        initial_hour = adapter._request_count_hour
        initial_total = adapter._total_requests
        
        adapter._update_request_counts()
        
        assert adapter._request_count_minute == initial_minute + 1
        assert adapter._request_count_hour == initial_hour + 1
        assert adapter._total_requests == initial_total + 1
    
    def test_check_rate_limits_minute_exceeded(self, adapter):
        """Test rate limit check when minute limit exceeded."""
        adapter._request_count_minute = adapter.requests_per_minute
        
        with pytest.raises(RateLimitExceededError, match="minute rate limit exceeded"):
            adapter._check_rate_limits()
    
    def test_check_rate_limits_hour_exceeded(self, adapter):
        """Test rate limit check when hour limit exceeded."""
        adapter._request_count_hour = adapter.requests_per_hour
        
        with pytest.raises(RateLimitExceededError, match="hour rate limit exceeded"):
            adapter._check_rate_limits()
    
    @pytest.mark.asyncio
    async def test_get_session(self, adapter):
        """Test HTTP session creation."""
        session = await adapter._get_session()
        
        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed
        
        # Check headers
        headers = session._default_headers
        assert "User-Agent" in headers
        assert "Accept" in headers
        
        # Should reuse existing session
        session2 = await adapter._get_session()
        assert session is session2
        
        await adapter._close_session()
    
    @pytest.mark.asyncio
    async def test_close_session(self, adapter):
        """Test HTTP session closing."""
        session = await adapter._get_session()
        assert not session.closed
        
        await adapter._close_session()
        assert session.closed
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, adapter, mock_chart_response):
        """Test successful API request."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_chart_response)
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            url = "https://test.com"
            result = await adapter._make_request(url)
            
            assert result == mock_chart_response
            assert adapter._request_count_minute == 1
            assert adapter._request_count_hour == 1
    
    @pytest.mark.asyncio
    async def test_make_request_429_status(self, adapter):
        """Test API request with 429 status code."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 429
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            url = "https://test.com"
            
            with pytest.raises(RateLimitExceededError):
                await adapter._make_request(url)
    
    @pytest.mark.asyncio
    async def test_make_request_404_status(self, adapter):
        """Test API request with 404 status code."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 404
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            url = "https://test.com"
            
            with pytest.raises(InvalidDataError, match="Symbol not found"):
                await adapter._make_request(url)
    
    @pytest.mark.asyncio
    async def test_make_request_server_error_with_retry(self, adapter):
        """Test API request with server error and retry."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            
            # First call returns 500, second call succeeds
            mock_response_error = AsyncMock()
            mock_response_error.status = 500
            
            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.json = AsyncMock(return_value={"success": True})
            
            mock_session.get.return_value.__aenter__.side_effect = [
                mock_response_error,
                mock_response_success
            ]
            mock_get_session.return_value = mock_session
            
            url = "https://test.com"
            result = await adapter._make_request(url)
            
            assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_make_request_connection_error(self, adapter):
        """Test API request with connection error."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get.side_effect = aiohttp.ClientError("Connection failed")
            mock_get_session.return_value = mock_session
            
            url = "https://test.com"
            
            with pytest.raises(DataSourceUnavailableError, match="connection error"):
                await adapter._make_request(url)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_chart_response):
        """Test health check when API is healthy."""
        with patch.object(adapter, '_make_request', return_value=mock_chart_response):
            health = await adapter.health_check()
            
            assert health.status == HealthStatus.HEALTHY
            assert health.response_time_ms > 0
            assert health.error_message is None
            assert "requests_this_hour" in health.metadata
            assert health.metadata["data_delay_minutes"] == 15
    
    @pytest.mark.asyncio
    async def test_health_check_rate_limited(self, adapter):
        """Test health check when rate limited."""
        with patch.object(adapter, '_make_request', side_effect=RateLimitExceededError("Rate limited")):
            health = await adapter.health_check()
            
            assert health.status == HealthStatus.DEGRADED
            assert health.error_message == "Rate limited"
            assert health.metadata.get("rate_limited") is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, adapter):
        """Test health check when API is unhealthy."""
        with patch.object(adapter, '_make_request', side_effect=DataSourceUnavailableError("API down")):
            health = await adapter.health_check()
            
            assert health.status == HealthStatus.UNHEALTHY
            assert health.error_message == "API down"
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, adapter):
        """Test getting rate limit information."""
        adapter._request_count_minute = 5
        adapter._request_count_hour = 100
        
        rate_limit = await adapter.get_rate_limit_info()
        
        assert rate_limit.requests_per_minute == 30
        assert rate_limit.requests_per_hour == 1000
        assert rate_limit.current_usage["minute"] == 5
        assert rate_limit.current_usage["hour"] == 100
        assert "minute" in rate_limit.reset_times
        assert "hour" in rate_limit.reset_times
    
    @pytest.mark.asyncio
    async def test_get_cost_info(self, adapter):
        """Test getting cost information."""
        cost_info = await adapter.get_cost_info()
        
        assert cost_info.cost_per_request == 0.0  # Free service
        assert cost_info.currency == "USD"
        assert cost_info.monthly_budget == 0.0
        assert cost_info.current_monthly_usage == 0.0
    
    @pytest.mark.asyncio
    async def test_get_current_price(self, adapter, mock_chart_response):
        """Test getting current stock price."""
        with patch.object(adapter, '_make_request', return_value=mock_chart_response):
            result = await adapter.get_current_price("7203.T")
            
            assert result["symbol"] == "7203.T"
            assert result["price"] == 2500.0
            assert result["currency"] == "JPY"
            assert result["data_delay_minutes"] == 15
    
    @pytest.mark.asyncio
    async def test_get_current_price_us_stock(self, adapter):
        """Test getting current price for US stock."""
        us_response = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "symbol": "AAPL",
                            "regularMarketPrice": 150.0,
                            "previousClose": 148.0
                        }
                    }
                ]
            }
        }
        
        with patch.object(adapter, '_make_request', return_value=us_response):
            result = await adapter.get_current_price("AAPL")
            
            assert result["symbol"] == "AAPL"
            assert result["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_get_historical_prices(self, adapter, mock_historical_response):
        """Test getting historical prices."""
        start_date = datetime(2022, 1, 13)
        end_date = datetime(2022, 1, 15)
        
        with patch.object(adapter, '_make_request', return_value=mock_historical_response):
            result = await adapter.get_historical_prices("7203.T", start_date, end_date)
            
            assert len(result) == 3
            assert all(record["symbol"] == "7203.T" for record in result)
            
            # Check date filtering (all dates should be within range)
            for record in result:
                record_date = datetime.fromisoformat(record["date"].replace("Z", "+00:00"))
                assert start_date <= record_date <= end_date
    
    @pytest.mark.asyncio
    async def test_get_historical_prices_unsupported_interval(self, adapter):
        """Test getting historical prices with unsupported interval."""
        start_date = datetime(2022, 1, 13)
        end_date = datetime(2022, 1, 15)
        
        with pytest.raises(InvalidDataError, match="Unsupported interval"):
            await adapter.get_historical_prices("7203.T", start_date, end_date, "5m")
    
    @pytest.mark.asyncio
    async def test_search_symbols(self, adapter, mock_search_response):
        """Test searching for symbols."""
        with patch.object(adapter, '_make_request', return_value=mock_search_response):
            result = await adapter.search_symbols("Toyota")
            
            assert len(result) == 2
            
            # Should be sorted by score (descending)
            assert result[0]["score"] == 1.0
            assert result[1]["score"] == 0.8
            
            # Check first result
            first_result = result[0]
            assert first_result["symbol"] == "7203.T"
            assert first_result["name"] == "Toyota Motor Corporation"
            assert first_result["exchange"] == "JPX"
            assert first_result["currency"] == "JPY"
    
    @pytest.mark.asyncio
    async def test_search_symbols_no_results(self, adapter):
        """Test searching for symbols with no results."""
        empty_response = {"quotes": []}
        
        with patch.object(adapter, '_make_request', return_value=empty_response):
            result = await adapter.search_symbols("NonexistentCompany")
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_search_symbols_no_quotes_key(self, adapter):
        """Test searching for symbols when response has no quotes key."""
        invalid_response = {"someOtherKey": "value"}
        
        with patch.object(adapter, '_make_request', return_value=invalid_response):
            result = await adapter.search_symbols("Toyota")
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test using adapter as async context manager."""
        async with YahooFinanceJapanAdapter(config=config) as adapter:
            assert isinstance(adapter, YahooFinanceJapanAdapter)
            
            # Session should be created when needed
            session = await adapter._get_session()
            assert not session.closed
        
        # Session should be closed after context exit
        assert session.closed
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset_after_time(self, adapter):
        """Test that rate limits reset after time passes."""
        # Set request counts to maximum
        adapter._request_count_minute = adapter.requests_per_minute
        adapter._request_count_hour = adapter.requests_per_hour
        
        # Should be rate limited
        with pytest.raises(RateLimitExceededError):
            adapter._check_rate_limits()
        
        # Simulate time passing for minute reset
        adapter._last_minute_reset = datetime.utcnow() - timedelta(minutes=2)
        adapter._update_request_counts()
        
        # Minute limit should be reset, but hour limit still exceeded
        assert adapter._request_count_minute == 1
        with pytest.raises(RateLimitExceededError, match="hour rate limit"):
            adapter._check_rate_limits()
        
        # Simulate time passing for hour reset
        adapter._last_hour_reset = datetime.utcnow() - timedelta(hours=2)
        adapter._update_request_counts()
        
        # Both limits should be reset
        assert adapter._request_count_hour == 1
        # Should not raise exception
        adapter._check_rate_limits()
    
    def test_data_delay_indication(self, adapter, mock_chart_response):
        """Test that data delay is properly indicated."""
        result = adapter._parse_chart_data(mock_chart_response, "7203.T")
        
        # Should indicate 15-minute delay for free tier data
        assert result["data_delay_minutes"] == 15
    
    @pytest.mark.asyncio
    async def test_japanese_stock_symbol_handling(self, adapter, mock_chart_response):
        """Test proper handling of Japanese stock symbols."""
        test_cases = [
            ("7203", "7203.T"),
            ("7203.T", "7203.T"),
            ("7203.TYO", "7203.T")
        ]
        
        for input_symbol, expected_normalized in test_cases:
            normalized = adapter._normalize_symbol(input_symbol)
            assert normalized == expected_normalized
            
            # Test that the original symbol is preserved in response
            with patch.object(adapter, '_make_request', return_value=mock_chart_response):
                result = await adapter.get_current_price(input_symbol)
                assert result["symbol"] == input_symbol  # Original symbol preserved
    
    def test_error_handling_in_parsing(self, adapter):
        """Test error handling in data parsing methods."""
        # Test chart data parsing with missing fields
        incomplete_response = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 2500.0
                            # Missing other fields
                        }
                    }
                ]
            }
        }
        
        result = adapter._parse_chart_data(incomplete_response, "7203.T")
        
        # Should handle missing fields gracefully
        assert result["symbol"] == "7203.T"
        assert result["price"] == 2500.0
        assert result["open"] is None
        assert result["volume"] == 0  # Default value
    
    @pytest.mark.asyncio
    async def test_historical_data_with_none_values(self, adapter):
        """Test handling of None values in historical data."""
        response_with_nones = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1642204800, 1642118400],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [2490.0, None],  # None value
                                    "high": [2520.0, 2500.0],
                                    "low": [2470.0, 2450.0],
                                    "close": [2500.0, 2480.0],
                                    "volume": [15000000, None]  # None value
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        result = adapter._parse_historical_data(response_with_nones, "7203.T")
        
        assert len(result) == 2
        
        # Check that None values are handled properly
        second_record = result[1]  # Sorted newest first
        assert second_record["open"] == 0.0  # None converted to 0
        assert second_record["volume"] == 0  # None converted to 0
        assert second_record["high"] == 2500.0  # Valid value preserved