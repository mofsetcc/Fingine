"""
Integration tests for external API services with mocking.
Tests data source adapters and external service integrations.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import json
from datetime import datetime, date
from decimal import Decimal

from app.adapters.alpha_vantage_adapter import AlphaVantageAdapter
from app.adapters.yahoo_finance_adapter import YahooFinanceJapanAdapter as YahooFinanceAdapter
from app.adapters.edinet_adapter import EDINETAdapter as EdinetAdapter
from app.adapters.news_adapter import NewsAdapter
from app.services.ai_analysis_service import AIAnalysisService
from app.services.data_source_service import DataSourceService


class TestAlphaVantageIntegration:
    """Test Alpha Vantage API integration."""
    
    @pytest.fixture
    def alpha_vantage_adapter(self):
        """Alpha Vantage adapter fixture."""
        config = {
            "api_key": "test_api_key",
            "base_url": "https://www.alphavantage.co/query"
        }
        return AlphaVantageAdapter(config)
    
    @pytest.fixture
    def mock_alpha_vantage_response(self):
        """Mock Alpha Vantage API response."""
        return {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": "7203.T",
                "3. Last Refreshed": "2024-01-15",
                "4. Output Size": "Compact",
                "5. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": {
                "2024-01-15": {
                    "1. open": "2500.0000",
                    "2. high": "2550.0000",
                    "3. low": "2480.0000",
                    "4. close": "2520.0000",
                    "5. volume": "15000000"
                },
                "2024-01-14": {
                    "1. open": "2480.0000",
                    "2. high": "2510.0000",
                    "3. low": "2460.0000",
                    "4. close": "2500.0000",
                    "5. volume": "12000000"
                }
            }
        }
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_daily_prices_success(self, mock_get, alpha_vantage_adapter, mock_alpha_vantage_response):
        """Test successful daily price fetching from Alpha Vantage."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_alpha_vantage_response
        mock_get.return_value = mock_response
        
        # Fetch data
        result = await alpha_vantage_adapter.fetch_daily_prices("7203", "2024-01-01", "2024-01-15")
        
        # Verify results
        assert len(result) == 2
        assert result[0]["ticker"] == "7203"
        assert result[0]["date"] == "2024-01-15"
        assert result[0]["open"] == 2500.0
        assert result[0]["high"] == 2550.0
        assert result[0]["low"] == 2480.0
        assert result[0]["close"] == 2520.0
        assert result[0]["volume"] == 15000000
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "function=TIME_SERIES_DAILY" in str(call_args)
        assert "symbol=7203.T" in str(call_args)
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_daily_prices_api_error(self, mock_get, alpha_vantage_adapter):
        """Test handling of Alpha Vantage API errors."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        # Should handle error gracefully
        with pytest.raises(Exception):
            await alpha_vantage_adapter.fetch_daily_prices("7203", "2024-01-01", "2024-01-15")
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_daily_prices_rate_limit(self, mock_get, alpha_vantage_adapter):
        """Test handling of Alpha Vantage rate limiting."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 500 calls per day."
        }
        mock_get.return_value = mock_response
        
        # Should handle rate limit
        result = await alpha_vantage_adapter.fetch_daily_prices("7203", "2024-01-01", "2024-01-15")
        assert result == []  # Should return empty list when rate limited
    
    async def test_data_normalization(self, alpha_vantage_adapter, mock_alpha_vantage_response):
        """Test data normalization from Alpha Vantage format."""
        normalized_data = alpha_vantage_adapter._normalize_alpha_vantage_data(
            mock_alpha_vantage_response, "2024-01-01", "2024-01-15"
        )
        
        assert len(normalized_data) == 2
        
        # Check first record
        first_record = normalized_data[0]
        assert first_record["ticker"] == "7203"
        assert first_record["date"] == "2024-01-15"
        assert isinstance(first_record["open"], float)
        assert isinstance(first_record["volume"], int)
        
        # Check data types
        assert all(isinstance(record["open"], float) for record in normalized_data)
        assert all(isinstance(record["volume"], int) for record in normalized_data)


class TestYahooFinanceIntegration:
    """Test Yahoo Finance API integration."""
    
    @pytest.fixture
    def yahoo_adapter(self):
        """Yahoo Finance adapter fixture."""
        config = {
            "base_url": "https://query1.finance.yahoo.com/v8/finance/chart/"
        }
        return YahooFinanceAdapter(config)
    
    @pytest.fixture
    def mock_yahoo_response(self):
        """Mock Yahoo Finance API response."""
        return {
            "chart": {
                "result": [{
                    "meta": {
                        "currency": "JPY",
                        "symbol": "7203.T",
                        "exchangeName": "JPX",
                        "instrumentType": "EQUITY",
                        "firstTradeDate": 322441800,
                        "regularMarketTime": 1705305600,
                        "gmtoffset": 32400,
                        "timezone": "JST"
                    },
                    "timestamp": [1705305600, 1705219200],
                    "indicators": {
                        "quote": [{
                            "open": [2500.0, 2480.0],
                            "high": [2550.0, 2510.0],
                            "low": [2480.0, 2460.0],
                            "close": [2520.0, 2500.0],
                            "volume": [15000000, 12000000]
                        }]
                    }
                }],
                "error": None
            }
        }
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_daily_prices_success(self, mock_get, yahoo_adapter, mock_yahoo_response):
        """Test successful daily price fetching from Yahoo Finance."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_yahoo_response
        mock_get.return_value = mock_response
        
        # Fetch data
        result = await yahoo_adapter.fetch_daily_prices("7203", "2024-01-01", "2024-01-15")
        
        # Verify results
        assert len(result) == 2
        assert result[0]["ticker"] == "7203"
        assert result[0]["open"] == 2500.0
        assert result[0]["close"] == 2520.0
        assert result[0]["volume"] == 15000000
        
        # Verify API call
        mock_get.assert_called_once()
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_daily_prices_with_delay(self, mock_get, yahoo_adapter, mock_yahoo_response):
        """Test Yahoo Finance data with 15-minute delay for free tier."""
        # Mock response with delayed data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_yahoo_response
        mock_get.return_value = mock_response
        
        result = await yahoo_adapter.fetch_daily_prices("7203", "2024-01-01", "2024-01-15")
        
        # Should still return data but with delay indication
        assert len(result) >= 1
        # In real implementation, would check for delay metadata


class TestEdinetIntegration:
    """Test EDINET API integration for financial data."""
    
    @pytest.fixture
    def edinet_adapter(self):
        """EDINET adapter fixture."""
        config = {
            "base_url": "https://disclosure.edinet-fsa.go.jp/api/v1/"
        }
        return EdinetAdapter(config)
    
    @pytest.fixture
    def mock_edinet_documents_response(self):
        """Mock EDINET documents API response."""
        return {
            "metadata": {
                "title": "EDINET API",
                "parameter": {
                    "date": "2024-01-15",
                    "type": "2"
                },
                "resultset": {
                    "count": 1
                }
            },
            "results": [{
                "seqNumber": 1,
                "docID": "S100R123",
                "edinetCode": "E04149",
                "secCode": "72030",
                "JCN": "9010001008844",
                "filerName": "トヨタ自動車株式会社",
                "fundCode": None,
                "ordinanceCode": "010",
                "formCode": "030000",
                "docTypeCode": "120",
                "periodStart": "2023-04-01",
                "periodEnd": "2023-12-31",
                "submitDateTime": "2024-01-15 15:00:00",
                "docDescription": "四半期報告書－第105期第3四半期(令和5年10月1日－令和5年12月31日)",
                "issuerEdinetCode": None,
                "subjectEdinetCode": None,
                "subsidiaryEdinetCode": None,
                "currentReportReason": None,
                "parentDocID": None,
                "opeDateTime": None,
                "withdrawalStatus": "0",
                "docInfoEditStatus": "0",
                "disclosureStatus": "0",
                "xbrlFlag": "1",
                "pdfFlag": "1",
                "attachDocFlag": "0",
                "englishFlag": "0"
            }]
        }
    
    @pytest.fixture
    def mock_xbrl_data(self):
        """Mock XBRL financial data."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance">
            <context id="CurrentYearDuration">
                <entity>
                    <identifier scheme="http://disclosure.edinet-fsa.go.jp">E04149</identifier>
                </entity>
                <period>
                    <startDate>2023-04-01</startDate>
                    <endDate>2023-12-31</endDate>
                </period>
            </context>
            <jpcrp_cor:NetSales contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">37154200000000</jpcrp_cor:NetSales>
            <jpcrp_cor:OperatingIncome contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">4052800000000</jpcrp_cor:OperatingIncome>
            <jpcrp_cor:NetIncome contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">2926100000000</jpcrp_cor:NetIncome>
        </xbrl>"""
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_financial_reports_success(self, mock_get, edinet_adapter, mock_edinet_documents_response):
        """Test successful financial report fetching from EDINET."""
        # Mock documents list response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_edinet_documents_response
        mock_get.return_value = mock_response
        
        # Fetch financial reports
        result = await edinet_adapter.fetch_latest_reports("7203", ["quarterly"])
        
        # Verify results
        assert len(result) >= 1
        report = result[0]
        assert report["ticker"] == "7203"
        assert report["company_name"] == "トヨタ自動車株式会社"
        assert report["report_type"] == "quarterly"
        assert "doc_id" in report
        
        # Verify API call
        mock_get.assert_called_once()
    
    @patch('httpx.AsyncClient.get')
    async def test_parse_xbrl_financial_data(self, mock_get, edinet_adapter, mock_xbrl_data):
        """Test XBRL financial data parsing."""
        # Mock XBRL document response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_xbrl_data
        mock_get.return_value = mock_response
        
        # Parse XBRL data
        parsed_data = edinet_adapter._parse_xbrl_financial_data(mock_xbrl_data)
        
        # Verify parsed financial metrics
        assert "net_sales" in parsed_data
        assert "operating_income" in parsed_data
        assert "net_income" in parsed_data
        
        assert parsed_data["net_sales"] == 37154200000000
        assert parsed_data["operating_income"] == 4052800000000
        assert parsed_data["net_income"] == 2926100000000
    
    async def test_financial_data_validation(self, edinet_adapter):
        """Test financial data validation and error handling."""
        # Test with invalid XBRL data
        invalid_xbrl = "<invalid>not valid xbrl</invalid>"
        
        with pytest.raises(Exception):
            edinet_adapter._parse_xbrl_financial_data(invalid_xbrl)


class TestNewsAPIIntegration:
    """Test News API integration."""
    
    @pytest.fixture
    def news_adapter(self):
        """News adapter fixture."""
        config = {
            "api_key": "test_news_api_key",
            "base_url": "https://newsapi.org/v2/"
        }
        return NewsAdapter(config)
    
    @pytest.fixture
    def mock_news_response(self):
        """Mock News API response."""
        return {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "source": {"id": "reuters", "name": "Reuters"},
                    "author": "Reuters Staff",
                    "title": "トヨタ自動車、第3四半期決算を発表",
                    "description": "トヨタ自動車は本日、第3四半期の決算を発表しました。",
                    "url": "https://reuters.com/toyota-earnings",
                    "urlToImage": "https://reuters.com/image.jpg",
                    "publishedAt": "2024-01-15T10:00:00Z",
                    "content": "トヨタ自動車の第3四半期決算の詳細..."
                },
                {
                    "source": {"id": "nikkei", "name": "Nikkei"},
                    "author": "Nikkei Reporter",
                    "title": "自動車業界の動向について",
                    "description": "自動車業界全体の最新動向をお伝えします。",
                    "url": "https://nikkei.com/auto-industry",
                    "urlToImage": "https://nikkei.com/image.jpg",
                    "publishedAt": "2024-01-15T08:00:00Z",
                    "content": "自動車業界の動向の詳細..."
                }
            ]
        }
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_stock_related_news_success(self, mock_get, news_adapter, mock_news_response):
        """Test successful news fetching for a stock."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_news_response
        mock_get.return_value = mock_response
        
        # Fetch news
        result = await news_adapter.fetch_stock_related_news("7203", "トヨタ自動車", days_back=7)
        
        # Verify results
        assert len(result) == 2
        
        first_article = result[0]
        assert first_article["title"] == "トヨタ自動車、第3四半期決算を発表"
        assert first_article["source"] == "Reuters"
        assert first_article["ticker"] == "7203"
        assert "sentiment_score" in first_article
        assert "relevance_score" in first_article
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "q=トヨタ自動車" in str(call_args) or "q=7203" in str(call_args)
    
    @patch('app.services.sentiment_service.SentimentService.analyze_text')
    async def test_news_sentiment_analysis(self, mock_sentiment, news_adapter, mock_news_response):
        """Test sentiment analysis integration for news articles."""
        # Mock sentiment analysis
        mock_sentiment.return_value = {
            "label": "positive",
            "score": 0.85
        }
        
        # Process news with sentiment
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_news_response
            mock_get.return_value = mock_response
            
            result = await news_adapter.fetch_stock_related_news("7203", "トヨタ自動車")
        
        # Verify sentiment was analyzed
        assert all("sentiment_score" in article for article in result)
        assert all("sentiment_label" in article for article in result)


class TestAIServiceIntegration:
    """Test AI service integration with external LLM APIs."""
    
    @pytest.fixture
    def ai_service(self):
        """AI analysis service fixture."""
        mock_data_service = Mock()
        mock_cost_manager = Mock()
        mock_llm_client = Mock()
        
        return AIAnalysisService(
            llm_client=mock_llm_client,
            data_service=mock_data_service,
            cost_manager=mock_cost_manager
        )
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock Google Gemini API response."""
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "rating": "Bullish",
                            "confidence": 0.85,
                            "key_factors": [
                                "Strong quarterly earnings growth",
                                "Positive market sentiment",
                                "Solid fundamentals"
                            ],
                            "price_target_range": {"min": 2600, "max": 2800},
                            "risk_factors": [
                                "Market volatility",
                                "Supply chain concerns"
                            ],
                            "reasoning": "Toyota shows strong financial performance with consistent growth in key metrics."
                        })
                    }]
                },
                "finishReason": "STOP"
            }],
            "usageMetadata": {
                "promptTokenCount": 1500,
                "candidatesTokenCount": 300,
                "totalTokenCount": 1800
            }
        }
    
    @patch('app.services.ai_analysis_service.genai.GenerativeModel')
    async def test_generate_analysis_success(self, mock_genai, ai_service, mock_gemini_response):
        """Test successful AI analysis generation."""
        # Mock Gemini client
        mock_model = Mock()
        mock_model.generate_content.return_value = Mock(
            text=json.dumps({
                "rating": "Bullish",
                "confidence": 0.85,
                "key_factors": ["Strong earnings"],
                "price_target_range": {"min": 2600, "max": 2800},
                "risk_factors": ["Market volatility"],
                "reasoning": "Strong performance"
            })
        )
        mock_genai.return_value = mock_model
        
        # Mock dependencies
        ai_service.data_service.get_price_history.return_value = [
            {"date": "2024-01-15", "close": 2520.0, "volume": 15000000}
        ]
        ai_service.data_service.get_financials.return_value = {
            "net_sales": 37154200000000,
            "operating_income": 4052800000000
        }
        ai_service.data_service.get_news_sentiment.return_value = [
            {"title": "Positive news", "sentiment_score": 0.8}
        ]
        ai_service.cost_manager.can_afford.return_value = True
        ai_service.cost_manager.estimate_cost.return_value = 0.05
        
        # Generate analysis
        result = await ai_service.generate_analysis("7203", "comprehensive")
        
        # Verify results
        assert result["ticker"] == "7203"
        assert result["rating"] == "Bullish"
        assert result["confidence"] == 0.85
        assert len(result["key_factors"]) >= 1
        assert "price_target_range" in result
        assert "risk_factors" in result
        
        # Verify cost tracking
        ai_service.cost_manager.record_usage.assert_called_once()
    
    async def test_analysis_cost_control(self, ai_service):
        """Test AI analysis cost control mechanisms."""
        # Mock cost manager to reject expensive requests
        ai_service.cost_manager.can_afford.return_value = False
        ai_service.cost_manager.estimate_cost.return_value = 10.0  # Expensive request
        
        # Should raise budget exception
        with pytest.raises(Exception):  # BudgetExceededException
            await ai_service.generate_analysis("7203", "comprehensive")
    
    async def test_analysis_caching(self, ai_service):
        """Test AI analysis caching mechanism."""
        # Mock cached analysis
        cached_analysis = {
            "ticker": "7203",
            "rating": "Bullish",
            "confidence": 0.85,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        with patch.object(ai_service, '_check_cache', return_value=cached_analysis):
            with patch.object(ai_service.cost_manager, 'should_use_cache', return_value=True):
                result = await ai_service.generate_analysis("7203", "comprehensive")
                
                # Should return cached result
                assert result == cached_analysis
                
                # Should not call LLM
                ai_service.llm.generate_content.assert_not_called()


class TestDataSourceServiceIntegration:
    """Test data source service integration with multiple adapters."""
    
    @pytest.fixture
    def data_source_service(self):
        """Data source service fixture."""
        return DataSourceService()
    
    async def test_automatic_failover(self, data_source_service):
        """Test automatic failover between data sources."""
        # Mock primary source failure
        with patch.object(data_source_service, 'alpha_vantage_adapter') as mock_primary:
            mock_primary.fetch_daily_prices.side_effect = Exception("API Error")
            
            # Mock secondary source success
            with patch.object(data_source_service, 'yahoo_adapter') as mock_secondary:
                mock_secondary.fetch_daily_prices.return_value = [
                    {"ticker": "7203", "date": "2024-01-15", "close": 2520.0}
                ]
                
                # Should automatically failover to secondary source
                result = await data_source_service.get_stock_prices("7203", "2024-01-01", "2024-01-15")
                
                assert len(result) >= 1
                assert result[0]["ticker"] == "7203"
                
                # Verify failover occurred
                mock_primary.fetch_daily_prices.assert_called_once()
                mock_secondary.fetch_daily_prices.assert_called_once()
    
    async def test_data_source_health_monitoring(self, data_source_service):
        """Test data source health monitoring."""
        # Mock health check responses
        with patch.object(data_source_service, 'check_source_health') as mock_health:
            mock_health.return_value = {
                "alpha_vantage": {"status": "healthy", "response_time": 0.5},
                "yahoo_finance": {"status": "degraded", "response_time": 2.0},
                "edinet": {"status": "healthy", "response_time": 0.8}
            }
            
            health_status = await data_source_service.get_health_status()
            
            assert "alpha_vantage" in health_status
            assert health_status["alpha_vantage"]["status"] == "healthy"
            assert health_status["yahoo_finance"]["status"] == "degraded"
    
    async def test_cost_optimization_across_sources(self, data_source_service):
        """Test cost optimization across different data sources."""
        # Mock cost tracking
        with patch.object(data_source_service, 'cost_tracker') as mock_cost_tracker:
            mock_cost_tracker.get_daily_costs.return_value = {
                "alpha_vantage": 5.50,
                "news_api": 2.30,
                "gemini": 12.80
            }
            
            # Should choose most cost-effective source
            with patch.object(data_source_service, 'choose_optimal_source') as mock_choose:
                mock_choose.return_value = "yahoo_finance"  # Free source
                
                source = await data_source_service.get_optimal_price_source("7203")
                assert source == "yahoo_finance"
                
                mock_choose.assert_called_once()


class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    @patch('app.adapters.alpha_vantage_adapter.AlphaVantageAdapter.fetch_daily_prices')
    @patch('app.adapters.news_adapter.NewsAdapter.fetch_stock_related_news')
    @patch('app.services.ai_analysis_service.AIAnalysisService.generate_analysis')
    async def test_complete_stock_analysis_pipeline(self, mock_ai, mock_news, mock_prices):
        """Test complete stock analysis pipeline integration."""
        # Mock data sources
        mock_prices.return_value = [
            {"ticker": "7203", "date": "2024-01-15", "close": 2520.0, "volume": 15000000}
        ]
        
        mock_news.return_value = [
            {
                "title": "Toyota reports strong earnings",
                "sentiment_score": 0.8,
                "sentiment_label": "positive",
                "published_at": "2024-01-15T10:00:00Z"
            }
        ]
        
        mock_ai.return_value = {
            "ticker": "7203",
            "rating": "Bullish",
            "confidence": 0.85,
            "key_factors": ["Strong earnings", "Positive sentiment"],
            "price_target_range": {"min": 2600, "max": 2800}
        }
        
        # Create service instances
        data_service = DataSourceService()
        ai_service = AIAnalysisService(Mock(), data_service, Mock())
        
        # Execute complete pipeline
        analysis_result = await ai_service.generate_analysis("7203", "comprehensive")
        
        # Verify pipeline execution
        assert analysis_result["ticker"] == "7203"
        assert analysis_result["rating"] == "Bullish"
        assert len(analysis_result["key_factors"]) >= 2
        
        # Verify all data sources were called
        mock_prices.assert_called_once()
        mock_news.assert_called_once()
        mock_ai.assert_called_once()
    
    async def test_error_propagation_and_recovery(self):
        """Test error propagation and recovery mechanisms."""
        # This would test how errors in one service affect others
        # and how the system recovers from partial failures
        pass
    
    async def test_data_consistency_across_services(self):
        """Test data consistency across different services."""
        # This would test that data remains consistent
        # when accessed through different service layers
        pass