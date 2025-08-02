"""Data source adapters package."""

from .base import (
    BaseDataSourceAdapter,
    StockPriceAdapter,
    FinancialDataAdapter,
    NewsAdapter,
    MarketDataAdapter,
    DataSourceType,
    HealthStatus,
    HealthCheck,
    RateLimitInfo,
    CostInfo,
    DataSourceError,
    RateLimitExceededError,
    DataSourceUnavailableError,
    InvalidDataError
)

from .registry import DataSourceRegistry, registry

from .mock_adapter import (
    MockStockPriceAdapter,
    MockFinancialDataAdapter
)

from .alpha_vantage_adapter import AlphaVantageAdapter

from .yahoo_finance_adapter import YahooFinanceJapanAdapter

from .edinet_adapter import EDINETAdapter

from .edinet_setup import (
    create_edinet_config,
    setup_edinet_adapter,
    setup_edinet_with_registry,
    get_edinet_production_config,
    get_edinet_development_config,
    validate_edinet_config,
    test_edinet_connection,
    setup_from_environment as setup_edinet_from_environment
)

from .yahoo_finance_setup import (
    create_yahoo_finance_config,
    setup_yahoo_finance_adapter,
    setup_yahoo_finance_fallback,
    get_yahoo_finance_conservative_config,
    validate_yahoo_finance_config,
    test_yahoo_finance_connection,
    setup_from_environment as setup_yahoo_finance_from_environment
)

from .alpha_vantage_setup import (
    create_alpha_vantage_config,
    setup_alpha_vantage_adapter,
    setup_alpha_vantage_with_fallback,
    get_alpha_vantage_premium_config,
    validate_alpha_vantage_config,
    test_alpha_vantage_connection,
    setup_from_environment
)

__all__ = [
    # Base classes and types
    "BaseDataSourceAdapter",
    "StockPriceAdapter", 
    "FinancialDataAdapter",
    "NewsAdapter",
    "MarketDataAdapter",
    "DataSourceType",
    "HealthStatus",
    "HealthCheck",
    "RateLimitInfo",
    "CostInfo",
    
    # Exceptions
    "DataSourceError",
    "RateLimitExceededError",
    "DataSourceUnavailableError",
    "InvalidDataError",
    
    # Registry
    "DataSourceRegistry",
    "registry",
    
    # Mock adapters
    "MockStockPriceAdapter",
    "MockFinancialDataAdapter",
    
    # Alpha Vantage adapter
    "AlphaVantageAdapter",
    
    # Yahoo Finance adapter
    "YahooFinanceJapanAdapter",
    
    # EDINET adapter
    "EDINETAdapter",
    
    # EDINET setup utilities
    "create_edinet_config",
    "setup_edinet_adapter",
    "setup_edinet_with_registry",
    "get_edinet_production_config",
    "get_edinet_development_config",
    "validate_edinet_config",
    "test_edinet_connection",
    "setup_edinet_from_environment",
    
    # Yahoo Finance setup utilities
    "create_yahoo_finance_config",
    "setup_yahoo_finance_adapter",
    "setup_yahoo_finance_fallback",
    "get_yahoo_finance_conservative_config",
    "validate_yahoo_finance_config",
    "test_yahoo_finance_connection",
    "setup_yahoo_finance_from_environment",
    
    # Alpha Vantage setup utilities
    "create_alpha_vantage_config",
    "setup_alpha_vantage_adapter",
    "setup_alpha_vantage_with_fallback",
    "get_alpha_vantage_premium_config",
    "validate_alpha_vantage_config",
    "test_alpha_vantage_connection",
    "setup_from_environment"
]