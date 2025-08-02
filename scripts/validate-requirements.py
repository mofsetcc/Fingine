#!/usr/bin/env python3
"""
Requirements.txt Validation Script
Checks for common issues in Python requirements files
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


def validate_requirements_file(file_path):
    """Validate a requirements.txt file for common issues"""
    print(f"🔍 Validating {file_path}")
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    issues = []
    warnings = []
    packages = defaultdict(list)
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
        
        # Parse package specification
        # Handle formats like: package==1.0.0, package>=1.0.0, package[extra]==1.0.0
        match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)\s*([><=!]+.*)?', line)
        
        if not match:
            issues.append(f"Line {line_num}: Invalid format: {line}")
            continue
        
        package_name = match.group(1).split('[')[0].lower()  # Remove extras for duplicate check
        version_spec = match.group(2) or ""
        
        # Track packages for duplicate detection
        packages[package_name].append((line_num, line, version_spec))
        
        # Check for common version issues
        if '==' in version_spec:
            # Check for obviously wrong versions
            version = version_spec.replace('==', '')
            if version.count('.') > 3:  # Too many dots
                warnings.append(f"Line {line_num}: Suspicious version format: {version}")
            elif re.match(r'^0\.[0-4]\.\d+$', version) and package_name in ['pytest-cov']:
                # pytest-cov versions below 0.6 don't exist
                issues.append(f"Line {line_num}: Invalid {package_name} version {version} (minimum is 0.6)")
    
    # Check for duplicates
    for package_name, occurrences in packages.items():
        if len(occurrences) > 1:
            lines_info = [f"line {line_num}: {line}" for line_num, line, _ in occurrences]
            issues.append(f"Duplicate package '{package_name}' found on: {', '.join(lines_info)}")
    
    # Print results
    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    
    if warnings:
        print("⚠️ Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not issues and not warnings:
        print("✅ No issues found")
        return True
    
    return len(issues) == 0  # Return True if only warnings, False if there are issues


def fix_common_issues(file_path):
    """Fix common issues in requirements.txt"""
    print(f"🔧 Attempting to fix common issues in {file_path}")
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    seen_packages = set()
    fixes_applied = []
    
    for line_num, line in enumerate(lines, 1):
        original_line = line
        line = line.strip()
        
        # Keep comments and empty lines
        if not line or line.startswith('#'):
            fixed_lines.append(original_line)
            continue
        
        # Parse package name
        match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)', line)
        if not match:
            fixed_lines.append(original_line)
            continue
        
        package_full = match.group(1)
        package_name = package_full.split('[')[0].lower()
        
        # Skip duplicates
        if package_name in seen_packages:
            fixes_applied.append(f"Removed duplicate {package_name} from line {line_num}")
            continue
        
        seen_packages.add(package_name)
        
        # Fix known version issues
        if 'pytest-cov==0.4.4' in line:
            line = line.replace('pytest-cov==0.4.4', 'pytest-cov==4.1.0')
            fixes_applied.append(f"Fixed pytest-cov version on line {line_num}")
        
        fixed_lines.append(line + '\n')
    
    # Write back if fixes were applied
    if fixes_applied:
        # Create backup
        backup_path = f"{file_path}.backup"
        Path(file_path).rename(backup_path)
        print(f"📄 Created backup: {backup_path}")
        
        with open(file_path, 'w') as f:
            f.writelines(fixed_lines)
        
        print("✅ Fixes applied:")
        for fix in fixes_applied:
            print(f"  - {fix}")
        
        return True
    else:
        print("ℹ️ No fixes needed")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python validate-requirements.py <requirements.txt> [--fix]")
        print("\nExamples:")
        print("  python validate-requirements.py backend/requirements.txt")
        print("  python validate-requirements.py backend/requirements.txt --fix")
        sys.exit(1)
    
    file_path = sys.argv[1]
    should_fix = '--fix' in sys.argv
    
    print("🔍 Requirements.txt Validation Tool")
    print("=" * 40)
    
    if should_fix:
        print("🔧 Fix mode enabled")
        fix_common_issues(file_path)
        print("\n" + "=" * 40)
    
    # Always validate after fixing
    is_valid = validate_requirements_file(file_path)
    
    print("\n" + "=" * 40)
    if is_valid:
        print("🎉 Requirements file is valid!")
        sys.exit(0)
    else:
        print("💥 Requirements file has issues that need manual attention")
        sys.exit(1)


if __name__ == "__main__":
    main()