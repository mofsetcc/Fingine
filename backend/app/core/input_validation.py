"""
Input validation middleware and utilities for security.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

logger = structlog.get_logger(__name__)


class SecurityViolation(HTTPException):
    """Exception raised when security violation is detected."""
    
    def __init__(self, detail: str = "Security violation detected"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class InputValidator:
    """Input validation and sanitization utilities."""
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(\b(UNION|OR|AND)\s+(SELECT|INSERT|UPDATE|DELETE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT|ONLOAD|ONERROR)\b)",
        r"(\b(EVAL|EXPRESSION|EXEC|EXECUTE)\s*\()",
        r"(\b(CHAR|NCHAR|VARCHAR|NVARCHAR)\s*\()",
        r"(\b(CAST|CONVERT|SUBSTRING|ASCII|CHAR_LENGTH)\s*\()",
        r"(\b(WAITFOR|DELAY|SLEEP)\s*\()",
        r"(\b(XP_|SP_)\w+)",
        r"(\b(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)\b)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<\s*script[^>]*>.*?</\s*script\s*>",
        r"<\s*iframe[^>]*>.*?</\s*iframe\s*>",
        r"<\s*object[^>]*>.*?</\s*object\s*>",
        r"<\s*embed[^>]*>.*?</\s*embed\s*>",
        r"<\s*link[^>]*>",
        r"<\s*meta[^>]*>",
        r"javascript\s*:",
        r"vbscript\s*:",
        r"data\s*:",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"url\s*\(",
        r"@import",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"..%2f",
        r"..%5c",
        r"%252e%252e%252f",
        r"%252e%252e%255c",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig|ping|wget|curl|nc|telnet|ssh|ftp)\b",
        r"\b(rm|mv|cp|chmod|chown|kill|killall|sudo|su)\b",
        r"\b(echo|printf|print)\s+.*[;&|`$]",
    ]
    
    def __init__(self):
        self.sql_regex = re.compile("|".join(self.SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.xss_regex = re.compile("|".join(self.XSS_PATTERNS), re.IGNORECASE)
        self.path_traversal_regex = re.compile("|".join(self.PATH_TRAVERSAL_PATTERNS), re.IGNORECASE)
        self.command_injection_regex = re.compile("|".join(self.COMMAND_INJECTION_PATTERNS), re.IGNORECASE)
    
    def validate_input(self, value: Any, field_name: str = "input") -> Any:
        """
        Validate and sanitize input value.
        
        Args:
            value: Input value to validate
            field_name: Name of the field being validated
            
        Returns:
            Sanitized value
            
        Raises:
            SecurityViolation: If security violation is detected
        """
        if value is None:
            return value
        
        # Convert to string for validation
        str_value = str(value)
        
        # URL decode to catch encoded attacks
        decoded_value = unquote(str_value)
        
        # Check for SQL injection
        if self.sql_regex.search(decoded_value):
            logger.warning(
                "SQL injection attempt detected",
                field=field_name,
                value=str_value[:100],  # Log first 100 chars only
                pattern="sql_injection"
            )
            raise SecurityViolation(f"Invalid input detected in {field_name}")
        
        # Check for XSS
        if self.xss_regex.search(decoded_value):
            logger.warning(
                "XSS attempt detected",
                field=field_name,
                value=str_value[:100],
                pattern="xss"
            )
            raise SecurityViolation(f"Invalid input detected in {field_name}")
        
        # Check for path traversal
        if self.path_traversal_regex.search(decoded_value):
            logger.warning(
                "Path traversal attempt detected",
                field=field_name,
                value=str_value[:100],
                pattern="path_traversal"
            )
            raise SecurityViolation(f"Invalid input detected in {field_name}")
        
        # Check for command injection
        if self.command_injection_regex.search(decoded_value):
            logger.warning(
                "Command injection attempt detected",
                field=field_name,
                value=str_value[:100],
                pattern="command_injection"
            )
            raise SecurityViolation(f"Invalid input detected in {field_name}")
        
        return self._sanitize_value(value)
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize input value."""
        if isinstance(value, str):
            # Remove null bytes
            value = value.replace('\x00', '')
            
            # Limit string length to prevent DoS
            if len(value) > 10000:  # 10KB limit
                raise SecurityViolation("Input too long")
            
            # Basic HTML entity encoding for display
            value = (value
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
        
        return value
    
    def validate_dict(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Recursively validate dictionary data."""
        validated_data = {}
        
        for key, value in data.items():
            field_name = f"{prefix}.{key}" if prefix else key
            
            # Validate key name
            self.validate_input(key, f"{field_name}_key")
            
            # Validate value
            if isinstance(value, dict):
                validated_data[key] = self.validate_dict(value, field_name)
            elif isinstance(value, list):
                validated_data[key] = self.validate_list(value, field_name)
            else:
                validated_data[key] = self.validate_input(value, field_name)
        
        return validated_data
    
    def validate_list(self, data: List[Any], field_name: str) -> List[Any]:
        """Validate list data."""
        validated_list = []
        
        for i, item in enumerate(data):
            item_field_name = f"{field_name}[{i}]"
            
            if isinstance(item, dict):
                validated_list.append(self.validate_dict(item, item_field_name))
            elif isinstance(item, list):
                validated_list.append(self.validate_list(item, item_field_name))
            else:
                validated_list.append(self.validate_input(item, item_field_name))
        
        return validated_list
    
    def validate_ticker(self, ticker: str) -> str:
        """Validate stock ticker symbol."""
        if not ticker:
            raise SecurityViolation("Ticker symbol is required")
        
        # Basic ticker validation (alphanumeric, dots, hyphens)
        if not re.match(r'^[A-Za-z0-9.-]+$', ticker):
            raise SecurityViolation("Invalid ticker symbol format")
        
        # Length validation
        if len(ticker) > 20:
            raise SecurityViolation("Ticker symbol too long")
        
        return ticker.upper()
    
    def validate_email(self, email: str) -> str:
        """Validate email address."""
        if not email:
            raise SecurityViolation("Email is required")
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise SecurityViolation("Invalid email format")
        
        # Length validation
        if len(email) > 254:
            raise SecurityViolation("Email too long")
        
        return email.lower()
    
    def validate_password(self, password: str) -> str:
        """Validate password strength."""
        if not password:
            raise SecurityViolation("Password is required")
        
        # Import here to avoid circular imports
        from app.core.security import validate_password_strength
        
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            raise SecurityViolation(f"Password validation failed: {', '.join(errors)}")
        
        return password


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and sanitization."""
    
    def __init__(self, app):
        super().__init__(app)
        self.validator = InputValidator()
        
        # Paths that require strict validation
        self.strict_validation_paths = {
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/stocks/",
            "/api/v1/analysis/",
        }
        
        # Exempt paths from validation
        self.exempt_paths = {
            "/health",
            "/health/detailed",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate input data in requests."""
        
        # Skip validation for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        try:
            # Validate query parameters
            if request.query_params:
                for key, value in request.query_params.items():
                    self.validator.validate_input(value, f"query.{key}")
            
            # Validate path parameters
            if hasattr(request, 'path_params') and request.path_params:
                for key, value in request.path_params.items():
                    self.validator.validate_input(value, f"path.{key}")
            
            # Validate request body for POST/PUT/PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)
            
            # Validate headers (basic check)
            self._validate_headers(request)
            
        except SecurityViolation as e:
            logger.warning(
                "Input validation failed",
                path=request.url.path,
                method=request.method,
                error=str(e),
                client_ip=request.client.host if request.client else "unknown"
            )
            raise e
        except Exception as e:
            logger.error(
                "Input validation error",
                path=request.url.path,
                method=request.method,
                error=str(e)
            )
            # Don't expose internal errors
            raise SecurityViolation("Input validation failed")
        
        return await call_next(request)
    
    async def _validate_request_body(self, request: Request):
        """Validate request body data."""
        try:
            # Get content type
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                # Read and validate JSON body
                body = await request.body()
                if body:
                    try:
                        json_data = json.loads(body)
                        if isinstance(json_data, dict):
                            self.validator.validate_dict(json_data)
                        elif isinstance(json_data, list):
                            self.validator.validate_list(json_data, "body")
                        else:
                            self.validator.validate_input(json_data, "body")
                    except json.JSONDecodeError:
                        raise SecurityViolation("Invalid JSON format")
            
            elif "application/x-www-form-urlencoded" in content_type:
                # Validate form data
                form_data = await request.form()
                for key, value in form_data.items():
                    self.validator.validate_input(value, f"form.{key}")
            
            elif "multipart/form-data" in content_type:
                # Basic validation for multipart data
                form_data = await request.form()
                for key, value in form_data.items():
                    if hasattr(value, 'filename'):
                        # File upload validation
                        self._validate_file_upload(value, key)
                    else:
                        self.validator.validate_input(value, f"form.{key}")
        
        except SecurityViolation:
            raise
        except Exception as e:
            logger.error("Request body validation error", error=str(e))
            raise SecurityViolation("Request body validation failed")
    
    def _validate_headers(self, request: Request):
        """Validate request headers."""
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-host",
            "x-original-url",
            "x-rewrite-url",
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                self.validator.validate_input(value, f"header.{header}")
        
        # Validate User-Agent (basic check)
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 1000:  # Reasonable limit
            raise SecurityViolation("User-Agent header too long")
    
    def _validate_file_upload(self, file, field_name: str):
        """Validate file upload."""
        if not hasattr(file, 'filename') or not file.filename:
            return
        
        filename = file.filename
        
        # Validate filename
        self.validator.validate_input(filename, f"{field_name}.filename")
        
        # Check file extension
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.csv', '.xlsx'}
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if f'.{file_ext}' not in allowed_extensions:
            raise SecurityViolation(f"File type not allowed: {file_ext}")
        
        # Check file size (if available)
        if hasattr(file, 'size') and file.size > 10 * 1024 * 1024:  # 10MB limit
            raise SecurityViolation("File too large")


# Global validator instance
input_validator = InputValidator()