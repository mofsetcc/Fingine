"""
Simple test to verify API endpoints work.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Project Kessan API"

def test_health_endpoint():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_stock_search_endpoint():
    """Test stock search endpoint."""
    response = client.get("/api/v1/stocks/search?query=test&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "query" in data
    assert "execution_time_ms" in data
    assert data["query"] == "test"

def test_market_indices_endpoint():
    """Test market indices endpoint."""
    response = client.get("/api/v1/stocks/market/indices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # At least Nikkei and TOPIX

def test_hot_stocks_endpoint():
    """Test hot stocks endpoint."""
    response = client.get("/api/v1/stocks/market/hot-stocks")
    assert response.status_code == 200
    data = response.json()
    assert "gainers" in data
    assert "losers" in data
    assert "most_traded" in data
    assert "updated_at" in data

def test_stock_detail_invalid_ticker():
    """Test stock detail with invalid ticker."""
    response = client.get("/api/v1/stocks/invalid")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "4 digits" in data["detail"]

def test_price_history_invalid_ticker():
    """Test price history with invalid ticker."""
    response = client.get("/api/v1/stocks/invalid/price-history")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "4 digits" in data["detail"]

if __name__ == "__main__":
    print("Testing API endpoints...")
    
    test_root_endpoint()
    print("✓ Root endpoint works")
    
    test_health_endpoint()
    print("✓ Health endpoint works")
    
    test_stock_search_endpoint()
    print("✓ Stock search endpoint works")
    
    test_market_indices_endpoint()
    print("✓ Market indices endpoint works")
    
    test_hot_stocks_endpoint()
    print("✓ Hot stocks endpoint works")
    
    test_stock_detail_invalid_ticker()
    print("✓ Stock detail validation works")
    
    test_price_history_invalid_ticker()
    print("✓ Price history validation works")
    
    print("\nAll API endpoint tests passed! ✅")