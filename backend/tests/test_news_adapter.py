"""
Tests for news data adapter.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

from app.adapters.news_adapter import NewsDataAdapter
from app.adapters.base import HealthStatus


class TestNewsDataAdapter:
    """Test cases for NewsDataAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create news adapter instance for testing."""
        config = {
            "news_api_key": "test_api_key"
        }
        return NewsDataAdapter(config=config)
    
    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session."""
        session = Mock()
        session.closed = False
        return session
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter):
        """Test successful health check."""
        with patch.object(adapter, '_test_news_api') as mock_news_api, \
             patch.object(adapter, '_test_rss_feeds') as mock_rss:
            
            mock_news_api.return_value = None
            mock_rss.return_value = None
            
            health = await adapter.health_check()
            
            assert health.status == HealthStatus.HEALTHY
            assert health.response_time_ms > 0
            assert health.error_message is None
            assert health.metadata["sources_tested"] == 5  # 1 News API + 4 RSS
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, adapter):
        """Test health check failure."""
        with patch.object(adapter, '_test_news_api') as mock_news_api:
            mock_news_api.side_effect = Exception("API unavailable")
            
            health = await adapter.health_check()
            
            assert health.status == HealthStatus.UNHEALTHY
            assert health.error_message == "API unavailable"
    
    @pytest.mark.asyncio
    async def test_get_news_api_articles_success(self, adapter):
        """Test successful News API article retrieval."""
        mock_response_data = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article",
                    "description": "Test description",
                    "url": "https://example.com/article1",
                    "publishedAt": "2024-01-01T12:00:00Z",
                    "source": {"name": "Test Source"},
                    "author": "Test Author"
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_session = Mock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(adapter, '_get_session', return_value=mock_session):
            articles = await adapter._get_news_api_articles(
                symbol="7203",
                keywords=["test"],
                limit=10,
                start_date=None,
                end_date=None
            )
            
            assert len(articles) == 1
            assert articles[0]["headline"] == "Test Article"
            assert articles[0]["source"] == "Test Source"
            assert articles[0]["source_type"] == "news_api"
    
    @pytest.mark.asyncio
    async def test_get_news_api_articles_error(self, adapter):
        """Test News API error handling."""
        mock_response = Mock()
        mock_response.status = 400
        
        mock_session = Mock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(adapter, '_get_session', return_value=mock_session):
            articles = await adapter._get_news_api_articles(
                symbol="7203",
                keywords=["test"],
                limit=10,
                start_date=None,
                end_date=None
            )
            
            assert articles == []
    
    @pytest.mark.asyncio
    async def test_get_rss_articles_success(self, adapter):
        """Test successful RSS article retrieval."""
        # Mock RSS feed content
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test RSS Article</title>
                    <description>Test RSS description</description>
                    <link>https://example.com/rss-article</link>
                    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    <author>RSS Author</author>
                </item>
            </channel>
        </rss>"""
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=rss_content)
        
        mock_session = Mock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(adapter, '_get_session', return_value=mock_session):
            articles = await adapter._get_rss_articles(
                symbol="7203",
                keywords=["test"],
                limit=10,
                start_date=None,
                end_date=None
            )
            
            assert len(articles) == 1
            assert articles[0]["headline"] == "Test RSS Article"
            assert articles[0]["source_type"] == "rss"
    
    def test_normalize_news_api_article(self, adapter):
        """Test News API article normalization."""
        raw_article = {
            "title": "Test Title",
            "description": "Test description",
            "url": "https://example.com/test",
            "publishedAt": "2024-01-01T12:00:00Z",
            "source": {"name": "Test Source"},
            "author": "Test Author"
        }
        
        normalized = adapter._normalize_news_api_article(raw_article)
        
        assert normalized["headline"] == "Test Title"
        assert normalized["content_summary"] == "Test description"
        assert normalized["source"] == "Test Source"
        assert normalized["author"] == "Test Author"
        assert normalized["published_at"] == "2024-01-01T12:00:00Z"
        assert normalized["article_url"] == "https://example.com/test"
        assert normalized["language"] == "ja"
        assert normalized["source_type"] == "news_api"
        assert "id" in normalized
    
    def test_normalize_rss_article_xml(self, adapter):
        """Test RSS article normalization from XML."""
        import xml.etree.ElementTree as ET
        
        # Create mock XML element
        xml_content = """
        <item>
            <title>RSS Test Title</title>
            <description><![CDATA[<p>RSS test description</p>]]></description>
            <link>https://example.com/rss-test</link>
            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            <author>RSS Author</author>
        </item>
        """
        
        item = ET.fromstring(xml_content)
        
        source = {
            "name": "Test RSS Source",
            "language": "ja"
        }
        
        normalized = adapter._normalize_rss_article_xml(item, source)
        
        assert normalized["headline"] == "RSS Test Title"
        assert normalized["content_summary"] == "RSS test description"  # HTML cleaned
        assert normalized["source"] == "Test RSS Source"
        assert normalized["author"] == "RSS Author"
        assert normalized["article_url"] == "https://example.com/rss-test"
        assert normalized["language"] == "ja"
        assert normalized["source_type"] == "rss"
        assert "id" in normalized
    
    def test_clean_html(self, adapter):
        """Test HTML cleaning functionality."""
        html_content = "<p>This is <strong>bold</strong> text with <a href='#'>link</a>.</p>"
        cleaned = adapter._clean_html(html_content)
        
        assert cleaned == "This is bold text with link."
        
        # Test long content truncation
        long_html = "<p>" + "A" * 600 + "</p>"
        cleaned_long = adapter._clean_html(long_html)
        
        assert len(cleaned_long) == 500
        assert cleaned_long.endswith("...")
    
    def test_generate_article_id(self, adapter):
        """Test article ID generation."""
        url1 = "https://example.com/article1"
        url2 = "https://example.com/article2"
        
        id1 = adapter._generate_article_id(url1)
        id2 = adapter._generate_article_id(url2)
        
        assert id1 != id2
        assert len(id1) == 32  # MD5 hash length
        assert len(id2) == 32
        
        # Same URL should generate same ID
        id1_again = adapter._generate_article_id(url1)
        assert id1 == id1_again
    
    def test_filter_article_by_date(self, adapter):
        """Test article filtering by date."""
        article = {
            "headline": "Test Article",
            "content_summary": "Test content",
            "published_at": "2024-01-01T12:00:00"
        }
        
        # Test start date filter
        start_date = datetime(2024, 1, 1, 10, 0, 0)
        assert adapter._filter_article(article, None, None, start_date, None) == True
        
        start_date = datetime(2024, 1, 1, 14, 0, 0)
        assert adapter._filter_article(article, None, None, start_date, None) == False
        
        # Test end date filter
        end_date = datetime(2024, 1, 1, 14, 0, 0)
        assert adapter._filter_article(article, None, None, None, end_date) == True
        
        end_date = datetime(2024, 1, 1, 10, 0, 0)
        assert adapter._filter_article(article, None, None, None, end_date) == False
    
    def test_filter_article_by_symbol(self, adapter):
        """Test article filtering by stock symbol."""
        article = {
            "headline": "Toyota reports strong earnings",
            "content_summary": "7203 stock rises after earnings",
            "published_at": "2024-01-01T12:00:00"
        }
        
        # Should match symbol in content
        assert adapter._filter_article(article, "7203", None, None, None) == True
        
        # Should not match different symbol
        assert adapter._filter_article(article, "6758", None, None, None) == False
    
    def test_filter_article_by_keywords(self, adapter):
        """Test article filtering by keywords."""
        article = {
            "headline": "Stock market rises",
            "content_summary": "Earnings season brings gains",
            "published_at": "2024-01-01T12:00:00"
        }
        
        # Should match keyword in headline
        assert adapter._filter_article(article, None, ["market"], None, None) == True
        
        # Should match keyword in content
        assert adapter._filter_article(article, None, ["earnings"], None, None) == True
        
        # Should not match missing keyword
        assert adapter._filter_article(article, None, ["technology"], None, None) == False
        
        # Should match at least one keyword
        assert adapter._filter_article(article, None, ["technology", "market"], None, None) == True
    
    def test_deduplicate_articles(self, adapter):
        """Test article deduplication."""
        articles = [
            {
                "id": "1",
                "headline": "Toyota reports strong earnings",
                "content_summary": "Content 1"
            },
            {
                "id": "2", 
                "headline": "Toyota reports strong earnings",  # Duplicate headline
                "content_summary": "Content 2"
            },
            {
                "id": "1",  # Duplicate ID
                "headline": "Different headline",
                "content_summary": "Content 3"
            },
            {
                "id": "3",
                "headline": "Unique headline",
                "content_summary": "Content 4"
            }
        ]
        
        deduplicated = adapter._deduplicate_articles(articles)
        
        # Should keep first occurrence of each unique article
        assert len(deduplicated) == 2
        assert deduplicated[0]["id"] == "1"
        assert deduplicated[1]["id"] == "3"
    
    def test_calculate_similarity(self, adapter):
        """Test text similarity calculation."""
        text1 = "toyota reports strong earnings"
        text2 = "toyota reports weak earnings"
        text3 = "sony announces new product"
        
        # Similar texts should have high similarity
        similarity1 = adapter._calculate_similarity(text1, text2)
        assert similarity1 > 0.5
        
        # Different texts should have low similarity
        similarity2 = adapter._calculate_similarity(text1, text3)
        assert similarity2 < 0.5
        
        # Identical texts should have similarity of 1.0
        similarity3 = adapter._calculate_similarity(text1, text1)
        assert similarity3 == 1.0
    
    def test_score_relevance(self, adapter):
        """Test article relevance scoring."""
        articles = [
            {
                "headline": "Toyota 7203 earnings strong",
                "content_summary": "Toyota reports good results",
                "source": "Nikkei",
                "published_at": datetime.utcnow().isoformat()
            },
            {
                "headline": "Market news",
                "content_summary": "General market update",
                "source": "Other Source",
                "published_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
        ]
        
        scored = adapter._score_relevance(articles, "7203", ["earnings"])
        
        # First article should have higher relevance score
        assert scored[0]["relevance_score"] > scored[1]["relevance_score"]
        
        # Nikkei source should get bonus
        assert scored[0]["relevance_score"] > 0.3  # Base Nikkei bonus
        
        # Symbol and keyword matches should increase score
        assert scored[0]["relevance_score"] > 0.5
    
    @pytest.mark.asyncio
    async def test_get_news_integration(self, adapter):
        """Test full get_news method integration."""
        # Mock both News API and RSS responses
        with patch.object(adapter, '_get_news_api_articles') as mock_news_api, \
             patch.object(adapter, '_get_rss_articles') as mock_rss:
            
            mock_news_api.return_value = [
                {
                    "id": "1",
                    "headline": "News API Article",
                    "content_summary": "From News API",
                    "source": "News API Source",
                    "published_at": datetime.utcnow().isoformat(),
                    "source_type": "news_api"
                }
            ]
            
            mock_rss.return_value = [
                {
                    "id": "2",
                    "headline": "RSS Article",
                    "content_summary": "From RSS",
                    "source": "RSS Source",
                    "published_at": datetime.utcnow().isoformat(),
                    "source_type": "rss"
                }
            ]
            
            articles = await adapter.get_news(
                symbol="7203",
                keywords=["test"],
                limit=10
            )
            
            assert len(articles) == 2
            assert any(article["source_type"] == "news_api" for article in articles)
            assert any(article["source_type"] == "rss" for article in articles)
            
            # All articles should have relevance scores
            for article in articles:
                assert "relevance_score" in article
                assert 0 <= article["relevance_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_close_session(self, adapter):
        """Test session cleanup."""
        # Create a mock session
        mock_session = Mock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        
        adapter._session = mock_session
        
        await adapter.close()
        
        mock_session.close.assert_called_once()
    
    def test_get_company_name_for_symbol_sync(self, adapter):
        """Test company name lookup."""
        # Test known symbols
        assert adapter._get_company_name_for_symbol_sync("7203") == "トヨタ自動車"
        assert adapter._get_company_name_for_symbol_sync("6758") == "ソニーグループ"
        
        # Test unknown symbol
        assert adapter._get_company_name_for_symbol_sync("UNKNOWN") is None
    
    @pytest.mark.asyncio
    async def test_rate_limit_info(self, adapter):
        """Test rate limit information."""
        rate_limit = await adapter.get_rate_limit_info()
        
        assert rate_limit.requests_per_minute == 5
        assert rate_limit.requests_per_hour == 100
        assert rate_limit.requests_per_day == 1000
        assert "minute" in rate_limit.current_usage
        assert "hour" in rate_limit.current_usage
        assert "day" in rate_limit.current_usage
    
    @pytest.mark.asyncio
    async def test_cost_info(self, adapter):
        """Test cost information."""
        cost_info = await adapter.get_cost_info()
        
        assert cost_info.cost_per_request == 0.0001  # Has API key
        assert cost_info.currency == "USD"
        assert cost_info.monthly_budget == 100.0
        assert cost_info.current_monthly_usage == 0.0
        
        # Test without API key
        adapter.news_api_key = None
        cost_info_free = await adapter.get_cost_info()
        assert cost_info_free.cost_per_request == 0.0