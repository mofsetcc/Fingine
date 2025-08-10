"""
Cached stock service demonstrating Redis cache integration.
"""

import hashlib
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, desc, func, or_, text
from sqlalchemy.orm import Session

from app.core.cache import CacheKeyBuilder
from app.models.stock import Stock, StockDailyMetrics, StockPriceHistory
from app.schemas.stock import (
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
from app.services.cache_service import CacheKeyType, cache_service


class CachedStockService:
    """Stock service with Redis caching integration."""

    def __init__(self, db: Session):
        self.db = db

    def _generate_search_cache_key(self, query: StockSearchQuery) -> str:
        """Generate a cache key for search queries."""
        # Create a hash of the search parameters
        search_params = {
            "query": query.query.strip().lower(),
            "limit": query.limit,
            "include_inactive": query.include_inactive,
        }

        # Create a hash of the parameters for consistent caching
        params_str = str(sorted(search_params.items()))
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

        return f"stock_search:{params_hash}"

    async def search_stocks_cached(
        self, query: StockSearchQuery
    ) -> StockSearchResponse:
        """
        Search stocks with caching support.

        Args:
            query: Search query parameters

        Returns:
            Cached or fresh search results
        """
        # Generate cache key
        cache_key = self._generate_search_cache_key(query)

        # Define the fetch function for cache miss
        async def fetch_search_results():
            return await self._search_stocks_uncached(query)

        # Use cache service to get or set results
        # Use a shorter TTL for search results (5 minutes)
        return await cache_service.get_or_set(
            cache_key, fetch_search_results, ttl=300  # 5 minutes
        )

    async def _search_stocks_uncached(
        self, query: StockSearchQuery
    ) -> StockSearchResponse:
        """
        Perform actual stock search without caching.
        This is the original search logic.
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
        price_data = await self._get_latest_prices_cached(tickers)

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

        return StockSearchResponse(
            results=search_results,
            total=total,
            query=query.query,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

    async def _get_latest_prices_cached(
        self, tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get latest prices for multiple tickers with caching.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to price data
        """
        price_data = {}
        uncached_tickers = []

        # Check cache for each ticker
        for ticker in tickers:
            cached_price = await cache_service.get_stock_price_cached(
                ticker, lambda: self._fetch_single_price(ticker)
            )

            if cached_price:
                price_data[ticker] = cached_price
            else:
                uncached_tickers.append(ticker)

        # Fetch uncached prices
        if uncached_tickers:
            fresh_prices = await self._fetch_multiple_prices(uncached_tickers)

            # Cache the fresh prices
            for ticker, price_info in fresh_prices.items():
                await cache_service.cache_manager.set_stock_price(ticker, price_info)
                price_data[ticker] = price_info

        return price_data

    async def _fetch_single_price(self, ticker: str) -> Dict[str, Any]:
        """Fetch price data for a single ticker."""
        # This would normally call external API or database
        # For now, return mock data
        return {
            "current_price": 2500.0,
            "change_percent": 1.5,
            "volume": 1000000,
            "last_updated": datetime.now().isoformat(),
        }

    async def _fetch_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch price data for multiple tickers."""
        # This would normally batch fetch from external API
        # For now, return mock data
        result = {}
        for ticker in tickers:
            result[ticker] = await self._fetch_single_price(ticker)
        return result

    async def get_stock_detail_cached(self, ticker: str) -> Optional[StockDetail]:
        """
        Get detailed stock information with caching.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Cached or fresh stock detail
        """

        # Define the fetch function for cache miss
        async def fetch_stock_detail():
            return await self._get_stock_detail_uncached(ticker)

        # Use cache service with stock price TTL
        return await cache_service.get_stock_price_cached(ticker, fetch_stock_detail)

    async def _get_stock_detail_uncached(self, ticker: str) -> Optional[StockDetail]:
        """Get stock detail without caching."""
        # Query stock from database
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()

        if not stock:
            return None

        # Get latest price data
        price_data = await self._fetch_single_price(ticker)

        # Get latest financial metrics
        latest_metrics = (
            self.db.query(StockDailyMetrics)
            .filter(StockDailyMetrics.ticker == ticker)
            .order_by(desc(StockDailyMetrics.date))
            .first()
        )

        return StockDetail(
            ticker=stock.ticker,
            company_name_jp=stock.company_name_jp,
            company_name_en=stock.company_name_en,
            sector_jp=stock.sector_jp,
            industry_jp=stock.industry_jp,
            description=stock.description,
            current_price=price_data.get("current_price"),
            change_percent=price_data.get("change_percent"),
            volume=price_data.get("volume"),
            market_cap=latest_metrics.market_cap if latest_metrics else None,
            pe_ratio=float(latest_metrics.pe_ratio)
            if latest_metrics and latest_metrics.pe_ratio
            else None,
            pb_ratio=float(latest_metrics.pb_ratio)
            if latest_metrics and latest_metrics.pb_ratio
            else None,
            dividend_yield=float(latest_metrics.dividend_yield)
            if latest_metrics and latest_metrics.dividend_yield
            else None,
        )

    async def get_hot_stocks_cached(self) -> HotStocksResponse:
        """
        Get hot stocks (gainers, losers, most traded) with caching.

        Returns:
            Cached or fresh hot stocks data
        """
        cache_key = "market_data:hot_stocks:daily"

        # Define the fetch function for cache miss
        async def fetch_hot_stocks():
            return await self._get_hot_stocks_uncached()

        # Use cache service with market data TTL (5 minutes)
        return await cache_service.get_or_set(
            cache_key, fetch_hot_stocks, key_type=CacheKeyType.MARKET_DATA
        )

    async def _get_hot_stocks_uncached(self) -> HotStocksResponse:
        """Get hot stocks without caching."""
        # This would normally query recent price changes
        # For now, return mock data

        mock_stocks = [
            HotStock(
                ticker="7203",
                company_name_jp="トヨタ自動車",
                current_price=2500.0,
                change_percent=5.2,
                volume=2000000,
            ),
            HotStock(
                ticker="6758",
                company_name_jp="ソニーグループ",
                current_price=15000.0,
                change_percent=-3.1,
                volume=1500000,
            ),
            HotStock(
                ticker="9984",
                company_name_jp="ソフトバンクグループ",
                current_price=3000.0,
                change_percent=2.8,
                volume=3000000,
            ),
        ]

        return HotStocksResponse(
            gainers=mock_stocks[:1],  # Top gainer
            losers=mock_stocks[1:2],  # Top loser
            most_traded=mock_stocks[2:3],  # Most traded
            last_updated=datetime.now(),
        )

    async def invalidate_stock_cache(self, ticker: str) -> int:
        """
        Invalidate all cached data for a specific stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Number of cache entries invalidated
        """
        return await cache_service.invalidate_stock_data(ticker)

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        return await cache_service.get_cache_statistics()
