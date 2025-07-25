"""
Structured logging configuration for the application.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging() -> None:
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
            structlog.processors.JSONRenderer() if not settings.DEBUG 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class StructuredLogger:
    """Structured logger for business events and API requests."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(service_name)
    
    def log_api_request(self, request_data: Dict[str, Any]) -> None:
        """Log API request with structured data."""
        self.logger.info(
            "api_request",
            event_type="api_request",
            method=request_data.get("method"),
            endpoint=request_data.get("endpoint"),
            user_id=request_data.get("user_id"),
            response_time_ms=request_data.get("response_time"),
            status_code=request_data.get("status_code"),
            ip_address=self._anonymize_ip(request_data.get("ip_address")),
        )
    
    def log_ai_analysis_request(self, analysis_data: Dict[str, Any]) -> None:
        """Log AI analysis request with cost tracking."""
        self.logger.info(
            "ai_analysis",
            event_type="ai_analysis",
            ticker=analysis_data.get("ticker"),
            analysis_type=analysis_data.get("analysis_type"),
            model_version=analysis_data.get("model_version"),
            processing_time_ms=analysis_data.get("processing_time"),
            cost_usd=analysis_data.get("cost"),
            cache_hit=analysis_data.get("cache_hit", False),
        )
    
    def log_business_event(self, event_data: Dict[str, Any]) -> None:
        """Log business events for analytics."""
        self.logger.info(
            "business_event",
            event_type="business_event",
            event_name=event_data.get("event_name"),
            user_id=event_data.get("user_id"),
            metadata=event_data.get("metadata", {}),
        )
    
    @staticmethod
    def _anonymize_ip(ip_address: str) -> str:
        """Anonymize IP address for privacy."""
        if not ip_address:
            return "unknown"
        
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return "anonymized"