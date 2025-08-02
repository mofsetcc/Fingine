"""
Tests for news-stock mapping service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.news_stock_mapping_service import NewsStockMappingService, news_stock_mapping_service
from app.models.news import NewsArticle, StockNewsLink
from app.models.stock import Stock


class TestNewsStockMappingService:
    """Test cases for NewsStockMappingService."""
    
    @pytest.fixture
    def service(self):
        """Create mapping service instance for testing."""
        service = NewsStockMappingService()
        return service
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_stocks(self):
        """Sample stock data for testing."""
        return [
            Stock(
                ticker="7203",
                company_name_jp="トヨタ自動車株式会社",
                company_name_en="Toyota Motor Corporation",
                sector_jp="自動車",
                industry_jp="自動車製造",
                is_active=True
            ),
            Stock(
                ticker="6758",
                company_name_jp="ソニーグループ株式会社",
                company_name_en="Sony Group Corporation",
                sector_jp="電機",
                industry_jp="電子機器",
                is_active=True
            ),
            Stock(
                ticker="9984",
                company_name_jp="ソフトバンクグループ株式会社",
                company_name_en="SoftBank Group Corp",
                sector_jp="通信",
                industry_jp="通信サービス",
                is_active=True
            )
        ]
    
    @pytest.fixture
    def sample_articles(self):
        """Sample article data for testing."""
        return [
            {
                "id": "article-1",
                "headline": "トヨタ自動車(7203)が決算発表、売上高が過去最高を記録",
                "content_summary": "トヨタ自動車株式会社は本日、第4四半期の決算を発表し、売上高が前年同期比15%増となった。",
                "source": "Nikkei",
                "published_at": datetime.utcnow().isoformat()
            },
            {
                "id": "article-2", 
                "headline": "Sony Group reports strong gaming division performance",
                "content_summary": "ソニーグループのゲーム部門が好調な業績を報告。PlayStation 5の売上が予想を上回る。",
                "source": "Reuters Japan",
                "published_at": datetime.utcnow().isoformat()
            },
            {
                "id": "article-3",
                "headline": "日本株式市場全体が上昇、自動車セクターが牽引",
                "content_summary": "東京証券取引所で日経平均が上昇。自動車関連株が全面高となり、市場を牽引した。",
                "source": "Yahoo Finance Japan",
                "published_at": datetime.utcnow().isoformat()
            }
        ]
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.min_relevance_threshold == 0.1
        assert service._stock_cache == {}
        assert service._cache_last_updated is None
        assert service._cache_ttl_seconds == 3600
        assert len(service._japanese_company_suffixes) > 0
        assert len(service._financial_keywords) > 0
    
    @pytest.mark.asyncio
    async def test_refresh_stock_cache(self, service, sample_stocks):
        """Test stock cache refresh."""
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = sample_stocks
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            await service.refresh_stock_cache()
            
            assert len(service._stock_cache) == len(sample_stocks)
            assert "7203" in service._stock_cache
            assert "6758" in service._stock_cache
            assert "9984" in service._stock_cache
            assert service._cache_last_updated is not None
    
    @pytest.mark.asyncio
    async def test_ensure_stock_cache_refresh_needed(self, service, sample_stocks):
        """Test cache refresh when TTL expired."""
        # Set cache as expired
        service._cache_last_updated = datetime.utcnow() - timedelta(seconds=3700)
        
        with patch.object(service, 'refresh_stock_cache') as mock_refresh:
            mock_refresh.return_value = None
            
            await service._ensure_stock_cache()
            
            mock_refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_stock_cache_no_refresh_needed(self, service, sample_stocks):
        """Test cache not refreshed when still valid."""
        # Set cache as fresh
        service._cache_last_updated = datetime.utcnow() - timedelta(seconds=1800)
        service._stock_cache = {"7203": sample_stocks[0]}
        
        with patch.object(service, 'refresh_stock_cache') as mock_refresh:
            await service._ensure_stock_cache()
            
            mock_refresh.assert_not_called()
    
    def test_generate_company_name_variations(self, service):
        """Test company name variation generation."""
        # Test Japanese company name
        variations = service._generate_company_name_variations("トヨタ自動車株式会社")
        assert "トヨタ自動車株式会社" in variations
        assert "トヨタ自動車" in variations
        assert "トヨタ" in variations
        
        # Test English company name
        variations = service._generate_company_name_variations("Toyota Motor Corporation")
        assert "Toyota Motor Corporation" in variations
        assert "Toyota Motor" in variations
        assert "Toyo" in variations
        
        # Test short name
        variations = service._generate_company_name_variations("ABC")
        assert variations == ["ABC"]  # No variations for short names
    
    def test_get_sector_keywords(self, service):
        """Test sector keyword mapping."""
        auto_keywords = service._get_sector_keywords("自動車")
        assert "自動車" in auto_keywords
        assert "car" in auto_keywords
        
        electronics_keywords = service._get_sector_keywords("電機")
        assert "電機" in electronics_keywords
        assert "electronics" in electronics_keywords
        
        unknown_keywords = service._get_sector_keywords("未知のセクター")
        assert unknown_keywords == []
    
    def test_calculate_relevance_score_direct_ticker_match(self, service, sample_stocks):
        """Test relevance score calculation with direct ticker match."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_text = "トヨタ自動車(7203)の決算が発表されました"
        stock = sample_stocks[0]  # Toyota
        
        score = service._calculate_relevance_score(article_text.lower(), "7203", stock)
        
        # Should get high score for direct ticker + company name match
        assert score >= 0.7  # 0.4 for ticker + 0.3 for company name
    
    def test_calculate_relevance_score_company_name_match(self, service, sample_stocks):
        """Test relevance score calculation with company name match."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_text = "ソニーグループの業績が好調です"
        stock = sample_stocks[1]  # Sony
        
        score = service._calculate_relevance_score(article_text.lower(), "6758", stock)
        
        # Should get score for company name match
        assert score >= 0.3
    
    def test_calculate_relevance_score_financial_keywords_boost(self, service, sample_stocks):
        """Test relevance score boost from financial keywords."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_text = "トヨタ自動車(7203)の決算発表、売上高と利益が増加"
        stock = sample_stocks[0]  # Toyota
        
        score = service._calculate_relevance_score(article_text.lower(), "7203", stock)
        
        # Should get boost from financial keywords (決算, 売上, 利益)
        assert score >= 0.8  # Base score + financial keyword boost
    
    def test_calculate_relevance_score_sector_boost(self, service, sample_stocks):
        """Test relevance score boost from sector keywords."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_text = "トヨタ自動車(7203)の新しい自動車モデルが発表"
        stock = sample_stocks[0]  # Toyota (自動車 sector)
        
        score = service._calculate_relevance_score(article_text.lower(), "7203", stock)
        
        # Should get boost from sector keyword (自動車)
        assert score >= 0.8  # Base score + sector boost
    
    def test_calculate_relevance_score_no_match(self, service, sample_stocks):
        """Test relevance score calculation with no matches."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_text = "全く関係のないニュース記事です"
        stock = sample_stocks[0]  # Toyota
        
        score = service._calculate_relevance_score(article_text.lower(), "7203", stock)
        
        assert score == 0.0
    
    def test_find_stock_matches(self, service, sample_stocks):
        """Test finding stock matches in article text."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_text = "トヨタ自動車(7203)とソニーグループの業績について"
        
        matches = service._find_stock_matches(article_text)
        
        # Should find matches for both Toyota and Sony
        tickers = [match[0] for match in matches]
        assert "7203" in tickers
        assert "6758" in tickers
        
        # Should be sorted by relevance score
        assert matches[0][1] >= matches[1][1]
    
    @pytest.mark.asyncio
    async def test_create_stock_news_links_success(self, service, sample_stocks):
        """Test successful creation of stock-news links."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_id = "test-article-id"
        article_text = "トヨタ自動車(7203)の決算発表"
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock no existing links
            mock_existing_result = Mock()
            mock_existing_result.scalars.return_value.first.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_existing_result)
            
            mock_db.add = Mock()
            mock_db.commit = AsyncMock()
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            links = await service.create_stock_news_links(article_id, article_text)
            
            assert len(links) > 0
            assert any(link["ticker"] == "7203" for link in links)
            mock_db.add.assert_called()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_stock_news_links_existing_links(self, service, sample_stocks):
        """Test handling of existing stock-news links."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_id = "test-article-id"
        article_text = "トヨタ自動車(7203)の決算発表"
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock existing links found
            mock_existing_result = Mock()
            mock_existing_link = Mock()
            mock_existing_result.scalars.return_value.first.return_value = mock_existing_link
            mock_db.execute = AsyncMock(return_value=mock_existing_result)
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            links = await service.create_stock_news_links(article_id, article_text)
            
            # Should return empty list when links already exist
            assert links == []
    
    @pytest.mark.asyncio
    async def test_create_stock_news_links_force_refresh(self, service, sample_stocks):
        """Test force refresh of existing stock-news links."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_id = "test-article-id"
        article_text = "トヨタ自動車(7203)の決算発表"
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.execute = AsyncMock()
            mock_db.add = Mock()
            mock_db.commit = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            links = await service.create_stock_news_links(
                article_id, article_text, force_refresh=True
            )
            
            # Should create links even if they exist
            assert len(links) > 0
            mock_db.add.assert_called()
    
    @pytest.mark.asyncio
    async def test_batch_create_links_for_articles(self, service, sample_stocks):
        """Test batch creation of stock-news links."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_ids = ["article-1", "article-2", "article-3"]
        
        # Mock articles in database
        mock_articles = [
            Mock(id="article-1", headline="トヨタ自動車(7203)の決算", content_summary=""),
            Mock(id="article-2", headline="ソニーグループの業績", content_summary=""),
            Mock(id="article-3", headline="一般的なニュース", content_summary="")
        ]
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_articles
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # Mock create_stock_news_links method
            with patch.object(service, 'create_stock_news_links') as mock_create:
                mock_create.side_effect = [
                    [{"ticker": "7203", "relevance_score": 0.8}],  # Article 1
                    [{"ticker": "6758", "relevance_score": 0.7}],  # Article 2
                    []  # Article 3 (no matches)
                ]
                
                stats = await service.batch_create_links_for_articles(article_ids)
                
                assert stats["total_processed"] == 3
                assert stats["total_links_created"] == 2
                assert stats["errors"] == 0
                assert stats["success_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_get_news_for_stock(self, service):
        """Test getting news for a specific stock."""
        ticker = "7203"
        
        # Mock database query results
        mock_article = Mock()
        mock_article.id = "test-id"
        mock_article.headline = "Test Article"
        mock_article.content_summary = "Test content"
        mock_article.source = "Test Source"
        mock_article.author = "Test Author"
        mock_article.published_at = "2024-01-01T12:00:00"
        mock_article.article_url = "https://example.com/test"
        mock_article.language = "ja"
        mock_article.sentiment_label = "positive"
        mock_article.sentiment_score = 0.8
        
        mock_relevance_score = 0.9
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.all.return_value = [(mock_article, mock_relevance_score)]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            articles = await service.get_news_for_stock(ticker, limit=10)
            
            assert len(articles) == 1
            assert articles[0]["headline"] == "Test Article"
            assert articles[0]["relevance_score"] == 0.9
            assert articles[0]["sentiment_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_get_stocks_mentioned_in_article(self, service):
        """Test getting stocks mentioned in an article."""
        article_id = "test-article-id"
        
        # Mock database query results
        mock_stock = Mock()
        mock_stock.ticker = "7203"
        mock_stock.company_name_jp = "トヨタ自動車"
        mock_stock.company_name_en = "Toyota Motor"
        mock_stock.sector_jp = "自動車"
        mock_stock.industry_jp = "自動車製造"
        
        mock_relevance_score = 0.8
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.all.return_value = [(mock_stock, mock_relevance_score)]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            stocks = await service.get_stocks_mentioned_in_article(article_id)
            
            assert len(stocks) == 1
            assert stocks[0]["ticker"] == "7203"
            assert stocks[0]["company_name_jp"] == "トヨタ自動車"
            assert stocks[0]["relevance_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_update_relevance_scores(self, service, sample_stocks):
        """Test updating relevance scores for an article."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        
        article_id = "test-article-id"
        
        # Mock article with stock links
        mock_article = Mock()
        mock_article.id = article_id
        mock_article.headline = "トヨタ自動車(7203)の決算発表"
        mock_article.content_summary = "業績が好調"
        
        mock_link = Mock()
        mock_link.ticker = "7203"
        mock_link.relevance_score = 0.5  # Old score
        mock_article.stock_links = [mock_link]
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_article
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            updated_count = await service.update_relevance_scores(article_id, force_recalculate=True)
            
            assert updated_count == 1
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_mapping_statistics(self, service):
        """Test getting mapping statistics."""
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            
            # Mock various database queries
            mock_db.execute = AsyncMock(side_effect=[
                Mock(scalar=Mock(return_value=100)),  # Total articles
                Mock(scalar=Mock(return_value=80)),   # Linked articles
                Mock(scalar=Mock(return_value=150)),  # Total links
                Mock(scalar=Mock(return_value=0.75)), # Average relevance
                Mock(all=Mock(return_value=[("7203", 25), ("6758", 20)]))  # Top stocks
            ])
            
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            service._stock_cache = {"7203": Mock(), "6758": Mock()}
            service._cache_last_updated = datetime.utcnow()
            
            stats = await service.get_mapping_statistics()
            
            assert stats["total_articles"] == 100
            assert stats["linked_articles"] == 80
            assert stats["linking_rate"] == 0.8
            assert stats["total_links"] == 150
            assert stats["avg_links_per_article"] == 1.875
            assert stats["avg_relevance_score"] == 0.75
            assert len(stats["top_stocks_by_news"]) == 2
            assert stats["cache_size"] == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_database_error(self, service):
        """Test error handling for database errors."""
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.execute = AsyncMock(side_effect=Exception("Database error"))
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # Test various methods handle database errors gracefully
            result = await service.get_news_for_stock("7203")
            assert result == []
            
            result = await service.get_stocks_mentioned_in_article("article-id")
            assert result == []
            
            result = await service.update_relevance_scores("article-id")
            assert result == 0
            
            result = await service.get_mapping_statistics()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_minimum_relevance_threshold_filtering(self, service, sample_stocks):
        """Test that links below minimum relevance threshold are not created."""
        service._stock_cache = {stock.ticker: stock for stock in sample_stocks}
        service.min_relevance_threshold = 0.5  # Set high threshold
        
        article_id = "test-article-id"
        article_text = "一般的なニュース記事"  # Low relevance text
        
        with patch('app.services.news_stock_mapping_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_existing_result = Mock()
            mock_existing_result.scalars.return_value.first.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_existing_result)
            mock_db.add = Mock()
            mock_db.commit = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            links = await service.create_stock_news_links(article_id, article_text)
            
            # Should not create any links due to low relevance
            assert len(links) == 0
            mock_db.add.assert_not_called()
    
    def test_global_service_instance(self):
        """Test that global service instance exists."""
        assert news_stock_mapping_service is not None
        assert isinstance(news_stock_mapping_service, NewsStockMappingService)
    
    @pytest.mark.asyncio
    async def test_cache_ttl_behavior(self, service, sample_stocks):
        """Test cache TTL behavior."""
        # Test fresh cache
        service._cache_last_updated = datetime.utcnow()
        service._stock_cache = {"7203": sample_stocks[0]}
        
        with patch.object(service, 'refresh_stock_cache') as mock_refresh:
            await service._ensure_stock_cache()
            mock_refresh.assert_not_called()
        
        # Test expired cache
        service._cache_last_updated = datetime.utcnow() - timedelta(seconds=3700)
        
        with patch.object(service, 'refresh_stock_cache') as mock_refresh:
            mock_refresh.return_value = None
            await service._ensure_stock_cache()
            mock_refresh.assert_called_once()
    
    def test_japanese_text_processing(self, service):
        """Test Japanese text processing capabilities."""
        # Test company name variations
        variations = service._generate_company_name_variations("トヨタ自動車株式会社")
        assert "トヨタ自動車" in variations
        assert "トヨタ" in variations
        
        # Test financial keywords detection
        assert "決算" in service._financial_keywords
        assert "売上" in service._financial_keywords
        assert "利益" in service._financial_keywords
        
        # Test sector keywords
        auto_keywords = service._get_sector_keywords("自動車")
        assert "自動車" in auto_keywords
        assert "car" in auto_keywords