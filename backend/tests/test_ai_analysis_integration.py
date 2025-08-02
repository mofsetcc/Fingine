"""
Integration tests for AI analysis pipeline.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.services.ai_analysis_service import AIAnalysisService, AIAnalysisRequest
from app.models.analysis import AIAnalysisCache
from app.models.stock import Stock, StockPriceHistory
from app.models.financial import FinancialReport, FinancialReportLineItem
from app.models.news import NewsArticle, StockNewsLink


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.add = Mock()
    db.commit = Mock()
    return db


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing."""
    return Stock(
        ticker="7203",
        company_name_jp="トヨタ自動車",
        company_name_en="Toyota Motor Corporation",
        sector_jp="自動車",
        industry_jp="自動車製造",
        is_active=True
    )


@pytest.fixture
def sample_price_data():
    """Sample price history data."""
    base_date = date.today() - timedelta(days=30)
    price_data = []
    
    for i in range(30):
        price_data.append(StockPriceHistory(
            ticker="7203",
            date=base_date + timedelta(days=i),
            open=2000 + i,
            high=2010 + i,
            low=1990 + i,
            close=2005 + i,
            volume=1000000 + (i * 10000)
        ))
    
    return price_data


@pytest.fixture
def sample_financial_data():
    """Sample financial report data."""
    report = FinancialReport(
        ticker="7203",
        fiscal_year=2024,
        fiscal_period="Q1",
        report_type="quarterly",
        announced_at=datetime.now()
    )
    
    line_items = [
        FinancialReportLineItem(
            report_id=report.id,
            metric_name="revenue",
            metric_value=1000000000,
            unit="JPY"
        ),
        FinancialReportLineItem(
            report_id=report.id,
            metric_name="net_income",
            metric_value=50000000,
            unit="JPY"
        )
    ]
    
    return report, line_items


@pytest.fixture
def sample_news_data():
    """Sample news data."""
    article = NewsArticle(
        headline="トヨタ自動車、好決算を発表",
        content_summary="トヨタ自動車が第1四半期の好調な業績を発表",
        source="日経新聞",
        published_at=datetime.now(),
        sentiment_label="positive",
        sentiment_score=0.8
    )
    
    link = StockNewsLink(
        article_id=article.id,
        ticker="7203",
        relevance_score=0.9
    )
    
    return article, link


class TestAIAnalysisServiceIntegration:
    """Integration tests for AI analysis service."""
    
    @pytest.fixture
    def ai_service(self, mock_db):
        """Create AI analysis service with mocked dependencies."""
        with patch('app.services.ai_analysis_service.settings') as mock_settings:
            mock_settings.GOOGLE_GEMINI_API_KEY = "test_key"
            mock_settings.DAILY_AI_BUDGET_USD = 100.0
            mock_settings.MONTHLY_AI_BUDGET_USD = 2500.0
            
            service = AIAnalysisService(mock_db)
            return service
    
    @pytest.mark.asyncio
    async def test_complete_analysis_pipeline_short_term(
        self, 
        ai_service, 
        mock_db,
        sample_stock_data,
        sample_price_data,
        sample_news_data
    ):
        """Test complete short-term analysis pipeline."""
        # Setup mock data
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = sample_price_data
        
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "rating": "Bullish",
            "confidence": 0.8,
            "key_factors": ["Strong technical momentum", "Positive volume trend"],
            "price_target_range": {"min": 2100, "max": 2200},
            "risk_factors": ["Market volatility"],
            "technical_outlook": "Positive short-term trend",
            "reasoning": "Technical indicators show bullish momentum"
        }
        ```'''
        
        with patch.object(ai_service.gemini_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            with patch.object(ai_service.cost_manager, 'can_afford', new=AsyncMock(return_value=True)):
                with patch.object(ai_service.cost_manager, 'record_usage', new=AsyncMock()):
                    
                    # Execute analysis
                    request = AIAnalysisRequest(
                        ticker="7203",
                        analysis_type="short_term",
                        force_refresh=False
                    )
                    
                    result = await ai_service.generate_analysis(request, "test_user_id")
                    
                    # Verify result structure
                    assert "result" in result
                    assert "analysis_metadata" in result
                    assert "confidence_metrics" in result
                    assert "risk_assessment" in result
                    assert "validation" in result
                    
                    # Verify analysis content
                    analysis_result = result["result"]
                    assert analysis_result["rating"] == "Bullish"
                    assert analysis_result["confidence"] == 0.8
                    assert len(analysis_result["key_factors"]) == 2
                    
                    # Verify metadata
                    metadata = result["analysis_metadata"]
                    assert metadata["ticker"] == "7203"
                    assert metadata["analysis_type"] == "short_term"
                    assert "data_sources_used" in metadata
                    
                    # Verify caching was called
                    mock_db.add.assert_called()
                    mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_cached_analysis_retrieval(
        self, 
        ai_service, 
        mock_db
    ):
        """Test retrieval of cached analysis."""
        # Setup cached analysis
        cached_analysis = AIAnalysisCache(
            ticker="7203",
            analysis_date=date.today(),
            analysis_type="short_term",
            model_version="gemini-pro",
            analysis_result={
                "rating": "Bullish",
                "confidence": 0.8,
                "key_factors": ["Cached analysis"]
            },
            confidence_score=0.8,
            processing_time_ms=1500,
            cost_usd=0.005,
            created_at=datetime.now()
        )
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = cached_analysis
        
        with patch.object(ai_service.cost_manager, 'should_use_cache', new=AsyncMock(return_value=True)):
            
            request = AIAnalysisRequest(
                ticker="7203",
                analysis_type="short_term",
                force_refresh=False
            )
            
            result = await ai_service.generate_analysis(request, "test_user_id")
            
            # Verify cached result
            assert result["from_cache"] is True
            assert result["result"]["rating"] == "Bullish"
            assert "cache_age_seconds" in result
    
    @pytest.mark.asyncio
    async def test_multi_source_data_aggregation(
        self, 
        ai_service,
        mock_db,
        sample_price_data,
        sample_financial_data,
        sample_news_data
    ):
        """Test multi-source data aggregation for comprehensive analysis."""
        # Setup mock data for different sources
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            sample_price_data,  # Price data query
            [sample_financial_data[0]],  # Financial reports query
            [sample_news_data[0]]  # News articles query
        ]
        
        # Mock financial line items query
        mock_db.query.return_value.filter.return_value.all.return_value = sample_financial_data[1]
        
        # Test data aggregation
        context = await ai_service._aggregate_multi_source_data("7203", "comprehensive")
        
        # Verify context contains all expected data sources
        assert "ticker" in context
        assert "analysis_type" in context
        assert "company_name" in context
        assert "data_sources" in context
        assert "data_quality" in context
        
        # Verify data sources were included
        data_sources = context["data_sources"]
        expected_sources = [
            "technical_indicators", "momentum_analysis", "fundamental_data",
            "growth_analysis", "news_sentiment", "market_context"
        ]
        
        for source in expected_sources:
            assert source in data_sources
    
    @pytest.mark.asyncio
    async def test_analysis_validation_and_error_handling(
        self, 
        ai_service, 
        mock_db
    ):
        """Test analysis validation and error handling."""
        # Mock invalid Gemini response
        mock_response = Mock()
        mock_response.text = "Invalid JSON response"
        
        with patch.object(ai_service.gemini_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            with patch.object(ai_service.cost_manager, 'can_afford', new=AsyncMock(return_value=True)):
                with patch.object(ai_service.cost_manager, 'record_usage', new=AsyncMock()):
                    
                    request = AIAnalysisRequest(
                        ticker="7203",
                        analysis_type="short_term",
                        force_refresh=True
                    )
                    
                    result = await ai_service.generate_analysis(request, "test_user_id")
                    
                    # Verify error handling
                    analysis_result = result["result"]
                    assert analysis_result["format"] == "text"
                    assert analysis_result["parsed"] is False
                    
                    # Verify validation caught the issue
                    validation = result["validation"]
                    assert validation["is_valid"] is False
                    assert len(validation["validation_errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_cost_management_integration(
        self, 
        ai_service, 
        mock_db
    ):
        """Test cost management integration."""
        # Mock budget exceeded scenario
        with patch.object(ai_service.cost_manager, 'can_afford', new=AsyncMock(return_value=False)):
            
            request = AIAnalysisRequest(
                ticker="7203",
                analysis_type="comprehensive",
                force_refresh=True
            )
            
            # Should raise budget exception
            with pytest.raises(Exception) as exc_info:
                await ai_service.generate_analysis(request, "test_user_id")
            
            assert "budget" in str(exc_info.value).lower() or "insufficient" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_different_analysis_types(
        self, 
        ai_service, 
        mock_db
    ):
        """Test different analysis types generate appropriate contexts."""
        analysis_types = ["short_term", "mid_term", "long_term", "comprehensive"]
        
        for analysis_type in analysis_types:
            # Mock successful response
            mock_response = Mock()
            mock_response.text = f'''```json
            {{
                "rating": "Neutral",
                "confidence": 0.7,
                "key_factors": ["{analysis_type} analysis factor"],
                "reasoning": "{analysis_type} analysis reasoning"
            }}
            ```'''
            
            with patch.object(ai_service.gemini_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
                with patch.object(ai_service.cost_manager, 'can_afford', new=AsyncMock(return_value=True)):
                    with patch.object(ai_service.cost_manager, 'record_usage', new=AsyncMock()):
                        
                        request = AIAnalysisRequest(
                            ticker="7203",
                            analysis_type=analysis_type,
                            force_refresh=True
                        )
                        
                        result = await ai_service.generate_analysis(request, "test_user_id")
                        
                        # Verify analysis type specific result
                        assert result["analysis_metadata"]["analysis_type"] == analysis_type
                        assert analysis_type in result["result"]["key_factors"][0]
    
    @pytest.mark.asyncio
    async def test_confidence_and_risk_assessment(
        self, 
        ai_service, 
        mock_db
    ):
        """Test confidence metrics and risk assessment calculation."""
        # Mock high confidence response
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "rating": "Strong Bullish",
            "confidence": 0.95,
            "key_factors": ["Very strong fundamentals", "Excellent technical setup"],
            "reasoning": "High confidence analysis"
        }
        ```'''
        
        with patch.object(ai_service.gemini_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            with patch.object(ai_service.cost_manager, 'can_afford', new=AsyncMock(return_value=True)):
                with patch.object(ai_service.cost_manager, 'record_usage', new=AsyncMock()):
                    
                    request = AIAnalysisRequest(
                        ticker="7203",
                        analysis_type="short_term",
                        force_refresh=True
                    )
                    
                    result = await ai_service.generate_analysis(request, "test_user_id")
                    
                    # Verify confidence metrics
                    confidence_metrics = result["confidence_metrics"]
                    assert "data_confidence" in confidence_metrics
                    assert "model_confidence" in confidence_metrics
                    assert "overall_confidence" in confidence_metrics
                    assert confidence_metrics["model_confidence"] == 0.95
                    
                    # Verify risk assessment
                    risk_assessment = result["risk_assessment"]
                    assert "data_risks" in risk_assessment
                    assert "model_risks" in risk_assessment
                    assert "market_risks" in risk_assessment
                    assert "overall_risk_level" in risk_assessment
    
    @pytest.mark.asyncio
    async def test_analysis_enhancement_and_metadata(
        self, 
        ai_service, 
        mock_db
    ):
        """Test analysis result enhancement and metadata addition."""
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "rating": "Bullish",
            "confidence": 0.8,
            "key_factors": ["Factor 1", "Factor 2"],
            "price_target_range": {"min": 2000, "max": 2100}
        }
        ```'''
        
        with patch.object(ai_service.gemini_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            with patch.object(ai_service.cost_manager, 'can_afford', new=AsyncMock(return_value=True)):
                with patch.object(ai_service.cost_manager, 'record_usage', new=AsyncMock()):
                    
                    request = AIAnalysisRequest(
                        ticker="7203",
                        analysis_type="mid_term",
                        force_refresh=True
                    )
                    
                    result = await ai_service.generate_analysis(request, "test_user_id")
                    
                    # Verify enhanced structure
                    required_keys = [
                        "result", "analysis_metadata", "confidence_metrics",
                        "risk_assessment", "validation"
                    ]
                    
                    for key in required_keys:
                        assert key in result
                    
                    # Verify metadata completeness
                    metadata = result["analysis_metadata"]
                    required_metadata = [
                        "ticker", "analysis_type", "data_sources_used",
                        "data_quality_score", "analysis_timestamp",
                        "model_version", "processing_time_ms"
                    ]
                    
                    for key in required_metadata:
                        assert key in metadata
                    
                    # Verify validation results
                    validation = result["validation"]
                    assert "is_valid" in validation
                    assert "validation_errors" in validation
                    assert "validation_warnings" in validation


class TestAIAnalysisAPIIntegration:
    """Integration tests for AI analysis API endpoints."""
    
    @pytest.mark.asyncio
    async def test_api_endpoint_integration(self):
        """Test API endpoint integration with AI service."""
        # This would test the actual API endpoints
        # For now, we'll test the service integration
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])