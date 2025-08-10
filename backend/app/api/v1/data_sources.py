"""Data source management API endpoints."""

import logging
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.adapters import DataSourceUnavailableError, RateLimitExceededError
from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin
from app.models.user import User
from app.schemas.api_response import APIResponse, SuccessResponse
from app.services.data_source_service import DataSourceService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_data_source_service() -> DataSourceService:
    """Get data source service instance."""
    return DataSourceService()


@router.get("/status", response_model=APIResponse[dict])
async def get_data_source_status(
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[dict]:
    """
    Get status of all data sources.

    Returns information about all registered data source adapters including:
    - Health status
    - Circuit breaker states
    - Performance metrics
    """
    try:
        status = await service.get_data_source_status()

        return APIResponse(
            success=True,
            message="Data source status retrieved successfully",
            data=status,
        )

    except Exception as e:
        logger.error(f"Error getting data source status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data source status",
        )


@router.get("/adapters/{adapter_name}/health", response_model=APIResponse[dict])
async def get_adapter_health(
    adapter_name: str,
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[dict]:
    """
    Get detailed health information for a specific adapter.

    Args:
        adapter_name: Name of the adapter

    Returns:
        Detailed health, rate limit, and cost information
    """
    try:
        health_info = await service.get_adapter_health(adapter_name)

        if not health_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adapter '{adapter_name}' not found",
            )

        return APIResponse(
            success=True,
            message=f"Health information for adapter '{adapter_name}' retrieved successfully",
            data=health_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting adapter health for {adapter_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve adapter health information",
        )


@router.post("/adapters/{adapter_name}/enable", response_model=SuccessResponse)
async def enable_adapter(
    adapter_name: str,
    current_user: User = Depends(require_admin),
    service: DataSourceService = Depends(get_data_source_service),
) -> SuccessResponse:
    """
    Enable a data source adapter.

    Args:
        adapter_name: Name of the adapter to enable

    Requires admin privileges.
    """
    try:
        success = await service.enable_adapter(adapter_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adapter '{adapter_name}' not found",
            )

        return SuccessResponse(message=f"Adapter '{adapter_name}' enabled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling adapter {adapter_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable adapter",
        )


@router.post("/adapters/{adapter_name}/disable", response_model=SuccessResponse)
async def disable_adapter(
    adapter_name: str,
    current_user: User = Depends(require_admin),
    service: DataSourceService = Depends(get_data_source_service),
) -> SuccessResponse:
    """
    Disable a data source adapter.

    Args:
        adapter_name: Name of the adapter to disable

    Requires admin privileges.
    """
    try:
        success = await service.disable_adapter(adapter_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adapter '{adapter_name}' not found",
            )

        return SuccessResponse(
            message=f"Adapter '{adapter_name}' disabled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling adapter {adapter_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable adapter",
        )


@router.post(
    "/adapters/{adapter_name}/reset-circuit-breaker", response_model=SuccessResponse
)
async def reset_adapter_circuit_breaker(
    adapter_name: str,
    current_user: User = Depends(require_admin),
    service: DataSourceService = Depends(get_data_source_service),
) -> SuccessResponse:
    """
    Reset circuit breaker for a data source adapter.

    Args:
        adapter_name: Name of the adapter

    Requires admin privileges.
    """
    try:
        success = await service.reset_adapter_circuit_breaker(adapter_name)

        if not success:
            return SuccessResponse(
                message=f"Circuit breaker for adapter '{adapter_name}' was not open"
            )

        return SuccessResponse(
            message=f"Circuit breaker for adapter '{adapter_name}' reset successfully"
        )

    except Exception as e:
        logger.error(f"Error resetting circuit breaker for {adapter_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset circuit breaker",
        )


@router.post("/monitoring/start", response_model=SuccessResponse)
async def start_monitoring(
    current_user: User = Depends(require_admin),
    service: DataSourceService = Depends(get_data_source_service),
) -> SuccessResponse:
    """
    Start health monitoring for all data source adapters.

    Requires admin privileges.
    """
    try:
        await service.start_monitoring()

        return SuccessResponse(message="Data source monitoring started successfully")

    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start monitoring",
        )


@router.post("/monitoring/stop", response_model=SuccessResponse)
async def stop_monitoring(
    current_user: User = Depends(require_admin),
    service: DataSourceService = Depends(get_data_source_service),
) -> SuccessResponse:
    """
    Stop health monitoring for all data source adapters.

    Requires admin privileges.
    """
    try:
        await service.stop_monitoring()

        return SuccessResponse(message="Data source monitoring stopped successfully")

    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop monitoring",
        )


# Stock data endpoints
@router.get("/stocks/{symbol}/price", response_model=APIResponse[dict])
async def get_stock_price(
    symbol: str,
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[dict]:
    """
    Get current stock price.

    Args:
        symbol: Stock symbol (e.g., "7203.T" for Toyota)

    Returns:
        Current stock price data
    """
    try:
        price_data = await service.get_stock_price(symbol)

        return APIResponse(
            success=True,
            message=f"Stock price for {symbol} retrieved successfully",
            data=price_data,
        )

    except DataSourceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting stock price for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stock price",
        )


@router.get("/stocks/{symbol}/history", response_model=APIResponse[List[dict]])
async def get_historical_prices(
    symbol: str,
    start_date: datetime = Query(..., description="Start date for historical data"),
    end_date: datetime = Query(..., description="End date for historical data"),
    interval: str = Query(
        "1d", description="Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)"
    ),
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[List[dict]]:
    """
    Get historical stock prices.

    Args:
        symbol: Stock symbol
        start_date: Start date for historical data
        end_date: End date for historical data
        interval: Data interval

    Returns:
        List of historical price data
    """
    try:
        historical_data = await service.get_historical_prices(
            symbol, start_date, end_date, interval
        )

        return APIResponse(
            success=True,
            message=f"Historical prices for {symbol} retrieved successfully",
            data=historical_data,
        )

    except DataSourceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting historical prices for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical prices",
        )


@router.get("/stocks/search", response_model=APIResponse[List[dict]])
async def search_stocks(
    q: str = Query(..., description="Search query (company name or symbol)"),
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[List[dict]]:
    """
    Search for stock symbols.

    Args:
        q: Search query

    Returns:
        List of matching stocks
    """
    try:
        search_results = await service.search_stocks(q)

        return APIResponse(
            success=True,
            message=f"Stock search completed for query: {q}",
            data=search_results,
        )

    except DataSourceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error searching stocks with query {q}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search stocks",
        )


@router.get(
    "/stocks/{symbol}/financials/{statement_type}",
    response_model=APIResponse[List[dict]],
)
async def get_financial_statements(
    symbol: str,
    statement_type: str,
    period: str = Query("annual", description="Period type (annual, quarterly)"),
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[List[dict]]:
    """
    Get financial statements for a company.

    Args:
        symbol: Stock symbol
        statement_type: Type of statement (income, balance, cash_flow)
        period: Period type (annual, quarterly)

    Returns:
        List of financial statements
    """
    if statement_type not in ["income", "balance", "cash_flow"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="statement_type must be one of: income, balance, cash_flow",
        )

    try:
        statements = await service.get_financial_statements(
            symbol, statement_type, period
        )

        return APIResponse(
            success=True,
            message=f"{statement_type.title()} statements for {symbol} retrieved successfully",
            data=statements,
        )

    except DataSourceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting {statement_type} statements for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve financial statements",
        )


@router.get("/stocks/{symbol}/overview", response_model=APIResponse[dict])
async def get_company_overview(
    symbol: str,
    current_user: User = Depends(get_current_active_user),
    service: DataSourceService = Depends(get_data_source_service),
) -> APIResponse[dict]:
    """
    Get company overview information.

    Args:
        symbol: Stock symbol

    Returns:
        Company overview data
    """
    try:
        overview = await service.get_company_overview(symbol)

        return APIResponse(
            success=True,
            message=f"Company overview for {symbol} retrieved successfully",
            data=overview,
        )

    except DataSourceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting company overview for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company overview",
        )
