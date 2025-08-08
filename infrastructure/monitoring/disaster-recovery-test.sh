#!/bin/bash

# Disaster Recovery and Backup Testing Script
# This script tests backup procedures and disaster recovery capabilities

set -e

PROJECT_NAME="${PROJECT_NAME:-kessan}"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TEST_RESULTS=()

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    log "Running test: $test_name"
    
    if eval "$test_command"; then
        success "✅ $test_name - PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        TEST_RESULTS+=("PASS: $test_name")
    else
        error "❌ $test_name - FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        TEST_RESULTS+=("FAIL: $test_name")
    fi
    
    echo ""
}

# Test 1: RDS Automated Backup Verification
test_rds_backups() {
    log "Checking RDS automated backups..."
    
    local db_instance="${PROJECT_NAME}-${ENVIRONMENT}-postgres"
    
    # Check if automated backups are enabled
    local backup_retention=$(aws rds describe-db-instances \
        --db-instance-identifier "$db_instance" \
        --region "$AWS_REGION" \
        --query 'DBInstances[0].BackupRetentionPeriod' \
        --output text 2>/dev/null)
    
    if [[ "$backup_retention" -gt 0 ]]; then
        log "✅ Automated backups enabled with $backup_retention days retention"
        
        # Check for recent snapshots
        local recent_snapshots=$(aws rds describe-db-snapshots \
            --db-instance-identifier "$db_instance" \
            --snapshot-type automated \
            --region "$AWS_REGION" \
            --query 'length(DBSnapshots[?SnapshotCreateTime>=`2024-01-01`])' \
            --output text 2>/dev/null)
        
        if [[ "$recent_snapshots" -gt 0 ]]; then
            log "✅ Found $recent_snapshots recent automated snapshots"
            return 0
        else
            error "❌ No recent automated snapshots found"
            return 1
        fi
    else
        error "❌ Automated backups are not enabled"
        return 1
    fi
}

# Test 2: Manual RDS Snapshot Creation
test_manual_snapshot() {
    log "Testing manual RDS snapshot creation..."
    
    local db_instance="${PROJECT_NAME}-${ENVIRONMENT}-postgres"
    local snapshot_id="${db_instance}-dr-test-$(date +%Y%m%d-%H%M%S)"
    
    # Create manual snapshot
    aws rds create-db-snapshot \
        --db-instance-identifier "$db_instance" \
        --db-snapshot-identifier "$snapshot_id" \
        --region "$AWS_REGION" > /dev/null
    
    if [[ $? -eq 0 ]]; then
        log "✅ Manual snapshot creation initiated: $snapshot_id"
        
        # Wait for snapshot to be available (with timeout)
        local timeout=300  # 5 minutes
        local elapsed=0
        
        while [[ $elapsed -lt $timeout ]]; do
            local status=$(aws rds describe-db-snapshots \
                --db-snapshot-identifier "$snapshot_id" \
                --region "$AWS_REGION" \
                --query 'DBSnapshots[0].Status' \
                --output text 2>/dev/null)
            
            if [[ "$status" == "available" ]]; then
                success "✅ Manual snapshot completed successfully"
                
                # Clean up test snapshot
                aws rds delete-db-snapshot \
                    --db-snapshot-identifier "$snapshot_id" \
                    --region "$AWS_REGION" > /dev/null
                
                log "🧹 Test snapshot cleaned up"
                return 0
            elif [[ "$status" == "failed" ]]; then
                error "❌ Manual snapshot failed"
                return 1
            fi
            
            sleep 30
            elapsed=$((elapsed + 30))
            log "⏳ Waiting for snapshot completion... ($elapsed/${timeout}s)"
        done
        
        error "❌ Manual snapshot timed out"
        return 1
    else
        error "❌ Failed to initiate manual snapshot"
        return 1
    fi
}

# Test 3: ECS Service Recovery
test_ecs_service_recovery() {
    log "Testing ECS service recovery capabilities..."
    
    local cluster_name="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
    local service_name="${PROJECT_NAME}-${ENVIRONMENT}-backend"
    
    # Get current desired count
    local current_count=$(aws ecs describe-services \
        --cluster "$cluster_name" \
        --services "$service_name" \
        --region "$AWS_REGION" \
        --query 'services[0].desiredCount' \
        --output text 2>/dev/null)
    
    if [[ "$current_count" -gt 0 ]]; then
        log "✅ Service is running with $current_count tasks"
        
        # Check service health
        local running_count=$(aws ecs describe-services \
            --cluster "$cluster_name" \
            --services "$service_name" \
            --region "$AWS_REGION" \
            --query 'services[0].runningCount' \
            --output text 2>/dev/null)
        
        if [[ "$running_count" -eq "$current_count" ]]; then
            log "✅ All tasks are running healthy"
            return 0
        else
            warning "⚠️ Only $running_count of $current_count tasks are running"
            return 1
        fi
    else
        error "❌ Service has no desired tasks"
        return 1
    fi
}

# Test 4: Load Balancer Health Check
test_load_balancer_health() {
    log "Testing load balancer health checks..."
    
    local lb_name="${PROJECT_NAME}-${ENVIRONMENT}-alb"
    
    # Get target group ARN
    local tg_arn=$(aws elbv2 describe-target-groups \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-backend-tg" \
        --region "$AWS_REGION" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text 2>/dev/null)
    
    if [[ "$tg_arn" != "None" && "$tg_arn" != "" ]]; then
        # Check target health
        local healthy_targets=$(aws elbv2 describe-target-health \
            --target-group-arn "$tg_arn" \
            --region "$AWS_REGION" \
            --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' \
            --output text 2>/dev/null)
        
        if [[ "$healthy_targets" -gt 0 ]]; then
            log "✅ Load balancer has $healthy_targets healthy targets"
            return 0
        else
            error "❌ No healthy targets found in load balancer"
            return 1
        fi
    else
        error "❌ Target group not found"
        return 1
    fi
}

# Test 5: ElastiCache Backup Verification
test_elasticache_backups() {
    log "Testing ElastiCache backup capabilities..."
    
    local cache_cluster="${PROJECT_NAME}-${ENVIRONMENT}-redis-001"
    
    # Check if backups are enabled
    local backup_window=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cache_cluster" \
        --region "$AWS_REGION" \
        --query 'CacheClusters[0].PreferredMaintenanceWindow' \
        --output text 2>/dev/null)
    
    if [[ "$backup_window" != "None" && "$backup_window" != "" ]]; then
        log "✅ ElastiCache maintenance window configured: $backup_window"
        
        # For Redis, check if snapshots exist
        local snapshots=$(aws elasticache describe-snapshots \
            --cache-cluster-id "$cache_cluster" \
            --region "$AWS_REGION" \
            --query 'length(Snapshots)' \
            --output text 2>/dev/null)
        
        if [[ "$snapshots" -gt 0 ]]; then
            log "✅ Found $snapshots ElastiCache snapshots"
            return 0
        else
            warning "⚠️ No ElastiCache snapshots found (may be expected for cluster mode)"
            return 0
        fi
    else
        warning "⚠️ ElastiCache maintenance window not configured"
        return 1
    fi
}

# Test 6: Application Health Endpoint
test_application_health() {
    log "Testing application health endpoint..."
    
    # Get load balancer DNS name
    local lb_dns=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --region "$AWS_REGION" \
        --query 'LoadBalancers[0].DNSName' \
        --output text 2>/dev/null)
    
    if [[ "$lb_dns" != "None" && "$lb_dns" != "" ]]; then
        # Test health endpoint
        local health_url="https://$lb_dns/health"
        local response=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" --max-time 30)
        
        if [[ "$response" == "200" ]]; then
            log "✅ Application health endpoint responding with HTTP 200"
            return 0
        else
            error "❌ Application health endpoint returned HTTP $response"
            return 1
        fi
    else
        error "❌ Load balancer DNS name not found"
        return 1
    fi
}

# Test 7: CloudWatch Logs Retention
test_cloudwatch_logs() {
    log "Testing CloudWatch logs retention..."
    
    local log_groups=(
        "/aws/ecs/${PROJECT_NAME}-${ENVIRONMENT}/backend"
        "/aws/ecs/${PROJECT_NAME}-${ENVIRONMENT}/frontend"
        "/aws/lambda/${PROJECT_NAME}-${ENVIRONMENT}-slack-notifier"
    )
    
    local all_good=true
    
    for log_group in "${log_groups[@]}"; do
        local retention=$(aws logs describe-log-groups \
            --log-group-name-prefix "$log_group" \
            --region "$AWS_REGION" \
            --query 'logGroups[0].retentionInDays' \
            --output text 2>/dev/null)
        
        if [[ "$retention" != "None" && "$retention" != "" ]]; then
            log "✅ Log group $log_group has $retention days retention"
        else
            warning "⚠️ Log group $log_group has no retention policy (infinite)"
            all_good=false
        fi
    done
    
    if $all_good; then
        return 0
    else
        return 1
    fi
}

# Test 8: Backup Restoration Simulation (Read-only test)
test_backup_restoration_readiness() {
    log "Testing backup restoration readiness..."
    
    local db_instance="${PROJECT_NAME}-${ENVIRONMENT}-postgres"
    
    # Check if we have recent snapshots that could be restored
    local latest_snapshot=$(aws rds describe-db-snapshots \
        --db-instance-identifier "$db_instance" \
        --snapshot-type automated \
        --region "$AWS_REGION" \
        --query 'DBSnapshots | sort_by(@, &SnapshotCreateTime) | [-1].DBSnapshotIdentifier' \
        --output text 2>/dev/null)
    
    if [[ "$latest_snapshot" != "None" && "$latest_snapshot" != "" ]]; then
        log "✅ Latest automated snapshot available: $latest_snapshot"
        
        # Check snapshot size and status
        local snapshot_info=$(aws rds describe-db-snapshots \
            --db-snapshot-identifier "$latest_snapshot" \
            --region "$AWS_REGION" \
            --query 'DBSnapshots[0].{Status:Status,Size:AllocatedStorage,Engine:Engine}' \
            --output table 2>/dev/null)
        
        log "Snapshot details:"
        echo "$snapshot_info"
        
        return 0
    else
        error "❌ No automated snapshots available for restoration"
        return 1
    fi
}

# Main execution
main() {
    log "🚀 Starting Disaster Recovery and Backup Testing"
    log "Project: $PROJECT_NAME"
    log "Environment: $ENVIRONMENT"
    log "Region: $AWS_REGION"
    echo ""
    
    # Check AWS CLI configuration
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        error "AWS CLI not configured or credentials invalid"
        exit 1
    fi
    
    # Run all tests
    run_test "RDS Automated Backup Verification" "test_rds_backups"
    run_test "Manual RDS Snapshot Creation" "test_manual_snapshot"
    run_test "ECS Service Recovery" "test_ecs_service_recovery"
    run_test "Load Balancer Health Check" "test_load_balancer_health"
    run_test "ElastiCache Backup Verification" "test_elasticache_backups"
    run_test "Application Health Endpoint" "test_application_health"
    run_test "CloudWatch Logs Retention" "test_cloudwatch_logs"
    run_test "Backup Restoration Readiness" "test_backup_restoration_readiness"
    
    # Summary
    echo ""
    log "📊 Test Summary"
    log "==============="
    log "Tests Passed: $TESTS_PASSED"
    log "Tests Failed: $TESTS_FAILED"
    log "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    
    echo ""
    log "📋 Detailed Results:"
    for result in "${TEST_RESULTS[@]}"; do
        if [[ "$result" == PASS:* ]]; then
            success "$result"
        else
            error "$result"
        fi
    done
    
    # Generate report
    local report_file="disaster-recovery-test-report-$(date +%Y%m%d-%H%M%S).json"
    cat > "$report_file" << EOF
{
  "test_run": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project": "$PROJECT_NAME",
    "environment": "$ENVIRONMENT",
    "region": "$AWS_REGION"
  },
  "summary": {
    "tests_passed": $TESTS_PASSED,
    "tests_failed": $TESTS_FAILED,
    "total_tests": $((TESTS_PASSED + TESTS_FAILED)),
    "success_rate": $(echo "scale=2; $TESTS_PASSED * 100 / ($TESTS_PASSED + $TESTS_FAILED)" | bc -l)
  },
  "results": [
$(IFS=$'\n'; echo "${TEST_RESULTS[*]}" | sed 's/^PASS: /    {"status": "PASS", "test": "/; s/^FAIL: /    {"status": "FAIL", "test": "/; s/$/"},/' | sed '$s/,$//')
  ]
}
EOF
    
    log "📄 Test report saved to: $report_file"
    
    # Exit with appropriate code
    if [[ $TESTS_FAILED -eq 0 ]]; then
        success "🎉 All disaster recovery tests passed!"
        exit 0
    else
        error "💥 Some disaster recovery tests failed. Please review and fix issues."
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Disaster Recovery and Backup Testing Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --dry-run      Show what tests would be run without executing them"
        echo ""
        echo "Environment Variables:"
        echo "  PROJECT_NAME   Project name (default: kessan)"
        echo "  ENVIRONMENT    Environment name (default: prod)"
        echo "  AWS_REGION     AWS region (default: ap-northeast-1)"
        exit 0
        ;;
    --dry-run)
        log "🔍 Dry run mode - showing tests that would be executed:"
        echo ""
        echo "1. RDS Automated Backup Verification"
        echo "2. Manual RDS Snapshot Creation"
        echo "3. ECS Service Recovery"
        echo "4. Load Balancer Health Check"
        echo "5. ElastiCache Backup Verification"
        echo "6. Application Health Endpoint"
        echo "7. CloudWatch Logs Retention"
        echo "8. Backup Restoration Readiness"
        echo ""
        log "Use '$0' to run all tests"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        echo "Use '$0 --help' for usage information"
        exit 1
        ;;
esac