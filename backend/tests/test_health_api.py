"""
Tests for health check API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.core.health import ServiceStatus


class TestHealthAPI:
    """Test health check API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_basic_health_check(self):
        """Test basic health check endpoint."""
        response = self.client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "kessan-backend"
    
    def test_liveness_check(self):
        """Test liveness probe endpoint."""
        response = self.client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
    
    def test_readiness_check_healthy(self):
        """Test readiness probe when database is healthy."""
        with patch('app.api.v1.health.check_database_health') as mock_db_health:
            mock_db_health.return_value = {"status": "healthy"}
            
            response = self.client.get("/api/v1/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
    
    def test_readiness_check_unhealthy(self):
        """Test readiness probe when database is unhealthy."""
        with patch('app.api.v1.health.check_database_health') as mock_db_health:
            mock_db_health.return_value = {"status": "unhealthy", "error": "Connection failed"}
            
            response = self.client.get("/api/v1/health/ready")
            
            assert response.status_code == 503
            assert "Database not ready" in response.json()["detail"]
    
    def test_database_health_check_healthy(self):
        """Test database health check endpoint when healthy."""
        with patch('app.api.v1.health.check_database_health') as mock_db_health:
            mock_db_health.return_value = {
                "status": "healthy",
                "tables_count": 10,
                "plans_count": 3,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = self.client.get("/api/v1/health/database")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["tables_count"] == 10
            assert data["plans_count"] == 3
    
    def test_database_health_check_unhealthy(self):
        """Test database health check endpoint when unhealthy."""
        with patch('app.api.v1.health.check_database_health') as mock_db_health:
            mock_db_health.return_value = {
                "status": "unhealthy",
                "error": "Connection timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = self.client.get("/api/v1/health/database")
            
            assert response.status_code == 503
    
    def test_system_health_check_healthy(self):
        """Test system health check endpoint when all services are healthy."""
        mock_health_data = {
            "status": ServiceStatus.HEALTHY.value,
            "timestamp": datetime.utcnow().isoformat(),
            "health_check_duration_ms": 150.0,
            "services": {
                "database": {"status": ServiceStatus.HEALTHY.value},
                "redis": {"status": ServiceStatus.HEALTHY.value},
                "data_sources": {"status": ServiceStatus.HEALTHY.value},
                "external_apis": {"status": ServiceStatus.HEALTHY.value},
                "system_resources": {"status": ServiceStatus.HEALTHY.value}
            }
        }
        
        with patch('app.api.v1.health.get_system_health') as mock_system_health:
            mock_system_health.return_value = mock_health_data
            
            response = self.client.get("/api/v1/health/system")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == ServiceStatus.HEALTHY.value
            assert len(data["services"]) == 5
    
    def test_system_health_check_degraded(self):
        """Test system health check endpoint when system is degraded."""
        mock_health_data = {
            "status": ServiceStatus.DEGRADED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "health_check_duration_ms": 150.0,
            "services": {
                "database": {"status": ServiceStatus.HEALTHY.value},
                "redis": {"status": ServiceStatus.DEGRADED.value},
                "data_sources": {"status": ServiceStatus.HEALTHY.value},
                "external_apis": {"status": ServiceStatus.HEALTHY.value},
                "system_resources": {"status": ServiceStatus.HEALTHY.value}
            }
        }
        
        with patch('app.api.v1.health.get_system_health') as mock_system_health:
            mock_system_health.return_value = mock_health_data
            
            response = self.client.get("/api/v1/health/system")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == ServiceStatus.DEGRADED.value
            assert "warning" in data
    
    def test_system_health_check_unhealthy(self):
        """Test system health check endpoint when system is unhealthy."""
        mock_health_data = {
            "status": ServiceStatus.UNHEALTHY.value,
            "timestamp": datetime.utcnow().isoformat(),
            "health_check_duration_ms": 150.0,
            "services": {
                "database": {"status": ServiceStatus.UNHEALTHY.value, "error": "Connection failed"},
                "redis": {"status": ServiceStatus.HEALTHY.value},
                "data_sources": {"status": ServiceStatus.HEALTHY.value},
                "external_apis": {"status": ServiceStatus.HEALTHY.value},
                "system_resources": {"status": ServiceStatus.HEALTHY.value}
            }
        }
        
        with patch('app.api.v1.health.get_system_health') as mock_system_health:
            mock_system_health.return_value = mock_health_data
            
            response = self.client.get("/api/v1/health/system")
            
            assert response.status_code == 503
    
    def test_data_sources_health_check(self):
        """Test data sources health check endpoint."""
        mock_health_data = {
            "status": ServiceStatus.HEALTHY.value,
            "summary": {
                "total": 3,
                "healthy": 3,
                "degraded": 0,
                "unhealthy": 0
            },
            "adapters": {
                "alpha_vantage": {
                    "status": "healthy",
                    "type": "stock_price",
                    "enabled": True,
                    "response_time_ms": 150.0
                }
            },
            "circuit_breakers": {},
            "failover_enabled": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch('app.api.v1.health.check_data_sources_health') as mock_ds_health:
            mock_ds_health.return_value = mock_health_data
            
            response = self.client.get("/api/v1/health/data-sources")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == ServiceStatus.HEALTHY.value
            assert data["summary"]["total"] == 3
            assert "alpha_vantage" in data["adapters"]
    
    def test_external_apis_health_check(self):
        """Test external APIs health check endpoint."""
        mock_health_data = {
            "status": ServiceStatus.HEALTHY.value,
            "services": {
                "gemini_api": {
                    "status": ServiceStatus.HEALTHY.value,
                    "response_time_ms": 200.0,
                    "last_check": datetime.utcnow().isoformat()
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch('app.api.v1.health.check_external_apis_health') as mock_apis_health:
            mock_apis_health.return_value = mock_health_data
            
            response = self.client.get("/api/v1/health/external-apis")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == ServiceStatus.HEALTHY.value
            assert "gemini_api" in data["services"]
    
    def test_system_resources_health_check(self):
        """Test system resources health check endpoint."""
        mock_health_data = {
            "status": ServiceStatus.HEALTHY.value,
            "cpu_percent": 45.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0,
            "memory_available_gb": 8.0,
            "disk_free_gb": 100.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch('app.api.v1.health.check_system_resources') as mock_resources_health:
            mock_resources_health.return_value = mock_health_data
            
            response = self.client.get("/api/v1/health/resources")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == ServiceStatus.HEALTHY.value
            assert data["cpu_percent"] == 45.0
            assert data["memory_percent"] == 60.0


class TestHealthAPIAuthenticated:
    """Test authenticated health check API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def get_auth_headers(self):
        """Get authentication headers for testing."""
        # Mock JWT token for testing
        return {"Authorization": "Bearer test_token"}
    
    def test_system_dashboard_authenticated(self):
        """Test system dashboard endpoint with authentication."""
        mock_dashboard_data = {
            "current_status": {"status": ServiceStatus.HEALTHY.value},
            "history": {"points": 100, "uptime_percentage": 99.5},
            "recent_alerts": [],
            "data_sources": {"adapters": {}, "circuit_breakers": {}},
            "monitoring": {"active": True, "history_points": 100},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.get_system_dashboard.return_value = mock_dashboard_data
            
            response = self.client.get(
                "/api/v1/health/dashboard",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "current_status" in data
            assert "history" in data
            assert "recent_alerts" in data
    
    def test_service_metrics_authenticated(self):
        """Test service metrics endpoint with authentication."""
        mock_metrics_data = {
            "service": "database",
            "time_range_hours": 1,
            "metrics": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": ServiceStatus.HEALTHY.value,
                    "response_time_ms": 50.0,
                    "error": None
                }
            ],
            "summary": {
                "total_points": 1,
                "error_count": 0,
                "avg_response_time_ms": 50.0
            }
        }
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.get_service_metrics.return_value = mock_metrics_data
            
            response = self.client.get(
                "/api/v1/health/metrics/database?hours=1",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "database"
            assert len(data["metrics"]) == 1
    
    def test_recent_alerts_authenticated(self):
        """Test recent alerts endpoint with authentication."""
        mock_dashboard_data = {
            "recent_alerts": [
                {
                    "type": "high_cpu",
                    "severity": "warning",
                    "message": "High CPU usage: 85.0%",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.get_system_dashboard.return_value = mock_dashboard_data
            
            response = self.client.get(
                "/api/v1/health/alerts?limit=10",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            assert len(data["alerts"]) == 1
            assert data["alerts"][0]["type"] == "high_cpu"
    
    def test_reset_circuit_breaker_authenticated(self):
        """Test reset circuit breaker endpoint with authentication."""
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.api.v1.health.data_source_registry') as mock_registry:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_registry.reset_circuit_breaker.return_value = True
            
            response = self.client.post(
                "/api/v1/health/data-sources/alpha_vantage/reset-circuit-breaker",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Circuit breaker reset" in data["message"]
    
    def test_reset_circuit_breaker_not_found(self):
        """Test reset circuit breaker endpoint when adapter not found."""
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.api.v1.health.data_source_registry') as mock_registry:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_registry.reset_circuit_breaker.return_value = False
            
            response = self.client.post(
                "/api/v1/health/data-sources/nonexistent/reset-circuit-breaker",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 404
    
    def test_enable_adapter_authenticated(self):
        """Test enable adapter endpoint with authentication."""
        mock_adapter = Mock()
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.api.v1.health.data_source_registry') as mock_registry:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_registry.get_adapter.return_value = mock_adapter
            
            response = self.client.post(
                "/api/v1/health/data-sources/alpha_vantage/enable",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            mock_adapter.enable.assert_called_once()
    
    def test_disable_adapter_authenticated(self):
        """Test disable adapter endpoint with authentication."""
        mock_adapter = Mock()
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.api.v1.health.data_source_registry') as mock_registry:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_registry.get_adapter.return_value = mock_adapter
            
            response = self.client.post(
                "/api/v1/health/data-sources/alpha_vantage/disable",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            mock_adapter.disable.assert_called_once()
    
    def test_get_alert_thresholds_authenticated(self):
        """Test get alert thresholds endpoint with authentication."""
        mock_thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90
        }
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.get_alert_thresholds.return_value = mock_thresholds
            
            response = self.client.get(
                "/api/v1/health/thresholds",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "thresholds" in data
            assert data["thresholds"]["cpu_percent"] == 80
    
    def test_update_alert_thresholds_authenticated(self):
        """Test update alert thresholds endpoint with authentication."""
        new_thresholds = {"cpu_percent": 90, "memory_percent": 95}
        updated_thresholds = {"cpu_percent": 90, "memory_percent": 95, "disk_percent": 90}
        
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.get_alert_thresholds.return_value = updated_thresholds
            
            response = self.client.put(
                "/api/v1/health/thresholds",
                json=new_thresholds,
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "thresholds" in data
            mock_monitor.update_alert_thresholds.assert_called_once_with(new_thresholds)
    
    def test_start_monitoring_authenticated(self):
        """Test start monitoring endpoint with authentication."""
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.start_monitoring = AsyncMock()
            
            response = self.client.post(
                "/api/v1/health/monitoring/start",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_stop_monitoring_authenticated(self):
        """Test stop monitoring endpoint with authentication."""
        with patch('app.api.v1.health.get_current_user') as mock_auth, \
             patch('app.services.system_monitor.system_monitor') as mock_monitor:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_monitor.stop_monitoring = AsyncMock()
            
            response = self.client.post(
                "/api/v1/health/monitoring/stop",
                headers=self.get_auth_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"