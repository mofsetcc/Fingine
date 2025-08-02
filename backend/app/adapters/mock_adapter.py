"""Mock data source adapter for testing."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .base import (
    StockPriceAdapter,
    FinancialDataAdapter,
    NewsAdapter,
    MarketDataAdapter,
    HealthCheck,
    HealthStatus,
    RateLimitInfo,
    CostInfo,
    DataSourceError,
    RateLimitExceededError
)


class MockStockPriceAdapter(StockPriceAdapter):
    """Mock stock price adapter for testing."""
    
    def __init__(self, name: str = "mock_stock_price", priority: int = 999, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, priority, config)
        self._request_count = 0
        self._should_fail = False
        self._failure_rate = 0.0  # 0.0 = never fail, 1.0 = always fail
        self._response_delay = 0.0  # Seconds to delay responses
        
    def set_failure_rate(self, rate: float) -> None:
        """Set the failure rate for testing."""
        self._failure_rate = max(0.0, min(1.0, rate))
    
    def set_response_delay(self, delay: float) -> None:
        """Set response delay for testing."""
        self._response_delay = max(0.0, delay)
    
    def force_failure(self, should_fail: bool = True) -> None:
        """Force the adapter to fail for testing."""
        self._should_fail = should_fail
    
    async def _simulate_delay_and_failure(self) -> None:
        """Simulate delay and potential failure."""
        if self._response_delay > 0:
            await asyncio.sleep(self._response_delay)
        
        self._request_count += 1
        
        if self._should_fail or (self._failure_rate > 0 and random.random() < self._failure_rate):
            raise DataSourceError("Mock adapter forced failure")
    
    async def health_check(self) -> HealthCheck:
        """Check adapter health."""
        start_time = datetime.utcnow()
        
        try:
            await asyncio.sleep(0.01)  # Simulate health check delay
            
            if self._should_fail:
                status = HealthStatus.UNHEALTHY
                error_message = "Mock adapter is set to fail"
            elif self._failure_rate > 0.5:
                status = HealthStatus.DEGRADED
                error_message = f"High failure rate: {self._failure_rate}"
            else:
                status = HealthStatus.HEALTHY
                error_message = None
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                status=status,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error_message=error_message,
                metadata={"request_count": self._request_count}
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
        """Get rate limit information."""
        return RateLimitInfo(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            current_usage={
                "minute": self._request_count % 60,
                "hour": self._request_count % 1000,
                "day": self._request_count % 10000
            },
            reset_times={
                "minute": datetime.utcnow() + timedelta(minutes=1),
                "hour": datetime.utcnow() + timedelta(hours=1),
                "day": datetime.utcnow() + timedelta(days=1)
            }
        )
    
    async def get_cost_info(self) -> CostInfo:
        """Get cost information."""
        return CostInfo(
            cost_per_request=0.001,
            currency="USD",
            monthly_budget=100.0,
            current_monthly_usage=self._request_count * 0.001
        )
    
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price for a stock symbol."""
        await self._simulate_delay_and_failure()
        
        # Generate mock price data
        base_price = hash(symbol) % 10000 + 1000  # Deterministic but varied prices
        price = base_price + random.uniform(-50, 50)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(random.uniform(-100, 100), 2),
            "change_percent": round(random.uniform(-5, 5), 2),
            "volume": random.randint(100000, 10000000),
            "timestamp": datetime.utcnow().isoformat(),
            "currency": "JPY" if symbol.endswith(".T") else "USD",
            "market_status": "open" if 9 <= datetime.utcnow().hour <= 15 else "closed"
        }
    
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """Get historical price data."""
        await self._simulate_delay_and_failure()
        
        # Generate mock historical data
        data = []
        current_date = start_date
        base_price = hash(symbol) % 10000 + 1000
        
        while current_date <= end_date:
            price = base_price + random.uniform(-200, 200)
            high = price + random.uniform(0, 50)
            low = price - random.uniform(0, 50)
            
            data.append({
                "symbol": symbol,
                "date": current_date.isoformat(),
                "open": round(price + random.uniform(-10, 10), 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(price, 2),
                "volume": random.randint(100000, 10000000),
                "adjusted_close": round(price, 2)
            })
            
            # Move to next interval
            if interval == "1d":
                current_date += timedelta(days=1)
            elif interval == "1h":
                current_date += timedelta(hours=1)
            elif interval == "1m":
                current_date += timedelta(minutes=1)
            else:
                current_date += timedelta(days=1)
        
        return data
    
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Search for stock symbols."""
        await self._simulate_delay_and_failure()
        
        # Generate mock search results
        mock_symbols = [
            {"symbol": "7203.T", "name": "Toyota Motor Corp", "exchange": "TSE"},
            {"symbol": "6758.T", "name": "Sony Group Corp", "exchange": "TSE"},
            {"symbol": "9984.T", "name": "SoftBank Group Corp", "exchange": "TSE"},
            {"symbol": "AAPL", "name": "Apple Inc", "exchange": "NASDAQ"},
            {"symbol": "GOOGL", "name": "Alphabet Inc", "exchange": "NASDAQ"},
            {"symbol": "MSFT", "name": "Microsoft Corp", "exchange": "NASDAQ"}
        ]
        
        # Filter based on query
        results = []
        query_lower = query.lower()
        
        for symbol_data in mock_symbols:
            if (
                query_lower in symbol_data["symbol"].lower() or
                query_lower in symbol_data["name"].lower()
            ):
                results.append(symbol_data)
        
        return results[:10]  # Limit to 10 results


class MockFinancialDataAdapter(FinancialDataAdapter):
    """Mock financial data adapter for testing."""
    
    def __init__(self, name: str = "mock_financial", priority: int = 999, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, priority, config)
        self._request_count = 0
        self._should_fail = False
    
    def force_failure(self, should_fail: bool = True) -> None:
        """Force the adapter to fail for testing."""
        self._should_fail = should_fail
    
    async def health_check(self) -> HealthCheck:
        """Check adapter health."""
        start_time = datetime.utcnow()
        
        try:
            await asyncio.sleep(0.01)
            
            status = HealthStatus.UNHEALTHY if self._should_fail else HealthStatus.HEALTHY
            error_message = "Mock adapter is set to fail" if self._should_fail else None
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                status=status,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error_message=error_message
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
        """Get rate limit information."""
        return RateLimitInfo(
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=5000,
            current_usage={
                "minute": self._request_count % 30,
                "hour": self._request_count % 500,
                "day": self._request_count % 5000
            },
            reset_times={
                "minute": datetime.utcnow() + timedelta(minutes=1),
                "hour": datetime.utcnow() + timedelta(hours=1),
                "day": datetime.utcnow() + timedelta(days=1)
            }
        )
    
    async def get_cost_info(self) -> CostInfo:
        """Get cost information."""
        return CostInfo(
            cost_per_request=0.01,
            currency="USD",
            monthly_budget=500.0,
            current_monthly_usage=self._request_count * 0.01
        )
    
    async def get_financial_statements(
        self,
        symbol: str,
        statement_type: str,
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """Get financial statements."""
        if self._should_fail:
            raise DataSourceError("Mock adapter forced failure")
        
        self._request_count += 1
        
        # Generate mock financial data
        statements = []
        for i in range(3):  # Last 3 periods
            year = datetime.utcnow().year - i
            
            if statement_type == "income":
                statements.append({
                    "symbol": symbol,
                    "period": f"{year}",
                    "revenue": random.randint(1000000, 100000000),
                    "gross_profit": random.randint(500000, 50000000),
                    "operating_income": random.randint(100000, 20000000),
                    "net_income": random.randint(50000, 15000000),
                    "eps": round(random.uniform(1, 100), 2)
                })
            elif statement_type == "balance":
                statements.append({
                    "symbol": symbol,
                    "period": f"{year}",
                    "total_assets": random.randint(5000000, 500000000),
                    "total_liabilities": random.randint(2000000, 300000000),
                    "shareholders_equity": random.randint(1000000, 200000000),
                    "cash": random.randint(100000, 50000000),
                    "debt": random.randint(500000, 100000000)
                })
            elif statement_type == "cash_flow":
                statements.append({
                    "symbol": symbol,
                    "period": f"{year}",
                    "operating_cash_flow": random.randint(100000, 30000000),
                    "investing_cash_flow": random.randint(-10000000, 5000000),
                    "financing_cash_flow": random.randint(-5000000, 10000000),
                    "free_cash_flow": random.randint(50000, 25000000)
                })
        
        return statements
    
    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Get company overview."""
        if self._should_fail:
            raise DataSourceError("Mock adapter forced failure")
        
        self._request_count += 1
        
        return {
            "symbol": symbol,
            "name": f"Mock Company {symbol}",
            "description": f"This is a mock company for symbol {symbol}",
            "sector": random.choice(["Technology", "Finance", "Healthcare", "Manufacturing"]),
            "industry": f"Mock Industry",
            "market_cap": random.randint(1000000000, 1000000000000),
            "employees": random.randint(1000, 500000),
            "founded": random.randint(1950, 2020),
            "headquarters": "Mock City, Mock Country",
            "website": f"https://mock-{symbol.lower()}.com"
        }