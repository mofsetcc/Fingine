"""Watchlist Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema, PaginatedResponse, TimestampSchema, UUIDSchema
from app.schemas.stock import Stock


# Simple Watchlist Stock Schemas (matching current database model)
class WatchlistStockBase(BaseModel):
    """Base watchlist stock schema."""

    ticker: str = Field(..., max_length=10, description="Stock ticker")
    notes: Optional[str] = Field(
        None, max_length=1000, description="User notes about the stock"
    )


class WatchlistStockCreate(WatchlistStockBase):
    """Watchlist stock creation schema."""

    pass


class WatchlistStockUpdate(BaseModel):
    """Watchlist stock update schema."""

    notes: Optional[str] = Field(
        None, max_length=1000, description="User notes about the stock"
    )


class WatchlistStockWithPrice(WatchlistStockBase):
    """Watchlist stock with current price data."""

    id: Optional[UUID] = Field(None, description="Entry ID")
    user_id: UUID = Field(..., description="User ID")
    created_at: datetime = Field(..., description="When stock was added to watchlist")
    updated_at: datetime = Field(..., description="When stock was last updated")
    stock: Optional[Stock] = Field(None, description="Stock details")

    # Price data
    current_price: Optional[float] = Field(None, description="Current stock price")
    price_change: Optional[float] = Field(
        None, description="Price change from previous close"
    )
    price_change_percent: Optional[float] = Field(
        None, description="Price change percentage"
    )
    volume_today: Optional[int] = Field(None, description="Today's trading volume")
    last_updated: Optional[date] = Field(None, description="Price data last updated")

    # Alert status (simplified)
    price_alert_triggered: bool = Field(
        False, description="Whether price alert was triggered"
    )
    volume_alert_triggered: bool = Field(
        False, description="Whether volume alert was triggered"
    )


# Bulk Operations Schemas
class BulkWatchlistStockOperation(BaseModel):
    """Bulk watchlist stock operation schema."""

    tickers: List[str] = Field(
        ..., min_items=1, max_items=100, description="Stock tickers"
    )


class BulkOperationResult(BaseModel):
    """Bulk operation result schema."""

    successful: List[str] = Field(..., description="Successfully processed tickers")
    failed: List[Dict[str, str]] = Field(..., description="Failed tickers with reasons")
    already_exists: Optional[List[str]] = Field(
        None, description="Tickers already in watchlist"
    )
    not_found: Optional[List[str]] = Field(
        None, description="Tickers not found in watchlist"
    )


# Legacy complex schemas (keeping for future expansion)
class WatchlistBase(BaseModel):
    """Base watchlist schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Watchlist name")
    description: Optional[str] = Field(
        None, max_length=500, description="Watchlist description"
    )
    is_public: bool = Field(False, description="Whether watchlist is public")
    color: Optional[str] = Field(
        None, max_length=7, description="Watchlist color (hex)"
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        """Validate hex color format."""
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("Color must be in hex format (#RRGGBB)")
            try:
                int(v[1:], 16)
            except ValueError:
                raise ValueError("Invalid hex color format")
        return v


class WatchlistCreate(WatchlistBase):
    """Watchlist creation schema."""

    pass


class WatchlistUpdate(BaseModel):
    """Watchlist update schema."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Watchlist name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Watchlist description"
    )
    is_public: Optional[bool] = Field(None, description="Whether watchlist is public")
    color: Optional[str] = Field(
        None, max_length=7, description="Watchlist color (hex)"
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        """Validate hex color format."""
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("Color must be in hex format (#RRGGBB)")
            try:
                int(v[1:], 16)
            except ValueError:
                raise ValueError("Invalid hex color format")
        return v


class Watchlist(UUIDSchema, WatchlistBase, TimestampSchema):
    """Watchlist response schema."""

    user_id: UUID = Field(..., description="Owner user ID")
    stock_count: int = Field(0, description="Number of stocks in watchlist")


class WatchlistWithStocks(Watchlist):
    """Watchlist with stocks response schema."""

    stocks: List["WatchlistStock"] = Field(..., description="Stocks in watchlist")


# Watchlist Stock Schemas
class WatchlistStockBase(BaseModel):
    """Base watchlist stock schema."""

    ticker: str = Field(..., max_length=10, description="Stock ticker")
    notes: Optional[str] = Field(
        None, max_length=1000, description="User notes about the stock"
    )
    target_price: Optional[Decimal] = Field(None, description="User's target price")
    stop_loss_price: Optional[Decimal] = Field(
        None, description="User's stop loss price"
    )
    alert_price_above: Optional[Decimal] = Field(
        None, description="Alert when price goes above"
    )
    alert_price_below: Optional[Decimal] = Field(
        None, description="Alert when price goes below"
    )
    alert_volume_above: Optional[int] = Field(
        None, description="Alert when volume goes above"
    )
    alert_enabled: bool = Field(True, description="Whether alerts are enabled")

    @field_validator(
        "target_price", "stop_loss_price", "alert_price_above", "alert_price_below"
    )
    @classmethod
    def validate_positive_prices(cls, v):
        """Validate that prices are positive."""
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("alert_volume_above")
    @classmethod
    def validate_positive_volume(cls, v):
        """Validate that volume is positive."""
        if v is not None and v <= 0:
            raise ValueError("Volume must be positive")
        return v


class WatchlistStockCreate(WatchlistStockBase):
    """Watchlist stock creation schema."""

    watchlist_id: UUID = Field(..., description="Watchlist ID")


class WatchlistStockUpdate(BaseModel):
    """Watchlist stock update schema."""

    notes: Optional[str] = Field(
        None, max_length=1000, description="User notes about the stock"
    )
    target_price: Optional[Decimal] = Field(None, description="User's target price")
    stop_loss_price: Optional[Decimal] = Field(
        None, description="User's stop loss price"
    )
    alert_price_above: Optional[Decimal] = Field(
        None, description="Alert when price goes above"
    )
    alert_price_below: Optional[Decimal] = Field(
        None, description="Alert when price goes below"
    )
    alert_volume_above: Optional[int] = Field(
        None, description="Alert when volume goes above"
    )
    alert_enabled: Optional[bool] = Field(
        None, description="Whether alerts are enabled"
    )


class WatchlistStock(UUIDSchema, WatchlistStockBase, TimestampSchema):
    """Watchlist stock response schema."""

    watchlist_id: UUID = Field(..., description="Watchlist ID")
    stock: Optional[Stock] = Field(None, description="Stock details")


class WatchlistStockWithPrice(WatchlistStock):
    """Watchlist stock with current price data."""

    current_price: Optional[Decimal] = Field(None, description="Current stock price")
    price_change: Optional[Decimal] = Field(
        None, description="Price change from previous close"
    )
    price_change_percent: Optional[float] = Field(
        None, description="Price change percentage"
    )
    volume_today: Optional[int] = Field(None, description="Today's trading volume")
    last_updated: Optional[datetime] = Field(
        None, description="Price data last updated"
    )

    # Alert status
    price_alert_triggered: bool = Field(
        False, description="Whether price alert was triggered"
    )
    volume_alert_triggered: bool = Field(
        False, description="Whether volume alert was triggered"
    )


# Watchlist Alert Schemas
class WatchlistAlertBase(BaseModel):
    """Base watchlist alert schema."""

    watchlist_stock_id: UUID = Field(..., description="Watchlist stock ID")
    alert_type: str = Field(..., description="Type of alert")
    trigger_value: Decimal = Field(..., description="Value that triggered the alert")
    current_value: Decimal = Field(
        ..., description="Current value when alert triggered"
    )
    message: str = Field(..., description="Alert message")
    is_read: bool = Field(False, description="Whether alert has been read")

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v):
        """Validate alert type."""
        valid_types = [
            "price_above",
            "price_below",
            "volume_above",
            "target_reached",
            "stop_loss_hit",
        ]
        if v not in valid_types:
            raise ValueError(f'Alert type must be one of: {", ".join(valid_types)}')
        return v


class WatchlistAlertCreate(WatchlistAlertBase):
    """Watchlist alert creation schema."""

    pass


class WatchlistAlert(UUIDSchema, WatchlistAlertBase, TimestampSchema):
    """Watchlist alert response schema."""

    watchlist_stock: Optional[WatchlistStock] = Field(
        None, description="Related watchlist stock"
    )


# Watchlist Performance Schemas
class WatchlistPerformance(BaseModel):
    """Watchlist performance schema."""

    watchlist_id: UUID = Field(..., description="Watchlist ID")
    total_value: Decimal = Field(..., description="Total current value")
    total_change: Decimal = Field(..., description="Total change in value")
    total_change_percent: float = Field(..., description="Total change percentage")
    best_performer: Optional[Dict[str, Any]] = Field(
        None, description="Best performing stock"
    )
    worst_performer: Optional[Dict[str, Any]] = Field(
        None, description="Worst performing stock"
    )
    stocks_up: int = Field(..., description="Number of stocks that are up")
    stocks_down: int = Field(..., description="Number of stocks that are down")
    stocks_unchanged: int = Field(..., description="Number of unchanged stocks")
    average_change_percent: float = Field(..., description="Average change percentage")
    calculation_date: datetime = Field(..., description="Performance calculation date")


# Watchlist Statistics Schemas
class WatchlistStatistics(BaseModel):
    """Watchlist statistics schema."""

    user_id: UUID = Field(..., description="User ID")
    total_watchlists: int = Field(..., description="Total number of watchlists")
    total_stocks_watched: int = Field(
        ..., description="Total stocks across all watchlists"
    )
    most_watched_sectors: List[Dict[str, Any]] = Field(
        ..., description="Most watched sectors"
    )
    most_watched_stocks: List[Dict[str, Any]] = Field(
        ..., description="Most watched stocks"
    )
    average_watchlist_size: float = Field(
        ..., description="Average stocks per watchlist"
    )
    alerts_triggered_today: int = Field(..., description="Alerts triggered today")
    alerts_triggered_this_week: int = Field(
        ..., description="Alerts triggered this week"
    )
    performance_summary: Dict[str, Any] = Field(
        ..., description="Overall performance summary"
    )


# Public Watchlist Schemas
class PublicWatchlistSummary(BaseModel):
    """Public watchlist summary schema."""

    id: UUID = Field(..., description="Watchlist ID")
    name: str = Field(..., description="Watchlist name")
    description: Optional[str] = Field(None, description="Watchlist description")
    owner_display_name: str = Field(..., description="Owner display name")
    stock_count: int = Field(..., description="Number of stocks")
    followers_count: int = Field(0, description="Number of followers")
    performance_1d: Optional[float] = Field(None, description="1-day performance")
    performance_1w: Optional[float] = Field(None, description="1-week performance")
    performance_1m: Optional[float] = Field(None, description="1-month performance")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")


class WatchlistFollower(BaseModel):
    """Watchlist follower schema."""

    watchlist_id: UUID = Field(..., description="Watchlist ID")
    user_id: UUID = Field(..., description="Follower user ID")
    followed_at: datetime = Field(..., description="When user started following")


# Watchlist Import/Export Schemas
class WatchlistImportRequest(BaseModel):
    """Watchlist import request schema."""

    name: str = Field(..., description="Name for imported watchlist")
    tickers: List[str] = Field(
        ..., min_items=1, max_items=500, description="Stock tickers to import"
    )
    source: Optional[str] = Field(None, description="Import source")

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
        """Validate ticker list."""
        if len(set(v)) != len(v):
            raise ValueError("Duplicate tickers are not allowed")
        return [ticker.upper().strip() for ticker in v]


class WatchlistExportRequest(BaseModel):
    """Watchlist export request schema."""

    watchlist_ids: List[UUID] = Field(
        ..., min_items=1, max_items=50, description="Watchlist IDs to export"
    )
    format: str = Field("csv", description="Export format")
    include_notes: bool = Field(True, description="Include user notes")
    include_alerts: bool = Field(True, description="Include alert settings")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        """Validate export format."""
        if v not in ["csv", "excel", "json"]:
            raise ValueError("Format must be one of: csv, excel, json")
        return v


class WatchlistExportResponse(BaseModel):
    """Watchlist export response schema."""

    export_id: UUID = Field(..., description="Export job ID")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    status: str = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Export creation time")
    expires_at: Optional[datetime] = Field(None, description="Download expiration time")


# Bulk Operations Schemas
class BulkWatchlistStockOperation(BaseModel):
    """Bulk watchlist stock operation schema."""

    operation: str = Field(..., description="Operation type")
    watchlist_id: UUID = Field(..., description="Target watchlist ID")
    tickers: List[str] = Field(
        ..., min_items=1, max_items=100, description="Stock tickers"
    )

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v):
        """Validate operation type."""
        if v not in ["add", "remove", "move", "copy"]:
            raise ValueError("Operation must be one of: add, remove, move, copy")
        return v


class BulkOperationResult(BaseModel):
    """Bulk operation result schema."""

    operation: str = Field(..., description="Operation type")
    total_requested: int = Field(..., description="Total items requested")
    successful: int = Field(..., description="Successfully processed items")
    failed: int = Field(..., description="Failed items")
    errors: List[str] = Field(..., description="Error messages")
    warnings: List[str] = Field(..., description="Warning messages")


# Paginated Watchlist Responses
class PaginatedWatchlistsResponse(PaginatedResponse):
    """Paginated watchlists response."""

    items: List[Watchlist]


class PaginatedWatchlistStocksResponse(PaginatedResponse):
    """Paginated watchlist stocks response."""

    items: List[WatchlistStockWithPrice]


class PaginatedWatchlistAlertsResponse(PaginatedResponse):
    """Paginated watchlist alerts response."""

    items: List[WatchlistAlert]


class PaginatedPublicWatchlistsResponse(PaginatedResponse):
    """Paginated public watchlists response."""

    items: List[PublicWatchlistSummary]
