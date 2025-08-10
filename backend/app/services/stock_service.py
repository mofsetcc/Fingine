"""
Stock service for handling stock data operations.
"""

import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, desc, func, or_, text
from sqlalchemy.orm import Session

from app.models.stock import Stock, StockDailyMetrics, StockPriceHistory
from app.schemas.stock import (
    BatchPriceData,
    BatchPriceResponse,
    HotStock,
    HotStocksResponse,
    MarketIndex,
    PriceData,
    PriceHistoryRequest,
    PriceHistoryResponse,
    StockDetail,
    StockSearchQuery,
    StockSearchResponse,
    StockSearchResult,
)


class StockService:
    """Service for stock-related operations."""

    def __init__(self, db: Session):
        self.db = db

    async def search_stocks(self, query: StockSearchQuery) -> StockSearchResponse:
        """
        Search stocks by ticker symbol or company name with fuzzy matching.

        Args:
            query: Search query parameters

        Returns:
            Search results with relevance scoring
        """
        start_time = time.time()

        # Build the search query
        search_term = query.query.strip()

        # Create base query
        base_query = self.db.query(Stock)

        if not query.include_inactive:
            base_query = base_query.filter(Stock.is_active == True)

        # Search conditions with relevance scoring
        search_conditions = []

        # Exact ticker match (highest priority)
        if search_term.isdigit() and len(search_term) <= 4:
            search_conditions.append((Stock.ticker == search_term.zfill(4), 1.0))

        # Ticker prefix match
        if search_term.isdigit():
            search_conditions.append((Stock.ticker.like(f"{search_term}%"), 0.9))

        # Company name matches (Japanese)
        search_conditions.extend(
            [
                (Stock.company_name_jp.ilike(f"{search_term}%"), 0.8),
                (Stock.company_name_jp.ilike(f"%{search_term}%"), 0.6),
            ]
        )

        # Company name matches (English)
        if query.query.encode("ascii", "ignore").decode("ascii"):
            search_conditions.extend(
                [
                    (Stock.company_name_en.ilike(f"{search_term}%"), 0.7),
                    (Stock.company_name_en.ilike(f"%{search_term}%"), 0.5),
                ]
            )

        # Sector/Industry matches
        search_conditions.extend(
            [
                (Stock.sector_jp.ilike(f"%{search_term}%"), 0.4),
                (Stock.industry_jp.ilike(f"%{search_term}%"), 0.3),
            ]
        )

        # Build CASE statement for relevance scoring
        relevance_cases = []
        combined_conditions = []

        for condition, score in search_conditions:
            relevance_cases.append(f"WHEN {condition} THEN {score}")
            combined_conditions.append(condition)

        if not combined_conditions:
            return StockSearchResponse(
                results=[],
                total=0,
                query=query.query,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        # Create relevance score expression
        relevance_expr = text(
            f"""
            CASE 
                {' '.join(relevance_cases)}
                ELSE 0.0 
            END
        """
        )

        # Execute search query with relevance scoring
        search_query = (
            self.db.query(Stock, relevance_expr.label("match_score"))
            .filter(or_(*combined_conditions))
            .order_by(desc("match_score"), Stock.ticker)
            .limit(query.limit)
        )

        results = search_query.all()

        # Get current price data for results
        tickers = [result.Stock.ticker for result in results]
        price_data = self._get_latest_prices(tickers)

        # Build search results
        search_results = []
        for result in results:
            stock = result.Stock
            price_info = price_data.get(stock.ticker, {})

            search_results.append(
                StockSearchResult(
                    ticker=stock.ticker,
                    company_name_jp=stock.company_name_jp,
                    company_name_en=stock.company_name_en,
                    sector_jp=stock.sector_jp,
                    current_price=price_info.get("current_price"),
                    change_percent=price_info.get("change_percent"),
                    volume=price_info.get("volume"),
                    match_score=float(result.match_score),
                )
            )

        # Get total count for pagination
        total_query = self.db.query(func.count(Stock.ticker)).filter(
            or_(*combined_conditions)
        )

        if not query.include_inactive:
            total_query = total_query.filter(Stock.is_active == True)

        total = total_query.scalar() or 0

        execution_time = int((time.time() - start_time) * 1000)

        return StockSearchResponse(
            results=search_results,
            total=total,
            query=query.query,
            execution_time_ms=execution_time,
        )

    async def get_market_indices(self) -> List[MarketIndex]:
        """
        Get current market indices data (Nikkei 225, TOPIX).

        Returns:
            List of market indices with current values
        """
        # For now, return mock data since we don't have real-time index data
        # In production, this would fetch from a real data source
        indices = [
            MarketIndex(
                name="日経平均株価",
                symbol="N225",
                value=Decimal("33000.00"),
                change=Decimal("150.25"),
                change_percent=0.46,
                volume=1500000000,
                updated_at=datetime.now(),
            ),
            MarketIndex(
                name="TOPIX",
                symbol="TOPIX",
                value=Decimal("2400.50"),
                change=Decimal("-12.30"),
                change_percent=-0.51,
                volume=2100000000,
                updated_at=datetime.now(),
            ),
        ]

        return indices

    async def get_hot_stocks(self) -> HotStocksResponse:
        """
        Get hot stocks data (gainers, losers, most traded).

        Returns:
            Hot stocks categorized by performance
        """
        # Get latest trading date
        latest_date = self.db.query(func.max(StockPriceHistory.date)).scalar()

        if not latest_date:
            # Return empty response if no price data
            return HotStocksResponse(
                gainers=[], losers=[], most_traded=[], updated_at=datetime.now()
            )

        # Get previous trading date for comparison
        previous_date = (
            self.db.query(func.max(StockPriceHistory.date))
            .filter(StockPriceHistory.date < latest_date)
            .scalar()
        )

        if not previous_date:
            previous_date = latest_date - timedelta(days=1)

        # Query for price changes
        price_change_query = text(
            """
            SELECT 
                s.ticker,
                s.company_name_jp,
                current.close as current_price,
                (current.close - previous.close) as change,
                ((current.close - previous.close) / previous.close * 100) as change_percent,
                current.volume
            FROM stocks s
            JOIN stock_price_history current ON s.ticker = current.ticker AND current.date = :latest_date
            LEFT JOIN stock_price_history previous ON s.ticker = previous.ticker AND previous.date = :previous_date
            WHERE s.is_active = true
            AND previous.close IS NOT NULL
            AND current.close > 0
            AND previous.close > 0
        """
        )

        results = self.db.execute(
            price_change_query,
            {"latest_date": latest_date, "previous_date": previous_date},
        ).fetchall()

        # Convert to list of dictionaries
        stock_data = [
            {
                "ticker": row.ticker,
                "company_name": row.company_name_jp,
                "current_price": Decimal(str(row.current_price)),
                "change": Decimal(str(row.change)),
                "change_percent": float(row.change_percent),
                "volume": int(row.volume),
            }
            for row in results
        ]

        # Sort and get top performers
        gainers = sorted(
            [stock for stock in stock_data if stock["change_percent"] > 0],
            key=lambda x: x["change_percent"],
            reverse=True,
        )[:10]

        losers = sorted(
            [stock for stock in stock_data if stock["change_percent"] < 0],
            key=lambda x: x["change_percent"],
        )[:10]

        most_traded = sorted(stock_data, key=lambda x: x["volume"], reverse=True)[:10]

        # Convert to HotStock objects
        def to_hot_stock(stock_dict: dict, category: str) -> HotStock:
            return HotStock(
                ticker=stock_dict["ticker"],
                company_name=stock_dict["company_name"],
                current_price=stock_dict["current_price"],
                change=stock_dict["change"],
                change_percent=stock_dict["change_percent"],
                volume=stock_dict["volume"],
                category=category,
            )

        return HotStocksResponse(
            gainers=[to_hot_stock(stock, "gainer") for stock in gainers],
            losers=[to_hot_stock(stock, "loser") for stock in losers],
            most_traded=[to_hot_stock(stock, "most_traded") for stock in most_traded],
            updated_at=datetime.now(),
        )

    async def get_stock_detail(self, ticker: str) -> StockDetail:
        """
        Get detailed stock information.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Detailed stock information

        Raises:
            HTTPException: If stock not found
        """
        # Get stock basic info
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ticker {ticker} not found",
            )

        # Get latest price data
        latest_price = (
            self.db.query(StockPriceHistory)
            .filter(StockPriceHistory.ticker == ticker)
            .order_by(desc(StockPriceHistory.date))
            .first()
        )

        # Get latest metrics
        latest_metrics = (
            self.db.query(StockDailyMetrics)
            .filter(StockDailyMetrics.ticker == ticker)
            .order_by(desc(StockDailyMetrics.date))
            .first()
        )

        # Calculate 52-week high/low
        one_year_ago = date.today() - timedelta(days=365)
        year_prices = (
            self.db.query(
                func.max(StockPriceHistory.high).label("high_52w"),
                func.min(StockPriceHistory.low).label("low_52w"),
                func.avg(StockPriceHistory.volume).label("avg_volume"),
            )
            .filter(
                StockPriceHistory.ticker == ticker,
                StockPriceHistory.date >= one_year_ago,
            )
            .first()
        )

        # Calculate daily change
        current_price = latest_price.close if latest_price else None
        change = None
        change_percent = None

        if latest_price:
            change = latest_price.close - latest_price.open
            if latest_price.open > 0:
                change_percent = float((change / latest_price.open) * 100)

        return StockDetail(
            ticker=stock.ticker,
            company_name_jp=stock.company_name_jp,
            company_name_en=stock.company_name_en,
            sector_jp=stock.sector_jp,
            industry_jp=stock.industry_jp,
            description=stock.description,
            logo_url=stock.logo_url,
            listing_date=stock.listing_date,
            is_active=stock.is_active,
            created_at=stock.created_at,
            updated_at=stock.updated_at,
            current_price=current_price,
            change=change,
            change_percent=change_percent,
            volume=latest_price.volume if latest_price else None,
            market_cap=latest_metrics.market_cap if latest_metrics else None,
            pe_ratio=latest_metrics.pe_ratio if latest_metrics else None,
            pb_ratio=latest_metrics.pb_ratio if latest_metrics else None,
            dividend_yield=latest_metrics.dividend_yield if latest_metrics else None,
            week_52_high=year_prices.high_52w if year_prices else None,
            week_52_low=year_prices.low_52w if year_prices else None,
            avg_volume=int(year_prices.avg_volume)
            if year_prices and year_prices.avg_volume
            else None,
        )

    async def get_price_history(
        self, request: PriceHistoryRequest
    ) -> PriceHistoryResponse:
        """
        Get historical price data for a stock.

        Args:
            request: Price history request parameters

        Returns:
            Historical price data

        Raises:
            HTTPException: If stock not found
        """
        # Validate stock exists
        stock = self.db.query(Stock).filter(Stock.ticker == request.ticker).first()
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ticker {request.ticker} not found",
            )

        # Calculate date range
        end_date = request.end_date or date.today()

        if request.start_date:
            start_date = request.start_date
        else:
            # Calculate start date based on period
            period_days = {
                "1d": 1,
                "1w": 7,
                "1m": 30,
                "3m": 90,
                "6m": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825,
            }
            days = period_days.get(request.period, 365)
            start_date = end_date - timedelta(days=days)

        # Query price history
        price_query = (
            self.db.query(StockPriceHistory)
            .filter(
                StockPriceHistory.ticker == request.ticker,
                StockPriceHistory.date >= start_date,
                StockPriceHistory.date <= end_date,
            )
            .order_by(asc(StockPriceHistory.date))
        )

        price_records = price_query.all()

        # Convert to PriceData objects
        price_data = [
            PriceData(
                ticker=record.ticker,
                date=record.date,
                open=record.open,
                high=record.high,
                low=record.low,
                close=record.close,
                volume=record.volume,
                adjusted_close=record.adjusted_close,
            )
            for record in price_records
        ]

        return PriceHistoryResponse(
            ticker=request.ticker,
            data=price_data,
            period=request.period,
            interval=request.interval,
            total_points=len(price_data),
            start_date=price_data[0].date if price_data else start_date,
            end_date=price_data[-1].date if price_data else end_date,
        )

    def _get_latest_prices(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get latest price information for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to price information
        """
        if not tickers:
            return {}

        # Get latest prices with previous day comparison
        price_query = text(
            """
            WITH latest_prices AS (
                SELECT DISTINCT ON (ticker) 
                    ticker, date, close, volume, open
                FROM stock_price_history 
                WHERE ticker = ANY(:tickers)
                ORDER BY ticker, date DESC
            ),
            previous_prices AS (
                SELECT DISTINCT ON (sph.ticker)
                    sph.ticker, sph.close as prev_close
                FROM stock_price_history sph
                JOIN latest_prices lp ON sph.ticker = lp.ticker
                WHERE sph.date < lp.date
                ORDER BY sph.ticker, sph.date DESC
            )
            SELECT 
                lp.ticker,
                lp.close as current_price,
                lp.volume,
                COALESCE(
                    ((lp.close - pp.prev_close) / pp.prev_close * 100), 
                    ((lp.close - lp.open) / lp.open * 100)
                ) as change_percent
            FROM latest_prices lp
            LEFT JOIN previous_prices pp ON lp.ticker = pp.ticker
        """
        )

        results = self.db.execute(price_query, {"tickers": tickers}).fetchall()

        return {
            row.ticker: {
                "current_price": Decimal(str(row.current_price)),
                "volume": int(row.volume),
                "change_percent": float(row.change_percent)
                if row.change_percent
                else 0.0,
            }
            for row in results
        }

    async def get_batch_prices(self, tickers: List[str]) -> "BatchPriceResponse":
        """
        Get current prices for multiple stocks in batch.

        Args:
            tickers: List of stock ticker symbols

        Returns:
            Batch price response with current prices and changes
        """
        if not tickers:
            return BatchPriceResponse(
                prices={},
                requested_count=0,
                successful_count=0,
                failed_count=0,
                updated_at=datetime.now(),
            )

        # Get latest prices with change calculations
        price_query = text(
            """
            WITH latest_prices AS (
                SELECT DISTINCT ON (ticker) 
                    ticker, date, close, volume
                FROM stock_price_history 
                WHERE ticker = ANY(:tickers)
                ORDER BY ticker, date DESC
            ),
            previous_prices AS (
                SELECT DISTINCT ON (sph.ticker)
                    sph.ticker, sph.close as prev_close
                FROM stock_price_history sph
                JOIN latest_prices lp ON sph.ticker = lp.ticker
                WHERE sph.date < lp.date
                ORDER BY sph.ticker, sph.date DESC
            )
            SELECT 
                lp.ticker,
                lp.date,
                lp.close as current_price,
                lp.volume,
                COALESCE(pp.prev_close, lp.close) as prev_close,
                COALESCE(
                    (lp.close - pp.prev_close), 
                    0
                ) as price_change,
                COALESCE(
                    ((lp.close - pp.prev_close) / pp.prev_close * 100), 
                    0
                ) as change_percent
            FROM latest_prices lp
            LEFT JOIN previous_prices pp ON lp.ticker = pp.ticker
        """
        )

        try:
            results = self.db.execute(price_query, {"tickers": tickers}).fetchall()

            # Create price data dictionary
            price_data = {}
            successful_tickers = set()

            for row in results:
                successful_tickers.add(row.ticker)
                price_data[row.ticker] = BatchPriceData(
                    ticker=row.ticker,
                    current_price=Decimal(str(row.current_price)),
                    price_change=Decimal(str(row.price_change)),
                    price_change_percent=float(row.change_percent),
                    volume_today=int(row.volume),
                    last_updated=row.date,
                    error=None,
                )

            # Add error entries for tickers without data
            for ticker in tickers:
                if ticker not in successful_tickers:
                    price_data[ticker] = BatchPriceData(
                        ticker=ticker,
                        current_price=None,
                        price_change=None,
                        price_change_percent=None,
                        volume_today=None,
                        last_updated=None,
                        error="Price data not available",
                    )

            return BatchPriceResponse(
                prices=price_data,
                requested_count=len(tickers),
                successful_count=len(successful_tickers),
                failed_count=len(tickers) - len(successful_tickers),
                updated_at=datetime.now(),
            )

        except Exception as e:
            # Return error response for all tickers
            price_data = {
                ticker: BatchPriceData(
                    ticker=ticker,
                    current_price=None,
                    price_change=None,
                    price_change_percent=None,
                    volume_today=None,
                    last_updated=None,
                    error=f"Database error: {str(e)}",
                )
                for ticker in tickers
            }

            return BatchPriceResponse(
                prices=price_data,
                requested_count=len(tickers),
                successful_count=0,
                failed_count=len(tickers),
                updated_at=datetime.now(),
            )
