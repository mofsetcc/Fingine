#!/usr/bin/env python3
"""
Integration Test Execution Script
Demonstrates how to run the comprehensive integration test suite
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def main():
    """Execute the comprehensive integration test suite"""
    
    print("🚀 Japanese Stock Analysis Platform - Integration Test Execution")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists("backend") or not os.path.exists("frontend"):
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected structure: backend/, frontend/, etc.")
        sys.exit(1)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    print("📋 Available Test Suites:")
    print("   1. Quick Integration Test (recommended for development)")
    print("   2. Full Comprehensive Test Suite (recommended for CI/CD)")
    print("   3. Backend Only Tests")
    print("   4. Frontend Only Tests")
    print("   5. Database Integration Tests")
    print("   6. Custom Test Selection")
    print()
    
    # Get user choice
    try:
        choice = input("Select test suite (1-6) [1]: ").strip() or "1"
    except KeyboardInterrupt:
        print("\n⏹️ Test execution cancelled by user")
        sys.exit(0)
    
    start_time = time.time()
    
    try:
        if choice == "1":
            print("\n🏃 Running Quick Integration Test...")
            run_quick_test()
        elif choice == "2":
            print("\n🔬 Running Full Comprehensive Test Suite...")
            run_full_test_suite()
        elif choice == "3":
            print("\n🐍 Running Backend Only Tests...")
            run_backend_tests()
        elif choice == "4":
            print("\n⚛️ Running Frontend Only Tests...")
            run_frontend_tests()
        elif choice == "5":
            print("\n🗄️ Running Database Integration Tests...")
            run_database_tests()
        elif choice == "6":
            print("\n🎯 Custom Test Selection...")
            run_custom_tests()
        else:
            print("❌ Invalid choice. Running quick test by default...")
            run_quick_test()
            
    except KeyboardInterrupt:
        print("\n⏹️ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n⏱️ Total execution time: {duration:.1f} seconds")
    print(f"🏁 Test execution completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_quick_test():
    """Run quick integration test"""
    print("Running comprehensive integration test...")
    
    # Install required packages
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "requests", "psycopg2-binary", "redis", "pytest"
    ], check=False)
    
    # Run the main integration test
    result = subprocess.run([sys.executable, "comprehensive_integration_test.py"])
    
    if result.returncode == 0:
        print("✅ Quick integration test completed successfully!")
    else:
        print("❌ Quick integration test failed!")
        
    return result.returncode == 0

def run_full_test_suite():
    """Run full comprehensive test suite"""
    print("Running full test suite with bash script...")
    
    # Make sure the script is executable
    subprocess.run(["chmod", "+x", "run_comprehensive_tests.sh"], check=False)
    
    # Run the comprehensive test script
    result = subprocess.run(["./run_comprehensive_tests.sh"])
    
    if result.returncode == 0:
        print("✅ Full test suite completed successfully!")
    else:
        print("❌ Full test suite failed!")
        
    return result.returncode == 0

def run_backend_tests():
    """Run backend-only tests"""
    print("Running backend tests...")
    
    # Install Python dependencies
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "requests", "psycopg2-binary", "redis", "pytest"
    ], check=False)
    
    # Run backend integration test
    result1 = subprocess.run([sys.executable, "comprehensive_integration_test.py"])
    
    # Run database integration test
    result2 = subprocess.run([sys.executable, "database_integration_test.py"])
    
    success = result1.returncode == 0 and result2.returncode == 0
    
    if success:
        print("✅ Backend tests completed successfully!")
    else:
        print("❌ Backend tests failed!")
        
    return success

def run_frontend_tests():
    """Run frontend-only tests"""
    print("Running frontend tests...")
    
    # Check if Node.js is available
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js is not installed or not in PATH")
        return False
    
    # Run frontend integration test
    result = subprocess.run(["node", "frontend_integration_test.js"])
    
    if result.returncode == 0:
        print("✅ Frontend tests completed successfully!")
    else:
        print("❌ Frontend tests failed!")
        
    return result.returncode == 0

def run_database_tests():
    """Run database integration tests"""
    print("Running database integration tests...")
    
    # Install required packages
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "psycopg2-binary", "redis", "sqlalchemy"
    ], check=False)
    
    # Run database integration test
    result = subprocess.run([sys.executable, "database_integration_test.py"])
    
    if result.returncode == 0:
        print("✅ Database tests completed successfully!")
    else:
        print("❌ Database tests failed!")
        
    return result.returncode == 0

def run_custom_tests():
    """Run custom test selection"""
    print("\n📋 Available Individual Tests:")
    print("   a. Comprehensive Integration Test")
    print("   b. Database Integration Test")
    print("   c. Frontend Integration Test")
    print("   d. Generate Test Report (demo)")
    print()
    
    selection = input("Select tests (e.g., 'a,b' or 'all'): ").strip().lower()
    
    if selection == "all":
        selection = "a,b,c,d"
    
    tests = [t.strip() for t in selection.split(",")]
    results = []
    
    for test in tests:
        if test == "a":
            print("\n🧪 Running Comprehensive Integration Test...")
            result = subprocess.run([sys.executable, "comprehensive_integration_test.py"])
            results.append(("Comprehensive Integration", result.returncode == 0))
            
        elif test == "b":
            print("\n🗄️ Running Database Integration Test...")
            result = subprocess.run([sys.executable, "database_integration_test.py"])
            results.append(("Database Integration", result.returncode == 0))
            
        elif test == "c":
            print("\n⚛️ Running Frontend Integration Test...")
            result = subprocess.run(["node", "frontend_integration_test.js"])
            results.append(("Frontend Integration", result.returncode == 0))
            
        elif test == "d":
            print("\n📊 Generating Test Report Demo...")
            result = subprocess.run([sys.executable, "generate_test_report.py"])
            results.append(("Test Report Generation", result.returncode == 0))
            
        else:
            print(f"⚠️ Unknown test: {test}")
    
    # Print results summary
    print("\n📋 Custom Test Results:")
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    return all(success for _, success in results)

def check_prerequisites():
    """Check if prerequisites are met"""
    print("🔍 Checking prerequisites...")
    
    # Check Python
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check if test files exist
    required_files = [
        "comprehensive_integration_test.py",
        "database_integration_test.py",
        "frontend_integration_test.js",
        "generate_test_report.py"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"❌ Missing test files: {missing_files}")
        return False
    
    print("✅ Prerequisites check passed")
    return True

if __name__ == "__main__":
    if not check_prerequisites():
        print("❌ Prerequisites not met. Please ensure all test files are present.")
        sys.exit(1)
    
    main()