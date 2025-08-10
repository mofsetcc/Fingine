"""Data source service for managing data retrieval."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.adapters import (
    DataSourceError,
    DataSourceType,
    DataSourceUnavailableError,
    RateLimitExceededError,
    registry,
)

logger = logging.getLogger(__name__)


class DataSourceService:
    """Service for managing data source operations."""

    def __init__(self):
        """Initialize the data source service."""
        self.registry = registry

    async def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current stock price.

        Args:
            symbol: Stock symbol

        Returns:
            Stock price data

        Raises:
            DataSourceUnavailableError: If no data sources available
            RateLimitExceededError: If rate limit exceeded
        """
        try:

            async def operation(adapter):
                return await adapter.get_current_price(symbol)

            result = await self.registry.execute_with_failover(
                DataSourceType.STOCK_PRICE, operation
            )

            logger.info(f"Retrieved stock price for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get stock price for {symbol}: {e}")
            raise

    async def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[Dict[str, Any]]:
        """
        Get historical stock prices.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            interval: Data interval

        Returns:
            List of historical price data
        """
        try:

            async def operation(adapter):
                return await adapter.get_historical_prices(
                    symbol, start_date, end_date, interval
                )

            result = await self.registry.execute_with_failover(
                DataSourceType.STOCK_PRICE, operation
            )

            logger.info(
                f"Retrieved historical prices for {symbol} from {start_date} to {end_date}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get historical prices for {symbol}: {e}")
            raise

    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for stock symbols.

        Args:
            query: Search query

        Returns:
            List of matching stocks
        """
        try:

            async def operation(adapter):
                return await adapter.search_symbols(query)

            result = await self.registry.execute_with_failover(
                DataSourceType.STOCK_PRICE, operation
            )

            logger.info(f"Searched stocks with query: {query}")
            return result

        except Exception as e:
            logger.error(f"Failed to search stocks with query {query}: {e}")
            raise

    async def get_financial_statements(
        self, symbol: str, statement_type: str, period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get financial statements.

        Args:
            symbol: Stock symbol
            statement_type: Type of statement (income, balance, cash_flow)
            period: Period type (annual, quarterly)

        Returns:
            List of financial statements
        """
        try:

            async def operation(adapter):
                return await adapter.get_financial_statements(
                    symbol, statement_type, period
                )

            result = await self.registry.execute_with_failover(
                DataSourceType.FINANCIAL_DATA, operation
            )

            logger.info(f"Retrieved {statement_type} statements for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get {statement_type} statements for {symbol}: {e}")
            raise

    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview.

        Args:
            symbol: Stock symbol

        Returns:
            Company overview data
        """
        try:

            async def operation(adapter):
                return await adapter.get_company_overview(symbol)

            result = await self.registry.execute_with_failover(
                DataSourceType.FINANCIAL_DATA, operation
            )

            logger.info(f"Retrieved company overview for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get company overview for {symbol}: {e}")
            raise

    async def get_news(
        self,
        symbol: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
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
        try:

            async def operation(adapter):
                return await adapter.get_news(
                    symbol, keywords, limit, start_date, end_date
                )

            result = await self.registry.execute_with_failover(
                DataSourceType.NEWS, operation
            )

            logger.info(f"Retrieved news articles (symbol: {symbol}, limit: {limit})")
            return result

        except Exception as e:
            logger.error(f"Failed to get news: {e}")
            raise

    async def get_market_indices(self) -> List[Dict[str, Any]]:
        """
        Get market indices.

        Returns:
            List of market indices
        """
        try:

            async def operation(adapter):
                return await adapter.get_market_indices()

            result = await self.registry.execute_with_failover(
                DataSourceType.MARKET_DATA, operation
            )

            logger.info("Retrieved market indices")
            return result

        except Exception as e:
            logger.error(f"Failed to get market indices: {e}")
            raise

    async def get_market_movers(
        self, market: str = "TSE", category: str = "gainers"
    ) -> List[Dict[str, Any]]:
        """
        Get market movers.

        Args:
            market: Market identifier
            category: Category (gainers, losers, most_active)

        Returns:
            List of market movers
        """
        try:

            async def operation(adapter):
                return await adapter.get_market_movers(market, category)

            result = await self.registry.execute_with_failover(
                DataSourceType.MARKET_DATA, operation
            )

            logger.info(f"Retrieved market movers ({market}, {category})")
            return result

        except Exception as e:
            logger.error(f"Failed to get market movers: {e}")
            raise

    async def get_data_source_status(self) -> Dict[str, Any]:
        """
        Get status of all data sources.

        Returns:
            Data source status information
        """
        try:
            status = self.registry.get_registry_status()

            # Add summary statistics
            total_adapters = len(status["adapters"])
            healthy_adapters = sum(
                1
                for adapter in status["adapters"].values()
                if adapter["health_status"] == "healthy" and adapter["enabled"]
            )

            status["summary"] = {
                "total_adapters": total_adapters,
                "healthy_adapters": healthy_adapters,
                "unhealthy_adapters": total_adapters - healthy_adapters,
                "circuit_breakers_open": len(status["circuit_breakers"]),
            }

            return status

        except Exception as e:
            logger.error(f"Failed to get data source status: {e}")
            raise

    async def reset_adapter_circuit_breaker(self, adapter_name: str) -> bool:
        """
        Reset circuit breaker for an adapter.

        Args:
            adapter_name: Name of the adapter

        Returns:
            True if reset successfully
        """
        try:
            result = self.registry.reset_circuit_breaker(adapter_name)

            if result:
                logger.info(f"Reset circuit breaker for adapter: {adapter_name}")
            else:
                logger.warning(
                    f"Circuit breaker was not open for adapter: {adapter_name}"
                )

            return result

        except Exception as e:
            logger.error(f"Failed to reset circuit breaker for {adapter_name}: {e}")
            raise

    async def enable_adapter(self, adapter_name: str) -> bool:
        """
        Enable an adapter.

        Args:
            adapter_name: Name of the adapter

        Returns:
            True if enabled successfully
        """
        try:
            adapter = self.registry.get_adapter(adapter_name)
            if not adapter:
                logger.warning(f"Adapter not found: {adapter_name}")
                return False

            adapter.enable()
            logger.info(f"Enabled adapter: {adapter_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable adapter {adapter_name}: {e}")
            raise

    async def disable_adapter(self, adapter_name: str) -> bool:
        """
        Disable an adapter.

        Args:
            adapter_name: Name of the adapter

        Returns:
            True if disabled successfully
        """
        try:
            adapter = self.registry.get_adapter(adapter_name)
            if not adapter:
                logger.warning(f"Adapter not found: {adapter_name}")
                return False

            adapter.disable()
            logger.info(f"Disabled adapter: {adapter_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable adapter {adapter_name}: {e}")
            raise

    async def get_adapter_health(self, adapter_name: str) -> Optional[Dict[str, Any]]:
        """
        Get health information for a specific adapter.

        Args:
            adapter_name: Name of the adapter

        Returns:
            Health information or None if adapter not found
        """
        try:
            adapter = self.registry.get_adapter(adapter_name)
            if not adapter:
                return None

            health_check = await adapter.get_cached_health_check()
            rate_limit = await adapter.get_rate_limit_info()
            cost_info = await adapter.get_cost_info()

            return {
                "name": adapter.name,
                "type": adapter.data_source_type.value,
                "priority": adapter.priority,
                "enabled": adapter.enabled,
                "health": {
                    "status": health_check.status.value,
                    "response_time_ms": health_check.response_time_ms,
                    "last_check": health_check.last_check.isoformat(),
                    "error_message": health_check.error_message,
                    "metadata": health_check.metadata,
                },
                "rate_limit": {
                    "requests_per_minute": rate_limit.requests_per_minute,
                    "requests_per_hour": rate_limit.requests_per_hour,
                    "requests_per_day": rate_limit.requests_per_day,
                    "current_usage": rate_limit.current_usage,
                    "reset_times": {
                        k: v.isoformat() for k, v in rate_limit.reset_times.items()
                    },
                },
                "cost": {
                    "cost_per_request": cost_info.cost_per_request,
                    "currency": cost_info.currency,
                    "monthly_budget": cost_info.monthly_budget,
                    "current_monthly_usage": cost_info.current_monthly_usage,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get adapter health for {adapter_name}: {e}")
            raise

    async def start_monitoring(self) -> None:
        """Start health monitoring for all adapters."""
        try:
            await self.registry.start_health_monitoring()
            logger.info("Started data source monitoring")

        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise

    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        try:
            await self.registry.stop_health_monitoring()
            logger.info("Stopped data source monitoring")

        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            raise
