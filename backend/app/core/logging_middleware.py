"""
Logging middleware for FastAPI to capture request/response data.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import api_logger
from app.core.encryption import data_anonymizer


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses with structured data."""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log structured data."""
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Capture request start time
        start_time = time.time()
        
        # Extract request data
        request_data = await self._extract_request_data(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract response data
            response_data = self._extract_response_data(
                response, request_id, response_time_ms
            )
            
            # Log successful request
            request_data.update({
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "response_size": response_data.get("response_size_bytes"),
            })
            
            api_logger.log_api_request(request_data)
            api_logger.log_api_response(response_data)
            
            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate response time for error case
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log error request
            request_data.update({
                "status_code": 500,
                "response_time_ms": response_time_ms,
                "error_message": str(e),
            })
            
            api_logger.log_api_request(request_data)
            
            # Re-raise the exception
            raise
    
    async def _extract_request_data(self, request: Request, request_id: str) -> dict:
        """Extract structured data from the request."""
        # Get client IP (handle proxy headers)
        client_ip = self._get_client_ip(request)
        
        # Get request body size
        request_size = 0
        if hasattr(request, "body"):
            try:
                body = await request.body()
                request_size = len(body) if body else 0
            except Exception:
                request_size = 0
        
        # Extract user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        # Anonymize sensitive data for logging
        anonymized_data = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": str(request.url.path),
            "query_params": data_anonymizer.anonymize_dict(dict(request.query_params)),
            "user_id": data_anonymizer.anonymize_user_id(user_id) if user_id else None,
            "ip_address": data_anonymizer.anonymize_ip(client_ip),
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer"),
            "request_size": request_size,
            "content_type": request.headers.get("content-type"),
        }
        
        return anonymized_data
    
    def _extract_response_data(self, response: Response, request_id: str, response_time_ms: int) -> dict:
        """Extract structured data from the response."""
        # Get response size from content-length header
        response_size = response.headers.get("content-length")
        if response_size:
            response_size = int(response_size)
        else:
            response_size = None
        
        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "response_size_bytes": response_size,
            "content_type": response.headers.get("content-type"),
            "cache_hit": response.headers.get("X-Cache-Hit") == "true",
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address, handling proxy headers."""
        # Check for forwarded headers (common in load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class BusinessEventLogger:
    """Helper class for logging business events throughout the application."""
    
    @staticmethod
    def log_user_registration(user_id: str, registration_method: str, metadata: dict = None):
        """Log user registration event."""
        from app.core.logging import business_logger
        
        business_logger.log_business_event({
            "event_name": "user_registration",
            "event_category": "authentication",
            "user_id": data_anonymizer.anonymize_user_id(user_id),
            "properties": {
                "registration_method": registration_method,
            },
            "metadata": data_anonymizer.anonymize_dict(metadata or {}),
        })
    
    @staticmethod
    def log_user_login(user_id: str, login_method: str, success: bool, metadata: dict = None):
        """Log user login attempt."""
        from app.core.logging import business_logger
        
        business_logger.log_business_event({
            "event_name": "user_login",
            "event_category": "authentication",
            "user_id": data_anonymizer.anonymize_user_id(user_id),
            "properties": {
                "login_method": login_method,
                "success": success,
            },
            "metadata": data_anonymizer.anonymize_dict(metadata or {}),
        })
    
    @staticmethod
    def log_stock_analysis_request(user_id: str, ticker: str, analysis_type: str, metadata: dict = None):
        """Log stock analysis request."""
        from app.core.logging import business_logger
        
        business_logger.log_business_event({
            "event_name": "stock_analysis_request",
            "event_category": "analysis",
            "user_id": data_anonymizer.anonymize_user_id(user_id),
            "properties": {
                "ticker": ticker,
                "analysis_type": analysis_type,
            },
            "metadata": data_anonymizer.anonymize_dict(metadata or {}),
        })
    
    @staticmethod
    def log_subscription_change(user_id: str, old_plan: str, new_plan: str, metadata: dict = None):
        """Log subscription plan change."""
        from app.core.logging import business_logger
        
        business_logger.log_business_event({
            "event_name": "subscription_change",
            "event_category": "billing",
            "user_id": data_anonymizer.anonymize_user_id(user_id),
            "properties": {
                "old_plan": old_plan,
                "new_plan": new_plan,
            },
            "metadata": data_anonymizer.anonymize_dict(metadata or {}),
        })
    
    @staticmethod
    def log_watchlist_action(user_id: str, action: str, ticker: str, metadata: dict = None):
        """Log watchlist actions (add, remove, view)."""
        from app.core.logging import business_logger
        
        business_logger.log_business_event({
            "event_name": "watchlist_action",
            "event_category": "user_interaction",
            "user_id": data_anonymizer.anonymize_user_id(user_id),
            "properties": {
                "action": action,
                "ticker": ticker,
            },
            "metadata": data_anonymizer.anonymize_dict(metadata or {}),
        })
    
    @staticmethod
    def log_quota_exceeded(user_id: str, quota_type: str, current_usage: int, limit: int, metadata: dict = None):
        """Log quota exceeded events."""
        from app.core.logging import business_logger
        
        business_logger.log_business_event({
            "event_name": "quota_exceeded",
            "event_category": "system",
            "user_id": data_anonymizer.anonymize_user_id(user_id),
            "properties": {
                "quota_type": quota_type,
                "current_usage": current_usage,
                "limit": limit,
            },
            "metadata": data_anonymizer.anonymize_dict(metadata or {}),
        })