"""
Unit tests for GeminiAnalysisClient.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the dependencies that might not be available
with patch.dict('sys.modules', {
    'app.services.email_service': Mock(),
    'app.services.auth_service': Mock(),
    'jinja2': Mock()
}):
    from app.services.ai_analysis_service import (
        GeminiAnalysisClient,
        PromptTemplateManager,
        BudgetExceededException,
        AnalysisGenerationException,
        ResponseParsingException
    )


class TestGeminiAnalysisClient:
    """Test cases for GeminiAnalysisClient."""
    
    @pytest.fixture
    def mock_cost_tracker(self):
        """Mock cost tracker."""
        mock_tracker = Mock()
        mock_tracker.can_afford = AsyncMock(return_value=True)
        mock_tracker.record_usage = AsyncMock()
        return mock_tracker
    
    @pytest.fixture
    def client(self, mock_cost_tracker):
        """Create GeminiAnalysisClient instance."""
        with patch('app.services.ai_analysis_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            client = GeminiAnalysisClient("test_api_key")
            client.cost_tracker = mock_cost_tracker
            return client
    
    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        with patch('app.services.ai_analysis_service.genai') as mock_genai:
            client = GeminiAnalysisClient("valid_key")
            
            mock_genai.configure.assert_called_once_with(api_key="valid_key")
            mock_genai.GenerativeModel.assert_called_once_with('gemini-pro')
            assert client.input_token_cost == 0.00025
            assert client.output_token_cost == 0.0005
    
    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key raises error."""
        with pytest.raises(ValueError, match="Google Gemini API key is required"):
            GeminiAnalysisClient("")
    
    def test_estimate_cost(self, client):
        """Test cost estimation."""
        # Test with default response length
        cost = client.estimate_cost(1000)  # 1000 characters
        expected_input_cost = (1000 / 4 / 1000) * 0.00025  # 250 tokens
        expected_output_cost = (2000 / 4 / 1000) * 0.0005   # 500 tokens
        expected_total = expected_input_cost + expected_output_cost
        
        assert cost == expected_total
    
    def test_estimate_cost_with_custom_response_length(self, client):
        """Test cost estimation with custom response length."""
        cost = client.estimate_cost(2000, 1000)  # 2000 char prompt, 1000 char response
        expected_input_cost = (2000 / 4 / 1000) * 0.00025   # 500 tokens
        expected_output_cost = (1000 / 4 / 1000) * 0.0005   # 250 tokens
        expected_total = expected_input_cost + expected_output_cost
        
        assert cost == expected_total
    
    @pytest.mark.asyncio
    async def test_generate_analysis_success(self, client, mock_cost_tracker):
        """Test successful analysis generation."""
        # Mock response
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "rating": "Bullish",
            "confidence": 0.8,
            "key_factors": ["Strong earnings", "Positive sentiment"],
            "price_target_range": {"min": 1000, "max": 1200}
        }
        ```'''
        
        client.model.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await client.generate_analysis(
            "Test prompt", "7203", "short_term"
        )
        
        assert "result" in result
        assert "processing_time_ms" in result
        assert "estimated_cost" in result
        assert "model_version" in result
        assert "generated_at" in result
        
        assert result["result"]["rating"] == "Bullish"
        assert result["result"]["confidence"] == 0.8
        assert result["model_version"] == "gemini-pro"
        
        # Verify cost tracking
        mock_cost_tracker.can_afford.assert_called_once()
        mock_cost_tracker.record_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_analysis_budget_exceeded(self, client, mock_cost_tracker):
        """Test analysis generation when budget is exceeded."""
        mock_cost_tracker.can_afford = AsyncMock(return_value=False)
        
        with pytest.raises(BudgetExceededException):
            await client.generate_analysis(
                "Test prompt", "7203", "short_term"
            )
    
    @pytest.mark.asyncio
    async def test_generate_analysis_api_error(self, client, mock_cost_tracker):
        """Test analysis generation when API call fails."""
        client.model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(AnalysisGenerationException):
            await client.generate_analysis(
                "Test prompt", "7203", "short_term"
            )
    
    def test_parse_response_valid_json(self, client):
        """Test parsing valid JSON response."""
        response_text = '''```json
        {
            "rating": "Bullish",
            "confidence": 0.8,
            "key_factors": ["Factor 1", "Factor 2"]
        }
        ```'''
        
        result = client._parse_response(response_text, "short_term")
        
        assert result["rating"] == "Bullish"
        assert result["confidence"] == 0.8
        assert len(result["key_factors"]) == 2
    
    def test_parse_response_json_without_markers(self, client):
        """Test parsing JSON response without code markers."""
        response_text = '''
        {
            "rating": "Neutral",
            "confidence": 0.6
        }
        '''
        
        result = client._parse_response(response_text, "short_term")
        
        assert result["rating"] == "Neutral"
        assert result["confidence"] == 0.6
    
    def test_parse_response_invalid_json(self, client):
        """Test parsing invalid JSON returns text response."""
        response_text = "This is not valid JSON response"
        
        result = client._parse_response(response_text, "short_term")
        
        assert result["analysis_text"] == response_text
        assert result["format"] == "text"
        assert result["parsed"] == False
    
    def test_validate_analysis_result_valid(self, client):
        """Test validation of valid analysis result."""
        result = {
            "rating": "Bullish",
            "confidence": 0.8,
            "key_factors": ["Factor 1"],
            "price_target_range": {"min": 1000, "max": 1200}
        }
        
        # Should not raise exception
        client._validate_analysis_result(result, "short_term")
    
    def test_validate_analysis_result_missing_fields(self, client):
        """Test validation with missing fields logs warning."""
        result = {
            "rating": "Bullish",
            "confidence": 0.8
            # Missing key_factors and price_target_range
        }
        
        with patch('app.services.ai_analysis_service.logger') as mock_logger:
            client._validate_analysis_result(result, "short_term")
            mock_logger.warning.assert_called_once()


class TestPromptTemplateManager:
    """Test cases for PromptTemplateManager."""
    
    @pytest.fixture
    def template_manager(self):
        """Create PromptTemplateManager instance."""
        return PromptTemplateManager()
    
    def test_init(self, template_manager):
        """Test initialization."""
        assert "short_term" in template_manager.templates
        assert "mid_term" in template_manager.templates
        assert "long_term" in template_manager.templates
        assert "comprehensive" in template_manager.templates
    
    def test_build_prompt_short_term(self, template_manager):
        """Test building short-term analysis prompt."""
        context = {
            "price_data": "Test price data",
            "technical_indicators": "Test indicators",
            "news_sentiment": "Test sentiment",
            "volume_analysis": "Test volume"
        }
        
        prompt = template_manager.build_prompt(
            "short_term", context, "7203", "トヨタ自動車"
        )
        
        assert "7203" in prompt
        assert "トヨタ自動車" in prompt
        assert "Test price data" in prompt
        assert "Test indicators" in prompt
        assert "短期（1-4週間）" in prompt
    
    def test_build_prompt_mid_term(self, template_manager):
        """Test building mid-term analysis prompt."""
        context = {
            "financial_data": "Test financial data",
            "industry_trends": "Test industry trends",
            "quarterly_trends": "Test quarterly trends",
            "peer_comparison": "Test peer comparison",
            "macro_environment": "Test macro environment"
        }
        
        prompt = template_manager.build_prompt(
            "mid_term", context, "7203", "トヨタ自動車"
        )
        
        assert "7203" in prompt
        assert "トヨタ自動車" in prompt
        assert "Test financial data" in prompt
        assert "中期（1-6ヶ月）" in prompt
    
    def test_build_prompt_long_term(self, template_manager):
        """Test building long-term analysis prompt."""
        context = {
            "annual_financial_data": "Test annual data",
            "business_strategy": "Test strategy",
            "esg_metrics": "Test ESG",
            "long_term_industry_outlook": "Test outlook",
            "management_analysis": "Test management",
            "dividend_policy": "Test dividend"
        }
        
        prompt = template_manager.build_prompt(
            "long_term", context, "7203", "トヨタ自動車"
        )
        
        assert "7203" in prompt
        assert "トヨタ自動車" in prompt
        assert "Test annual data" in prompt
        assert "長期（1年以上）" in prompt
    
    def test_build_prompt_comprehensive(self, template_manager):
        """Test building comprehensive analysis prompt."""
        context = {
            "price_technical_data": "Test price technical",
            "fundamental_data": "Test fundamental",
            "news_sentiment_data": "Test news sentiment",
            "industry_competitive_data": "Test industry competitive",
            "macro_economic_data": "Test macro economic"
        }
        
        prompt = template_manager.build_prompt(
            "comprehensive", context, "7203", "トヨタ自動車"
        )
        
        assert "7203" in prompt
        assert "トヨタ自動車" in prompt
        assert "Test price technical" in prompt
        assert "包括的な投資分析" in prompt
    
    def test_build_prompt_unknown_type(self, template_manager):
        """Test building prompt with unknown analysis type."""
        context = {}
        
        with pytest.raises(ValueError, match="Unknown analysis type"):
            template_manager.build_prompt(
                "unknown_type", context, "7203", "トヨタ自動車"
            )
    
    def test_build_prompt_missing_context(self, template_manager):
        """Test building prompt with missing context."""
        context = {}  # Missing required context keys
        
        with pytest.raises(Exception):  # Should raise PromptBuildException or KeyError
            template_manager.build_prompt(
                "short_term", context, "7203", "トヨタ自動車"
            )


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for AI analysis components."""
    
    async def test_full_analysis_flow(self):
        """Test complete analysis flow."""
        # This would be an integration test that tests the full flow
        # from request to cached result
        pass