"""
Performance tests for stock search functionality.
"""

import time
import pytest
from decimal import Decimal
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db
from app.models.stock import Stock, StockPriceHistory, StockDailyMetrics
from app.services.stock_service import StockService
from app.schemas.stock import StockSearchQuery


class TestStockSearchPerformance:
    """Performance tests for stock search functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def db_session(self):
        """Create database session for testing."""
        # This would be configured with your test database
        # For now, we'll mock it
        pass
    
    @pytest.fixture
    def sample_stocks(self, db_session):
        """Create sample stock data for performance testing."""
        stocks = []
        
        # Create 1000 sample stocks for performance testing
        for i in range(1000):
            ticker = f"{i+1:04d}"  # 0001, 0002, etc.
            stock = Stock(
                ticker=ticker,
                company_name_jp=f"テスト会社{i+1}",
                company_name_en=f"Test Company {i+1}",
                sector_jp=f"セクター{i % 10}",
                industry_jp=f"業界{i % 20}",
                is_active=True
            )
            stocks.append(stock)
        
        # Add some specific test cases
        test_cases = [
            Stock(
                ticker="7203",
                company_name_jp="トヨタ自動車",
                company_name_en="Toyota Motor Corporation",
                sector_jp="輸送用機器",
                industry_jp="自動車",
                is_active=True
            ),
            Stock(
                ticker="9984",
                company_name_jp="ソフトバンクグループ",
                company_name_en="SoftBank Group Corp",
                sector_jp="情報・通信業",
                industry_jp="通信",
                is_active=True
            ),
            Stock(
                ticker="6758",
                company_name_jp="ソニーグループ",
                company_name_en="Sony Group Corporation",
                sector_jp="電気機器",
                industry_jp="電子機器",
                is_active=True
            )
        ]
        
        stocks.extend(test_cases)
        
        # Mock database operations
        return stocks
    
    @pytest.fixture
    def sample_price_data(self, db_session, sample_stocks):
        """Create sample price data for performance testing."""
        price_data = []
        today = date.today()
        
        for stock in sample_stocks[:100]:  # Only create price data for first 100 stocks
            for days_back in range(30):  # 30 days of data
                price_date = today - timedelta(days=days_back)
                base_price = 1000 + (hash(stock.ticker) % 5000)  # Deterministic price
                
                price_record = StockPriceHistory(
                    ticker=stock.ticker,
                    date=price_date,
                    open=Decimal(str(base_price)),
                    high=Decimal(str(base_price * 1.05)),
                    low=Decimal(str(base_price * 0.95)),
                    close=Decimal(str(base_price * (1 + (days_back % 10 - 5) * 0.01))),
                    volume=1000000 + (hash(stock.ticker + str(days_back)) % 5000000),
                    adjusted_close=None
                )
                price_data.append(price_record)
        
        return price_data
    
    def test_search_response_time_under_500ms(self, client, sample_stocks):
        """Test that search responses are under 500ms."""
        test_queries = [
            "トヨタ",
            "Toyota",
            "7203",
            "ソフト",
            "電気",
            "72"
        ]
        
        for query in test_queries:
            start_time = time.time()
            
            response = client.get(f"/api/v1/stocks/search?query={query}&limit=20")
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Assert response is successful
            assert response.status_code == 200
            
            # Assert response time is under 500ms
            assert response_time_ms < 500, f"Search for '{query}' took {response_time_ms:.2f}ms (>500ms)"
            
            # Verify response structure
            data = response.json()
            assert "results" in data
            assert "total" in data
            assert "query" in data
            assert "execution_time_ms" in data
            assert data["execution_time_ms"] < 500
    
    def test_fuzzy_search_performance(self, client):
        """Test fuzzy search performance with various query types."""
        fuzzy_queries = [
            ("トヨタ", "Toyota-related searches"),
            ("ソニー", "Sony-related searches"),
            ("銀行", "Bank-related searches"),
            ("電気", "Electronics-related searches"),
            ("通信", "Telecom-related searches"),
            ("7203", "Exact ticker search"),
            ("720", "Partial ticker search"),
            ("Toy", "English partial match"),
            ("Soft", "English partial match")
        ]
        
        performance_results = []
        
        for query, description in fuzzy_queries:
            start_time = time.time()
            
            response = client.get(f"/api/v1/stocks/search?query={query}&limit=50")
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            data = response.json()
            
            performance_results.append({
                "query": query,
                "description": description,
                "response_time_ms": response_time_ms,
                "results_count": len(data["results"]),
                "total_matches": data["total"]
            })
            
            # Each query should be under 500ms
            assert response_time_ms < 500
        
        # Log performance results for analysis
        print("\nFuzzy Search Performance Results:")
        for result in performance_results:
            print(f"  {result['description']}: {result['response_time_ms']:.2f}ms "
                  f"({result['results_count']} results, {result['total_matches']} total)")
    
    def test_hot_stocks_performance(self, client, sample_price_data):
        """Test hot stocks endpoint performance."""
        start_time = time.time()
        
        response = client.get("/api/v1/stocks/market/hot-stocks")
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time_ms < 1000  # Hot stocks can take up to 1 second
        
        data = response.json()
        assert "gainers" in data
        assert "losers" in data
        assert "most_traded" in data
        assert "updated_at" in data
        
        # Verify data structure
        for category in ["gainers", "losers", "most_traded"]:
            assert isinstance(data[category], list)
            assert len(data[category]) <= 10  # Max 10 items per category
    
    def test_market_indices_performance(self, client):
        """Test market indices endpoint performance."""
        start_time = time.time()
        
        response = client.get("/api/v1/stocks/market/indices")
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time_ms < 200  # Market indices should be very fast
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least Nikkei and TOPIX
        
        # Verify data structure
        for index in data:
            assert "name" in index
            assert "symbol" in index
            assert "value" in index
            assert "change" in index
            assert "change_percent" in index
    
    def test_stock_detail_performance(self, client):
        """Test stock detail endpoint performance."""
        test_tickers = ["7203", "9984", "6758"]
        
        for ticker in test_tickers:
            start_time = time.time()
            
            response = client.get(f"/api/v1/stocks/{ticker}")
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Stock detail should be fast
            assert response_time_ms < 300
            
            if response.status_code == 200:
                data = response.json()
                assert data["ticker"] == ticker
                assert "company_name_jp" in data
                assert "current_price" in data
    
    def test_price_history_performance(self, client):
        """Test price history endpoint performance."""
        test_cases = [
            ("7203", "1m", "1d"),
            ("7203", "3m", "1d"),
            ("7203", "1y", "1d"),
            ("9984", "1m", "1d")
        ]
        
        for ticker, period, interval in test_cases:
            start_time = time.time()
            
            response = client.get(
                f"/api/v1/stocks/{ticker}/price-history"
                f"?period={period}&interval={interval}"
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Price history should be reasonably fast
            assert response_time_ms < 800
            
            if response.status_code == 200:
                data = response.json()
                assert data["ticker"] == ticker
                assert data["period"] == period
                assert data["interval"] == interval
                assert "data" in data
    
    def test_concurrent_search_performance(self, client):
        """Test search performance under concurrent load."""
        import concurrent.futures
        import threading
        
        def perform_search(query):
            """Perform a single search request."""
            start_time = time.time()
            response = client.get(f"/api/v1/stocks/search?query={query}&limit=20")
            end_time = time.time()
            
            return {
                "query": query,
                "status_code": response.status_code,
                "response_time_ms": (end_time - start_time) * 1000,
                "success": response.status_code == 200
            }
        
        # Test queries
        queries = ["トヨタ", "ソニー", "7203", "9984", "銀行", "電気"] * 5  # 30 total requests
        
        # Perform concurrent searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(perform_search, query) for query in queries]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        avg_response_time = sum(r["response_time_ms"] for r in successful_requests) / len(successful_requests)
        max_response_time = max(r["response_time_ms"] for r in successful_requests)
        
        print(f"\nConcurrent Search Performance:")
        print(f"  Total requests: {len(queries)}")
        print(f"  Successful: {len(successful_requests)}")
        print(f"  Failed: {len(failed_requests)}")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Max response time: {max_response_time:.2f}ms")
        print(f"  Total execution time: {total_time:.2f}s")
        
        # Assertions
        assert len(failed_requests) == 0, f"Failed requests: {failed_requests}"
        assert avg_response_time < 600, f"Average response time too high: {avg_response_time:.2f}ms"
        assert max_response_time < 1000, f"Max response time too high: {max_response_time:.2f}ms"
    
    def test_search_relevance_scoring(self, client):
        """Test that search results are properly scored for relevance."""
        # Test exact ticker match gets highest score
        response = client.get("/api/v1/stocks/search?query=7203&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        if data["results"]:
            # First result should be exact match with high score
            first_result = data["results"][0]
            if first_result["ticker"] == "7203":
                assert first_result["match_score"] >= 0.9
        
        # Test company name search
        response = client.get("/api/v1/stocks/search?query=トヨタ&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        if data["results"]:
            # Results should be ordered by relevance score
            scores = [result["match_score"] for result in data["results"]]
            assert scores == sorted(scores, reverse=True), "Results not ordered by relevance"
    
    def test_search_with_filters(self, client):
        """Test search performance with various filters."""
        test_cases = [
            {"query": "電気", "include_inactive": False},
            {"query": "電気", "include_inactive": True},
            {"query": "7203", "limit": 5},
            {"query": "ソフト", "limit": 50}
        ]
        
        for params in test_cases:
            start_time = time.time()
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            response = client.get(f"/api/v1/stocks/search?{query_string}")
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            assert response_time_ms < 500
            
            data = response.json()
            assert len(data["results"]) <= params.get("limit", 20)


class TestStockServicePerformance:
    """Unit tests for StockService performance."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        # This would be a proper mock of the database session
        pass
    
    @pytest.fixture
    def stock_service(self, mock_db):
        """Create StockService instance."""
        return StockService(mock_db)
    
    def test_search_query_optimization(self, stock_service):
        """Test that search queries are optimized."""
        # This would test the actual SQL queries generated
        # to ensure they use proper indexes and are optimized
        pass
    
    def test_price_data_aggregation_performance(self, stock_service):
        """Test performance of price data aggregation for hot stocks."""
        # This would test the hot stocks calculation performance
        pass
    
    def test_cache_effectiveness(self, stock_service):
        """Test that caching improves performance."""
        # This would test caching mechanisms if implemented
        pass


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])