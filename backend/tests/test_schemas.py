"""
Unit tests for Pydantic schema validation.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.user import UserRegistration, UserLogin, UserProfileUpdate
from app.schemas.stock import StockCreate, PriceDataCreate, StockSearchQuery, PriceHistoryRequest
from app.schemas.ai_analysis import AIAnalysisRequest, BulkAnalysisRequest, FundamentalAnalysisResult, TechnicalAnalysisResult


class TestUserSchemas:
    """Test user-related schema validation."""
    
    def test_user_registration_valid(self):
        """Test valid user registration data."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123",
            "display_name": "Test User"
        }
        user_reg = UserRegistration(**data)
        assert user_reg.email == "test@example.com"
        assert user_reg.password == "SecurePass123"
        assert user_reg.display_name == "Test User"
    
    def test_user_registration_invalid_password(self):
        """Test user registration with invalid password."""
        data = {
            "email": "test@example.com",
            "password": "weak",  # Too short, no uppercase, no digit
        }
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**data)
        
        errors = exc_info.value.errors()
        assert any("Password must be at least 8 characters long" in str(error) for error in errors)
    
    def test_user_registration_invalid_email(self):
        """Test user registration with invalid email."""
        data = {
            "email": "invalid-email",
            "password": "SecurePass123",
        }
        with pytest.raises(ValidationError):
            UserRegistration(**data)
    
    def test_user_login_valid(self):
        """Test valid user login data."""
        data = {
            "email": "test@example.com",
            "password": "password123"
        }
        login = UserLogin(**data)
        assert login.email == "test@example.com"
        assert login.password == "password123"
    
    def test_user_profile_update_valid(self):
        """Test valid user profile update."""
        data = {
            "display_name": "Updated Name",
            "timezone": "America/New_York",
            "notification_preferences": {"email": True, "push": False}
        }
        profile_update = UserProfileUpdate(**data)
        assert profile_update.display_name == "Updated Name"
        assert profile_update.timezone == "America/New_York"
        assert profile_update.notification_preferences == {"email": True, "push": False}


class TestStockSchemas:
    """Test stock-related schema validation."""
    
    def test_stock_create_valid(self):
        """Test valid stock creation data."""
        data = {
            "ticker": "7203",
            "company_name_jp": "トヨタ自動車株式会社",
            "company_name_en": "Toyota Motor Corporation",
            "sector_jp": "輸送用機器",
            "industry_jp": "自動車",
            "is_active": True
        }
        stock = StockCreate(**data)
        assert stock.ticker == "7203"
        assert stock.company_name_jp == "トヨタ自動車株式会社"
        assert stock.is_active is True
    
    def test_stock_create_invalid_ticker(self):
        """Test stock creation with invalid ticker."""
        data = {
            "ticker": "INVALID",  # Should be 4 digits for Japanese stocks
            "company_name_jp": "Test Company",
        }
        with pytest.raises(ValidationError) as exc_info:
            StockCreate(**data)
        
        errors = exc_info.value.errors()
        assert any("Japanese stock ticker must be 4 digits" in str(error) for error in errors)
    
    def test_price_data_create_valid(self):
        """Test valid price data creation."""
        data = {
            "ticker": "7203",
            "date": date(2024, 1, 15),
            "open": Decimal("2500.00"),
            "high": Decimal("2550.00"),
            "low": Decimal("2480.00"),
            "close": Decimal("2520.00"),
            "volume": 1000000
        }
        price_data = PriceDataCreate(**data)
        assert price_data.ticker == "7203"
        assert price_data.open_price == Decimal("2500.00")
        assert price_data.volume == 1000000
    
    def test_price_data_create_invalid_price(self):
        """Test price data creation with invalid price."""
        data = {
            "ticker": "7203",
            "date": date(2024, 1, 15),
            "open": Decimal("-100.00"),  # Negative price
            "high": Decimal("2550.00"),
            "low": Decimal("2480.00"),
            "close": Decimal("2520.00"),
            "volume": 1000000
        }
        with pytest.raises(ValidationError) as exc_info:
            PriceDataCreate(**data)
        
        errors = exc_info.value.errors()
        assert any("Price must be positive" in str(error) for error in errors)
    
    def test_stock_search_query_valid(self):
        """Test valid stock search query."""
        data = {
            "query": "トヨタ",
            "limit": 10,
            "include_inactive": False
        }
        search_query = StockSearchQuery(**data)
        assert search_query.query == "トヨタ"
        assert search_query.limit == 10
        assert search_query.include_inactive is False
    
    def test_stock_search_query_invalid_limit(self):
        """Test stock search query with invalid limit."""
        data = {
            "query": "トヨタ",
            "limit": 200,  # Exceeds maximum of 100
        }
        with pytest.raises(ValidationError):
            StockSearchQuery(**data)
    
    def test_price_history_request_valid(self):
        """Test valid price history request."""
        data = {
            "ticker": "7203",
            "period": "1y",
            "interval": "1d"
        }
        request = PriceHistoryRequest(**data)
        assert request.ticker == "7203"
        assert request.period == "1y"
        assert request.interval == "1d"
    
    def test_price_history_request_invalid_period(self):
        """Test price history request with invalid period."""
        data = {
            "ticker": "7203",
            "period": "invalid_period",
            "interval": "1d"
        }
        with pytest.raises(ValidationError) as exc_info:
            PriceHistoryRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("Period must be one of" in str(error) for error in errors)


class TestAIAnalysisSchemas:
    """Test AI analysis schema validation."""
    
    def test_ai_analysis_request_valid(self):
        """Test valid AI analysis request."""
        data = {
            "ticker": "7203",
            "analysis_type": "fundamental",
            "language": "ja",
            "parameters": {"time_horizon": "1_year"}
        }
        request = AIAnalysisRequest(**data)
        assert request.ticker == "7203"
        assert request.analysis_type == "fundamental"
        assert request.language == "ja"
    
    def test_ai_analysis_request_invalid_type(self):
        """Test AI analysis request with invalid analysis type."""
        data = {
            "ticker": "7203",
            "analysis_type": "invalid_type",
            "language": "ja"
        }
        with pytest.raises(ValidationError) as exc_info:
            AIAnalysisRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("Analysis type must be one of" in str(error) for error in errors)
    
    def test_ai_analysis_request_invalid_language(self):
        """Test AI analysis request with invalid language."""
        data = {
            "ticker": "7203",
            "analysis_type": "fundamental",
            "language": "fr"  # Not supported
        }
        with pytest.raises(ValidationError) as exc_info:
            AIAnalysisRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("Language must be ja or en" in str(error) for error in errors)
    
    def test_bulk_analysis_request_valid(self):
        """Test valid bulk analysis request."""
        data = {
            "tickers": ["7203", "6758", "9984"],
            "analysis_type": "technical",
            "language": "en"
        }
        request = BulkAnalysisRequest(**data)
        assert len(request.tickers) == 3
        assert request.analysis_type == "technical"
    
    def test_bulk_analysis_request_duplicate_tickers(self):
        """Test bulk analysis request with duplicate tickers."""
        data = {
            "tickers": ["7203", "7203", "6758"],  # Duplicate ticker
            "analysis_type": "technical",
            "language": "en"
        }
        with pytest.raises(ValidationError) as exc_info:
            BulkAnalysisRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("Duplicate tickers are not allowed" in str(error) for error in errors)
    
    def test_fundamental_analysis_result_valid(self):
        """Test valid fundamental analysis result."""
        data = {
            "overall_score": 75.5,
            "financial_health": {"debt_ratio": 0.3, "current_ratio": 1.5},
            "valuation": {"pe_ratio": 15.2, "pb_ratio": 1.1},
            "growth_prospects": {"revenue_growth": 0.05, "earnings_growth": 0.08},
            "competitive_position": {"market_share": 0.25, "moat_strength": "strong"},
            "risks": ["Economic downturn", "Currency fluctuation"],
            "opportunities": ["Electric vehicle market", "Autonomous driving"],
            "summary": "Strong fundamental position with growth potential",
            "recommendation": "Buy",
            "target_price": 2800.0,
            "confidence_level": 0.85
        }
        result = FundamentalAnalysisResult(**data)
        assert result.overall_score == 75.5
        assert result.confidence_level == 0.85
        assert len(result.risks) == 2
    
    def test_fundamental_analysis_result_invalid_score(self):
        """Test fundamental analysis result with invalid score."""
        data = {
            "overall_score": 150.0,  # Exceeds maximum of 100
            "financial_health": {},
            "valuation": {},
            "growth_prospects": {},
            "competitive_position": {},
            "risks": [],
            "opportunities": [],
            "summary": "Test summary",
            "recommendation": "Buy",
            "confidence_level": 0.85
        }
        with pytest.raises(ValidationError):
            FundamentalAnalysisResult(**data)
    
    def test_technical_analysis_result_valid(self):
        """Test valid technical analysis result."""
        data = {
            "overall_signal": "buy",
            "trend_analysis": {"trend": "upward", "strength": "strong"},
            "support_resistance": {"support": 2400, "resistance": 2600},
            "indicators": {"rsi": 65, "macd": "bullish"},
            "chart_patterns": ["ascending triangle", "golden cross"],
            "volume_analysis": {"volume_trend": "increasing"},
            "momentum": {"momentum_score": 0.7},
            "summary": "Bullish technical outlook",
            "short_term_outlook": "Positive momentum continues",
            "medium_term_outlook": "Uptrend likely to persist",
            "key_levels": {"support": 2400.0, "resistance": 2600.0}
        }
        result = TechnicalAnalysisResult(**data)
        assert result.overall_signal == "buy"
        assert len(result.chart_patterns) == 2
    
    def test_technical_analysis_result_invalid_signal(self):
        """Test technical analysis result with invalid signal."""
        data = {
            "overall_signal": "invalid_signal",
            "trend_analysis": {},
            "support_resistance": {},
            "indicators": {},
            "chart_patterns": [],
            "volume_analysis": {},
            "momentum": {},
            "summary": "Test summary",
            "short_term_outlook": "Test outlook",
            "medium_term_outlook": "Test outlook",
            "key_levels": {}
        }
        with pytest.raises(ValidationError) as exc_info:
            TechnicalAnalysisResult(**data)
        
        errors = exc_info.value.errors()
        assert any("Signal must be one of" in str(error) for error in errors)


class TestSchemaIntegration:
    """Test schema integration and basic functionality."""
    
    def test_price_data_calculations(self):
        """Test price data calculations."""
        price_data = {
            "ticker": "7203",
            "date": date(2024, 1, 15),
            "open": Decimal("2500.00"),
            "high": Decimal("2550.00"),
            "low": Decimal("2480.00"),
            "close": Decimal("2520.00"),
            "volume": 1000000
        }
        
        # Test that we can create the price data object
        price = PriceDataCreate(**price_data)
        assert price.ticker == "7203"
        assert price.open_price == Decimal("2500.00")
        assert price.close_price == Decimal("2520.00")
        assert price.volume == 1000000


if __name__ == "__main__":
    pytest.main([__file__])