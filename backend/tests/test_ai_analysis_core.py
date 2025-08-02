"""
Core unit tests for AI analysis components.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


# Mock the Google Generative AI module
@pytest.fixture
def mock_genai():
    with patch('google.generativeai') as mock:
        mock_model = Mock()
        mock.GenerativeModel.return_value = mock_model
        yield mock


class TestGeminiAnalysisClientCore:
    """Test core functionality of GeminiAnalysisClient."""
    
    def test_cost_estimation(self, mock_genai):
        """Test cost estimation logic."""
        # Import here to avoid dependency issues
        from app.services.ai_analysis_service import GeminiAnalysisClient
        
        client = GeminiAnalysisClient("test_key")
        
        # Test with 1000 character prompt, 2000 character response
        cost = client.estimate_cost(1000, 2000)
        
        # Expected calculation:
        # Input: 1000/4 = 250 tokens, 250/1000 * 0.00025 = 0.0000625
        # Output: 2000/4 = 500 tokens, 500/1000 * 0.0005 = 0.00025
        # Total: 0.0000625 + 0.00025 = 0.0003125
        expected_cost = 0.0003125
        
        assert abs(cost - expected_cost) < 0.0000001  # Allow for floating point precision
    
    def test_json_response_parsing(self, mock_genai):
        """Test JSON response parsing."""
        from app.services.ai_analysis_service import GeminiAnalysisClient
        
        client = GeminiAnalysisClient("test_key")
        
        # Test with JSON wrapped in code blocks
        response_text = '''```json
        {
            "rating": "Bullish",
            "confidence": 0.8,
            "key_factors": ["Strong earnings", "Positive sentiment"]
        }
        ```'''
        
        result = client._parse_response(response_text, "short_term")
        
        assert result["rating"] == "Bullish"
        assert result["confidence"] == 0.8
        assert len(result["key_factors"]) == 2
    
    def test_invalid_json_response_parsing(self, mock_genai):
        """Test handling of invalid JSON response."""
        from app.services.ai_analysis_service import GeminiAnalysisClient
        
        client = GeminiAnalysisClient("test_key")
        
        response_text = "This is not valid JSON"
        result = client._parse_response(response_text, "short_term")
        
        assert result["analysis_text"] == response_text
        assert result["format"] == "text"
        assert result["parsed"] == False


class TestPromptTemplateManagerCore:
    """Test core functionality of PromptTemplateManager."""
    
    def test_template_initialization(self):
        """Test that all required templates are initialized."""
        from app.services.ai_analysis_service import PromptTemplateManager
        
        manager = PromptTemplateManager()
        
        required_templates = ["short_term", "mid_term", "long_term", "comprehensive"]
        for template_type in required_templates:
            assert template_type in manager.templates
            assert isinstance(manager.templates[template_type], str)
            assert len(manager.templates[template_type]) > 0
    
    def test_prompt_building_basic(self):
        """Test basic prompt building functionality."""
        from app.services.ai_analysis_service import PromptTemplateManager
        
        manager = PromptTemplateManager()
        
        context = {
            "price_data": "Test price data",
            "technical_indicators": "Test indicators",
            "news_sentiment": "Test sentiment",
            "volume_analysis": "Test volume"
        }
        
        prompt = manager.build_prompt(
            "short_term", context, "7203", "トヨタ自動車"
        )
        
        # Check that ticker and company name are included
        assert "7203" in prompt
        assert "トヨタ自動車" in prompt
        
        # Check that context data is included
        assert "Test price data" in prompt
        assert "Test indicators" in prompt
    
    def test_unknown_analysis_type(self):
        """Test handling of unknown analysis type."""
        from app.services.ai_analysis_service import PromptTemplateManager
        
        manager = PromptTemplateManager()
        
        with pytest.raises(ValueError, match="Unknown analysis type"):
            manager.build_prompt("unknown_type", {}, "7203", "Test Company")


class TestTechnicalIndicators:
    """Test technical indicator calculations."""
    
    def test_sma_calculation(self):
        """Test Simple Moving Average calculation."""
        from app.services.data_transformer import TechnicalIndicatorCalculator
        
        prices = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        sma_5 = TechnicalIndicatorCalculator.calculate_sma(prices, 5)
        
        # Expected SMA values for 5-period:
        # [14, 16, 18, 20, 22, 24] (starting from 5th element)
        expected = [14.0, 16.0, 18.0, 20.0, 22.0, 24.0]
        
        assert len(sma_5) == 6
        assert sma_5 == expected
    
    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        from app.services.data_transformer import TechnicalIndicatorCalculator
        
        prices = [10, 12, 14]  # Only 3 prices
        sma_5 = TechnicalIndicatorCalculator.calculate_sma(prices, 5)
        
        assert sma_5 == []
    
    def test_rsi_calculation(self):
        """Test RSI calculation with known values."""
        from app.services.data_transformer import TechnicalIndicatorCalculator
        
        # Simple test case
        prices = [44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.85, 47.25, 47.92,
                 46.23, 44.18, 46.57, 47.61, 46.5, 46.23, 46.08, 47.03, 47.74, 46.95]
        
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, 14)
        
        # RSI should be between 0 and 100
        assert len(rsi) > 0
        for value in rsi:
            assert 0 <= value <= 100
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation."""
        from app.services.data_transformer import TechnicalIndicatorCalculator
        
        prices = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
        
        bands = TechnicalIndicatorCalculator.calculate_bollinger_bands(prices, 20)
        
        assert "upper" in bands
        assert "middle" in bands
        assert "lower" in bands
        
        # Should have one value (for the 20th price)
        assert len(bands["upper"]) == 1
        assert len(bands["middle"]) == 1
        assert len(bands["lower"]) == 1
        
        # Upper band should be higher than middle, middle higher than lower
        assert bands["upper"][0] > bands["middle"][0]
        assert bands["middle"][0] > bands["lower"][0]


class TestCostManagerCore:
    """Test core cost management functionality."""
    
    def test_cost_estimation_by_analysis_type(self):
        """Test cost estimation for different analysis types."""
        from app.services.cost_manager import CostManager
        
        cost_manager = CostManager()
        
        # Test different analysis types
        short_term_cost = cost_manager.estimate_analysis_cost("short_term")
        mid_term_cost = cost_manager.estimate_analysis_cost("mid_term")
        long_term_cost = cost_manager.estimate_analysis_cost("long_term")
        comprehensive_cost = cost_manager.estimate_analysis_cost("comprehensive")
        
        # Costs should increase with complexity
        assert short_term_cost < mid_term_cost
        assert mid_term_cost < long_term_cost
        assert long_term_cost < comprehensive_cost
        
        # All costs should be positive
        assert short_term_cost > 0
        assert mid_term_cost > 0
        assert long_term_cost > 0
        assert comprehensive_cost > 0
    
    def test_cache_threshold_calculation(self):
        """Test cache threshold calculation."""
        from app.services.cost_manager import CostManager
        
        cost_manager = CostManager()
        
        # Test with different times and costs
        current_time = datetime(2024, 1, 15, 10, 0, 0)  # Monday 10 AM
        
        # Market hours threshold
        threshold = cost_manager._get_cache_threshold(current_time)
        assert threshold == 300  # 5 minutes during market hours
        
        # After hours
        after_hours_time = datetime(2024, 1, 15, 18, 0, 0)  # Monday 6 PM
        threshold = cost_manager._get_cache_threshold(after_hours_time)
        assert threshold == 1800  # 30 minutes after hours
        
        # Weekend
        weekend_time = datetime(2024, 1, 13, 10, 0, 0)  # Saturday 10 AM
        threshold = cost_manager._get_cache_threshold(weekend_time)
        assert threshold == 3600  # 1 hour on weekends


if __name__ == "__main__":
    pytest.main([__file__])