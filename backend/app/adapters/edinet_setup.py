"""EDINET adapter setup utilities."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .base import DataSourceType, HealthStatus
from .edinet_adapter import EDINETAdapter
from .registry import registry

logger = logging.getLogger(__name__)


def create_edinet_config(
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: int = 2,
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    cache_ttl: int = 86400,
) -> Dict[str, Any]:
    """
    Create EDINET adapter configuration.

    Args:
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        requests_per_minute: Rate limit per minute
        requests_per_hour: Rate limit per hour
        cache_ttl: Cache TTL for documents in seconds

    Returns:
        Configuration dictionary
    """
    return {
        "timeout": timeout,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "requests_per_minute": requests_per_minute,
        "requests_per_hour": requests_per_hour,
        "cache_ttl": cache_ttl,
    }


def setup_edinet_adapter(
    name: str = "edinet", priority: int = 10, config: Optional[Dict[str, Any]] = None
) -> EDINETAdapter:
    """
    Set up EDINET adapter with configuration.

    Args:
        name: Adapter name
        priority: Adapter priority (lower = higher priority)
        config: Configuration dictionary

    Returns:
        Configured EDINET adapter

    Raises:
        ValueError: If configuration is invalid
    """
    if config is None:
        config = create_edinet_config()

    # Validate configuration
    validate_edinet_config(config)

    # Create adapter
    adapter = EDINETAdapter(name=name, priority=priority, config=config)

    logger.info(f"Created EDINET adapter '{name}' with priority {priority}")

    return adapter


def setup_edinet_with_registry(
    name: str = "edinet",
    priority: int = 10,
    config: Optional[Dict[str, Any]] = None,
    auto_register: bool = True,
) -> EDINETAdapter:
    """
    Set up EDINET adapter and optionally register it.

    Args:
        name: Adapter name
        priority: Adapter priority
        config: Configuration dictionary
        auto_register: Whether to automatically register with global registry

    Returns:
        Configured EDINET adapter
    """
    adapter = setup_edinet_adapter(name, priority, config)

    if auto_register:
        registry.register_adapter(adapter)
        logger.info(f"Registered EDINET adapter '{name}' with global registry")

    return adapter


def get_edinet_production_config() -> Dict[str, Any]:
    """
    Get production-ready EDINET configuration.

    Returns:
        Production configuration dictionary
    """
    return create_edinet_config(
        timeout=30,
        max_retries=3,
        retry_delay=2,
        requests_per_minute=50,  # Conservative rate limit
        requests_per_hour=800,  # Conservative rate limit
        cache_ttl=86400,  # 24 hours
    )


def get_edinet_development_config() -> Dict[str, Any]:
    """
    Get development-friendly EDINET configuration.

    Returns:
        Development configuration dictionary
    """
    return create_edinet_config(
        timeout=10,
        max_retries=2,
        retry_delay=1,
        requests_per_minute=30,  # Lower rate limit for development
        requests_per_hour=500,  # Lower rate limit for development
        cache_ttl=3600,  # 1 hour
    )


def validate_edinet_config(config: Dict[str, Any]) -> None:
    """
    Validate EDINET adapter configuration.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = [
        "timeout",
        "max_retries",
        "retry_delay",
        "requests_per_minute",
        "requests_per_hour",
        "cache_ttl",
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required configuration field: {field}")

    # Validate numeric fields
    numeric_fields = {
        "timeout": (1, 300),
        "max_retries": (0, 10),
        "retry_delay": (0, 60),
        "requests_per_minute": (1, 1000),
        "requests_per_hour": (1, 10000),
        "cache_ttl": (60, 604800),  # 1 minute to 1 week
    }

    for field, (min_val, max_val) in numeric_fields.items():
        value = config[field]
        if not isinstance(value, (int, float)) or value < min_val or value > max_val:
            raise ValueError(
                f"Invalid {field}: {value}. Must be between {min_val} and {max_val}"
            )

    logger.info("EDINET configuration validation passed")


async def test_edinet_connection(
    adapter: Optional[EDINETAdapter] = None, config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Test EDINET API connection.

    Args:
        adapter: Existing adapter to test (optional)
        config: Configuration for new adapter (optional)

    Returns:
        Test results dictionary
    """
    if adapter is None:
        if config is None:
            config = get_edinet_development_config()
        adapter = setup_edinet_adapter("test_edinet", config=config)

    test_results = {
        "adapter_name": adapter.name,
        "connection_successful": False,
        "health_status": None,
        "response_time_ms": None,
        "error_message": None,
        "test_timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Test health check
        health_check = await adapter.health_check()

        test_results.update(
            {
                "connection_successful": health_check.status == HealthStatus.HEALTHY,
                "health_status": health_check.status.value,
                "response_time_ms": health_check.response_time_ms,
                "error_message": health_check.error_message,
            }
        )

        # Test document search if health check passed
        if health_check.status == HealthStatus.HEALTHY:
            try:
                # Search for recent documents
                date_from = datetime.utcnow() - timedelta(days=7)
                documents = await adapter._search_documents(date_from=date_from)

                test_results["documents_found"] = len(documents)
                test_results["sample_document"] = (
                    {
                        "doc_id": documents[0].doc_id,
                        "filer_name": documents[0].filer_name,
                        "doc_type": documents[0].doc_type_code,
                    }
                    if documents
                    else None
                )

            except Exception as e:
                test_results["search_error"] = str(e)

        logger.info(
            f"EDINET connection test completed: {test_results['connection_successful']}"
        )

    except Exception as e:
        test_results.update({"connection_successful": False, "error_message": str(e)})
        logger.error(f"EDINET connection test failed: {e}")

    finally:
        # Clean up test adapter
        if adapter and hasattr(adapter, "_close_session"):
            await adapter._close_session()

    return test_results


def setup_from_environment() -> Optional[EDINETAdapter]:
    """
    Set up EDINET adapter from environment variables.

    Note: EDINET is a free service, so no API key is required.
    Environment variables can be used to override default configuration.

    Returns:
        Configured EDINET adapter or None if setup fails
    """
    import os

    try:
        # Get configuration from environment with defaults
        config = create_edinet_config(
            timeout=int(os.getenv("EDINET_TIMEOUT", "30")),
            max_retries=int(os.getenv("EDINET_MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("EDINET_RETRY_DELAY", "2")),
            requests_per_minute=int(os.getenv("EDINET_REQUESTS_PER_MINUTE", "60")),
            requests_per_hour=int(os.getenv("EDINET_REQUESTS_PER_HOUR", "1000")),
            cache_ttl=int(os.getenv("EDINET_CACHE_TTL", "86400")),
        )

        # Determine priority from environment
        priority = int(os.getenv("EDINET_PRIORITY", "10"))

        # Create and register adapter
        adapter = setup_edinet_with_registry(
            name="edinet", priority=priority, config=config, auto_register=True
        )

        logger.info("EDINET adapter set up from environment variables")
        return adapter

    except Exception as e:
        logger.error(f"Failed to set up EDINET adapter from environment: {e}")
        return None


def create_edinet_fallback_chain() -> list[EDINETAdapter]:
    """
    Create a fallback chain of EDINET adapters with different configurations.

    This is useful for redundancy, though EDINET is typically reliable.

    Returns:
        List of EDINET adapters with different priorities
    """
    adapters = []

    # Primary adapter with production config
    primary_adapter = setup_edinet_adapter(
        name="edinet_primary", priority=10, config=get_edinet_production_config()
    )
    adapters.append(primary_adapter)

    # Secondary adapter with more conservative settings
    secondary_config = get_edinet_production_config()
    secondary_config.update(
        {"requests_per_minute": 30, "requests_per_hour": 500, "retry_delay": 3}
    )

    secondary_adapter = setup_edinet_adapter(
        name="edinet_secondary", priority=20, config=secondary_config
    )
    adapters.append(secondary_adapter)

    logger.info(f"Created EDINET fallback chain with {len(adapters)} adapters")
    return adapters


def register_edinet_fallback_chain() -> list[EDINETAdapter]:
    """
    Create and register EDINET fallback chain with global registry.

    Returns:
        List of registered EDINET adapters
    """
    adapters = create_edinet_fallback_chain()

    for adapter in adapters:
        registry.register_adapter(adapter)
        logger.info(
            f"Registered EDINET adapter '{adapter.name}' with priority {adapter.priority}"
        )

    return adapters


# Convenience functions for common setups
def setup_edinet_for_production() -> EDINETAdapter:
    """Set up EDINET adapter for production use."""
    return setup_edinet_with_registry(
        name="edinet_production",
        priority=10,
        config=get_edinet_production_config(),
        auto_register=True,
    )


def setup_edinet_for_development() -> EDINETAdapter:
    """Set up EDINET adapter for development use."""
    return setup_edinet_with_registry(
        name="edinet_development",
        priority=10,
        config=get_edinet_development_config(),
        auto_register=True,
    )
