"""AI analysis Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema, PaginatedResponse, TimestampSchema, UUIDSchema


# AI Analysis Request Schemas
class AIAnalysisRequest(BaseModel):
    """AI analysis request schema."""

    ticker: str = Field(..., max_length=10, description="Stock ticker to analyze")
    analysis_type: str = Field(..., description="Type of analysis requested")
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Analysis parameters"
    )
    language: str = Field("ja", description="Response language (ja, en)")

    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, v):
        """Validate analysis type."""
        valid_types = [
            "fundamental",
            "technical",
            "sentiment",
            "risk_assessment",
            "price_prediction",
            "earnings_forecast",
            "peer_comparison",
            "market_outlook",
            "investment_recommendation",
        ]
        if v not in valid_types:
            raise ValueError(f'Analysis type must be one of: {", ".join(valid_types)}')
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """Validate language code."""
        if v not in ["ja", "en"]:
            raise ValueError("Language must be ja or en")
        return v


class BulkAnalysisRequest(BaseModel):
    """Bulk AI analysis request schema."""

    tickers: List[str] = Field(
        ..., min_items=1, max_items=50, description="Stock tickers to analyze"
    )
    analysis_type: str = Field(..., description="Type of analysis requested")
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Analysis parameters"
    )
    language: str = Field("ja", description="Response language (ja, en)")

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
        """Validate ticker list."""
        if len(set(v)) != len(v):
            raise ValueError("Duplicate tickers are not allowed")
        return v

    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, v):
        """Validate analysis type."""
        valid_types = [
            "fundamental",
            "technical",
            "sentiment",
            "risk_assessment",
            "price_prediction",
            "earnings_forecast",
            "peer_comparison",
            "market_outlook",
            "investment_recommendation",
        ]
        if v not in valid_types:
            raise ValueError(f'Analysis type must be one of: {", ".join(valid_types)}')
        return v


# AI Analysis Response Schemas
class AIAnalysisBase(BaseModel):
    """Base AI analysis schema."""

    ticker: str = Field(..., max_length=10, description="Stock ticker")
    analysis_type: str = Field(..., description="Type of analysis")
    status: str = Field(..., description="Analysis status")
    language: str = Field(..., description="Response language")
    user_id: UUID = Field(..., description="User who requested analysis")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate analysis status."""
        if v not in ["pending", "processing", "completed", "failed"]:
            raise ValueError(
                "Status must be one of: pending, processing, completed, failed"
            )
        return v


class AIAnalysisCreate(AIAnalysisBase):
    """AI analysis creation schema."""

    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Analysis parameters"
    )


class AIAnalysis(UUIDSchema, AIAnalysisBase, TimestampSchema):
    """AI analysis response schema."""

    result: Optional[Dict[str, Any]] = Field(None, description="Analysis result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(
        None, description="Processing time in seconds"
    )
    tokens_used: Optional[int] = Field(None, description="AI tokens consumed")
    cost_usd: Optional[float] = Field(None, description="Analysis cost in USD")


# Specific Analysis Result Schemas
class FundamentalAnalysisResult(BaseModel):
    """Fundamental analysis result schema."""

    overall_score: float = Field(
        ..., ge=0, le=100, description="Overall fundamental score"
    )
    financial_health: Dict[str, Any] = Field(
        ..., description="Financial health metrics"
    )
    valuation: Dict[str, Any] = Field(..., description="Valuation analysis")
    growth_prospects: Dict[str, Any] = Field(..., description="Growth analysis")
    competitive_position: Dict[str, Any] = Field(
        ..., description="Competitive analysis"
    )
    risks: List[str] = Field(..., description="Identified risks")
    opportunities: List[str] = Field(..., description="Identified opportunities")
    summary: str = Field(..., description="Analysis summary")
    recommendation: str = Field(..., description="Investment recommendation")
    target_price: Optional[float] = Field(None, description="Target price")
    confidence_level: float = Field(..., ge=0, le=1, description="Analysis confidence")


class TechnicalAnalysisResult(BaseModel):
    """Technical analysis result schema."""

    overall_signal: str = Field(..., description="Overall technical signal")
    trend_analysis: Dict[str, Any] = Field(..., description="Trend analysis")
    support_resistance: Dict[str, Any] = Field(
        ..., description="Support/resistance levels"
    )
    indicators: Dict[str, Any] = Field(..., description="Technical indicators")
    chart_patterns: List[str] = Field(..., description="Identified chart patterns")
    volume_analysis: Dict[str, Any] = Field(..., description="Volume analysis")
    momentum: Dict[str, Any] = Field(..., description="Momentum indicators")
    summary: str = Field(..., description="Technical summary")
    short_term_outlook: str = Field(..., description="Short-term outlook")
    medium_term_outlook: str = Field(..., description="Medium-term outlook")
    key_levels: Dict[str, float] = Field(..., description="Key price levels")

    @field_validator("overall_signal")
    @classmethod
    def validate_signal(cls, v):
        """Validate technical signal."""
        if v not in ["strong_buy", "buy", "hold", "sell", "strong_sell"]:
            raise ValueError(
                "Signal must be one of: strong_buy, buy, hold, sell, strong_sell"
            )
        return v


class SentimentAnalysisResult(BaseModel):
    """Sentiment analysis result schema."""

    overall_sentiment: str = Field(..., description="Overall sentiment")
    sentiment_score: float = Field(
        ..., ge=-1, le=1, description="Sentiment score (-1 to 1)"
    )
    news_sentiment: Dict[str, Any] = Field(..., description="News sentiment analysis")
    social_sentiment: Dict[str, Any] = Field(..., description="Social media sentiment")
    analyst_sentiment: Dict[str, Any] = Field(..., description="Analyst sentiment")
    sentiment_trends: List[Dict[str, Any]] = Field(
        ..., description="Sentiment trends over time"
    )
    key_themes: List[str] = Field(..., description="Key sentiment themes")
    sentiment_drivers: List[str] = Field(..., description="Main sentiment drivers")
    summary: str = Field(..., description="Sentiment summary")

    @field_validator("overall_sentiment")
    @classmethod
    def validate_sentiment(cls, v):
        """Validate sentiment."""
        if v not in [
            "very_positive",
            "positive",
            "neutral",
            "negative",
            "very_negative",
        ]:
            raise ValueError(
                "Sentiment must be one of: very_positive, positive, neutral, negative, very_negative"
            )
        return v


class RiskAssessmentResult(BaseModel):
    """Risk assessment result schema."""

    overall_risk_level: str = Field(..., description="Overall risk level")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")
    financial_risks: List[Dict[str, Any]] = Field(..., description="Financial risks")
    market_risks: List[Dict[str, Any]] = Field(..., description="Market risks")
    operational_risks: List[Dict[str, Any]] = Field(
        ..., description="Operational risks"
    )
    regulatory_risks: List[Dict[str, Any]] = Field(..., description="Regulatory risks")
    volatility_analysis: Dict[str, Any] = Field(..., description="Volatility analysis")
    correlation_analysis: Dict[str, Any] = Field(
        ..., description="Correlation analysis"
    )
    risk_mitigation: List[str] = Field(..., description="Risk mitigation strategies")
    summary: str = Field(..., description="Risk assessment summary")

    @field_validator("overall_risk_level")
    @classmethod
    def validate_risk_level(cls, v):
        """Validate risk level."""
        if v not in ["very_low", "low", "moderate", "high", "very_high"]:
            raise ValueError(
                "Risk level must be one of: very_low, low, moderate, high, very_high"
            )
        return v


class PricePredictionResult(BaseModel):
    """Price prediction result schema."""

    prediction_horizon: str = Field(..., description="Prediction time horizon")
    predicted_price: float = Field(..., description="Predicted price")
    current_price: float = Field(..., description="Current price")
    price_change_percent: float = Field(..., description="Predicted price change %")
    confidence_interval: Dict[str, float] = Field(
        ..., description="Confidence intervals"
    )
    prediction_factors: List[str] = Field(..., description="Key prediction factors")
    model_accuracy: Optional[float] = Field(None, description="Model accuracy score")
    scenarios: Dict[str, Dict[str, float]] = Field(
        ..., description="Different scenarios"
    )
    risks_to_prediction: List[str] = Field(..., description="Risks to prediction")
    summary: str = Field(..., description="Prediction summary")

    @field_validator("prediction_horizon")
    @classmethod
    def validate_horizon(cls, v):
        """Validate prediction horizon."""
        if v not in ["1_week", "1_month", "3_months", "6_months", "1_year"]:
            raise ValueError(
                "Horizon must be one of: 1_week, 1_month, 3_months, 6_months, 1_year"
            )
        return v


# Analysis History Schemas
class AnalysisHistory(BaseModel):
    """Analysis history schema."""

    user_id: UUID = Field(..., description="User ID")
    analyses: List[AIAnalysis] = Field(..., description="User's analysis history")
    total_analyses: int = Field(..., description="Total number of analyses")
    analyses_this_month: int = Field(..., description="Analyses this month")
    favorite_analysis_types: List[str] = Field(
        ..., description="Most used analysis types"
    )
    total_cost_usd: float = Field(..., description="Total cost of analyses")


# Analysis Queue Schemas
class AnalysisQueueStatus(BaseModel):
    """Analysis queue status schema."""

    queue_position: int = Field(..., description="Position in queue")
    estimated_wait_time: int = Field(..., description="Estimated wait time in seconds")
    total_queue_size: int = Field(..., description="Total queue size")
    processing_capacity: int = Field(..., description="Current processing capacity")


# Analysis Comparison Schemas
class AnalysisComparison(BaseModel):
    """Analysis comparison schema."""

    tickers: List[str] = Field(..., description="Compared tickers")
    analysis_type: str = Field(..., description="Analysis type")
    comparison_metrics: Dict[str, Any] = Field(..., description="Comparison metrics")
    rankings: List[Dict[str, Any]] = Field(..., description="Ticker rankings")
    summary: str = Field(..., description="Comparison summary")
    created_at: datetime = Field(..., description="Comparison creation time")


# Analysis Export Schemas
class AnalysisExportRequest(BaseModel):
    """Analysis export request schema."""

    analysis_ids: List[UUID] = Field(
        ..., min_items=1, max_items=100, description="Analysis IDs to export"
    )
    format: str = Field("pdf", description="Export format")
    include_charts: bool = Field(True, description="Include charts in export")
    language: str = Field("ja", description="Export language")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        """Validate export format."""
        if v not in ["pdf", "excel", "csv", "json"]:
            raise ValueError("Format must be one of: pdf, excel, csv, json")
        return v


class AnalysisExportResponse(BaseModel):
    """Analysis export response schema."""

    export_id: UUID = Field(..., description="Export job ID")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    status: str = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Export creation time")
    expires_at: Optional[datetime] = Field(None, description="Download expiration time")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate export status."""
        if v not in ["pending", "processing", "completed", "failed", "expired"]:
            raise ValueError(
                "Status must be one of: pending, processing, completed, failed, expired"
            )
        return v


# Paginated AI Analysis Responses
class PaginatedAIAnalysisResponse(PaginatedResponse):
    """Paginated AI analysis response."""

    items: List[AIAnalysis]


# Analysis Statistics Schemas
class AnalysisStatistics(BaseModel):
    """Analysis statistics schema."""

    total_analyses: int = Field(..., description="Total analyses performed")
    analyses_by_type: Dict[str, int] = Field(..., description="Analyses by type")
    analyses_by_language: Dict[str, int] = Field(
        ..., description="Analyses by language"
    )
    average_processing_time: float = Field(..., description="Average processing time")
    success_rate: float = Field(..., description="Analysis success rate")
    total_cost_usd: float = Field(..., description="Total cost")
    most_analyzed_stocks: List[Dict[str, Any]] = Field(
        ..., description="Most analyzed stocks"
    )
    peak_usage_hours: List[int] = Field(..., description="Peak usage hours")
    user_satisfaction_score: Optional[float] = Field(
        None, description="User satisfaction score"
    )
