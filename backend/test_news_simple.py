#!/usr/bin/env python3
"""
Simple test script for news data collection functionality.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.adapters.news_adapter import NewsDataAdapter


async def test_news_adapter():
    """Test the news adapter functionality."""
    print("Testing NewsDataAdapter...")
    
    # Create adapter instance
    config = {
        "news_api_key": None  # Test without API key
    }
    adapter = NewsDataAdapter(config=config)
    
    # Test health check
    print("Testing health check...")
    try:
        health = await adapter.health_check()
        print(f"Health status: {health.status.value}")
        print(f"Response time: {health.response_time_ms}ms")
        if health.error_message:
            print(f"Error: {health.error_message}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test rate limit info
    print("\nTesting rate limit info...")
    try:
        rate_limit = await adapter.get_rate_limit_info()
        print(f"Requests per minute: {rate_limit.requests_per_minute}")
        print(f"Requests per hour: {rate_limit.requests_per_hour}")
        print(f"Requests per day: {rate_limit.requests_per_day}")
    except Exception as e:
        print(f"Rate limit info failed: {e}")
    
    # Test cost info
    print("\nTesting cost info...")
    try:
        cost_info = await adapter.get_cost_info()
        print(f"Cost per request: ${cost_info.cost_per_request}")
        print(f"Currency: {cost_info.currency}")
        print(f"Monthly budget: ${cost_info.monthly_budget}")
    except Exception as e:
        print(f"Cost info failed: {e}")
    
    # Test news collection (this will likely fail without real APIs, but we can test the structure)
    print("\nTesting news collection...")
    try:
        articles = await adapter.get_news(
            symbol="7203",
            keywords=["Toyota", "earnings"],
            limit=5
        )
        print(f"Collected {len(articles)} articles")
        for i, article in enumerate(articles[:2]):  # Show first 2
            print(f"Article {i+1}: {article.get('headline', 'No headline')}")
    except Exception as e:
        print(f"News collection failed (expected): {e}")
    
    # Test article normalization
    print("\nTesting article normalization...")
    try:
        # Test News API article normalization
        sample_news_api_article = {
            "title": "Test News Article",
            "description": "This is a test description",
            "url": "https://example.com/test",
            "publishedAt": "2024-01-01T12:00:00Z",
            "source": {"name": "Test Source"},
            "author": "Test Author"
        }
        
        normalized = adapter._normalize_news_api_article(sample_news_api_article)
        if normalized:
            print("News API normalization successful:")
            print(f"  Headline: {normalized['headline']}")
            print(f"  Source: {normalized['source']}")
            print(f"  ID: {normalized['id']}")
        else:
            print("News API normalization failed")
    except Exception as e:
        print(f"Article normalization failed: {e}")
    
    # Test deduplication
    print("\nTesting deduplication...")
    try:
        test_articles = [
            {"id": "1", "headline": "Test Article 1", "content_summary": "Content 1"},
            {"id": "2", "headline": "Test Article 2", "content_summary": "Content 2"},
            {"id": "1", "headline": "Duplicate Article", "content_summary": "Content 3"},  # Duplicate ID
            {"id": "3", "headline": "Test Article 1", "content_summary": "Content 4"},  # Similar headline
        ]
        
        deduplicated = adapter._deduplicate_articles(test_articles)
        print(f"Original articles: {len(test_articles)}")
        print(f"After deduplication: {len(deduplicated)}")
        
        for article in deduplicated:
            print(f"  - {article['headline']} (ID: {article['id']})")
    except Exception as e:
        print(f"Deduplication test failed: {e}")
    
    # Test relevance scoring
    print("\nTesting relevance scoring...")
    try:
        test_articles = [
            {
                "headline": "Toyota reports strong earnings",
                "content_summary": "Toyota Motor Corp announced strong quarterly results",
                "source": "Nikkei",
                "published_at": "2024-01-01T12:00:00Z"
            },
            {
                "headline": "General market update",
                "content_summary": "Stock market sees mixed results",
                "source": "Other Source",
                "published_at": "2024-01-01T10:00:00Z"
            }
        ]
        
        scored = adapter._score_relevance(test_articles, "7203", ["earnings"])
        print("Relevance scoring results:")
        for article in scored:
            print(f"  - {article['headline']}: {article.get('relevance_score', 0):.2f}")
    except Exception as e:
        print(f"Relevance scoring test failed: {e}")
    
    # Clean up
    await adapter.close()
    print("\nNews adapter tests completed!")


if __name__ == "__main__":
    asyncio.run(test_news_adapter())