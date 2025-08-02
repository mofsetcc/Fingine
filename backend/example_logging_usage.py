"""
Example usage of structured logging in API endpoints.
"""

from fastapi import FastAPI, HTTPException, Request
from app.core.logging import StructuredLogger, error_logger
from app.core.logging_middleware import BusinessEventLogger

# Create logger for this service
api_logger = StructuredLogger("stock_api")

app = FastAPI()

@app.get("/api/v1/stocks/{ticker}")
async def get_stock_data(ticker: str, request: Request):
    """Example endpoint showing structured logging usage."""
    
    try:
        # Log business event for analytics
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            BusinessEventLogger.log_stock_analysis_request(
                user_id=user_id,
                ticker=ticker,
                analysis_type="basic_info",
                metadata={"source": "api_endpoint"}
            )
        
        # Simulate some processing
        if ticker == "INVALID":
            raise ValueError("Invalid ticker symbol")
        
        # Log data source access
        api_logger.log_data_source_event({
            "source_name": "stock_database",
            "source_type": "stock_info",
            "operation": "fetch_stock_data",
            "status": "success",
            "response_time_ms": 50,
            "records_processed": 1
        })
        
        # Return mock data
        return {
            "ticker": ticker,
            "company_name": f"Company {ticker}",
            "price": 1000.0
        }
        
    except ValueError as e:
        # Log structured error
        error_logger.log_error({
            "error_type": "validation_error",
            "error_message": str(e),
            "error_code": "INVALID_TICKER",
            "user_id": user_id,
            "endpoint": f"/api/v1/stocks/{ticker}",
            "method": "GET",
            "context": {"ticker": ticker}
        }, e)
        
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Log unexpected errors
        error_logger.log_error({
            "error_type": "internal_error",
            "error_message": "Unexpected error occurred",
            "user_id": user_id,
            "endpoint": f"/api/v1/stocks/{ticker}",
            "method": "GET",
            "context": {"ticker": ticker}
        }, e)
        
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    print("Example of structured logging usage in API endpoints:")
    print("- Business events are logged for analytics")
    print("- Data source operations are tracked")
    print("- Errors are logged with full context")
    print("- All logs are in structured JSON format")
    print("- IP addresses are automatically anonymized")
    print("- Request/response data is captured by middleware")