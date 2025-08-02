#!/usr/bin/env python3
"""
Simple integration test for health check functionality.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.health import (
    check_database_health,
    check_data_sources_health,
    check_external_apis_health,
    check_system_resources,
    get_system_health,
    ServiceStatus
)
from app.services.system_monitor import SystemMonitor


async def test_health_checks():
    """Test all health check functions."""
    print("🔍 Testing health check functions...")
    
    try:
        # Test system resources (should work without external dependencies)
        print("\n📊 Testing system resources check...")
        resources_health = await check_system_resources()
        print(f"   Status: {resources_health['status']}")
        if resources_health['status'] != ServiceStatus.UNKNOWN.value:
            print(f"   CPU: {resources_health.get('cpu_percent', 'N/A')}%")
            print(f"   Memory: {resources_health.get('memory_percent', 'N/A')}%")
            print(f"   Disk: {resources_health.get('disk_percent', 'N/A')}%")
        
        # Test external APIs check
        print("\n🌐 Testing external APIs check...")
        apis_health = await check_external_apis_health()
        print(f"   Status: {apis_health['status']}")
        for service, info in apis_health.get('services', {}).items():
            print(f"   {service}: {info['status']}")
        
        # Test data sources check
        print("\n📡 Testing data sources check...")
        ds_health = await check_data_sources_health()
        print(f"   Status: {ds_health['status']}")
        print(f"   Summary: {ds_health.get('summary', {})}")
        
        # Test comprehensive system health
        print("\n🏥 Testing comprehensive system health...")
        system_health = await get_system_health()
        print(f"   Overall Status: {system_health['status']}")
        print(f"   Check Duration: {system_health.get('health_check_duration_ms', 0):.1f}ms")
        
        services = system_health.get('services', {})
        for service_name, service_info in services.items():
            status = service_info.get('status', 'unknown')
            print(f"   {service_name}: {status}")
        
        print("\n✅ All health checks completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_system_monitor():
    """Test system monitor functionality."""
    print("\n🔧 Testing system monitor...")
    
    try:
        monitor = SystemMonitor()
        
        # Test basic functionality
        print("   Testing alert thresholds...")
        thresholds = monitor.get_alert_thresholds()
        print(f"   Default thresholds: {thresholds}")
        
        # Test threshold updates
        new_thresholds = {"cpu_percent": 90}
        monitor.update_alert_thresholds(new_thresholds)
        updated_thresholds = monitor.get_alert_thresholds()
        print(f"   Updated CPU threshold: {updated_thresholds['cpu_percent']}")
        
        # Test dashboard data (without starting monitoring)
        print("   Testing dashboard data...")
        dashboard = await monitor.get_system_dashboard()
        print(f"   Dashboard keys: {list(dashboard.keys())}")
        
        print("   ✅ System monitor tests passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ System monitor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting health check integration tests...\n")
    
    # Test health checks
    health_success = await test_health_checks()
    
    # Test system monitor
    monitor_success = await test_system_monitor()
    
    # Summary
    print("\n" + "="*50)
    if health_success and monitor_success:
        print("🎉 All tests passed! Health monitoring system is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)