"""
Database performance tests.
"""

import asyncio
import pytest
import time
from datetime import date, datetime, timedelta
from typing import List
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session, db_metrics, check_database_health
from app.models.stock import Stock, StockPriceHistory, StockDailyMetrics
from app.models.user import User, UserProfile
from app.models.financial import FinancialReport, FinancialReportLineItem
from app.models.news import NewsArticle, StockNewsLink
from app.models.analysis import AIAnalysisCache
from app.services.database_monitor import db_monitor


class TestDatabasePerformance:
    """Test database performance and optimization."""
    
    @pytest.fixture
    async def sample_data(self):
        """Create sample data for performance testing."""
        async with get_db_session() as session:
            # Create sample stocks
            stocks = []
            for i in range(100):
                stock = Stock(
                    ticker=f"TST{i:04d}",
                    company_name_jp=f"テスト会社{i}",
                    company_name_en=f"Test Company {i}",
                    sector_jp="テクノロジー",
                    industry_jp="ソフトウェア",
                    is_active=True
                )
                stocks.append(stock)
                session.add(stock)
            
            await session.commit()
            
            # Create price history data
            base_date = date.today() - timedelta(days=365)
            for stock in stocks[:10]:  # Only for first 10 stocks to keep test fast
                for day_offset in range(0, 365, 7):  # Weekly data
                    price_date = base_date + timedelta(days=day_offset)
                    price = StockPriceHistory(
                        ticker=stock.ticker,
                        date=price_date,
                        open=1000.0 + (day_offset % 100),
                        high=1050.0 + (day_offset % 100),
                        low=950.0 + (day_offset % 100),
                        close=1000.0 + (day_offset % 100),
                        volume=1000000 + (day_offset * 1000),
                        adjusted_close=1000.0 + (day_offset % 100)
                    )
                    session.add(price)
            
            await session.commit()
            
            # Create users
            users = []
            for i in range(50):
                user = User(
                    email=f"test{i}@example.com",
                    password_hash="hashed_password",
                    email_verified_at=datetime.utcnow().isoformat()
                )
                users.append(user)
                session.add(user)
            
            await session.commit()
            
            return {
                'stocks': stocks,
                'users': users
            }
    
    @pytest.mark.asyncio
    async def test_stock_search_performance(self, sample_data):
        """Test stock search query performance."""
        async with get_db_session() as session:
            # Test ticker search performance
            start_time = time.time()
            
            result = await session.execute(
                text("""
                    SELECT ticker, company_name_jp, company_name_en
                    FROM stocks 
                    WHERE ticker LIKE :pattern 
                    AND is_active = true
                    ORDER BY ticker
                    LIMIT 10
                """),
                {"pattern": "TST%"}
            )
            
            search_time = time.time() - start_time
            results = result.fetchall()
            
            # Should return results quickly (< 50ms)
            assert search_time < 0.05, f"Stock search took {search_time:.3f}s, expected < 0.05s"
            assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_fuzzy_search_performance(self, sample_data):
        """Test fuzzy search performance with trigram indexes."""
        async with get_db_session() as session:
            start_time = time.time()
            
            # Test fuzzy search using similarity
            result = await session.execute(
                text("""
                    SELECT ticker, company_name_jp, 
                           similarity(company_name_jp, :search_term) as sim
                    FROM stocks 
                    WHERE company_name_jp % :search_term
                    AND is_active = true
                    ORDER BY sim DESC
                    LIMIT 10
                """),
                {"search_term": "テスト"}
            )
            
            search_time = time.time() - start_time
            results = result.fetchall()
            
            # Should complete within reasonable time (< 100ms)
            assert search_time < 0.1, f"Fuzzy search took {search_time:.3f}s, expected < 0.1s"
            assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_price_history_query_performance(self, sample_data):
        """Test price history query performance."""
        async with get_db_session() as session:
            ticker = sample_data['stocks'][0].ticker
            
            start_time = time.time()
            
            # Test recent price history query
            result = await session.execute(
                text("""
                    SELECT date, open, high, low, close, volume
                    FROM stock_price_history
                    WHERE ticker = :ticker
                    AND date >= :start_date
                    ORDER BY date DESC
                    LIMIT 100
                """),
                {
                    "ticker": ticker,
                    "start_date": date.today() - timedelta(days=100)
                }
            )
            
            query_time = time.time() - start_time
            results = result.fetchall()
            
            # Should be very fast with proper indexing (< 10ms)
            assert query_time < 0.01, f"Price history query took {query_time:.3f}s, expected < 0.01s"
            assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_hot_stocks_query_performance(self, sample_data):
        """Test hot stocks query performance."""
        async with get_db_session() as session:
            start_time = time.time()
            
            # Test hot stocks query (gainers)
            result = await session.execute(
                text("""
                    WITH latest_prices AS (
                        SELECT DISTINCT ON (ticker) 
                            ticker, date, close, volume,
                            LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close
                        FROM stock_price_history
                        WHERE date >= :recent_date
                        ORDER BY ticker, date DESC
                    )
                    SELECT 
                        ticker,
                        close,
                        prev_close,
                        CASE 
                            WHEN prev_close > 0 
                            THEN ((close - prev_close) / prev_close) * 100 
                            ELSE 0 
                        END as change_percent
                    FROM latest_prices
                    WHERE prev_close IS NOT NULL
                    ORDER BY change_percent DESC
                    LIMIT 10
                """),
                {"recent_date": date.today() - timedelta(days=7)}
            )
            
            query_time = time.time() - start_time
            results = result.fetchall()
            
            # Complex query should still be reasonably fast (< 100ms)
            assert query_time < 0.1, f"Hot stocks query took {query_time:.3f}s, expected < 0.1s"
    
    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self, sample_data):
        """Test performance under concurrent load."""
        
        async def run_concurrent_queries():
            """Run multiple queries concurrently."""
            tasks = []
            
            # Create 10 concurrent stock search tasks
            for i in range(10):
                task = asyncio.create_task(self._search_stocks(f"TST{i:04d}"))
                tasks.append(task)
            
            # Wait for all tasks to complete
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Check that all queries succeeded
            for result in results:
                assert not isinstance(result, Exception), f"Query failed: {result}"
            
            # Total time should be reasonable for concurrent execution
            assert total_time < 1.0, f"Concurrent queries took {total_time:.3f}s, expected < 1.0s"
            
            return results
        
        results = await run_concurrent_queries()
        assert len(results) == 10
    
    async def _search_stocks(self, ticker_pattern: str):
        """Helper method for concurrent testing."""
        async with get_db_session() as session:
            result = await session.execute(
                text("""
                    SELECT ticker, company_name_jp
                    FROM stocks 
                    WHERE ticker LIKE :pattern
                    LIMIT 5
                """),
                {"pattern": f"{ticker_pattern[:3]}%"}
            )
            return result.fetchall()
    
    @pytest.mark.asyncio
    async def test_index_usage_verification(self):
        """Verify that queries are using indexes properly."""
        async with get_db_session() as session:
            # Test that stock search uses index
            result = await session.execute(
                text("""
                    EXPLAIN (ANALYZE, BUFFERS) 
                    SELECT ticker, company_name_jp
                    FROM stocks 
                    WHERE ticker = 'TST0001'
                    AND is_active = true
                """)
            )
            
            explain_output = [row[0] for row in result.fetchall()]
            explain_text = '\n'.join(explain_output)
            
            # Should use index scan, not sequential scan
            assert 'Index Scan' in explain_text or 'Bitmap Index Scan' in explain_text, \
                f"Query not using index: {explain_text}"
            assert 'Seq Scan' not in explain_text, \
                f"Query using sequential scan: {explain_text}"
    
    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check functionality."""
        health_status = await check_database_health()
        
        assert health_status['status'] == 'healthy'
        assert 'connection_time' in health_status
        assert health_status['connection_time'] < 0.1  # Should connect quickly
        assert 'metrics' in health_status
    
    @pytest.mark.asyncio
    async def test_database_monitoring(self):
        """Test database monitoring functionality."""
        # Run monitoring check
        metrics = await db_monitor.check_performance_metrics()
        
        assert 'timestamp' in metrics
        assert 'stats' in metrics
        assert 'status' in metrics
        assert metrics['status'] in ['healthy', 'warning', 'error']
        
        # Check stats structure
        stats = metrics['stats']
        assert 'application_metrics' in stats
        assert 'connections' in stats
        assert 'database_size' in stats
    
    @pytest.mark.asyncio
    async def test_optimization_recommendations(self):
        """Test optimization recommendations."""
        recommendations = await db_monitor.get_optimization_recommendations()
        
        # Should return a list (may be empty for test database)
        assert isinstance(recommendations, list)
        
        # If there are recommendations, they should have proper structure
        for rec in recommendations:
            assert 'type' in rec
            assert 'priority' in rec
            assert 'description' in rec
    
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self):
        """Test bulk insert performance."""
        async with get_db_session() as session:
            # Create bulk news articles
            articles = []
            for i in range(1000):
                article = NewsArticle(
                    headline=f"Test News Article {i}",
                    content_summary=f"Summary for article {i}",
                    source="test_source",
                    published_at=datetime.utcnow().isoformat(),
                    sentiment_label="neutral",
                    sentiment_score=0.0,
                    language="ja"
                )
                articles.append(article)
            
            # Time the bulk insert
            start_time = time.time()
            
            session.add_all(articles)
            await session.commit()
            
            insert_time = time.time() - start_time
            
            # Bulk insert should be efficient (< 1 second for 1000 records)
            assert insert_time < 1.0, f"Bulk insert took {insert_time:.3f}s, expected < 1.0s"
    
    @pytest.mark.asyncio
    async def test_complex_join_performance(self):
        """Test complex join query performance."""
        async with get_db_session() as session:
            start_time = time.time()
            
            # Complex query joining multiple tables
            result = await session.execute(
                text("""
                    SELECT 
                        s.ticker,
                        s.company_name_jp,
                        ph.close as latest_price,
                        dm.market_cap,
                        COUNT(snl.article_id) as news_count
                    FROM stocks s
                    LEFT JOIN LATERAL (
                        SELECT close
                        FROM stock_price_history
                        WHERE ticker = s.ticker
                        ORDER BY date DESC
                        LIMIT 1
                    ) ph ON true
                    LEFT JOIN LATERAL (
                        SELECT market_cap
                        FROM stock_daily_metrics
                        WHERE ticker = s.ticker
                        ORDER BY date DESC
                        LIMIT 1
                    ) dm ON true
                    LEFT JOIN stock_news_link snl ON snl.ticker = s.ticker
                    WHERE s.is_active = true
                    GROUP BY s.ticker, s.company_name_jp, ph.close, dm.market_cap
                    ORDER BY s.ticker
                    LIMIT 20
                """)
            )
            
            query_time = time.time() - start_time
            results = result.fetchall()
            
            # Complex join should complete in reasonable time (< 200ms)
            assert query_time < 0.2, f"Complex join took {query_time:.3f}s, expected < 0.2s"
    
    @pytest.mark.asyncio
    async def test_query_metrics_collection(self):
        """Test that query metrics are being collected."""
        # Reset metrics
        db_metrics.query_count = 0
        db_metrics.total_query_time = 0.0
        db_metrics.slow_queries = []
        
        # Run some queries
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            await session.execute(text("SELECT COUNT(*) FROM stocks"))
        
        # Check that metrics were collected
        stats = db_metrics.get_stats()
        assert stats['total_queries'] >= 2
        assert stats['average_query_time'] >= 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_efficiency(self):
        """Test connection pool efficiency under load."""
        
        async def run_query_batch():
            """Run a batch of queries."""
            async with get_db_session() as session:
                await session.execute(text("SELECT 1"))
                await asyncio.sleep(0.01)  # Small delay
                return True
        
        # Run multiple batches concurrently
        start_time = time.time()
        
        tasks = [run_query_batch() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # All queries should succeed
        assert all(results)
        
        # Should complete efficiently with connection pooling
        assert total_time < 2.0, f"Connection pool test took {total_time:.3f}s, expected < 2.0s"


@pytest.mark.asyncio
async def test_database_maintenance():
    """Test database maintenance operations."""
    from app.services.database_monitor import db_monitor
    
    # Run maintenance tasks
    results = await db_monitor.run_maintenance_tasks()
    
    assert 'analyze' in results
    assert results['analyze'] == 'completed'
    
    # Should have vacuum candidates info
    assert 'vacuum_candidates' in results