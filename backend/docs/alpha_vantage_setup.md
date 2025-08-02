# Alpha Vantage Stock Price Adapter

This document describes how to set up and use the Alpha Vantage adapter for stock price data in the Japanese Stock Analysis Platform.

## Overview

The Alpha Vantage adapter provides real-time and historical stock price data through the Alpha Vantage API. It supports:

- Current stock prices (global quotes)
- Historical price data (daily, weekly, monthly)
- Stock symbol search
- Rate limiting and cost tracking
- Automatic failover and health monitoring

## Prerequisites

1. **Alpha Vantage API Key**: Sign up at [Alpha Vantage](https://www.alphavantage.co/support/#api-key) to get a free API key
2. **Python Dependencies**: The adapter requires `aiohttp` for async HTTP requests

## Quick Start

### 1. Environment Setup

Set your Alpha Vantage API key as an environment variable:

```bash
export ALPHA_VANTAGE_API_KEY="your_api_key_here"
```

### 2. Basic Usage

```python
from app.adapters import setup_alpha_vantage_adapter

# Set up adapter with default configuration
adapter = setup_alpha_vantage_adapter()

# Get current stock price
price_data = await adapter.get_current_price("AAPL")
print(f"AAPL current price: ${price_data['price']}")

# Get historical data
from datetime import datetime, timedelta
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=30)

historical_data = await adapter.get_historical_prices(
    "AAPL", start_date, end_date, "1d"
)
print(f"Retrieved {len(historical_data)} historical records")

# Search for symbols
search_results = await adapter.search_symbols("Apple")
for result in search_results:
    print(f"{result['symbol']}: {result['name']}")
```

### 3. Automatic Setup from Environment

The adapter can be automatically configured from environment variables:

```python
from app.adapters import setup_from_environment

# This will automatically configure based on environment variables
adapter = setup_from_environment()
if adapter:
    print("Alpha Vantage adapter configured successfully")
else:
    print("No API key found in environment")
```

## Configuration Options

### Free Tier Configuration

```python
from app.adapters import create_alpha_vantage_config, setup_alpha_vantage_adapter

config = create_alpha_vantage_config(
    api_key="your_api_key",
    requests_per_minute=5,      # Free tier limit
    requests_per_day=500,       # Free tier limit
    timeout=30,                 # Request timeout in seconds
    max_retries=3,              # Maximum retry attempts
    retry_delay=1.0,            # Delay between retries
    cost_per_request=0.0,       # Free tier
    monthly_budget=0.0          # No budget limit
)

adapter = setup_alpha_vantage_adapter(
    name="alpha_vantage_primary",
    priority=10,
    config=config
)
```

### Premium Plan Configuration

```python
from app.adapters import get_alpha_vantage_premium_config, setup_alpha_vantage_adapter

# Premium plan configuration
config = get_alpha_vantage_premium_config(
    api_key="your_premium_api_key",
    plan_type="premium"  # Options: premium, professional, enterprise
)

adapter = setup_alpha_vantage_adapter(config=config)
```

### Environment Variables

The following environment variables are supported:

| Variable | Description | Default |
|----------|-------------|---------|
| `ALPHA_VANTAGE_API_KEY` | API key (required) | None |
| `ALPHA_VANTAGE_PLAN` | Plan type (free, premium, professional, enterprise) | free |
| `ALPHA_VANTAGE_REQUESTS_PER_MINUTE` | Custom rate limit per minute | Plan default |
| `ALPHA_VANTAGE_REQUESTS_PER_DAY` | Custom rate limit per day | Plan default |

## Failover Setup

Set up primary and fallback adapters for high availability:

```python
from app.adapters import setup_alpha_vantage_with_fallback

primary, fallback = setup_alpha_vantage_with_fallback(
    primary_api_key="primary_key",
    fallback_api_key="fallback_key"  # Optional
)

# Both adapters are automatically registered with the global registry
# Primary has priority 10, fallback has priority 20
```

## Rate Limiting

The adapter automatically handles Alpha Vantage rate limits:

### Free Tier Limits
- 5 requests per minute
- 500 requests per day

### Premium Tier Limits
- **Premium**: 75 requests/minute, 75,000 requests/day
- **Professional**: 300 requests/minute, 300,000 requests/day
- **Enterprise**: 600 requests/minute, 600,000 requests/day

### Rate Limit Handling

```python
from app.adapters.base import RateLimitExceededError

try:
    price_data = await adapter.get_current_price("AAPL")
except RateLimitExceededError as e:
    print(f"Rate limit exceeded: {e}")
    print(f"Retry after: {e.retry_after}")
```

## Health Monitoring

The adapter includes built-in health monitoring:

```python
# Check adapter health
health = await adapter.health_check()
print(f"Status: {health.status.value}")
print(f"Response time: {health.response_time_ms}ms")

if health.error_message:
    print(f"Error: {health.error_message}")

# Get rate limit information
rate_limit = await adapter.get_rate_limit_info()
print(f"Requests per minute: {rate_limit.requests_per_minute}")
print(f"Current usage: {rate_limit.current_usage}")

# Get cost information
cost_info = await adapter.get_cost_info()
print(f"Cost per request: ${cost_info.cost_per_request}")
print(f"Monthly usage: ${cost_info.current_monthly_usage}")
```

## Symbol Normalization

The adapter automatically normalizes symbols for different markets:

```python
# Japanese stocks
adapter._normalize_symbol("7203.T")    # Returns "7203.TYO"
adapter._normalize_symbol("7203.TYO")  # Returns "7203.TYO"

# US stocks
adapter._normalize_symbol("AAPL")      # Returns "AAPL"
adapter._normalize_symbol("aapl")      # Returns "AAPL"
```

## Data Format

### Current Price Data

```python
{
    "symbol": "AAPL",
    "price": 152.50,
    "open": 150.00,
    "high": 155.00,
    "low": 149.00,
    "volume": 50000000,
    "change": 1.50,
    "change_percent": 0.99,
    "previous_close": 151.00,
    "trading_day": "2024-01-15",
    "timestamp": "2024-01-15T20:00:00",
    "currency": "USD",
    "market_status": "closed"
}
```

### Historical Price Data

```python
[
    {
        "symbol": "AAPL",
        "date": "2024-01-15T00:00:00",
        "open": 150.00,
        "high": 155.00,
        "low": 149.00,
        "close": 152.50,
        "volume": 50000000,
        "adjusted_close": 152.50
    },
    # ... more records
]
```

### Symbol Search Results

```python
[
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "Equity",
        "region": "United States",
        "market_open": "09:30",
        "market_close": "16:00",
        "timezone": "UTC-05",
        "currency": "USD",
        "match_score": 1.0
    },
    # ... more results
]
```

## Error Handling

The adapter provides specific error types for different scenarios:

```python
from app.adapters.base import (
    RateLimitExceededError,
    DataSourceUnavailableError,
    InvalidDataError
)

try:
    price_data = await adapter.get_current_price("INVALID_SYMBOL")
except RateLimitExceededError:
    # Handle rate limiting
    pass
except DataSourceUnavailableError:
    # Handle API unavailability
    pass
except InvalidDataError:
    # Handle invalid API responses
    pass
```

## Testing Connection

Test your Alpha Vantage configuration:

```python
from app.adapters import test_alpha_vantage_connection

config = {"api_key": "your_api_key"}
results = await test_alpha_vantage_connection(config)

print(f"Config valid: {results['config_valid']}")
print(f"Connection successful: {results['connection_successful']}")
print(f"Health check passed: {results['health_check_passed']}")

if results['error_message']:
    print(f"Error: {results['error_message']}")
```

## Best Practices

### 1. Use Connection Pooling

The adapter automatically manages HTTP connections, but you should properly close sessions:

```python
async with AlphaVantageAdapter(config=config) as adapter:
    # Use adapter
    price_data = await adapter.get_current_price("AAPL")
# Session is automatically closed
```

### 2. Handle Rate Limits Gracefully

```python
import asyncio
from app.adapters.base import RateLimitExceededError

async def get_price_with_retry(adapter, symbol, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await adapter.get_current_price(symbol)
        except RateLimitExceededError as e:
            if attempt < max_retries - 1:
                # Wait until rate limit resets
                if e.retry_after:
                    wait_time = (e.retry_after - datetime.utcnow()).total_seconds()
                    await asyncio.sleep(max(wait_time, 60))  # Wait at least 1 minute
                else:
                    await asyncio.sleep(60)  # Default wait
            else:
                raise
```

### 3. Monitor Costs

```python
async def monitor_usage(adapter):
    cost_info = await adapter.get_cost_info()
    
    if cost_info.monthly_budget > 0:
        usage_percent = (cost_info.current_monthly_usage / cost_info.monthly_budget) * 100
        
        if usage_percent > 80:
            print(f"Warning: {usage_percent:.1f}% of monthly budget used")
        elif usage_percent > 95:
            print("Critical: Approaching monthly budget limit")
```

### 4. Use Failover Configuration

```python
# Set up multiple adapters for redundancy
primary, fallback = setup_alpha_vantage_with_fallback(
    primary_api_key="primary_key",
    fallback_api_key="fallback_key"
)

# The data source registry will automatically failover
# if the primary adapter fails
```

## Troubleshooting

### Common Issues

1. **Invalid API Key**
   ```
   Error: Alpha Vantage API error: Invalid API call
   ```
   - Verify your API key is correct
   - Check if your API key is active

2. **Rate Limit Exceeded**
   ```
   Error: Alpha Vantage rate limit exceeded
   ```
   - Wait for rate limit to reset
   - Consider upgrading to a premium plan
   - Implement proper retry logic

3. **Symbol Not Found**
   ```
   Error: Alpha Vantage API error: Invalid API call
   ```
   - Verify the symbol format
   - Use symbol search to find correct symbols

4. **Connection Timeout**
   ```
   Error: Alpha Vantage connection error: timeout
   ```
   - Check internet connectivity
   - Increase timeout in configuration
   - Verify Alpha Vantage API status

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

logging.getLogger('app.adapters.alpha_vantage_adapter').setLevel(logging.DEBUG)
```

### Health Check

Use the health check endpoint to verify adapter status:

```python
health = await adapter.health_check()
print(f"Status: {health.status.value}")
print(f"Response time: {health.response_time_ms}ms")
print(f"Last check: {health.last_check}")

if health.metadata:
    print(f"Requests today: {health.metadata.get('requests_today', 0)}")
    print(f"Requests this minute: {health.metadata.get('requests_this_minute', 0)}")
```

## Integration with Data Source Registry

The Alpha Vantage adapter integrates seamlessly with the data source registry:

```python
from app.adapters import registry, DataSourceType

# Get all stock price adapters (including Alpha Vantage)
stock_adapters = registry.get_adapters_by_type(DataSourceType.STOCK_PRICE)

# Get the primary (highest priority) adapter
primary_adapter = registry.get_primary_adapter(DataSourceType.STOCK_PRICE)

# Execute with automatic failover
async def get_stock_price(symbol):
    async def operation(adapter):
        return await adapter.get_current_price(symbol)
    
    return await registry.execute_with_failover(
        DataSourceType.STOCK_PRICE,
        operation
    )
```

This integration provides automatic failover, health monitoring, and centralized management of all data source adapters.