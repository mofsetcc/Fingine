"""Data source registry with plugin-based architecture."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Type, Any, Callable
from collections import defaultdict
import json

from .base import (
    BaseDataSourceAdapter,
    DataSourceType,
    HealthStatus,
    HealthCheck,
    DataSourceError,
    DataSourceUnavailableError,
    RateLimitExceededError
)

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    """Registry for managing data source adapters with failover logic."""
    
    def __init__(self):
        """Initialize the registry."""
        self._adapters: Dict[DataSourceType, List[BaseDataSourceAdapter]] = defaultdict(list)
        self._adapter_by_name: Dict[str, BaseDataSourceAdapter] = {}
        self._health_check_interval = 300  # 5 minutes
        self._health_check_task: Optional[asyncio.Task] = None
        self._failover_enabled = True
        self._circuit_breaker_threshold = 5  # Number of failures before circuit opens
        self._circuit_breaker_timeout = 300  # 5 minutes
        self._adapter_failures: Dict[str, List[datetime]] = defaultdict(list)
        self._circuit_breaker_state: Dict[str, bool] = {}  # True = open (disabled)
        self._circuit_breaker_reset_time: Dict[str, datetime] = {}
        
    def register_adapter(self, adapter: BaseDataSourceAdapter) -> None:
        """
        Register a data source adapter.
        
        Args:
            adapter: The adapter to register
            
        Raises:
            ValueError: If adapter name already exists
        """
        if adapter.name in self._adapter_by_name:
            raise ValueError(f"Adapter with name '{adapter.name}' already registered")
        
        # Add to type-specific list (sorted by priority)
        self._adapters[adapter.data_source_type].append(adapter)
        self._adapters[adapter.data_source_type].sort(key=lambda x: x.priority)
        
        # Add to name lookup
        self._adapter_by_name[adapter.name] = adapter
        
        logger.info(f"Registered data source adapter: {adapter}")
    
    def unregister_adapter(self, name: str) -> None:
        """
        Unregister a data source adapter.
        
        Args:
            name: Name of the adapter to unregister
            
        Raises:
            KeyError: If adapter not found
        """
        if name not in self._adapter_by_name:
            raise KeyError(f"Adapter '{name}' not found")
        
        adapter = self._adapter_by_name[name]
        
        # Remove from type-specific list
        self._adapters[adapter.data_source_type].remove(adapter)
        
        # Remove from name lookup
        del self._adapter_by_name[name]
        
        # Clean up failure tracking
        if name in self._adapter_failures:
            del self._adapter_failures[name]
        if name in self._circuit_breaker_state:
            del self._circuit_breaker_state[name]
        if name in self._circuit_breaker_reset_time:
            del self._circuit_breaker_reset_time[name]
        
        logger.info(f"Unregistered data source adapter: {name}")
    
    def get_adapter(self, name: str) -> Optional[BaseDataSourceAdapter]:
        """
        Get adapter by name.
        
        Args:
            name: Adapter name
            
        Returns:
            Adapter instance or None if not found
        """
        return self._adapter_by_name.get(name)
    
    def get_adapters_by_type(self, data_source_type: DataSourceType) -> List[BaseDataSourceAdapter]:
        """
        Get all adapters for a specific data source type.
        
        Args:
            data_source_type: Type of data source
            
        Returns:
            List of adapters sorted by priority
        """
        return self._adapters[data_source_type].copy()
    
    def get_healthy_adapters(self, data_source_type: DataSourceType) -> List[BaseDataSourceAdapter]:
        """
        Get healthy adapters for a specific data source type.
        
        Args:
            data_source_type: Type of data source
            
        Returns:
            List of healthy adapters sorted by priority
        """
        adapters = []
        for adapter in self._adapters[data_source_type]:
            if (
                adapter.enabled and
                not self._is_circuit_breaker_open(adapter.name) and
                adapter.is_healthy()
            ):
                adapters.append(adapter)
        
        return adapters
    
    def get_primary_adapter(self, data_source_type: DataSourceType) -> Optional[BaseDataSourceAdapter]:
        """
        Get the primary (highest priority) healthy adapter for a data source type.
        
        Args:
            data_source_type: Type of data source
            
        Returns:
            Primary adapter or None if no healthy adapters available
        """
        healthy_adapters = self.get_healthy_adapters(data_source_type)
        return healthy_adapters[0] if healthy_adapters else None
    
    async def execute_with_failover(
        self,
        data_source_type: DataSourceType,
        operation: Callable[[BaseDataSourceAdapter], Any],
        max_retries: int = 3
    ) -> Any:
        """
        Execute an operation with automatic failover to backup adapters.
        
        Args:
            data_source_type: Type of data source needed
            operation: Async function that takes an adapter and returns result
            max_retries: Maximum number of adapters to try
            
        Returns:
            Result from the operation
            
        Raises:
            DataSourceUnavailableError: If all adapters fail
        """
        if not self._failover_enabled:
            # If failover is disabled, only try primary adapter
            primary = self.get_primary_adapter(data_source_type)
            if not primary:
                raise DataSourceUnavailableError(f"No healthy adapters available for {data_source_type.value}")
            
            return await self._execute_with_adapter(primary, operation)
        
        # Get healthy adapters in priority order
        healthy_adapters = self.get_healthy_adapters(data_source_type)
        
        if not healthy_adapters:
            raise DataSourceUnavailableError(f"No healthy adapters available for {data_source_type.value}")
        
        # Try adapters in order until one succeeds or we run out
        last_error = None
        adapters_tried = 0
        
        for adapter in healthy_adapters[:max_retries]:
            try:
                result = await self._execute_with_adapter(adapter, operation)
                
                # Reset failure count on success
                if adapter.name in self._adapter_failures:
                    self._adapter_failures[adapter.name].clear()
                
                logger.info(f"Successfully executed operation using adapter: {adapter.name}")
                return result
                
            except Exception as e:
                adapters_tried += 1
                last_error = e
                
                # Record failure
                self._record_adapter_failure(adapter.name)
                
                logger.warning(
                    f"Adapter '{adapter.name}' failed (attempt {adapters_tried}): {e}"
                )
                
                # Continue to next adapter
                continue
        
        # All adapters failed
        raise DataSourceUnavailableError(
            f"All {adapters_tried} adapters failed for {data_source_type.value}. "
            f"Last error: {last_error}"
        )
    
    async def _execute_with_adapter(
        self,
        adapter: BaseDataSourceAdapter,
        operation: Callable[[BaseDataSourceAdapter], Any]
    ) -> Any:
        """
        Execute operation with a specific adapter.
        
        Args:
            adapter: Adapter to use
            operation: Operation to execute
            
        Returns:
            Result from operation
            
        Raises:
            Various exceptions from the operation
        """
        # Check circuit breaker
        if self._is_circuit_breaker_open(adapter.name):
            raise DataSourceUnavailableError(f"Circuit breaker open for adapter: {adapter.name}")
        
        # Execute operation
        try:
            return await operation(adapter)
        except RateLimitExceededError:
            # Don't count rate limit errors as failures
            raise
        except Exception as e:
            # Record failure for circuit breaker
            self._record_adapter_failure(adapter.name)
            raise
    
    def _record_adapter_failure(self, adapter_name: str) -> None:
        """
        Record a failure for an adapter and check circuit breaker.
        
        Args:
            adapter_name: Name of the adapter that failed
        """
        now = datetime.utcnow()
        
        # Add failure timestamp
        self._adapter_failures[adapter_name].append(now)
        
        # Remove old failures (older than circuit breaker timeout)
        cutoff_time = now - timedelta(seconds=self._circuit_breaker_timeout)
        self._adapter_failures[adapter_name] = [
            failure_time for failure_time in self._adapter_failures[adapter_name]
            if failure_time > cutoff_time
        ]
        
        # Check if we should open circuit breaker
        failure_count = len(self._adapter_failures[adapter_name])
        if failure_count >= self._circuit_breaker_threshold:
            self._circuit_breaker_state[adapter_name] = True
            self._circuit_breaker_reset_time[adapter_name] = now + timedelta(seconds=self._circuit_breaker_timeout)
            
            logger.warning(
                f"Circuit breaker opened for adapter '{adapter_name}' "
                f"after {failure_count} failures"
            )
    
    def _is_circuit_breaker_open(self, adapter_name: str) -> bool:
        """
        Check if circuit breaker is open for an adapter.
        
        Args:
            adapter_name: Name of the adapter
            
        Returns:
            True if circuit breaker is open
        """
        if adapter_name not in self._circuit_breaker_state:
            return False
        
        if not self._circuit_breaker_state[adapter_name]:
            return False
        
        # Check if it's time to reset
        now = datetime.utcnow()
        reset_time = self._circuit_breaker_reset_time.get(adapter_name)
        
        if reset_time and now >= reset_time:
            # Reset circuit breaker
            self._circuit_breaker_state[adapter_name] = False
            if adapter_name in self._circuit_breaker_reset_time:
                del self._circuit_breaker_reset_time[adapter_name]
            
            logger.info(f"Circuit breaker reset for adapter: {adapter_name}")
            return False
        
        return True
    
    async def start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_check_task and not self._health_check_task.done():
            logger.warning("Health monitoring already running")
            return
        
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Started health monitoring")
    
    async def stop_health_monitoring(self) -> None:
        """Stop background health monitoring task."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped health monitoring")
    
    async def _health_monitor_loop(self) -> None:
        """Background task for monitoring adapter health."""
        while True:
            try:
                await self._check_all_adapters_health()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _check_all_adapters_health(self) -> None:
        """Check health of all registered adapters."""
        tasks = []
        
        for adapter in self._adapter_by_name.values():
            if adapter.enabled:
                task = asyncio.create_task(self._check_adapter_health(adapter))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_adapter_health(self, adapter: BaseDataSourceAdapter) -> None:
        """
        Check health of a single adapter.
        
        Args:
            adapter: Adapter to check
        """
        try:
            health_check = await adapter.health_check()
            
            if health_check.status == HealthStatus.UNHEALTHY:
                logger.warning(f"Adapter '{adapter.name}' is unhealthy: {health_check.error_message}")
            elif health_check.status == HealthStatus.DEGRADED:
                logger.info(f"Adapter '{adapter.name}' is degraded: {health_check.error_message}")
            
        except Exception as e:
            logger.error(f"Health check failed for adapter '{adapter.name}': {e}")
    
    def enable_failover(self) -> None:
        """Enable automatic failover."""
        self._failover_enabled = True
        logger.info("Failover enabled")
    
    def disable_failover(self) -> None:
        """Disable automatic failover."""
        self._failover_enabled = False
        logger.info("Failover disabled")
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get current status of the registry.
        
        Returns:
            Dictionary with registry status information
        """
        status = {
            "failover_enabled": self._failover_enabled,
            "health_check_interval": self._health_check_interval,
            "health_monitoring_active": self._health_check_task and not self._health_check_task.done(),
            "adapters": {},
            "circuit_breakers": {}
        }
        
        # Adapter status
        for adapter_name, adapter in self._adapter_by_name.items():
            last_health = adapter._last_health_check
            status["adapters"][adapter_name] = {
                "type": adapter.data_source_type.value,
                "priority": adapter.priority,
                "enabled": adapter.enabled,
                "health_status": last_health.status.value if last_health else "unknown",
                "last_health_check": last_health.last_check.isoformat() if last_health else None,
                "response_time_ms": last_health.response_time_ms if last_health else None,
                "error_message": last_health.error_message if last_health else None
            }
        
        # Circuit breaker status
        for adapter_name, is_open in self._circuit_breaker_state.items():
            if is_open:
                reset_time = self._circuit_breaker_reset_time.get(adapter_name)
                status["circuit_breakers"][adapter_name] = {
                    "open": True,
                    "reset_time": reset_time.isoformat() if reset_time else None,
                    "failure_count": len(self._adapter_failures.get(adapter_name, []))
                }
        
        return status
    
    def reset_circuit_breaker(self, adapter_name: str) -> bool:
        """
        Manually reset circuit breaker for an adapter.
        
        Args:
            adapter_name: Name of the adapter
            
        Returns:
            True if circuit breaker was reset, False if it wasn't open
        """
        if adapter_name not in self._circuit_breaker_state or not self._circuit_breaker_state[adapter_name]:
            return False
        
        self._circuit_breaker_state[adapter_name] = False
        if adapter_name in self._circuit_breaker_reset_time:
            del self._circuit_breaker_reset_time[adapter_name]
        if adapter_name in self._adapter_failures:
            self._adapter_failures[adapter_name].clear()
        
        logger.info(f"Manually reset circuit breaker for adapter: {adapter_name}")
        return True


# Global registry instance
registry = DataSourceRegistry()