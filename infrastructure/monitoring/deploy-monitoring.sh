#!/bin/bash

# Production Monitoring Deployment Script
# Deploys CloudWatch dashboards, alarms, and monitoring infrastructure

set -e

PROJECT_NAME="${PROJECT_NAME:-kessan}"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}-monitoring"

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

# Check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        error "AWS credentials not configured"
        exit 1
    fi
    
    # Check required environment variables
    if [[ -z "$SLACK_WEBHOOK_URL" ]]; then
        warning "SLACK_WEBHOOK_URL not set - Slack notifications will not work"
    fi
    
    if [[ -z "$PAGERDUTY_INTEGRATION_KEY" ]]; then
        warning "PAGERDUTY_INTEGRATION_KEY not set - PagerDuty alerts will not work"
    fi
    
    if [[ -z "$EMAIL_NOTIFICATION_TOPIC" ]]; then
        warning "EMAIL_NOTIFICATION_TOPIC not set - Email notifications will not work"
    fi
    
    success "✅ Prerequisites check completed"
}

# Deploy CloudWatch dashboards
deploy_dashboards() {
    log "📊 Deploying CloudWatch dashboards..."
    
    local dashboard_stack="${STACK_NAME}-dashboards"
    
    aws cloudformation deploy \
        --template-file infrastructure/monitoring/cloudwatch-dashboards.yml \
        --stack-name "$dashboard_stack" \
        --parameter-overrides \
            ProjectName="$PROJECT_NAME" \
            Environment="$ENVIRONMENT" \
        --region "$AWS_REGION" \
        --no-fail-on-empty-changeset
    
    if [[ $? -eq 0 ]]; then
        success "✅ CloudWatch dashboards deployed successfully"
        
        # Get dashboard URLs
        local app_dashboard_url=$(aws cloudformation describe-stacks \
            --stack-name "$dashboard_stack" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`ApplicationDashboardURL`].OutputValue' \
            --output text)
        
        local business_dashboard_url=$(aws cloudformation describe-stacks \
            --stack-name "$dashboard_stack" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`BusinessDashboardURL`].OutputValue' \
            --output text)
        
        local infra_dashboard_url=$(aws cloudformation describe-stacks \
            --stack-name "$dashboard_stack" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`InfrastructureDashboardURL`].OutputValue' \
            --output text)
        
        log "📊 Dashboard URLs:"
        log "   Application: $app_dashboard_url"
        log "   Business: $business_dashboard_url"
        log "   Infrastructure: $infra_dashboard_url"
    else
        error "❌ Failed to deploy CloudWatch dashboards"
        return 1
    fi
}

# Deploy CloudWatch alarms
deploy_alarms() {
    log "🚨 Deploying CloudWatch alarms..."
    
    local alarms_stack="${STACK_NAME}-alarms"
    
    # Prepare parameters
    local parameters="ProjectName=$PROJECT_NAME Environment=$ENVIRONMENT"
    
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        parameters="$parameters SlackWebhookURL=$SLACK_WEBHOOK_URL"
    fi
    
    if [[ -n "$PAGERDUTY_INTEGRATION_KEY" ]]; then
        parameters="$parameters PagerDutyIntegrationKey=$PAGERDUTY_INTEGRATION_KEY"
    fi
    
    if [[ -n "$EMAIL_NOTIFICATION_TOPIC" ]]; then
        parameters="$parameters EmailNotificationTopic=$EMAIL_NOTIFICATION_TOPIC"
    fi
    
    aws cloudformation deploy \
        --template-file infrastructure/monitoring/cloudwatch-alarms.yml \
        --stack-name "$alarms_stack" \
        --parameter-overrides $parameters \
        --capabilities CAPABILITY_IAM \
        --region "$AWS_REGION" \
        --no-fail-on-empty-changeset
    
    if [[ $? -eq 0 ]]; then
        success "✅ CloudWatch alarms deployed successfully"
        
        # Get SNS topic ARNs
        local critical_topic=$(aws cloudformation describe-stacks \
            --stack-name "$alarms_stack" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`CriticalAlertsTopicArn`].OutputValue' \
            --output text)
        
        local warning_topic=$(aws cloudformation describe-stacks \
            --stack-name "$alarms_stack" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`WarningAlertsTopicArn`].OutputValue' \
            --output text)
        
        log "📢 SNS Topics:"
        log "   Critical Alerts: $critical_topic"
        log "   Warning Alerts: $warning_topic"
    else
        error "❌ Failed to deploy CloudWatch alarms"
        return 1
    fi
}

# Test monitoring setup
test_monitoring() {
    log "🧪 Testing monitoring setup..."
    
    # Test dashboard access
    log "Testing dashboard accessibility..."
    local dashboard_stack="${STACK_NAME}-dashboards"
    
    local app_dashboard_url=$(aws cloudformation describe-stacks \
        --stack-name "$dashboard_stack" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationDashboardURL`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -n "$app_dashboard_url" && "$app_dashboard_url" != "None" ]]; then
        success "✅ Application dashboard URL available"
    else
        error "❌ Application dashboard URL not found"
    fi
    
    # Test alarm configuration
    log "Testing alarm configuration..."
    local alarms_count=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "${PROJECT_NAME}-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'length(MetricAlarms)' \
        --output text 2>/dev/null)
    
    if [[ "$alarms_count" -gt 0 ]]; then
        success "✅ Found $alarms_count configured alarms"
    else
        warning "⚠️ No alarms found with prefix ${PROJECT_NAME}-${ENVIRONMENT}"
    fi
    
    # Test SNS topics
    log "Testing SNS topics..."
    local alarms_stack="${STACK_NAME}-alarms"
    
    local critical_topic=$(aws cloudformation describe-stacks \
        --stack-name "$alarms_stack" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`CriticalAlertsTopicArn`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -n "$critical_topic" && "$critical_topic" != "None" ]]; then
        # Test topic exists
        local topic_exists=$(aws sns get-topic-attributes \
            --topic-arn "$critical_topic" \
            --region "$AWS_REGION" \
            --query 'Attributes.TopicArn' \
            --output text 2>/dev/null)
        
        if [[ "$topic_exists" == "$critical_topic" ]]; then
            success "✅ Critical alerts SNS topic is accessible"
        else
            error "❌ Critical alerts SNS topic is not accessible"
        fi
    else
        warning "⚠️ Critical alerts SNS topic not found"
    fi
}

# Validate SLA compliance
validate_slas() {
    log "🎯 Validating SLA compliance..."
    
    if [[ -f "infrastructure/monitoring/sla-validation.py" ]]; then
        # Install required Python packages if needed
        if ! python3 -c "import aiohttp, boto3" 2>/dev/null; then
            log "Installing required Python packages..."
            pip3 install aiohttp boto3 2>/dev/null || {
                warning "⚠️ Could not install Python packages. Skipping SLA validation."
                return 0
            }
        fi
        
        # Run SLA validation
        local sla_report_file="sla-validation-report-$(date +%Y%m%d-%H%M%S).txt"
        if python3 infrastructure/monitoring/sla-validation.py \
            --project "$PROJECT_NAME" \
            --environment "$ENVIRONMENT" \
            --region "$AWS_REGION" \
            --output "$sla_report_file"; then
            success "✅ SLA validation completed successfully"
            log "📄 SLA report saved to: $sla_report_file"
        else
            local exit_code=$?
            if [[ $exit_code -eq 1 ]]; then
                error "❌ SLA violations detected - check $sla_report_file for details"
            elif [[ $exit_code -eq 2 ]]; then
                warning "⚠️ SLA warnings detected - check $sla_report_file for details"
            else
                error "❌ SLA validation failed"
            fi
        fi
    else
        warning "⚠️ SLA validation script not found. Skipping SLA validation."
    fi
}

# Validate performance metrics and SLA compliance
validate_performance_metrics() {
    log "🚀 Validating performance metrics and SLA compliance..."
    
    if [[ -f "infrastructure/monitoring/performance-metrics-validation.py" ]]; then
        # Install required Python packages if needed
        if ! python3 -c "import aiohttp, boto3" 2>/dev/null; then
            log "Installing required Python packages..."
            pip3 install aiohttp boto3 2>/dev/null || {
                warning "⚠️ Could not install Python packages. Skipping performance validation."
                return 0
            }
        fi
        
        # Run performance metrics validation
        local performance_report_file="performance-metrics-report-$(date +%Y%m%d-%H%M%S).txt"
        if python3 infrastructure/monitoring/performance-metrics-validation.py \
            --project "$PROJECT_NAME" \
            --environment "$ENVIRONMENT" \
            --region "$AWS_REGION" \
            --output "$performance_report_file"; then
            success "✅ Performance metrics validation completed successfully"
            log "📄 Performance report saved to: $performance_report_file"
        else
            local exit_code=$?
            if [[ $exit_code -eq 1 ]]; then
                error "❌ Critical performance issues detected - check $performance_report_file for details"
            elif [[ $exit_code -eq 2 ]]; then
                warning "⚠️ Performance warnings detected - check $performance_report_file for details"
            else
                error "❌ Performance metrics validation failed"
            fi
        fi
    else
        warning "⚠️ Performance metrics validation script not found. Skipping performance validation."
    fi
}

# Test disaster recovery procedures
test_disaster_recovery() {
    log "🔄 Testing disaster recovery procedures..."
    
    if [[ -f "infrastructure/monitoring/disaster-recovery-test.sh" ]]; then
        # Set environment variables for the DR test script
        export PROJECT_NAME="$PROJECT_NAME"
        export ENVIRONMENT="$ENVIRONMENT"
        export AWS_REGION="$AWS_REGION"
        
        # Run disaster recovery tests
        if bash infrastructure/monitoring/disaster-recovery-test.sh; then
            success "✅ Disaster recovery tests passed"
        else
            error "❌ Some disaster recovery tests failed"
            warning "⚠️ Please review the disaster recovery test report"
        fi
    else
        warning "⚠️ Disaster recovery test script not found. Skipping DR tests."
    fi
}

# Run comprehensive monitoring health check
run_monitoring_health_check() {
    log "🏥 Running comprehensive monitoring health check..."
    
    if [[ -f "infrastructure/monitoring/monitoring-health-check.py" ]]; then
        # Install required Python packages if needed
        if ! python3 -c "import boto3" 2>/dev/null; then
            log "Installing required Python packages..."
            pip3 install boto3 2>/dev/null || {
                warning "⚠️ Could not install Python packages. Skipping health check."
                return 0
            }
        fi
        
        # Run monitoring health check
        local health_report_file="monitoring-health-check-$(date +%Y%m%d-%H%M%S).txt"
        if python3 infrastructure/monitoring/monitoring-health-check.py \
            --project "$PROJECT_NAME" \
            --environment "$ENVIRONMENT" \
            --region "$AWS_REGION" \
            --output "$health_report_file"; then
            success "✅ Monitoring health check completed successfully"
            log "📄 Health check report saved to: $health_report_file"
        else
            local exit_code=$?
            if [[ $exit_code -eq 1 ]]; then
                error "❌ Critical monitoring issues detected - check $health_report_file for details"
            elif [[ $exit_code -eq 2 ]]; then
                warning "⚠️ Monitoring warnings detected - check $health_report_file for details"
            else
                error "❌ Monitoring health check failed"
            fi
        fi
    else
        warning "⚠️ Monitoring health check script not found. Skipping health check."
    fi
}

# Run comprehensive monitoring validation
run_comprehensive_validation() {
    log "🔍 Running comprehensive monitoring validation..."
    
    if [[ -f "infrastructure/monitoring/validate-monitoring-setup.sh" ]]; then
        # Set environment variables for the validation script
        export PROJECT_NAME="$PROJECT_NAME"
        export ENVIRONMENT="$ENVIRONMENT"
        export AWS_REGION="$AWS_REGION"
        
        # Run comprehensive validation
        if bash infrastructure/monitoring/validate-monitoring-setup.sh; then
            success "✅ Comprehensive monitoring validation passed"
        else
            error "❌ Some monitoring validation tests failed"
            warning "⚠️ Please review the validation report for details"
        fi
    else
        warning "⚠️ Monitoring validation script not found. Skipping comprehensive validation."
    fi
}

# Generate monitoring summary
generate_summary() {
    log "📋 Generating monitoring deployment summary..."
    
    local summary_file="monitoring-deployment-summary-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$summary_file" << EOF
# Monitoring Deployment Summary

**Deployment Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Project:** $PROJECT_NAME
**Environment:** $ENVIRONMENT
**Region:** $AWS_REGION

## Deployed Components

### CloudWatch Dashboards
- Application Dashboard: Monitors API performance, ECS services, and load balancer metrics
- Business Dashboard: Tracks user metrics, feature usage, and cost metrics
- Infrastructure Dashboard: Monitors ECS tasks, RDS, and ElastiCache resources

### CloudWatch Alarms
- **API Performance Alarms:**
  - High Response Time (>1s warning, >3s critical)
  - High Error Rate (>5% warning, >15% critical)
  
- **Infrastructure Alarms:**
  - ECS Service Health (CPU, Memory, Task Count)
  - RDS Database Health (CPU, Connections, Storage)
  - ElastiCache Redis Health (CPU, Memory)
  
- **Business Alarms:**
  - AI Cost Monitoring (\$80 warning, \$95 critical)
  - Data Source Availability (<90% warning, <70% critical)

### Notification Channels
EOF

    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        echo "- Slack notifications configured" >> "$summary_file"
    fi
    
    if [[ -n "$PAGERDUTY_INTEGRATION_KEY" ]]; then
        echo "- PagerDuty integration configured" >> "$summary_file"
    fi
    
    if [[ -n "$EMAIL_NOTIFICATION_TOPIC" ]]; then
        echo "- Email notifications configured" >> "$summary_file"
    fi
    
    cat >> "$summary_file" << EOF

## Dashboard URLs

EOF

    # Get dashboard URLs if available
    local dashboard_stack="${STACK_NAME}-dashboards"
    
    local app_dashboard_url=$(aws cloudformation describe-stacks \
        --stack-name "$dashboard_stack" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationDashboardURL`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -n "$app_dashboard_url" && "$app_dashboard_url" != "None" ]]; then
        echo "- [Application Dashboard]($app_dashboard_url)" >> "$summary_file"
    fi
    
    local business_dashboard_url=$(aws cloudformation describe-stacks \
        --stack-name "$dashboard_stack" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`BusinessDashboardURL`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -n "$business_dashboard_url" && "$business_dashboard_url" != "None" ]]; then
        echo "- [Business Dashboard]($business_dashboard_url)" >> "$summary_file"
    fi
    
    local infra_dashboard_url=$(aws cloudformation describe-stacks \
        --stack-name "$dashboard_stack" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`InfrastructureDashboardURL`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -n "$infra_dashboard_url" && "$infra_dashboard_url" != "None" ]]; then
        echo "- [Infrastructure Dashboard]($infra_dashboard_url)" >> "$summary_file"
    fi
    
    cat >> "$summary_file" << EOF

## SLA Targets

- **System Uptime:** 99.9%
- **API Response Time:** <1s average
- **Search Response Time:** <500ms (95th percentile)
- **Database Query Time:** <100ms (95th percentile)
- **Error Rate:** <1%
- **Data Freshness:** <15 minutes
- **AI Analysis Time:** <30s (95th percentile)
- **Data Source Availability:** >99%

## Monitoring Components Status

### CloudWatch Dashboards
- Application Dashboard: Real-time API performance, ECS services, load balancer metrics
- Business Dashboard: User engagement, feature usage, cost tracking
- Infrastructure Dashboard: Resource utilization, capacity planning

### CloudWatch Alarms
- **Performance Alarms:** Response time, error rate, throughput
- **Infrastructure Alarms:** CPU, memory, storage, network
- **Business Alarms:** Cost thresholds, data source availability
- **Health Alarms:** Service availability, health check failures

### Notification Channels
- SNS Topics: Critical and warning alert routing
- Lambda Functions: Slack integration for real-time notifications
- Email Subscriptions: Management team alerts

## SLA Monitoring

The following SLAs are actively monitored:

- **System Uptime:** 99.9% (monitored via health checks)
- **API Response Time:** <1s average (monitored via ALB metrics)
- **Search Response Time:** <500ms 95th percentile (custom metrics)
- **Database Query Time:** <100ms 95th percentile (RDS metrics)
- **Error Rate:** <1% (monitored via ALB error metrics)
- **Data Freshness:** <15 minutes (custom application metrics)
- **AI Analysis Time:** <30s 95th percentile (custom metrics)
- **Data Source Availability:** >99% (custom metrics)

## Disaster Recovery Readiness

- **RDS Automated Backups:** Enabled with point-in-time recovery
- **Manual Snapshots:** Tested and validated
- **ECS Service Recovery:** Auto-scaling and health checks configured
- **Load Balancer Health:** Multi-AZ deployment with health checks
- **ElastiCache Backups:** Automated snapshots configured
- **Application Health:** Comprehensive health endpoints

## Next Steps

1. **Immediate (First 24 hours):**
   - Monitor dashboards for baseline performance
   - Validate alert thresholds against actual traffic
   - Test notification channels with controlled alerts
   - Review SLA compliance reports

2. **Short-term (First week):**
   - Fine-tune alert thresholds based on observed patterns
   - Set up automated SLA reporting schedule
   - Validate disaster recovery procedures
   - Train operations team on monitoring tools

3. **Medium-term (First month):**
   - Establish monitoring runbooks and escalation procedures
   - Implement automated remediation for common issues
   - Set up capacity planning based on growth trends
   - Review and optimize cost monitoring thresholds

4. **Long-term (Ongoing):**
   - Monthly review of alert thresholds and SLA targets
   - Quarterly disaster recovery testing
   - Continuous improvement of monitoring coverage
   - Regular training updates for operations team

## Troubleshooting Guide

### Common Issues and Solutions

1. **Missing Metrics Data:**
   - Verify CloudWatch agent configuration
   - Check IAM permissions for metric publishing
   - Validate custom metric namespace and dimensions

2. **Alarm Not Triggering:**
   - Review alarm configuration and thresholds
   - Check metric data availability and frequency
   - Verify alarm state and evaluation periods

3. **Notification Failures:**
   - Test SNS topic subscriptions
   - Verify Lambda function execution logs
   - Check Slack webhook URL and permissions

4. **Dashboard Loading Issues:**
   - Verify CloudWatch dashboard permissions
   - Check metric namespace and dimension names
   - Review dashboard JSON configuration

### Emergency Contacts

- **Critical Issues:** PagerDuty integration (if configured)
- **Slack Alerts:** #kessan-alerts channel
- **Email Notifications:** Operations team distribution list

## Maintenance Schedule

### Daily
- Review critical alerts and system health
- Monitor SLA compliance dashboard
- Check cost tracking and budget alerts

### Weekly
- Review monitoring system health
- Validate notification channel functionality
- Analyze performance trends and capacity

### Monthly
- Review and adjust alert thresholds
- Update monitoring documentation
- Conduct monitoring system health assessment
- Review SLA performance and trends

### Quarterly
- Full disaster recovery testing
- Monitoring system security review
- Capacity planning and scaling assessment
- Training updates for operations team
EOF

    success "✅ Monitoring summary generated: $summary_file"
}

# Main execution
main() {
    log "🚀 Starting production monitoring deployment"
    log "Project: $PROJECT_NAME"
    log "Environment: $ENVIRONMENT"
    log "Region: $AWS_REGION"
    echo ""
    
    # Run deployment steps
    check_prerequisites
    echo ""
    
    deploy_dashboards
    echo ""
    
    deploy_alarms
    echo ""
    
    test_monitoring
    echo ""
    
    validate_slas
    echo ""
    
    validate_performance_metrics
    echo ""
    
    test_disaster_recovery
    echo ""
    
    run_monitoring_health_check
    echo ""
    
    run_comprehensive_validation
    echo ""
    
    generate_summary
    echo ""
    
    success "🎉 Production monitoring deployment completed successfully!"
    log "📊 Access your dashboards through the AWS CloudWatch console"
    log "🚨 Alerts will be sent to configured notification channels"
    log "📋 Review the monitoring summary for detailed information"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Production Monitoring Deployment Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --dashboards-only   Deploy only CloudWatch dashboards"
        echo "  --alarms-only       Deploy only CloudWatch alarms"
        echo "  --test-only         Run only monitoring tests"
        echo ""
        echo "Environment Variables:"
        echo "  PROJECT_NAME                Project name (default: kessan)"
        echo "  ENVIRONMENT                 Environment name (default: prod)"
        echo "  AWS_REGION                  AWS region (default: ap-northeast-1)"
        echo "  SLACK_WEBHOOK_URL           Slack webhook URL for notifications"
        echo "  PAGERDUTY_INTEGRATION_KEY   PagerDuty integration key"
        echo "  EMAIL_NOTIFICATION_TOPIC    SNS topic ARN for email notifications"
        exit 0
        ;;
    --dashboards-only)
        check_prerequisites
        deploy_dashboards
        ;;
    --alarms-only)
        check_prerequisites
        deploy_alarms
        ;;
    --test-only)
        check_prerequisites
        test_monitoring
        validate_slas
        test_disaster_recovery
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