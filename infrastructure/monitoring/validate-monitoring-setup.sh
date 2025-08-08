#!/bin/bash

# Comprehensive Monitoring Setup Validation Script
# This script validates that all monitoring components are properly configured and working

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

# Test 1: CloudFormation Stack Status
test_cloudformation_stacks() {
    log "Checking CloudFormation monitoring stacks..."
    
    local stacks=(
        "${PROJECT_NAME}-${ENVIRONMENT}-monitoring-dashboards"
        "${PROJECT_NAME}-${ENVIRONMENT}-monitoring-alarms"
    )
    
    local all_healthy=true
    
    for stack in "${stacks[@]}"; do
        local status=$(aws cloudformation describe-stacks \
            --stack-name "$stack" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].StackStatus' \
            --output text 2>/dev/null)
        
        if [[ "$status" == "CREATE_COMPLETE" || "$status" == "UPDATE_COMPLETE" ]]; then
            log "✅ Stack $stack is in healthy state: $status"
        else
            error "❌ Stack $stack is in unhealthy state: $status"
            all_healthy=false
        fi
    done
    
    return $([ "$all_healthy" = true ] && echo 0 || echo 1)
}

# Test 2: CloudWatch Dashboards
test_cloudwatch_dashboards() {
    log "Validating CloudWatch dashboards..."
    
    local expected_dashboards=(
        "${PROJECT_NAME}-${ENVIRONMENT}-application"
        "${PROJECT_NAME}-${ENVIRONMENT}-business"
        "${PROJECT_NAME}-${ENVIRONMENT}-infrastructure"
    )
    
    local existing_dashboards=$(aws cloudwatch list-dashboards \
        --region "$AWS_REGION" \
        --query 'DashboardEntries[].DashboardName' \
        --output text)
    
    local all_found=true
    
    for dashboard in "${expected_dashboards[@]}"; do
        if echo "$existing_dashboards" | grep -q "$dashboard"; then
            log "✅ Dashboard found: $dashboard"
        else
            error "❌ Dashboard missing: $dashboard"
            all_found=false
        fi
    done
    
    return $([ "$all_found" = true ] && echo 0 || echo 1)
}

# Test 3: CloudWatch Alarms
test_cloudwatch_alarms() {
    log "Validating CloudWatch alarms..."
    
    local alarm_count=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "${PROJECT_NAME}-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'length(MetricAlarms)' \
        --output text)
    
    local expected_min_alarms=15
    
    if [[ "$alarm_count" -ge "$expected_min_alarms" ]]; then
        log "✅ Found $alarm_count alarms (expected minimum: $expected_min_alarms)"
        
        # Check for critical alarms in ALARM state
        local critical_alarms=$(aws cloudwatch describe-alarms \
            --alarm-name-prefix "${PROJECT_NAME}-${ENVIRONMENT}-critical" \
            --state-value ALARM \
            --region "$AWS_REGION" \
            --query 'length(MetricAlarms)' \
            --output text)
        
        if [[ "$critical_alarms" -eq 0 ]]; then
            log "✅ No critical alarms are currently active"
            return 0
        else
            warning "⚠️ $critical_alarms critical alarms are currently active"
            return 1
        fi
    else
        error "❌ Only $alarm_count alarms found (expected minimum: $expected_min_alarms)"
        return 1
    fi
}

# Test 4: SNS Topics and Subscriptions
test_sns_topics() {
    log "Validating SNS topics and subscriptions..."
    
    local expected_topics=(
        "${PROJECT_NAME}-${ENVIRONMENT}-critical-alerts"
        "${PROJECT_NAME}-${ENVIRONMENT}-warning-alerts"
    )
    
    local all_topics_healthy=true
    
    for topic_name in "${expected_topics[@]}"; do
        # Find topic ARN
        local topic_arn=$(aws sns list-topics \
            --region "$AWS_REGION" \
            --query "Topics[?contains(TopicArn, '$topic_name')].TopicArn" \
            --output text)
        
        if [[ -n "$topic_arn" && "$topic_arn" != "None" ]]; then
            log "✅ SNS topic found: $topic_name"
            
            # Check subscriptions
            local subscription_count=$(aws sns list-subscriptions-by-topic \
                --topic-arn "$topic_arn" \
                --region "$AWS_REGION" \
                --query 'length(Subscriptions)' \
                --output text)
            
            if [[ "$subscription_count" -gt 0 ]]; then
                log "✅ Topic $topic_name has $subscription_count subscriptions"
            else
                warning "⚠️ Topic $topic_name has no subscriptions"
                all_topics_healthy=false
            fi
        else
            error "❌ SNS topic not found: $topic_name"
            all_topics_healthy=false
        fi
    done
    
    return $([ "$all_topics_healthy" = true ] && echo 0 || echo 1)
}

# Test 5: Lambda Functions
test_lambda_functions() {
    log "Validating Lambda notification functions..."
    
    local expected_functions=(
        "${PROJECT_NAME}-${ENVIRONMENT}-slack-notifier"
    )
    
    local all_functions_healthy=true
    
    for function_name in "${expected_functions[@]}"; do
        local function_state=$(aws lambda get-function \
            --function-name "$function_name" \
            --region "$AWS_REGION" \
            --query 'Configuration.State' \
            --output text 2>/dev/null)
        
        if [[ "$function_state" == "Active" ]]; then
            log "✅ Lambda function is active: $function_name"
            
            # Check recent invocations
            local invocation_count=$(aws logs describe-log-streams \
                --log-group-name "/aws/lambda/$function_name" \
                --region "$AWS_REGION" \
                --query 'length(logStreams)' \
                --output text 2>/dev/null)
            
            if [[ "$invocation_count" -gt 0 ]]; then
                log "✅ Lambda function has log streams (has been invoked)"
            else
                warning "⚠️ Lambda function has no log streams (never invoked)"
            fi
        else
            error "❌ Lambda function is not active: $function_name (state: $function_state)"
            all_functions_healthy=false
        fi
    done
    
    return $([ "$all_functions_healthy" = true ] && echo 0 || echo 1)
}

# Test 6: Metric Data Availability
test_metric_data() {
    log "Validating metric data availability..."
    
    local end_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    local start_time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)
    
    # Test basic AWS metrics
    local metrics_with_data=0
    local total_metrics=0
    
    # ALB metrics
    total_metrics=$((total_metrics + 1))
    local alb_data=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ApplicationELB \
        --metric-name RequestCount \
        --dimensions Name=LoadBalancer,Value="${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Sum \
        --region "$AWS_REGION" \
        --query 'length(Datapoints)' \
        --output text 2>/dev/null)
    
    if [[ "$alb_data" -gt 0 ]]; then
        log "✅ ALB metrics available ($alb_data datapoints)"
        metrics_with_data=$((metrics_with_data + 1))
    else
        warning "⚠️ No ALB metrics data found"
    fi
    
    # ECS metrics
    total_metrics=$((total_metrics + 1))
    local ecs_data=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name CPUUtilization \
        --dimensions Name=ServiceName,Value="${PROJECT_NAME}-${ENVIRONMENT}-backend" Name=ClusterName,Value="${PROJECT_NAME}-${ENVIRONMENT}-cluster" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Average \
        --region "$AWS_REGION" \
        --query 'length(Datapoints)' \
        --output text 2>/dev/null)
    
    if [[ "$ecs_data" -gt 0 ]]; then
        log "✅ ECS metrics available ($ecs_data datapoints)"
        metrics_with_data=$((metrics_with_data + 1))
    else
        warning "⚠️ No ECS metrics data found"
    fi
    
    # RDS metrics
    total_metrics=$((total_metrics + 1))
    local rds_data=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/RDS \
        --metric-name CPUUtilization \
        --dimensions Name=DBInstanceIdentifier,Value="${PROJECT_NAME}-${ENVIRONMENT}-postgres" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Average \
        --region "$AWS_REGION" \
        --query 'length(Datapoints)' \
        --output text 2>/dev/null)
    
    if [[ "$rds_data" -gt 0 ]]; then
        log "✅ RDS metrics available ($rds_data datapoints)"
        metrics_with_data=$((metrics_with_data + 1))
    else
        warning "⚠️ No RDS metrics data found"
    fi
    
    # Check if we have sufficient metric data
    local data_percentage=$((metrics_with_data * 100 / total_metrics))
    
    if [[ "$data_percentage" -ge 70 ]]; then
        log "✅ Sufficient metric data available ($metrics_with_data/$total_metrics = $data_percentage%)"
        return 0
    else
        error "❌ Insufficient metric data ($metrics_with_data/$total_metrics = $data_percentage%)"
        return 1
    fi
}

# Test 7: Application Health Endpoint
test_application_health() {
    log "Testing application health endpoint..."
    
    # Get load balancer DNS
    local lb_dns=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --region "$AWS_REGION" \
        --query 'LoadBalancers[0].DNSName' \
        --output text 2>/dev/null)
    
    if [[ -n "$lb_dns" && "$lb_dns" != "None" ]]; then
        local health_url="https://$lb_dns/health"
        
        # Test health endpoint with timeout
        local response_code=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" --max-time 30 --connect-timeout 10)
        
        if [[ "$response_code" == "200" ]]; then
            log "✅ Application health endpoint responding (HTTP $response_code)"
            return 0
        else
            error "❌ Application health endpoint returned HTTP $response_code"
            return 1
        fi
    else
        error "❌ Load balancer DNS not found"
        return 1
    fi
}

# Test 8: Notification Channel Test
test_notification_channels() {
    log "Testing notification channels (dry run)..."
    
    # This test validates that notification infrastructure is in place
    # without actually sending test notifications
    
    local critical_topic_arn=$(aws sns list-topics \
        --region "$AWS_REGION" \
        --query "Topics[?contains(TopicArn, '${PROJECT_NAME}-${ENVIRONMENT}-critical-alerts')].TopicArn" \
        --output text)
    
    if [[ -n "$critical_topic_arn" && "$critical_topic_arn" != "None" ]]; then
        # Check topic attributes
        local topic_attributes=$(aws sns get-topic-attributes \
            --topic-arn "$critical_topic_arn" \
            --region "$AWS_REGION" \
            --query 'Attributes.DisplayName' \
            --output text 2>/dev/null)
        
        if [[ -n "$topic_attributes" ]]; then
            log "✅ Critical alerts topic is accessible and configured"
            
            # Check if Lambda function can be invoked (without actually invoking)
            local lambda_function="${PROJECT_NAME}-${ENVIRONMENT}-slack-notifier"
            local lambda_policy=$(aws lambda get-policy \
                --function-name "$lambda_function" \
                --region "$AWS_REGION" \
                --query 'Policy' \
                --output text 2>/dev/null)
            
            if [[ -n "$lambda_policy" ]]; then
                log "✅ Lambda notification function has proper permissions"
                return 0
            else
                warning "⚠️ Lambda notification function may not have proper permissions"
                return 1
            fi
        else
            error "❌ Critical alerts topic is not properly configured"
            return 1
        fi
    else
        error "❌ Critical alerts topic not found"
        return 1
    fi
}

# Generate comprehensive validation report
generate_validation_report() {
    log "📋 Generating comprehensive validation report..."
    
    local report_file="monitoring-validation-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# Monitoring Setup Validation Report

**Validation Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Project:** $PROJECT_NAME
**Environment:** $ENVIRONMENT
**Region:** $AWS_REGION

## Executive Summary

- **Total Tests:** $((TESTS_PASSED + TESTS_FAILED))
- **Tests Passed:** $TESTS_PASSED ✅
- **Tests Failed:** $TESTS_FAILED ❌
- **Success Rate:** $(echo "scale=1; $TESTS_PASSED * 100 / ($TESTS_PASSED + $TESTS_FAILED)" | bc -l)%

## Test Results

EOF

    for result in "${TEST_RESULTS[@]}"; do
        if [[ "$result" == PASS:* ]]; then
            echo "- ✅ ${result#PASS: }" >> "$report_file"
        else
            echo "- ❌ ${result#FAIL: }" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

## Infrastructure Status

### CloudWatch Components
- **Dashboards:** Application, Business, Infrastructure monitoring
- **Alarms:** Performance, infrastructure, business, and health monitoring
- **Metrics:** AWS service metrics and custom application metrics

### Notification Infrastructure
- **SNS Topics:** Critical and warning alert routing
- **Lambda Functions:** Slack integration for real-time notifications
- **Subscriptions:** Email and webhook notification channels

### Monitoring Coverage
- **Application Performance:** Response times, error rates, throughput
- **Infrastructure Health:** CPU, memory, storage, network utilization
- **Business Metrics:** User activity, feature usage, cost tracking
- **Data Quality:** Source availability, freshness, accuracy

## Recommendations

EOF

    if [[ $TESTS_FAILED -eq 0 ]]; then
        cat >> "$report_file" << EOF
✅ **All monitoring components are functioning correctly.**

### Next Steps:
1. Monitor dashboards for baseline performance patterns
2. Fine-tune alert thresholds based on actual traffic
3. Schedule regular monitoring health checks
4. Set up automated SLA reporting

EOF
    else
        cat >> "$report_file" << EOF
⚠️ **Some monitoring components need attention.**

### Immediate Actions Required:
1. Review and fix failed test components
2. Validate CloudFormation stack deployments
3. Check IAM permissions for monitoring services
4. Test notification channels manually

### Failed Components:
EOF
        for result in "${TEST_RESULTS[@]}"; do
            if [[ "$result" == FAIL:* ]]; then
                echo "- ${result#FAIL: }" >> "$report_file"
            fi
        done
    fi
    
    cat >> "$report_file" << EOF

## Monitoring Runbook

### Daily Operations
- Review critical alerts and system health
- Monitor SLA compliance dashboards
- Check cost tracking and budget alerts

### Weekly Operations
- Validate monitoring system health
- Review performance trends and capacity
- Test notification channel functionality

### Monthly Operations
- Review and adjust alert thresholds
- Conduct monitoring system assessment
- Update monitoring documentation

### Quarterly Operations
- Full disaster recovery testing
- Security review of monitoring systems
- Capacity planning and scaling assessment

## Contact Information

- **Operations Team:** [Your team contact]
- **Emergency Escalation:** [Emergency contact]
- **Slack Channel:** #kessan-alerts
- **Documentation:** [Link to monitoring documentation]

---
*Report generated by monitoring validation script*
EOF

    success "✅ Validation report generated: $report_file"
}

# Main execution
main() {
    log "🚀 Starting comprehensive monitoring validation"
    log "Project: $PROJECT_NAME"
    log "Environment: $ENVIRONMENT"
    log "Region: $AWS_REGION"
    echo ""
    
    # Check AWS CLI configuration
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        error "AWS CLI not configured or credentials invalid"
        exit 1
    fi
    
    # Run all validation tests
    run_test "CloudFormation Stack Status" "test_cloudformation_stacks"
    run_test "CloudWatch Dashboards" "test_cloudwatch_dashboards"
    run_test "CloudWatch Alarms" "test_cloudwatch_alarms"
    run_test "SNS Topics and Subscriptions" "test_sns_topics"
    run_test "Lambda Functions" "test_lambda_functions"
    run_test "Metric Data Availability" "test_metric_data"
    run_test "Application Health Endpoint" "test_application_health"
    run_test "Notification Channels" "test_notification_channels"
    
    # Generate comprehensive report
    generate_validation_report
    
    # Summary
    echo ""
    log "📊 Validation Summary"
    log "===================="
    log "Tests Passed: $TESTS_PASSED"
    log "Tests Failed: $TESTS_FAILED"
    log "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    
    # Exit with appropriate code
    if [[ $TESTS_FAILED -eq 0 ]]; then
        success "🎉 All monitoring validation tests passed!"
        log "📊 Your monitoring infrastructure is ready for production"
        exit 0
    else
        error "💥 Some monitoring validation tests failed"
        log "📋 Please review the validation report and fix the issues"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Comprehensive Monitoring Setup Validation Script"
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
        echo "1. CloudFormation Stack Status"
        echo "2. CloudWatch Dashboards"
        echo "3. CloudWatch Alarms"
        echo "4. SNS Topics and Subscriptions"
        echo "5. Lambda Functions"
        echo "6. Metric Data Availability"
        echo "7. Application Health Endpoint"
        echo "8. Notification Channels"
        echo ""
        log "Use '$0' to run all validation tests"
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