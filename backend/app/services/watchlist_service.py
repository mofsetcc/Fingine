"""
Watchlist management service.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc

from app.models.watchlist import UserWatchlist
from app.models.stock import Stock, StockPriceHistory
from app.models.user import User
from app.schemas.watchlist import WatchlistStockWithPrice
from app.services.stock_service import StockService


class WatchlistService:
    """Service for managing user watchlists."""
    
    def __init__(self, db: Session):
        self.db = db
        self.stock_service = StockService(db)
    
    async def get_user_watchlist_with_prices(self, user_id: UUID) -> List[WatchlistStockWithPrice]:
        """Get user's watchlist with current price data."""
        # Get watchlist entries with stock details
        watchlist_entries = (
            self.db.query(UserWatchlist)
            .options(joinedload(UserWatchlist.stock))
            .filter(UserWatchlist.user_id == user_id)
            .order_by(UserWatchlist.created_at.desc())
            .all()
        )
        
        result = []
        for entry in watchlist_entries:
            # Get current price data
            price_data = await self._get_current_price_data(entry.ticker)
            
            # Create response object
            watchlist_stock = WatchlistStockWithPrice(
                id=None,  # Not using UUID for simple watchlist
                user_id=user_id,
                ticker=entry.ticker,
                notes=entry.notes,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                stock=entry.stock,
                current_price=price_data.get('current_price'),
                price_change=price_data.get('price_change'),
                price_change_percent=price_data.get('price_change_percent'),
                volume_today=price_data.get('volume_today'),
                last_updated=price_data.get('last_updated'),
                price_alert_triggered=False,  # Simple implementation
                volume_alert_triggered=False
            )
            result.append(watchlist_stock)
        
        return result
    
    async def add_stock_to_watchlist(
        self, 
        user_id: UUID, 
        ticker: str, 
        notes: Optional[str] = None
    ) -> WatchlistStockWithPrice:
        """Add a stock to user's watchlist."""
        # Validate stock exists
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            raise ValueError(f"Stock with ticker {ticker} not found")
        
        # Check if already in watchlist
        existing = (
            self.db.query(UserWatchlist)
            .filter(and_(UserWatchlist.user_id == user_id, UserWatchlist.ticker == ticker))
            .first()
        )
        if existing:
            raise ValueError(f"Stock {ticker} is already in watchlist")
        
        # Create watchlist entry
        watchlist_entry = UserWatchlist(
            user_id=user_id,
            ticker=ticker,
            notes=notes
        )
        self.db.add(watchlist_entry)
        self.db.commit()
        self.db.refresh(watchlist_entry)
        
        # Get price data and return
        price_data = await self._get_current_price_data(ticker)
        
        return WatchlistStockWithPrice(
            id=None,
            user_id=user_id,
            ticker=ticker,
            notes=notes,
            created_at=watchlist_entry.created_at,
            updated_at=watchlist_entry.updated_at,
            stock=stock,
            current_price=price_data.get('current_price'),
            price_change=price_data.get('price_change'),
            price_change_percent=price_data.get('price_change_percent'),
            volume_today=price_data.get('volume_today'),
            last_updated=price_data.get('last_updated'),
            price_alert_triggered=False,
            volume_alert_triggered=False
        )
    
    async def update_watchlist_stock(
        self, 
        user_id: UUID, 
        ticker: str, 
        notes: Optional[str] = None
    ) -> WatchlistStockWithPrice:
        """Update a stock in user's watchlist."""
        watchlist_entry = (
            self.db.query(UserWatchlist)
            .filter(and_(UserWatchlist.user_id == user_id, UserWatchlist.ticker == ticker))
            .first()
        )
        
        if not watchlist_entry:
            raise ValueError(f"Stock {ticker} not found in watchlist")
        
        # Update notes
        watchlist_entry.notes = notes
        watchlist_entry.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(watchlist_entry)
        
        # Get stock and price data
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        price_data = await self._get_current_price_data(ticker)
        
        return WatchlistStockWithPrice(
            id=None,
            user_id=user_id,
            ticker=ticker,
            notes=notes,
            created_at=watchlist_entry.created_at,
            updated_at=watchlist_entry.updated_at,
            stock=stock,
            current_price=price_data.get('current_price'),
            price_change=price_data.get('price_change'),
            price_change_percent=price_data.get('price_change_percent'),
            volume_today=price_data.get('volume_today'),
            last_updated=price_data.get('last_updated'),
            price_alert_triggered=False,
            volume_alert_triggered=False
        )
    
    async def remove_stock_from_watchlist(self, user_id: UUID, ticker: str) -> None:
        """Remove a stock from user's watchlist."""
        watchlist_entry = (
            self.db.query(UserWatchlist)
            .filter(and_(UserWatchlist.user_id == user_id, UserWatchlist.ticker == ticker))
            .first()
        )
        
        if not watchlist_entry:
            raise ValueError(f"Stock {ticker} not found in watchlist")
        
        self.db.delete(watchlist_entry)
        self.db.commit()
    
    async def get_watchlist_stock(
        self, 
        user_id: UUID, 
        ticker: str
    ) -> Optional[WatchlistStockWithPrice]:
        """Get a specific stock from user's watchlist."""
        watchlist_entry = (
            self.db.query(UserWatchlist)
            .options(joinedload(UserWatchlist.stock))
            .filter(and_(UserWatchlist.user_id == user_id, UserWatchlist.ticker == ticker))
            .first()
        )
        
        if not watchlist_entry:
            return None
        
        price_data = await self._get_current_price_data(ticker)
        
        return WatchlistStockWithPrice(
            id=None,
            user_id=user_id,
            ticker=ticker,
            notes=watchlist_entry.notes,
            created_at=watchlist_entry.created_at,
            updated_at=watchlist_entry.updated_at,
            stock=watchlist_entry.stock,
            current_price=price_data.get('current_price'),
            price_change=price_data.get('price_change'),
            price_change_percent=price_data.get('price_change_percent'),
            volume_today=price_data.get('volume_today'),
            last_updated=price_data.get('last_updated'),
            price_alert_triggered=False,
            volume_alert_triggered=False
        )
    
    async def bulk_add_stocks_to_watchlist(
        self, 
        user_id: UUID, 
        tickers: List[str]
    ) -> Dict[str, Any]:
        """Add multiple stocks to user's watchlist."""
        results = {
            "successful": [],
            "failed": [],
            "already_exists": []
        }
        
        for ticker in tickers:
            try:
                # Check if stock exists
                stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
                if not stock:
                    results["failed"].append({"ticker": ticker, "reason": "Stock not found"})
                    continue
                
                # Check if already in watchlist
                existing = (
                    self.db.query(UserWatchlist)
                    .filter(and_(UserWatchlist.user_id == user_id, UserWatchlist.ticker == ticker))
                    .first()
                )
                if existing:
                    results["already_exists"].append(ticker)
                    continue
                
                # Add to watchlist
                watchlist_entry = UserWatchlist(
                    user_id=user_id,
                    ticker=ticker,
                    notes=None
                )
                self.db.add(watchlist_entry)
                results["successful"].append(ticker)
                
            except Exception as e:
                results["failed"].append({"ticker": ticker, "reason": str(e)})
        
        self.db.commit()
        return results
    
    async def bulk_remove_stocks_from_watchlist(
        self, 
        user_id: UUID, 
        tickers: List[str]
    ) -> Dict[str, Any]:
        """Remove multiple stocks from user's watchlist."""
        results = {
            "successful": [],
            "not_found": []
        }
        
        for ticker in tickers:
            watchlist_entry = (
                self.db.query(UserWatchlist)
                .filter(and_(UserWatchlist.user_id == user_id, UserWatchlist.ticker == ticker))
                .first()
            )
            
            if watchlist_entry:
                self.db.delete(watchlist_entry)
                results["successful"].append(ticker)
            else:
                results["not_found"].append(ticker)
        
        self.db.commit()
        return results
    
    async def _get_current_price_data(self, ticker: str) -> Dict[str, Any]:
        """Get current price data for a stock."""
        try:
            # Get latest price from price history
            latest_price = (
                self.db.query(StockPriceHistory)
                .filter(StockPriceHistory.ticker == ticker)
                .order_by(desc(StockPriceHistory.date))
                .first()
            )
            
            if not latest_price:
                return {}
            
            # Get previous day's price for change calculation
            previous_price = (
                self.db.query(StockPriceHistory)
                .filter(StockPriceHistory.ticker == ticker)
                .filter(StockPriceHistory.date < latest_price.date)
                .order_by(desc(StockPriceHistory.date))
                .first()
            )
            
            current_price = float(latest_price.close)
            price_change = None
            price_change_percent = None
            
            if previous_price:
                previous_close = float(previous_price.close)
                price_change = current_price - previous_close
                price_change_percent = (price_change / previous_close) * 100 if previous_close > 0 else 0
            
            return {
                "current_price": current_price,
                "price_change": price_change,
                "price_change_percent": price_change_percent,
                "volume_today": int(latest_price.volume),
                "last_updated": latest_price.date
            }
            
        except Exception as e:
            # Return empty data if price retrieval fails
            return {}