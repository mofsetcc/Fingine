"""
Example usage of the error handling and alerting system.
"""

import asyncio
from app.core.exceptions import (
    InvalidTickerException,
    QuotaExceededException,
    DataSourceUnavailableException,
    BudgetExceededException
)
from app.core.alerting import alert_manager, system_health_alerter


async def example_user_error():
    """Example of handling user errors."""
    try:
        # Simulate user providing invalid ticker
        ticker = "INVALID_TICKER"
        if not ticker.isdigit() and len(ticker) > 10:
            raise InvalidTickerException(ticker)
    except InvalidTickerException as e:
        print(f"User Error: {e.user_message}")
        print(f"Error ID: {e.error_id}")
        print(f"Should Alert: {e.should_alert}")  # False for user errors


async def example_quota_error():
    """Example of handling quota exceeded errors."""
    try:
        # Simulate quota exceeded
        current_usage = 150
        limit = 100
        raise QuotaExceededException("api_calls", current_usage, limit)
    except QuotaExceededException as e:
        print(f"Quota Error: {e.user_message}")
        print(f"Details: {e.details}")
        print(f"Should Alert: {e.should_alert}")  # True for quota errors
        
        # This would trigger an alert in production
        if e.should_alert:
            await alert_manager.send_alert(e)


async def example_system_health_alerts():
    """Example of system health alerts."""
    
    # Database connection failure
    await system_health_alerter.alert_database_connection_failure({
        "connection_string": "postgresql://localhost:5432/kessan",
        "error": "Connection refused",
        "retry_count": 3
    })
    
    # External API failure
    await system_health_alerter.alert_external_api_failure(
        "alpha_vantage", 503, "Service unavailable"
    )
    
    # Budget exceeded
    await system_health_alerter.alert_budget_exceeded("daily", {
        "current_usage": 150.0,
        "budget": 100.0
    })
    
    # High error rate
    await system_health_alerter.alert_high_error_rate(
        0.15, 0.05, "5 minutes", {
            "endpoint": "/api/v1/stocks",
            "error_count": 15,
            "total_requests": 100
        }
    )


async def example_graceful_degradation():
    """Example of graceful degradation."""
    from app.core.error_middleware import GracefulDegradationService
    
    # Get cached data when live data is unavailable
    cached_data = await GracefulDegradationService.get_cached_stock_data("7203")
    print(f"Cached Data: {cached_data}")
    
    # Get basic analysis when AI analysis fails
    basic_analysis = await GracefulDegradationService.get_basic_analysis("7203")
    print(f"Basic Analysis: {basic_analysis}")
    
    # Get error response template
    from app.core.exceptions import ErrorCategory
    template = GracefulDegradationService.get_error_response_template(
        ErrorCategory.EXTERNAL_API_ERROR
    )
    print(f"Error Template: {template}")


async def main():
    """Run all examples."""
    print("🔧 Error Handling System Examples")
    print("=" * 50)
    
    print("\n1. User Error Example:")
    await example_user_error()
    
    print("\n2. Quota Error Example:")
    await example_quota_error()
    
    print("\n3. System Health Alerts Example:")
    print("(These would send alerts to Slack/PagerDuty in production)")
    await example_system_health_alerts()
    
    print("\n4. Graceful Degradation Example:")
    await example_graceful_degradation()
    
    print("\n✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())