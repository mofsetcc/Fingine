"""Alpha Vantage stock price adapter."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import json
from urllib.parse import urlencode

from .base import (
    StockPriceAdapter,
    HealthCheck,
    HealthStatus,
    RateLimitInfo,
    CostInfo,
    DataSourceError,
    RateLimitExceededError,
    DataSourceUnavailableError,
    InvalidDataError
)

logger = logging.getLogger(__name__)


class AlphaVantageAdapter(StockPriceAdapter):
    """Alpha Vantage API adapter for stock price data."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(
        self,
        name: str = "alpha_vantage",
        priority: int = 10,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Alpha Vantage adapter.
        
        Args:
            name: Adapter name
            priority: Adapter priority
            config: Configuration dictionary containing:
                - api_key: Alpha Vantage API key (required)
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 1)
        """
        super().__init__(name, priority, config)
        
        self.api_key = self.config.get("api_key")
        if not self.api_key:
            raise ValueError("Alpha Vantage API key is required")
        
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        
        # Rate limiting (Alpha Vantage free tier: 5 calls per minute, 500 per day)
        self.requests_per_minute = self.config.get("requests_per_minute", 5)
        self.requests_per_day = self.config.get("requests_per_day", 500)
        
        # Cost tracking (free tier)
        self.cost_per_request = self.config.get("cost_per_request", 0.0)
        self.monthly_budget = self.config.get("monthly_budget", 0.0)
        
        # Request tracking
        self._request_count_minute = 0
        self._request_count_day = 0
        self._last_minute_reset = datetime.utcnow()
        self._last_day_reset = datetime.utcnow()
        self._total_requests = 0
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _close_session(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _update_request_counts(self):
        """Update request counts for rate limiting."""
        now = datetime.utcnow()
        
        # Reset minute counter if needed
        if (now - self._last_minute_reset).total_seconds() >= 60:
            self._request_count_minute = 0
            self._last_minute_reset = now
        
        # Reset day counter if needed
        if (now - self._last_day_reset).total_seconds() >= 86400:  # 24 hours
            self._request_count_day = 0
            self._last_day_reset = now
        
        # Increment counters
        self._request_count_minute += 1
        self._request_count_day += 1
        self._total_requests += 1
    
    def _check_rate_limits(self):
        """Check if we're within rate limits."""
        if self._request_count_minute >= self.requests_per_minute:
            next_reset = self._last_minute_reset + timedelta(minutes=1)
            raise RateLimitExceededError(
                f"Alpha Vantage minute rate limit exceeded ({self.requests_per_minute} requests/minute)",
                retry_after=next_reset
            )
        
        if self._request_count_day >= self.requests_per_day:
            next_reset = self._last_day_reset + timedelta(days=1)
            raise RateLimitExceededError(
                f"Alpha Vantage daily rate limit exceeded ({self.requests_per_day} requests/day)",
                retry_after=next_reset
            )
    
    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make API request to Alpha Vantage.
        
        Args:
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            DataSourceUnavailableError: If API is unavailable
            InvalidDataError: If response data is invalid
        """
        # Check rate limits
        self._check_rate_limits()
        
        # Add API key to parameters
        params["apikey"] = self.api_key
        
        session = await self._get_session()
        url = f"{self.BASE_URL}?{urlencode(params)}"
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making Alpha Vantage API request: {params.get('function', 'unknown')}")
                
                async with session.get(url) as response:
                    # Update request counts
                    self._update_request_counts()
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check for API errors
                        if "Error Message" in data:
                            raise InvalidDataError(f"Alpha Vantage API error: {data['Error Message']}")
                        
                        if "Note" in data:
                            # Rate limit message
                            if "API call frequency" in data["Note"]:
                                raise RateLimitExceededError("Alpha Vantage rate limit exceeded")
                            else:
                                logger.warning(f"Alpha Vantage note: {data['Note']}")
                        
                        return data
                    
                    elif response.status == 429:
                        raise RateLimitExceededError("Alpha Vantage rate limit exceeded")
                    
                    elif response.status >= 500:
                        if attempt < self.max_retries:
                            logger.warning(f"Alpha Vantage server error (attempt {attempt + 1}): {response.status}")
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        else:
                            raise DataSourceUnavailableError(f"Alpha Vantage server error: {response.status}")
                    
                    else:
                        raise DataSourceError(f"Alpha Vantage API error: {response.status}")
            
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    logger.warning(f"Alpha Vantage connection error (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise DataSourceUnavailableError(f"Alpha Vantage connection error: {e}")
        
        raise DataSourceUnavailableError("Alpha Vantage API unavailable after retries")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for Alpha Vantage API.
        
        Args:
            symbol: Input symbol
            
        Returns:
            Normalized symbol
        """
        # Remove common suffixes for Japanese stocks
        if symbol.endswith(".T"):
            return symbol[:-2] + ".TYO"  # Tokyo Stock Exchange
        elif symbol.endswith(".TYO"):
            return symbol  # Already normalized
        
        # For US stocks, use as-is
        return symbol.upper()
    
    def _parse_price_data(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Parse price data from Alpha Vantage response.
        
        Args:
            data: API response data
            symbol: Stock symbol
            
        Returns:
            Normalized price data
        """
        # Try to find the quote data
        quote_data = None
        
        if "Global Quote" in data:
            quote_data = data["Global Quote"]
        elif "Realtime Currency Exchange Rate" in data:
            # For currency pairs
            quote_data = data["Realtime Currency Exchange Rate"]
        
        if not quote_data:
            raise InvalidDataError("No quote data found in Alpha Vantage response")
        
        # Map Alpha Vantage fields to our format
        field_mapping = {
            "01. symbol": "symbol",
            "02. open": "open",
            "03. high": "high",
            "04. low": "low",
            "05. price": "price",
            "06. volume": "volume",
            "07. latest trading day": "trading_day",
            "08. previous close": "previous_close",
            "09. change": "change",
            "10. change percent": "change_percent"
        }
        
        result = {"symbol": symbol}
        
        for av_field, our_field in field_mapping.items():
            if av_field in quote_data:
                value = quote_data[av_field]
                
                # Convert numeric fields
                if our_field in ["open", "high", "low", "price", "previous_close", "change"]:
                    try:
                        result[our_field] = float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid numeric value for {our_field}: {value}")
                        result[our_field] = None
                
                elif our_field == "volume":
                    try:
                        result[our_field] = int(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid volume value: {value}")
                        result[our_field] = 0
                
                elif our_field == "change_percent":
                    # Remove percentage sign and convert
                    try:
                        clean_value = value.replace("%", "")
                        result[our_field] = float(clean_value)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid percentage value: {value}")
                        result[our_field] = None
                
                else:
                    result[our_field] = value
        
        # Add timestamp
        result["timestamp"] = datetime.utcnow().isoformat()
        
        # Determine currency based on symbol
        if symbol.endswith(".TYO") or symbol.endswith(".T"):
            result["currency"] = "JPY"
        else:
            result["currency"] = "USD"
        
        # Add market status (simplified)
        now = datetime.utcnow()
        if 0 <= now.hour <= 6 or 21 <= now.hour <= 23:  # Rough US market hours in UTC
            result["market_status"] = "open"
        else:
            result["market_status"] = "closed"
        
        return result
    
    def _parse_historical_data(self, data: Dict[str, Any], symbol: str) -> List[Dict[str, Any]]:
        """
        Parse historical data from Alpha Vantage response.
        
        Args:
            data: API response data
            symbol: Stock symbol
            
        Returns:
            List of historical price data
        """
        # Find time series data
        time_series_key = None
        for key in data.keys():
            if "Time Series" in key:
                time_series_key = key
                break
        
        if not time_series_key:
            raise InvalidDataError("No time series data found in Alpha Vantage response")
        
        time_series = data[time_series_key]
        result = []
        
        for date_str, price_data in time_series.items():
            try:
                # Parse date
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Extract OHLCV data
                record = {
                    "symbol": symbol,
                    "date": date_obj.isoformat(),
                    "open": float(price_data.get("1. open", 0)),
                    "high": float(price_data.get("2. high", 0)),
                    "low": float(price_data.get("3. low", 0)),
                    "close": float(price_data.get("4. close", 0)),
                    "volume": int(price_data.get("5. volume", 0)),
                    "adjusted_close": float(price_data.get("5. adjusted close", price_data.get("4. close", 0)))
                }
                
                result.append(record)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing historical data for {date_str}: {e}")
                continue
        
        # Sort by date (newest first)
        result.sort(key=lambda x: x["date"], reverse=True)
        
        return result
    
    async def health_check(self) -> HealthCheck:
        """Check Alpha Vantage API health."""
        start_time = datetime.utcnow()
        
        try:
            # Make a simple API call to check health
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": "AAPL"  # Use a common symbol
            }
            
            await self._make_request(params)
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                metadata={
                    "requests_today": self._request_count_day,
                    "requests_this_minute": self._request_count_minute,
                    "total_requests": self._total_requests
                }
            )
            
        except RateLimitExceededError as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error_message=str(e),
                metadata={"rate_limited": True}
            )
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit information."""
        now = datetime.utcnow()
        
        return RateLimitInfo(
            requests_per_minute=self.requests_per_minute,
            requests_per_hour=self.requests_per_minute * 60,  # Not enforced by Alpha Vantage
            requests_per_day=self.requests_per_day,
            current_usage={
                "minute": self._request_count_minute,
                "hour": 0,  # Not tracked
                "day": self._request_count_day
            },
            reset_times={
                "minute": self._last_minute_reset + timedelta(minutes=1),
                "hour": now + timedelta(hours=1),
                "day": self._last_day_reset + timedelta(days=1)
            }
        )
    
    async def get_cost_info(self) -> CostInfo:
        """Get cost information."""
        return CostInfo(
            cost_per_request=self.cost_per_request,
            currency="USD",
            monthly_budget=self.monthly_budget,
            current_monthly_usage=self._total_requests * self.cost_per_request
        )
    
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current price for a stock symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price data
        """
        normalized_symbol = self._normalize_symbol(symbol)
        
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": normalized_symbol
        }
        
        try:
            data = await self._make_request(params)
            return self._parse_price_data(data, symbol)
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            raise
    
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            interval: Data interval (1d, 1wk, 1mo supported)
            
        Returns:
            List of historical price data
        """
        normalized_symbol = self._normalize_symbol(symbol)
        
        # Map interval to Alpha Vantage function
        if interval == "1d":
            function = "TIME_SERIES_DAILY_ADJUSTED"
        elif interval == "1wk":
            function = "TIME_SERIES_WEEKLY_ADJUSTED"
        elif interval == "1mo":
            function = "TIME_SERIES_MONTHLY_ADJUSTED"
        else:
            raise InvalidDataError(f"Unsupported interval: {interval}")
        
        params = {
            "function": function,
            "symbol": normalized_symbol,
            "outputsize": "full"  # Get full historical data
        }
        
        try:
            data = await self._make_request(params)
            historical_data = self._parse_historical_data(data, symbol)
            
            # Filter by date range
            filtered_data = []
            for record in historical_data:
                record_date = datetime.fromisoformat(record["date"].replace("Z", "+00:00"))
                if start_date <= record_date <= end_date:
                    filtered_data.append(record)
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol}: {e}")
            raise
    
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for stock symbols.
        
        Args:
            query: Search query
            
        Returns:
            List of matching symbols
        """
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query
        }
        
        try:
            data = await self._make_request(params)
            
            if "bestMatches" not in data:
                return []
            
            results = []
            for match in data["bestMatches"]:
                results.append({
                    "symbol": match.get("1. symbol", ""),
                    "name": match.get("2. name", ""),
                    "type": match.get("3. type", ""),
                    "region": match.get("4. region", ""),
                    "market_open": match.get("5. marketOpen", ""),
                    "market_close": match.get("6. marketClose", ""),
                    "timezone": match.get("7. timezone", ""),
                    "currency": match.get("8. currency", ""),
                    "match_score": float(match.get("9. matchScore", 0))
                })
            
            # Sort by match score (descending)
            results.sort(key=lambda x: x["match_score"], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching symbols with query {query}: {e}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()