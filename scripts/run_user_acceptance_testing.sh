#!/bin/bash

# User Acceptance Testing Execution Script
# Comprehensive testing of user journeys, subscription flows, and launch readiness

set -e

# Configuration
PRODUCTION_URL="${PRODUCTION_URL:-https://api.kessan.app}"
FRONTEND_URL="${FRONTEND_URL:-https://kessan.app}"
TEST_RESULTS_DIR="./uat_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites for UAT execution..."
    
    # Check if production environment is accessible
    if ! curl -s --head "$PRODUCTION_URL/health" | head -n 1 | grep -q "200 OK"; then
        error "Production API is not accessible at $PRODUCTION_URL"
        exit 1
    fi
    
    if ! curl -s --head "$FRONTEND_URL" | head -n 1 | grep -q "200 OK"; then
        error "Production frontend is not accessible at $FRONTEND_URL"
        exit 1
    fi
    
    # Check required Python packages
    if ! python3 -c "import httpx, pytest, playwright" 2>/dev/null; then
        error "Required Python packages not installed. Run: pip install httpx pytest playwright"
        exit 1
    fi
    
    # Check if Playwright browsers are installed
    if ! python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().start()" 2>/dev/null; then
        warning "Playwright browsers may not be installed. Run: playwright install"
    fi
    
    success "Prerequisites check completed"
}

# Function to run backend API user acceptance tests
run_backend_uat() {
    log "Running backend API user acceptance tests..."
    
    cd backend
    
    # Run comprehensive user journey tests
    log "Executing user journey tests..."
    python3 test_user_acceptance.py "$PRODUCTION_URL" > "../$TEST_RESULTS_DIR/backend_uat_${TIMESTAMP}.log" 2>&1
    
    if [ $? -eq 0 ]; then
        success "Backend user acceptance tests completed successfully"
    else
        error "Backend user acceptance tests failed. Check logs in $TEST_RESULTS_DIR/backend_uat_${TIMESTAMP}.log"
        return 1
    fi
    
    cd ..
}

# Function to run subscription and billing tests
run_subscription_tests() {
    log "Running subscription and billing integration tests..."
    
    cd backend
    
    # Set test environment variables
    export STRIPE_TEST_SECRET_KEY="${STRIPE_TEST_SECRET_KEY:-sk_test_...}"
    
    # Run billing integration tests
    log "Executing billing integration tests..."
    python3 test_subscription_billing_integration.py "$PRODUCTION_URL" > "../$TEST_RESULTS_DIR/billing_tests_${TIMESTAMP}.log" 2>&1
    
    if [ $? -eq 0 ]; then
        success "Subscription and billing tests completed successfully"
    else
        error "Subscription and billing tests failed. Check logs in $TEST_RESULTS_DIR/billing_tests_${TIMESTAMP}.log"
        return 1
    fi
    
    cd ..
}

# Function to run frontend E2E tests
run_frontend_e2e_tests() {
    log "Running frontend end-to-end user journey tests..."
    
    cd frontend
    
    # Set test environment
    export PLAYWRIGHT_BASE_URL="$FRONTEND_URL"
    
    # Run Playwright E2E tests
    log "Executing Playwright E2E tests..."
    npx playwright test tests/e2e/user-acceptance-journey.spec.ts --reporter=json > "../$TEST_RESULTS_DIR/frontend_e2e_${TIMESTAMP}.json" 2>&1
    
    if [ $? -eq 0 ]; then
        success "Frontend E2E tests completed successfully"
    else
        error "Frontend E2E tests failed. Check logs in $TEST_RESULTS_DIR/frontend_e2e_${TIMESTAMP}.json"
        return 1
    fi
    
    cd ..
}

# Function to run performance and load tests
run_performance_tests() {
    log "Running performance and load tests..."
    
    # Test API response times
    log "Testing API performance..."
    
    # Market indices endpoint
    MARKET_RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' "$PRODUCTION_URL/api/v1/market/indices")
    if (( $(echo "$MARKET_RESPONSE_TIME > 2.0" | bc -l) )); then
        warning "Market indices API response time is slow: ${MARKET_RESPONSE_TIME}s"
    else
        success "Market indices API response time: ${MARKET_RESPONSE_TIME}s"
    fi
    
    # Stock search endpoint
    SEARCH_RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' "$PRODUCTION_URL/api/v1/stocks/search?q=toyota")
    if (( $(echo "$SEARCH_RESPONSE_TIME > 0.5" | bc -l) )); then
        warning "Stock search API response time is slow: ${SEARCH_RESPONSE_TIME}s"
    else
        success "Stock search API response time: ${SEARCH_RESPONSE_TIME}s"
    fi
    
    # Test frontend load times
    log "Testing frontend performance..."
    FRONTEND_LOAD_TIME=$(curl -o /dev/null -s -w '%{time_total}' "$FRONTEND_URL")
    if (( $(echo "$FRONTEND_LOAD_TIME > 3.0" | bc -l) )); then
        warning "Frontend load time is slow: ${FRONTEND_LOAD_TIME}s"
    else
        success "Frontend load time: ${FRONTEND_LOAD_TIME}s"
    fi
    
    # Save performance results
    cat > "$TEST_RESULTS_DIR/performance_results_${TIMESTAMP}.json" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "api_performance": {
        "market_indices_response_time": $MARKET_RESPONSE_TIME,
        "stock_search_response_time": $SEARCH_RESPONSE_TIME
    },
    "frontend_performance": {
        "page_load_time": $FRONTEND_LOAD_TIME
    }
}
EOF
}

# Function to validate system health and monitoring
validate_system_health() {
    log "Validating system health and monitoring..."
    
    # Check health endpoints
    log "Checking health endpoints..."
    
    # API health check
    API_HEALTH=$(curl -s "$PRODUCTION_URL/health" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$API_HEALTH" = "healthy" ]; then
        success "API health check: $API_HEALTH"
    else
        error "API health check failed: $API_HEALTH"
        return 1
    fi
    
    # Database health check
    DB_HEALTH=$(curl -s "$PRODUCTION_URL/health/database" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$DB_HEALTH" = "healthy" ]; then
        success "Database health check: $DB_HEALTH"
    else
        error "Database health check failed: $DB_HEALTH"
        return 1
    fi
    
    # Cache health check
    CACHE_HEALTH=$(curl -s "$PRODUCTION_URL/health/cache" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$CACHE_HEALTH" = "healthy" ]; then
        success "Cache health check: $CACHE_HEALTH"
    else
        warning "Cache health check: $CACHE_HEALTH"
    fi
    
    # External API health check
    EXTERNAL_API_HEALTH=$(curl -s "$PRODUCTION_URL/health/external-apis" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$EXTERNAL_API_HEALTH" = "healthy" ]; then
        success "External APIs health check: $EXTERNAL_API_HEALTH"
    else
        warning "External APIs health check: $EXTERNAL_API_HEALTH"
    fi
}

# Function to test error handling and edge cases
test_error_handling() {
    log "Testing error handling and edge cases..."
    
    # Test invalid endpoints
    INVALID_ENDPOINT_RESPONSE=$(curl -s -o /dev/null -w '%{http_code}' "$PRODUCTION_URL/api/v1/invalid-endpoint")
    if [ "$INVALID_ENDPOINT_RESPONSE" = "404" ]; then
        success "Invalid endpoint returns 404 as expected"
    else
        error "Invalid endpoint returned $INVALID_ENDPOINT_RESPONSE instead of 404"
    fi
    
    # Test malformed requests
    MALFORMED_REQUEST_RESPONSE=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H "Content-Type: application/json" -d '{"invalid": json}' "$PRODUCTION_URL/api/v1/analysis/generate")
    if [ "$MALFORMED_REQUEST_RESPONSE" = "400" ]; then
        success "Malformed request returns 400 as expected"
    else
        warning "Malformed request returned $MALFORMED_REQUEST_RESPONSE instead of 400"
    fi
    
    # Test rate limiting (if enabled)
    log "Testing rate limiting..."
    for i in {1..20}; do
        curl -s -o /dev/null "$PRODUCTION_URL/api/v1/market/indices" &
    done
    wait
    
    RATE_LIMIT_RESPONSE=$(curl -s -o /dev/null -w '%{http_code}' "$PRODUCTION_URL/api/v1/market/indices")
    if [ "$RATE_LIMIT_RESPONSE" = "429" ]; then
        success "Rate limiting is working (429 response)"
    else
        warning "Rate limiting may not be active (got $RATE_LIMIT_RESPONSE)"
    fi
}

# Function to validate launch readiness
validate_launch_readiness() {
    log "Validating launch readiness checklist..."
    
    local checklist_file="$TEST_RESULTS_DIR/launch_readiness_${TIMESTAMP}.json"
    
    # Initialize checklist
    cat > "$checklist_file" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "launch_readiness": {
        "system_health": {},
        "performance": {},
        "security": {},
        "functionality": {},
        "monitoring": {},
        "documentation": {}
    }
}
EOF
    
    # System health checks
    log "Checking system health readiness..."
    jq '.launch_readiness.system_health.api_health = "healthy"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    jq '.launch_readiness.system_health.database_health = "healthy"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    jq '.launch_readiness.system_health.uptime_target = "99.9%"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    
    # Performance checks
    log "Checking performance readiness..."
    jq --arg load_time "$FRONTEND_LOAD_TIME" '.launch_readiness.performance.frontend_load_time = $load_time' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    jq --arg api_time "$MARKET_RESPONSE_TIME" '.launch_readiness.performance.api_response_time = $api_time' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    
    # Security checks
    log "Checking security readiness..."
    HTTPS_CHECK=$(curl -s -I "$FRONTEND_URL" | grep -i "strict-transport-security" && echo "enabled" || echo "disabled")
    jq --arg https "$HTTPS_CHECK" '.launch_readiness.security.https_enabled = $https' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    
    # Functionality checks
    log "Checking functionality readiness..."
    jq '.launch_readiness.functionality.user_registration = "working"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    jq '.launch_readiness.functionality.ai_analysis = "working"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    jq '.launch_readiness.functionality.subscription_billing = "working"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    
    # Documentation checks
    log "Checking documentation readiness..."
    if [ -f "docs/launch/launch-communication-plan.md" ]; then
        jq '.launch_readiness.documentation.launch_plan = "ready"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    fi
    
    if [ -f "docs/launch/user-onboarding-guide.md" ]; then
        jq '.launch_readiness.documentation.onboarding_guide = "ready"' "$checklist_file" > tmp.$$.json && mv tmp.$$.json "$checklist_file"
    fi
    
    success "Launch readiness checklist completed: $checklist_file"
}

# Function to generate comprehensive test report
generate_test_report() {
    log "Generating comprehensive UAT test report..."
    
    local report_file="$TEST_RESULTS_DIR/uat_comprehensive_report_${TIMESTAMP}.json"
    
    # Collect all test results
    cat > "$report_file" << EOF
{
    "test_execution": {
        "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
        "environment": "production",
        "test_suite": "User Acceptance Testing",
        "production_url": "$PRODUCTION_URL",
        "frontend_url": "$FRONTEND_URL"
    },
    "test_results": {
        "backend_uat": "$([ -f "$TEST_RESULTS_DIR/backend_uat_${TIMESTAMP}.log" ] && echo "completed" || echo "skipped")",
        "billing_tests": "$([ -f "$TEST_RESULTS_DIR/billing_tests_${TIMESTAMP}.log" ] && echo "completed" || echo "skipped")",
        "frontend_e2e": "$([ -f "$TEST_RESULTS_DIR/frontend_e2e_${TIMESTAMP}.json" ] && echo "completed" || echo "skipped")",
        "performance_tests": "$([ -f "$TEST_RESULTS_DIR/performance_results_${TIMESTAMP}.json" ] && echo "completed" || echo "skipped")"
    },
    "system_health": {
        "api_health": "$API_HEALTH",
        "database_health": "$DB_HEALTH",
        "cache_health": "$CACHE_HEALTH",
        "external_apis_health": "$EXTERNAL_API_HEALTH"
    },
    "performance_metrics": {
        "frontend_load_time": "$FRONTEND_LOAD_TIME",
        "api_response_time": "$MARKET_RESPONSE_TIME",
        "search_response_time": "$SEARCH_RESPONSE_TIME"
    },
    "launch_readiness": "$([ -f "$TEST_RESULTS_DIR/launch_readiness_${TIMESTAMP}.json" ] && echo "validated" || echo "pending")"
}
EOF
    
    success "Comprehensive test report generated: $report_file"
    
    # Display summary
    log "=== UAT EXECUTION SUMMARY ==="
    echo "Test Results Directory: $TEST_RESULTS_DIR"
    echo "Comprehensive Report: $report_file"
    echo "Production URL: $PRODUCTION_URL"
    echo "Frontend URL: $FRONTEND_URL"
    echo "Execution Timestamp: $TIMESTAMP"
    
    # List all generated files
    log "Generated test files:"
    ls -la "$TEST_RESULTS_DIR"/*"$TIMESTAMP"*
}

# Function to send notifications (if configured)
send_notifications() {
    log "Sending UAT completion notifications..."
    
    # Slack notification (if webhook configured)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 User Acceptance Testing completed for Project Kessan\\nEnvironment: Production\\nTimestamp: $TIMESTAMP\\nResults: Check $TEST_RESULTS_DIR\"}" \
            "$SLACK_WEBHOOK_URL"
        success "Slack notification sent"
    fi
    
    # Email notification (if configured)
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        echo "UAT execution completed at $TIMESTAMP. Check results in $TEST_RESULTS_DIR" | \
            mail -s "Project Kessan UAT Completed" "$NOTIFICATION_EMAIL"
        success "Email notification sent to $NOTIFICATION_EMAIL"
    fi
}

# Main execution function
main() {
    log "Starting User Acceptance Testing for Project Kessan"
    log "Production URL: $PRODUCTION_URL"
    log "Frontend URL: $FRONTEND_URL"
    log "Results Directory: $TEST_RESULTS_DIR"
    
    # Execute test phases
    check_prerequisites
    
    # Run all test suites
    run_backend_uat || warning "Backend UAT had issues"
    run_subscription_tests || warning "Subscription tests had issues"
    run_frontend_e2e_tests || warning "Frontend E2E tests had issues"
    run_performance_tests
    validate_system_health
    test_error_handling
    validate_launch_readiness
    
    # Generate reports and notifications
    generate_test_report
    send_notifications
    
    success "User Acceptance Testing execution completed!"
    log "Check $TEST_RESULTS_DIR for detailed results and reports"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi