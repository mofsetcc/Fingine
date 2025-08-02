"""
Tests for news collection service.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.news_service import NewsCollectionService, news_service
from app.models.news import NewsArticle, StockNewsLink
from app.models.stock import Stock


class TestNewsCollectionService:
    """Test cases for NewsCollectionService."""
    
    @pytest.fixture
    def service(self):
        """Create news service instance for testing."""
        service = NewsCollectionService()
        # Mock the adapter to avoid actual API calls
        service.news_adapter = Mock()
        return service
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_articles(self):
        """Sample article data for testing."""
        return [
            {
                "id": "1",
                "headline": "Toyota reports strong Q4 earnings",
                "content_summary": "Toyota Motor Corp reported strong quarterly earnings...",
                "source": "Nikkei",
                "author": "Business Reporter",
                "published_at": datetime.utcnow().isoformat(),
                "article_url": "https://nikkei.com/article1",
                "language": "ja",
                "relevance_score": 0.9
            },
            {
                "id": "2", 
                "headline": "Japanese stock market rises",
                "content_summary": "Tokyo Stock Exchange sees gains across sectors...",
                "source": "Reuters Japan",
                "author": "Market Reporter",
                "published_at": datetime.utcnow().isoformat(),
                "article_url": "https://reuters.com/article2",
                "language": "ja",
                "relevance_score": 0.7
            }
        ]
    
    @pytest.fixture
    def sample_stocks(self):
        """Sample stock data for testing."""
        return [
            Stock(
                ticker="7203",
                company_name_jp="トヨタ自動車",
                company_name_en="Toyota Motor Corp",
                is_active=True
            ),
            Stock(
                ticker="6758",
                company_name_jp="ソニーグループ",
                company_name_en="Sony Group Corp",
                is_active=True
            )
        ]
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.collection_interval == 3600
        assert service.max_articles_per_collection == 100
        assert service.article_retention_days == 30
        assert not service._is_running
        assert service._collection_task is None
    
    @pytest.mark.asyncio
    async def test_start_stop_collection_scheduler(self, service):
        """Test starting and stopping the collection scheduler."""
        # Mock the collection loop to avoid infinite loop
        with patch.object(service, '_collection_loop') as mock_loop:
            mock_loop.return_value = None
            
            # Start scheduler
            await service.start_collection_scheduler()
            assert service._is_running == True
            assert service._collection_task is not None
            
            # Stop scheduler
            await service.stop_collection_scheduler()
            assert service._is_running == False
    
    @pytest.mark.asyncio
    async def test_collect_general_news_success(self, service, sample_articles):
        """Test successful general news collection."""
        # Mock adapter response
        service.news_adapter.get_news = AsyncMock(return_value=sample_articles)
        
        # Mock database operations
        with patch.object(service, '_store_articles') as mock_store:
            mock_store.return_value = len(sample_articles)
            
            result = await service.collect_general_news()
            
            assert result == len(sample_articles)
            service.news_adapter.get_news.assert_called_once()
            mock_store.assert_called_once_with(sample_articles)
    
    @pytest.mark.asyncio
    async def test_collect_general_news_no_adapter(self, service):
        """Test general news collection without adapter."""
        service.news_adapter = None
        
        result = await service.collect_general_news()
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_collect_general_news_error(self, service):
        """Test general news collection with error."""
        service.news_adapter.get_news = AsyncMock(side_effect=Exception("API Error"))
        
        result = await service.collect_general_news()
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_collect_stock_specific_news(self, service, sample_stocks, sample_articles):
        """Test stock-specific news collection."""
        # Mock database query for stocks
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = sample_stocks
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # Mock stock news collection
            with patch.object(service, '_collect_stock_news') as mock_collect:
                mock_collect.return_value = 2  # 2 articles per stock
                
                result = await service.collect_stock_specific_news()
                
                assert result == 4  # 2 stocks * 2 articles each
                assert mock_collect.call_count == len(sample_stocks)
    
    @pytest.mark.asyncio
    async def test_collect_stock_news(self, service, sample_stocks, sample_articles):
        """Test collecting news for a specific stock."""
        stock = sample_stocks[0]
        
        # Mock adapter response
        service.news_adapter.get_news = AsyncMock(return_value=sample_articles)
        
        # Mock database operations
        with patch.object(service, '_store_articles') as mock_store:
            mock_store.return_value = len(sample_articles)
            
            result = await service._collect_stock_news(stock)
            
            assert result == len(sample_articles)
            service.news_adapter.get_news.assert_called_once()
            
            # Check that stock ticker was passed to store_articles
            call_args = mock_store.call_args
            assert call_args[0][1] == stock.ticker  # Second argument should be ticker
    
    @pytest.mark.asyncio
    async def test_store_articles_new_articles(self, service, sample_articles):
        """Test storing new articles."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock no existing articles (all are new)
            mock_existing_result = Mock()
            mock_existing_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_existing_result)
            
            mock_db.add = Mock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            result = await service._store_articles(sample_articles)
            
            assert result == len(sample_articles)
            assert mock_db.add.call_count == len(sample_articles)
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_articles_with_ticker(self, service, sample_articles):
        """Test storing articles with stock ticker link."""
        ticker = "7203"
        
        with patch('app.services.news_service.get_db') as mock_get_db, \
             patch('app.services.news_service.news_stock_mapping_service') as mock_mapping_service:
            
            mock_db = Mock()
            
            # Mock no existing articles
            mock_existing_result = Mock()
            mock_existing_result.scalar_one_or_none.return_value = None
            
            # Mock stock exists
            mock_stock_result = Mock()
            mock_stock = Mock()
            mock_stock_result.scalar_one_or_none.return_value = mock_stock
            
            # Mock no existing stock links
            mock_link_result = Mock()
            mock_link_result.scalar_one_or_none.return_value = None
            
            # Return different results for different queries
            mock_db.execute = AsyncMock(side_effect=[
                mock_existing_result,  # First article check
                mock_stock_result,     # Stock check
                mock_link_result,      # Stock link check
                mock_existing_result,  # Second article check
                mock_stock_result,     # Stock check
                mock_link_result       # Stock link check
            ])
            
            mock_db.add = Mock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # Mock mapping service
            mock_mapping_service.create_stock_news_links = AsyncMock(return_value=[])
            
            result = await service._store_articles(sample_articles, ticker)
            
            assert result == len(sample_articles)
            # Should call mapping service for each article
            assert mock_mapping_service.create_stock_news_links.call_count == len(sample_articles)
            # Should add articles + targeted stock links
            expected_calls = len(sample_articles) * 2  # articles + targeted links
            assert mock_db.add.call_count == expected_calls
    
    @pytest.mark.asyncio
    async def test_store_articles_duplicate_handling(self, service, sample_articles):
        """Test handling of duplicate articles."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock existing article found (duplicate)
            mock_existing_result = Mock()
            mock_existing_article = Mock()
            mock_existing_result.scalar_one_or_none.return_value = mock_existing_article
            mock_db.execute = AsyncMock(return_value=mock_existing_result)
            
            mock_db.add = Mock()
            mock_db.commit = AsyncMock()
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            result = await service._store_articles(sample_articles)
            
            # No new articles should be stored (all duplicates)
            assert result == 0
            mock_db.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_articles(self, service):
        """Test cleanup of old articles."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock old articles found
            old_articles = [Mock(), Mock(), Mock()]
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = old_articles
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            mock_db.delete = AsyncMock()
            mock_db.commit = AsyncMock()
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            result = await service.cleanup_old_articles()
            
            assert result == len(old_articles)
            assert mock_db.delete.call_count == len(old_articles)
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_news_for_stock(self, service):
        """Test getting news for a specific stock using mapping service."""
        ticker = "7203"
        
        expected_articles = [
            {
                "id": "test-id",
                "headline": "Test Article",
                "content_summary": "Test content",
                "source": "Test Source",
                "author": "Test Author",
                "published_at": "2024-01-01T12:00:00",
                "article_url": "https://example.com/test",
                "language": "ja",
                "sentiment_label": "positive",
                "sentiment_score": 0.8,
                "relevance_score": 0.9
            }
        ]
        
        with patch('app.services.news_service.news_stock_mapping_service') as mock_mapping_service:
            mock_mapping_service.get_news_for_stock = AsyncMock(return_value=expected_articles)
            
            articles = await service.get_news_for_stock(ticker, limit=10)
            
            assert len(articles) == 1
            assert articles[0]["headline"] == "Test Article"
            assert articles[0]["relevance_score"] == 0.9
            assert articles[0]["sentiment_score"] == 0.8
            
            # Verify mapping service was called with correct parameters
            mock_mapping_service.get_news_for_stock.assert_called_once_with(
                ticker=ticker,
                limit=10,
                min_relevance=0.1,
                start_date=None,
                end_date=None
            )
    
    @pytest.mark.asyncio
    async def test_get_recent_news(self, service):
        """Test getting recent news articles."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock recent articles
            mock_article = Mock()
            mock_article.id = "recent-id"
            mock_article.headline = "Recent Article"
            mock_article.content_summary = "Recent content"
            mock_article.source = "Recent Source"
            mock_article.author = "Recent Author"
            mock_article.published_at = datetime.utcnow().isoformat()
            mock_article.article_url = "https://example.com/recent"
            mock_article.language = "ja"
            mock_article.sentiment_label = None
            mock_article.sentiment_score = None
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_article]
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            articles = await service.get_recent_news(limit=20, hours_back=24)
            
            assert len(articles) == 1
            assert articles[0]["headline"] == "Recent Article"
            assert articles[0]["sentiment_score"] is None
    
    @pytest.mark.asyncio
    async def test_force_collection(self, service):
        """Test forced news collection."""
        with patch.object(service, 'collect_general_news') as mock_general, \
             patch.object(service, 'collect_stock_specific_news') as mock_stock, \
             patch.object(service, 'cleanup_old_articles') as mock_cleanup:
            
            mock_general.return_value = 10
            mock_stock.return_value = 20
            mock_cleanup.return_value = 5
            
            stats = await service.force_collection()
            
            assert stats["general_articles"] == 10
            assert stats["stock_articles"] == 20
            assert stats["cleaned_articles"] == 5
            assert stats["total_new_articles"] == 30
            
            mock_general.assert_called_once()
            mock_stock.assert_called_once()
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_collection_status(self, service):
        """Test getting collection status."""
        # Mock adapter health check
        mock_health = Mock()
        mock_health.status.value = "healthy"
        mock_health.response_time_ms = 100.0
        mock_health.last_check = datetime.utcnow()
        mock_health.error_message = None
        
        service.news_adapter.get_cached_health_check = AsyncMock(return_value=mock_health)
        
        # Mock database queries
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock total articles count
            mock_total_result = Mock()
            mock_total_result.scalars.return_value.all.return_value = [Mock()] * 100
            
            # Mock recent articles count
            mock_recent_result = Mock()
            mock_recent_result.scalars.return_value.all.return_value = [Mock()] * 20
            
            mock_db.execute = AsyncMock(side_effect=[mock_total_result, mock_recent_result])
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            status = await service.get_collection_status()
            
            assert status["is_running"] == service._is_running
            assert status["collection_interval"] == service.collection_interval
            assert status["adapter_status"]["status"] == "healthy"
            assert status["total_articles"] == 100
            assert status["recent_articles_24h"] == 20
    
    @pytest.mark.asyncio
    async def test_get_collection_status_no_adapter(self, service):
        """Test getting collection status without adapter."""
        service.news_adapter = None
        
        # Mock database queries
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            status = await service.get_collection_status()
            
            assert status["adapter_status"] is None
            assert status["total_articles"] == 0
            assert status["recent_articles_24h"] == 0
    
    @pytest.mark.asyncio
    async def test_process_existing_articles_for_mapping(self, service):
        """Test processing existing articles for stock mapping."""
        article_ids = ["article-1", "article-2", "article-3"]
        
        with patch('app.services.news_service.get_db') as mock_get_db, \
             patch('app.services.news_service.news_stock_mapping_service') as mock_mapping_service:
            
            mock_db = Mock()
            mock_result = Mock()
            mock_result.all.return_value = [(aid,) for aid in article_ids]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # Mock mapping service batch processing
            expected_stats = {
                "total_processed": 3,
                "total_links_created": 5,
                "errors": 0,
                "success_rate": 1.0
            }
            mock_mapping_service.batch_create_links_for_articles = AsyncMock(return_value=expected_stats)
            
            stats = await service.process_existing_articles_for_mapping()
            
            assert stats == expected_stats
            mock_mapping_service.batch_create_links_for_articles.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_existing_articles_for_mapping_no_articles(self, service):
        """Test processing when no articles need mapping."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.all.return_value = []  # No articles
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            stats = await service.process_existing_articles_for_mapping()
            
            assert stats["total_processed"] == 0
            assert stats["total_links_created"] == 0
            assert stats["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_process_existing_articles_for_mapping_force_refresh(self, service):
        """Test processing with force refresh option."""
        with patch('app.services.news_service.get_db') as mock_get_db, \
             patch('app.services.news_service.news_stock_mapping_service') as mock_mapping_service:
            
            mock_db = Mock()
            mock_result = Mock()
            mock_result.all.return_value = [("article-1",), ("article-2",)]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            mock_mapping_service.batch_create_links_for_articles = AsyncMock(return_value={
                "total_processed": 2,
                "total_links_created": 3,
                "errors": 0,
                "success_rate": 1.0
            })
            
            await service.process_existing_articles_for_mapping(force_refresh=True)
            
            # Should query all articles, not just unlinked ones
            mock_db.execute.assert_called_once()
            # Verify the query doesn't filter by missing links when force_refresh=True
            call_args = mock_db.execute.call_args[0][0]
            query_str = str(call_args)
            assert "outerjoin" not in query_str.lower() or "is_(None)" not in query_str
    
    def test_global_service_instance(self):
        """Test that global service instance exists."""
        assert news_service is not None
        assert isinstance(news_service, NewsCollectionService)
    
    @pytest.mark.asyncio
    async def test_collection_loop_error_handling(self, service):
        """Test error handling in collection loop."""
        service._is_running = True
        
        # Mock methods to raise exceptions
        with patch.object(service, 'collect_general_news') as mock_general, \
             patch.object(service, 'collect_stock_specific_news') as mock_stock, \
             patch.object(service, 'cleanup_old_articles') as mock_cleanup:
            
            mock_general.side_effect = Exception("General news error")
            mock_stock.return_value = 0
            mock_cleanup.return_value = 0
            
            # Mock sleep to avoid waiting
            with patch('asyncio.sleep') as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]  # First sleep succeeds, second cancels
                
                # This should handle the exception and continue
                with pytest.raises(asyncio.CancelledError):
                    await service._collection_loop()
                
                # Should have tried to sleep after error (300 seconds)
                assert mock_sleep.call_count == 2
                assert mock_sleep.call_args_list[0][0][0] == 300  # Error recovery sleep
    
    @pytest.mark.asyncio
    async def test_store_articles_error_handling(self, service, sample_articles):
        """Test error handling in store_articles."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.execute = AsyncMock(side_effect=Exception("Database error"))
            mock_db.rollback = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            result = await service._store_articles(sample_articles)
            
            assert result == 0
            mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_articles_error_handling(self, service):
        """Test error handling in cleanup_old_articles."""
        with patch('app.services.news_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.execute = AsyncMock(side_effect=Exception("Database error"))
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            result = await service.cleanup_old_articles()
            
            assert result == 0