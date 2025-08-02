"""
Tests for health check functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.core.health import (
    check_database_health,
    check_redis_health,
    check_data_sources_health,
    check_external_apis_health,
    check_system_resources,
    get_system_health,
    ServiceStatus
)
from app.services.system_monitor import SystemMonitor


class TestHealthChecks:
    """Test health check functions."""
    
    @pytest.mark.asyncio
    async def test_check_database_health_success(self):
        """Test successful database health check."""
        with patch('app.core.health.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock database queries
            mock_result = Mock()
            mock_result.scalar.side_effect = [1, 5, 3]  # SELECT 1, table count, plans count
            mock_session.execute.return_value = mock_result
            
            result = await check_database_health()
            
            assert result["status"] == "healthy"
            assert "database_url" in result
            assert result["tables_count"] == 5
            assert result["plans_count"] == 3
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_check_database_health_failure(self):
        """Test database health check failure."""
        with patch('app.core.health.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.side_effect = Exception("Connection failed")
            
            result = await check_database_health()
            
            assert result["status"] == "unhealthy"
            assert "Connection failed" in result["error"]
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_check_redis_health_success(self):
        """Test successful Redis health check."""
        with patch('app.core.health.cache_manager') as mock_cache:
            mock_cache.get_cache_health.return_value = {
                "status": "healthy",
                "response_time_ms": 5.2,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = await check_redis_health()
            
            assert result["status"] == "healthy"
            assert result["response_time_ms"] == 5.2
    
    @pytest.mark.asyncio
    async def test_check_redis_health_failure(self):
        """Test Redis health check failure."""
        with patch('app.core.health.cache_manager') as mock_cache:
            mock_cache.get_cache_health.side_effect = Exception("Redis connection failed")
            
            result = await check_redis_health()
            
            assert result["status"] == "unhealthy"
            assert "Redis connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_data_sources_health_all_healthy(self):
        """Test data sources health check with all adapters healthy."""
        mock_registry_status = {
            "adapters": {
                "alpha_vantage": {
                    "health_status": "healthy",
                    "type": "stock_price",
                    "enabled": True,
                    "last_health_check": datetime.utcnow().isoformat(),
                    "response_time_ms": 150.0,
                    "error_message": None
                },
                "yahoo_finance": {
                    "health_status": "healthy",
                    "type": "stock_price",
                    "enabled": True,
                    "last_health_check": datetime.utcnow().isoformat(),
                    "response_time_ms": 200.0,
                    "error_message": None
                }
            },
            "circuit_breakers": {},
            "failover_enabled": True
        }
        
        with patch('app.core.health.data_source_registry') as mock_registry:
            mock_registry.get_registry_status.return_value = mock_registry_status
            
            result = await check_data_sources_health()
            
            assert result["status"] == ServiceStatus.HEALTHY.value
            assert result["summary"]["total"] == 2
            assert result["summary"]["healthy"] == 2
            assert result["summary"]["unhealthy"] == 0
            assert "alpha_vantage" in result["adapters"]
            assert "yahoo_finance" in result["adapters"]
    
    @pytest.mark.asyncio
    async def test_check_data_sources_health_some_unhealthy(self):
        """Test data sources health check with some adapters unhealthy."""
        mock_registry_status = {
            "adapters": {
                "alpha_vantage": {
                    "health_status": "healthy",
                    "type": "stock_price",
                    "enabled": True,
                    "last_health_check": datetime.utcnow().isoformat(),
                    "response_time_ms": 150.0,
                    "error_message": None
                },
                "yahoo_finance": {
                    "health_status": "unhealthy",
                    "type": "stock_price",
                    "enabled": True,
                    "last_health_check": datetime.utcnow().isoformat(),
                    "response_time_ms": None,
                    "error_message": "Connection timeout"
                }
            },
            "circuit_breakers": {
                "yahoo_finance": {
                    "open": True,
                    "reset_time": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                    "failure_count": 5
                }
            },
            "failover_enabled": True
        }
        
        with patch('app.core.health.data_source_registry') as mock_registry:
            mock_registry.get_registry_status.return_value = mock_registry_status
            
            result = await check_data_sources_health()
            
            assert result["status"] == ServiceStatus.DEGRADED.value
            assert result["summary"]["total"] == 2
            assert result["summary"]["healthy"] == 1
            assert result["summary"]["unhealthy"] == 1
            assert result["circuit_breakers"]["yahoo_finance"]["open"] is True
    
    @pytest.mark.asyncio
    async def test_check_external_apis_health_gemini_configured(self):
        """Test external APIs health check with Gemini configured."""
        mock_settings = Mock()
        mock_settings.GEMINI_API_KEY = "test_api_key"
        
        with patch('app.core.health.settings', mock_settings), \
             patch('app.core.health.genai') as mock_genai:
            
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            result = await check_external_apis_health()
            
            assert result["status"] in [ServiceStatus.HEALTHY.value, ServiceStatus.DEGRADED.value]
            assert "gemini_api" in result["services"]
            assert result["services"]["gemini_api"]["status"] == ServiceStatus.HEALTHY.value
    
    @pytest.mark.asyncio
    async def test_check_external_apis_health_gemini_not_configured(self):
        """Test external APIs health check with Gemini not configured."""
        mock_settings = Mock()
        mock_settings.GEMINI_API_KEY = None
        
        with patch('app.core.health.settings', mock_settings):
            result = await check_external_apis_health()
            
            assert "gemini_api" in result["services"]
            assert result["services"]["gemini_api"]["status"] == ServiceStatus.UNKNOWN.value
            assert "API key not configured" in result["services"]["gemini_api"]["error"]
    
    @pytest.mark.asyncio
    async def test_check_system_resources_healthy(self):
        """Test system resources check with healthy values."""
        mock_psutil = Mock()
        mock_psutil.cpu_percent.return_value = 45.0
        
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.free = 100 * 1024**3  # 100GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        with patch('app.core.health.psutil', mock_psutil):
            result = await check_system_resources()
            
            assert result["status"] == ServiceStatus.HEALTHY.value
            assert result["cpu_percent"] == 45.0
            assert result["memory_percent"] == 60.0
            assert result["disk_percent"] == 70.0
            assert result["memory_available_gb"] == 8.0
            assert result["disk_free_gb"] == 100.0
    
    @pytest.mark.asyncio
    async def test_check_system_resources_unhealthy(self):
        """Test system resources check with unhealthy values."""
        mock_psutil = Mock()
        mock_psutil.cpu_percent.return_value = 95.0
        
        mock_memory = Mock()
        mock_memory.percent = 92.0
        mock_memory.available = 1 * 1024**3  # 1GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.percent = 95.0
        mock_disk.free = 5 * 1024**3  # 5GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        with patch('app.core.health.psutil', mock_psutil):
            result = await check_system_resources()
            
            assert result["status"] == ServiceStatus.UNHEALTHY.value
            assert result["cpu_percent"] == 95.0
            assert result["memory_percent"] == 92.0
            assert result["disk_percent"] == 95.0
    
    @pytest.mark.asyncio
    async def test_check_system_resources_psutil_not_available(self):
        """Test system resources check when psutil is not available."""
        with patch('app.core.health.psutil', side_effect=ImportError("psutil not available")):
            result = await check_system_resources()
            
            assert result["status"] == ServiceStatus.UNKNOWN.value
            assert "psutil not available" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_system_health_all_healthy(self):
        """Test comprehensive system health check with all services healthy."""
        with patch('app.core.health.check_database_health') as mock_db, \
             patch('app.core.health.check_redis_health') as mock_redis, \
             patch('app.core.health.check_data_sources_health') as mock_ds, \
             patch('app.core.health.check_external_apis_health') as mock_apis, \
             patch('app.core.health.check_system_resources') as mock_resources:
            
            # Mock all services as healthy
            mock_db.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_redis.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_ds.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_apis.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_resources.return_value = {"status": ServiceStatus.HEALTHY.value}
            
            result = await get_system_health()
            
            assert result["status"] == ServiceStatus.HEALTHY.value
            assert "services" in result
            assert len(result["services"]) == 5
            assert "health_check_duration_ms" in result
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_get_system_health_some_unhealthy(self):
        """Test comprehensive system health check with some services unhealthy."""
        with patch('app.core.health.check_database_health') as mock_db, \
             patch('app.core.health.check_redis_health') as mock_redis, \
             patch('app.core.health.check_data_sources_health') as mock_ds, \
             patch('app.core.health.check_external_apis_health') as mock_apis, \
             patch('app.core.health.check_system_resources') as mock_resources:
            
            # Mock some services as unhealthy
            mock_db.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_redis.return_value = {"status": ServiceStatus.UNHEALTHY.value, "error": "Connection failed"}
            mock_ds.return_value = {"status": ServiceStatus.DEGRADED.value}
            mock_apis.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_resources.return_value = {"status": ServiceStatus.HEALTHY.value}
            
            result = await get_system_health()
            
            assert result["status"] == ServiceStatus.UNHEALTHY.value
            assert result["services"]["redis"]["status"] == ServiceStatus.UNHEALTHY.value
            assert result["services"]["data_sources"]["status"] == ServiceStatus.DEGRADED.value
    
    @pytest.mark.asyncio
    async def test_get_system_health_exception_handling(self):
        """Test system health check handles exceptions gracefully."""
        with patch('app.core.health.check_database_health') as mock_db, \
             patch('app.core.health.check_redis_health') as mock_redis, \
             patch('app.core.health.check_data_sources_health') as mock_ds, \
             patch('app.core.health.check_external_apis_health') as mock_apis, \
             patch('app.core.health.check_system_resources') as mock_resources:
            
            # Mock some services to raise exceptions
            mock_db.side_effect = Exception("Database connection failed")
            mock_redis.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_ds.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_apis.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_resources.return_value = {"status": ServiceStatus.HEALTHY.value}
            
            result = await get_system_health()
            
            assert result["status"] == ServiceStatus.UNHEALTHY.value
            assert result["services"]["database"]["status"] == ServiceStatus.UNHEALTHY.value
            assert "Database connection failed" in result["services"]["database"]["error"]


class TestSystemMonitor:
    """Test system monitor functionality."""
    
    def test_system_monitor_initialization(self):
        """Test system monitor initialization."""
        monitor = SystemMonitor()
        
        assert not monitor._monitoring_active
        assert monitor._monitoring_task is None
        assert monitor._check_interval == 60
        assert len(monitor._health_history) == 0
        assert len(monitor._recent_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = SystemMonitor()
        
        # Start monitoring
        await monitor.start_monitoring()
        assert monitor._monitoring_active is True
        assert monitor._monitoring_task is not None
        
        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor._monitoring_active is False
    
    @pytest.mark.asyncio
    async def test_collect_health_metrics(self):
        """Test health metrics collection."""
        monitor = SystemMonitor()
        
        mock_health_data = {
            "status": ServiceStatus.HEALTHY.value,
            "health_check_duration_ms": 150.0,
            "services": {
                "database": {"status": ServiceStatus.HEALTHY.value},
                "redis": {"status": ServiceStatus.HEALTHY.value},
                "system_resources": {
                    "status": ServiceStatus.HEALTHY.value,
                    "cpu_percent": 45.0,
                    "memory_percent": 60.0,
                    "disk_percent": 70.0
                }
            }
        }
        
        with patch('app.services.system_monitor.get_system_health') as mock_health, \
             patch.object(monitor, '_cache_current_status') as mock_cache:
            
            mock_health.return_value = mock_health_data
            mock_cache.return_value = None
            
            await monitor._collect_health_metrics()
            
            assert len(monitor._health_history) == 1
            assert monitor._health_history[0]["status"] == ServiceStatus.HEALTHY.value
            assert "database" in monitor._service_metrics
            assert "redis" in monitor._service_metrics
            assert "system_resources" in monitor._service_metrics
    
    @pytest.mark.asyncio
    async def test_check_alerts_high_cpu(self):
        """Test alert generation for high CPU usage."""
        monitor = SystemMonitor()
        
        health_data = {
            "status": ServiceStatus.DEGRADED.value,
            "health_check_duration_ms": 100.0,
            "services": {
                "system_resources": {
                    "status": ServiceStatus.DEGRADED.value,
                    "cpu_percent": 85.0,  # Above threshold
                    "memory_percent": 60.0,
                    "disk_percent": 70.0
                }
            }
        }
        
        timestamp = datetime.utcnow()
        
        with patch.object(monitor, '_cache_current_status'):
            await monitor._check_alerts(health_data, timestamp)
            
            alerts = list(monitor._recent_alerts)
            assert len(alerts) >= 1
            
            # Check for high CPU alert
            cpu_alerts = [alert for alert in alerts if alert["type"] == "high_cpu"]
            assert len(cpu_alerts) == 1
            assert cpu_alerts[0]["severity"] == "warning"
            assert "85.0%" in cpu_alerts[0]["message"]
    
    @pytest.mark.asyncio
    async def test_get_system_dashboard(self):
        """Test getting system dashboard data."""
        monitor = SystemMonitor()
        
        # Add some mock history
        monitor._health_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "status": ServiceStatus.HEALTHY.value,
            "duration_ms": 100.0,
            "services": {"database": ServiceStatus.HEALTHY.value}
        })
        
        # Add some mock alerts
        monitor._recent_alerts.append({
            "type": "test_alert",
            "severity": "warning",
            "message": "Test alert",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        with patch.object(monitor, '_get_cached_status') as mock_cached, \
             patch('app.services.system_monitor.data_source_registry') as mock_registry:
            
            mock_cached.return_value = {"status": ServiceStatus.HEALTHY.value}
            mock_registry.get_registry_status.return_value = {
                "adapters": {},
                "circuit_breakers": {},
                "failover_enabled": True
            }
            
            dashboard = await monitor.get_system_dashboard()
            
            assert "current_status" in dashboard
            assert "history" in dashboard
            assert "recent_alerts" in dashboard
            assert "data_sources" in dashboard
            assert "monitoring" in dashboard
            assert dashboard["monitoring"]["history_points"] == 1
    
    @pytest.mark.asyncio
    async def test_get_service_metrics(self):
        """Test getting metrics for a specific service."""
        monitor = SystemMonitor()
        
        # Add some mock metrics
        service_name = "database"
        timestamp = datetime.utcnow()
        
        monitor._service_metrics[service_name].append({
            "timestamp": timestamp.isoformat(),
            "status": ServiceStatus.HEALTHY.value,
            "response_time_ms": 50.0,
            "error": None
        })
        
        monitor._service_metrics[service_name].append({
            "timestamp": (timestamp + timedelta(minutes=1)).isoformat(),
            "status": ServiceStatus.HEALTHY.value,
            "response_time_ms": 75.0,
            "error": None
        })
        
        metrics = await monitor.get_service_metrics(service_name, hours=1)
        
        assert metrics["service"] == service_name
        assert len(metrics["metrics"]) == 2
        assert metrics["summary"]["total_points"] == 2
        assert metrics["summary"]["error_count"] == 0
        assert metrics["summary"]["avg_response_time_ms"] == 62.5
    
    def test_alert_thresholds_management(self):
        """Test alert thresholds management."""
        monitor = SystemMonitor()
        
        # Get default thresholds
        thresholds = monitor.get_alert_thresholds()
        assert "cpu_percent" in thresholds
        assert thresholds["cpu_percent"] == 80
        
        # Update thresholds
        new_thresholds = {"cpu_percent": 90, "memory_percent": 95}
        monitor.update_alert_thresholds(new_thresholds)
        
        updated_thresholds = monitor.get_alert_thresholds()
        assert updated_thresholds["cpu_percent"] == 90
        assert updated_thresholds["memory_percent"] == 95