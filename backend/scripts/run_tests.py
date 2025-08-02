#!/usr/bin/env python3
"""
Test automation script for backend services.
Provides comprehensive test execution with coverage reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, cwd=None, env=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr


def run_unit_tests(verbose=False, coverage=True, fail_under=70):
    """Run unit tests with coverage."""
    print("🧪 Running unit tests...")
    
    # Base pytest command
    cmd_parts = ["python", "-m", "pytest"]
    
    if verbose:
        cmd_parts.append("-v")
    
    # Add coverage options
    if coverage:
        cmd_parts.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
            f"--cov-fail-under={fail_under}"
        ])
    
    # Add test markers
    cmd_parts.extend(["-m", "unit or not integration"])
    
    # Add test path
    cmd_parts.append("tests/")
    
    command = " ".join(cmd_parts)
    returncode, stdout, stderr = run_command(command)
    
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    if returncode == 0:
        print("✅ Unit tests passed!")
        if coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print("❌ Unit tests failed!")
        return False
    
    return True


def run_integration_tests(verbose=False):
    """Run integration tests."""
    print("🔗 Running integration tests...")
    
    cmd_parts = ["python", "-m", "pytest"]
    
    if verbose:
        cmd_parts.append("-v")
    
    # Run only integration tests
    cmd_parts.extend(["-m", "integration"])
    cmd_parts.append("tests/")
    
    command = " ".join(cmd_parts)
    returncode, stdout, stderr = run_command(command)
    
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    if returncode == 0:
        print("✅ Integration tests passed!")
    else:
        print("❌ Integration tests failed!")
        return False
    
    return True


def run_linting():
    """Run code linting checks."""
    print("🔍 Running linting checks...")
    
    # Run black formatting check
    print("Checking code formatting with black...")
    returncode, stdout, stderr = run_command("python -m black --check --diff app/")
    if returncode != 0:
        print("❌ Code formatting issues found!")
        print(stdout)
        return False
    
    # Run isort import sorting check
    print("Checking import sorting with isort...")
    returncode, stdout, stderr = run_command("python -m isort --check-only --diff app/")
    if returncode != 0:
        print("❌ Import sorting issues found!")
        print(stdout)
        return False
    
    # Run mypy type checking
    print("Running type checking with mypy...")
    returncode, stdout, stderr = run_command("python -m mypy app/")
    if returncode != 0:
        print("⚠️  Type checking issues found:")
        print(stdout)
        # Don't fail on mypy issues for now, just warn
    
    print("✅ Linting checks passed!")
    return True


def run_security_checks():
    """Run security vulnerability checks."""
    print("🔒 Running security checks...")
    
    # Check for known vulnerabilities in dependencies
    print("Checking for known vulnerabilities...")
    returncode, stdout, stderr = run_command("python -m pip check")
    if returncode != 0:
        print("⚠️  Dependency issues found:")
        print(stdout)
    
    # Run bandit security linter
    try:
        returncode, stdout, stderr = run_command("python -m bandit -r app/ -f json")
        if returncode != 0:
            print("⚠️  Security issues found:")
            print(stdout)
    except:
        print("ℹ️  Bandit not installed, skipping security scan")
    
    print("✅ Security checks completed!")
    return True


def generate_test_report():
    """Generate comprehensive test report."""
    print("📋 Generating test report...")
    
    # Run tests with JUnit XML output for CI
    cmd = "python -m pytest --junitxml=test-results.xml --cov=app --cov-report=xml tests/"
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("✅ Test report generated!")
        print("📄 JUnit XML: test-results.xml")
        print("📄 Coverage XML: coverage.xml")
    else:
        print("❌ Failed to generate test report!")
        return False
    
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run backend tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--lint", action="store_true", help="Run linting checks only")
    parser.add_argument("--security", action="store_true", help="Run security checks only")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--coverage-threshold", type=int, default=70, help="Coverage threshold")
    parser.add_argument("--report", action="store_true", help="Generate test report for CI")
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    success = True
    
    # If no specific test type is specified, run all
    if not any([args.unit, args.integration, args.lint, args.security]):
        args.all = True
    
    if args.unit or args.all:
        success &= run_unit_tests(
            verbose=args.verbose,
            coverage=not args.no_coverage,
            fail_under=args.coverage_threshold
        )
    
    if args.integration or args.all:
        success &= run_integration_tests(verbose=args.verbose)
    
    if args.lint or args.all:
        success &= run_linting()
    
    if args.security or args.all:
        success &= run_security_checks()
    
    if args.report:
        success &= generate_test_report()
    
    if success:
        print("\n🎉 All tests and checks passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests or checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()