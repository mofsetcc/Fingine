"""
AI Analysis API endpoints for stock analysis generation.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import check_api_quota, get_current_user, get_db
from app.models.user import User
from app.schemas.ai_analysis import AIAnalysis
from app.schemas.ai_analysis import AIAnalysisRequest as AIAnalysisRequestSchema
from app.services.ai_analysis_service import AIAnalysisRequest, AIAnalysisService

router = APIRouter()


@router.post("/{ticker}/generate", response_model=dict)
async def generate_analysis(
    ticker: str,
    analysis_type: str,
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_api_quota),
):
    """
    Generate AI-powered stock analysis.

    This endpoint generates comprehensive AI analysis for Japanese stocks using
    Google Gemini API with multi-source data aggregation and intelligent caching.

    **Analysis Types:**
    - **short_term**: 1-4 week momentum analysis based on technical indicators
    - **mid_term**: 1-6 month trend analysis based on fundamentals and earnings
    - **long_term**: 1+ year value analysis based on strategic factors
    - **comprehensive**: Complete analysis covering all time horizons

    **Features:**
    - Multi-source data aggregation (price, financial, news, sentiment)
    - Intelligent caching to optimize costs and response times
    - Japanese language analysis with cultural context
    - Confidence scoring and risk assessment
    - Cost tracking and budget management

    **Parameters:**
    - **ticker**: 4-digit Japanese stock ticker (e.g., "7203" for Toyota)
    - **analysis_type**: Type of analysis to generate
    - **force_refresh**: Force new analysis even if cached version exists

    **Rate Limits:**
    - Free tier: 5 analyses/day
    - Pro tier: 50 analyses/day
    - Business tier: 200 analyses/day

    **Cost:**
    - Short-term: ~$0.005 per analysis
    - Mid-term: ~$0.008 per analysis
    - Long-term: ~$0.012 per analysis
    - Comprehensive: ~$0.020 per analysis
    """
    # Validate ticker format
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    # Validate analysis type
    valid_types = ["short_term", "mid_term", "long_term", "comprehensive"]
    if analysis_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis type must be one of: {', '.join(valid_types)}",
        )

    try:
        # Initialize AI analysis service
        ai_service = AIAnalysisService(db)

        # Create analysis request
        request = AIAnalysisRequest(
            ticker=ticker, analysis_type=analysis_type, force_refresh=force_refresh
        )

        # Generate analysis
        result = await ai_service.generate_analysis(request, str(current_user.id))

        return {
            "ticker": ticker,
            "analysis_type": analysis_type,
            "analysis": result,
            "user_id": str(current_user.id),
            "status": "completed",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analysis: {str(e)}",
        )


@router.get("/{ticker}/short-term", response_model=dict)
async def get_short_term_analysis(
    ticker: str,
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_api_quota),
):
    """
    Generate short-term momentum analysis (1-4 weeks).

    Focuses on technical indicators, recent price action, volume analysis,
    and short-term sentiment to provide trading insights.

    **Data Sources:**
    - Real-time price and volume data
    - Technical indicators (SMA, RSI, MACD, Bollinger Bands)
    - Recent news sentiment
    - Market momentum indicators

    **Use Cases:**
    - Day trading and swing trading decisions
    - Entry/exit timing optimization
    - Short-term risk assessment
    - Technical pattern recognition
    """
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    try:
        ai_service = AIAnalysisService(db)
        result = await ai_service.generate_short_term_analysis(
            ticker, str(current_user.id), force_refresh
        )

        return {
            "ticker": ticker,
            "analysis_type": "short_term",
            "analysis": result,
            "time_horizon": "1-4 weeks",
            "focus": "technical_momentum",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate short-term analysis: {str(e)}",
        )


@router.get("/{ticker}/mid-term", response_model=dict)
async def get_mid_term_analysis(
    ticker: str,
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_api_quota),
):
    """
    Generate mid-term trend analysis (1-6 months).

    Combines fundamental analysis with technical trends to identify
    medium-term investment opportunities based on earnings and growth.

    **Data Sources:**
    - Quarterly financial reports
    - Earnings trends and guidance
    - Industry analysis
    - Peer comparison
    - Macroeconomic factors

    **Use Cases:**
    - Position trading strategies
    - Earnings-based investing
    - Sector rotation decisions
    - Growth stock identification
    """
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    try:
        ai_service = AIAnalysisService(db)
        result = await ai_service.generate_mid_term_analysis(
            ticker, str(current_user.id), force_refresh
        )

        return {
            "ticker": ticker,
            "analysis_type": "mid_term",
            "analysis": result,
            "time_horizon": "1-6 months",
            "focus": "fundamental_trends",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate mid-term analysis: {str(e)}",
        )


@router.get("/{ticker}/long-term", response_model=dict)
async def get_long_term_analysis(
    ticker: str,
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_api_quota),
):
    """
    Generate long-term value analysis (1+ years).

    Deep fundamental analysis focusing on business quality, competitive
    advantages, and long-term value creation potential.

    **Data Sources:**
    - Annual financial reports
    - Business strategy analysis
    - ESG factors
    - Management quality assessment
    - Long-term industry outlook

    **Use Cases:**
    - Buy-and-hold investing
    - Value investing strategies
    - Portfolio core positions
    - Retirement planning
    """
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    try:
        ai_service = AIAnalysisService(db)
        result = await ai_service.generate_long_term_analysis(
            ticker, str(current_user.id), force_refresh
        )

        return {
            "ticker": ticker,
            "analysis_type": "long_term",
            "analysis": result,
            "time_horizon": "1+ years",
            "focus": "value_creation",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate long-term analysis: {str(e)}",
        )


@router.get("/{ticker}/comprehensive", response_model=dict)
async def get_comprehensive_analysis(
    ticker: str,
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_api_quota),
):
    """
    Generate comprehensive analysis covering all time horizons.

    Complete investment analysis combining technical, fundamental, and
    strategic factors across short, medium, and long-term perspectives.

    **Data Sources:**
    - All available data sources
    - Multi-timeframe analysis
    - Cross-validation of signals
    - Integrated risk assessment

    **Use Cases:**
    - Complete investment research
    - Due diligence reports
    - Investment committee presentations
    - Comprehensive stock evaluation
    """
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    try:
        ai_service = AIAnalysisService(db)
        result = await ai_service.generate_comprehensive_analysis(
            ticker, str(current_user.id), force_refresh
        )

        return {
            "ticker": ticker,
            "analysis_type": "comprehensive",
            "analysis": result,
            "time_horizon": "all_horizons",
            "focus": "complete_analysis",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate comprehensive analysis: {str(e)}",
        )


@router.get("/{ticker}/history", response_model=dict)
async def get_analysis_history(
    ticker: str,
    analysis_type: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analysis history for a stock.

    Returns previous analyses for the specified stock, useful for
    tracking analysis evolution and performance over time.

    **Parameters:**
    - **ticker**: Stock ticker to get history for
    - **analysis_type**: Filter by analysis type (optional)
    - **limit**: Maximum number of analyses to return (1-50)

    **Use Cases:**
    - Track analysis accuracy over time
    - Compare different analysis types
    - Monitor recommendation changes
    - Performance evaluation
    """
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 50",
        )

    try:
        from app.models.analysis import AIAnalysisCache

        query = db.query(AIAnalysisCache).filter(AIAnalysisCache.ticker == ticker)

        if analysis_type:
            query = query.filter(AIAnalysisCache.analysis_type == analysis_type)

        analyses = query.order_by(AIAnalysisCache.created_at.desc()).limit(limit).all()

        history = []
        for analysis in analyses:
            history.append(
                {
                    "analysis_date": analysis.analysis_date.isoformat(),
                    "analysis_type": analysis.analysis_type,
                    "model_version": analysis.model_version,
                    "confidence_score": float(analysis.confidence_score)
                    if analysis.confidence_score
                    else None,
                    "processing_time_ms": analysis.processing_time_ms,
                    "cost_usd": float(analysis.cost_usd) if analysis.cost_usd else None,
                    "created_at": analysis.created_at.isoformat(),
                    "result_summary": analysis.analysis_result.get("rating")
                    if analysis.analysis_result
                    else None,
                }
            )

        return {
            "ticker": ticker,
            "analysis_history": history,
            "total_analyses": len(history),
            "analysis_type_filter": analysis_type,
            "user_id": str(current_user.id),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis history: {str(e)}",
        )
