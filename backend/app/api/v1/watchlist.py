"""
Watchlist management API endpoints.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.stock import Stock
from app.models.user import User
from app.models.watchlist import UserWatchlist
from app.schemas.watchlist import (
    WatchlistStockCreate,
    WatchlistStockUpdate,
    WatchlistStockWithPrice,
)
from app.services.watchlist_service import WatchlistService

router = APIRouter()


@router.get("/", response_model=List[WatchlistStockWithPrice])
async def get_user_watchlist(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user's watchlist with real-time price data."""
    watchlist_service = WatchlistService(db)
    return await watchlist_service.get_user_watchlist_with_prices(current_user.id)


@router.post("/", response_model=WatchlistStockWithPrice)
async def add_stock_to_watchlist(
    stock_data: WatchlistStockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a stock to user's watchlist."""
    watchlist_service = WatchlistService(db)
    return await watchlist_service.add_stock_to_watchlist(
        user_id=current_user.id, ticker=stock_data.ticker, notes=stock_data.notes
    )


@router.put("/{ticker}", response_model=WatchlistStockWithPrice)
async def update_watchlist_stock(
    ticker: str,
    stock_data: WatchlistStockUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update notes for a stock in user's watchlist."""
    watchlist_service = WatchlistService(db)
    return await watchlist_service.update_watchlist_stock(
        user_id=current_user.id, ticker=ticker, notes=stock_data.notes
    )


@router.delete("/{ticker}")
async def remove_stock_from_watchlist(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a stock from user's watchlist."""
    watchlist_service = WatchlistService(db)
    await watchlist_service.remove_stock_from_watchlist(
        user_id=current_user.id, ticker=ticker
    )
    return {"message": "Stock removed from watchlist"}


@router.get("/{ticker}", response_model=WatchlistStockWithPrice)
async def get_watchlist_stock(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific stock from user's watchlist."""
    watchlist_service = WatchlistService(db)
    stock = await watchlist_service.get_watchlist_stock(
        user_id=current_user.id, ticker=ticker
    )
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found in watchlist"
        )
    return stock


@router.post("/bulk-add")
async def bulk_add_stocks_to_watchlist(
    tickers: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add multiple stocks to user's watchlist."""
    watchlist_service = WatchlistService(db)
    results = await watchlist_service.bulk_add_stocks_to_watchlist(
        user_id=current_user.id, tickers=tickers
    )
    return results


@router.delete("/bulk-remove")
async def bulk_remove_stocks_from_watchlist(
    tickers: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove multiple stocks from user's watchlist."""
    watchlist_service = WatchlistService(db)
    results = await watchlist_service.bulk_remove_stocks_from_watchlist(
        user_id=current_user.id, tickers=tickers
    )
    return results
