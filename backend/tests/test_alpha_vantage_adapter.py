"""Tests for Alpha Vantage adapter."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
import json

from app.adapters.alpha_vantage_adapter import AlphaVantageAdapter
from app.adapters.base import (
    HealthStatus,
    RateLimitExceededError,
    DataSourceUnavailableError,
    InvalidDataError
)


class TestAlphaVantageAdapter:
    """Test cases for AlphaVantageAdapter."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            "api_key": "test_api_key",
            "timeout": 30,
            "max_retries": 2,
            "retry_delay": 0.1,  # Short delay for tests
            "requests_per_minute": 5,
            "requests_per_day": 500
        }
    
    @pytest.fixture
    def adapter(self, config):
        """Create Alpha Vantage adapter instance."""
        return AlphaVantageAdapter(config=config)
    
    @pytest.fixture
    def mock_global_quote_response(self):
        """Mock Alpha Vantage global quote response."""
        return {
            "Global Quote": {
                "01. symbol": "AAPL",
                "02. open": "150.00",
                "03. high": "155.00",
                "04. low": "149.00",
                "05. price": "152.50",
                "06. volume": "50000000",
                "07. latest trading day": "2024-01-15",
                "08. previous close": "151.00",
                "09. change": "1.50",
                "10. change percent": "0.99%"
            }
        }
    
    @pytest.fixture
    def mock_time_series_response(self):
        """Mock Alpha Vantage time series response."""
        return {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": "AAPL",
                "3. Last Refreshed": "2024-01-15",
                "4. Output Size": "Compact",
                "5. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": {
                "2024-01-15": {
                    "1. open": "150.00",
                    "2. high": "155.00",
                    "3. low": "149.00",
                    "4. close": "152.50",
                    "5. volume": "50000000"
                },
                "2024-01-14": {
                    "1. open": "148.00",
                    "2. high": "151.00",
                    "3. low": "147.50",
                    "4. close": "151.00",
                    "5. volume": "45000000"
                }
            }
        }
    
    @pytest.fixture
    def mock_symbol_search_response(self):
        """Mock Alpha Vantage symbol search response."""
        return {
            "bestMatches": [
                {
                    "1. symbol": "AAPL",
                    "2. name": "Apple Inc.",
                    "3. type": "Equity",
                    "4. region": "United States",
                    "5. marketOpen": "09:30",
                    "6. marketClose": "16:00",
                    "7. timezone": "UTC-05",
                    "8. currency": "USD",
                    "9. matchScore": "1.0000"
                },
                {
                    "1. symbol": "AAPLF",
                    "2. name": "Apple Inc. (Foreign)",
                    "3. type": "Equity",
                    "4. region": "United States",
                    "5. marketOpen": "09:30",
                    "6. marketClose": "16:00",
                    "7. timezone": "UTC-05",
                    "8. currency": "USD",
                    "9. matchScore": "0.8000"
                }
            ]
        }
    
    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with pytest.raises(ValueError, match="API key is required"):
            AlphaVantageAdapter(config={})
    
    def test_init_with_config(self, config):
        """Test initialization with configuration."""
        adapter = AlphaVantageAdapter(config=config)
        
        assert adapter.api_key == "test_api_key"
        assert adapter.timeout == 30
        assert adapter.max_retries == 2
        assert adapter.retry_delay == 0.1
        assert adapter.requests_per_minute == 5
        assert adapter.requests_per_day == 500
    
    def test_normalize_symbol(self, adapter):
        """Test symbol normalization."""
        # Japanese stocks
        assert adapter._normalize_symbol("7203.T") == "7203.TYO"
        assert adapter._normalize_symbol("7203.TYO") == "7203.TYO"
        
        # US stocks
        assert adapter._normalize_symbol("AAPL") == "AAPL"
        assert adapter._normalize_symbol("aapl") == "AAPL"
    
    def test_parse_price_data(self, adapter, mock_global_quote_response):
        """Test parsing price data from API response."""
        result = adapter._parse_price_data(mock_global_quote_response, "AAPL")
        
        assert result["symbol"] == "AAPL"
        assert result["open"] == 150.00
        assert result["high"] == 155.00
        assert result["low"] == 149.00
        assert result["price"] == 152.50
        assert result["volume"] == 50000000
        assert result["change"] == 1.50
        assert result["change_percent"] == 0.99
        assert result["currency"] == "USD"
        assert "timestamp" in result
    
    def test_parse_price_data_japanese_stock(self, adapter, mock_global_quote_response):
        """Test parsing price data for Japanese stock."""
        result = adapter._parse_price_data(mock_global_quote_response, "7203.T")
        
        assert result["symbol"] == "7203.T"
        assert result["currency"] == "JPY"
    
    def test_parse_price_data_invalid(self, adapter):
        """Test parsing invalid price data."""
        invalid_response = {"Invalid": "data"}
        
        with pytest.raises(InvalidDataError, match="No quote data found"):
            adapter._parse_price_data(invalid_response, "AAPL")
    
    def test_parse_historical_data(self, adapter, mock_time_series_response):
        """Test parsing historical data."""
        result = adapter._parse_historical_data(mock_time_series_response, "AAPL")
        
        assert len(result) == 2
        
        # Check first record (should be sorted by date, newest first)
        first_record = result[0]
        assert first_record["symbol"] == "AAPL"
        assert first_record["open"] == 150.00
        assert first_record["high"] == 155.00
        assert first_record["low"] == 149.00
        assert first_record["close"] == 152.50
        assert first_record["volume"] == 50000000
        assert "2024-01-15" in first_record["date"]
    
    def test_parse_historical_data_invalid(self, adapter):
        """Test parsing invalid historical data."""
        invalid_response = {"Invalid": "data"}
        
        with pytest.raises(InvalidDataError, match="No time series data found"):
            adapter._parse_historical_data(invalid_response, "AAPL")
    
    def test_update_request_counts(self, adapter):
        """Test request count tracking."""
        initial_minute = adapter._request_count_minute
        initial_day = adapter._request_count_day
        initial_total = adapter._total_requests
        
        adapter._update_request_counts()
        
        assert adapter._request_count_minute == initial_minute + 1
        assert adapter._request_count_day == initial_day + 1
        assert adapter._total_requests == initial_total + 1
    
    def test_check_rate_limits_minute_exceeded(self, adapter):
        """Test rate limit check when minute limit exceeded."""
        adapter._request_count_minute = adapter.requests_per_minute
        
        with pytest.raises(RateLimitExceededError, match="minute rate limit exceeded"):
            adapter._check_rate_limits()
    
    def test_check_rate_limits_day_exceeded(self, adapter):
        """Test rate limit check when day limit exceeded."""
        adapter._request_count_day = adapter.requests_per_day
        
        with pytest.raises(RateLimitExceededError, match="daily rate limit exceeded"):
            adapter._check_rate_limits()
    
    @pytest.mark.asyncio
    async def test_get_session(self, adapter):
        """Test HTTP session creation."""
        session = await adapter._get_session()
        
        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed
        
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
    async def test_make_request_success(self, adapter, mock_global_quote_response):
        """Test successful API request."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_global_quote_response)
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            params = {"function": "GLOBAL_QUOTE", "symbol": "AAPL"}
            result = await adapter._make_request(params)
            
            assert result == mock_global_quote_response
            assert adapter._request_count_minute == 1
            assert adapter._request_count_day == 1
    
    @pytest.mark.asyncio
    async def test_make_request_api_error(self, adapter):
        """Test API request with Alpha Vantage error."""
        error_response = {"Error Message": "Invalid API call"}
        
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=error_response)
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            params = {"function": "GLOBAL_QUOTE", "symbol": "INVALID"}
            
            with pytest.raises(InvalidDataError, match="Alpha Vantage API error"):
                await adapter._make_request(params)
    
    @pytest.mark.asyncio
    async def test_make_request_rate_limit_note(self, adapter):
        """Test API request with rate limit note."""
        rate_limit_response = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute"
        }
        
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=rate_limit_response)
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            params = {"function": "GLOBAL_QUOTE", "symbol": "AAPL"}
            
            with pytest.raises(RateLimitExceededError):
                await adapter._make_request(params)
    
    @pytest.mark.asyncio
    async def test_make_request_429_status(self, adapter):
        """Test API request with 429 status code."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 429
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session
            
            params = {"function": "GLOBAL_QUOTE", "symbol": "AAPL"}
            
            with pytest.raises(RateLimitExceededError):
                await adapter._make_request(params)
    
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
            
            params = {"function": "GLOBAL_QUOTE", "symbol": "AAPL"}
            result = await adapter._make_request(params)
            
            assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_make_request_connection_error(self, adapter):
        """Test API request with connection error."""
        with patch.object(adapter, '_get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get.side_effect = aiohttp.ClientError("Connection failed")
            mock_get_session.return_value = mock_session
            
            params = {"function": "GLOBAL_QUOTE", "symbol": "AAPL"}
            
            with pytest.raises(DataSourceUnavailableError, match="connection error"):
                await adapter._make_request(params)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_global_quote_response):
        """Test health check when API is healthy."""
        with patch.object(adapter, '_make_request', return_value=mock_global_quote_response):
            health = await adapter.health_check()
            
            assert health.status == HealthStatus.HEALTHY
            assert health.response_time_ms > 0
            assert health.error_message is None
            assert "requests_today" in health.metadata
    
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
        adapter._request_count_minute = 2
        adapter._request_count_day = 50
        
        rate_limit = await adapter.get_rate_limit_info()
        
        assert rate_limit.requests_per_minute == 5
        assert rate_limit.requests_per_day == 500
        assert rate_limit.current_usage["minute"] == 2
        assert rate_limit.current_usage["day"] == 50
        assert "minute" in rate_limit.reset_times
        assert "day" in rate_limit.reset_times
    
    @pytest.mark.asyncio
    async def test_get_cost_info(self, adapter):
        """Test getting cost information."""
        adapter._total_requests = 100
        
        cost_info = await adapter.get_cost_info()
        
        assert cost_info.cost_per_request == 0.0  # Free tier
        assert cost_info.currency == "USD"
        assert cost_info.current_monthly_usage == 0.0  # 100 * 0.0
    
    @pytest.mark.asyncio
    async def test_get_current_price(self, adapter, mock_global_quote_response):
        """Test getting current stock price."""
        with patch.object(adapter, '_make_request', return_value=mock_global_quote_response):
            result = await adapter.get_current_price("AAPL")
            
            assert result["symbol"] == "AAPL"
            assert result["price"] == 152.50
            assert result["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_get_current_price_japanese_stock(self, adapter, mock_global_quote_response):
        """Test getting current price for Japanese stock."""
        with patch.object(adapter, '_make_request', return_value=mock_global_quote_response):
            result = await adapter.get_current_price("7203.T")
            
            assert result["symbol"] == "7203.T"
            assert result["currency"] == "JPY"
    
    @pytest.mark.asyncio
    async def test_get_historical_prices(self, adapter, mock_time_series_response):
        """Test getting historical prices."""
        start_date = datetime(2024, 1, 14)
        end_date = datetime(2024, 1, 15)
        
        with patch.object(adapter, '_make_request', return_value=mock_time_series_response):
            result = await adapter.get_historical_prices("AAPL", start_date, end_date)
            
            assert len(result) == 2
            assert all(record["symbol"] == "AAPL" for record in result)
            
            # Check date filtering
            for record in result:
                record_date = datetime.fromisoformat(record["date"].replace("Z", "+00:00"))
                assert start_date <= record_date <= end_date
    
    @pytest.mark.asyncio
    async def test_get_historical_prices_unsupported_interval(self, adapter):
        """Test getting historical prices with unsupported interval."""
        start_date = datetime(2024, 1, 14)
        end_date = datetime(2024, 1, 15)
        
        with pytest.raises(InvalidDataError, match="Unsupported interval"):
            await adapter.get_historical_prices("AAPL", start_date, end_date, "5m")
    
    @pytest.mark.asyncio
    async def test_search_symbols(self, adapter, mock_symbol_search_response):
        """Test searching for symbols."""
        with patch.object(adapter, '_make_request', return_value=mock_symbol_search_response):
            result = await adapter.search_symbols("Apple")
            
            assert len(result) == 2
            
            # Should be sorted by match score (descending)
            assert result[0]["match_score"] == 1.0
            assert result[1]["match_score"] == 0.8
            
            # Check first result
            first_result = result[0]
            assert first_result["symbol"] == "AAPL"
            assert first_result["name"] == "Apple Inc."
            assert first_result["type"] == "Equity"
            assert first_result["region"] == "United States"
            assert first_result["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_search_symbols_no_matches(self, adapter):
        """Test searching for symbols with no matches."""
        empty_response = {"bestMatches": []}
        
        with patch.object(adapter, '_make_request', return_value=empty_response):
            result = await adapter.search_symbols("NonexistentCompany")
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_search_symbols_no_best_matches_key(self, adapter):
        """Test searching for symbols when response has no bestMatches key."""
        invalid_response = {"someOtherKey": "value"}
        
        with patch.object(adapter, '_make_request', return_value=invalid_response):
            result = await adapter.search_symbols("Apple")
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test using adapter as async context manager."""
        async with AlphaVantageAdapter(config=config) as adapter:
            assert isinstance(adapter, AlphaVantageAdapter)
            
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
        adapter._request_count_day = adapter.requests_per_day
        
        # Should be rate limited
        with pytest.raises(RateLimitExceededError):
            adapter._check_rate_limits()
        
        # Simulate time passing for minute reset
        adapter._last_minute_reset = datetime.utcnow() - timedelta(minutes=2)
        adapter._update_request_counts()
        
        # Minute limit should be reset, but day limit still exceeded
        assert adapter._request_count_minute == 1
        with pytest.raises(RateLimitExceededError, match="daily rate limit"):
            adapter._check_rate_limits()
        
        # Simulate time passing for day reset
        adapter._last_day_reset = datetime.utcnow() - timedelta(days=2)
        adapter._update_request_counts()
        
        # Both limits should be reset
        assert adapter._request_count_day == 1
        # Should not raise exception
        adapter._check_rate_limits()