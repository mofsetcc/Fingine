# Redis Caching Layer Implementation

## Overview

This document describes the Redis caching layer implementation for Project Kessan. The caching system provides multi-layer caching with intelligent TTL policies, automatic failover, and comprehensive monitoring.

## Architecture

### Core Components

1. **RedisCache** - Low-level Redis client wrapper
2. **CacheManager** - High-level cache operations for business entities
3. **CacheService** - Service layer with business logic integration
4. **CacheKeyBuilder** - Standardized cache key generation
5. **CacheTTLPolicy** - TTL policies for different data types

### Cache Key Strategy

Cache keys follow a hierarchical naming convention:

```
{data_type}:{entity_id}:{additional_params}
```

Examples:
- `stock_price:7203:latest`
- `financial_data:7203:quarterly:Q3`
- `ai_analysis:7203:short_term`
- `news_data:7203:earnings`
- `user_session:user123`
- `api_quota:user123:daily`

### TTL Policies

Different data types have different Time-To-Live (TTL) policies:

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Stock Price | 5 minutes (300s) | Real-time data needs frequent updates |
| Financial Data | 24 hours (86400s) | Financial reports change infrequently |
| News Data | 1 hour (3600s) | News updates regularly but not constantly |
| AI Analysis | 6 hours (21600s) | Analysis is expensive to generate |
| User Session | 30 minutes (1800s) | Security and user experience balance |
| API Quota | 24 hours (86400s) | Daily quota tracking |
| Market Data | 5 minutes (300s) | Market indices update frequently |

## Usage Examples

### Basic Cache Operations

```python
from app.core.cache import cache, CacheKeyType

# Connect to Redis
await cache.connect()

# Set a value with automatic TTL
await cache.set("my_key", {"data": "value"}, key_type=CacheKeyType.STOCK_PRICE)

# Get a value
result = await cache.get("my_key")

# Delete a value
await cache.delete("my_key")

# Check if key exists
exists = await cache.exists("my_key")

# Get TTL
ttl = await cache.ttl("my_key")
```

### Using Cache Manager

```python
from app.core.cache import cache_manager

# Cache stock price data
await cache_manager.set_stock_price("7203", {
    "open": 2500.0,
    "high": 2550.0,
    "low": 2480.0,
    "close": 2520.0,
    "volume": 1000000
})

# Retrieve cached stock price
price_data = await cache_manager.get_stock_price("7203")

# Cache financial data
await cache_manager.set_financial_data("7203", "quarterly", "Q3", {
    "revenue": 30000000000,
    "operating_income": 2500000000,
    "net_income": 2000000000
})

# Invalidate all cache entries for a stock
deleted_count = await cache_manager.invalidate_stock_cache("7203")
```

### Using Cache Service

```python
from app.services.cache_service import cache_service

# Get or set pattern with automatic caching
async def fetch_expensive_data():
    # Simulate expensive operation
    return {"result": "expensive_computation"}

result = await cache_service.get_or_set(
    "expensive_operation:key",
    fetch_expensive_data,
    key_type=CacheKeyType.AI_ANALYSIS
)

# Track API quota usage
usage = await cache_service.track_api_quota("user123", "daily")
current_usage = await cache_service.get_api_quota_usage("user123", "daily")

# Cache user session
await cache_service.cache_user_session("user123", {
    "preferences": {"theme": "dark"},
    "last_activity": "2024-01-15T10:00:00Z"
})
```

### Service Integration Example

```python
from app.services.cache_service import cache_service, CacheKeyType

class MyService:
    async def get_stock_analysis(self, ticker: str) -> dict:
        """Get stock analysis with caching."""
        
        # Define fetch function for cache miss
        async def fetch_analysis():
            # Expensive AI analysis operation
            return await self._generate_ai_analysis(ticker)
        
        # Use cache service
        return await cache_service.get_ai_analysis_cached(
            ticker,
            "comprehensive",
            fetch_analysis
        )
    
    async def search_stocks(self, query: str) -> list:
        """Search stocks with caching."""
        cache_key = f"stock_search:{hash(query)}"
        
        async def fetch_search_results():
            return await self._perform_database_search(query)
        
        return await cache_service.get_or_set(
            cache_key,
            fetch_search_results,
            ttl=300  # 5 minutes for search results
        )
```

### Cache Decorator

```python
from app.services.cache_service import cache_result, CacheKeyType

@cache_result(
    key_func=lambda ticker, analysis_type: f"ai_analysis:{ticker}:{analysis_type}",
    key_type=CacheKeyType.AI_ANALYSIS
)
async def generate_ai_analysis(ticker: str, analysis_type: str) -> dict:
    """Generate AI analysis with automatic caching."""
    # Expensive AI operation
    return {"analysis": "result"}

# Usage
result = await generate_ai_analysis("7203", "short_term")  # Cache miss
result = await generate_ai_analysis("7203", "short_term")  # Cache hit
```

## Configuration

### Environment Variables

```bash
# Redis connection
REDIS_URL=redis://localhost:6379

# Optional Redis cluster configuration
REDIS_CLUSTER_NODES=redis://node1:6379,redis://node2:6379,redis://node3:6379
```

### Application Startup

The cache is automatically initialized when the FastAPI application starts:

```python
# In app/main.py
@app.on_event("startup")
async def startup_event():
    from app.core.cache import cache
    await cache.connect()

@app.on_event("shutdown")
async def shutdown_event():
    from app.core.cache import cache
    await cache.disconnect()
```

## Monitoring and Health Checks

### Health Check Endpoint

The cache health is included in the system health check:

```bash
GET /health/detailed
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "redis": {
      "status": "healthy",
      "connected": true,
      "hit_rate_percent": 85.5,
      "memory_usage": "256MB",
      "total_commands": 10000,
      "uptime_seconds": 86400,
      "connected_clients": 5
    }
  }
}
```

### Cache Statistics

```python
from app.services.cache_service import cache_service

# Get comprehensive cache statistics
stats = await cache_service.get_cache_statistics()
print(f"Cache hit rate: {stats['health']['hit_rate_percent']}%")
print(f"Memory usage: {stats['health']['memory_usage']}")
print(f"Key counts: {stats['key_counts']}")
```

## Error Handling

The cache system is designed to fail gracefully:

1. **Connection Failures**: If Redis is unavailable, operations return `None` or `False` instead of raising exceptions
2. **Serialization Errors**: Automatic fallback between JSON and pickle serialization
3. **Memory Pressure**: Automatic TTL enforcement prevents memory overflow
4. **Network Issues**: Connection retry logic with exponential backoff

### Example Error Handling

```python
# Cache operations never break your application
cached_data = await cache.get("some_key")
if cached_data is None:
    # Cache miss or error - fetch from primary source
    data = await fetch_from_database()
    # Try to cache for next time (fails silently if Redis is down)
    await cache.set("some_key", data)
else:
    data = cached_data
```

## Performance Optimization

### Batch Operations

```python
# Batch get multiple keys
keys = ["stock_price:7203", "stock_price:6758", "stock_price:9984"]
pipeline_results = await cache.pipeline_get(keys)

# Batch set multiple keys
data = {
    "stock_price:7203": {"price": 2500},
    "stock_price:6758": {"price": 15000},
    "stock_price:9984": {"price": 3000}
}
await cache.pipeline_set(data)
```

### Memory Management

```python
# Clean up expired keys
await cache.cleanup_expired()

# Get memory usage
memory_info = await cache.get_memory_info()

# Flush specific patterns
deleted_count = await cache.flush_pattern("stock_price:*")
```

## Testing

### Unit Tests

Run the cache unit tests:

```bash
cd backend
python test_cache_unit.py
```

### Integration Tests

For integration tests with a running Redis instance:

```bash
cd backend
python test_cache_integration.py
```

### Mock Testing

For testing without Redis:

```python
from unittest.mock import AsyncMock, patch

@patch('app.core.cache.cache')
async def test_my_service(mock_cache):
    mock_cache.get.return_value = {"cached": "data"}
    mock_cache.set.return_value = True
    
    # Your test code here
    result = await my_cached_function()
    assert result == {"cached": "data"}
```

## Best Practices

### 1. Cache Key Naming

- Use consistent, hierarchical naming
- Include version information when needed
- Use the CacheKeyBuilder for standardization

```python
# Good
key = CacheKeyBuilder.build_stock_price_key("7203", "2024-01-15")

# Avoid
key = f"stock_{ticker}_price_{date}"
```

### 2. TTL Selection

- Use appropriate TTL for your data freshness requirements
- Consider business hours for financial data
- Use shorter TTLs for frequently changing data

### 3. Error Handling

- Always handle cache misses gracefully
- Don't let cache failures break your application
- Log cache errors for monitoring

### 4. Memory Management

- Monitor cache memory usage
- Use appropriate data structures
- Clean up expired keys regularly

### 5. Testing

- Test both cache hit and miss scenarios
- Mock cache operations in unit tests
- Include cache performance in integration tests

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check if Redis is running and accessible
2. **Memory Errors**: Monitor Redis memory usage and adjust TTLs
3. **Slow Performance**: Check network latency and Redis configuration
4. **Serialization Errors**: Ensure data is JSON-serializable or use pickle

### Debug Commands

```python
# Check cache connection
health = await cache_manager.get_cache_health()
print(f"Cache status: {health['status']}")

# List all keys matching pattern
keys = await cache.keys("stock_price:*")
print(f"Found {len(keys)} stock price keys")

# Get key information
ttl = await cache.ttl("stock_price:7203")
exists = await cache.exists("stock_price:7203")
print(f"Key TTL: {ttl}, Exists: {exists}")
```

## Future Enhancements

1. **Redis Cluster Support**: Horizontal scaling across multiple Redis nodes
2. **Cache Warming**: Pre-populate cache with frequently accessed data
3. **Intelligent Eviction**: Custom eviction policies based on access patterns
4. **Compression**: Compress large cache values to save memory
5. **Metrics Integration**: Integration with Prometheus/Grafana for monitoring