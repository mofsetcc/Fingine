"""Stock-related Pydantic schemas."""

from datetime import date as Date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import BaseModel, Field, validator

from app.schemas.base import BaseSchema, TimestampSchema


# Stock Base Schemas
class StockBase(BaseModel):
    """Base stock schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker symbol")
    company_name_jp: str = Field(..., max_length=255, description="Japanese company name")
    company_name_en: Optional[str] = Field(None, max_length=255, description="English company name")
    sector_jp: Optional[str] = Field(None, max_length=100, description="Japanese sector name")
    industry_jp: Optional[str] = Field(None, max_length=100, description="Japanese industry name")
    description: Optional[str] = Field(None, description="Company description")
    logo_url: Optional[str] = Field(None, max_length=255, description="Company logo URL")
    listing_date: Optional[Date] = Field(None, description="Stock listing date")
    is_active: bool = Field(True, description="Whether stock is actively traded")
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validate ticker format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError('Japanese stock ticker must be 4 digits')
        return v


class StockCreate(StockBase):
    """Stock creation schema."""
    pass


class StockUpdate(BaseModel):
    """Stock update schema."""
    
    company_name_jp: Optional[str] = Field(None, max_length=255, description="Japanese company name")
    company_name_en: Optional[str] = Field(None, max_length=255, description="English company name")
    sector_jp: Optional[str] = Field(None, max_length=100, description="Japanese sector name")
    industry_jp: Optional[str] = Field(None, max_length=100, description="Japanese industry name")
    description: Optional[str] = Field(None, description="Company description")
    logo_url: Optional[str] = Field(None, max_length=255, description="Company logo URL")
    listing_date: Optional[Date] = Field(None, description="Stock listing date")
    is_active: Optional[bool] = Field(None, description="Whether stock is actively traded")


class Stock(StockBase, TimestampSchema):
    """Stock response schema."""
    
    class Config:
        from_attributes = True


# Stock Price Schemas
class PriceDataBase(BaseModel):
    """Base price data schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    date: Date = Field(..., description="Price date")
    open_price: Decimal = Field(..., description="Opening price")
    high_price: Decimal = Field(..., description="Highest price")
    low_price: Decimal = Field(..., description="Lowest price")
    close_price: Decimal = Field(..., description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    adjusted_close: Optional[Decimal] = Field(None, description="Adjusted closing price")
    
    @validator('open_price', 'high_price', 'low_price', 'close_price', 'adjusted_close')
    def validate_prices(cls, v):
        """Validate price values."""
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        return v


class PriceDataCreate(PriceDataBase):
    """Price data creation schema."""
    pass


class PriceData(PriceDataBase):
    """Price data response schema."""
    
    class Config:
        from_attributes = True
    
    @property
    def change(self) -> Decimal:
        """Price change from open to close."""
        return self.close_price - self.open_price
    
    @property
    def change_percent(self) -> float:
        """Percentage change from open to close."""
        if self.open_price == 0:
            return 0.0
        return float((self.close_price - self.open_price) / self.open_price * 100)


# Stock Search Schemas
class StockSearchQuery(BaseModel):
    """Stock search query schema."""
    
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    include_inactive: bool = Field(False, description="Include inactive stocks")


class StockSearchResult(BaseModel):
    """Stock search result schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    company_name_jp: str = Field(..., description="Japanese company name")
    company_name_en: Optional[str] = Field(None, description="English company name")
    sector_jp: Optional[str] = Field(None, description="Sector")
    current_price: Optional[Decimal] = Field(None, description="Current stock price")
    change_percent: Optional[float] = Field(None, description="Daily change percentage")
    volume: Optional[int] = Field(None, description="Trading volume")
    match_score: float = Field(..., ge=0, le=1, description="Search relevance score")


class StockSearchResponse(BaseModel):
    """Stock search response schema."""
    
    results: List[StockSearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total matching stocks")
    query: str = Field(..., description="Original search query")
    execution_time_ms: int = Field(..., description="Search execution time")


# Price History Schemas
class PriceHistoryRequest(BaseModel):
    """Price history request schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    start_date: Optional[Date] = Field(None, description="Start date")
    end_date: Optional[Date] = Field(None, description="End date")
    period: str = Field("1y", description="Time period (1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y)")
    interval: str = Field("1d", description="Data interval (1m, 5m, 15m, 30m, 1h, 1d)")
    
    @validator('period')
    def validate_period(cls, v):
        """Validate period format."""
        valid_periods = ['1d', '1w', '1m', '3m', '6m', '1y', '2y', '5y', 'max']
        if v not in valid_periods:
            raise ValueError(f'Period must be one of: {", ".join(valid_periods)}')
        return v
    
    @validator('interval')
    def validate_interval(cls, v):
        """Validate interval format."""
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '1d', '1w', '1mo']
        if v not in valid_intervals:
            raise ValueError(f'Interval must be one of: {", ".join(valid_intervals)}')
        return v


class PriceHistoryResponse(BaseModel):
    """Price history response schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    data: List[PriceData] = Field(..., description="Price data points")
    period: str = Field(..., description="Requested period")
    interval: str = Field(..., description="Data interval")
    total_points: int = Field(..., description="Total data points")
    start_date: Date = Field(..., description="Actual start date")
    end_date: Date = Field(..., description="Actual end date")


# Stock Detail Schema
class StockDetail(Stock):
    """Detailed stock information schema."""
    
    current_price: Optional[Decimal] = Field(None, description="Current stock price")
    change: Optional[Decimal] = Field(None, description="Daily price change")
    change_percent: Optional[float] = Field(None, description="Daily change percentage")
    volume: Optional[int] = Field(None, description="Current trading volume")
    market_cap: Optional[int] = Field(None, description="Market capitalization")
    pe_ratio: Optional[Decimal] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[Decimal] = Field(None, description="Price-to-book ratio")
    dividend_yield: Optional[Decimal] = Field(None, description="Dividend yield")
    week_52_high: Optional[Decimal] = Field(None, description="52-week high")
    week_52_low: Optional[Decimal] = Field(None, description="52-week low")
    avg_volume: Optional[int] = Field(None, description="Average trading volume")


# Stock List Schema
class StockList(BaseModel):
    """Stock list response schema."""
    
    stocks: List[Stock] = Field(..., description="List of stocks")
    total: int = Field(..., description="Total number of stocks")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")
    filters: Dict[str, Any] = Field(..., description="Applied filters")


# Stock Daily Metrics Schemas
class StockDailyMetricsBase(BaseModel):
    """Base daily metrics schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    date: Date = Field(..., description="Metrics date")
    market_cap: Optional[int] = Field(None, ge=0, description="Market capitalization")
    pe_ratio: Optional[Decimal] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[Decimal] = Field(None, description="Price-to-book ratio")
    dividend_yield: Optional[Decimal] = Field(None, ge=0, le=1, description="Dividend yield")
    shares_outstanding: Optional[int] = Field(None, ge=0, description="Shares outstanding")


class StockDailyMetricsCreate(StockDailyMetricsBase):
    """Daily metrics creation schema."""
    pass


class StockDailyMetrics(StockDailyMetricsBase):
    """Daily metrics response schema."""
    
    class Config:
        from_attributes = True


# Market Index Schemas
class MarketIndex(BaseModel):
    """Market index schema."""
    
    name: str = Field(..., description="Index name")
    symbol: str = Field(..., description="Index symbol")
    value: Decimal = Field(..., description="Current index value")
    change: Decimal = Field(..., description="Change from previous close")
    change_percent: float = Field(..., description="Percentage change")
    volume: Optional[int] = Field(None, description="Trading volume")
    updated_at: datetime = Field(..., description="Last update time")


# Hot Stocks Schemas
class HotStock(BaseModel):
    """Hot stock schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    company_name: str = Field(..., description="Company name")
    current_price: Decimal = Field(..., description="Current price")
    change: Decimal = Field(..., description="Price change")
    change_percent: float = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    category: str = Field(..., description="Category (gainer/loser/most_traded)")
    
    @validator('category')
    def validate_category(cls, v):
        """Validate hot stock category."""
        if v not in ['gainer', 'loser', 'most_traded']:
            raise ValueError('Category must be gainer, loser, or most_traded')
        return v


class HotStocksResponse(BaseModel):
    """Hot stocks response schema."""
    
    gainers: List[HotStock] = Field(..., description="Top gaining stocks")
    losers: List[HotStock] = Field(..., description="Top losing stocks")
    most_traded: List[HotStock] = Field(..., description="Most traded stocks")
    updated_at: datetime = Field(..., description="Last update time")


# Price History Query Schema (alias for compatibility)
PriceHistoryQuery = PriceHistoryRequest


# Technical Indicators Schema
class TechnicalIndicators(BaseModel):
    """Technical indicators schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    rsi: Optional[Decimal] = Field(None, description="Relative Strength Index")
    macd: Optional[Decimal] = Field(None, description="MACD")
    moving_avg_20: Optional[Decimal] = Field(None, description="20-day moving average")
    moving_avg_50: Optional[Decimal] = Field(None, description="50-day moving average")
    moving_avg_200: Optional[Decimal] = Field(None, description="200-day moving average")
    bollinger_upper: Optional[Decimal] = Field(None, description="Bollinger upper band")
    bollinger_lower: Optional[Decimal] = Field(None, description="Bollinger lower band")
    volume_avg: Optional[int] = Field(None, description="Average volume")
    updated_at: datetime = Field(..., description="Last update time")


# Paginated Response Schemas
class PaginatedStocksResponse(BaseModel):
    """Paginated stocks response schema."""
    
    items: List[Stock] = Field(..., description="Stock items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class PaginatedPriceDataResponse(BaseModel):
    """Paginated price data response schema."""
    
    items: List[PriceData] = Field(..., description="Price data items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


# Batch Price Schemas
class BatchPriceRequest(BaseModel):
    """Batch price request schema."""
    
    tickers: List[str] = Field(..., min_items=1, max_items=50, description="Stock tickers")
    
    @validator('tickers')
    def validate_tickers(cls, v):
        """Validate ticker list."""
        for ticker in v:
            if not ticker.isdigit() or len(ticker) != 4:
                raise ValueError(f'Invalid ticker format: {ticker}. Japanese stock ticker must be 4 digits')
        return v


class BatchPriceData(BaseModel):
    """Batch price data schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    current_price: Optional[Decimal] = Field(None, description="Current price")
    price_change: Optional[Decimal] = Field(None, description="Price change from previous close")
    price_change_percent: Optional[float] = Field(None, description="Price change percentage")
    volume_today: Optional[int] = Field(None, description="Today's trading volume")
    last_updated: Optional[Date] = Field(None, description="Last price update date")
    error: Optional[str] = Field(None, description="Error message if price unavailable")


class BatchPriceResponse(BaseModel):
    """Batch price response schema."""
    
    prices: Dict[str, BatchPriceData] = Field(..., description="Price data by ticker")
    requested_count: int = Field(..., description="Number of tickers requested")
    successful_count: int = Field(..., description="Number of successful price retrievals")
    failed_count: int = Field(..., description="Number of failed price retrievals")
    updated_at: datetime = Field(..., description="Response generation time")