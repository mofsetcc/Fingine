# Design Document

## Overview

This document outlines the comprehensive technical design for Project Kessan (決算 - "Financial Results"), an AI-powered Japanese stock trend analysis platform. The system democratizes institutional-grade investment analysis by providing retail investors and small-to-medium financial institutions with in-depth, accurate, and forward-looking stock insights at an affordable cost.

The platform follows a cloud-native microservices architecture deployed on AWS, featuring a React TypeScript frontend, FastAPI Python backend services, PostgreSQL database with Redis caching, and comprehensive AI integration using Google Gemini API. The design emphasizes scalability, cost optimization, data accuracy, and real-time insights for Tokyo Stock Exchange (TSE) listed companies with multi-horizon AI forecasting capabilities.

## Architecture

### System Architecture Overview

The system adopts a cloud-native microservices architecture with the following key principles:

- **Microservices Design**: Services are split by business domain (user management, stock data, AI analysis, news processing)
- **Event-Driven Communication**: Asynchronous message queues for inter-service communication
- **Stateless Services**: All services are stateless to support horizontal scaling
- **Multi-Layer Caching**: Memory, Redis, and database caching for optimal performance
- **Plugin-Based Data Sources**: Extensible adapter pattern for multiple data providers

### High-Level Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React SPA     │    │   API Gateway    │    │  Load Balancer  │
│   (CloudFront)  │◄──►│  (AWS Gateway)   │◄──►│   (ALB/ELB)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │ User Service │ │Stock Service│ │ AI Service │
        │  (Fargate)   │ │  (Fargate)  │ │ (Fargate)  │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │   Users DB   │ │  Stocks DB  │ │ Redis Cache│
        │ (RDS Postgres│ │(RDS Postgres│ │(ElastiCache│
        └──────────────┘ └─────────────┘ └────────────┘
```

### Data Flow Architecture

```
External APIs → Data Ingestion Service → Message Queue → Processing Services → Database → Cache → API → Frontend
     │                    │                   │              │           │        │      │
     │                    │                   │              │           │        │      │
Alpha Vantage         Lambda Functions    SQS/Redis      Stock Service   PostgreSQL  Redis   React
EDINET API           Scheduled Jobs       Event Bus      AI Service      Normalized  L1/L2   SPA
News APIs            Error Handling       Dead Letter    News Service    Schema      Cache   
```

### Data Source Architecture

The platform implements a tiered data source classification system:

**Tier 1 Critical (99.9% SLA)**
- Stock price data (Alpha Vantage primary, Yahoo Finance Japan secondary)
- Financial statements (EDINET API primary, company IR scraping secondary)
- Basic company information

**Tier 2 Important (99.0% SLA)**
- News data (News API, RSS feeds)
- Market sentiment analysis
- Currency exchange rates (JPY/USD, JPY/EUR, JPY/CNY)

**Tier 3 Enhancement (95.0% SLA)**
- Macroeconomic indicators (Bank of Japan API, Federal Reserve API)
- Policy data and regulatory changes
- Commodity prices and international market data

## Components and Interfaces

### Frontend Components

#### Core React Components

**Dashboard Component**
- Displays market indices (Nikkei 225, TOPIX)
- Shows hot stocks section (gainers, losers, most traded)
- Provides search functionality with autocomplete
- Manages user watchlist display

**StockAnalysis Component**
- AI-powered analysis display (short/mid/long term)
- Interactive TradingView charts integration
- Financial data tables and visualizations
- News feed with sentiment indicators

**Authentication Components**
- Login/Register forms with validation
- OAuth integration (Google, LINE)
- Password reset functionality
- User profile management

#### State Management Structure

```typescript
interface AppState {
  auth: {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
  };
  stocks: {
    searchResults: Stock[];
    selectedStock: Stock | null;
    watchlist: Stock[];
    marketIndices: MarketIndex[];
  };
  analysis: {
    currentAnalysis: AIAnalysis | null;
    analysisHistory: AIAnalysis[];
    isLoading: boolean;
  };
  ui: {
    theme: 'light' | 'dark';
    notifications: Notification[];
  };
}
```

### Backend Services

#### User Service (FastAPI)

**Endpoints:**
- `POST /auth/register` - User registration with email validation
- `POST /auth/login` - User authentication with JWT token generation
- `POST /auth/oauth/{provider}` - OAuth authentication (Google, LINE)
- `POST /auth/password-reset` - Password reset functionality
- `GET /users/profile` - Get user profile and preferences
- `PUT /users/profile` - Update user profile
- `GET /users/subscription` - Get subscription details and quotas
- `POST /users/subscription/upgrade` - Handle subscription upgrades

**Key Classes:**
```python
class UserService:
    def __init__(self, db: Database, auth_provider: AuthProvider, email_service: EmailService):
        self.db = db
        self.auth = auth_provider
        self.email_service = email_service
    
    async def register_user(self, user_data: UserRegistration) -> User:
        # Hash password, create user, send verification email
        pass
    
    async def authenticate_user(self, credentials: LoginCredentials) -> AuthToken:
        # Validate credentials, generate JWT token
        pass
    
    async def oauth_authenticate(self, provider: str, oauth_data: dict) -> AuthToken:
        # Handle Google/LINE OAuth authentication
        pass
    
    async def get_user_profile(self, user_id: str) -> UserProfile:
        # Retrieve user profile with preferences
        pass
```

#### Stock Data Service (FastAPI)

**Endpoints:**
- `GET /stocks/search` - Fuzzy search by ticker/company name
- `GET /stocks/{ticker}` - Get comprehensive stock details
- `GET /stocks/{ticker}/price-history` - Get OHLCV historical data
- `GET /stocks/{ticker}/financials` - Get financial reports from EDINET
- `GET /stocks/{ticker}/news` - Get related news with sentiment
- `GET /market/indices` - Get Nikkei 225, TOPIX real-time data
- `GET /market/hot-stocks` - Get gainers, losers, most traded

**Data Source Adapters:**
```python
class DataSourceRegistry:
    def __init__(self):
        self.registered_sources = {}
        self.source_health_status = {}
        self.cost_tracker = {}
    
    def register_source(self, source_id: str, adapter_class, config: dict, priority: int = 1):
        # Register new data source with priority and health monitoring
        pass
    
    async def fetch_data(self, data_type: str, parameters: dict) -> dict:
        # Smart data retrieval with automatic failover
        pass
    
    async def health_check_all(self) -> dict:
        # Monitor health of all registered sources
        pass

class StockPriceAdapter:
    def __init__(self, provider_config: dict):
        self.config = provider_config
        self.client = self._init_client()
    
    async def fetch_daily_prices(self, ticker: str, start_date: str, end_date: str) -> List[dict]:
        # Unified interface for fetching price data from multiple providers
        pass
    
    def _normalize_alpha_vantage_data(self, raw_data: dict, start_date: str, end_date: str) -> List[dict]:
        # Normalize Alpha Vantage data to internal format
        pass

class FinancialDataAdapter:
    async def fetch_latest_reports(self, ticker: str, report_types: List[str]) -> List[dict]:
        # Fetch financial reports from EDINET API
        pass
    
    def _parse_xbrl_financial_data(self, xbrl_content: str) -> dict:
        # Parse XBRL/iXBRL financial data
        pass
```

#### AI Analysis Service (FastAPI)

**Endpoints:**
- `POST /analysis/generate` - Generate comprehensive AI analysis
- `GET /analysis/{ticker}/latest` - Get latest cached analysis
- `GET /analysis/{ticker}/history` - Get analysis history
- `POST /analysis/batch` - Batch analysis for multiple stocks

**AI Processing Pipeline:**
```python
class AIAnalysisService:
    def __init__(self, llm_client: LLMClient, data_service: StockDataService, cost_manager: CostManager):
        self.llm = llm_client
        self.data_service = data_service
        self.cost_manager = cost_manager
    
    async def generate_analysis(self, ticker: str, analysis_type: str) -> AIAnalysis:
        # 1. Check cache first to avoid unnecessary LLM calls
        cached_analysis = await self._check_cache(ticker, analysis_type)
        if cached_analysis and self.cost_manager.should_use_cache(ticker, cached_analysis.generated_at):
            return cached_analysis
        
        # 2. Gather multi-source data
        price_data = await self.data_service.get_price_history(ticker)
        financial_data = await self.data_service.get_financials(ticker)
        news_data = await self.data_service.get_news_sentiment(ticker)
        
        # 3. Transform data for LLM consumption
        context = self.prepare_analysis_context(price_data, financial_data, news_data)
        
        # 4. Generate analysis using LLM with cost control
        prompt = self.build_analysis_prompt(context, analysis_type)
        estimated_cost = self.cost_manager.estimate_cost(len(prompt), 2000)
        
        if not await self.cost_manager.can_afford(estimated_cost):
            raise BudgetExceededException()
        
        result = await self.llm.generate(prompt)
        
        # 5. Validate, cache, and track cost
        validated_result = self.validate_analysis(result)
        await self.cache_analysis(ticker, validated_result)
        await self.cost_manager.record_usage(ticker, estimated_cost)
        
        return validated_result
    
    def prepare_analysis_context(self, price_data, financial_data, news_data) -> dict:
        # Transform raw data into LLM-friendly format
        pass
    
    def build_analysis_prompt(self, context: dict, analysis_type: str) -> str:
        # Build structured prompt for different analysis types
        pass

class GeminiAnalysisClient:
    def __init__(self, api_key: str):
        self.client = genai.GenerativeModel('gemini-pro')
        self.cost_tracker = CostTracker()
    
    async def generate_stock_analysis(self, prompt: str, ticker: str) -> dict:
        # Generate analysis with cost tracking and validation
        pass
```

#### News Processing Service (FastAPI)

**Endpoints:**
- `GET /news/stock/{ticker}` - Get news related to specific stock
- `GET /news/sentiment/{ticker}` - Get sentiment timeline
- `POST /news/analyze-sentiment` - Analyze sentiment for text

**Japanese Sentiment Analysis:**
```python
class JapaneseSentimentAnalyzer:
    def __init__(self):
        from transformers import pipeline
        self.classifier = pipeline(
            "sentiment-analysis",
            model="nlp-waseda/roberta-base-japanese-sentiment",
            tokenizer="nlp-waseda/roberta-base-japanese-sentiment"
        )
    
    async def analyze_batch(self, texts: List[str]) -> List[dict]:
        # Batch sentiment analysis for Japanese text
        pass

class NewsDataAdapter:
    def __init__(self):
        self.sentiment_analyzer = JapaneseSentimentAnalyzer()
    
    async def fetch_stock_related_news(self, ticker: str, company_name: str, days_back: int = 7) -> List[dict]:
        # Fetch and analyze news from multiple sources
        pass
```

### Database Schema Design

#### Core Tables Structure

**Users Domain:**
```sql
-- Core authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profiles and preferences
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    display_name VARCHAR(50),
    avatar_url VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'Asia/Tokyo',
    notification_preferences JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- OAuth identities
CREATE TABLE user_oauth_identities (
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (provider, provider_user_id)
);
```

**Subscription & Billing Domain:**
```sql
-- Subscription plans
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    plan_name VARCHAR(50) UNIQUE NOT NULL,
    price_monthly INTEGER NOT NULL, -- in Japanese Yen
    features JSONB DEFAULT '{}',
    api_quota_daily INTEGER DEFAULT 10,
    ai_analysis_quota_daily INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    status VARCHAR(20) CHECK (status IN ('active', 'inactive', 'cancelled', 'expired')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Stocks Domain:**
```sql
-- Stock master data
CREATE TABLE stocks (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name_jp VARCHAR(255) NOT NULL,
    company_name_en VARCHAR(255),
    sector_jp VARCHAR(100),
    industry_jp VARCHAR(100),
    description TEXT,
    logo_url VARCHAR(255),
    listing_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily stock metrics
CREATE TABLE stock_daily_metrics (
    ticker VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    date DATE NOT NULL,
    market_cap BIGINT,
    pe_ratio DECIMAL(10, 2),
    pb_ratio DECIMAL(10, 2),
    dividend_yield DECIMAL(5, 4),
    shares_outstanding BIGINT,
    PRIMARY KEY (ticker, date)
);

-- Price history (OHLCV)
CREATE TABLE stock_price_history (
    ticker VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    date DATE NOT NULL,
    open NUMERIC(14,4) NOT NULL,
    high NUMERIC(14,4) NOT NULL,
    low NUMERIC(14,4) NOT NULL,
    close NUMERIC(14,4) NOT NULL,
    volume BIGINT NOT NULL,
    adjusted_close NUMERIC(14,4),
    PRIMARY KEY (ticker, date)
);

-- Financial reports
CREATE TABLE financial_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    fiscal_year INT NOT NULL,
    fiscal_period VARCHAR(10) CHECK (fiscal_period IN ('Q1','Q2','Q3','Q4','FY')),
    report_type VARCHAR(20) CHECK (report_type IN ('quarterly', 'annual')),
    announced_at TIMESTAMPTZ NOT NULL,
    source_url VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, fiscal_year, fiscal_period)
);

-- Financial report line items (EAV model for extensibility)
CREATE TABLE financial_report_line_items (
    report_id UUID NOT NULL REFERENCES financial_reports(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(20, 2) NOT NULL,
    unit VARCHAR(20) DEFAULT 'JPY',
    period_type VARCHAR(10) CHECK (period_type IN ('quarterly', 'annual', 'ytd')),
    PRIMARY KEY (report_id, metric_name)
);
```

**News, AI Analysis & Logs Domain:**
```sql
-- News articles
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_url VARCHAR(512) UNIQUE,
    headline TEXT NOT NULL,
    content_summary TEXT,
    source VARCHAR(100),
    author VARCHAR(255),
    published_at TIMESTAMPTZ NOT NULL,
    sentiment_label VARCHAR(20) CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    sentiment_score NUMERIC(5, 4), -- from -1.0 to 1.0
    language VARCHAR(10) DEFAULT 'ja',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stock-news relationships
CREATE TABLE stock_news_link (
    article_id UUID NOT NULL REFERENCES news_articles(id),
    ticker VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    relevance_score DECIMAL(3, 2) DEFAULT 1.0, -- from 0.0 to 1.0
    PRIMARY KEY (article_id, ticker)
);

-- AI analysis cache
CREATE TABLE ai_analysis_cache (
    ticker VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    analysis_date DATE NOT NULL,
    analysis_type VARCHAR(50) CHECK (analysis_type IN ('short_term','mid_term','long_term','comprehensive')),
    model_version VARCHAR(100) NOT NULL,
    prompt_hash VARCHAR(64),
    analysis_result JSONB NOT NULL,
    confidence_score DECIMAL(3,2),
    processing_time_ms INTEGER,
    cost_usd NUMERIC(10,8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ticker, analysis_date, analysis_type, model_version)
);

-- API usage logs
CREATE TABLE api_usage_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    api_provider VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255),
    request_type VARCHAR(50),
    cost_usd NUMERIC(10,8),
    response_time_ms INTEGER,
    status_code INTEGER,
    request_timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- User watchlists
CREATE TABLE user_watchlists (
    user_id UUID NOT NULL REFERENCES users(id),
    ticker VARCHAR(10) NOT NULL REFERENCES stocks(ticker),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    PRIMARY KEY (user_id, ticker)
);
```

### External API Integration

#### Data Source Configuration

**Primary Data Sources:**
```python
DATA_SOURCES = {
    "stock_prices": {
        "primary": {
            "provider": "alpha_vantage",
            "api_key": "your_api_key",
            "rate_limit": "5_calls_per_minute",
            "cost_per_call": "$0.01",
            "data_delay": "real_time",
            "supported_markets": ["TSE", "JPX"]
        },
        "secondary": {
            "provider": "yahoo_finance_japan",
            "api_endpoint": "https://query1.finance.yahoo.com/v8/finance/chart/",
            "rate_limit": "2000_calls_per_hour",
            "cost_per_call": "free",
            "data_delay": "15_minutes"
        },
        "tertiary": {
            "provider": "stooq",
            "api_endpoint": "https://stooq.com/q/d/l/",
            "rate_limit": "unlimited",
            "cost_per_call": "free",
            "data_delay": "end_of_day"
        }
    },
    "financial_data": {
        "primary": {
            "provider": "edinet_api",
            "base_url": "https://disclosure.edinet-fsa.go.jp/api/v1/documents.json",
            "format": "xbrl",
            "cost": "free",
            "official": True
        },
        "secondary": {
            "provider": "company_ir_scraping",
            "target_sites": "investor_relations_pages",
            "format": "pdf_parsing",
            "cost": "compute_intensive"
        }
    },
    "news_data": {
        "primary": {
            "provider": "news_api",
            "endpoint": "https://newsapi.org/v2/everything",
            "cost_per_call": "$0.0001",
            "rate_limit": "1000_calls_per_day",
            "sources": ["reuters.co.jp", "nikkei.com"]
        },
        "secondary": {
            "provider": "rss_feeds",
            "sources": [
                "https://www.nikkei.com/rss/",
                "https://feeds.reuters.com/reuters/JPdomesticNews",
                "https://news.yahoo.co.jp/rss/topics/business.xml"
            ],
            "cost": "free",
            "update_frequency": "hourly"
        }
    }
}
```

#### LLM Integration Strategy

**Google Gemini Integration:**
```python
class GeminiAnalysisClient:
    def __init__(self, api_key: str):
        self.client = genai.GenerativeModel('gemini-pro')
        self.cost_tracker = CostTracker()
    
    async def generate_stock_analysis(self, prompt: str, ticker: str) -> dict:
        # Cost estimation and budget check
        estimated_cost = self.estimate_cost(len(prompt))
        if not await self.cost_tracker.can_afford(estimated_cost):
            raise BudgetExceededException()
        
        # Generate analysis
        response = await self.client.generate_content(prompt)
        
        # Parse and validate response
        parsed_result = self.parse_analysis_response(response.text)
        
        # Track actual cost
        await self.cost_tracker.record_usage(ticker, estimated_cost)
        
        return parsed_result

# Hierarchical Prompt Templates
PROMPT_TEMPLATES = {
    "data_preprocessing": """Convert the following raw data into structured analytical inputs:
Stock price data: {price_data}
Financial metrics: {financial_metrics}
News sentiment: {news_sentiment}
Please extract key trends, anomalies, and significant changes, and output in JSON format.""",

    "short_term_analysis": """As a professional technical analyst, conduct a short-term (1–4 week) analysis of {company_name} ({ticker}) based on the following data:
Technical indicators: {technical_indicators}
Recent news sentiment: {recent_sentiment}
Volume changes: {volume_analysis}
Please output in JSON format:
{{
  "rating": "Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish",
  "confidence": 0.0–1.0,
  "key_factors": ["Factor 1", "Factor 2", "Factor 3"],
  "price_target_range": {{"min": price, "max": price}},
  "risk_factors": ["Risk 1", "Risk 2"]
}}""",

    "fundamental_analysis": """As a fundamental analysis expert, analyze the long-term investment value of {company_name} based on the following financial data:
Financial ratios: {financial_ratios}
Industry comparison: {industry_comparison}
Growth trends: {growth_trends}
Please provide a detailed valuation and investment recommendation."""
}
```

#### Cost Control and Optimization

**Cost Management System:**
```python
class CostOptimizer:
    def __init__(self):
        self.cost_budgets = {
            "daily_budget": 100.00,  # Daily budget (USD)
            "monthly_budget": 2500.00,
            "emergency_buffer": 200.00
        }
        self.current_costs = {"daily": 0.0, "monthly": 0.0}
    
    async def should_allow_api_call(self, source_id: str, estimated_cost: float) -> dict:
        # Check remaining budget
        if self.current_costs["daily"] + estimated_cost > self.cost_budgets["daily_budget"]:
            return {
                "allowed": False,
                "reason": "daily_budget_exceeded",
                "alternative": "use_cached_data_or_free_source"
            }
        
        return {"allowed": True, "reason": "within_budget"}

class IntelligentCacheManager:
    def __init__(self):
        self.cache_policies = {
            "stock_prices": {"ttl": 300, "priority": "high"},      # 5 minutes
            "financial_data": {"ttl": 86400, "priority": "high"},  # 24 hours
            "news_data": {"ttl": 3600, "priority": "medium"},      # 1 hour
            "macro_data": {"ttl": 21600, "priority": "low"}        # 6 hours
        }
    
    async def get_cached_data(self, cache_key: str, data_type: str) -> dict:
        # Retrieve data from intelligent cache with TTL validation
        pass
    
    async def cache_data(self, cache_key: str, data: dict, data_type: str):
        # Store data into intelligent cache with appropriate TTL
        pass
```

## Data Models

### Core Data Models

#### Stock Data Models

```python
from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional

class Stock(BaseModel):
    ticker: str
    company_name_jp: str
    company_name_en: Optional[str]
    sector_jp: Optional[str]
    industry_jp: Optional[str]
    description: Optional[str]
    is_active: bool = True

class PriceData(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float]

class FinancialMetrics(BaseModel):
    ticker: str
    fiscal_year: int
    fiscal_period: str
    revenue: Optional[float]
    operating_income: Optional[float]
    net_income: Optional[float]
    total_assets: Optional[float]
    shareholders_equity: Optional[float]
```

#### AI Analysis Models

```python
class AIAnalysisRequest(BaseModel):
    ticker: str
    analysis_type: str  # 'short_term', 'mid_term', 'long_term'
    force_refresh: bool = False

class AIAnalysisResult(BaseModel):
    ticker: str
    analysis_type: str
    rating: str  # 'Strong Bullish', 'Bullish', 'Neutral', 'Bearish', 'Strong Bearish'
    confidence: float  # 0.0 to 1.0
    key_factors: List[str]
    price_target_range: dict  # {'min': float, 'max': float}
    risk_factors: List[str]
    reasoning: str
    generated_at: datetime
    model_version: str

class NewsArticle(BaseModel):
    id: str
    headline: str
    content_summary: Optional[str]
    source: str
    published_at: datetime
    sentiment_label: str  # 'positive', 'negative', 'neutral'
    sentiment_score: float  # -1.0 to 1.0
    relevance_score: float  # 0.0 to 1.0
```

#### User and Subscription Models

```python
class User(BaseModel):
    id: str
    email: str
    email_verified: bool
    created_at: datetime

class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str]
    timezone: str = "Asia/Tokyo"
    notification_preferences: dict

class Subscription(BaseModel):
    user_id: str
    plan_id: int
    status: str  # 'active', 'inactive', 'cancelled', 'expired'
    current_period_start: datetime
    current_period_end: datetime
    api_quota_daily: int
    ai_analysis_quota_daily: int
```

## Error Handling

### Error Classification and Response Strategy

#### Error Categories

```python
class ErrorCategory(Enum):
    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"
    BUSINESS_ERROR = "business_error"
    EXTERNAL_API_ERROR = "external_api_error"

class KessanException(Exception):
    def __init__(self, message: str, category: ErrorCategory, details: dict = None):
        self.message = message
        self.category = category
        self.details = details or {}
        super().__init__(message)

# Specific exception types
class InvalidTickerException(KessanException):
    def __init__(self, ticker: str):
        super().__init__(
            f"Invalid ticker symbol: {ticker}",
            ErrorCategory.USER_ERROR,
            {"ticker": ticker}
        )

class DataSourceUnavailableException(KessanException):
    def __init__(self, source: str):
        super().__init__(
            f"Data source unavailable: {source}",
            ErrorCategory.EXTERNAL_API_ERROR,
            {"source": source}
        )
```

#### Error Handling Middleware

```python
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except KessanException as e:
        return handle_kessan_exception(e)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "request_id": str(uuid.uuid4())}
        )

def handle_kessan_exception(e: KessanException) -> JSONResponse:
    status_codes = {
        ErrorCategory.USER_ERROR: 400,
        ErrorCategory.SYSTEM_ERROR: 500,
        ErrorCategory.BUSINESS_ERROR: 422,
        ErrorCategory.EXTERNAL_API_ERROR: 503
    }
    
    return JSONResponse(
        status_code=status_codes[e.category],
        content={
            "error": e.message,
            "category": e.category.value,
            "details": e.details
        }
    )
```

### Graceful Degradation Strategy

```python
class GracefulDegradationService:
    async def get_stock_analysis(self, ticker: str) -> dict:
        try:
            # Try primary AI analysis
            return await self.ai_service.generate_analysis(ticker)
        except AIServiceUnavailableException:
            # Fall back to cached analysis
            cached = await self.cache.get_latest_analysis(ticker)
            if cached:
                cached['is_cached'] = True
                cached['cache_age'] = self.calculate_cache_age(cached)
                return cached
            
            # Fall back to basic technical analysis
            return await self.generate_basic_analysis(ticker)
        except Exception as e:
            logger.error(f"All analysis methods failed for {ticker}: {e}")
            return self.get_error_analysis_response(ticker)
```

## Testing Strategy

### Testing Pyramid Structure

#### Unit Tests (70% of test coverage)

**Backend Service Tests:**
```python
# Example: Stock service unit tests
class TestStockService:
    @pytest.fixture
    def stock_service(self):
        mock_db = Mock()
        mock_data_source = Mock()
        return StockService(mock_db, mock_data_source)
    
    async def test_get_stock_by_ticker_success(self, stock_service):
        # Arrange
        expected_stock = Stock(ticker="7203", company_name_jp="トヨタ自動車")
        stock_service.db.get_stock.return_value = expected_stock
        
        # Act
        result = await stock_service.get_stock("7203")
        
        # Assert
        assert result.ticker == "7203"
        assert result.company_name_jp == "トヨタ自動車"
    
    async def test_get_stock_invalid_ticker(self, stock_service):
        # Arrange
        stock_service.db.get_stock.return_value = None
        
        # Act & Assert
        with pytest.raises(InvalidTickerException):
            await stock_service.get_stock("INVALID")
```

**Frontend Component Tests:**
```typescript
// Example: Dashboard component tests
describe('Dashboard Component', () => {
  it('should display market indices on load', async () => {
    const mockIndices = [
      { name: 'Nikkei 225', value: 28000, change: 150 }
    ];
    
    render(<Dashboard />, {
      preloadedState: {
        stocks: { marketIndices: mockIndices }
      }
    });
    
    expect(screen.getByText('Nikkei 225')).toBeInTheDocument();
    expect(screen.getByText('28000')).toBeInTheDocument();
  });
  
  it('should handle search functionality', async () => {
    render(<Dashboard />);
    
    const searchInput = screen.getByPlaceholderText('Search stocks...');
    fireEvent.change(searchInput, { target: { value: 'Toyota' } });
    
    await waitFor(() => {
      expect(screen.getByText('7203 - トヨタ自動車')).toBeInTheDocument();
    });
  });
});
```

#### Integration Tests (20% of test coverage)

**API Integration Tests:**
```python
class TestStockAnalysisIntegration:
    @pytest.mark.integration
    async def test_full_analysis_pipeline(self, test_client):
        # Test the complete flow from API request to AI analysis
        response = await test_client.post(
            "/analysis/generate",
            json={"ticker": "7203", "analysis_type": "short_term"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "7203"
        assert data["rating"] in ["Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish"]
        assert 0.0 <= data["confidence"] <= 1.0
```

#### End-to-End Tests (10% of test coverage)

**User Journey Tests:**
```typescript
// Example: E2E test using Playwright
test('complete stock analysis user journey', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('[data-testid=email]', 'test@example.com');
  await page.fill('[data-testid=password]', 'password123');
  await page.click('[data-testid=login-button]');
  
  // Search for stock
  await page.fill('[data-testid=stock-search]', 'Toyota');
  await page.click('[data-testid=search-result-7203]');
  
  // Verify analysis is displayed
  await expect(page.locator('[data-testid=ai-analysis]')).toBeVisible();
  await expect(page.locator('[data-testid=stock-chart]')).toBeVisible();
  
  // Add to watchlist
  await page.click('[data-testid=add-to-watchlist]');
  await expect(page.locator('[data-testid=watchlist-success]')).toBeVisible();
});
```

### Performance Testing Strategy

```python
# Load testing configuration
LOAD_TEST_SCENARIOS = {
    "normal_load": {
        "concurrent_users": 100,
        "duration": "10m",
        "ramp_up": "2m"
    },
    "peak_load": {
        "concurrent_users": 500,
        "duration": "5m",
        "ramp_up": "1m"
    },
    "stress_test": {
        "concurrent_users": 1000,
        "duration": "3m",
        "ramp_up": "30s"
    }
}

# Performance benchmarks
PERFORMANCE_TARGETS = {
    "api_response_time_p95": "500ms",
    "page_load_time_lcp": "2.5s",
    "database_query_p95": "100ms",
    "ai_analysis_generation": "10s"
}
```

### Monitoring and Observability

```python
# Application metrics
MONITORING_METRICS = {
    "business_metrics": [
        "daily_active_users",
        "analysis_requests_per_user",
        "subscription_conversion_rate",
        "ai_analysis_accuracy"
    ],
    "technical_metrics": [
        "api_response_time",
        "error_rate",
        "cache_hit_rate",
        "database_connection_pool_usage"
    ],
    "cost_metrics": [
        "ai_api_costs_daily",
        "data_source_costs",
        "infrastructure_costs"
    ]
}

# Alerting rules
ALERT_RULES = {
    "critical": {
        "api_error_rate > 5%": "immediate_pagerduty",
        "database_connections > 80%": "scale_up_trigger",
        "ai_service_down": "immediate_slack_alert"
    },
    "warning": {
        "api_response_time > 1000ms": "slack_notification",
        "daily_ai_costs > budget * 0.8": "cost_alert"
    }
}
```

## Deployment Architecture

### AWS Infrastructure Design

```yaml
# Infrastructure as Code (Terraform/CloudFormation)
services:
  frontend:
    type: "static_site"
    hosting: "aws_s3 + cloudfront"
    build: "react_spa"
    
  api_gateway:
    type: "managed_service"
    provider: "aws_api_gateway"
    features: ["rate_limiting", "authentication", "monitoring"]
    
  user_service:
    type: "container"
    platform: "aws_fargate"
    auto_scaling: "cpu_based"
    database: "users_db"
    
  stock_data_service:
    type: "container"
    platform: "aws_fargate"
    auto_scaling: "memory_based"
    database: "stocks_db"
    
  ai_analysis_service:
    type: "container"
    platform: "aws_fargate"
    external_apis: ["gemini_api", "openai_api"]
    cost_monitoring: "enabled"
    
  data_ingestion_service:
    type: "scheduled_jobs"
    platform: "aws_lambda"
    triggers: ["cron", "s3_events", "sqs_messages"]

databases:
  primary_db:
    type: "aws_rds_postgresql"
    version: "15.3"
    instance_class: "db.t3.medium"
    multi_az: true
    backup_retention: "30_days"
    
  cache_layer:
    type: "aws_elasticache_redis"
    version: "7.0"
    node_type: "cache.t3.micro"
    cluster_mode: "enabled"
```

### Environment Configuration

```yaml
# Multi-environment configuration
environments:
  development:
    database_size: "db.t3.micro"
    cache_size: "cache.t3.micro"
    auto_scaling_min: 1
    auto_scaling_max: 2
    
  staging:
    database_size: "db.t3.small"
    cache_size: "cache.t3.small"
    auto_scaling_min: 1
    auto_scaling_max: 3
    load_testing: "enabled"
    
  production:
    database_size: "db.t3.large"
    cache_size: "cache.t3.medium"
    auto_scaling_min: 2
    auto_scaling_max: 10
    monitoring: "full_stack"
    backup_strategy: "cross_region"
```