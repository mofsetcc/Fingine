"""Integration tests for Alpha Vantage adapter setup and configuration."""

import pytest
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime

from app.adapters.alpha_vantage_setup import (
    create_alpha_vantage_config,
    setup_alpha_vantage_adapter,
    setup_alpha_vantage_with_fallback,
    get_alpha_vantage_premium_config,
    validate_alpha_vantage_config,
    test_alpha_vantage_connection,
    setup_from_environment
)
from app.adapters.alpha_vantage_adapter import AlphaVantageAdapter
from app.adapters.registry import DataSourceRegistry


class TestAlphaVantageSetup:
    """Test Alpha Vantage setup and configuration utilities."""
    
    def test_create_alpha_vantage_config_with_api_key(self):
        """Test creating config with provided API key."""
        config = create_alpha_vantage_config(api_key="test_key_123")
        
        assert config["api_key"] == "test_key_123"
        assert config["requests_per_minute"] == 5
        assert config["requests_per_day"] == 500
        assert config["timeout"] == 30
        assert config["max_retries"] == 3
        assert config["retry_delay"] == 1.0
        assert config["cost_per_request"] == 0.0
        assert config["monthly_budget"] == 0.0
    
    def test_create_alpha_vantage_config_custom_params(self):
        """Test creating config with custom parameters."""
        config = create_alpha_vantage_config(
            api_key="test_key_123",
            requests_per_minute=10,
            requests_per_day=1000,
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            cost_per_request=0.001,
            monthly_budget=100.0
        )
        
        assert config["requests_per_minute"] == 10
        assert config["requests_per_day"] == 1000
        assert config["timeout"] == 60
        assert config["max_retries"] == 5
        assert config["retry_delay"] == 2.0
        assert config["cost_per_request"] == 0.001
        assert config["monthly_budget"] == 100.0
    
    @patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "env_test_key"})
    def test_create_alpha_vantage_config_from_env(self):
        """Test creating config from environment variable."""
        config = create_alpha_vantage_config()
        
        assert config["api_key"] == "env_test_key"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_create_alpha_vantage_config_no_api_key(self):
        """Test creating config without API key raises error."""
        with pytest.raises(ValueError, match="API key is required"):
            create_alpha_vantage_config()
    
    def test_setup_alpha_vantage_adapter(self):
        """Test setting up Alpha Vantage adapter."""
        config = {"api_key": "test_key_123"}
        
        adapter = setup_alpha_vantage_adapter(
            name="test_adapter",
            priority=15,
            config=config,
            register_adapter=False
        )
        
        assert isinstance(adapter, AlphaVantageAdapter)
        assert adapter.name == "test_adapter"
        assert adapter.priority == 15
        assert adapter.api_key == "test_key_123"
    
    def test_setup_alpha_vantage_adapter_with_registry(self):
        """Test setting up adapter with registry registration."""
        config = {"api_key": "test_key_123"}
        registry = DataSourceRegistry()
        
        with patch('app.adapters.alpha_vantage_setup.registry', registry):
            adapter = setup_alpha_vantage_adapter(
                name="test_adapter",
                config=config,
                register_adapter=True
            )
            
            # Check adapter is registered
            assert registry.get_adapter("test_adapter") == adapter
    
    def test_setup_alpha_vantage_adapter_default_config(self):
        """Test setting up adapter with default config creation."""
        with patch('app.adapters.alpha_vantage_setup.create_alpha_vantage_config') as mock_create:
            mock_create.return_value = {"api_key": "default_key"}
            
            adapter = setup_alpha_vantage_adapter(register_adapter=False)
            
            mock_create.assert_called_once()
            assert adapter.api_key == "default_key"
    
    def test_setup_alpha_vantage_with_fallback_primary_only(self):
        """Test setting up with fallback when only primary key provided."""
        primary, fallback = setup_alpha_vantage_with_fallback(
            primary_api_key="primary_key",
            register_adapters=False
        )
        
        assert isinstance(primary, AlphaVantageAdapter)
        assert primary.name == "alpha_vantage_primary"
        assert primary.priority == 10
        assert primary.api_key == "primary_key"
        
        assert fallback is None
    
    def test_setup_alpha_vantage_with_fallback_both_keys(self):
        """Test setting up with fallback when both keys provided."""
        primary, fallback = setup_alpha_vantage_with_fallback(
            primary_api_key="primary_key",
            fallback_api_key="fallback_key",
            register_adapters=False
        )
        
        assert isinstance(primary, AlphaVantageAdapter)
        assert primary.name == "alpha_vantage_primary"
        assert primary.priority == 10
        assert primary.api_key == "primary_key"
        
        assert isinstance(fallback, AlphaVantageAdapter)
        assert fallback.name == "alpha_vantage_fallback"
        assert fallback.priority == 20
        assert fallback.api_key == "fallback_key"
        
        # Fallback should have lower rate limits
        assert fallback.requests_per_minute == 3
        assert fallback.requests_per_day == 300
    
    def test_get_alpha_vantage_premium_config_premium(self):
        """Test getting premium plan configuration."""
        config = get_alpha_vantage_premium_config("premium_key", "premium")
        
        assert config["api_key"] == "premium_key"
        assert config["requests_per_minute"] == 75
        assert config["requests_per_day"] == 75000
        assert config["cost_per_request"] == 0.0005
        assert config["monthly_budget"] == 50.0
    
    def test_get_alpha_vantage_premium_config_professional(self):
        """Test getting professional plan configuration."""
        config = get_alpha_vantage_premium_config("pro_key", "professional")
        
        assert config["requests_per_minute"] == 300
        assert config["requests_per_day"] == 300000
        assert config["cost_per_request"] == 0.0003
        assert config["monthly_budget"] == 200.0
    
    def test_get_alpha_vantage_premium_config_enterprise(self):
        """Test getting enterprise plan configuration."""
        config = get_alpha_vantage_premium_config("ent_key", "enterprise")
        
        assert config["requests_per_minute"] == 600
        assert config["requests_per_day"] == 600000
        assert config["cost_per_request"] == 0.0002
        assert config["monthly_budget"] == 500.0
    
    def test_get_alpha_vantage_premium_config_invalid_plan(self):
        """Test getting config for invalid plan type."""
        with pytest.raises(ValueError, match="Unknown plan type"):
            get_alpha_vantage_premium_config("key", "invalid_plan")
    
    def test_validate_alpha_vantage_config_valid(self):
        """Test validating valid configuration."""
        config = {
            "api_key": "valid_key_123",
            "requests_per_minute": 5,
            "requests_per_day": 500,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "cost_per_request": 0.0,
            "monthly_budget": 0.0
        }
        
        assert validate_alpha_vantage_config(config) is True
    
    def test_validate_alpha_vantage_config_missing_api_key(self):
        """Test validating config without API key."""
        config = {"requests_per_minute": 5}
        
        with pytest.raises(ValueError, match="Missing required configuration field: api_key"):
            validate_alpha_vantage_config(config)
    
    def test_validate_alpha_vantage_config_invalid_api_key(self):
        """Test validating config with invalid API key."""
        config = {"api_key": "short"}
        
        with pytest.raises(ValueError, match="Invalid API key format"):
            validate_alpha_vantage_config(config)
    
    def test_validate_alpha_vantage_config_negative_values(self):
        """Test validating config with negative values."""
        config = {
            "api_key": "valid_key_123",
            "requests_per_minute": -1
        }
        
        with pytest.raises(ValueError, match="must be non-negative number"):
            validate_alpha_vantage_config(config)
    
    def test_validate_alpha_vantage_config_invalid_rate_limits(self):
        """Test validating config with invalid rate limits."""
        config = {
            "api_key": "valid_key_123",
            "requests_per_minute": 100,
            "requests_per_day": 50  # Less than per minute
        }
        
        with pytest.raises(ValueError, match="requests_per_minute cannot exceed requests_per_day"):
            validate_alpha_vantage_config(config)
    
    @pytest.mark.asyncio
    async def test_test_alpha_vantage_connection_success(self):
        """Test successful connection test."""
        config = {"api_key": "test_key_123"}
        
        # Mock adapter methods
        mock_adapter = AsyncMock()
        mock_adapter.health_check.return_value = AsyncMock(status=AsyncMock(value="healthy"))
        mock_adapter.get_rate_limit_info.return_value = {"requests_per_minute": 5}
        mock_adapter.get_cost_info.return_value = {"cost_per_request": 0.0}
        mock_adapter.get_current_price.return_value = {"symbol": "AAPL", "price": 150.0}
        mock_adapter._close_session = AsyncMock()
        
        with patch('app.adapters.alpha_vantage_setup.AlphaVantageAdapter', return_value=mock_adapter):
            results = await test_alpha_vantage_connection(config)
            
            assert results["config_valid"] is True
            assert results["connection_successful"] is True
            assert results["health_check_passed"] is True
            assert results["rate_limit_info"] == {"requests_per_minute": 5}
            assert results["cost_info"] == {"cost_per_request": 0.0}
            assert results["sample_data"]["symbol"] == "AAPL"
            assert results["error_message"] is None
    
    @pytest.mark.asyncio
    async def test_test_alpha_vantage_connection_invalid_config(self):
        """Test connection test with invalid config."""
        config = {"invalid": "config"}
        
        results = await test_alpha_vantage_connection(config)
        
        assert results["config_valid"] is False
        assert results["connection_successful"] is False
        assert results["health_check_passed"] is False
        assert results["error_message"] is not None
    
    @pytest.mark.asyncio
    async def test_test_alpha_vantage_connection_unhealthy(self):
        """Test connection test when adapter is unhealthy."""
        config = {"api_key": "test_key_123"}
        
        mock_adapter = AsyncMock()
        mock_adapter.health_check.return_value = AsyncMock(
            status=AsyncMock(value="unhealthy"),
            error_message="API unavailable"
        )
        mock_adapter._close_session = AsyncMock()
        
        with patch('app.adapters.alpha_vantage_setup.AlphaVantageAdapter', return_value=mock_adapter):
            results = await test_alpha_vantage_connection(config)
            
            assert results["config_valid"] is True
            assert results["connection_successful"] is False
            assert results["health_check_passed"] is False
            assert results["error_message"] == "API unavailable"
    
    @patch.dict(os.environ, {
        "ALPHA_VANTAGE_API_KEY": "env_key_123",
        "ALPHA_VANTAGE_PLAN": "premium"
    })
    def test_setup_from_environment_premium(self):
        """Test setting up from environment with premium plan."""
        with patch('app.adapters.alpha_vantage_setup.setup_alpha_vantage_adapter') as mock_setup:
            mock_adapter = Mock()
            mock_setup.return_value = mock_adapter
            
            result = setup_from_environment()
            
            assert result == mock_adapter
            mock_setup.assert_called_once()
            
            # Check that premium config was used
            call_args = mock_setup.call_args
            config = call_args[1]["config"]
            assert config["api_key"] == "env_key_123"
            assert config["requests_per_minute"] == 75  # Premium rate limit
    
    @patch.dict(os.environ, {
        "ALPHA_VANTAGE_API_KEY": "env_key_123",
        "ALPHA_VANTAGE_REQUESTS_PER_MINUTE": "10",
        "ALPHA_VANTAGE_REQUESTS_PER_DAY": "2000"
    })
    def test_setup_from_environment_custom_limits(self):
        """Test setting up from environment with custom rate limits."""
        with patch('app.adapters.alpha_vantage_setup.setup_alpha_vantage_adapter') as mock_setup:
            mock_adapter = Mock()
            mock_setup.return_value = mock_adapter
            
            result = setup_from_environment()
            
            # Check that custom rate limits were applied
            call_args = mock_setup.call_args
            config = call_args[1]["config"]
            assert config["requests_per_minute"] == 10
            assert config["requests_per_day"] == 2000
    
    @patch.dict(os.environ, {}, clear=True)
    def test_setup_from_environment_no_api_key(self):
        """Test setting up from environment without API key."""
        result = setup_from_environment()
        
        assert result is None
    
    @patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "env_key_123"})
    def test_setup_from_environment_setup_failure(self):
        """Test setup from environment when adapter setup fails."""
        with patch('app.adapters.alpha_vantage_setup.setup_alpha_vantage_adapter', side_effect=Exception("Setup failed")):
            result = setup_from_environment()
            
            assert result is None
    
    def test_setup_alpha_vantage_adapter_invalid_config(self):
        """Test setting up adapter with invalid configuration."""
        invalid_config = {"invalid": "config"}
        
        with pytest.raises(ValueError):
            setup_alpha_vantage_adapter(config=invalid_config, register_adapter=False)
    
    def test_setup_alpha_vantage_with_fallback_primary_failure(self):
        """Test fallback setup when primary setup fails."""
        with patch('app.adapters.alpha_vantage_setup.create_alpha_vantage_config', side_effect=Exception("Primary failed")):
            with pytest.raises(Exception, match="Primary failed"):
                setup_alpha_vantage_with_fallback(
                    primary_api_key="primary_key",
                    register_adapters=False
                )
    
    def test_setup_alpha_vantage_with_fallback_fallback_failure(self):
        """Test fallback setup when fallback setup fails but primary succeeds."""
        with patch('app.adapters.alpha_vantage_setup.create_alpha_vantage_config') as mock_create:
            # First call (primary) succeeds, second call (fallback) fails
            mock_create.side_effect = [
                {"api_key": "primary_key"},
                Exception("Fallback failed")
            ]
            
            with patch('app.adapters.alpha_vantage_setup.setup_alpha_vantage_adapter') as mock_setup:
                mock_primary = Mock()
                mock_setup.return_value = mock_primary
                
                primary, fallback = setup_alpha_vantage_with_fallback(
                    primary_api_key="primary_key",
                    fallback_api_key="fallback_key",
                    register_adapters=False
                )
                
                # Primary should succeed, fallback should be None
                assert primary == mock_primary
                assert fallback is None