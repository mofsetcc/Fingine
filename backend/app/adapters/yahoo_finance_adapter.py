"""Yahoo Finance Japan adapter for stock price data."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import json
from urllib.parse import urlencode, quote
import re

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


class YahooFinanceJapanAdapter(StockPriceAdapter):
    """Yahoo Finance Japan API adapter for stock price data."""
    
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
    
    def __init__(
        self,
        name: str = "yahoo_finance_japan",
        priority: int = 20,  # Lower priority than Alpha Vantage
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Yahoo Finance Japan adapter.
        
        Args:
            name: Adapter name
            priority: Adapter priority (higher number = lower priority)
            config: Configuration dictionary containing:
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 1)
                - delay_minutes: Delay for free tier data in minutes (default: 15)
                - user_agent: User agent string for requests
        """
        super().__init__(name, priority, config)
        
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        self.delay_minutes = self.config.get("delay_minutes", 15)  # 15-minute delay for free data
        
        # User agent to avoid blocking
        self.user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Rate limiting (conservative limits to avoid blocking)
        self.requests_per_minute = self.config.get("requests_per_minute", 30)
        self.requests_per_hour = self.config.get("requests_per_hour", 1000)
        
        # Request tracking
        self._request_count_minute = 0
        self._request_count_hour = 0
        self._last_minute_reset = datetime.utcnow()
        self._last_hour_reset = datetime.utcnow()
        self._total_requests = 0
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
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
        
        # Reset hour counter if needed
        if (now - self._last_hour_reset).total_seconds() >= 3600:
            self._request_count_hour = 0
            self._last_hour_reset = now
        
        # Increment counters
        self._request_count_minute += 1
        self._request_count_hour += 1
        self._total_requests += 1
    
    def _check_rate_limits(self):
        """Check if we're within rate limits."""
        if self._request_count_minute >= self.requests_per_minute:
            next_reset = self._last_minute_reset + timedelta(minutes=1)
            raise RateLimitExceededError(
                f"Yahoo Finance minute rate limit exceeded ({self.requests_per_minute} requests/minute)",
                retry_after=next_reset
            )
        
        if self._request_count_hour >= self.requests_per_hour:
            next_reset = self._last_hour_reset + timedelta(hours=1)
            raise RateLimitExceededError(
                f"Yahoo Finance hour rate limit exceeded ({self.requests_per_hour} requests/hour)",
                retry_after=next_reset
            )
    
    async def _make_request(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Make API request to Yahoo Finance.
        
        Args:
            url: Request URL
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
        
        session = await self._get_session()
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making Yahoo Finance API request: {url}")
                
                async with session.get(url, params=params) as response:
                    # Update request counts
                    self._update_request_counts()
                    
                    if response.status == 200:
                        data = await response.json()
                        return data
                    
                    elif response.status == 429:
                        raise RateLimitExceededError("Yahoo Finance rate limit exceeded")
                    
                    elif response.status == 404:
                        raise InvalidDataError("Symbol not found")
                    
                    elif response.status >= 500:
                        if attempt < self.max_retries:
                            logger.warning(f"Yahoo Finance server error (attempt {attempt + 1}): {response.status}")
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        else:
                            raise DataSourceUnavailableError(f"Yahoo Finance server error: {response.status}")
                    
                    else:
                        raise DataSourceError(f"Yahoo Finance API error: {response.status}")
            
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    logger.warning(f"Yahoo Finance connection error (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise DataSourceUnavailableError(f"Yahoo Finance connection error: {e}")
        
        raise DataSourceUnavailableError("Yahoo Finance API unavailable after retries")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for Yahoo Finance API.
        
        Args:
            symbol: Input symbol
            
        Returns:
            Normalized symbol for Yahoo Finance
        """
        # Handle Japanese stocks
        if symbol.endswith(".T"):
            return symbol  # Yahoo Finance uses .T for Tokyo Stock Exchange
        elif symbol.endswith(".TYO"):
            return symbol.replace(".TYO", ".T")
        elif re.match(r'^\d{4}$', symbol):  # 4-digit Japanese stock code
            return f"{symbol}.T"
        
        # For US stocks, use as-is
        return symbol.upper()
    
    def _parse_chart_data(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Parse chart data from Yahoo Finance response.
        
        Args:
            data: API response data
            symbol: Stock symbol
            
        Returns:
            Normalized price data
        """
        try:
            chart = data["chart"]
            if not chart or "result" not in chart or not chart["result"]:
                raise InvalidDataError("No chart data found in Yahoo Finance response")
            
            result = chart["result"][0]
            meta = result.get("meta", {})
            
            # Get current price data
            current_price = meta.get("regularMarketPrice")
            previous_close = meta.get("previousClose")
            
            # Calculate change
            change = None
            change_percent = None
            if current_price is not None and previous_close is not None:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
            
            # Get trading session info
            regular_market_time = meta.get("regularMarketTime")
            if regular_market_time:
                trading_day = datetime.fromtimestamp(regular_market_time).strftime("%Y-%m-%d")
            else:
                trading_day = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Build result
            result_data = {
                "symbol": symbol,
                "price": current_price,
                "open": meta.get("regularMarketOpen"),
                "high": meta.get("regularMarketDayHigh"),
                "low": meta.get("regularMarketDayLow"),
                "volume": meta.get("regularMarketVolume", 0),
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent,
                "trading_day": trading_day,
                "timestamp": datetime.utcnow().isoformat(),
                "currency": meta.get("currency", "JPY" if symbol.endswith(".T") else "USD"),
                "market_status": "open" if meta.get("marketState") == "REGULAR" else "closed",
                "data_delay_minutes": self.delay_minutes  # Indicate data delay
            }
            
            return result_data
            
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error parsing Yahoo Finance chart data: {e}")
            raise InvalidDataError(f"Invalid chart data format: {e}")
    
    def _parse_historical_data(self, data: Dict[str, Any], symbol: str) -> List[Dict[str, Any]]:
        """
        Parse historical data from Yahoo Finance response.
        
        Args:
            data: API response data
            symbol: Stock symbol
            
        Returns:
            List of historical price data
        """
        try:
            chart = data["chart"]
            if not chart or "result" not in chart or not chart["result"]:
                raise InvalidDataError("No chart data found in Yahoo Finance response")
            
            result = chart["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            
            if "quote" not in indicators or not indicators["quote"]:
                raise InvalidDataError("No quote data in indicators")
            
            quote = indicators["quote"][0]
            
            # Get OHLCV arrays
            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])
            
            # Get adjusted close if available
            adjusted_closes = []
            if "adjclose" in indicators and indicators["adjclose"]:
                adjusted_closes = indicators["adjclose"][0].get("adjclose", [])
            
            historical_data = []
            
            for i, timestamp in enumerate(timestamps):
                try:
                    # Convert timestamp to date
                    date_obj = datetime.fromtimestamp(timestamp)
                    
                    # Get values (handle None values)
                    open_price = opens[i] if i < len(opens) and opens[i] is not None else 0
                    high_price = highs[i] if i < len(highs) and highs[i] is not None else 0
                    low_price = lows[i] if i < len(lows) and lows[i] is not None else 0
                    close_price = closes[i] if i < len(closes) and closes[i] is not None else 0
                    volume = volumes[i] if i < len(volumes) and volumes[i] is not None else 0
                    
                    adjusted_close = close_price
                    if i < len(adjusted_closes) and adjusted_closes[i] is not None:
                        adjusted_close = adjusted_closes[i]
                    
                    record = {
                        "symbol": symbol,
                        "date": date_obj.isoformat(),
                        "open": float(open_price),
                        "high": float(high_price),
                        "low": float(low_price),
                        "close": float(close_price),
                        "volume": int(volume),
                        "adjusted_close": float(adjusted_close)
                    }
                    
                    historical_data.append(record)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing historical data point {i}: {e}")
                    continue
            
            # Sort by date (newest first)
            historical_data.sort(key=lambda x: x["date"], reverse=True)
            
            return historical_data
            
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing Yahoo Finance historical data: {e}")
            raise InvalidDataError(f"Invalid historical data format: {e}")
    
    async def health_check(self) -> HealthCheck:
        """Check Yahoo Finance API health."""
        start_time = datetime.utcnow()
        
        try:
            # Make a simple API call to check health
            test_symbol = "7203.T"  # Toyota - common Japanese stock
            url = f"{self.BASE_URL}/{test_symbol}"
            params = {
                "interval": "1d",
                "range": "1d"
            }
            
            await self._make_request(url, params)
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                metadata={
                    "requests_this_hour": self._request_count_hour,
                    "requests_this_minute": self._request_count_minute,
                    "total_requests": self._total_requests,
                    "data_delay_minutes": self.delay_minutes
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
            requests_per_hour=self.requests_per_hour,
            requests_per_day=self.requests_per_hour * 24,  # Estimated
            current_usage={
                "minute": self._request_count_minute,
                "hour": self._request_count_hour,
                "day": 0  # Not tracked
            },
            reset_times={
                "minute": self._last_minute_reset + timedelta(minutes=1),
                "hour": self._last_hour_reset + timedelta(hours=1),
                "day": now + timedelta(days=1)
            }
        )
    
    async def get_cost_info(self) -> CostInfo:
        """Get cost information (Yahoo Finance is free)."""
        return CostInfo(
            cost_per_request=0.0,  # Free service
            currency="USD",
            monthly_budget=0.0,
            current_monthly_usage=0.0
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
        
        url = f"{self.BASE_URL}/{normalized_symbol}"
        params = {
            "interval": "1d",
            "range": "1d"
        }
        
        try:
            data = await self._make_request(url, params)
            return self._parse_chart_data(data, symbol)
            
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
        
        # Convert interval to Yahoo Finance format
        yahoo_interval = interval
        if interval == "1d":
            yahoo_interval = "1d"
        elif interval == "1wk":
            yahoo_interval = "1wk"
        elif interval == "1mo":
            yahoo_interval = "1mo"
        else:
            raise InvalidDataError(f"Unsupported interval: {interval}")
        
        # Convert dates to timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        url = f"{self.BASE_URL}/{normalized_symbol}"
        params = {
            "interval": yahoo_interval,
            "period1": str(start_timestamp),
            "period2": str(end_timestamp),
            "events": "history"
        }
        
        try:
            data = await self._make_request(url, params)
            historical_data = self._parse_historical_data(data, symbol)
            
            # Filter by date range (additional safety check)
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
            "q": query,
            "quotesCount": 10,
            "newsCount": 0,
            "enableFuzzyQuery": "false",
            "quotesQueryId": "tss_match_phrase_query",
            "multiQuoteQueryId": "multi_quote_single_token_query"
        }
        
        try:
            data = await self._make_request(self.SEARCH_URL, params)
            
            if "quotes" not in data:
                return []
            
            results = []
            for quote in data["quotes"]:
                # Focus on Japanese stocks and major US stocks
                symbol = quote.get("symbol", "")
                exchange = quote.get("exchange", "")
                
                results.append({
                    "symbol": symbol,
                    "name": quote.get("longname") or quote.get("shortname", ""),
                    "type": quote.get("quoteType", ""),
                    "exchange": exchange,
                    "market": quote.get("market", ""),
                    "currency": quote.get("currency", ""),
                    "score": quote.get("score", 0)
                })
            
            # Sort by score (descending)
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return results[:10]  # Limit to top 10 results
            
        except Exception as e:
            logger.error(f"Error searching symbols with query {query}: {e}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()