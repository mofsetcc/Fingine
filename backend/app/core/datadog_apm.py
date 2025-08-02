"""
Datadog APM integration for application performance monitoring.
"""

import os
import time
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import contextmanager

from ddtrace import tracer, patch_all
from ddtrace.contrib.fastapi import patch as patch_fastapi
from ddtrace.ext import http, db
from ddtrace import config

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatadogAPM:
    """Datadog APM integration for comprehensive application monitoring."""
    
    def __init__(self):
        self.enabled = self._should_enable_apm()
        self.service_name = os.getenv("DD_SERVICE", "kessan-backend")
        self.environment = os.getenv("DD_ENV", settings.ENVIRONMENT)
        self.version = os.getenv("DD_VERSION", "1.0.0")
        
        if self.enabled:
            self._configure_datadog()
            logger.info("Datadog APM initialized", service=self.service_name, env=self.environment)
        else:
            logger.info("Datadog APM disabled")
    
    def _should_enable_apm(self) -> bool:
        """Determine if APM should be enabled based on environment."""
        # Enable APM in production and staging environments
        if settings.ENVIRONMENT in ["production", "staging"]:
            return True
        
        # Enable if explicitly set via environment variable
        if os.getenv("DD_TRACE_ENABLED", "").lower() == "true":
            return True
        
        # Enable if Datadog agent is detected
        if os.getenv("DD_AGENT_HOST") or os.path.exists("/var/run/datadog/apm.socket"):
            return True
        
        return False
    
    def _configure_datadog(self):
        """Configure Datadog APM settings."""
        # Configure service information
        config.service = self.service_name
        config.env = self.environment
        config.version = self.version
        
        # Configure FastAPI integration
        config.fastapi["service_name"] = self.service_name
        config.fastapi["request_span_name"] = "fastapi.request"
        config.fastapi["distributed_tracing"] = True
        
        # Configure database integration
        config.sqlalchemy["service_name"] = f"{self.service_name}-db"
        config.sqlalchemy["trace_fetch_methods"] = True
        
        # Configure Redis integration
        config.redis["service_name"] = f"{self.service_name}-redis"
        
        # Configure HTTP client integration
        config.httpx["service_name"] = f"{self.service_name}-http"
        config.aiohttp["service_name"] = f"{self.service_name}-http"
        
        # Patch all supported libraries
        patch_all()
        
        # Patch FastAPI specifically
        patch_fastapi()
        
        # Set global tags
        tracer.set_tags({
            "service.name": self.service_name,
            "service.version": self.version,
            "env": self.environment,
            "component": "backend-api"
        })
    
    def trace_function(self, operation_name: str, service: Optional[str] = None, resource: Optional[str] = None):
        """Decorator to trace function execution."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                with tracer.trace(
                    operation_name,
                    service=service or self.service_name,
                    resource=resource or f"{func.__module__}.{func.__name__}"
                ) as span:
                    try:
                        # Add function metadata
                        span.set_tag("function.name", func.__name__)
                        span.set_tag("function.module", func.__module__)
                        
                        # Execute function
                        result = await func(*args, **kwargs)
                        
                        # Mark as successful
                        span.set_tag("function.success", True)
                        return result
                        
                    except Exception as e:
                        # Mark as error and re-raise
                        span.set_error(e)
                        span.set_tag("function.success", False)
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                with tracer.trace(
                    operation_name,
                    service=service or self.service_name,
                    resource=resource or f"{func.__module__}.{func.__name__}"
                ) as span:
                    try:
                        # Add function metadata
                        span.set_tag("function.name", func.__name__)
                        span.set_tag("function.module", func.__module__)
                        
                        # Execute function
                        result = func(*args, **kwargs)
                        
                        # Mark as successful
                        span.set_tag("function.success", True)
                        return result
                        
                    except Exception as e:
                        # Mark as error and re-raise
                        span.set_error(e)
                        span.set_tag("function.success", False)
                        raise
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @contextmanager
    def trace_operation(self, operation_name: str, **tags):
        """Context manager for tracing operations."""
        if not self.enabled:
            yield None
            return
        
        with tracer.trace(operation_name, service=self.service_name) as span:
            # Add custom tags
            for key, value in tags.items():
                span.set_tag(key, value)
            
            try:
                yield span
            except Exception as e:
                span.set_error(e)
                raise
    
    def trace_ai_analysis(self, ticker: str, analysis_type: str, model_version: str):
        """Specialized tracing for AI analysis operations."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                with tracer.trace(
                    "ai.analysis",
                    service=f"{self.service_name}-ai",
                    resource=f"analyze.{ticker}.{analysis_type}"
                ) as span:
                    # Add AI-specific tags
                    span.set_tag("ai.ticker", ticker)
                    span.set_tag("ai.analysis_type", analysis_type)
                    span.set_tag("ai.model_version", model_version)
                    span.set_tag("ai.provider", "google-gemini")
                    
                    start_time = time.time()
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Add result metadata
                        processing_time = time.time() - start_time
                        span.set_tag("ai.processing_time_ms", int(processing_time * 1000))
                        span.set_tag("ai.success", True)
                        
                        if isinstance(result, dict):
                            span.set_tag("ai.confidence_score", result.get("confidence", 0))
                            span.set_tag("ai.cache_hit", result.get("cache_hit", False))
                            span.set_tag("ai.cost_usd", result.get("cost_usd", 0))
                        
                        return result
                        
                    except Exception as e:
                        span.set_error(e)
                        span.set_tag("ai.success", False)
                        span.set_tag("ai.error_type", type(e).__name__)
                        raise
            
            return wrapper
        return decorator
    
    def trace_data_source(self, source_name: str, operation: str):
        """Specialized tracing for data source operations."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                with tracer.trace(
                    "data_source.operation",
                    service=f"{self.service_name}-data",
                    resource=f"{source_name}.{operation}"
                ) as span:
                    # Add data source tags
                    span.set_tag("data_source.name", source_name)
                    span.set_tag("data_source.operation", operation)
                    
                    start_time = time.time()
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Add result metadata
                        response_time = time.time() - start_time
                        span.set_tag("data_source.response_time_ms", int(response_time * 1000))
                        span.set_tag("data_source.success", True)
                        
                        if isinstance(result, (list, dict)):
                            if isinstance(result, list):
                                span.set_tag("data_source.records_count", len(result))
                            elif isinstance(result, dict) and "data" in result:
                                data = result["data"]
                                if isinstance(data, list):
                                    span.set_tag("data_source.records_count", len(data))
                        
                        return result
                        
                    except Exception as e:
                        span.set_error(e)
                        span.set_tag("data_source.success", False)
                        span.set_tag("data_source.error_type", type(e).__name__)
                        raise
            
            return wrapper
        return decorator
    
    def add_custom_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Add custom business metric to Datadog."""
        if not self.enabled:
            return
        
        try:
            from datadog import statsd
            
            # Prepare tags
            metric_tags = [f"{k}:{v}" for k, v in (tags or {}).items()]
            metric_tags.extend([
                f"service:{self.service_name}",
                f"env:{self.environment}",
                f"version:{self.version}"
            ])
            
            # Send metric
            statsd.gauge(f"kessan.{metric_name}", value, tags=metric_tags)
            
        except ImportError:
            logger.warning("Datadog statsd client not available for custom metrics")
        except Exception as e:
            logger.error(f"Failed to send custom metric {metric_name}: {e}")
    
    def increment_counter(self, counter_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        if not self.enabled:
            return
        
        try:
            from datadog import statsd
            
            # Prepare tags
            metric_tags = [f"{k}:{v}" for k, v in (tags or {}).items()]
            metric_tags.extend([
                f"service:{self.service_name}",
                f"env:{self.environment}",
                f"version:{self.version}"
            ])
            
            # Send counter
            statsd.increment(f"kessan.{counter_name}", value, tags=metric_tags)
            
        except ImportError:
            logger.warning("Datadog statsd client not available for counter metrics")
        except Exception as e:
            logger.error(f"Failed to increment counter {counter_name}: {e}")
    
    def record_histogram(self, histogram_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        if not self.enabled:
            return
        
        try:
            from datadog import statsd
            
            # Prepare tags
            metric_tags = [f"{k}:{v}" for k, v in (tags or {}).items()]
            metric_tags.extend([
                f"service:{self.service_name}",
                f"env:{self.environment}",
                f"version:{self.version}"
            ])
            
            # Send histogram
            statsd.histogram(f"kessan.{histogram_name}", value, tags=metric_tags)
            
        except ImportError:
            logger.warning("Datadog statsd client not available for histogram metrics")
        except Exception as e:
            logger.error(f"Failed to record histogram {histogram_name}: {e}")


# Global APM instance
datadog_apm = DatadogAPM()


# Convenience decorators
def trace_function(operation_name: str, service: Optional[str] = None, resource: Optional[str] = None):
    """Convenience decorator for tracing functions."""
    return datadog_apm.trace_function(operation_name, service, resource)


def trace_ai_analysis(ticker: str, analysis_type: str, model_version: str):
    """Convenience decorator for tracing AI analysis."""
    return datadog_apm.trace_ai_analysis(ticker, analysis_type, model_version)


def trace_data_source(source_name: str, operation: str):
    """Convenience decorator for tracing data source operations."""
    return datadog_apm.trace_data_source(source_name, operation)