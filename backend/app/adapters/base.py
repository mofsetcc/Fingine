"""Base data source adapter interface."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Types of data sources."""
    STOCK_PRICE = "stock_price"
    FINANCIAL_DATA = "financial_data"
    NEWS = "news"
    MARKET_DATA = "market_data"


class HealthStatus(Enum):
    """Health status of a data source."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    status: HealthStatus
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitInfo:
    """Rate limit information."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    current_usage: Dict[str, int]  # {"minute": 10, "hour": 100, "day": 1000}
    reset_times: Dict[str, datetime]  # When each limit resets


@dataclass
class CostInfo:
    """Cost information for API calls."""
    cost_per_request: float
    currency: str = "USD"
    monthly_budget: Optional[float] = None
    current_monthly_usage: float = 0.0


class DataSourceError(Exception):
    """Base exception for data source errors."""
    pass


class RateLimitExceededError(DataSourceError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[datetime] = None):
        super().__init__(message)
        self.retry_after = retry_after


class DataSourceUnavailableError(DataSourceError):
    """Raised when data source is unavailable."""
    pass


class InvalidDataError(DataSourceError):
    """Raised when received data is invalid."""
    pass


class BaseDataSourceAdapter(ABC):
    """Base class for all data source adapters."""
    
    def __init__(
        self,
        name: str,
        data_source_type: DataSourceType,
        priority: int = 100,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the adapter.
        
        Args:
            name: Unique name for this adapter
            data_source_type: Type of data this adapter provides
            priority: Priority level (lower = higher priority)
            config: Configuration dictionary
        """
        self.name = name
        self.data_source_type = data_source_type
        self.priority = priority
        self.config = config or {}
        self._last_health_check: Optional[HealthCheck] = None
        self._enabled = True
        
    @property
    def enabled(self) -> bool:
        """Whether this adapter is enabled."""
        return self._enabled
    
    def enable(self) -> None:
        """Enable this adapter."""
        self._enabled = True
        logger.info(f"Data source adapter '{self.name}' enabled")
    
    def disable(self) -> None:
        """Disable this adapter."""
        self._enabled = False
        logger.warning(f"Data source adapter '{self.name}' disabled")
    
    @abstractmethod
    async def health_check(self) -> HealthCheck:
        """
        Check the health of this data source.
        
        Returns:
            HealthCheck result
        """
        pass
    
    @abstractmethod
    async def get_rate_limit_info(self) -> RateLimitInfo:
        """
        Get current rate limit information.
        
        Returns:
            Rate limit information
        """
        pass
    
    @abstractmethod
    async def get_cost_info(self) -> CostInfo:
        """
        Get cost information for this data source.
        
        Returns:
            Cost information
        """
        pass
    
    async def get_cached_health_check(self, max_age_seconds: int = 300) -> HealthCheck:
        """
        Get cached health check result if available and not too old.
        
        Args:
            max_age_seconds: Maximum age of cached result in seconds
            
        Returns:
            Health check result
        """
        if (
            self._last_health_check and
            (datetime.utcnow() - self._last_health_check.last_check).total_seconds() < max_age_seconds
        ):
            return self._last_health_check
        
        # Perform new health check
        self._last_health_check = await self.health_check()
        return self._last_health_check
    
    def is_healthy(self) -> bool:
        """
        Check if the adapter is currently healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        if not self._last_health_check:
            return False
        
        return self._last_health_check.status == HealthStatus.HEALTHY
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"{self.__class__.__name__}(name='{self.name}', type={self.data_source_type.value}, priority={self.priority})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the adapter."""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"type={self.data_source_type.value}, "
            f"priority={self.priority}, "
            f"enabled={self.enabled})"
        )


class StockPriceAdapter(BaseDataSourceAdapter):
    """Base class for stock price data adapters."""
    
    def __init__(self, name: str, priority: int = 100, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, DataSourceType.STOCK_PRICE, priority, config)
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current price for a stock symbol.
        
        Args:
            symbol: Stock symbol (e.g., "7203.T" for Toyota)
            
        Returns:
            Dictionary containing price data
        """
        pass
    
    @abstractmethod
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a stock symbol.
        
        Args:
            symbol: Stock symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
            
        Returns:
            List of price data dictionaries
        """
        pass
    
    @abstractmethod
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for stock symbols.
        
        Args:
            query: Search query (company name or symbol)
            
        Returns:
            List of matching symbols with metadata
        """
        pass


class FinancialDataAdapter(BaseDataSourceAdapter):
    """Base class for financial data adapters."""
    
    def __init__(self, name: str, priority: int = 100, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, DataSourceType.FINANCIAL_DATA, priority, config)
    
    @abstractmethod
    async def get_financial_statements(
        self,
        symbol: str,
        statement_type: str,
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get financial statements for a company.
        
        Args:
            symbol: Stock symbol
            statement_type: Type of statement (income, balance, cash_flow)
            period: Period type (annual, quarterly)
            
        Returns:
            List of financial statement data
        """
        pass
    
    @abstractmethod
    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview information.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Company overview data
        """
        pass


class NewsAdapter(BaseDataSourceAdapter):
    """Base class for news data adapters."""
    
    def __init__(self, name: str, priority: int = 100, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, DataSourceType.NEWS, priority, config)
    
    @abstractmethod
    async def get_news(
        self,
        symbol: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get news articles.
        
        Args:
            symbol: Stock symbol to filter news
            keywords: Keywords to search for
            limit: Maximum number of articles
            start_date: Start date for news
            end_date: End date for news
            
        Returns:
            List of news articles
        """
        pass


class MarketDataAdapter(BaseDataSourceAdapter):
    """Base class for market data adapters."""
    
    def __init__(self, name: str, priority: int = 100, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, DataSourceType.MARKET_DATA, priority, config)
    
    @abstractmethod
    async def get_market_indices(self) -> List[Dict[str, Any]]:
        """
        Get market indices data.
        
        Returns:
            List of market indices with current values
        """
        pass
    
    @abstractmethod
    async def get_market_movers(
        self,
        market: str = "TSE",
        category: str = "gainers"
    ) -> List[Dict[str, Any]]:
        """
        Get market movers (gainers, losers, most active).
        
        Args:
            market: Market identifier (TSE, NASDAQ, etc.)
            category: Category (gainers, losers, most_active)
            
        Returns:
            List of stocks with movement data
        """
        pass