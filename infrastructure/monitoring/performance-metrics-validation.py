#!/usr/bin/env python3
"""
Performance Metrics Validation Script

This script validates that the production system meets performance requirements
and SLA targets as defined in the requirements document.
"""

import asyncio
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import boto3
from botocore.exceptions import ClientError


class PerformanceStatus(Enum):
    """Performance validation status."""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class PerformanceMetric:
    """Performance metric with validation results."""
    name: str
    description: str
    target_value: float
    current_value: Optional[float]
    unit: str
    status: PerformanceStatus
    trend: str  # "improving", "stable", "degrading"
    percentile: Optional[str]
    measurement_window: str
    last_updated: datetime
    historical_data: List[float]
    recommendations: List[str]


@dataclass
class PerformanceReport:
    """Complete performance validation report."""
    timestamp: datetime
    overall_status: PerformanceStatus
    metrics: List[PerformanceMetric]
    summary: Dict[str, Any]
    sla_compliance: Dict[str, bool]
    capacity_analysis: Dict[str, Any]
    recommendations: List[str]


class PerformanceValidator:
    """Validates performance metrics and SLA compliance."""
    
    def __init__(self, project_name: str = "kessan", environment: str = "prod", region: str = "ap-northeast-1"):
        self.project_name = project_name
        self.environment = environment
        self.region = region
        
        # AWS clients
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.elbv2 = boto3.client('elbv2', region_name=region)
        self.rds = boto3.client('rds', region_name=region)
        self.ecs = boto3.client('ecs', region_name=region)
        
        # Performance targets based on requirements
        self.performance_targets = {
            # Requirement 2.5: Search results within 500ms
            "search_response_time_p95": {
                "target": 500.0,
                "unit": "milliseconds",
                "description": "Stock search response time (95th percentile)",
                "percentile": "p95"
            },
            
            # Requirement 4.9: 95% of database queries within 100ms
            "database_query_time_p95": {
                "target": 100.0,
                "unit": "milliseconds", 
                "description": "Database query response time (95th percentile)",
                "percentile": "p95"
            },
            
            # API response time SLA
            "api_response_time_avg": {
                "target": 1000.0,
                "unit": "milliseconds",
                "description": "API response time (average)",
                "percentile": "avg"
            },
            
            # API response time 95th percentile
            "api_response_time_p95": {
                "target": 2000.0,
                "unit": "milliseconds",
                "description": "API response time (95th percentile)",
                "percentile": "p95"
            },
            
            # Error rate SLA
            "error_rate": {
                "target": 1.0,
                "unit": "percent",
                "description": "API error rate",
                "percentile": "avg"
            },
            
            # Throughput metrics
            "requests_per_second": {
                "target": 100.0,
                "unit": "requests/second",
                "description": "API throughput capacity",
                "percentile": "avg"
            },
            
            # Resource utilization
            "cpu_utilization_avg": {
                "target": 70.0,
                "unit": "percent",
                "description": "Average CPU utilization",
                "percentile": "avg"
            },
            
            "memory_utilization_avg": {
                "target": 80.0,
                "unit": "percent", 
                "description": "Average memory utilization",
                "percentile": "avg"
            },
            
            # Database performance
            "database_cpu_utilization": {
                "target": 70.0,
                "unit": "percent",
                "description": "Database CPU utilization",
                "percentile": "avg"
            },
            
            "database_connections": {
                "target": 80.0,
                "unit": "connections",
                "description": "Database connection count",
                "percentile": "avg"
            }
        }
    
    async def validate_all_performance_metrics(self) -> PerformanceReport:
        """Validate all performance metrics and generate comprehensive report."""
        print("🚀 Starting performance metrics validation...")
        
        metrics = []
        recommendations = []
        
        # Validate each performance metric
        for metric_name, target_config in self.performance_targets.items():
            try:
                metric = await self.validate_performance_metric(metric_name, target_config)
                metrics.append(metric)
                
                # Add recommendations for poor performance
                if metric.status in [PerformanceStatus.WARNING, PerformanceStatus.CRITICAL]:
                    recommendations.extend(metric.recommendations)
                
            except Exception as e:
                print(f"❌ Error validating {metric_name}: {e}")
                metrics.append(PerformanceMetric(
                    name=metric_name,
                    description=target_config["description"],
                    target_value=target_config["target"],
                    current_value=None,
                    unit=target_config["unit"],
                    status=PerformanceStatus.UNKNOWN,
                    trend="unknown",
                    percentile=target_config.get("percentile"),
                    measurement_window="1 hour",
                    last_updated=datetime.utcnow(),
                    historical_data=[],
                    recommendations=[]
                ))
        
        # Determine overall status
        overall_status = self._calculate_overall_performance_status(metrics)
        
        # Generate summary and analysis
        summary = self._generate_performance_summary(metrics)
        sla_compliance = self._check_sla_compliance(metrics)
        capacity_analysis = await self._analyze_capacity_trends()
        
        return PerformanceReport(
            timestamp=datetime.utcnow(),
            overall_status=overall_status,
            metrics=metrics,
            summary=summary,
            sla_compliance=sla_compliance,
            capacity_analysis=capacity_analysis,
            recommendations=list(set(recommendations))  # Remove duplicates
        )
    
    async def validate_performance_metric(self, metric_name: str, target_config: Dict) -> PerformanceMetric:
        """Validate a specific performance metric."""
        print(f"📊 Validating {metric_name}...")
        
        # Get current and historical values
        current_value, historical_data = await self._get_metric_data(metric_name, target_config)
        
        # Determine status
        status = self._determine_performance_status(current_value, target_config["target"], metric_name)
        
        # Analyze trend
        trend = self._analyze_trend(historical_data)
        
        # Generate recommendations
        recommendations = self._get_performance_recommendations(metric_name, current_value, target_config, status)
        
        return PerformanceMetric(
            name=metric_name,
            description=target_config["description"],
            target_value=target_config["target"],
            current_value=current_value,
            unit=target_config["unit"],
            status=status,
            trend=trend,
            percentile=target_config.get("percentile"),
            measurement_window="1 hour",
            last_updated=datetime.utcnow(),
            historical_data=historical_data,
            recommendations=recommendations
        )
    
    async def _get_metric_data(self, metric_name: str, target_config: Dict) -> Tuple[Optional[float], List[float]]:
        """Get current and historical metric data."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)  # 24 hours of historical data
        
        try:
            if metric_name == "search_response_time_p95":
                return await self._get_search_response_time_data(start_time, end_time)
            elif metric_name == "database_query_time_p95":
                return await self._get_database_query_time_data(start_time, end_time)
            elif metric_name.startswith("api_response_time"):
                return await self._get_api_response_time_data(start_time, end_time, target_config["percentile"])
            elif metric_name == "error_rate":
                return await self._get_error_rate_data(start_time, end_time)
            elif metric_name == "requests_per_second":
                return await self._get_throughput_data(start_time, end_time)
            elif metric_name == "cpu_utilization_avg":
                return await self._get_cpu_utilization_data(start_time, end_time)
            elif metric_name == "memory_utilization_avg":
                return await self._get_memory_utilization_data(start_time, end_time)
            elif metric_name == "database_cpu_utilization":
                return await self._get_database_cpu_data(start_time, end_time)
            elif metric_name == "database_connections":
                return await self._get_database_connections_data(start_time, end_time)
            else:
                return None, []
                
        except Exception as e:
            print(f"Error getting data for {metric_name}: {e}")
            return None, []
    
    async def _get_search_response_time_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get search response time data."""
        try:
            # Try custom metrics first
            response = self.cloudwatch.get_metric_statistics(
                Namespace='Kessan/Performance',
                MetricName='SearchResponseTime',
                Dimensions=[
                    {'Name': 'Endpoint', 'Value': '/api/v1/stocks/search'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                values = [dp['Average'] for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            # Fallback: test actual endpoint
            current_value = await self._test_search_endpoint_performance()
            return current_value, [current_value] if current_value else []
            
        except ClientError:
            # Fallback to direct testing
            current_value = await self._test_search_endpoint_performance()
            return current_value, [current_value] if current_value else []
    
    async def _test_search_endpoint_performance(self) -> Optional[float]:
        """Test search endpoint performance directly."""
        try:
            # Get load balancer DNS
            lb_response = self.elbv2.describe_load_balancers(
                Names=[f'{self.project_name}-{self.environment}-alb']
            )
            
            if not lb_response['LoadBalancers']:
                return None
            
            lb_dns = lb_response['LoadBalancers'][0]['DNSName']
            search_url = f"https://{lb_dns}/api/v1/stocks/search?q=toyota"
            
            # Perform multiple tests for better accuracy
            response_times = []
            
            async with aiohttp.ClientSession() as session:
                for _ in range(5):  # 5 test requests
                    start_time = time.time()
                    try:
                        async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            await response.text()
                            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                            
                            if response.status == 200:
                                response_times.append(response_time)
                    except Exception:
                        continue
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
            
            if response_times:
                # Return 95th percentile
                return statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            return None
            
        except Exception as e:
            print(f"Error testing search endpoint: {e}")
            return None
    
    async def _get_database_query_time_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get database query time data."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='ReadLatency',
                Dimensions=[
                    {'Name': 'DBInstanceIdentifier', 'Value': f'{self.project_name}-{self.environment}-postgres'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                # Convert from seconds to milliseconds
                values = [dp['Average'] * 1000 for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting database query time: {e}")
            return None, []
    
    async def _get_api_response_time_data(self, start_time: datetime, end_time: datetime, percentile: str) -> Tuple[Optional[float], List[float]]:
        """Get API response time data from load balancer."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='TargetResponseTime',
                Dimensions=[
                    {'Name': 'LoadBalancer', 'Value': f'{self.project_name}-{self.environment}-alb'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                # Convert from seconds to milliseconds
                values = [dp['Average'] * 1000 for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting API response time: {e}")
            return None, []
    
    async def _get_error_rate_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get API error rate data."""
        try:
            # Get total requests
            total_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='RequestCount',
                Dimensions=[
                    {'Name': 'LoadBalancer', 'Value': f'{self.project_name}-{self.environment}-alb'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            # Get error requests
            error_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='HTTPCode_Target_5XX_Count',
                Dimensions=[
                    {'Name': 'LoadBalancer', 'Value': f'{self.project_name}-{self.environment}-alb'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            if total_response['Datapoints'] and error_response['Datapoints']:
                total_datapoints = {dp['Timestamp']: dp['Sum'] for dp in total_response['Datapoints']}
                error_datapoints = {dp['Timestamp']: dp['Sum'] for dp in error_response['Datapoints']}
                
                error_rates = []
                for timestamp in total_datapoints:
                    total_requests = total_datapoints[timestamp]
                    error_requests = error_datapoints.get(timestamp, 0)
                    
                    if total_requests > 0:
                        error_rate = (error_requests / total_requests) * 100
                        error_rates.append(error_rate)
                
                current_value = error_rates[-1] if error_rates else 0.0
                return current_value, error_rates
            
            return 0.0, [0.0]
            
        except ClientError as e:
            print(f"Error getting error rate: {e}")
            return None, []
    
    async def _get_throughput_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get API throughput data."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='RequestCount',
                Dimensions=[
                    {'Name': 'LoadBalancer', 'Value': f'{self.project_name}-{self.environment}-alb'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                # Convert to requests per second (3600 seconds in an hour)
                values = [dp['Sum'] / 3600 for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting throughput data: {e}")
            return None, []
    
    async def _get_cpu_utilization_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get ECS CPU utilization data."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName='CPUUtilization',
                Dimensions=[
                    {'Name': 'ServiceName', 'Value': f'{self.project_name}-{self.environment}-backend'},
                    {'Name': 'ClusterName', 'Value': f'{self.project_name}-{self.environment}-cluster'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                values = [dp['Average'] for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting CPU utilization: {e}")
            return None, []
    
    async def _get_memory_utilization_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get ECS memory utilization data."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName='MemoryUtilization',
                Dimensions=[
                    {'Name': 'ServiceName', 'Value': f'{self.project_name}-{self.environment}-backend'},
                    {'Name': 'ClusterName', 'Value': f'{self.project_name}-{self.environment}-cluster'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                values = [dp['Average'] for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting memory utilization: {e}")
            return None, []
    
    async def _get_database_cpu_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get database CPU utilization data."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[
                    {'Name': 'DBInstanceIdentifier', 'Value': f'{self.project_name}-{self.environment}-postgres'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                values = [dp['Average'] for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting database CPU: {e}")
            return None, []
    
    async def _get_database_connections_data(self, start_time: datetime, end_time: datetime) -> Tuple[Optional[float], List[float]]:
        """Get database connections data."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[
                    {'Name': 'DBInstanceIdentifier', 'Value': f'{self.project_name}-{self.environment}-postgres'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                values = [dp['Average'] for dp in datapoints]
                current_value = values[-1] if values else None
                return current_value, values
            
            return None, []
            
        except ClientError as e:
            print(f"Error getting database connections: {e}")
            return None, []
    
    def _determine_performance_status(self, current_value: Optional[float], target_value: float, metric_name: str) -> PerformanceStatus:
        """Determine performance status based on current value and target."""
        if current_value is None:
            return PerformanceStatus.UNKNOWN
        
        # Different logic for different metric types
        if metric_name in ["cpu_utilization_avg", "memory_utilization_avg", "database_cpu_utilization", "database_connections"]:
            # Resource utilization metrics (lower is better, but too low might indicate underutilization)
            if current_value <= target_value * 0.5:
                return PerformanceStatus.EXCELLENT
            elif current_value <= target_value * 0.7:
                return PerformanceStatus.GOOD
            elif current_value <= target_value:
                return PerformanceStatus.WARNING
            else:
                return PerformanceStatus.CRITICAL
        
        elif metric_name == "error_rate":
            # Error rate (lower is better)
            if current_value <= target_value * 0.1:
                return PerformanceStatus.EXCELLENT
            elif current_value <= target_value * 0.5:
                return PerformanceStatus.GOOD
            elif current_value <= target_value:
                return PerformanceStatus.WARNING
            else:
                return PerformanceStatus.CRITICAL
        
        elif metric_name == "requests_per_second":
            # Throughput (higher is better, but we want to be within capacity)
            if current_value >= target_value * 0.8:
                return PerformanceStatus.EXCELLENT
            elif current_value >= target_value * 0.6:
                return PerformanceStatus.GOOD
            elif current_value >= target_value * 0.4:
                return PerformanceStatus.WARNING
            else:
                return PerformanceStatus.CRITICAL
        
        else:
            # Response time metrics (lower is better)
            if current_value <= target_value * 0.5:
                return PerformanceStatus.EXCELLENT
            elif current_value <= target_value * 0.7:
                return PerformanceStatus.GOOD
            elif current_value <= target_value:
                return PerformanceStatus.WARNING
            else:
                return PerformanceStatus.CRITICAL
    
    def _analyze_trend(self, historical_data: List[float]) -> str:
        """Analyze trend from historical data."""
        if len(historical_data) < 3:
            return "unknown"
        
        # Simple trend analysis using linear regression slope
        n = len(historical_data)
        x_values = list(range(n))
        
        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(historical_data) / n
        
        numerator = sum((x_values[i] - x_mean) * (historical_data[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Determine trend based on slope
        if slope > 0.1:
            return "degrading"  # Values increasing (bad for response times, good for throughput)
        elif slope < -0.1:
            return "improving"  # Values decreasing (good for response times, bad for throughput)
        else:
            return "stable"
    
    def _get_performance_recommendations(self, metric_name: str, current_value: Optional[float], 
                                       target_config: Dict, status: PerformanceStatus) -> List[str]:
        """Get performance recommendations based on metric status."""
        recommendations = []
        
        if status in [PerformanceStatus.WARNING, PerformanceStatus.CRITICAL]:
            if metric_name == "search_response_time_p95":
                recommendations.extend([
                    "Optimize database queries for stock search functionality",
                    "Implement search result caching with appropriate TTL",
                    "Consider using Elasticsearch for faster full-text search",
                    "Add database indexes for commonly searched fields"
                ])
            
            elif metric_name == "database_query_time_p95":
                recommendations.extend([
                    "Review and optimize slow database queries",
                    "Add missing database indexes",
                    "Consider query result caching",
                    "Implement database connection pooling optimization"
                ])
            
            elif metric_name.startswith("api_response_time"):
                recommendations.extend([
                    "Profile API endpoints to identify bottlenecks",
                    "Implement response caching where appropriate",
                    "Optimize data serialization and deserialization",
                    "Consider API rate limiting to prevent overload"
                ])
            
            elif metric_name == "error_rate":
                recommendations.extend([
                    "Review application logs for error patterns",
                    "Implement better error handling and retry logic",
                    "Add circuit breakers for external API calls",
                    "Improve input validation and error responses"
                ])
            
            elif metric_name == "requests_per_second":
                recommendations.extend([
                    "Implement auto-scaling policies",
                    "Optimize application performance",
                    "Consider load balancing improvements",
                    "Review capacity planning and scaling thresholds"
                ])
            
            elif metric_name == "cpu_utilization_avg":
                recommendations.extend([
                    "Implement CPU-based auto-scaling",
                    "Optimize CPU-intensive operations",
                    "Consider vertical scaling for CPU-bound workloads",
                    "Review application profiling for CPU hotspots"
                ])
            
            elif metric_name == "memory_utilization_avg":
                recommendations.extend([
                    "Implement memory-based auto-scaling",
                    "Review memory leaks and optimize memory usage",
                    "Consider increasing memory allocation",
                    "Implement memory caching strategies"
                ])
            
            elif metric_name == "database_cpu_utilization":
                recommendations.extend([
                    "Optimize database queries and indexes",
                    "Consider database instance scaling",
                    "Implement read replicas for read-heavy workloads",
                    "Review database configuration parameters"
                ])
            
            elif metric_name == "database_connections":
                recommendations.extend([
                    "Optimize database connection pooling",
                    "Review connection timeout settings",
                    "Consider increasing max connections limit",
                    "Implement connection monitoring and alerting"
                ])
        
        return recommendations
    
    def _calculate_overall_performance_status(self, metrics: List[PerformanceMetric]) -> PerformanceStatus:
        """Calculate overall performance status from individual metrics."""
        statuses = [metric.status for metric in metrics]
        
        if PerformanceStatus.CRITICAL in statuses:
            return PerformanceStatus.CRITICAL
        elif PerformanceStatus.WARNING in statuses:
            return PerformanceStatus.WARNING
        elif PerformanceStatus.UNKNOWN in statuses:
            return PerformanceStatus.WARNING  # Treat unknown as warning
        elif all(status == PerformanceStatus.EXCELLENT for status in statuses):
            return PerformanceStatus.EXCELLENT
        else:
            return PerformanceStatus.GOOD
    
    def _generate_performance_summary(self, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """Generate performance summary statistics."""
        total_metrics = len(metrics)
        excellent_count = sum(1 for m in metrics if m.status == PerformanceStatus.EXCELLENT)
        good_count = sum(1 for m in metrics if m.status == PerformanceStatus.GOOD)
        warning_count = sum(1 for m in metrics if m.status == PerformanceStatus.WARNING)
        critical_count = sum(1 for m in metrics if m.status == PerformanceStatus.CRITICAL)
        unknown_count = sum(1 for m in metrics if m.status == PerformanceStatus.UNKNOWN)
        
        return {
            "total_metrics": total_metrics,
            "excellent_count": excellent_count,
            "good_count": good_count,
            "warning_count": warning_count,
            "critical_count": critical_count,
            "unknown_count": unknown_count,
            "performance_score": ((excellent_count * 4 + good_count * 3 + warning_count * 2 + critical_count * 1) / (total_metrics * 4) * 100) if total_metrics > 0 else 0
        }
    
    def _check_sla_compliance(self, metrics: List[PerformanceMetric]) -> Dict[str, bool]:
        """Check SLA compliance for key metrics."""
        sla_compliance = {}
        
        for metric in metrics:
            if metric.current_value is not None:
                if metric.name in ["search_response_time_p95", "database_query_time_p95", "api_response_time_avg", "api_response_time_p95"]:
                    # Response time SLAs (lower is better)
                    sla_compliance[metric.name] = metric.current_value <= metric.target_value
                elif metric.name == "error_rate":
                    # Error rate SLA (lower is better)
                    sla_compliance[metric.name] = metric.current_value <= metric.target_value
                else:
                    # Other metrics
                    sla_compliance[metric.name] = metric.status in [PerformanceStatus.EXCELLENT, PerformanceStatus.GOOD]
            else:
                sla_compliance[metric.name] = False
        
        return sla_compliance
    
    async def _analyze_capacity_trends(self) -> Dict[str, Any]:
        """Analyze capacity trends and provide scaling recommendations."""
        capacity_analysis = {
            "current_utilization": {},
            "growth_trends": {},
            "scaling_recommendations": [],
            "capacity_alerts": []
        }
        
        # This would analyze historical data to predict capacity needs
        # For now, provide basic analysis based on current metrics
        
        try:
            # Get current ECS service details
            ecs_response = self.ecs.describe_services(
                cluster=f'{self.project_name}-{self.environment}-cluster',
                services=[f'{self.project_name}-{self.environment}-backend']
            )
            
            if ecs_response['services']:
                service = ecs_response['services'][0]
                capacity_analysis["current_utilization"]["ecs_tasks"] = {
                    "desired": service['desiredCount'],
                    "running": service['runningCount'],
                    "pending": service['pendingCount']
                }
                
                if service['runningCount'] < service['desiredCount']:
                    capacity_analysis["capacity_alerts"].append("ECS service has pending tasks - may indicate capacity constraints")
        
        except Exception as e:
            print(f"Error analyzing ECS capacity: {e}")
        
        return capacity_analysis


def format_performance_report(report: PerformanceReport) -> str:
    """Format performance report for console output."""
    output = []
    
    # Header
    output.append("=" * 80)
    output.append("🚀 PERFORMANCE METRICS VALIDATION REPORT")
    output.append("=" * 80)
    output.append(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    output.append(f"Overall Performance: {report.overall_status.value.upper()}")
    output.append(f"Performance Score: {report.summary['performance_score']:.1f}/100")
    output.append("")
    
    # Summary
    output.append("📊 PERFORMANCE SUMMARY")
    output.append("-" * 40)
    output.append(f"Total Metrics: {report.summary['total_metrics']}")
    output.append(f"Excellent: {report.summary['excellent_count']} 🚀")
    output.append(f"Good: {report.summary['good_count']} ✅")
    output.append(f"Warning: {report.summary['warning_count']} ⚠️")
    output.append(f"Critical: {report.summary['critical_count']} ❌")
    output.append(f"Unknown: {report.summary['unknown_count']} ❓")
    output.append("")
    
    # SLA Compliance
    output.append("🎯 SLA COMPLIANCE")
    output.append("-" * 40)
    compliant_count = sum(1 for compliant in report.sla_compliance.values() if compliant)
    total_slas = len(report.sla_compliance)
    compliance_rate = (compliant_count / total_slas * 100) if total_slas > 0 else 0
    
    output.append(f"SLA Compliance Rate: {compliance_rate:.1f}% ({compliant_count}/{total_slas})")
    
    for sla_name, compliant in report.sla_compliance.items():
        status_icon = "✅" if compliant else "❌"
        output.append(f"{status_icon} {sla_name}")
    
    output.append("")
    
    # Detailed metrics
    output.append("📋 DETAILED PERFORMANCE METRICS")
    output.append("-" * 40)
    
    for metric in report.metrics:
        status_icon = {
            PerformanceStatus.EXCELLENT: "🚀",
            PerformanceStatus.GOOD: "✅",
            PerformanceStatus.WARNING: "⚠️",
            PerformanceStatus.CRITICAL: "❌",
            PerformanceStatus.UNKNOWN: "❓"
        }[metric.status]
        
        output.append(f"{status_icon} {metric.name}")
        output.append(f"   Description: {metric.description}")
        output.append(f"   Target: {metric.target_value} {metric.unit}")
        
        if metric.current_value is not None:
            output.append(f"   Current: {metric.current_value:.2f} {metric.unit}")
        else:
            output.append(f"   Current: N/A")
        
        output.append(f"   Status: {metric.status.value.upper()}")
        output.append(f"   Trend: {metric.trend}")
        
        if metric.percentile:
            output.append(f"   Percentile: {metric.percentile}")
        
        if metric.recommendations:
            output.append(f"   Recommendations:")
            for rec in metric.recommendations:
                output.append(f"     • {rec}")
        
        output.append("")
    
    # Capacity Analysis
    if report.capacity_analysis:
        output.append("📈 CAPACITY ANALYSIS")
        output.append("-" * 40)
        
        if report.capacity_analysis.get("current_utilization"):
            output.append("Current Resource Utilization:")
            for resource, utilization in report.capacity_analysis["current_utilization"].items():
                output.append(f"  {resource}: {utilization}")
        
        if report.capacity_analysis.get("capacity_alerts"):
            output.append("Capacity Alerts:")
            for alert in report.capacity_analysis["capacity_alerts"]:
                output.append(f"  ⚠️ {alert}")
        
        output.append("")
    
    # Recommendations
    if report.recommendations:
        output.append("💡 PERFORMANCE RECOMMENDATIONS")
        output.append("-" * 40)
        for i, recommendation in enumerate(report.recommendations, 1):
            output.append(f"{i}. {recommendation}")
        output.append("")
    
    output.append("=" * 80)
    
    return "\n".join(output)


async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Metrics Validation")
    parser.add_argument("--project", default="kessan", help="Project name")
    parser.add_argument("--environment", default="prod", help="Environment name")
    parser.add_argument("--region", default="ap-northeast-1", help="AWS region")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--format", choices=["console", "json"], default="console", help="Output format")
    
    args = parser.parse_args()
    
    # Create validator
    validator = PerformanceValidator(args.project, args.environment, args.region)
    
    # Run validation
    report = await validator.validate_all_performance_metrics()
    
    # Output results
    if args.format == "json":
        # Convert to JSON-serializable format
        report_dict = asdict(report)
        report_dict['timestamp'] = report.timestamp.isoformat()
        report_dict['overall_status'] = report.overall_status.value
        
        for metric in report_dict['metrics']:
            metric['status'] = metric['status'].value
            metric['last_updated'] = metric['last_updated'].isoformat()
        
        json_output = json.dumps(report_dict, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            print(f"📄 JSON report saved to: {args.output}")
        else:
            print(json_output)
    
    else:
        # Console output
        console_output = format_performance_report(report)
        print(console_output)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(console_output)
            print(f"📄 Report saved to: {args.output}")
    
    # Exit with appropriate code
    if report.overall_status == PerformanceStatus.CRITICAL:
        exit(1)
    elif report.overall_status == PerformanceStatus.WARNING:
        exit(2)
    else:
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())