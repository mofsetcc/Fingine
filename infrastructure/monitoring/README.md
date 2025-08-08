# Production Monitoring Setup

This directory contains comprehensive production monitoring infrastructure for the Japanese Stock Analysis Platform (Project Kessan).

## Overview

The monitoring setup includes:

- **CloudWatch Dashboards**: Visual monitoring of application, business, and infrastructure metrics
- **CloudWatch Alarms**: Automated alerting for performance and reliability issues
- **SNS Notifications**: Multi-channel alert delivery (Slack, email, PagerDuty)
- **SLA Validation**: Automated compliance checking against defined service level agreements
- **Disaster Recovery Testing**: Automated backup and recovery procedure validation
- **Health Monitoring**: Continuous monitoring system health checks

## Components

### 1. CloudWatch Dashboards (`cloudwatch-dashboards.yml`)

Three comprehensive dashboards:

#### Application Dashboard
- API response times and error rates
- Load balancer metrics
- ECS service performance
- Recent error logs

#### Business Dashboard
- User engagement metrics (active users, registrations, logins)
- Feature usage (AI analysis requests, stock searches, watchlist updates)
- Cost metrics (API costs, LLM token usage, data source calls)
- API performance by endpoint

#### Infrastructure Dashboard
- ECS task counts and health
- RDS database metrics (storage, memory, connections)
- ElastiCache Redis performance
- Load balancer connection metrics

### 2. CloudWatch Alarms (`cloudwatch-alarms.yml`)

Comprehensive alerting covering:

#### API Performance Alarms
- **High Response Time**: >1s (warning), >3s (critical)
- **High Error Rate**: >5% (warning), >15% (critical)

#### Infrastructure Alarms
- **ECS Services**: CPU >80%, Memory >85%, Service down
- **RDS Database**: CPU >80%, Connections >80, Storage <2GB
- **ElastiCache**: CPU >80%, Memory >85%

#### Business Alarms
- **AI Costs**: >$80/day (warning), >$95/day (critical)
- **Data Sources**: Success rate <90% (warning), <70% (critical)

#### Health Check Alarms
- **Application Health**: Health endpoint failures
- **Load Balancer**: No healthy targets

### 3. Notification System

Multi-channel notification delivery:

- **Slack Integration**: Real-time alerts with rich formatting
- **Email Notifications**: Critical alerts via SNS
- **PagerDuty Integration**: Critical alerts for on-call escalation

### 4. SLA Validation (`sla-validation.py`)

Automated validation of service level agreements:

- **System Uptime**: 99.9% target
- **API Response Time**: <1s average
- **Search Response Time**: <500ms (95th percentile)
- **Database Query Time**: <100ms (95th percentile)
- **Error Rate**: <1%
- **Data Freshness**: <15 minutes
- **AI Analysis Time**: <30s (95th percentile)
- **Data Source Availability**: >99%

### 5. Disaster Recovery Testing (`disaster-recovery-test.sh`)

Automated testing of backup and recovery procedures:

- RDS automated backup verification
- Manual snapshot creation and validation
- ECS service recovery capabilities
- Load balancer health checks
- ElastiCache backup verification
- Application health endpoint testing
- CloudWatch logs retention validation
- Backup restoration readiness

### 6. Monitoring Health Checks (`monitoring-health-check.py`)

Continuous validation of monitoring system health:

- CloudFormation stack status
- Dashboard availability
- Alarm configuration
- SNS topic health
- Lambda function status
- Metric data availability
- Active alarm states
- Notification channel health

## Deployment

### Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Environment Variables** (optional but recommended):
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
   export PAGERDUTY_INTEGRATION_KEY="your-pagerduty-key"
   export EMAIL_NOTIFICATION_TOPIC="arn:aws:sns:region:account:topic"
   ```

### Quick Deployment

Deploy all monitoring components:

```bash
./infrastructure/monitoring/deploy-monitoring.sh
```

### Selective Deployment

Deploy only specific components:

```bash
# Deploy only dashboards
./infrastructure/monitoring/deploy-monitoring.sh --dashboards-only

# Deploy only alarms
./infrastructure/monitoring/deploy-monitoring.sh --alarms-only

# Run only tests
./infrastructure/monitoring/deploy-monitoring.sh --test-only
```

### Manual Deployment

Deploy individual components using AWS CLI:

```bash
# Deploy dashboards
aws cloudformation deploy \
  --template-file infrastructure/monitoring/cloudwatch-dashboards.yml \
  --stack-name kessan-prod-monitoring-dashboards \
  --parameter-overrides ProjectName=kessan Environment=prod

# Deploy alarms
aws cloudformation deploy \
  --template-file infrastructure/monitoring/cloudwatch-alarms.yml \
  --stack-name kessan-prod-monitoring-alarms \
  --parameter-overrides \
    ProjectName=kessan \
    Environment=prod \
    SlackWebhookURL=$SLACK_WEBHOOK_URL \
  --capabilities CAPABILITY_IAM
```

## Usage

### Accessing Dashboards

After deployment, dashboard URLs are available in CloudFormation outputs:

```bash
# Get dashboard URLs
aws cloudformation describe-stacks \
  --stack-name kessan-prod-monitoring-dashboards \
  --query 'Stacks[0].Outputs'
```

### Running SLA Validation

Check SLA compliance:

```bash
# Console output
python3 infrastructure/monitoring/sla-validation.py

# JSON output
python3 infrastructure/monitoring/sla-validation.py \
  --format json \
  --output sla-report.json

# Custom project/environment
python3 infrastructure/monitoring/sla-validation.py \
  --project myproject \
  --environment staging \
  --region us-west-2
```

### Testing Disaster Recovery

Run disaster recovery tests:

```bash
# Full test suite
./infrastructure/monitoring/disaster-recovery-test.sh

# Dry run (show tests without executing)
./infrastructure/monitoring/disaster-recovery-test.sh --dry-run
```

### Monitoring Health Checks

Validate monitoring system health:

```bash
# Console output
python3 infrastructure/monitoring/monitoring-health-check.py

# JSON output for automation
python3 infrastructure/monitoring/monitoring-health-check.py \
  --format json \
  --quiet \
  --output health-check.json
```

## Customization

### Adding Custom Alarms

1. **Edit CloudFormation Template**: Add new alarm resources to `cloudwatch-alarms.yml`
2. **Update Deployment**: Re-run the deployment script
3. **Test Alarm**: Validate the new alarm triggers correctly

Example custom alarm:

```yaml
CustomMetricAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: !Sub '${ProjectName}-${Environment}-custom-metric'
    AlarmDescription: 'Custom business metric threshold'
    MetricName: CustomMetric
    Namespace: Kessan/Business
    Statistic: Average
    Period: 300
    EvaluationPeriods: 2
    Threshold: 100.0
    ComparisonOperator: GreaterThanThreshold
    AlarmActions:
      - !Ref WarningAlertsTopic
```

### Adding Custom SLA Metrics

1. **Edit SLA Validator**: Add new metric definitions to `sla-validation.py`
2. **Implement Metric Collection**: Add data collection method
3. **Update Thresholds**: Define appropriate SLA targets

Example custom SLA metric:

```python
"custom_metric": {
    "target": 95.0,
    "unit": "percent",
    "description": "Custom business metric SLA",
    "measurement_period": "hourly"
}
```

### Notification Channel Configuration

#### Slack Integration

1. Create a Slack webhook URL in your workspace
2. Set the `SLACK_WEBHOOK_URL` environment variable
3. Deploy the monitoring stack

#### PagerDuty Integration

1. Create a PagerDuty integration key
2. Set the `PAGERDUTY_INTEGRATION_KEY` environment variable
3. Deploy the monitoring stack

#### Email Notifications

1. Create an SNS topic for email notifications
2. Add email subscriptions to the topic
3. Set the `EMAIL_NOTIFICATION_TOPIC` environment variable
4. Deploy the monitoring stack

## Maintenance

### Regular Tasks

1. **Weekly**: Review dashboard metrics and trends
2. **Monthly**: Validate SLA compliance and adjust thresholds
3. **Quarterly**: Run disaster recovery tests
4. **As Needed**: Update alert thresholds based on performance changes

### Troubleshooting

#### Common Issues

1. **Missing Metrics**: Ensure application is publishing custom metrics
2. **Alarm Not Triggering**: Check metric data availability and thresholds
3. **Notification Failures**: Validate SNS topic subscriptions and endpoints
4. **Dashboard Errors**: Verify resource names and permissions

#### Debug Commands

```bash
# Check alarm states
aws cloudwatch describe-alarms --alarm-name-prefix kessan-prod

# Test SNS topic
aws sns publish --topic-arn "arn:aws:sns:region:account:topic" --message "Test"

# Check metric data
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ApplicationELB" \
  --metric-name "RequestCount" \
  --start-time "2024-01-01T00:00:00Z" \
  --end-time "2024-01-01T01:00:00Z" \
  --period 3600 \
  --statistics Sum
```

### Monitoring Costs

Monitor CloudWatch costs:

- **Dashboards**: $3/month per dashboard
- **Alarms**: $0.10/month per alarm
- **Custom Metrics**: $0.30/metric/month
- **API Calls**: $0.01/1000 requests

Optimize costs by:
- Consolidating similar metrics
- Using appropriate metric retention periods
- Implementing metric filtering
- Regular cleanup of unused resources

## Security Considerations

1. **IAM Permissions**: Use least-privilege access for monitoring resources
2. **Webhook URLs**: Store sensitive URLs in AWS Secrets Manager
3. **SNS Topics**: Restrict topic access to authorized services
4. **Lambda Functions**: Use VPC endpoints for secure communication

## Integration with CI/CD

### Automated Deployment

Include monitoring deployment in your CI/CD pipeline:

```yaml
# Example GitHub Actions step
- name: Deploy Monitoring
  run: |
    export SLACK_WEBHOOK_URL="${{ secrets.SLACK_WEBHOOK_URL }}"
    export PAGERDUTY_INTEGRATION_KEY="${{ secrets.PAGERDUTY_KEY }}"
    ./infrastructure/monitoring/deploy-monitoring.sh
```

### Automated Testing

Include monitoring tests in your pipeline:

```yaml
# Example test step
- name: Validate Monitoring
  run: |
    python3 infrastructure/monitoring/monitoring-health-check.py --format json --quiet
    python3 infrastructure/monitoring/sla-validation.py --format json --quiet
```

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review CloudFormation stack events
3. Check CloudWatch logs for Lambda functions
4. Validate AWS resource permissions
5. Contact the development team for assistance

## License

This monitoring setup is part of the Japanese Stock Analysis Platform and follows the same licensing terms as the main project.