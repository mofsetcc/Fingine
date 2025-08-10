"""API response Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# Generic type for data payload
DataT = TypeVar("DataT")


# Base API Response Schemas
class APIResponse(GenericModel, Generic[DataT]):
    """Generic API response schema."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    data: Optional[DataT] = Field(None, description="Response data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request tracking ID")


class ErrorDetail(BaseModel):
    """Error detail schema."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class APIErrorResponse(BaseModel):
    """API error response schema."""

    success: bool = Field(False, description="Always false for error responses")
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    errors: Optional[List[ErrorDetail]] = Field(
        None, description="Detailed error information"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")


# Success Response Schemas
class SuccessResponse(BaseModel):
    """Simple success response schema."""

    success: bool = Field(True, description="Always true for success responses")
    message: str = Field(
        "Operation completed successfully", description="Success message"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class CreatedResponse(GenericModel, Generic[DataT]):
    """Resource creation response schema."""

    success: bool = Field(True, description="Always true for successful creation")
    message: str = Field("Resource created successfully", description="Success message")
    data: DataT = Field(..., description="Created resource data")
    resource_id: Union[UUID, int, str] = Field(
        ..., description="ID of created resource"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class UpdatedResponse(GenericModel, Generic[DataT]):
    """Resource update response schema."""

    success: bool = Field(True, description="Always true for successful update")
    message: str = Field("Resource updated successfully", description="Success message")
    data: DataT = Field(..., description="Updated resource data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class DeletedResponse(BaseModel):
    """Resource deletion response schema."""

    success: bool = Field(True, description="Always true for successful deletion")
    message: str = Field("Resource deleted successfully", description="Success message")
    resource_id: Union[UUID, int, str] = Field(
        ..., description="ID of deleted resource"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# Pagination Response Schemas
class PaginationMeta(BaseModel):
    """Pagination metadata schema."""

    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")


class PaginatedResponse(GenericModel, Generic[DataT]):
    """Paginated response schema."""

    success: bool = Field(True, description="Always true for successful responses")
    message: str = Field("Data retrieved successfully", description="Response message")
    data: List[DataT] = Field(..., description="Response data items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# Validation Error Response Schema
class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""

    success: bool = Field(False, description="Always false for validation errors")
    message: str = Field("Validation failed", description="Error message")
    error_code: str = Field("VALIDATION_ERROR", description="Error code")
    validation_errors: List[ErrorDetail] = Field(
        ..., description="Validation error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# Authentication Response Schemas
class AuthenticationErrorResponse(BaseModel):
    """Authentication error response schema."""

    success: bool = Field(False, description="Always false for auth errors")
    message: str = Field("Authentication failed", description="Error message")
    error_code: str = Field("AUTHENTICATION_ERROR", description="Error code")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class AuthorizationErrorResponse(BaseModel):
    """Authorization error response schema."""

    success: bool = Field(False, description="Always false for authorization errors")
    message: str = Field("Access denied", description="Error message")
    error_code: str = Field("AUTHORIZATION_ERROR", description="Error code")
    required_permissions: Optional[List[str]] = Field(
        None, description="Required permissions"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# Rate Limiting Response Schema
class RateLimitErrorResponse(BaseModel):
    """Rate limit error response schema."""

    success: bool = Field(False, description="Always false for rate limit errors")
    message: str = Field("Rate limit exceeded", description="Error message")
    error_code: str = Field("RATE_LIMIT_EXCEEDED", description="Error code")
    retry_after: int = Field(..., description="Seconds to wait before retrying")
    limit: int = Field(..., description="Rate limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_time: datetime = Field(..., description="When the rate limit resets")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# Health Check Response Schema
class HealthCheckResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Service uptime in seconds")
    checks: Dict[str, Dict[str, Any]] = Field(
        ..., description="Individual health checks"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "uptime": 3600.0,
                "checks": {
                    "database": {
                        "status": "healthy",
                        "response_time": 0.05,
                        "details": "Connection successful",
                    },
                    "redis": {
                        "status": "healthy",
                        "response_time": 0.01,
                        "details": "Connection successful",
                    },
                    "external_api": {
                        "status": "degraded",
                        "response_time": 2.5,
                        "details": "Slow response times",
                    },
                },
            }
        }
    }


# Batch Operation Response Schemas
class BatchOperationResult(BaseModel):
    """Batch operation result schema."""

    total_requested: int = Field(..., description="Total items requested")
    successful: int = Field(..., description="Successfully processed items")
    failed: int = Field(..., description="Failed items")
    skipped: int = Field(0, description="Skipped items")
    errors: List[ErrorDetail] = Field(default_factory=list, description="Error details")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    processing_time: float = Field(..., description="Processing time in seconds")


class BatchResponse(GenericModel, Generic[DataT]):
    """Batch operation response schema."""

    success: bool = Field(..., description="Whether the batch operation was successful")
    message: str = Field(..., description="Response message")
    result: BatchOperationResult = Field(..., description="Batch operation results")
    data: Optional[List[DataT]] = Field(None, description="Processed data items")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# File Upload Response Schema
class FileUploadResponse(BaseModel):
    """File upload response schema."""

    success: bool = Field(True, description="Upload success status")
    message: str = Field("File uploaded successfully", description="Response message")
    file_id: str = Field(..., description="Uploaded file ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File MIME type")
    upload_url: str = Field(..., description="File access URL")
    expires_at: Optional[datetime] = Field(None, description="URL expiration time")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Upload timestamp"
    )


# Export Response Schema
class ExportResponse(BaseModel):
    """Data export response schema."""

    success: bool = Field(True, description="Export success status")
    message: str = Field(
        "Export completed successfully", description="Response message"
    )
    export_id: UUID = Field(..., description="Export job ID")
    download_url: str = Field(..., description="Download URL")
    file_format: str = Field(..., description="Export file format")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    record_count: int = Field(..., description="Number of exported records")
    expires_at: datetime = Field(..., description="Download URL expiration")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Export timestamp"
    )


# Search Response Schema
class SearchMeta(BaseModel):
    """Search metadata schema."""

    query: str = Field(..., description="Search query")
    total_results: int = Field(..., description="Total search results")
    search_time: float = Field(..., description="Search time in seconds")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict, description="Applied filters"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Search suggestions"
    )


class SearchResponse(GenericModel, Generic[DataT]):
    """Search response schema."""

    success: bool = Field(True, description="Search success status")
    message: str = Field(
        "Search completed successfully", description="Response message"
    )
    data: List[DataT] = Field(..., description="Search results")
    meta: SearchMeta = Field(..., description="Search metadata")
    pagination: Optional[PaginationMeta] = Field(None, description="Pagination info")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# Analytics Response Schema
class AnalyticsResponse(BaseModel):
    """Analytics response schema."""

    success: bool = Field(True, description="Analytics success status")
    message: str = Field(
        "Analytics data retrieved successfully", description="Response message"
    )
    data: Dict[str, Any] = Field(..., description="Analytics data")
    period: str = Field(..., description="Analytics period")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Generation timestamp"
    )
    cache_expires_at: Optional[datetime] = Field(
        None, description="Cache expiration time"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


# WebSocket Response Schemas
class WebSocketMessage(BaseModel):
    """WebSocket message schema."""

    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    message_id: Optional[str] = Field(None, description="Message ID")


class WebSocketErrorMessage(BaseModel):
    """WebSocket error message schema."""

    type: str = Field("error", description="Message type")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )


# Status Response Schema
class StatusResponse(BaseModel):
    """Generic status response schema."""

    success: bool = Field(..., description="Operation success status")
    status: str = Field(..., description="Current status")
    message: str = Field(..., description="Status message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional status details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Status timestamp"
    )
