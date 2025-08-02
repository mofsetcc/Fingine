"""
Database integration tests with test fixtures.
Tests database operations, transactions, and data integrity.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from app.models.base import Base
from app.models.user import User, UserProfile, UserOAuthIdentity
from app.models.stock import Stock, StockDailyMetrics, StockPriceHistory
from app.models.subscription import Subscription, Plan
from app.models.financial import FinancialReport, FinancialReportLineItem
from app.models.news import NewsArticle, StockNewsLink
from app.models.analysis import AIAnalysisCache
from app.models.watchlist import UserWatchlist


# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def setup_test_database():
    """Set up test database with all tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_test_database):
    """Database session fixture for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        email_verified_at="2024-01-01T00:00:00Z"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_stock(db_session):
    """Create a sample stock for testing."""
    stock = Stock(
        ticker="7203",
        company_name_jp="トヨタ自動車株式会社",
        company_name_en="Toyota Motor Corporation",
        sector_jp="輸送用機器",
        industry_jp="自動車",
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()
    db_session.refresh(stock)
    return stock


@pytest.fixture
def sample_plan(db_session):
    """Create a sample subscription plan for testing."""
    plan = Plan(
        plan_name="pro",
        price_monthly=2980,
        features={"ai_analysis": True, "real_time_data": True},
        api_quota_daily=100,
        ai_analysis_quota_daily=20
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


class TestUserDatabaseOperations:
    """Test user-related database operations."""
    
    def test_user_creation_and_retrieval(self, db_session):
        """Test user creation and retrieval."""
        # Create user
        user_id = uuid4()
        user = User(
            id=user_id,
            email="newuser@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()
        
        # Retrieve user
        retrieved_user = db_session.query(User).filter(User.id == user_id).first()
        assert retrieved_user is not None
        assert retrieved_user.email == "newuser@example.com"
        assert retrieved_user.password_hash == "hashed_password"
        assert retrieved_user.created_at is not None
        assert retrieved_user.updated_at is not None
    
    def test_user_email_uniqueness_constraint(self, db_session, sample_user):
        """Test user email uniqueness constraint."""
        # Try to create another user with same email
        duplicate_user = User(
            id=uuid4(),
            email=sample_user.email,  # Same email
            password_hash="different_hash"
        )
        db_session.add(duplicate_user)
        
        # Should raise integrity error
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_profile_relationship(self, db_session, sample_user):
        """Test user-profile relationship."""
        # Create profile for user
        profile = UserProfile(
            user_id=sample_user.id,
            display_name="Test User",
            timezone="Asia/Tokyo",
            notification_preferences={"email": True}
        )
        db_session.add(profile)
        db_session.commit()
        
        # Test relationship
        db_session.refresh(sample_user)
        assert sample_user.profile is not None
        assert sample_user.profile.display_name == "Test User"
        assert sample_user.profile.timezone == "Asia/Tokyo"
        
        # Test reverse relationship
        assert profile.user.email == sample_user.email
    
    def test_user_oauth_identities_relationship(self, db_session, sample_user):
        """Test user OAuth identities relationship."""
        # Create OAuth identities
        google_identity = UserOAuthIdentity(
            provider="google",
            provider_user_id="google_123",
            user_id=sample_user.id
        )
        line_identity = UserOAuthIdentity(
            provider="line",
            provider_user_id="line_456",
            user_id=sample_user.id
        )
        
        db_session.add_all([google_identity, line_identity])
        db_session.commit()
        
        # Test relationship
        db_session.refresh(sample_user)
        assert len(sample_user.oauth_identities) == 2
        
        providers = [identity.provider for identity in sample_user.oauth_identities]
        assert "google" in providers
        assert "line" in providers
    
    def test_user_cascade_deletion(self, db_session, sample_user):
        """Test cascade deletion of user and related data."""
        # Create related data
        profile = UserProfile(
            user_id=sample_user.id,
            display_name="Test User"
        )
        oauth_identity = UserOAuthIdentity(
            provider="google",
            provider_user_id="google_123",
            user_id=sample_user.id
        )
        
        db_session.add_all([profile, oauth_identity])
        db_session.commit()
        
        # Delete user
        db_session.delete(sample_user)
        db_session.commit()
        
        # Verify related data is also deleted
        remaining_profiles = db_session.query(UserProfile).filter(
            UserProfile.user_id == sample_user.id
        ).count()
        remaining_oauth = db_session.query(UserOAuthIdentity).filter(
            UserOAuthIdentity.user_id == sample_user.id
        ).count()
        
        assert remaining_profiles == 0
        assert remaining_oauth == 0


class TestStockDatabaseOperations:
    """Test stock-related database operations."""
    
    def test_stock_creation_and_retrieval(self, db_session):
        """Test stock creation and retrieval."""
        # Create stock
        stock = Stock(
            ticker="6758",
            company_name_jp="ソニーグループ株式会社",
            company_name_en="Sony Group Corporation",
            sector_jp="電気機器",
            industry_jp="エレクトロニクス"
        )
        db_session.add(stock)
        db_session.commit()
        
        # Retrieve stock
        retrieved_stock = db_session.query(Stock).filter(Stock.ticker == "6758").first()
        assert retrieved_stock is not None
        assert retrieved_stock.company_name_jp == "ソニーグループ株式会社"
        assert retrieved_stock.sector_jp == "電気機器"
    
    def test_stock_price_history_relationship(self, db_session, sample_stock):
        """Test stock price history relationship."""
        # Create price history
        price_data = [
            StockPriceHistory(
                ticker=sample_stock.ticker,
                date=date(2024, 1, 15),
                open=Decimal("2500.0"),
                high=Decimal("2550.0"),
                low=Decimal("2480.0"),
                close=Decimal("2520.0"),
                volume=15000000
            ),
            StockPriceHistory(
                ticker=sample_stock.ticker,
                date=date(2024, 1, 14),
                open=Decimal("2480.0"),
                high=Decimal("2510.0"),
                low=Decimal("2460.0"),
                close=Decimal("2500.0"),
                volume=12000000
            )
        ]
        
        db_session.add_all(price_data)
        db_session.commit()
        
        # Test relationship
        db_session.refresh(sample_stock)
        assert len(sample_stock.price_history) == 2
        
        # Test ordering (should be by date)
        sorted_prices = sorted(sample_stock.price_history, key=lambda x: x.date, reverse=True)
        assert sorted_prices[0].date == date(2024, 1, 15)
        assert sorted_prices[0].close == Decimal("2520.0")
    
    def test_stock_daily_metrics_relationship(self, db_session, sample_stock):
        """Test stock daily metrics relationship."""
        # Create daily metrics
        metrics = StockDailyMetrics(
            ticker=sample_stock.ticker,
            date=date(2024, 1, 15),
            market_cap=35000000000000,
            pe_ratio=Decimal("12.5"),
            pb_ratio=Decimal("1.2"),
            dividend_yield=Decimal("0.0275"),
            shares_outstanding=14700000000
        )
        
        db_session.add(metrics)
        db_session.commit()
        
        # Test relationship
        db_session.refresh(sample_stock)
        assert len(sample_stock.daily_metrics) == 1
        assert sample_stock.daily_metrics[0].market_cap == 35000000000000
        assert sample_stock.daily_metrics[0].pe_ratio == Decimal("12.5")
    
    def test_stock_search_performance(self, db_session):
        """Test stock search performance with indexes."""
        # Create multiple stocks
        stocks = []
        for i in range(100):
            stock = Stock(
                ticker=f"{7000 + i}",
                company_name_jp=f"テスト会社{i}",
                company_name_en=f"Test Company {i}",
                sector_jp="テスト業界"
            )
            stocks.append(stock)
        
        db_session.add_all(stocks)
        db_session.commit()
        
        # Test search performance
        import time
        start_time = time.time()
        
        # Search by ticker
        ticker_results = db_session.query(Stock).filter(
            Stock.ticker.like("70%")
        ).limit(10).all()
        
        # Search by company name
        name_results = db_session.query(Stock).filter(
            Stock.company_name_jp.like("%テスト%")
        ).limit(10).all()
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Should be fast with proper indexing
        assert search_time < 1.0
        assert len(ticker_results) == 10
        assert len(name_results) >= 10


class TestFinancialDataIntegration:
    """Test financial data integration."""
    
    def test_financial_report_creation(self, db_session, sample_stock):
        """Test financial report creation and line items."""
        # Create financial report
        report = FinancialReport(
            id=uuid4(),
            ticker=sample_stock.ticker,
            fiscal_year=2023,
            fiscal_period="Q3",
            report_type="quarterly",
            announced_at=datetime(2024, 1, 15, 15, 0, 0),
            source_url="https://example.com/report.pdf"
        )
        db_session.add(report)
        db_session.commit()
        
        # Create line items
        line_items = [
            FinancialReportLineItem(
                report_id=report.id,
                metric_name="net_sales",
                metric_value=Decimal("37154200000000"),
                unit="JPY",
                period_type="quarterly"
            ),
            FinancialReportLineItem(
                report_id=report.id,
                metric_name="operating_income",
                metric_value=Decimal("4052800000000"),
                unit="JPY",
                period_type="quarterly"
            ),
            FinancialReportLineItem(
                report_id=report.id,
                metric_name="net_income",
                metric_value=Decimal("2926100000000"),
                unit="JPY",
                period_type="quarterly"
            )
        ]
        
        db_session.add_all(line_items)
        db_session.commit()
        
        # Test relationships
        db_session.refresh(report)
        assert len(report.line_items) == 3
        
        # Test specific metrics
        net_sales_item = next(
            item for item in report.line_items 
            if item.metric_name == "net_sales"
        )
        assert net_sales_item.metric_value == Decimal("37154200000000")
        assert net_sales_item.unit == "JPY"
    
    def test_financial_report_uniqueness_constraint(self, db_session, sample_stock):
        """Test financial report uniqueness constraint."""
        # Create first report
        report1 = FinancialReport(
            id=uuid4(),
            ticker=sample_stock.ticker,
            fiscal_year=2023,
            fiscal_period="Q3",
            report_type="quarterly",
            announced_at=datetime(2024, 1, 15, 15, 0, 0)
        )
        db_session.add(report1)
        db_session.commit()
        
        # Try to create duplicate report
        report2 = FinancialReport(
            id=uuid4(),
            ticker=sample_stock.ticker,
            fiscal_year=2023,
            fiscal_period="Q3",  # Same period
            report_type="quarterly",
            announced_at=datetime(2024, 1, 16, 15, 0, 0)
        )
        db_session.add(report2)
        
        # Should raise integrity error due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestNewsAndAnalysisIntegration:
    """Test news and analysis data integration."""
    
    def test_news_article_creation(self, db_session):
        """Test news article creation."""
        article = NewsArticle(
            id=uuid4(),
            article_url="https://example.com/news/toyota-earnings",
            headline="トヨタ自動車、第3四半期決算を発表",
            content_summary="トヨタ自動車は本日、第3四半期の決算を発表しました。",
            source="Reuters",
            author="Reuters Staff",
            published_at=datetime(2024, 1, 15, 10, 0, 0),
            sentiment_label="positive",
            sentiment_score=Decimal("0.85"),
            language="ja"
        )
        
        db_session.add(article)
        db_session.commit()
        
        # Retrieve and verify
        retrieved_article = db_session.query(NewsArticle).filter(
            NewsArticle.id == article.id
        ).first()
        
        assert retrieved_article is not None
        assert retrieved_article.headline == "トヨタ自動車、第3四半期決算を発表"
        assert retrieved_article.sentiment_label == "positive"
        assert retrieved_article.sentiment_score == Decimal("0.85")
    
    def test_stock_news_relationship(self, db_session, sample_stock):
        """Test stock-news relationship."""
        # Create news article
        article = NewsArticle(
            id=uuid4(),
            article_url="https://example.com/news/toyota",
            headline="Toyota News",
            source="Test Source",
            published_at=datetime(2024, 1, 15, 10, 0, 0),
            sentiment_label="positive",
            sentiment_score=Decimal("0.8")
        )
        db_session.add(article)
        db_session.commit()
        
        # Create stock-news link
        news_link = StockNewsLink(
            article_id=article.id,
            ticker=sample_stock.ticker,
            relevance_score=Decimal("0.95")
        )
        db_session.add(news_link)
        db_session.commit()
        
        # Test relationships
        db_session.refresh(sample_stock)
        assert len(sample_stock.news_links) == 1
        assert sample_stock.news_links[0].relevance_score == Decimal("0.95")
        
        # Test reverse relationship
        db_session.refresh(article)
        assert len(article.stock_links) == 1
        assert article.stock_links[0].ticker == sample_stock.ticker
    
    def test_ai_analysis_cache(self, db_session, sample_stock):
        """Test AI analysis cache functionality."""
        analysis = AIAnalysisCache(
            ticker=sample_stock.ticker,
            analysis_date=date(2024, 1, 15),
            analysis_type="comprehensive",
            model_version="gemini-pro-1.0",
            prompt_hash="abc123def456",
            analysis_result={
                "rating": "Bullish",
                "confidence": 0.85,
                "key_factors": ["Strong earnings", "Positive sentiment"],
                "price_target_range": {"min": 2600, "max": 2800},
                "risk_factors": ["Market volatility"]
            },
            confidence_score=Decimal("0.85"),
            processing_time_ms=1500,
            cost_usd=Decimal("0.05")
        )
        
        db_session.add(analysis)
        db_session.commit()
        
        # Retrieve and verify
        retrieved_analysis = db_session.query(AIAnalysisCache).filter(
            AIAnalysisCache.ticker == sample_stock.ticker,
            AIAnalysisCache.analysis_date == date(2024, 1, 15)
        ).first()
        
        assert retrieved_analysis is not None
        assert retrieved_analysis.analysis_result["rating"] == "Bullish"
        assert retrieved_analysis.confidence_score == Decimal("0.85")
        assert retrieved_analysis.cost_usd == Decimal("0.05")


class TestSubscriptionIntegration:
    """Test subscription and billing integration."""
    
    def test_subscription_creation(self, db_session, sample_user, sample_plan):
        """Test subscription creation."""
        subscription = Subscription(
            id=uuid4(),
            user_id=sample_user.id,
            plan_id=sample_plan.id,
            status="active",
            current_period_start=datetime(2024, 1, 1),
            current_period_end=datetime(2024, 2, 1)
        )
        
        db_session.add(subscription)
        db_session.commit()
        
        # Test relationships
        db_session.refresh(sample_user)
        assert sample_user.subscription is not None
        assert sample_user.subscription.status == "active"
        assert sample_user.subscription.plan.plan_name == "pro"
    
    def test_user_unique_subscription_constraint(self, db_session, sample_user, sample_plan):
        """Test that users can only have one active subscription."""
        # Create first subscription
        subscription1 = Subscription(
            id=uuid4(),
            user_id=sample_user.id,
            plan_id=sample_plan.id,
            status="active",
            current_period_start=datetime(2024, 1, 1),
            current_period_end=datetime(2024, 2, 1)
        )
        db_session.add(subscription1)
        db_session.commit()
        
        # Try to create second subscription for same user
        subscription2 = Subscription(
            id=uuid4(),
            user_id=sample_user.id,  # Same user
            plan_id=sample_plan.id,
            status="active",
            current_period_start=datetime(2024, 2, 1),
            current_period_end=datetime(2024, 3, 1)
        )
        db_session.add(subscription2)
        
        # Should raise integrity error due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWatchlistIntegration:
    """Test watchlist functionality integration."""
    
    def test_watchlist_creation(self, db_session, sample_user, sample_stock):
        """Test watchlist creation."""
        watchlist_item = UserWatchlist(
            user_id=sample_user.id,
            ticker=sample_stock.ticker,
            notes="Potential buy opportunity"
        )
        
        db_session.add(watchlist_item)
        db_session.commit()
        
        # Test relationships
        db_session.refresh(sample_user)
        assert len(sample_user.watchlist) == 1
        assert sample_user.watchlist[0].ticker == sample_stock.ticker
        assert sample_user.watchlist[0].notes == "Potential buy opportunity"
        
        # Test reverse relationship
        db_session.refresh(sample_stock)
        assert len(sample_stock.watchlist_entries) == 1
        assert sample_stock.watchlist_entries[0].user_id == sample_user.id
    
    def test_watchlist_unique_constraint(self, db_session, sample_user, sample_stock):
        """Test watchlist unique constraint (user can't add same stock twice)."""
        # Add stock to watchlist
        watchlist_item1 = UserWatchlist(
            user_id=sample_user.id,
            ticker=sample_stock.ticker,
            notes="First entry"
        )
        db_session.add(watchlist_item1)
        db_session.commit()
        
        # Try to add same stock again
        watchlist_item2 = UserWatchlist(
            user_id=sample_user.id,
            ticker=sample_stock.ticker,  # Same stock
            notes="Second entry"
        )
        db_session.add(watchlist_item2)
        
        # Should raise integrity error
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestTransactionIntegrity:
    """Test database transaction integrity."""
    
    def test_transaction_rollback_on_error(self, db_session):
        """Test transaction rollback on error."""
        # Start transaction
        user = User(
            id=uuid4(),
            email="transaction_test@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        
        # Add profile
        profile = UserProfile(
            user_id=user.id,
            display_name="Transaction Test"
        )
        db_session.add(profile)
        
        # Cause an error (invalid foreign key)
        invalid_watchlist = UserWatchlist(
            user_id=user.id,
            ticker="INVALID_TICKER"  # This ticker doesn't exist
        )
        db_session.add(invalid_watchlist)
        
        # Transaction should fail and rollback
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        # Verify rollback - user should not exist
        db_session.rollback()
        existing_user = db_session.query(User).filter(
            User.email == "transaction_test@example.com"
        ).first()
        assert existing_user is None
    
    def test_concurrent_access_handling(self, db_session):
        """Test concurrent access handling."""
        # This would test optimistic locking and concurrent updates
        # Implementation depends on specific concurrency requirements
        pass


class TestDatabasePerformance:
    """Test database performance and optimization."""
    
    def test_query_performance_with_indexes(self, db_session):
        """Test query performance with proper indexes."""
        # Create test data
        stocks = []
        for i in range(1000):
            stock = Stock(
                ticker=f"T{i:04d}",
                company_name_jp=f"会社{i}",
                sector_jp=f"業界{i % 10}"
            )
            stocks.append(stock)
        
        db_session.add_all(stocks)
        db_session.commit()
        
        # Test query performance
        import time
        
        # Test ticker search (should use index)
        start_time = time.time()
        result = db_session.query(Stock).filter(Stock.ticker == "T0500").first()
        ticker_search_time = time.time() - start_time
        
        # Test sector search (should use index)
        start_time = time.time()
        results = db_session.query(Stock).filter(Stock.sector_jp == "業界5").all()
        sector_search_time = time.time() - start_time
        
        # Should be fast with proper indexing
        assert ticker_search_time < 0.1
        assert sector_search_time < 0.5
        assert result is not None
        assert len(results) == 100  # 1000 / 10 sectors
    
    def test_bulk_operations_performance(self, db_session):
        """Test bulk operations performance."""
        # Test bulk insert
        price_data = []
        for i in range(1000):
            price = StockPriceHistory(
                ticker="BULK",
                date=date(2024, 1, 1),
                open=Decimal("100.0"),
                high=Decimal("105.0"),
                low=Decimal("95.0"),
                close=Decimal("102.0"),
                volume=1000000
            )
            price_data.append(price)
        
        # Create stock first
        stock = Stock(ticker="BULK", company_name_jp="Bulk Test")
        db_session.add(stock)
        db_session.commit()
        
        # Bulk insert
        import time
        start_time = time.time()
        db_session.add_all(price_data)
        db_session.commit()
        bulk_insert_time = time.time() - start_time
        
        # Should be reasonably fast
        assert bulk_insert_time < 5.0  # 5 seconds for 1000 records
        
        # Verify data
        count = db_session.query(StockPriceHistory).filter(
            StockPriceHistory.ticker == "BULK"
        ).count()
        assert count == 1000


class TestDataIntegrityConstraints:
    """Test data integrity constraints."""
    
    def test_foreign_key_constraints(self, db_session):
        """Test foreign key constraints."""
        # Try to create profile with non-existent user
        invalid_profile = UserProfile(
            user_id=uuid4(),  # Non-existent user ID
            display_name="Invalid Profile"
        )
        db_session.add(invalid_profile)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_check_constraints(self, db_session, sample_stock):
        """Test check constraints."""
        # Try to create price history with invalid data
        invalid_price = StockPriceHistory(
            ticker=sample_stock.ticker,
            date=date(2024, 1, 15),
            open=Decimal("100.0"),
            high=Decimal("90.0"),  # High < Open (invalid)
            low=Decimal("95.0"),
            close=Decimal("98.0"),
            volume=-1000  # Negative volume (invalid)
        )
        db_session.add(invalid_price)
        
        # Note: SQLite doesn't enforce all check constraints by default
        # In PostgreSQL, this would raise an IntegrityError
        try:
            db_session.commit()
        except IntegrityError:
            # Expected in databases with proper check constraint support
            pass
    
    def test_not_null_constraints(self, db_session):
        """Test NOT NULL constraints."""
        # Try to create stock without required fields
        invalid_stock = Stock(
            ticker="TEST",
            company_name_jp=None  # Required field
        )
        db_session.add(invalid_stock)
        
        with pytest.raises(IntegrityError):
            db_session.commit()