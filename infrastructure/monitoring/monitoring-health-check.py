#!/usr/bin/env python3
"""
Monitoring Health Check Script

This script validates that all monitoring components are working correctly
and can be run as a scheduled job to ensure monitoring system health.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class MonitoringHealthChecker:
    """Checks the health of monitoring infrastructure."""
    
    def __init__(self, project_name: str = "kessan", environment: str = "prod", region: str = "ap-northeast-1"):
        self.project_name = project_name
        self.environment = environment
        self.region = region
        
        # AWS clients
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        
        self.stack_name = f"{project_name}-{environment}-monitoring"
    
    async def run_all_checks(self) -> List[HealthCheck]:
        """Run all monitoring health checks."""
        print("🔍 Running monitoring health checks...")
        
        checks = []
        
        # Run individual checks
        checks.append(await self.check_cloudformation_stacks())
        checks.append(await self.check_cloudwatch_dashboards())
        checks.append(await self.check_cloudwatch_alarms())
        checks.append(await self.check_sns_topics())
        checks.append(await self.check_lambda_functions())
        checks.append(await self.check_metric_data_availability())
        checks.append(await self.check_alarm_states())
        checks.append(await self.check_notification_channels())
        
        return checks
    
    async def check_cloudformation_stacks(self) -> HealthCheck:
        """Check CloudFormation stack health."""
        try:
            stacks_to_check = [
                f"{self.stack_name}-dashboards",
                f"{self.stack_name}-alarms"
            ]
            
            stack_statuses = {}
            all_healthy = True
            
            for stack_name in stacks_to_check:
                try:
                    response = self.cloudformation.describe_stacks(StackName=stack_name)
                    stack = response['Stacks'][0]
                    status = stack['StackStatus']
                    stack_statuses[stack_name] = status
                    
                    if status not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                        all_healthy = False
                
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        stack_statuses[stack_name] = 'NOT_FOUND'
                        all_healthy = False
                    else:
                        raise
            
            if all_healthy:
                return HealthCheck(
                    name="CloudFormation Stacks",
                    status=HealthStatus.HEALTHY,
                    message="All monitoring stacks are in healthy state",
                    details=stack_statuses,
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="CloudFormation Stacks",
                    status=HealthStatus.CRITICAL,
                    message="Some monitoring stacks are not in healthy state",
                    details=stack_statuses,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="CloudFormation Stacks",
                status=HealthStatus.CRITICAL,
                message=f"Error checking CloudFormation stacks: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_cloudwatch_dashboards(self) -> HealthCheck:
        """Check CloudWatch dashboard availability."""
        try:
            expected_dashboards = [
                f"{self.project_name}-{self.environment}-application",
                f"{self.project_name}-{self.environment}-business",
                f"{self.project_name}-{self.environment}-infrastructure"
            ]
            
            response = self.cloudwatch.list_dashboards()
            existing_dashboards = [d['DashboardName'] for d in response['DashboardEntries']]
            
            dashboard_status = {}
            missing_dashboards = []
            
            for dashboard in expected_dashboards:
                if dashboard in existing_dashboards:
                    dashboard_status[dashboard] = "EXISTS"
                else:
                    dashboard_status[dashboard] = "MISSING"
                    missing_dashboards.append(dashboard)
            
            if not missing_dashboards:
                return HealthCheck(
                    name="CloudWatch Dashboards",
                    status=HealthStatus.HEALTHY,
                    message="All expected dashboards are available",
                    details=dashboard_status,
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="CloudWatch Dashboards",
                    status=HealthStatus.WARNING,
                    message=f"Missing dashboards: {', '.join(missing_dashboards)}",
                    details=dashboard_status,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="CloudWatch Dashboards",
                status=HealthStatus.CRITICAL,
                message=f"Error checking dashboards: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_cloudwatch_alarms(self) -> HealthCheck:
        """Check CloudWatch alarms configuration."""
        try:
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=f"{self.project_name}-{self.environment}"
            )
            
            alarms = response['MetricAlarms']
            alarm_count = len(alarms)
            
            # Expected minimum number of alarms
            expected_min_alarms = 10
            
            alarm_states = {}
            for alarm in alarms:
                alarm_states[alarm['AlarmName']] = alarm['StateValue']
            
            if alarm_count >= expected_min_alarms:
                return HealthCheck(
                    name="CloudWatch Alarms",
                    status=HealthStatus.HEALTHY,
                    message=f"Found {alarm_count} configured alarms",
                    details={
                        "alarm_count": alarm_count,
                        "alarm_states": alarm_states
                    },
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="CloudWatch Alarms",
                    status=HealthStatus.WARNING,
                    message=f"Only {alarm_count} alarms found, expected at least {expected_min_alarms}",
                    details={
                        "alarm_count": alarm_count,
                        "expected_min": expected_min_alarms,
                        "alarm_states": alarm_states
                    },
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="CloudWatch Alarms",
                status=HealthStatus.CRITICAL,
                message=f"Error checking alarms: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_sns_topics(self) -> HealthCheck:
        """Check SNS topics for notifications."""
        try:
            expected_topics = [
                f"{self.project_name}-{self.environment}-critical-alerts",
                f"{self.project_name}-{self.environment}-warning-alerts"
            ]
            
            response = self.sns.list_topics()
            existing_topics = [topic['TopicArn'].split(':')[-1] for topic in response['Topics']]
            
            topic_status = {}
            missing_topics = []
            
            for topic in expected_topics:
                if topic in existing_topics:
                    topic_status[topic] = "EXISTS"
                    
                    # Check topic attributes
                    topic_arn = next(
                        (t['TopicArn'] for t in response['Topics'] if t['TopicArn'].endswith(topic)),
                        None
                    )
                    
                    if topic_arn:
                        attrs_response = self.sns.get_topic_attributes(TopicArn=topic_arn)
                        subscriptions_response = self.sns.list_subscriptions_by_topic(TopicArn=topic_arn)
                        
                        topic_status[f"{topic}_subscriptions"] = len(subscriptions_response['Subscriptions'])
                else:
                    topic_status[topic] = "MISSING"
                    missing_topics.append(topic)
            
            if not missing_topics:
                return HealthCheck(
                    name="SNS Topics",
                    status=HealthStatus.HEALTHY,
                    message="All expected SNS topics are configured",
                    details=topic_status,
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="SNS Topics",
                    status=HealthStatus.WARNING,
                    message=f"Missing SNS topics: {', '.join(missing_topics)}",
                    details=topic_status,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="SNS Topics",
                status=HealthStatus.CRITICAL,
                message=f"Error checking SNS topics: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_lambda_functions(self) -> HealthCheck:
        """Check Lambda functions for notifications."""
        try:
            expected_functions = [
                f"{self.project_name}-{self.environment}-slack-notifier"
            ]
            
            function_status = {}
            
            for function_name in expected_functions:
                try:
                    response = self.lambda_client.get_function(FunctionName=function_name)
                    function_status[function_name] = {
                        "state": response['Configuration']['State'],
                        "last_modified": response['Configuration']['LastModified'],
                        "runtime": response['Configuration']['Runtime']
                    }
                
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        function_status[function_name] = "NOT_FOUND"
                    else:
                        function_status[function_name] = f"ERROR: {str(e)}"
            
            # Check if all functions exist and are active
            all_healthy = all(
                isinstance(status, dict) and status.get('state') == 'Active'
                for status in function_status.values()
            )
            
            if all_healthy:
                return HealthCheck(
                    name="Lambda Functions",
                    status=HealthStatus.HEALTHY,
                    message="All notification Lambda functions are active",
                    details=function_status,
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="Lambda Functions",
                    status=HealthStatus.WARNING,
                    message="Some Lambda functions are not active or missing",
                    details=function_status,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="Lambda Functions",
                status=HealthStatus.CRITICAL,
                message=f"Error checking Lambda functions: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_metric_data_availability(self) -> HealthCheck:
        """Check if metric data is being received."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            # Check for basic AWS metrics
            metrics_to_check = [
                {
                    'namespace': 'AWS/ApplicationELB',
                    'metric_name': 'RequestCount',
                    'dimensions': [{'Name': 'LoadBalancer', 'Value': f'{self.project_name}-{self.environment}-alb'}]
                },
                {
                    'namespace': 'AWS/ECS',
                    'metric_name': 'CPUUtilization',
                    'dimensions': [
                        {'Name': 'ServiceName', 'Value': f'{self.project_name}-{self.environment}-backend'},
                        {'Name': 'ClusterName', 'Value': f'{self.project_name}-{self.environment}-cluster'}
                    ]
                }
            ]
            
            metric_status = {}
            
            for metric in metrics_to_check:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace=metric['namespace'],
                        MetricName=metric['metric_name'],
                        Dimensions=metric['dimensions'],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Average']
                    )
                    
                    datapoint_count = len(response['Datapoints'])
                    metric_key = f"{metric['namespace']}/{metric['metric_name']}"
                    metric_status[metric_key] = {
                        "datapoints": datapoint_count,
                        "has_recent_data": datapoint_count > 0
                    }
                
                except ClientError as e:
                    metric_key = f"{metric['namespace']}/{metric['metric_name']}"
                    metric_status[metric_key] = f"ERROR: {str(e)}"
            
            # Check if we have recent data
            has_recent_data = any(
                isinstance(status, dict) and status.get('has_recent_data', False)
                for status in metric_status.values()
            )
            
            if has_recent_data:
                return HealthCheck(
                    name="Metric Data Availability",
                    status=HealthStatus.HEALTHY,
                    message="Recent metric data is available",
                    details=metric_status,
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="Metric Data Availability",
                    status=HealthStatus.WARNING,
                    message="No recent metric data found",
                    details=metric_status,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="Metric Data Availability",
                status=HealthStatus.CRITICAL,
                message=f"Error checking metric data: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_alarm_states(self) -> HealthCheck:
        """Check current alarm states for any critical issues."""
        try:
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=f"{self.project_name}-{self.environment}",
                StateValue='ALARM'
            )
            
            active_alarms = response['MetricAlarms']
            alarm_count = len(active_alarms)
            
            alarm_details = {}
            critical_alarms = []
            
            for alarm in active_alarms:
                alarm_name = alarm['AlarmName']
                alarm_details[alarm_name] = {
                    "state_reason": alarm['StateReason'],
                    "state_updated": alarm['StateUpdatedTimestamp'].isoformat(),
                    "threshold": alarm['Threshold'],
                    "comparison": alarm['ComparisonOperator']
                }
                
                # Check if it's a critical alarm
                if 'critical' in alarm_name.lower():
                    critical_alarms.append(alarm_name)
            
            if alarm_count == 0:
                return HealthCheck(
                    name="Alarm States",
                    status=HealthStatus.HEALTHY,
                    message="No alarms are currently in ALARM state",
                    details={"active_alarms": 0},
                    timestamp=datetime.utcnow()
                )
            elif critical_alarms:
                return HealthCheck(
                    name="Alarm States",
                    status=HealthStatus.CRITICAL,
                    message=f"Critical alarms are active: {', '.join(critical_alarms)}",
                    details={
                        "active_alarms": alarm_count,
                        "critical_alarms": critical_alarms,
                        "alarm_details": alarm_details
                    },
                    timestamp=datetime.utcnow()
                )
            else:
                return HealthCheck(
                    name="Alarm States",
                    status=HealthStatus.WARNING,
                    message=f"{alarm_count} non-critical alarms are active",
                    details={
                        "active_alarms": alarm_count,
                        "alarm_details": alarm_details
                    },
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="Alarm States",
                status=HealthStatus.CRITICAL,
                message=f"Error checking alarm states: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )
    
    async def check_notification_channels(self) -> HealthCheck:
        """Check notification channel health."""
        try:
            # This is a basic check - in production you might want to send test notifications
            notification_status = {}
            
            # Check SNS topic subscriptions
            try:
                topics_response = self.sns.list_topics()
                monitoring_topics = [
                    topic for topic in topics_response['Topics']
                    if f"{self.project_name}-{self.environment}" in topic['TopicArn']
                ]
                
                total_subscriptions = 0
                for topic in monitoring_topics:
                    subs_response = self.sns.list_subscriptions_by_topic(TopicArn=topic['TopicArn'])
                    subscriptions = subs_response['Subscriptions']
                    total_subscriptions += len(subscriptions)
                    
                    topic_name = topic['TopicArn'].split(':')[-1]
                    notification_status[topic_name] = {
                        "subscription_count": len(subscriptions),
                        "protocols": [sub['Protocol'] for sub in subscriptions]
                    }
                
                if total_subscriptions > 0:
                    return HealthCheck(
                        name="Notification Channels",
                        status=HealthStatus.HEALTHY,
                        message=f"Found {total_subscriptions} active notification subscriptions",
                        details=notification_status,
                        timestamp=datetime.utcnow()
                    )
                else:
                    return HealthCheck(
                        name="Notification Channels",
                        status=HealthStatus.WARNING,
                        message="No notification subscriptions found",
                        details=notification_status,
                        timestamp=datetime.utcnow()
                    )
            
            except Exception as e:
                return HealthCheck(
                    name="Notification Channels",
                    status=HealthStatus.WARNING,
                    message=f"Could not verify notification channels: {str(e)}",
                    details={},
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            return HealthCheck(
                name="Notification Channels",
                status=HealthStatus.CRITICAL,
                message=f"Error checking notification channels: {str(e)}",
                details={},
                timestamp=datetime.utcnow()
            )


def format_health_report(checks: List[HealthCheck]) -> str:
    """Format health check results for console output."""
    output = []
    
    # Header
    output.append("=" * 80)
    output.append("🏥 MONITORING HEALTH CHECK REPORT")
    output.append("=" * 80)
    output.append(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    output.append("")
    
    # Summary
    healthy_count = sum(1 for check in checks if check.status == HealthStatus.HEALTHY)
    warning_count = sum(1 for check in checks if check.status == HealthStatus.WARNING)
    critical_count = sum(1 for check in checks if check.status == HealthStatus.CRITICAL)
    unknown_count = sum(1 for check in checks if check.status == HealthStatus.UNKNOWN)
    
    output.append("📊 SUMMARY")
    output.append("-" * 40)
    output.append(f"Total Checks: {len(checks)}")
    output.append(f"Healthy: {healthy_count} ✅")
    output.append(f"Warning: {warning_count} ⚠️")
    output.append(f"Critical: {critical_count} ❌")
    output.append(f"Unknown: {unknown_count} ❓")
    output.append("")
    
    # Detailed results
    output.append("📋 DETAILED RESULTS")
    output.append("-" * 40)
    
    for check in checks:
        status_icon = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓"
        }[check.status]
        
        output.append(f"{status_icon} {check.name}")
        output.append(f"   Status: {check.status.value.upper()}")
        output.append(f"   Message: {check.message}")
        
        if check.details:
            output.append(f"   Details: {json.dumps(check.details, indent=6, default=str)}")
        
        output.append("")
    
    output.append("=" * 80)
    
    return "\n".join(output)


async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring Health Check")
    parser.add_argument("--project", default="kessan", help="Project name")
    parser.add_argument("--environment", default="prod", help="Environment name")
    parser.add_argument("--region", default="ap-northeast-1", help="AWS region")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--format", choices=["console", "json"], default="console", help="Output format")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    
    args = parser.parse_args()
    
    # Create health checker
    checker = MonitoringHealthChecker(args.project, args.environment, args.region)
    
    # Run health checks
    if not args.quiet:
        print(f"🔍 Running monitoring health checks for {args.project}-{args.environment}...")
    
    checks = await checker.run_all_checks()
    
    # Determine overall status
    has_critical = any(check.status == HealthStatus.CRITICAL for check in checks)
    has_warning = any(check.status == HealthStatus.WARNING for check in checks)
    
    # Output results
    if args.format == "json":
        # Convert to JSON-serializable format
        json_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "project": args.project,
            "environment": args.environment,
            "region": args.region,
            "overall_status": "critical" if has_critical else "warning" if has_warning else "healthy",
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                    "timestamp": check.timestamp.isoformat()
                }
                for check in checks
            ]
        }
        
        json_output = json.dumps(json_data, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            if not args.quiet:
                print(f"📄 JSON report saved to: {args.output}")
        else:
            print(json_output)
    
    else:
        # Console output
        console_output = format_health_report(checks)
        
        if not args.quiet:
            print(console_output)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(console_output)
            if not args.quiet:
                print(f"📄 Report saved to: {args.output}")
    
    # Exit with appropriate code
    if has_critical:
        sys.exit(1)
    elif has_warning:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())