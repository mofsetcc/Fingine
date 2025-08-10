"""
Stock API endpoints for search, discovery, and market data.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import check_api_quota, get_current_user_optional, get_db
from app.models.user import User
from app.schemas.stock import (
    BatchPriceRequest,
    BatchPriceResponse,
    HotStocksResponse,
    MarketIndex,
    PriceHistoryRequest,
    PriceHistoryResponse,
    StockDetail,
    StockSearchQuery,
    StockSearchResponse,
)
from app.services.stock_service import StockService

router = APIRouter()


@router.get("/search", response_model=StockSearchResponse)
async def search_stocks(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    include_inactive: bool = Query(False, description="Include inactive stocks"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Search stocks by ticker symbol or company name with fuzzy matching.

    This endpoint provides fast fuzzy search capabilities for Japanese stocks
    with relevance scoring and sub-500ms response times.

    **Search Features:**
    - Exact ticker match (highest priority)
    - Ticker prefix matching
    - Company name matching (Japanese and English)
    - Sector and industry matching
    - Relevance scoring from 0.0 to 1.0

    **Performance:**
    - Optimized for sub-500ms response times
    - Database indexes on searchable fields
    - Efficient query execution with relevance scoring

    **Rate Limits:**
    - Authenticated users: 100 requests/minute
    - Anonymous users: 20 requests/minute
    """
    stock_service = StockService(db)

    search_query = StockSearchQuery(
        query=query, limit=limit, include_inactive=include_inactive
    )

    return await stock_service.search_stocks(search_query)


@router.get("/market/indices", response_model=List[MarketIndex])
async def get_market_indices(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get current market indices data (Nikkei 225, TOPIX).

    Returns real-time or near real-time market index values with
    change information from the previous trading session.

    **Supported Indices:**
    - Nikkei 225 (N225)
    - TOPIX (Tokyo Stock Price Index)

    **Data Freshness:**
    - Real-time for premium users
    - 15-minute delay for free users
    - Updated during market hours (9:00-15:00 JST)
    """
    stock_service = StockService(db)
    return await stock_service.get_market_indices()


@router.get("/market/hot-stocks", response_model=HotStocksResponse)
async def get_hot_stocks(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get hot stocks data (gainers, losers, most traded).

    Returns the top performing stocks categorized by:
    - **Gainers**: Stocks with highest percentage gains
    - **Losers**: Stocks with highest percentage losses
    - **Most Traded**: Stocks with highest trading volume

    **Features:**
    - Top 10 stocks in each category
    - Real-time price changes and volume data
    - Percentage change calculations
    - Updated every 5 minutes during market hours

    **Data Quality:**
    - Filters out penny stocks and inactive stocks
    - Minimum volume thresholds applied
    - Accurate percentage calculations with proper handling of splits
    """
    stock_service = StockService(db)
    return await stock_service.get_hot_stocks()


@router.get("/{ticker}", response_model=StockDetail)
async def get_stock_detail(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get detailed information for a specific stock.

    Returns comprehensive stock information including:
    - Basic company information
    - Current price and daily change
    - Key financial metrics (P/E, P/B, dividend yield)
    - 52-week high/low prices
    - Average trading volume
    - Market capitalization

    **Parameters:**
    - **ticker**: 4-digit Japanese stock ticker (e.g., "7203" for Toyota)

    **Error Responses:**
    - 404: Stock not found
    - 400: Invalid ticker format
    """
    # Validate ticker format
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    stock_service = StockService(db)
    return await stock_service.get_stock_detail(ticker)


@router.get("/{ticker}/price-history", response_model=PriceHistoryResponse)
async def get_price_history(
    ticker: str,
    period: str = Query(
        "1y", description="Time period (1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y)"
    ),
    interval: str = Query("1d", description="Data interval (1m, 5m, 15m, 30m, 1h, 1d)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get historical price data (OHLCV) for a stock.

    Returns historical Open, High, Low, Close, Volume (OHLCV) data
    for technical analysis and charting.

    **Parameters:**
    - **ticker**: 4-digit Japanese stock ticker
    - **period**: Predefined time periods (1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y)
    - **interval**: Data granularity (1m, 5m, 15m, 30m, 1h, 1d)
    - **start_date**: Custom start date (overrides period)
    - **end_date**: Custom end date (defaults to today)

    **Data Quality:**
    - Adjusted for stock splits and dividends
    - Missing data points handled gracefully
    - Volume data included for liquidity analysis

    **Rate Limits:**
    - Free tier: 10 requests/day
    - Pro tier: 100 requests/day
    - Business tier: 1000 requests/day
    """
    # Validate ticker format
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    # Parse dates if provided
    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            from datetime import datetime

            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD",
            )

    if end_date:
        try:
            from datetime import datetime

            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD",
            )

    stock_service = StockService(db)

    request = PriceHistoryRequest(
        ticker=ticker,
        period=period,
        interval=interval,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return await stock_service.get_price_history(request)


@router.get("/{ticker}/metrics", response_model=dict)
async def get_stock_metrics(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_api_quota),
):
    """
    Get detailed financial metrics for a stock.

    Returns comprehensive financial metrics including:
    - Valuation ratios (P/E, P/B, P/S, EV/EBITDA)
    - Profitability metrics (ROE, ROA, profit margins)
    - Financial health indicators (debt ratios, current ratio)
    - Growth metrics (revenue growth, earnings growth)

    **Authentication Required**: This endpoint requires authentication
    and counts against your daily API quota.

    **Parameters:**
    - **ticker**: 4-digit Japanese stock ticker

    **Quota Usage:**
    - Free tier: 1 request per call
    - Pro tier: 1 request per call
    - Business tier: 1 request per call
    """
    # Validate ticker format
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    # TODO: Implement detailed metrics calculation
    # This would integrate with financial data from EDINET
    return {
        "ticker": ticker,
        "message": "Detailed metrics endpoint - to be implemented",
        "note": "This endpoint will provide comprehensive financial metrics",
    }


@router.get("/{ticker}/news", response_model=dict)
async def get_stock_news(
    ticker: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum news articles"),
    days: int = Query(7, ge=1, le=30, description="Days of news history"),
    min_relevance: float = Query(
        0.1, ge=0.0, le=1.0, description="Minimum relevance score"
    ),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get news articles related to a specific stock with enhanced relevance filtering.

    Returns recent news articles with sentiment analysis and relevance scoring for the specified stock.
    Uses advanced stock-news mapping to ensure high-quality, relevant results.

    **Features:**
    - Japanese and English news sources
    - Sentiment analysis (positive/negative/neutral)
    - Relevance scoring based on ticker and company name mentions
    - Source attribution and credibility scoring
    - Automatic stock-news relationship detection

    **Parameters:**
    - **ticker**: 4-digit Japanese stock ticker
    - **limit**: Maximum number of articles (1-100)
    - **days**: Days of history to search (1-30)
    - **min_relevance**: Minimum relevance score (0.0-1.0)

    **Data Sources:**
    - Nikkei Shimbun
    - Reuters Japan
    - Yahoo Finance Japan
    - Company press releases
    """
    # Validate ticker format
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    try:
        import logging
        from datetime import datetime, timedelta

        from ...services.news_service import news_service
        from ...services.sentiment_service import sentiment_service

        logger = logging.getLogger(__name__)

        # Get news articles for the stock using enhanced mapping service
        start_date = datetime.utcnow() - timedelta(days=days)
        articles = await news_service.get_news_for_stock(
            ticker=ticker,
            limit=limit,
            min_relevance=min_relevance,
            start_date=start_date,
        )

        # Get sentiment summary
        sentiment_summary = await sentiment_service.get_sentiment_summary(
            ticker=ticker, hours_back=days * 24
        )

        return {
            "ticker": ticker,
            "articles": articles,
            "sentiment_summary": sentiment_summary,
            "total_articles": len(articles),
            "days_analyzed": days,
            "min_relevance_used": min_relevance,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error getting news for stock {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stock news",
        )


@router.get("/{ticker}/news/stocks-mentioned", response_model=dict)
async def get_stocks_mentioned_in_news(
    ticker: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum articles to analyze"),
    min_relevance: float = Query(
        0.2, ge=0.0, le=1.0, description="Minimum relevance score"
    ),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get other stocks frequently mentioned alongside the specified stock in news articles.

    This endpoint analyzes news articles related to the specified stock and identifies
    other stocks that are commonly mentioned together, useful for finding related companies
    or sector trends.

    **Use Cases:**
    - Identify competitor stocks
    - Find sector-related companies
    - Discover supply chain relationships
    - Track market correlation patterns

    **Parameters:**
    - **ticker**: 4-digit Japanese stock ticker
    - **limit**: Maximum articles to analyze (1-50)
    - **min_relevance**: Minimum relevance score for stock mentions
    """
    # Validate ticker format
    if not ticker.isdigit() or len(ticker) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Japanese stock ticker must be 4 digits",
        )

    try:
        import logging
        from collections import defaultdict
        from datetime import datetime, timedelta

        from ...services.news_service import news_service
        from ...services.news_stock_mapping_service import news_stock_mapping_service

        logger = logging.getLogger(__name__)

        # Get recent news articles for the stock
        start_date = datetime.utcnow() - timedelta(days=30)
        articles = await news_service.get_news_for_stock(
            ticker=ticker,
            limit=limit,
            min_relevance=0.1,  # Lower threshold to get more articles
            start_date=start_date,
        )

        # Analyze each article for other stock mentions
        related_stocks = defaultdict(list)

        for article in articles:
            article_id = article["id"]
            stocks_mentioned = (
                await news_stock_mapping_service.get_stocks_mentioned_in_article(
                    article_id=article_id, min_relevance=min_relevance
                )
            )

            # Filter out the original ticker
            other_stocks = [s for s in stocks_mentioned if s["ticker"] != ticker]

            for stock in other_stocks:
                related_stocks[stock["ticker"]].append(
                    {
                        "article_id": article_id,
                        "article_headline": article["headline"],
                        "relevance_score": stock["relevance_score"],
                        "published_at": article["published_at"],
                    }
                )

        # Calculate co-occurrence statistics
        stock_stats = []
        for related_ticker, mentions in related_stocks.items():
            if mentions:  # Only include stocks with mentions
                stock_info = mentions[0]  # Get stock info from first mention
                avg_relevance = sum(m["relevance_score"] for m in mentions) / len(
                    mentions
                )

                # Get stock details
                stocks_mentioned = (
                    await news_stock_mapping_service.get_stocks_mentioned_in_article(
                        mentions[0]["article_id"], min_relevance=0.0
                    )
                )
                stock_detail = next(
                    (s for s in stocks_mentioned if s["ticker"] == related_ticker), None
                )

                if stock_detail:
                    stock_stats.append(
                        {
                            "ticker": related_ticker,
                            "company_name_jp": stock_detail["company_name_jp"],
                            "company_name_en": stock_detail["company_name_en"],
                            "sector_jp": stock_detail["sector_jp"],
                            "mention_count": len(mentions),
                            "avg_relevance_score": round(avg_relevance, 3),
                            "recent_mentions": mentions[:3],  # Show 3 most recent
                        }
                    )

        # Sort by mention count and relevance
        stock_stats.sort(
            key=lambda x: (x["mention_count"], x["avg_relevance_score"]), reverse=True
        )

        return {
            "ticker": ticker,
            "related_stocks": stock_stats[:20],  # Top 20 related stocks
            "articles_analyzed": len(articles),
            "total_related_stocks": len(stock_stats),
            "min_relevance_used": min_relevance,
            "analysis_period_days": 30,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error analyzing related stocks for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze related stocks",
        )


@router.get("/news/mapping-statistics", response_model=dict)
async def get_news_mapping_statistics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get statistics about news-stock mapping performance and coverage.

    This endpoint provides insights into the effectiveness of the automatic
    news-stock relationship mapping system, including coverage rates,
    relevance scores, and top stocks by news volume.

    **Metrics Provided:**
    - Total articles and linking rates
    - Average relevance scores
    - Top stocks by news coverage
    - Mapping system performance
    - Cache statistics

    **Use Cases:**
    - System monitoring and optimization
    - Content quality assessment
    - Market coverage analysis
    - Performance tuning
    """
    try:
        import logging

        from ...services.news_stock_mapping_service import news_stock_mapping_service

        logger = logging.getLogger(__name__)

        # Get comprehensive mapping statistics
        stats = await news_stock_mapping_service.get_mapping_statistics()

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mapping statistics temporarily unavailable",
            )

        return {
            "mapping_statistics": stats,
            "system_status": "operational",
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error getting mapping statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve mapping statistics",
        )


@router.post("/news/process-mapping", response_model=dict)
async def process_news_mapping(
    force_refresh: bool = Query(False, description="Force refresh existing mappings"),
    batch_size: int = Query(
        100, ge=10, le=500, description="Batch size for processing"
    ),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Trigger processing of existing news articles for stock mapping.

    This endpoint allows manual triggering of the news-stock mapping process
    for existing articles that may not have been processed yet, or to refresh
    existing mappings with updated algorithms.

    **Parameters:**
    - **force_refresh**: Reprocess all articles, even those with existing mappings
    - **batch_size**: Number of articles to process per batch (10-500)

    **Use Cases:**
    - Initial system setup
    - Algorithm improvements deployment
    - Data quality improvements
    - System maintenance

    **Note:** This is a potentially long-running operation for large datasets.
    """
    try:
        import logging

        from ...services.news_service import news_service

        logger = logging.getLogger(__name__)

        # Trigger batch processing
        stats = await news_service.process_existing_articles_for_mapping(
            batch_size=batch_size, force_refresh=force_refresh
        )

        return {
            "processing_stats": stats,
            "batch_size_used": batch_size,
            "force_refresh": force_refresh,
            "status": "completed",
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error processing news mapping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process news mapping",
        )


@router.post("/prices/batch", response_model=BatchPriceResponse)
async def get_batch_prices(
    request: BatchPriceRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get current prices for multiple stocks in a single request.

    This endpoint is optimized for real-time watchlist updates and portfolio
    tracking by allowing batch retrieval of current price data.

    **Features:**
    - Batch processing for up to 50 stocks
    - Current price, change, and volume data
    - Optimized for real-time updates
    - Efficient database queries

    **Parameters:**
    - **tickers**: List of 4-digit Japanese stock tickers (max 50)

    **Rate Limits:**
    - Free tier: 10 requests/minute
    - Pro tier: 60 requests/minute
    - Business tier: 300 requests/minute
    """
    if len(request.tickers) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 tickers allowed per batch request",
        )

    # Validate ticker formats
    for ticker in request.tickers:
        if not ticker.isdigit() or len(ticker) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ticker format: {ticker}. Japanese stock ticker must be 4 digits",
            )

    stock_service = StockService(db)
    return await stock_service.get_batch_prices(request.tickers)
