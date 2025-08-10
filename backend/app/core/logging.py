"""
Structured logging configuration for the application.
"""

import json
import logging
import sys
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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
            structlog.processors.JSONRenderer()
            if not settings.DEBUG
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
    """Enhanced structured logger for business events, API requests, and error tracking."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(service_name)

    def log_api_request(self, request_data: Dict[str, Any]) -> None:
        """Log API request with structured data and anonymized IP."""
        log_entry = {
            "event_type": "api_request",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "request_id": request_data.get("request_id", str(uuid.uuid4())),
            "method": request_data.get("method"),
            "endpoint": request_data.get("endpoint"),
            "user_id": request_data.get("user_id"),
            "user_agent": request_data.get("user_agent"),
            "response_time_ms": request_data.get("response_time_ms"),
            "status_code": request_data.get("status_code"),
            "ip_address": self._anonymize_ip(request_data.get("ip_address")),
            "request_size_bytes": request_data.get("request_size"),
            "response_size_bytes": request_data.get("response_size"),
            "error_message": request_data.get("error_message"),
        }

        # Remove None values for cleaner logs
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        if request_data.get("status_code", 200) >= 400:
            self.logger.error("api_request_error", **log_entry)
        else:
            self.logger.info("api_request_success", **log_entry)

    def log_api_response(self, response_data: Dict[str, Any]) -> None:
        """Log API response with structured data."""
        log_entry = {
            "event_type": "api_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "request_id": response_data.get("request_id"),
            "status_code": response_data.get("status_code"),
            "response_time_ms": response_data.get("response_time_ms"),
            "response_size_bytes": response_data.get("response_size_bytes"),
            "cache_hit": response_data.get("cache_hit", False),
            "data_source": response_data.get("data_source"),
        }

        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        self.logger.info("api_response", **log_entry)

    def log_ai_analysis_request(self, analysis_data: Dict[str, Any]) -> None:
        """Log AI analysis request with cost tracking."""
        log_entry = {
            "event_type": "ai_analysis",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "request_id": analysis_data.get("request_id", str(uuid.uuid4())),
            "ticker": analysis_data.get("ticker"),
            "analysis_type": analysis_data.get("analysis_type"),
            "model_version": analysis_data.get("model_version"),
            "processing_time_ms": analysis_data.get("processing_time_ms"),
            "cost_usd": analysis_data.get("cost_usd"),
            "cache_hit": analysis_data.get("cache_hit", False),
            "user_id": analysis_data.get("user_id"),
            "prompt_tokens": analysis_data.get("prompt_tokens"),
            "completion_tokens": analysis_data.get("completion_tokens"),
            "confidence_score": analysis_data.get("confidence_score"),
        }

        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        self.logger.info("ai_analysis_request", **log_entry)

    def log_business_event(self, event_data: Dict[str, Any]) -> None:
        """Log business events for analytics with comprehensive metadata."""
        log_entry = {
            "event_type": "business_event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "event_id": event_data.get("event_id", str(uuid.uuid4())),
            "event_name": event_data.get("event_name"),
            "event_category": event_data.get("event_category"),
            "user_id": event_data.get("user_id"),
            "session_id": event_data.get("session_id"),
            "subscription_tier": event_data.get("subscription_tier"),
            "metadata": event_data.get("metadata", {}),
            "properties": event_data.get("properties", {}),
        }

        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        self.logger.info("business_event", **log_entry)

    def log_error(
        self, error_data: Dict[str, Any], exception: Optional[Exception] = None
    ) -> None:
        """Log structured error information with context."""
        log_entry = {
            "event_type": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "error_id": error_data.get("error_id", str(uuid.uuid4())),
            "error_type": error_data.get("error_type"),
            "error_message": error_data.get("error_message"),
            "error_code": error_data.get("error_code"),
            "user_id": error_data.get("user_id"),
            "request_id": error_data.get("request_id"),
            "endpoint": error_data.get("endpoint"),
            "method": error_data.get("method"),
            "ip_address": self._anonymize_ip(error_data.get("ip_address")),
            "user_agent": error_data.get("user_agent"),
            "context": error_data.get("context", {}),
        }

        if exception:
            log_entry.update(
                {
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                    "stack_trace": traceback.format_exc(),
                }
            )

        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        self.logger.error("application_error", **log_entry)

    def log_data_source_event(self, source_data: Dict[str, Any]) -> None:
        """Log data source events for monitoring and analytics."""
        log_entry = {
            "event_type": "data_source",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "source_name": source_data.get("source_name"),
            "source_type": source_data.get("source_type"),
            "operation": source_data.get("operation"),
            "status": source_data.get("status"),
            "response_time_ms": source_data.get("response_time_ms"),
            "records_processed": source_data.get("records_processed"),
            "error_message": source_data.get("error_message"),
            "cost_usd": source_data.get("cost_usd"),
        }

        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        if source_data.get("status") == "error":
            self.logger.error("data_source_error", **log_entry)
        else:
            self.logger.info("data_source_success", **log_entry)

    def log_performance_metric(self, metric_data: Dict[str, Any]) -> None:
        """Log performance metrics for monitoring."""
        log_entry = {
            "event_type": "performance_metric",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "metric_name": metric_data.get("metric_name"),
            "metric_value": metric_data.get("metric_value"),
            "metric_unit": metric_data.get("metric_unit"),
            "tags": metric_data.get("tags", {}),
            "context": metric_data.get("context", {}),
        }

        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        self.logger.info("performance_metric", **log_entry)

    @staticmethod
    def _anonymize_ip(ip_address: Optional[str]) -> Optional[str]:
        """Anonymize IP address for privacy compliance."""
        if not ip_address:
            return None

        # Handle IPv4
        if "." in ip_address:
            parts = ip_address.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0"

        # Handle IPv6 - anonymize last 64 bits
        if ":" in ip_address:
            parts = ip_address.split(":")
            if len(parts) >= 2:
                # For short IPv6 addresses like ::1, handle specially
                if ip_address.startswith("::"):
                    return "::0"
                # For full addresses, keep first 4 groups
                if len(parts) >= 4:
                    return ":".join(parts[:4]) + "::0"

        return "anonymized"


# Global logger instances for common use cases
api_logger = StructuredLogger("api")
business_logger = StructuredLogger("business")
error_logger = StructuredLogger("error")
performance_logger = StructuredLogger("performance")
