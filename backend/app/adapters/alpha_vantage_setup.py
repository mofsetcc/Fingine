"""Alpha Vantage adapter setup and configuration."""

import logging
import os
from typing import Any, Dict, Optional

from .alpha_vantage_adapter import AlphaVantageAdapter
from .registry import registry

logger = logging.getLogger(__name__)


def create_alpha_vantage_config(
    api_key: Optional[str] = None,
    requests_per_minute: int = 5,
    requests_per_day: int = 500,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    cost_per_request: float = 0.0,
    monthly_budget: float = 0.0,
) -> Dict[str, Any]:
    """
    Create Alpha Vantage adapter configuration.

    Args:
        api_key: Alpha Vantage API key (if None, will try to get from environment)
        requests_per_minute: Rate limit per minute (default: 5 for free tier)
        requests_per_day: Rate limit per day (default: 500 for free tier)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        cost_per_request: Cost per API request (0.0 for free tier)
        monthly_budget: Monthly budget limit

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If API key is not provided and not found in environment
    """
    if api_key is None:
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        raise ValueError(
            "Alpha Vantage API key is required. "
            "Provide it as parameter or set ALPHA_VANTAGE_API_KEY environment variable."
        )

    return {
        "api_key": api_key,
        "requests_per_minute": requests_per_minute,
        "requests_per_day": requests_per_day,
        "timeout": timeout,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "cost_per_request": cost_per_request,
        "monthly_budget": monthly_budget,
    }


def setup_alpha_vantage_adapter(
    name: str = "alpha_vantage_primary",
    priority: int = 10,
    config: Optional[Dict[str, Any]] = None,
    register_adapter: bool = True,
) -> AlphaVantageAdapter:
    """
    Set up Alpha Vantage adapter with configuration.

    Args:
        name: Adapter name
        priority: Adapter priority (lower = higher priority)
        config: Configuration dictionary (if None, will create default config)
        register_adapter: Whether to register the adapter with the global registry

    Returns:
        Configured Alpha Vantage adapter

    Raises:
        ValueError: If configuration is invalid
    """
    try:
        if config is None:
            config = create_alpha_vantage_config()

        adapter = AlphaVantageAdapter(name=name, priority=priority, config=config)

        if register_adapter:
            registry.register_adapter(adapter)
            logger.info(
                f"Registered Alpha Vantage adapter: {name} (priority: {priority})"
            )

        return adapter

    except Exception as e:
        logger.error(f"Failed to setup Alpha Vantage adapter: {e}")
        raise


def setup_alpha_vantage_with_fallback(
    primary_api_key: Optional[str] = None,
    fallback_api_key: Optional[str] = None,
    register_adapters: bool = True,
) -> tuple[AlphaVantageAdapter, Optional[AlphaVantageAdapter]]:
    """
    Set up Alpha Vantage adapters with primary and fallback configuration.

    This is useful when you have multiple API keys or want to set up
    different rate limits for primary and fallback adapters.

    Args:
        primary_api_key: API key for primary adapter
        fallback_api_key: API key for fallback adapter (optional)
        register_adapters: Whether to register adapters with global registry

    Returns:
        Tuple of (primary_adapter, fallback_adapter)
        fallback_adapter will be None if fallback_api_key is not provided
    """
    adapters = []

    # Setup primary adapter
    try:
        primary_config = create_alpha_vantage_config(
            api_key=primary_api_key, requests_per_minute=5, requests_per_day=500
        )

        primary_adapter = setup_alpha_vantage_adapter(
            name="alpha_vantage_primary",
            priority=10,
            config=primary_config,
            register_adapter=register_adapters,
        )
        adapters.append(primary_adapter)

    except Exception as e:
        logger.error(f"Failed to setup primary Alpha Vantage adapter: {e}")
        raise

    # Setup fallback adapter if API key provided
    fallback_adapter = None
    if fallback_api_key:
        try:
            fallback_config = create_alpha_vantage_config(
                api_key=fallback_api_key,
                requests_per_minute=3,  # Lower rate limit for fallback
                requests_per_day=300,
            )

            fallback_adapter = setup_alpha_vantage_adapter(
                name="alpha_vantage_fallback",
                priority=20,  # Lower priority
                config=fallback_config,
                register_adapter=register_adapters,
            )
            adapters.append(fallback_adapter)

        except Exception as e:
            logger.warning(f"Failed to setup fallback Alpha Vantage adapter: {e}")
            # Don't raise error for fallback adapter failure

    return primary_adapter, fallback_adapter


def get_alpha_vantage_premium_config(
    api_key: str, plan_type: str = "premium"
) -> Dict[str, Any]:
    """
    Get configuration for Alpha Vantage premium plans.

    Args:
        api_key: Alpha Vantage API key
        plan_type: Plan type ("premium", "professional", "enterprise")

    Returns:
        Configuration dictionary with appropriate rate limits and costs
    """
    plan_configs = {
        "premium": {
            "requests_per_minute": 75,
            "requests_per_day": 75000,
            "cost_per_request": 0.0005,  # Estimated
            "monthly_budget": 50.0,
        },
        "professional": {
            "requests_per_minute": 300,
            "requests_per_day": 300000,
            "cost_per_request": 0.0003,  # Estimated
            "monthly_budget": 200.0,
        },
        "enterprise": {
            "requests_per_minute": 600,
            "requests_per_day": 600000,
            "cost_per_request": 0.0002,  # Estimated
            "monthly_budget": 500.0,
        },
    }

    if plan_type not in plan_configs:
        raise ValueError(f"Unknown plan type: {plan_type}")

    plan_config = plan_configs[plan_type]

    return create_alpha_vantage_config(
        api_key=api_key,
        requests_per_minute=plan_config["requests_per_minute"],
        requests_per_day=plan_config["requests_per_day"],
        cost_per_request=plan_config["cost_per_request"],
        monthly_budget=plan_config["monthly_budget"],
    )


def validate_alpha_vantage_config(config: Dict[str, Any]) -> bool:
    """
    Validate Alpha Vantage configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["api_key"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required configuration field: {field}")

    # Validate API key format (basic check)
    api_key = config["api_key"]
    if not isinstance(api_key, str) or len(api_key) < 10:
        raise ValueError("Invalid API key format")

    # Validate numeric fields
    numeric_fields = [
        "requests_per_minute",
        "requests_per_day",
        "timeout",
        "max_retries",
        "retry_delay",
        "cost_per_request",
        "monthly_budget",
    ]

    for field in numeric_fields:
        if field in config:
            value = config[field]
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(
                    f"Invalid value for {field}: must be non-negative number"
                )

    # Validate rate limits
    if config.get("requests_per_minute", 0) > config.get("requests_per_day", 0):
        raise ValueError("requests_per_minute cannot exceed requests_per_day")

    return True


async def test_alpha_vantage_connection(
    config: Dict[str, Any], test_symbol: str = "AAPL"
) -> Dict[str, Any]:
    """
    Test Alpha Vantage API connection with given configuration.

    Args:
        config: Alpha Vantage configuration
        test_symbol: Symbol to use for testing

    Returns:
        Test results dictionary
    """
    test_results = {
        "config_valid": False,
        "connection_successful": False,
        "health_check_passed": False,
        "rate_limit_info": None,
        "cost_info": None,
        "error_message": None,
    }

    try:
        # Validate configuration
        validate_alpha_vantage_config(config)
        test_results["config_valid"] = True

        # Create adapter
        adapter = AlphaVantageAdapter(name="test_adapter", config=config)

        try:
            # Test connection with health check
            health_check = await adapter.health_check()
            test_results["health_check_passed"] = health_check.status.value == "healthy"

            if test_results["health_check_passed"]:
                test_results["connection_successful"] = True

                # Get rate limit and cost info
                test_results["rate_limit_info"] = await adapter.get_rate_limit_info()
                test_results["cost_info"] = await adapter.get_cost_info()

                # Test actual API call
                try:
                    price_data = await adapter.get_current_price(test_symbol)
                    test_results["sample_data"] = price_data
                except Exception as e:
                    test_results["api_call_error"] = str(e)

            else:
                test_results["error_message"] = health_check.error_message

        finally:
            # Clean up
            await adapter._close_session()

    except Exception as e:
        test_results["error_message"] = str(e)

    return test_results


# Environment-based setup function
def setup_from_environment() -> Optional[AlphaVantageAdapter]:
    """
    Set up Alpha Vantage adapter from environment variables.

    Environment variables:
    - ALPHA_VANTAGE_API_KEY: API key (required)
    - ALPHA_VANTAGE_PLAN: Plan type (free, premium, professional, enterprise)
    - ALPHA_VANTAGE_REQUESTS_PER_MINUTE: Custom rate limit per minute
    - ALPHA_VANTAGE_REQUESTS_PER_DAY: Custom rate limit per day

    Returns:
        Configured adapter or None if API key not found
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.info("ALPHA_VANTAGE_API_KEY not found in environment, skipping setup")
        return None

    try:
        plan_type = os.getenv("ALPHA_VANTAGE_PLAN", "free")

        if plan_type == "free":
            config = create_alpha_vantage_config(api_key=api_key)
        else:
            config = get_alpha_vantage_premium_config(api_key, plan_type)

        # Override with custom rate limits if provided
        custom_rpm = os.getenv("ALPHA_VANTAGE_REQUESTS_PER_MINUTE")
        if custom_rpm:
            config["requests_per_minute"] = int(custom_rpm)

        custom_rpd = os.getenv("ALPHA_VANTAGE_REQUESTS_PER_DAY")
        if custom_rpd:
            config["requests_per_day"] = int(custom_rpd)

        adapter = setup_alpha_vantage_adapter(config=config)
        logger.info(f"Alpha Vantage adapter setup from environment (plan: {plan_type})")

        return adapter

    except Exception as e:
        logger.error(f"Failed to setup Alpha Vantage adapter from environment: {e}")
        return None
