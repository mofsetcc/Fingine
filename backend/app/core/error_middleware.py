"""
Error handling middleware with graceful degradation for Project Kessan.
"""

import traceback
import uuid
from typing import Callable, Dict, Any
from datetime import datetime, timezone

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.exceptions import (
    KessanException,
    ErrorCategory,
    ErrorSeverity,
    DatabaseConnectionException,
    CacheConnectionException,
    ExternalAPIException
)
from app.core.alerting import alert_manager
from app.core.logging import error_logger


logger = structlog.get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle all exceptions with proper categorization and alerting."""
    
    def __init__(self, app, enable_graceful_degradation: bool = True):
        super().__init__(app)
        self.enable_graceful_degradation = enable_graceful_degradation
        self.error_stats = ErrorStatistics()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle request and catch all exceptions."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        try:
            response = await call_next(request)
            return response
            
        except KessanException as e:
            # Handle our custom exceptions
            return await self._handle_kessan_exception(e, request, request_id)
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            return await self._handle_http_exception(e, request, request_id)
            
        except Exception as e:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(e, request, request_id)
    
    async def _handle_kessan_exception(
        self,
        exception: KessanException,
        request: Request,
        request_id: str
    ) -> JSONResponse:
        """Handle KessanException with proper logging and alerting."""
        
        # Add request context to exception
        exception.context.update({
            "request_id": request_id,
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', None),
            "ip_address": self._get_client_ip(request)
        })
        
        # Log the error
        error_logger.log_error({
            "error_id": exception.error_id,
            "error_type": exception.__class__.__name__,
            "error_message": exception.message,
            "error_code": exception.error_code,
            "category": exception.category.value,
            "severity": exception.severity.value,
            "request_id": request_id,
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', None),
            "ip_address": self._get_client_ip(request),
            "context": exception.context
        }, exception)
        
        # Send alert if needed
        if exception.should_alert:
            try:
                await alert_manager.send_alert(exception, exception.context)
            except Exception as alert_error:
                logger.error("Failed to send alert", error=str(alert_error))
        
        # Update error statistics
        self.error_stats.record_error(exception.category, exception.severity)
        
        # Determine HTTP status code
        status_code = self._get_http_status_code(exception)
        
        # Apply graceful degradation if enabled
        response_data = exception.to_dict()
        if self.enable_graceful_degradation:
            response_data = await self._apply_graceful_degradation(exception, request, response_data)
        
        return JSONResponse(
            status_code=status_code,
            content=response_data,
            headers={"X-Request-ID": request_id, "X-Error-ID": exception.error_id}
        )
    
    async def _handle_http_exception(
        self,
        exception: HTTPException,
        request: Request,
        request_id: str
    ) -> JSONResponse:
        """Handle FastAPI HTTPException."""
        
        # Convert to KessanException for consistent handling
        kessan_exception = self._convert_http_exception(exception)
        kessan_exception.context.update({
            "request_id": request_id,
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', None),
            "ip_address": self._get_client_ip(request)
        })
        
        # Log the error
        error_logger.log_error({
            "error_id": kessan_exception.error_id,
            "error_type": "HTTPException",
            "error_message": str(exception.detail),
            "error_code": f"HTTP_{exception.status_code}",
            "request_id": request_id,
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', None),
            "ip_address": self._get_client_ip(request),
            "status_code": exception.status_code
        })
        
        # Update error statistics
        self.error_stats.record_error(kessan_exception.category, kessan_exception.severity)
        
        return JSONResponse(
            status_code=exception.status_code,
            content={
                "error_id": kessan_exception.error_id,
                "error_code": f"HTTP_{exception.status_code}",
                "message": str(exception.detail),
                "user_message": str(exception.detail),
                "category": kessan_exception.category.value,
                "severity": kessan_exception.severity.value
            },
            headers={"X-Request-ID": request_id, "X-Error-ID": kessan_exception.error_id}
        )
    
    async def _handle_unexpected_exception(
        self,
        exception: Exception,
        request: Request,
        request_id: str
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        
        error_id = str(uuid.uuid4())
        
        # Log the unexpected error with full traceback
        error_logger.log_error({
            "error_id": error_id,
            "error_type": exception.__class__.__name__,
            "error_message": str(exception),
            "error_code": "UNEXPECTED_ERROR",
            "request_id": request_id,
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', None),
            "ip_address": self._get_client_ip(request),
            "stack_trace": traceback.format_exc()
        }, exception)
        
        # Create KessanException for alerting
        kessan_exception = KessanException(
            message=f"Unexpected error: {str(exception)}",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            error_code="UNEXPECTED_ERROR",
            should_alert=True,
            context={
                "request_id": request_id,
                "endpoint": str(request.url.path),
                "method": request.method,
                "user_id": getattr(request.state, 'user_id', None),
                "ip_address": self._get_client_ip(request),
                "exception_type": exception.__class__.__name__
            }
        )
        kessan_exception.error_id = error_id
        
        # Send alert
        try:
            await alert_manager.send_alert(kessan_exception)
        except Exception as alert_error:
            logger.error("Failed to send alert for unexpected error", error=str(alert_error))
        
        # Update error statistics
        self.error_stats.record_error(ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH)
        
        return JSONResponse(
            status_code=500,
            content={
                "error_id": error_id,
                "error_code": "UNEXPECTED_ERROR",
                "message": "An unexpected error occurred",
                "user_message": "An unexpected error occurred. Please try again later.",
                "category": ErrorCategory.SYSTEM_ERROR.value,
                "severity": ErrorSeverity.HIGH.value
            },
            headers={"X-Request-ID": request_id, "X-Error-ID": error_id}
        )
    
    def _convert_http_exception(self, exception: HTTPException) -> KessanException:
        """Convert HTTPException to KessanException."""
        
        # Map HTTP status codes to categories and severities
        if exception.status_code == 400:
            category = ErrorCategory.USER_ERROR
            severity = ErrorSeverity.LOW
        elif exception.status_code == 401:
            category = ErrorCategory.AUTHENTICATION_ERROR
            severity = ErrorSeverity.MEDIUM
        elif exception.status_code == 403:
            category = ErrorCategory.AUTHORIZATION_ERROR
            severity = ErrorSeverity.MEDIUM
        elif exception.status_code == 404:
            category = ErrorCategory.USER_ERROR
            severity = ErrorSeverity.LOW
        elif exception.status_code == 422:
            category = ErrorCategory.VALIDATION_ERROR
            severity = ErrorSeverity.LOW
        elif exception.status_code == 429:
            category = ErrorCategory.RATE_LIMIT_ERROR
            severity = ErrorSeverity.MEDIUM
        elif 500 <= exception.status_code < 600:
            category = ErrorCategory.SYSTEM_ERROR
            severity = ErrorSeverity.HIGH
        else:
            category = ErrorCategory.SYSTEM_ERROR
            severity = ErrorSeverity.MEDIUM
        
        return KessanException(
            message=str(exception.detail),
            category=category,
            severity=severity,
            error_code=f"HTTP_{exception.status_code}",
            user_message=str(exception.detail)
        )
    
    def _get_http_status_code(self, exception: KessanException) -> int:
        """Get appropriate HTTP status code for KessanException."""
        
        status_code_map = {
            ErrorCategory.USER_ERROR: 400,
            ErrorCategory.AUTHENTICATION_ERROR: 401,
            ErrorCategory.AUTHORIZATION_ERROR: 403,
            ErrorCategory.VALIDATION_ERROR: 422,
            ErrorCategory.RATE_LIMIT_ERROR: 429,
            ErrorCategory.QUOTA_ERROR: 429,
            ErrorCategory.BUSINESS_ERROR: 422,
            ErrorCategory.EXTERNAL_API_ERROR: 503,
            ErrorCategory.DATA_ERROR: 500,
            ErrorCategory.SYSTEM_ERROR: 500
        }
        
        return status_code_map.get(exception.category, 500)
    
    async def _apply_graceful_degradation(
        self,
        exception: KessanException,
        request: Request,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply graceful degradation strategies."""
        
        # Add degradation suggestions based on error type
        degradation_suggestions = []
        
        if exception.category == ErrorCategory.EXTERNAL_API_ERROR:
            degradation_suggestions.extend([
                "Using cached data where available",
                "Some features may be temporarily limited",
                "Real-time data may be delayed"
            ])
        
        elif exception.category == ErrorCategory.QUOTA_ERROR:
            degradation_suggestions.extend([
                "Consider upgrading your subscription plan",
                "Free tier limitations are in effect",
                "Usage will reset at the next billing cycle"
            ])
        
        elif exception.category == ErrorCategory.SYSTEM_ERROR:
            degradation_suggestions.extend([
                "System is operating in degraded mode",
                "Some features may be temporarily unavailable",
                "Please try again in a few minutes"
            ])
        
        if degradation_suggestions:
            response_data["degradation_info"] = {
                "suggestions": degradation_suggestions,
                "retry_after": self._get_retry_after_seconds(exception)
            }
        
        return response_data
    
    def _get_retry_after_seconds(self, exception: KessanException) -> int:
        """Get suggested retry delay in seconds."""
        
        retry_map = {
            ErrorCategory.RATE_LIMIT_ERROR: 60,
            ErrorCategory.QUOTA_ERROR: 3600,  # 1 hour
            ErrorCategory.EXTERNAL_API_ERROR: 300,  # 5 minutes
            ErrorCategory.SYSTEM_ERROR: 180  # 3 minutes
        }
        
        return retry_map.get(exception.category, 60)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class ErrorStatistics:
    """Track error statistics for monitoring."""
    
    def __init__(self):
        self.error_counts = {}
        self.last_reset = datetime.now(timezone.utc)
    
    def record_error(self, category: ErrorCategory, severity: ErrorSeverity) -> None:
        """Record an error occurrence."""
        key = f"{category.value}:{severity.value}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Reset counts every hour
        now = datetime.now(timezone.utc)
        if (now - self.last_reset).total_seconds() > 3600:
            self._reset_counts()
            self.last_reset = now
    
    def get_error_rate(self, category: ErrorCategory = None) -> float:
        """Get error rate for category or overall."""
        if category:
            total = sum(
                count for key, count in self.error_counts.items()
                if key.startswith(f"{category.value}:")
            )
        else:
            total = sum(self.error_counts.values())
        
        # Calculate rate per minute (assuming 1 hour window)
        return total / 60.0
    
    def _reset_counts(self) -> None:
        """Reset error counts."""
        self.error_counts.clear()


class GracefulDegradationService:
    """Service for implementing graceful degradation strategies."""
    
    @staticmethod
    async def get_cached_stock_data(ticker: str) -> Dict[str, Any]:
        """Get cached stock data when live data is unavailable."""
        try:
            from app.core.cache import cache
            cached_data = await cache.get(f"stock_data:{ticker}")
            if cached_data:
                return {
                    "data": cached_data,
                    "is_cached": True,
                    "cache_age": "unknown",
                    "message": "Live data unavailable, showing cached data"
                }
        except Exception:
            pass
        
        return {
            "data": None,
            "is_cached": False,
            "message": "No data available"
        }
    
    @staticmethod
    async def get_basic_analysis(ticker: str) -> Dict[str, Any]:
        """Get basic technical analysis when AI analysis fails."""
        return {
            "analysis_type": "basic_technical",
            "rating": "neutral",
            "confidence": 0.5,
            "key_factors": ["Technical analysis only", "Limited data available"],
            "message": "AI analysis unavailable, showing basic technical analysis",
            "is_degraded": True
        }
    
    @staticmethod
    def get_error_response_template(error_category: ErrorCategory) -> Dict[str, Any]:
        """Get error response template for graceful degradation."""
        templates = {
            ErrorCategory.EXTERNAL_API_ERROR: {
                "fallback_available": True,
                "degraded_features": ["Real-time data", "Advanced analysis"],
                "available_features": ["Cached data", "Basic analysis"]
            },
            ErrorCategory.QUOTA_ERROR: {
                "fallback_available": False,
                "upgrade_suggestion": True,
                "reset_time": "Next billing cycle"
            },
            ErrorCategory.SYSTEM_ERROR: {
                "fallback_available": True,
                "degraded_features": ["All features may be affected"],
                "retry_recommended": True
            }
        }
        
        return templates.get(error_category, {
            "fallback_available": False,
            "retry_recommended": True
        })