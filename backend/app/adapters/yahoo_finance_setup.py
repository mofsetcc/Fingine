"""Yahoo Finance adapter setup utilities."""

import logging
from typing import Dict, Optional, Any

from .yahoo_finance_adapter import YahooFinanceJapanAdapter
from .registry import registry

logger = logging.getLogger(__name__)


def create_yahoo_finance_config(
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    delay_minutes: int = 15,
    requests_per_minute: int = 30,
    requests_per_hour: int = 1000,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create configuration for Yahoo Finance adapter.
    
    Args:
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        delay_minutes: Data delay for free tier in minutes
        requests_per_minute: Rate limit per minute
        requests_per_hour: Rate limit per hour
        user_agent: Custom user agent string
        
    Returns:
        Configuration dictionary
    """
    config = {
        "timeout": timeout,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "delay_minutes": delay_minutes,
        "requests_per_minute": requests_per_minute,
        "requests_per_hour": requests_per_hour
    }
    
    if user_agent:
        config["user_agent"] = user_agent
    
    return config


def setup_yahoo_finance_adapter(
    name: str = "yahoo_finance_japan",
    priority: int = 20,
    config: Optional[Dict[str, Any]] = None,
    register_adapter: bool = True
) -> YahooFinanceJapanAdapter:
    """
    Set up Yahoo Finance Japan adapter.
    
    Args:
        name: Adapter name
        priority: Adapter priority (higher number = lower priority)
        config: Configuration dictionary (if None, will create default config)
        register_adapter: Whether to register the adapter with the global registry
        
    Returns:
        Configured Yahoo Finance adapter
        
    Raises:
        Exception: If adapter setup fails
    """
    try:
        # Create default config if none provided
        if config is None:
            config = create_yahoo_finance_config()
        
        # Create adapter
        adapter = YahooFinanceJapanAdapter(name=name, priority=priority, config=config)
        
        if register_adapter:
            registry.register_adapter(adapter)
            logger.info(f"Registered Yahoo Finance adapter: {name} (priority: {priority})")
        
        return adapter
        
    except Exception as e:
        logger.error(f"Failed to setup Yahoo Finance adapter: {e}")
        raise


def setup_yahoo_finance_fallback(
    primary_adapter_name: str = "yahoo_finance_japan",
    fallback_adapter_name: str = "yahoo_finance_japan_backup",
    register_adapters: bool = True
) -> tuple[YahooFinanceJapanAdapter, YahooFinanceJapanAdapter]:
    """
    Set up primary and fallback Yahoo Finance adapters.
    
    Args:
        primary_adapter_name: Name for primary adapter
        fallback_adapter_name: Name for fallback adapter
        register_adapters: Whether to register adapters with global registry
        
    Returns:
        Tuple of (primary_adapter, fallback_adapter)
    """
    adapters = []
    
    # Setup primary adapter
    try:
        primary_config = create_yahoo_finance_config(
            requests_per_minute=30,
            requests_per_hour=1000
        )
        
        primary_adapter = setup_yahoo_finance_adapter(
            name=primary_adapter_name,
            priority=20,
            config=primary_config,
            register_adapter=register_adapters
        )
        adapters.append(primary_adapter)
        
    except Exception as e:
        logger.error(f"Failed to setup primary Yahoo Finance adapter: {e}")
        raise
    
    # Setup fallback adapter with more conservative limits
    try:
        fallback_config = create_yahoo_finance_config(
            requests_per_minute=15,  # More conservative
            requests_per_hour=500,
            retry_delay=2.0  # Longer delay
        )
        
        fallback_adapter = setup_yahoo_finance_adapter(
            name=fallback_adapter_name,
            priority=30,  # Lower priority
            config=fallback_config,
            register_adapter=register_adapters
        )
        adapters.append(fallback_adapter)
        
    except Exception as e:
        logger.warning(f"Failed to setup fallback Yahoo Finance adapter: {e}")
        # Don't raise error for fallback adapter failure
        return primary_adapter, None
    
    logger.info("Yahoo Finance adapters setup complete (primary + fallback)")
    return primary_adapter, fallback_adapter


def get_yahoo_finance_conservative_config() -> Dict[str, Any]:
    """
    Get conservative configuration for Yahoo Finance to avoid rate limiting.
    
    Returns:
        Conservative configuration dictionary
    """
    return create_yahoo_finance_config(
        timeout=45,  # Longer timeout
        max_retries=2,  # Fewer retries
        retry_delay=2.0,  # Longer delay
        requests_per_minute=15,  # Conservative rate limit
        requests_per_hour=500,
        delay_minutes=15
    )


def validate_yahoo_finance_config(config: Dict[str, Any]) -> bool:
    """
    Validate Yahoo Finance adapter configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = [
        "timeout", "max_retries", "retry_delay", 
        "delay_minutes", "requests_per_minute", "requests_per_hour"
    ]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required configuration field: {field}")
    
    # Validate numeric fields
    if config["timeout"] <= 0:
        raise ValueError("Timeout must be positive")
    
    if config["max_retries"] < 0:
        raise ValueError("Max retries cannot be negative")
    
    if config["retry_delay"] < 0:
        raise ValueError("Retry delay cannot be negative")
    
    if config["delay_minutes"] < 0:
        raise ValueError("Delay minutes cannot be negative")
    
    if config["requests_per_minute"] <= 0:
        raise ValueError("Requests per minute must be positive")
    
    if config["requests_per_hour"] <= 0:
        raise ValueError("Requests per hour must be positive")
    
    # Validate rate limit consistency
    if config["requests_per_hour"] < config["requests_per_minute"]:
        raise ValueError("Hourly rate limit cannot be less than minute rate limit")
    
    return True


async def test_yahoo_finance_connection(
    adapter: Optional[YahooFinanceJapanAdapter] = None
) -> bool:
    """
    Test Yahoo Finance API connection.
    
    Args:
        adapter: Yahoo Finance adapter to test (if None, creates temporary adapter)
        
    Returns:
        True if connection successful
    """
    test_adapter = adapter
    
    if test_adapter is None:
        # Create temporary adapter for testing
        config = create_yahoo_finance_config()
        test_adapter = YahooFinanceJapanAdapter(config=config)
    
    try:
        # Test health check
        health = await test_adapter.health_check()
        
        if health.status.value in ["healthy", "degraded"]:
            logger.info("Yahoo Finance connection test successful")
            return True
        else:
            logger.warning(f"Yahoo Finance connection test failed: {health.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"Yahoo Finance connection test error: {e}")
        return False
    
    finally:
        # Clean up temporary adapter
        if adapter is None and test_adapter:
            await test_adapter._close_session()


def setup_from_environment() -> Optional[YahooFinanceJapanAdapter]:
    """
    Set up Yahoo Finance adapter from environment variables.
    
    Environment variables:
        YAHOO_FINANCE_TIMEOUT: Request timeout (default: 30)
        YAHOO_FINANCE_MAX_RETRIES: Max retries (default: 3)
        YAHOO_FINANCE_RETRY_DELAY: Retry delay (default: 1.0)
        YAHOO_FINANCE_DELAY_MINUTES: Data delay minutes (default: 15)
        YAHOO_FINANCE_REQUESTS_PER_MINUTE: Rate limit per minute (default: 30)
        YAHOO_FINANCE_REQUESTS_PER_HOUR: Rate limit per hour (default: 1000)
        YAHOO_FINANCE_USER_AGENT: Custom user agent
        YAHOO_FINANCE_ENABLED: Enable adapter (default: true)
        
    Returns:
        Configured adapter or None if disabled/failed
    """
    import os
    
    try:
        # Check if adapter is enabled
        enabled = os.getenv("YAHOO_FINANCE_ENABLED", "true").lower() == "true"
        if not enabled:
            logger.info("Yahoo Finance adapter disabled by environment variable")
            return None
        
        # Build configuration from environment
        config = create_yahoo_finance_config(
            timeout=int(os.getenv("YAHOO_FINANCE_TIMEOUT", "30")),
            max_retries=int(os.getenv("YAHOO_FINANCE_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("YAHOO_FINANCE_RETRY_DELAY", "1.0")),
            delay_minutes=int(os.getenv("YAHOO_FINANCE_DELAY_MINUTES", "15")),
            requests_per_minute=int(os.getenv("YAHOO_FINANCE_REQUESTS_PER_MINUTE", "30")),
            requests_per_hour=int(os.getenv("YAHOO_FINANCE_REQUESTS_PER_HOUR", "1000")),
            user_agent=os.getenv("YAHOO_FINANCE_USER_AGENT")
        )
        
        # Validate configuration
        validate_yahoo_finance_config(config)
        
        # Create and register adapter
        adapter = setup_yahoo_finance_adapter(config=config)
        logger.info("Yahoo Finance adapter setup from environment")
        
        return adapter
        
    except Exception as e:
        logger.error(f"Failed to setup Yahoo Finance adapter from environment: {e}")
        return None