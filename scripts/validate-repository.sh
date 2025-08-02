#!/bin/bash

# Repository Validation Script
# Checks for common issues that might cause CI failures

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
ISSUES=0
WARNINGS=0
CHECKS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✅]${NC} $1"
    CHECKS=$((CHECKS + 1))
}

log_warning() {
    echo -e "${YELLOW}[⚠️]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

log_error() {
    echo -e "${RED}[❌]${NC} $1"
    ISSUES=$((ISSUES + 1))
}

# Check repository structure
check_structure() {
    log_info "Checking repository structure..."
    
    # Check for main directories
    if [ -d "backend" ]; then
        log_success "Backend directory exists"
    else
        log_error "Backend directory missing"
    fi
    
    if [ -d "frontend" ]; then
        log_success "Frontend directory exists"
    else
        log_error "Frontend directory missing"
    fi
    
    if [ -d ".github/workflows" ]; then
        log_success "GitHub workflows directory exists"
    else
        log_error "GitHub workflows directory missing"
    fi
    
    # Check for key files
    if [ -f "README.md" ]; then
        log_success "README.md exists"
    else
        log_warning "README.md missing"
    fi
    
    if [ -f ".gitignore" ]; then
        log_success ".gitignore exists"
    else
        log_warning ".gitignore missing"
    fi
}

# Check backend structure
check_backend() {
    log_info "Checking backend structure..."
    
    if [ ! -d "backend" ]; then
        log_warning "Backend directory not found, skipping backend checks"
        return
    fi
    
    cd backend
    
    # Check for requirements.txt
    if [ -f "requirements.txt" ]; then
        log_success "requirements.txt exists"
        
        # Check if it's not empty
        if [ -s "requirements.txt" ]; then
            log_success "requirements.txt is not empty"
        else
            log_warning "requirements.txt is empty"
        fi
    else
        log_error "requirements.txt missing"
    fi
    
    # Check for app directory
    if [ -d "app" ]; then
        log_success "app/ directory exists"
        
        # Check for __init__.py
        if [ -f "app/__init__.py" ]; then
            log_success "app/__init__.py exists"
        else
            log_warning "app/__init__.py missing"
        fi
        
        # Check for main.py
        if [ -f "app/main.py" ]; then
            log_success "app/main.py exists"
        else
            log_warning "app/main.py missing"
        fi
    else
        log_error "app/ directory missing"
    fi
    
    # Check for tests directory
    if [ -d "tests" ]; then
        log_success "tests/ directory exists"
        
        # Check if tests directory has any Python files
        if find tests -name "*.py" | grep -q .; then
            log_success "Test files found"
        else
            log_warning "No Python test files found"
        fi
    else
        log_warning "tests/ directory missing"
    fi
    
    # Check for Dockerfile
    if [ -f "Dockerfile" ]; then
        log_success "Backend Dockerfile exists"
    else
        log_warning "Backend Dockerfile missing"
    fi
    
    cd ..
}

# Check frontend structure
check_frontend() {
    log_info "Checking frontend structure..."
    
    if [ ! -d "frontend" ]; then
        log_warning "Frontend directory not found, skipping frontend checks"
        return
    fi
    
    cd frontend
    
    # Check for package.json
    if [ -f "package.json" ]; then
        log_success "package.json exists"
        
        # Validate JSON syntax
        if python -m json.tool package.json > /dev/null 2>&1; then
            log_success "package.json has valid JSON syntax"
        else
            log_error "package.json has invalid JSON syntax"
        fi
        
        # Check for required scripts
        if grep -q '"build"' package.json; then
            log_success "Build script found in package.json"
        else
            log_warning "Build script missing in package.json"
        fi
        
        if grep -q '"test"' package.json; then
            log_success "Test script found in package.json"
        else
            log_warning "Test script missing in package.json"
        fi
    else
        log_error "package.json missing"
    fi
    
    # Check for package-lock.json
    if [ -f "package-lock.json" ]; then
        log_success "package-lock.json exists"
    else
        log_warning "package-lock.json missing (will use npm install instead of npm ci)"
    fi
    
    # Check for src directory
    if [ -d "src" ]; then
        log_success "src/ directory exists"
        
        # Check for main entry point
        if [ -f "src/main.tsx" ] || [ -f "src/main.ts" ] || [ -f "src/index.tsx" ] || [ -f "src/index.ts" ]; then
            log_success "Main entry point found"
        else
            log_warning "Main entry point (main.tsx/ts or index.tsx/ts) not found"
        fi
    else
        log_error "src/ directory missing"
    fi
    
    # Check for TypeScript config
    if [ -f "tsconfig.json" ]; then
        log_success "tsconfig.json exists"
        
        # Validate JSON syntax
        if python -m json.tool tsconfig.json > /dev/null 2>&1; then
            log_success "tsconfig.json has valid JSON syntax"
        else
            log_error "tsconfig.json has invalid JSON syntax"
        fi
    else
        log_warning "tsconfig.json missing"
    fi
    
    # Check for Vite config
    if [ -f "vite.config.ts" ] || [ -f "vite.config.js" ]; then
        log_success "Vite configuration found"
    else
        log_warning "Vite configuration missing"
    fi
    
    # Check for Dockerfile
    if [ -f "Dockerfile" ]; then
        log_success "Frontend Dockerfile exists"
    else
        log_warning "Frontend Dockerfile missing"
    fi
    
    cd ..
}

# Check workflow files
check_workflows() {
    log_info "Checking GitHub workflow files..."
    
    if [ ! -d ".github/workflows" ]; then
        log_error "No GitHub workflows directory found"
        return
    fi
    
    # Check for workflow files
    workflow_count=$(find .github/workflows -name "*.yml" -o -name "*.yaml" | wc -l)
    if [ $workflow_count -gt 0 ]; then
        log_success "Found $workflow_count workflow file(s)"
        
        # Validate YAML syntax
        for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
            if [ -f "$workflow" ]; then
                if python -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
                    log_success "$(basename "$workflow") has valid YAML syntax"
                else
                    log_error "$(basename "$workflow") has invalid YAML syntax"
                fi
            fi
        done
    else
        log_warning "No workflow files found"
    fi
}

# Check for common issues
check_common_issues() {
    log_info "Checking for common issues..."
    
    # Check for large files
    large_files=$(find . -type f -size +10M -not -path "./.git/*" -not -path "./node_modules/*" 2>/dev/null || true)
    if [ -n "$large_files" ]; then
        log_warning "Large files found (>10MB):"
        echo "$large_files" | while read -r file; do
            echo "  - $file"
        done
    else
        log_success "No large files found"
    fi
    
    # Check for node_modules in git
    if [ -d "node_modules" ] && git ls-files node_modules/ 2>/dev/null | grep -q .; then
        log_error "node_modules directory is tracked by git"
    else
        log_success "node_modules not tracked by git"
    fi
    
    # Check for __pycache__ in git
    if find . -name "__pycache__" -type d | xargs git ls-files 2>/dev/null | grep -q .; then
        log_error "__pycache__ directories are tracked by git"
    else
        log_success "__pycache__ not tracked by git"
    fi
    
    # Check for .env files in git
    if git ls-files | grep -E "\.env$|\.env\..*" | grep -v "\.env\.example"; then
        log_error "Environment files (.env) are tracked by git"
    else
        log_success "No environment files tracked by git"
    fi
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python dependencies
    if [ -f "backend/requirements.txt" ]; then
        # Check for common problematic patterns
        if grep -q "==" backend/requirements.txt; then
            log_success "Backend dependencies have version pins"
        else
            log_warning "Backend dependencies don't have version pins"
        fi
        
        # Check for development dependencies mixed with production
        if grep -qE "(pytest|black|flake8)" backend/requirements.txt; then
            log_warning "Development dependencies found in requirements.txt (consider requirements-dev.txt)"
        fi
    fi
    
    # Check Node.js dependencies
    if [ -f "frontend/package.json" ]; then
        # Check for security vulnerabilities (if npm is available)
        if command -v npm >/dev/null 2>&1; then
            cd frontend
            if npm audit --audit-level=high --json > /dev/null 2>&1; then
                log_success "No high-severity npm vulnerabilities found"
            else
                log_warning "High-severity npm vulnerabilities found (run 'npm audit' for details)"
            fi
            cd ..
        fi
    fi
}

# Generate report
generate_report() {
    echo ""
    echo "=================================================="
    echo "🏁 REPOSITORY VALIDATION REPORT"
    echo "=================================================="
    echo "Total Checks: $CHECKS"
    echo "✅ Passed: $((CHECKS - WARNINGS - ISSUES))"
    echo "⚠️ Warnings: $WARNINGS"
    echo "❌ Issues: $ISSUES"
    echo ""
    
    if [ $ISSUES -eq 0 ] && [ $WARNINGS -eq 0 ]; then
        echo "🎉 Repository is in excellent condition!"
        echo "All checks passed. CI should run smoothly."
    elif [ $ISSUES -eq 0 ]; then
        echo "✅ Repository is in good condition!"
        echo "Only minor warnings found. CI should run successfully."
    elif [ $ISSUES -le 2 ]; then
        echo "⚠️ Repository has minor issues."
        echo "Fix the issues above to improve CI reliability."
    else
        echo "🚨 Repository has significant issues."
        echo "Fix the issues above before running CI."
    fi
    
    echo ""
    echo "💡 Tips:"
    echo "- Run this script regularly to catch issues early"
    echo "- Fix issues in order of priority (errors first, then warnings)"
    echo "- Check the CI troubleshooting guide for detailed solutions"
    echo ""
    echo "📚 Documentation:"
    echo "- CI Troubleshooting: docs/development/ci-troubleshooting-guide.md"
    echo "- Integration Tests: INTEGRATION_TEST_SUMMARY.md"
}

# Main function
main() {
    echo "🔍 Repository Validation Script"
    echo "==============================="
    echo ""
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a Git repository"
        exit 1
    fi
    
    # Run all checks
    check_structure
    check_backend
    check_frontend
    check_workflows
    check_common_issues
    check_dependencies
    
    # Generate report
    generate_report
    
    # Exit with appropriate code
    if [ $ISSUES -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Handle command line arguments
case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Repository Validation Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (none)    Run full validation (default)"
        echo "  help      Show this help message"
        echo ""
        echo "This script checks for common issues that might cause CI failures:"
        echo "- Repository structure"
        echo "- Required files and directories"
        echo "- Configuration file syntax"
        echo "- Common git tracking issues"
        echo "- Dependency problems"
        ;;
    *)
        main
        ;;
esac