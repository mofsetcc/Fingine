"""
Production validation configuration for Japanese Stock Analysis Platform.
"""

import os
from typing import Dict, Any, List

# Production environment configuration
PRODUCTION_CONFIG = {
    "database": {
        "validate_connection": True,
        "check_tables": [
            "stocks", "stock_price_history", "stock_daily_metrics",
            "users", "subscriptions", "plans",
            "news_articles", "stock_news_link",
            "ai_analysis_cache", "api_usage_logs"
        ],
        "required_indexes": [
            "idx_stock_price_history_ticker_date",
            "idx_stock_daily_metrics_ticker_date", 
            "idx_news_articles_published_at",
            "idx_stock_news_link_ticker",
            "idx_ai_analysis_cache_ticker_date"
        ]
    },
    
    "data_sources": {
        "alpha_vantage": {
            "enabled": bool(os.getenv("ALPHA_VANTAGE_API_KEY")),
            "api_key": os.getenv("ALPHA_VANTAGE_API_KEY"),
            "test_symbols": ["7203", "AAPL"],
            "required_endpoints": ["GLOBAL_QUOTE", "TIME_SERIES_DAILY"],
            "max_response_time_ms": 5000
        },
        
        "yahoo_finance": {
            "enabled": True,
            "test_symbols": ["7203.T", "6758.T"],
            "required_endpoints": ["chart", "search"],
            "max_response_time_ms": 3000
        },
        
        "edinet": {
            "enabled": True,
            "test_symbols": ["7203", "6758"],
            "required_endpoints": ["documents.json"],
            "max_response_time_ms": 10000
        },
        
        "news_api": {
            "enabled": bool(os.getenv("NEWS_API_KEY")),
            "api_key": os.getenv("NEWS_API_KEY"),
            "test_queries": ["Japan stock market", "トヨタ自動車"],
            "required_sources": ["reuters.co.jp", "nikkei.com"],
            "max_response_time_ms": 5000
        }
    },
    
    "ai_services": {
        "gemini": {
            "enabled": bool(os.getenv("GOOGLE_API_KEY")),
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "test_prompts": [
                "Analyze Toyota stock performance",
                "Provide investment recommendation for Sony"
            ],
            "max_response_time_ms": 15000,
            "required_fields": ["rating", "confidence", "key_factors"]
        }
    },
    
    "performance_thresholds": {
        "database_query_ms": 100,
        "api_response_ms": 5000,
        "ai_analysis_ms": 15000,
        "news_aggregation_ms": 10000,
        "cache_hit_rate_percent": 80
    },
    
    "validation_criteria": {
        "min_stocks_in_db": 10,
        "min_price_records_per_stock": 30,
        "min_news_articles_per_stock": 5,
        "required_subscription_plans": ["Free", "Pro", "Business"],
        "data_freshness_hours": 24
    }
}

# Test data for validation
TEST_STOCKS = [
    {
        "ticker": "7203",
        "company_name_jp": "トヨタ自動車",
        "company_name_en": "Toyota Motor Corporation",
        "expected_sector": "輸送用機器",
        "expected_currency": "JPY"
    },
    {
        "ticker": "6758", 
        "company_name_jp": "ソニーグループ",
        "company_name_en": "Sony Group Corporation",
        "expected_sector": "電気機器",
        "expected_currency": "JPY"
    },
    {
        "ticker": "9984",
        "company_name_jp": "ソフトバンクグループ",
        "company_name_en": "SoftBank Group Corp",
        "expected_sector": "情報・通信業",
        "expected_currency": "JPY"
    }
]

# News sources for validation
NEWS_SOURCES = [
    {
        "name": "Nikkei",
        "url": "https://www.nikkei.com/rss/",
        "language": "ja",
        "expected_articles_per_day": 50
    },
    {
        "name": "Reuters Japan",
        "url": "https://feeds.reuters.com/reuters/JPdomesticNews",
        "language": "ja",
        "expected_articles_per_day": 30
    },
    {
        "name": "Yahoo Finance Japan",
        "url": "https://news.yahoo.co.jp/rss/topics/business.xml",
        "language": "ja",
        "expected_articles_per_day": 40
    }
]

# AI analysis test cases
AI_TEST_CASES = [
    {
        "symbol": "7203",
        "analysis_type": "short_term",
        "expected_fields": ["rating", "confidence", "key_factors", "price_target_range"],
        "min_confidence": 0.6
    },
    {
        "symbol": "6758",
        "analysis_type": "mid_term", 
        "expected_fields": ["rating", "confidence", "key_factors", "risk_factors"],
        "min_confidence": 0.6
    },
    {
        "symbol": "9984",
        "analysis_type": "long_term",
        "expected_fields": ["rating", "confidence", "reasoning"],
        "min_confidence": 0.5
    }
]

# Sentiment analysis test cases
SENTIMENT_TEST_CASES = [
    {
        "text": "トヨタ自動車の業績が好調で株価が上昇している",
        "expected_sentiment": "positive",
        "language": "ja"
    },
    {
        "text": "ソニーの新製品発表により投資家の期待が高まっている",
        "expected_sentiment": "positive", 
        "language": "ja"
    },
    {
        "text": "市場の不安定さにより株価が下落傾向にある",
        "expected_sentiment": "negative",
        "language": "ja"
    }
]

def get_production_config() -> Dict[str, Any]:
    """Get production configuration with environment variable substitution."""
    return PRODUCTION_CONFIG

def get_test_stocks() -> List[Dict[str, Any]]:
    """Get test stock data for validation."""
    return TEST_STOCKS

def get_news_sources() -> List[Dict[str, Any]]:
    """Get news sources for validation."""
    return NEWS_SOURCES

def get_ai_test_cases() -> List[Dict[str, Any]]:
    """Get AI analysis test cases."""
    return AI_TEST_CASES

def get_sentiment_test_cases() -> List[Dict[str, Any]]:
    """Get sentiment analysis test cases."""
    return SENTIMENT_TEST_CASES

def validate_environment() -> Dict[str, bool]:
    """Validate that required environment variables are set."""
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL", 
        "GOOGLE_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "NEWS_API_KEY"
    ]
    
    validation_results = {}
    for var in required_vars:
        validation_results[var] = bool(os.getenv(var))
    
    return validation_results