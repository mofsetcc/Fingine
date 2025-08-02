#!/usr/bin/env python3
"""
Simple verification of API endpoints without database dependencies.
"""

import sys
import os
import ast

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_api_endpoints_by_source():
    """Verify API endpoints by examining source code."""
    print("Verifying API endpoints by source code analysis...")
    
    api_file_path = "app/api/v1/subscription.py"
    
    if not os.path.exists(api_file_path):
        print(f"❌ API file not found: {api_file_path}")
        return False
    
    with open(api_file_path, 'r') as f:
        content = f.read()
    
    # Check for required endpoint decorators
    required_endpoints = [
        '@router.post("/plans"',
        '@router.get("/plans"',
        '@router.get("/plans/compare"',
        '@router.put("/plans/{plan_id}"',
        '@router.get("/my-subscription"',
        '@router.get("/usage"',
        '@router.post("/upgrade"',
        '@router.post("/downgrade"',
        '@router.post("/cancel"',
        '@router.post("/initialize-plans"'
    ]
    
    missing_endpoints = []
    for endpoint in required_endpoints:
        if endpoint not in content:
            missing_endpoints.append(endpoint)
    
    if missing_endpoints:
        print(f"❌ Missing endpoints: {missing_endpoints}")
        return False
    
    print("✓ All required API endpoints found in source code")
    return True


def verify_api_router_registration():
    """Verify that subscription router is registered in main API router."""
    print("Verifying API router registration...")
    
    api_init_file = "app/api/v1/__init__.py"
    
    if not os.path.exists(api_init_file):
        print(f"❌ API init file not found: {api_init_file}")
        return False
    
    with open(api_init_file, 'r') as f:
        content = f.read()
    
    # Check for subscription import and router inclusion
    if "subscription" not in content:
        print("❌ Subscription module not imported in API router")
        return False
    
    if 'subscription.router' not in content:
        print("❌ Subscription router not included in API router")
        return False
    
    if 'prefix="/subscription"' not in content:
        print("❌ Subscription router not configured with correct prefix")
        return False
    
    print("✓ Subscription router properly registered")
    return True


def verify_endpoint_functions():
    """Verify that endpoint functions are properly defined."""
    print("Verifying endpoint functions...")
    
    api_file_path = "app/api/v1/subscription.py"
    
    with open(api_file_path, 'r') as f:
        content = f.read()
    
    # Check for required function definitions
    required_functions = [
        "async def create_plan(",
        "async def get_plans(",
        "async def compare_plans(",
        "async def update_plan(",
        "async def get_my_subscription(",
        "async def get_usage_quota(",
        "async def upgrade_subscription(",
        "async def downgrade_subscription(",
        "async def cancel_subscription(",
        "async def initialize_default_plans("
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    
    print("✓ All required endpoint functions found")
    return True


def main():
    """Run API endpoint verification."""
    print("Verifying subscription API endpoints...\n")
    
    checks = [
        ("API Endpoints by Source", verify_api_endpoints_by_source),
        ("API Router Registration", verify_api_router_registration),
        ("Endpoint Functions", verify_endpoint_functions)
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {check_name} verification failed with error: {e}")
        print()
    
    print("="*50)
    print(f"API VERIFICATION RESULTS:")
    print(f"✓ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL API ENDPOINTS VERIFIED!")
        return 0
    else:
        print(f"\n❌ {failed} verification(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())