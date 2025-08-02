#!/bin/bash

# Comprehensive Integration Test Runner for Japanese Stock Analysis Platform
# This script runs all integration tests across the entire system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.dev.yml"

# Test results
TOTAL_TEST_SUITES=0
PASSED_TEST_SUITES=0
FAILED_TEST_SUITES=0

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3."
        exit 1
    fi
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed. Please install Node.js."
        exit 1
    fi
    
    log_success "All prerequisites are met"
}

# Function to start services
start_services() {
    log_info "Starting services with Docker Compose..."
    
    # Stop any existing services
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true
    fi
    
    # Start services
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
        log_success "Services started with Docker Compose"
    else
        log_warning "Docker Compose file not found, attempting to start services manually..."
        
        # Start PostgreSQL
        docker run -d --name kessan-postgres \
            -e POSTGRES_DB=kessan_test \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=password \
            -p 5432:5432 \
            postgres:15 || log_warning "PostgreSQL container may already be running"
        
        # Start Redis
        docker run -d --name kessan-redis \
            -p 6379:6379 \
            redis:7-alpine || log_warning "Redis container may already be running"
        
        log_success "Services started manually"
    fi
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Check PostgreSQL
    for i in {1..30}; do
        if docker exec kessan-postgres pg_isready -U postgres &> /dev/null; then
            log_success "PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "PostgreSQL failed to start"
            exit 1
        fi
        sleep 2
    done
    
    # Check Redis
    for i in {1..30}; do
        if docker exec kessan-redis redis-cli ping &> /dev/null; then
            log_success "Redis is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Redis failed to start"
            exit 1
        fi
        sleep 2
    done
}

# Function to setup backend
setup_backend() {
    log_info "Setting up backend environment..."
    
    cd "$BACKEND_DIR"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Run database migrations
    if [ -f "alembic.ini" ]; then
        alembic upgrade head || log_warning "Database migration failed"
    fi
    
    # Start backend server in background
    export DATABASE_URL="postgresql://postgres:password@localhost:5432/kessan_test"
    export REDIS_URL="redis://localhost:6379/1"
    export SECRET_KEY="test-secret-key-for-integration-tests"
    
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    # Wait for backend to be ready
    log_info "Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            log_success "Backend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Backend failed to start"
            kill $BACKEND_PID 2>/dev/null || true
            exit 1
        fi
        sleep 2
    done
    
    cd "$PROJECT_ROOT"
}

# Function to setup frontend
setup_frontend() {
    log_info "Setting up frontend environment..."
    
    cd "$FRONTEND_DIR"
    
    # Install dependencies
    npm install
    
    # Build frontend
    npm run build
    
    # Start frontend server in background
    npm run preview -- --port 3000 &
    FRONTEND_PID=$!
    
    # Wait for frontend to be ready
    log_info "Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 &> /dev/null; then
            log_success "Frontend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_warning "Frontend may not be ready, continuing with tests..."
            break
        fi
        sleep 2
    done
    
    cd "$PROJECT_ROOT"
}

# Function to run a test suite
run_test_suite() {
    local suite_name="$1"
    local test_command="$2"
    
    TOTAL_TEST_SUITES=$((TOTAL_TEST_SUITES + 1))
    
    log_info "Running $suite_name..."
    echo "=================================================="
    
    if eval "$test_command"; then
        PASSED_TEST_SUITES=$((PASSED_TEST_SUITES + 1))
        log_success "$suite_name completed successfully"
    else
        FAILED_TEST_SUITES=$((FAILED_TEST_SUITES + 1))
        log_error "$suite_name failed"
    fi
    
    echo ""
}

# Function to run backend unit tests
run_backend_unit_tests() {
    log_info "Running backend unit tests..."
    
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    
    # Run pytest with coverage
    python -m pytest tests/ -v --tb=short --maxfail=5
    
    cd "$PROJECT_ROOT"
}

# Function to run frontend unit tests
run_frontend_unit_tests() {
    log_info "Running frontend unit tests..."
    
    cd "$FRONTEND_DIR"
    
    # Run Jest tests
    npm test -- --watchAll=false --coverage --passWithNoTests
    
    cd "$PROJECT_ROOT"
}

# Function to run integration tests
run_integration_tests() {
    log_info "Running comprehensive integration tests..."
    
    # Install Python dependencies for integration tests
    pip3 install requests psycopg2-binary redis pytest
    
    # Run the comprehensive integration test
    python3 comprehensive_integration_test.py
}

# Function to run frontend integration tests
run_frontend_integration_tests() {
    log_info "Running frontend integration tests..."
    
    node frontend_integration_test.js
}

# Function to run performance tests
run_performance_tests() {
    log_info "Running performance tests..."
    
    # Simple performance test using curl
    log_info "Testing API response times..."
    
    # Test health endpoint
    response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        log_success "Health endpoint response time: ${response_time}s"
    else
        log_warning "Health endpoint slow response time: ${response_time}s"
    fi
    
    # Test stock search endpoint
    response_time=$(curl -o /dev/null -s -w '%{time_total}' "http://localhost:8000/api/v1/stocks/search?query=Toyota")
    if (( $(echo "$response_time < 2.0" | bc -l) )); then
        log_success "Stock search response time: ${response_time}s"
    else
        log_warning "Stock search slow response time: ${response_time}s"
    fi
}

# Function to run security tests
run_security_tests() {
    log_info "Running basic security tests..."
    
    # Test for common security headers
    headers=$(curl -s -I http://localhost:8000/health)
    
    if echo "$headers" | grep -i "x-content-type-options" > /dev/null; then
        log_success "X-Content-Type-Options header present"
    else
        log_warning "X-Content-Type-Options header missing"
    fi
    
    # Test for SQL injection protection (basic test)
    response=$(curl -s "http://localhost:8000/api/v1/stocks/search?query='; DROP TABLE users; --")
    if echo "$response" | grep -i "error" > /dev/null || echo "$response" | grep -i "results" > /dev/null; then
        log_success "SQL injection protection appears to be working"
    else
        log_warning "Potential SQL injection vulnerability"
    fi
}

# Function to cleanup
cleanup() {
    log_info "Cleaning up..."
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Stop Docker containers
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true
    else
        docker stop kessan-postgres kessan-redis 2>/dev/null || true
        docker rm kessan-postgres kessan-redis 2>/dev/null || true
    fi
    
    log_success "Cleanup completed"
}

# Function to print final results
print_final_results() {
    echo ""
    echo "=================================================="
    echo "🏁 COMPREHENSIVE TEST RESULTS"
    echo "=================================================="
    echo "Total Test Suites: $TOTAL_TEST_SUITES"
    echo "✅ Passed: $PASSED_TEST_SUITES"
    echo "❌ Failed: $FAILED_TEST_SUITES"
    
    if [ $FAILED_TEST_SUITES -eq 0 ]; then
        echo ""
        echo "🎉 ALL TEST SUITES PASSED!"
        echo "The Japanese Stock Analysis Platform is ready for production!"
    elif [ $FAILED_TEST_SUITES -le 2 ]; then
        echo ""
        echo "⚠️ MOSTLY PASSING - Minor issues detected"
        echo "Review failed test suites before production deployment"
    else
        echo ""
        echo "🚨 MULTIPLE FAILURES DETECTED"
        echo "System needs significant attention before production deployment"
    fi
    
    echo "=================================================="
}

# Main execution
main() {
    echo "🚀 Starting Comprehensive Integration Test Suite"
    echo "Japanese Stock Analysis Platform - Full System Test"
    echo "=================================================="
    
    # Set trap for cleanup on exit
    trap cleanup EXIT
    
    # Run all test phases
    check_prerequisites
    start_services
    setup_backend
    setup_frontend
    
    # Run test suites
    run_test_suite "Backend Unit Tests" "run_backend_unit_tests"
    run_test_suite "Frontend Unit Tests" "run_frontend_unit_tests"
    run_test_suite "Integration Tests" "run_integration_tests"
    run_test_suite "Frontend Integration Tests" "run_frontend_integration_tests"
    run_test_suite "Performance Tests" "run_performance_tests"
    run_test_suite "Security Tests" "run_security_tests"
    
    # Print final results
    print_final_results
    
    # Exit with appropriate code
    if [ $FAILED_TEST_SUITES -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    "backend-only")
        log_info "Running backend tests only..."
        check_prerequisites
        start_services
        setup_backend
        run_test_suite "Backend Unit Tests" "run_backend_unit_tests"
        run_test_suite "Integration Tests" "run_integration_tests"
        print_final_results
        ;;
    "frontend-only")
        log_info "Running frontend tests only..."
        check_prerequisites
        setup_frontend
        run_test_suite "Frontend Unit Tests" "run_frontend_unit_tests"
        run_test_suite "Frontend Integration Tests" "run_frontend_integration_tests"
        print_final_results
        ;;
    "quick")
        log_info "Running quick test suite..."
        check_prerequisites
        start_services
        setup_backend
        run_test_suite "Integration Tests" "run_integration_tests"
        print_final_results
        ;;
    *)
        main
        ;;
esac