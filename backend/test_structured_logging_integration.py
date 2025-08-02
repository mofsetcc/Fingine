#!/usr/bin/env python3
"""
Integration test for structured logging implementation.
"""

import json
import sys
from datetime import datetime
from app.core.logging import StructuredLogger, setup_logging
from app.core.logging_middleware import BusinessEventLogger

def test_structured_logging():
    """Test structured logging functionality."""
    print("Testing structured logging implementation...")
    
    # Setup logging
    setup_logging()
    
    # Test StructuredLogger
    logger = StructuredLogger("integration_test")
    
    # Test API request logging
    print("✓ Testing API request logging...")
    logger.log_api_request({
        "method": "GET",
        "endpoint": "/api/v1/stocks/7203",
        "user_id": "user-123",
        "status_code": 200,
        "response_time_ms": 150,
        "ip_address": "192.168.1.100"
    })
    
    # Test AI analysis logging
    print("✓ Testing AI analysis logging...")
    logger.log_ai_analysis_request({
        "ticker": "7203",
        "analysis_type": "short_term",
        "model_version": "gemini-pro-1.0",
        "processing_time_ms": 2500,
        "cost_usd": 0.05,
        "cache_hit": False
    })
    
    # Test business event logging
    print("✓ Testing business event logging...")
    logger.log_business_event({
        "event_name": "user_registration",
        "event_category": "authentication",
        "user_id": "user-456",
        "metadata": {"source": "web"}
    })
    
    # Test error logging
    print("✓ Testing error logging...")
    try:
        raise ValueError("Test error for logging")
    except ValueError as e:
        logger.log_error({
            "error_type": "validation_error",
            "error_message": "Test error occurred",
            "user_id": "user-789",
            "endpoint": "/api/v1/test"
        }, e)
    
    # Test data source logging
    print("✓ Testing data source logging...")
    logger.log_data_source_event({
        "source_name": "alpha_vantage",
        "source_type": "stock_prices",
        "operation": "fetch_daily_prices",
        "status": "success",
        "response_time_ms": 800,
        "records_processed": 100
    })
    
    # Test performance metric logging
    print("✓ Testing performance metric logging...")
    logger.log_performance_metric({
        "metric_name": "api_response_time",
        "metric_value": 150.5,
        "metric_unit": "milliseconds",
        "tags": {"endpoint": "/api/v1/stocks"}
    })
    
    # Test BusinessEventLogger
    print("✓ Testing BusinessEventLogger...")
    BusinessEventLogger.log_user_registration("user-999", "email", {"campaign": "organic"})
    BusinessEventLogger.log_stock_analysis_request("user-999", "7203", "comprehensive")
    BusinessEventLogger.log_quota_exceeded("user-999", "api_calls", 11, 10)
    
    # Test IP anonymization
    print("✓ Testing IP anonymization...")
    test_ips = [
        ("192.168.1.100", "192.168.1.0"),
        ("10.0.0.50", "10.0.0.0"),
        ("2001:db8:85a3:8d3:1319:8a2e:370:7348", "2001:db8:85a3:8d3::0"),
        ("::1", "::0"),
        ("invalid-ip", "anonymized"),
        (None, None)
    ]
    
    for ip, expected in test_ips:
        result = logger._anonymize_ip(ip)
        assert result == expected, f"IP {ip} should anonymize to {expected}, got {result}"
    
    print("✅ All structured logging tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_structured_logging()
        print("\n🎉 Structured logging implementation is working correctly!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)