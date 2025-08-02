# Monitoring and Alerting Setup Guide

This guide covers the comprehensive monitoring and alerting setup for Project Kessan.

## Overview

Our monitoring strategy includes:
- **Application Performance Monitoring (APM)**: Datadog for distributed tracing
- **Infrastructure Monitoring**: CloudWatch for AWS resources
- **Business Metrics**: Custom metrics for user engagement and system performance
- **Log Aggregation**: Structured logging with CloudWatch Logs
- **Alerting**: Multi-channel alerting via Slack, PagerDuty, and email

## Datadog APM Setup

### 1. Datadog Agent Configuration

```yaml
# infrastructure/monitoring/datadog-agent.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: datadog-agent
  namespace: default
spec:
  selector:
    matchLabels:
      app: datadog-agent
  template:
    metadata:
      labels:
        app: datadog-agent
    spec:
      containers:
      - name: datadog-agent
        image: datadog/agent:latest
        env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              name: datadog-secret
              key: api-key
        - name: DD_SITE
          value: "datadoghq.com"
        - name: DD_APM_ENABLED
          value: "true"
        - name: DD_APM_NON_LOCAL_TRAFFIC
          value: "true"
        - name: DD_LOGS_ENABLED
          value: "true"
        - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
          value: "true"
        ports:
        - containerPort: 8125
          name: dogstatsd
        - containerPort: 8126
          name: trace-agent
```

### 2. Application Integration

```python
# backend/app/core/datadog_apm.py
from ddtrace import config, patch_all, tracer
from ddtrace.contrib.fastapi import patch

class DatadogAPM:
    def __init__(self):
        self.enabled = False
        self.service_name = "kessan-api"
        
    def initialize(self, service_name: str = "kessan-api"):
        """Initialize Datadog APM tracing."""
        if not self.enabled:
            return
            
        self.service_name = service_name
        
        # Configure tracer
        tracer.configure(
            hostname="datadog-agent",
            port=8126,
        )
        
        # Patch all supported libraries
        patch_all()
        
        # Configure FastAPI integration
        patch()
        
        # Configure service mapping
        config.fastapi["service_name"] = service_name
        config.sqlalchemy["service_name"] = f"{service_name}-db"
        config.redis["service_name"] = f"{service_name}-cache"
        
        print(f"Datadog APM initialized for service: {service_name}")

datadog_apm = DatadogAPM()
```

## CloudWatch Monitoring

### 1. Custom Metrics

```python
# backend/app/services/business_metrics.py
import boto3
from datetime import datetime
from typing import Dict, Any

class BusinessMetrics:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'Kessan/Business'
        
    async def record_user_registration(self, registration_method: str):
        """Record user registration event."""
        await self._put_metric(
            metric_name='UserRegistrations',
            value=1,
            dimensions=[
                {'Name': 'Method', 'Value': registration_method}
            ]
        )
    
    async def record_api_usage(self, endpoint: str, response_time: float, status_code: int):
        """Record API usage metrics."""
        await self._put_metric(
            metric_name='APIRequests',
            value=1,
            dimensions=[
                {'Name': 'Endpoint', 'Value': endpoint},
                {'Name': 'StatusCode', 'Value': str(status_code)}
            ]
        )
        
        await self._put_metric(
            metric_name='APIResponseTime',
            value=response_time,
            unit='Milliseconds',
            dimensions=[
                {'Name': 'Endpoint', 'Value': endpoint}
            ]
        )
    
    async def record_ai_analysis_generation(self, analysis_type: str, cost_usd: float, processing_time: float):
        """Record AI analysis metrics."""
        await self._put_metric(
            metric_name='AIAnalysisGenerated',
            value=1,
            dimensions=[
                {'Name': 'AnalysisType', 'Value': analysis_type}
            ]
        )
        
        await self._put_metric(
            metric_name='AIAnalysisCost',
            value=cost_usd,
            unit='None',
            dimensions=[
                {'Name': 'AnalysisType', 'Value': analysis_type}
            ]
        )
        
        await self._put_metric(
            metric_name='AIAnalysisProcessingTime',
            value=processing_time,
            unit='Seconds',
            dimensions=[
                {'Name': 'AnalysisType', 'Value': analysis_type}
            ]
        )
    
    async def _put_metric(self, metric_name: str, value: float, unit: str = 'Count', dimensions: list = None):
        """Put metric to CloudWatch."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': dimensions or []
                    }
                ]
            )
        except Exception as e:
            print(f"Failed to put metric {metric_name}: {e}")

business_metrics = BusinessMetrics()
```

### 2. CloudWatch Dashboards

```yaml
# infrastructure/monitoring/cloudwatch-dashboards.yml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch Dashboards for Project Kessan'

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues: [development, staging, production]

Resources:
  KessanMainDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: !Sub 'Kessan-${Environment}-Main'
      DashboardBody: !Sub |
        {
          "widgets": [
            {
              "type": "metric",
              "x": 0,
              "y": 0,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "AWS/ECS", "CPUUtilization", "ServiceName", "kessan-api-service", "ClusterName", "kessan-${Environment}" ],
                  [ ".", "MemoryUtilization", ".", ".", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "ap-northeast-1",
                "title": "ECS Service Metrics",
                "period": 300
              }
            },
            {
              "type": "metric",
              "x": 12,
              "y": 0,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "kessan-db-${Environment}" ],
                  [ ".", "DatabaseConnections", ".", "." ],
                  [ ".", "ReadLatency", ".", "." ],
                  [ ".", "WriteLatency", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "ap-northeast-1",
                "title": "RDS Metrics",
                "period": 300
              }
            },
            {
              "type": "metric",
              "x": 0,
              "y": 6,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "Kessan/Business", "APIRequests", "Endpoint", "/stocks/search" ],
                  [ "...", "/analysis/{ticker}/generate" ],
                  [ "...", "/watchlist" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "ap-northeast-1",
                "title": "API Usage",
                "period": 300
              }
            },
            {
              "type": "metric",
              "x": 12,
              "y": 6,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "Kessan/Business", "UserRegistrations", "Method", "email" ],
                  [ "...", "google" ],
                  [ "...", "line" ]
                ],
                "view": "timeSeries",
                "stacked": true,
                "region": "ap-northeast-1",
                "title": "User Registrations",
                "period": 3600
              }
            }
          ]
        }

  KessanPerformanceDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: !Sub 'Kessan-${Environment}-Performance'
      DashboardBody: !Sub |
        {
          "widgets": [
            {
              "type": "metric",
              "x": 0,
              "y": 0,
              "width": 24,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "Kessan/Business", "APIResponseTime", "Endpoint", "/stocks/search" ],
                  [ "...", "/stocks/{ticker}" ],
                  [ "...", "/analysis/{ticker}/generate" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "ap-northeast-1",
                "title": "API Response Times",
                "period": 300,
                "stat": "Average"
              }
            },
            {
              "type": "metric",
              "x": 0,
              "y": 6,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "AWS/ElastiCache", "CacheHitRate", "CacheClusterId", "kessan-redis-${Environment}" ],
                  [ ".", "CacheMisses", ".", "." ],
                  [ ".", "CacheHits", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "ap-northeast-1",
                "title": "Redis Cache Performance",
                "period": 300
              }
            },
            {
              "type": "metric",
              "x": 12,
              "y": 6,
              "width": 12,
              "height": 6,
              "properties": {
                "metrics": [
                  [ "Kessan/Business", "AIAnalysisCost", "AnalysisType", "comprehensive" ],
                  [ "...", "short_term" ],
                  [ "...", "mid_term" ],
                  [ "...", "long_term" ]
                ],
                "view": "timeSeries",
                "stacked": true,
                "region": "ap-northeast-1",
                "title": "AI Analysis Costs",
                "period": 3600
              }
            }
          ]
        }
```#
## 3. CloudWatch Alarms

```yaml
# infrastructure/monitoring/cloudwatch-alarms.yml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch Alarms for Project Kessan'

Parameters:
  Environment:
    Type: String
    Default: production
  SNSTopicArn:
    Type: String
    Description: SNS Topic ARN for alarm notifications

Resources:
  # API Response Time Alarm
  APIResponseTimeAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub 'Kessan-${Environment}-API-HighResponseTime'
      AlarmDescription: 'API response time is too high'
      MetricName: APIResponseTime
      Namespace: Kessan/Business
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 1000
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SNSTopicArn
      Dimensions:
        - Name: Endpoint
          Value: '/stocks/search'

  # Database Connection Alarm
  DatabaseConnectionAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub 'Kessan-${Environment}-DB-HighConnections'
      AlarmDescription: 'Database connection count is too high'
      MetricName: DatabaseConnections
      Namespace: AWS/RDS
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SNSTopicArn
      Dimensions:
        - Name: DBInstanceIdentifier
          Value: !Sub 'kessan-db-${Environment}'

  # ECS CPU Utilization Alarm
  ECSCPUAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub 'Kessan-${Environment}-ECS-HighCPU'
      AlarmDescription: 'ECS service CPU utilization is too high'
      MetricName: CPUUtilization
      Namespace: AWS/ECS
      Statistic: Average
      Period: 300
      EvaluationPeriods: 3
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SNSTopicArn
      Dimensions:
        - Name: ServiceName
          Value: kessan-api-service
        - Name: ClusterName
          Value: !Sub 'kessan-${Environment}'

  # Error Rate Alarm
  ErrorRateAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub 'Kessan-${Environment}-API-HighErrorRate'
      AlarmDescription: 'API error rate is too high'
      MetricName: APIRequests
      Namespace: Kessan/Business
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 10
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SNSTopicArn
      Dimensions:
        - Name: StatusCode
          Value: '500'
```

## Structured Logging

### 1. Log Configuration

```python
# backend/app/core/logging.py
import structlog
import logging
import sys
from typing import Any, Dict

def setup_logging(log_level: str = "INFO", service_name: str = "kessan-api"):
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Add service name to all logs
    structlog.contextvars.bind_contextvars(service=service_name)

class StructuredLogger:
    """Structured logger for business events."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def log_user_action(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """Log user action for analytics."""
        self.logger.info(
            "user_action",
            user_id=user_id,
            action=action,
            details=details or {}
        )
    
    def log_api_request(self, method: str, path: str, status_code: int, 
                       response_time: float, user_id: str = None):
        """Log API request for monitoring."""
        self.logger.info(
            "api_request",
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time,
            user_id=user_id
        )
    
    def log_external_api_call(self, provider: str, endpoint: str, 
                             response_time: float, status_code: int, cost: float = None):
        """Log external API call for cost tracking."""
        self.logger.info(
            "external_api_call",
            provider=provider,
            endpoint=endpoint,
            response_time_ms=response_time,
            status_code=status_code,
            cost_usd=cost
        )
    
    def log_error(self, error_type: str, error_message: str, 
                  context: Dict[str, Any] = None, user_id: str = None):
        """Log error with context."""
        self.logger.error(
            "application_error",
            error_type=error_type,
            error_message=error_message,
            context=context or {},
            user_id=user_id
        )

structured_logger = StructuredLogger()
```

## Alerting Configuration

### 1. Slack Integration

```python
# backend/app/core/alerting.py
import aiohttp
import json
from typing import Dict, Any, Optional
from enum import Enum

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertManager:
    def __init__(self, slack_webhook_url: str = None, pagerduty_key: str = None):
        self.slack_webhook_url = slack_webhook_url
        self.pagerduty_key = pagerduty_key
    
    async def send_alert(self, title: str, message: str, severity: AlertSeverity, 
                        context: Dict[str, Any] = None):
        """Send alert to configured channels."""
        alert_data = {
            "title": title,
            "message": message,
            "severity": severity.value,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to Slack
        if self.slack_webhook_url and severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            await self._send_slack_alert(alert_data)
        
        # Send to PagerDuty for critical alerts
        if self.pagerduty_key and severity == AlertSeverity.CRITICAL:
            await self._send_pagerduty_alert(alert_data)
    
    async def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send alert to Slack."""
        color_map = {
            "low": "#36a64f",
            "medium": "#ff9500", 
            "high": "#ff0000",
            "critical": "#8B0000"
        }
        
        slack_payload = {
            "attachments": [
                {
                    "color": color_map.get(alert_data["severity"], "#ff0000"),
                    "title": alert_data["title"],
                    "text": alert_data["message"],
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert_data["severity"].upper(),
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert_data["timestamp"],
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        # Add context fields
        for key, value in alert_data["context"].items():
            slack_payload["attachments"][0]["fields"].append({
                "title": key.replace("_", " ").title(),
                "value": str(value),
                "short": True
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.slack_webhook_url,
                json=slack_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    print(f"Failed to send Slack alert: {response.status}")
    
    async def _send_pagerduty_alert(self, alert_data: Dict[str, Any]):
        """Send alert to PagerDuty."""
        pagerduty_payload = {
            "routing_key": self.pagerduty_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert_data["title"],
                "source": "kessan-api",
                "severity": alert_data["severity"],
                "custom_details": alert_data["context"]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=pagerduty_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 202:
                    print(f"Failed to send PagerDuty alert: {response.status}")

alert_manager = AlertManager()
```

### 2. Performance Alerts

```python
# backend/app/core/performance_alerts.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import psutil
import boto3

class PerformanceAlertManager:
    def __init__(self, alert_manager):
        self.alert_manager = alert_manager
        self.cloudwatch = boto3.client('cloudwatch')
        self.monitoring = True
        
    async def start_monitoring(self):
        """Start performance monitoring loop."""
        while self.monitoring:
            try:
                await self._check_system_performance()
                await self._check_api_performance()
                await self._check_database_performance()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
    
    async def _check_system_performance(self):
        """Check system resource usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        if cpu_percent > 80:
            await self.alert_manager.send_alert(
                title="High CPU Usage",
                message=f"CPU usage is {cpu_percent}%",
                severity=AlertSeverity.HIGH,
                context={"cpu_percent": cpu_percent}
            )
        
        if memory_percent > 85:
            await self.alert_manager.send_alert(
                title="High Memory Usage", 
                message=f"Memory usage is {memory_percent}%",
                severity=AlertSeverity.HIGH,
                context={"memory_percent": memory_percent}
            )
    
    async def _check_api_performance(self):
        """Check API performance metrics."""
        # Get recent API response times from CloudWatch
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='Kessan/Business',
                MetricName='APIResponseTime',
                Dimensions=[
                    {'Name': 'Endpoint', 'Value': '/stocks/search'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                avg_response_time = response['Datapoints'][-1]['Average']
                if avg_response_time > 1000:  # 1 second
                    await self.alert_manager.send_alert(
                        title="Slow API Response",
                        message=f"Stock search API response time is {avg_response_time}ms",
                        severity=AlertSeverity.MEDIUM,
                        context={"response_time_ms": avg_response_time}
                    )
        except Exception as e:
            print(f"Failed to check API performance: {e}")
    
    async def _check_database_performance(self):
        """Check database performance metrics."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[
                    {'Name': 'DBInstanceIdentifier', 'Value': 'kessan-db-prod'}
                ],
                StartTime=datetime.utcnow() - timedelta(minutes=5),
                EndTime=datetime.utcnow(),
                Period=300,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                connection_count = response['Datapoints'][-1]['Average']
                if connection_count > 80:  # 80% of max connections
                    await self.alert_manager.send_alert(
                        title="High Database Connections",
                        message=f"Database connection count is {connection_count}",
                        severity=AlertSeverity.HIGH,
                        context={"connection_count": connection_count}
                    )
        except Exception as e:
            print(f"Failed to check database performance: {e}")

def initialize_performance_alerts(alert_manager):
    """Initialize performance alert monitoring."""
    return PerformanceAlertManager(alert_manager)
```

## Log Analysis and Troubleshooting

### 1. Common Log Queries

```bash
# CloudWatch Insights queries for troubleshooting

# Find all errors in the last hour
fields @timestamp, @message, error_type, error_message, user_id
| filter @timestamp > @timestamp - 1h
| filter @message like /application_error/
| sort @timestamp desc

# API performance analysis
fields @timestamp, path, response_time_ms, status_code
| filter @message like /api_request/
| filter response_time_ms > 1000
| stats avg(response_time_ms), max(response_time_ms), count() by path
| sort avg desc

# User activity analysis
fields @timestamp, user_id, action, details
| filter @message like /user_action/
| filter @timestamp > @timestamp - 24h
| stats count() by action
| sort count desc

# External API cost tracking
fields @timestamp, provider, cost_usd
| filter @message like /external_api_call/
| filter @timestamp > @timestamp - 24h
| stats sum(cost_usd) by provider
| sort sum desc
```

### 2. Troubleshooting Runbook

```markdown
# Troubleshooting Runbook

## High Response Times
1. Check CloudWatch dashboard for API response times
2. Check database query performance
3. Check Redis cache hit rates
4. Review recent deployments
5. Scale ECS services if needed

## Database Connection Issues
1. Check RDS connection count metrics
2. Review application connection pooling
3. Check for long-running queries
4. Consider read replica for read-heavy workloads

## High Error Rates
1. Check CloudWatch logs for error patterns
2. Review recent code deployments
3. Check external API status
4. Verify environment variables and secrets

## Memory/CPU Issues
1. Check ECS service metrics
2. Review application memory usage patterns
3. Check for memory leaks in long-running processes
4. Scale ECS services vertically or horizontally
```

This comprehensive monitoring setup provides visibility into all aspects of the system performance, user behavior, and business metrics, enabling proactive issue detection and resolution.