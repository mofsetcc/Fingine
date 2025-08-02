"""Tests for data source adapters."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.adapters import (
    DataSourceRegistry,
    DataSourceType,
    HealthStatus,
    HealthCheck,
    MockStockPriceAdapter,
    MockFinancialDataAdapter,
    DataSourceError,
    DataSourceUnavailableError,
    RateLimitExceededError
)


class TestDataSourceRegistry:
    """Test cases for DataSourceRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return DataSourceRegistry()
    
    @pytest.fixture
    def mock_stock_adapter(self):
        """Create a mock stock price adapter."""
        return MockStockPriceAdapter("test_stock", priority=10)
    
    @pytest.fixture
    def mock_financial_adapter(self):
        """Create a mock financial data adapter."""
        return MockFinancialDataAdapter("test_financial", priority=20)
    
    def test_register_adapter(self, registry, mock_stock_adapter):
        """Test adapter registration."""
        registry.register_adapter(mock_stock_adapter)
        
        # Check adapter is registered
        assert registry.get_adapter("test_stock") == mock_stock_adapter
        
        # Check adapter is in type-specific list
        stock_adapters = registry.get_adapters_by_type(DataSourceType.STOCK_PRICE)
        assert mock_stock_adapter in stock_adapters
    
    def test_register_duplicate_adapter_name(self, registry, mock_stock_adapter):
        """Test registering adapter with duplicate name raises error."""
        registry.register_adapter(mock_stock_adapter)
        
        duplicate_adapter = MockStockPriceAdapter("test_stock", priority=20)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_adapter(duplicate_adapter)
    
    def test_unregister_adapter(self, registry, mock_stock_adapter):
        """Test adapter unregistration."""
        registry.register_adapter(mock_stock_adapter)
        
        # Verify it's registered
        assert registry.get_adapter("test_stock") == mock_stock_adapter
        
        # Unregister
        registry.unregister_adapter("test_stock")
        
        # Verify it's gone
        assert registry.get_adapter("test_stock") is None
        stock_adapters = registry.get_adapters_by_type(DataSourceType.STOCK_PRICE)
        assert mock_stock_adapter not in stock_adapters
    
    def test_unregister_nonexistent_adapter(self, registry):
        """Test unregistering non-existent adapter raises error."""
        with pytest.raises(KeyError, match="not found"):
            registry.unregister_adapter("nonexistent")
    
    def test_get_adapters_by_type_priority_order(self, registry):
        """Test adapters are returned in priority order."""
        adapter1 = MockStockPriceAdapter("adapter1", priority=30)
        adapter2 = MockStockPriceAdapter("adapter2", priority=10)
        adapter3 = MockStockPriceAdapter("adapter3", priority=20)
        
        # Register in random order
        registry.register_adapter(adapter1)
        registry.register_adapter(adapter2)
        registry.register_adapter(adapter3)
        
        # Should be returned in priority order (lower number = higher priority)
        adapters = registry.get_adapters_by_type(DataSourceType.STOCK_PRICE)
        assert adapters == [adapter2, adapter3, adapter1]
    
    @pytest.mark.asyncio
    async def test_get_healthy_adapters(self, registry, mock_stock_adapter):
        """Test getting healthy adapters."""
        # Set up adapter with healthy status
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        
        registry.register_adapter(mock_stock_adapter)
        
        healthy_adapters = registry.get_healthy_adapters(DataSourceType.STOCK_PRICE)
        assert mock_stock_adapter in healthy_adapters
    
    @pytest.mark.asyncio
    async def test_get_healthy_adapters_excludes_unhealthy(self, registry, mock_stock_adapter):
        """Test that unhealthy adapters are excluded."""
        # Set up adapter with unhealthy status
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow(),
            error_message="Test error"
        )
        
        registry.register_adapter(mock_stock_adapter)
        
        healthy_adapters = registry.get_healthy_adapters(DataSourceType.STOCK_PRICE)
        assert mock_stock_adapter not in healthy_adapters
    
    @pytest.mark.asyncio
    async def test_get_healthy_adapters_excludes_disabled(self, registry, mock_stock_adapter):
        """Test that disabled adapters are excluded."""
        # Set up healthy but disabled adapter
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        mock_stock_adapter.disable()
        
        registry.register_adapter(mock_stock_adapter)
        
        healthy_adapters = registry.get_healthy_adapters(DataSourceType.STOCK_PRICE)
        assert mock_stock_adapter not in healthy_adapters
    
    @pytest.mark.asyncio
    async def test_get_primary_adapter(self, registry):
        """Test getting primary (highest priority) adapter."""
        adapter1 = MockStockPriceAdapter("adapter1", priority=30)
        adapter2 = MockStockPriceAdapter("adapter2", priority=10)  # Highest priority
        adapter3 = MockStockPriceAdapter("adapter3", priority=20)
        
        # Set all as healthy
        for adapter in [adapter1, adapter2, adapter3]:
            adapter._last_health_check = HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=100,
                last_check=datetime.utcnow()
            )
            registry.register_adapter(adapter)
        
        primary = registry.get_primary_adapter(DataSourceType.STOCK_PRICE)
        assert primary == adapter2  # Lowest priority number = highest priority
    
    @pytest.mark.asyncio
    async def test_get_primary_adapter_no_healthy(self, registry, mock_stock_adapter):
        """Test getting primary adapter when none are healthy."""
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        registry.register_adapter(mock_stock_adapter)
        
        primary = registry.get_primary_adapter(DataSourceType.STOCK_PRICE)
        assert primary is None
    
    @pytest.mark.asyncio
    async def test_execute_with_failover_success(self, registry, mock_stock_adapter):
        """Test successful execution with failover."""
        # Set up healthy adapter
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        registry.register_adapter(mock_stock_adapter)
        
        # Define operation
        async def operation(adapter):
            return await adapter.get_current_price("TEST")
        
        # Execute
        result = await registry.execute_with_failover(
            DataSourceType.STOCK_PRICE,
            operation
        )
        
        assert result["symbol"] == "TEST"
        assert "price" in result
    
    @pytest.mark.asyncio
    async def test_execute_with_failover_primary_fails(self, registry):
        """Test failover when primary adapter fails."""
        # Create two adapters
        primary = MockStockPriceAdapter("primary", priority=10)
        secondary = MockStockPriceAdapter("secondary", priority=20)
        
        # Set both as healthy initially
        for adapter in [primary, secondary]:
            adapter._last_health_check = HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=100,
                last_check=datetime.utcnow()
            )
            registry.register_adapter(adapter)
        
        # Make primary fail
        primary.force_failure(True)
        
        # Define operation
        async def operation(adapter):
            return await adapter.get_current_price("TEST")
        
        # Execute - should failover to secondary
        result = await registry.execute_with_failover(
            DataSourceType.STOCK_PRICE,
            operation
        )
        
        assert result["symbol"] == "TEST"
    
    @pytest.mark.asyncio
    async def test_execute_with_failover_all_fail(self, registry):
        """Test failover when all adapters fail."""
        adapter = MockStockPriceAdapter("test", priority=10)
        adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        adapter.force_failure(True)
        registry.register_adapter(adapter)
        
        async def operation(adapter):
            return await adapter.get_current_price("TEST")
        
        with pytest.raises(DataSourceUnavailableError):
            await registry.execute_with_failover(
                DataSourceType.STOCK_PRICE,
                operation
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_failover_no_adapters(self, registry):
        """Test failover when no adapters are available."""
        async def operation(adapter):
            return await adapter.get_current_price("TEST")
        
        with pytest.raises(DataSourceUnavailableError, match="No healthy adapters"):
            await registry.execute_with_failover(
                DataSourceType.STOCK_PRICE,
                operation
            )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, registry, mock_stock_adapter):
        """Test circuit breaker opens after repeated failures."""
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        registry.register_adapter(mock_stock_adapter)
        
        # Set high failure rate
        mock_stock_adapter.set_failure_rate(1.0)  # Always fail
        
        async def operation(adapter):
            return await adapter.get_current_price("TEST")
        
        # Execute multiple times to trigger circuit breaker
        for _ in range(6):  # More than threshold (5)
            try:
                await registry.execute_with_failover(
                    DataSourceType.STOCK_PRICE,
                    operation,
                    max_retries=1
                )
            except DataSourceUnavailableError:
                pass
        
        # Circuit breaker should be open
        assert registry._is_circuit_breaker_open("test_stock")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, registry, mock_stock_adapter):
        """Test manual circuit breaker reset."""
        registry.register_adapter(mock_stock_adapter)
        
        # Manually open circuit breaker
        registry._circuit_breaker_state["test_stock"] = True
        registry._circuit_breaker_reset_time["test_stock"] = datetime.utcnow() + timedelta(minutes=5)
        
        assert registry._is_circuit_breaker_open("test_stock")
        
        # Reset circuit breaker
        result = registry.reset_circuit_breaker("test_stock")
        assert result is True
        assert not registry._is_circuit_breaker_open("test_stock")
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_not_counted_as_failure(self, registry):
        """Test that rate limit errors don't count as failures for circuit breaker."""
        adapter = MockStockPriceAdapter("test", priority=10)
        adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=100,
            last_check=datetime.utcnow()
        )
        registry.register_adapter(adapter)
        
        async def operation(adapter):
            raise RateLimitExceededError("Rate limit exceeded")
        
        # This should raise RateLimitExceededError but not trigger circuit breaker
        with pytest.raises(RateLimitExceededError):
            await registry.execute_with_failover(
                DataSourceType.STOCK_PRICE,
                operation
            )
        
        # Circuit breaker should not be open
        assert not registry._is_circuit_breaker_open("test")
    
    def test_enable_disable_failover(self, registry):
        """Test enabling and disabling failover."""
        assert registry._failover_enabled is True
        
        registry.disable_failover()
        assert registry._failover_enabled is False
        
        registry.enable_failover()
        assert registry._failover_enabled is True
    
    @pytest.mark.asyncio
    async def test_health_monitoring_start_stop(self, registry):
        """Test starting and stopping health monitoring."""
        await registry.start_health_monitoring()
        assert registry._health_check_task is not None
        assert not registry._health_check_task.done()
        
        await registry.stop_health_monitoring()
        assert registry._health_check_task.done()
    
    def test_get_registry_status(self, registry, mock_stock_adapter):
        """Test getting registry status."""
        mock_stock_adapter._last_health_check = HealthCheck(
            status=HealthStatus.HEALTHY,
            response_time_ms=150,
            last_check=datetime.utcnow()
        )
        registry.register_adapter(mock_stock_adapter)
        
        status = registry.get_registry_status()
        
        assert "failover_enabled" in status
        assert "adapters" in status
        assert "test_stock" in status["adapters"]
        
        adapter_status = status["adapters"]["test_stock"]
        assert adapter_status["type"] == "stock_price"
        assert adapter_status["priority"] == 999
        assert adapter_status["enabled"] is True
        assert adapter_status["health_status"] == "healthy"
        assert adapter_status["response_time_ms"] == 150


class TestMockStockPriceAdapter:
    """Test cases for MockStockPriceAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create a mock stock price adapter."""
        return MockStockPriceAdapter()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter):
        """Test health check when adapter is healthy."""
        health = await adapter.health_check()
        
        assert health.status == HealthStatus.HEALTHY
        assert health.response_time_ms > 0
        assert health.error_message is None
        assert "request_count" in health.metadata
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, adapter):
        """Test health check when adapter is forced to fail."""
        adapter.force_failure(True)
        
        health = await adapter.health_check()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert health.error_message == "Mock adapter is set to fail"
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, adapter):
        """Test health check when adapter has high failure rate."""
        adapter.set_failure_rate(0.8)  # High failure rate
        
        health = await adapter.health_check()
        
        assert health.status == HealthStatus.DEGRADED
        assert "High failure rate" in health.error_message
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, adapter):
        """Test getting rate limit information."""
        rate_limit = await adapter.get_rate_limit_info()
        
        assert rate_limit.requests_per_minute == 60
        assert rate_limit.requests_per_hour == 1000
        assert rate_limit.requests_per_day == 10000
        assert "minute" in rate_limit.current_usage
        assert "hour" in rate_limit.current_usage
        assert "day" in rate_limit.current_usage
    
    @pytest.mark.asyncio
    async def test_get_cost_info(self, adapter):
        """Test getting cost information."""
        cost_info = await adapter.get_cost_info()
        
        assert cost_info.cost_per_request == 0.001
        assert cost_info.currency == "USD"
        assert cost_info.monthly_budget == 100.0
        assert cost_info.current_monthly_usage >= 0
    
    @pytest.mark.asyncio
    async def test_get_current_price(self, adapter):
        """Test getting current price."""
        price_data = await adapter.get_current_price("7203.T")
        
        assert price_data["symbol"] == "7203.T"
        assert "price" in price_data
        assert "change" in price_data
        assert "change_percent" in price_data
        assert "volume" in price_data
        assert "timestamp" in price_data
        assert price_data["currency"] == "JPY"  # Japanese stock
    
    @pytest.mark.asyncio
    async def test_get_current_price_failure(self, adapter):
        """Test getting current price when adapter fails."""
        adapter.force_failure(True)
        
        with pytest.raises(DataSourceError):
            await adapter.get_current_price("TEST")
    
    @pytest.mark.asyncio
    async def test_get_historical_prices(self, adapter):
        """Test getting historical prices."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        historical_data = await adapter.get_historical_prices("TEST", start_date, end_date)
        
        assert len(historical_data) == 5  # 5 days
        
        for data_point in historical_data:
            assert data_point["symbol"] == "TEST"
            assert "date" in data_point
            assert "open" in data_point
            assert "high" in data_point
            assert "low" in data_point
            assert "close" in data_point
            assert "volume" in data_point
    
    @pytest.mark.asyncio
    async def test_search_symbols(self, adapter):
        """Test searching for symbols."""
        results = await adapter.search_symbols("Toyota")
        
        assert len(results) > 0
        
        # Should find Toyota
        toyota_found = any(
            "Toyota" in result["name"] for result in results
        )
        assert toyota_found
        
        for result in results:
            assert "symbol" in result
            assert "name" in result
            assert "exchange" in result
    
    @pytest.mark.asyncio
    async def test_response_delay(self, adapter):
        """Test response delay simulation."""
        adapter.set_response_delay(0.1)  # 100ms delay
        
        start_time = datetime.utcnow()
        await adapter.get_current_price("TEST")
        end_time = datetime.utcnow()
        
        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 0.1  # Should take at least 100ms
    
    @pytest.mark.asyncio
    async def test_failure_rate(self, adapter):
        """Test failure rate simulation."""
        adapter.set_failure_rate(1.0)  # Always fail
        
        with pytest.raises(DataSourceError):
            await adapter.get_current_price("TEST")


class TestMockFinancialDataAdapter:
    """Test cases for MockFinancialDataAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create a mock financial data adapter."""
        return MockFinancialDataAdapter()
    
    @pytest.mark.asyncio
    async def test_get_financial_statements_income(self, adapter):
        """Test getting income statements."""
        statements = await adapter.get_financial_statements("TEST", "income")
        
        assert len(statements) == 3  # Last 3 years
        
        for statement in statements:
            assert statement["symbol"] == "TEST"
            assert "period" in statement
            assert "revenue" in statement
            assert "gross_profit" in statement
            assert "operating_income" in statement
            assert "net_income" in statement
            assert "eps" in statement
    
    @pytest.mark.asyncio
    async def test_get_financial_statements_balance(self, adapter):
        """Test getting balance sheets."""
        statements = await adapter.get_financial_statements("TEST", "balance")
        
        assert len(statements) == 3
        
        for statement in statements:
            assert statement["symbol"] == "TEST"
            assert "total_assets" in statement
            assert "total_liabilities" in statement
            assert "shareholders_equity" in statement
            assert "cash" in statement
            assert "debt" in statement
    
    @pytest.mark.asyncio
    async def test_get_financial_statements_cash_flow(self, adapter):
        """Test getting cash flow statements."""
        statements = await adapter.get_financial_statements("TEST", "cash_flow")
        
        assert len(statements) == 3
        
        for statement in statements:
            assert statement["symbol"] == "TEST"
            assert "operating_cash_flow" in statement
            assert "investing_cash_flow" in statement
            assert "financing_cash_flow" in statement
            assert "free_cash_flow" in statement
    
    @pytest.mark.asyncio
    async def test_get_company_overview(self, adapter):
        """Test getting company overview."""
        overview = await adapter.get_company_overview("TEST")
        
        assert overview["symbol"] == "TEST"
        assert "name" in overview
        assert "description" in overview
        assert "sector" in overview
        assert "industry" in overview
        assert "market_cap" in overview
        assert "employees" in overview
        assert "founded" in overview
        assert "headquarters" in overview
        assert "website" in overview
    
    @pytest.mark.asyncio
    async def test_forced_failure(self, adapter):
        """Test forced failure."""
        adapter.force_failure(True)
        
        with pytest.raises(DataSourceError):
            await adapter.get_financial_statements("TEST", "income")
        
        with pytest.raises(DataSourceError):
            await adapter.get_company_overview("TEST")