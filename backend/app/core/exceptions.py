"""
Custom exception classes with error categorization for Project Kessan.
"""

import uuid
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCategory(Enum):
    """Error categories for classification and handling."""

    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"
    BUSINESS_ERROR = "business_error"
    EXTERNAL_API_ERROR = "external_api_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    QUOTA_ERROR = "quota_error"
    DATA_ERROR = "data_error"


class ErrorSeverity(Enum):
    """Error severity levels for alerting."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KessanException(Exception):
    """Base exception class for all Project Kessan errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        should_alert: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or self._generate_error_code()
        self.details = details or {}
        self.user_message = user_message or self._get_default_user_message()
        self.should_alert = should_alert
        self.context = context or {}
        self.error_id = str(uuid.uuid4())
        super().__init__(message)

    def _generate_error_code(self) -> str:
        """Generate a unique error code based on exception type."""
        return f"{self.__class__.__name__.upper().replace('EXCEPTION', '')}_ERROR"

    def _get_default_user_message(self) -> str:
        """Get default user-friendly message based on category."""
        user_messages = {
            ErrorCategory.USER_ERROR: "Invalid request. Please check your input and try again.",
            ErrorCategory.SYSTEM_ERROR: "A system error occurred. Please try again later.",
            ErrorCategory.BUSINESS_ERROR: "Unable to process your request due to business rules.",
            ErrorCategory.EXTERNAL_API_ERROR: "External service is temporarily unavailable. Please try again later.",
            ErrorCategory.AUTHENTICATION_ERROR: "Authentication failed. Please log in again.",
            ErrorCategory.AUTHORIZATION_ERROR: "You don't have permission to access this resource.",
            ErrorCategory.VALIDATION_ERROR: "Invalid data provided. Please check your input.",
            ErrorCategory.RATE_LIMIT_ERROR: "Too many requests. Please wait before trying again.",
            ErrorCategory.QUOTA_ERROR: "Usage quota exceeded. Please upgrade your plan or wait for reset.",
            ErrorCategory.DATA_ERROR: "Data processing error occurred. Please try again later.",
        }
        return user_messages.get(
            self.category, "An error occurred. Please try again later."
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and API responses."""
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "context": self.context,
            "should_alert": self.should_alert,
        }


# User Error Exceptions
class InvalidTickerException(KessanException):
    """Raised when an invalid ticker symbol is provided."""

    def __init__(self, ticker: str, **kwargs):
        super().__init__(
            message=f"Invalid ticker symbol: {ticker}",
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.LOW,
            details={"ticker": ticker},
            user_message=f"The ticker symbol '{ticker}' is not valid or not found.",
            **kwargs,
        )


class InvalidDateRangeException(KessanException):
    """Raised when an invalid date range is provided."""

    def __init__(self, start_date: str, end_date: str, **kwargs):
        super().__init__(
            message=f"Invalid date range: {start_date} to {end_date}",
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.LOW,
            details={"start_date": start_date, "end_date": end_date},
            user_message="Invalid date range provided. Please check your dates.",
            **kwargs,
        )


# Authentication and Authorization Exceptions
class AuthenticationFailedException(KessanException):
    """Raised when authentication fails."""

    def __init__(self, reason: str = "Invalid credentials", **kwargs):
        super().__init__(
            message=f"Authentication failed: {reason}",
            category=ErrorCategory.AUTHENTICATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"reason": reason},
            user_message="Authentication failed. Please check your credentials and try again.",
            should_alert=True,
            **kwargs,
        )


class TokenExpiredException(KessanException):
    """Raised when JWT token has expired."""

    def __init__(self, **kwargs):
        super().__init__(
            message="JWT token has expired",
            category=ErrorCategory.AUTHENTICATION_ERROR,
            severity=ErrorSeverity.LOW,
            user_message="Your session has expired. Please log in again.",
            **kwargs,
        )


class InsufficientPermissionsException(KessanException):
    """Raised when user lacks required permissions."""

    def __init__(self, required_permission: str, **kwargs):
        super().__init__(
            message=f"Insufficient permissions: {required_permission} required",
            category=ErrorCategory.AUTHORIZATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"required_permission": required_permission},
            user_message="You don't have permission to access this resource.",
            should_alert=True,
            **kwargs,
        )


# Business Logic Exceptions
class QuotaExceededException(KessanException):
    """Raised when user quota is exceeded."""

    def __init__(self, quota_type: str, current_usage: int, limit: int, **kwargs):
        super().__init__(
            message=f"Quota exceeded: {quota_type} usage {current_usage}/{limit}",
            category=ErrorCategory.QUOTA_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={
                "quota_type": quota_type,
                "current_usage": current_usage,
                "limit": limit,
            },
            user_message=f"You have exceeded your {quota_type} quota. Please upgrade your plan or wait for reset.",
            should_alert=True,
            **kwargs,
        )


class BudgetExceededException(KessanException):
    """Raised when AI analysis budget is exceeded."""

    def __init__(self, budget_type: str = "daily", **kwargs):
        kwargs.setdefault("should_alert", True)
        super().__init__(
            message=f"AI analysis {budget_type} budget exceeded",
            category=ErrorCategory.BUSINESS_ERROR,
            severity=ErrorSeverity.HIGH,
            details={"budget_type": budget_type},
            user_message="AI analysis budget exceeded. Service temporarily unavailable.",
            **kwargs,
        )


class SubscriptionRequiredException(KessanException):
    """Raised when a paid subscription is required."""

    def __init__(self, feature: str, required_plan: str, **kwargs):
        super().__init__(
            message=f"Subscription required: {feature} requires {required_plan} plan",
            category=ErrorCategory.BUSINESS_ERROR,
            severity=ErrorSeverity.LOW,
            details={"feature": feature, "required_plan": required_plan},
            user_message=f"This feature requires a {required_plan} subscription. Please upgrade your plan.",
            **kwargs,
        )


# External API Exceptions
class DataSourceUnavailableException(KessanException):
    """Raised when a data source is unavailable."""

    def __init__(self, source: str, **kwargs):
        super().__init__(
            message=f"Data source unavailable: {source}",
            category=ErrorCategory.EXTERNAL_API_ERROR,
            severity=ErrorSeverity.HIGH,
            details={"source": source},
            user_message="Data source is temporarily unavailable. Please try again later.",
            should_alert=True,
            **kwargs,
        )


class APIRateLimitException(KessanException):
    """Raised when external API rate limit is hit."""

    def __init__(self, api_name: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message=f"API rate limit exceeded: {api_name}",
            category=ErrorCategory.RATE_LIMIT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"api_name": api_name, "retry_after": retry_after},
            user_message="Service is temporarily busy. Please try again in a few minutes.",
            should_alert=True,
            **kwargs,
        )


class ExternalAPIException(KessanException):
    """Raised when external API returns an error."""

    def __init__(self, api_name: str, status_code: int, error_message: str, **kwargs):
        kwargs.setdefault("should_alert", True)
        super().__init__(
            message=f"External API error: {api_name} returned {status_code}: {error_message}",
            category=ErrorCategory.EXTERNAL_API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={
                "api_name": api_name,
                "status_code": status_code,
                "error_message": error_message,
            },
            user_message="External service error. Please try again later.",
            **kwargs,
        )


# System Exceptions
class DatabaseConnectionException(KessanException):
    """Raised when database connection fails."""

    def __init__(self, **kwargs):
        kwargs.setdefault("should_alert", True)
        super().__init__(
            message="Database connection failed",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            user_message="System temporarily unavailable. Please try again later.",
            **kwargs,
        )


class CacheConnectionException(KessanException):
    """Raised when cache connection fails."""

    def __init__(self, **kwargs):
        kwargs.setdefault("should_alert", True)
        super().__init__(
            message="Cache connection failed",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            user_message="System performance may be degraded. Please try again later.",
            **kwargs,
        )


class ConfigurationException(KessanException):
    """Raised when configuration is invalid."""

    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            message=f"Invalid configuration: {config_key}",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            details={"config_key": config_key},
            user_message="System configuration error. Please contact support.",
            should_alert=True,
            **kwargs,
        )


# Data Processing Exceptions
class DataValidationException(KessanException):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: Any, reason: str, **kwargs):
        super().__init__(
            message=f"Data validation failed: {field} = {value} ({reason})",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.LOW,
            details={"field": field, "value": str(value), "reason": reason},
            user_message=f"Invalid {field}: {reason}",
            **kwargs,
        )


class DataTransformationException(KessanException):
    """Raised when data transformation fails."""

    def __init__(self, transformation: str, **kwargs):
        super().__init__(
            message=f"Data transformation failed: {transformation}",
            category=ErrorCategory.DATA_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"transformation": transformation},
            user_message="Data processing error. Please try again later.",
            should_alert=True,
            **kwargs,
        )


class DataIntegrityException(KessanException):
    """Raised when data integrity check fails."""

    def __init__(self, check: str, **kwargs):
        super().__init__(
            message=f"Data integrity check failed: {check}",
            category=ErrorCategory.DATA_ERROR,
            severity=ErrorSeverity.HIGH,
            details={"check": check},
            user_message="Data integrity error detected. Please contact support.",
            should_alert=True,
            **kwargs,
        )


# AI Analysis Exceptions
class AnalysisGenerationException(KessanException):
    """Raised when AI analysis generation fails."""

    def __init__(self, ticker: str, analysis_type: str, **kwargs):
        super().__init__(
            message=f"Analysis generation failed: {ticker} ({analysis_type})",
            category=ErrorCategory.EXTERNAL_API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"ticker": ticker, "analysis_type": analysis_type},
            user_message="Analysis generation failed. Please try again later.",
            should_alert=True,
            **kwargs,
        )


class ResponseParsingException(KessanException):
    """Raised when AI response parsing fails."""

    def __init__(self, response_type: str, **kwargs):
        super().__init__(
            message=f"Response parsing failed: {response_type}",
            category=ErrorCategory.DATA_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"response_type": response_type},
            user_message="Analysis processing error. Please try again later.",
            should_alert=True,
            **kwargs,
        )


class PromptBuildException(KessanException):
    """Raised when prompt building fails."""

    def __init__(self, prompt_type: str, **kwargs):
        super().__init__(
            message=f"Prompt building failed: {prompt_type}",
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={"prompt_type": prompt_type},
            user_message="Analysis preparation failed. Please try again later.",
            should_alert=True,
            **kwargs,
        )
