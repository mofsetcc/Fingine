"""Add query optimization indexes

Revision ID: 003
Revises: 002
Create Date: 2025-01-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add comprehensive query optimization indexes."""
    
    # === User and Authentication Optimization ===
    
    # OAuth lookup optimization
    op.create_index(
        'idx_oauth_provider_lookup',
        'user_oauth_identities',
        ['provider', 'provider_user_id', 'user_id']
    )
    
    # User profile quick access
    op.create_index(
        'idx_user_profiles_timezone',
        'user_profiles',
        ['timezone', 'user_id']
    )
    
    # === Subscription and Billing Optimization ===
    
    # Active plan lookup
    op.create_index(
        'idx_plans_active_lookup',
        'plans',
        ['is_active', 'plan_name', 'price_monthly'],
        postgresql_where=sa.text('is_active = true')
    )
    
    # Subscription period queries
    op.create_index(
        'idx_subscriptions_period',
        'subscriptions',
        ['current_period_end', 'status', 'user_id']
    )
    
    # === Financial Data Optimization ===
    
    # Financial report line items lookup
    op.create_index(
        'idx_financial_line_items_metric',
        'financial_report_line_items',
        ['metric_name', 'report_id', 'metric_value']
    )
    
    # Financial reports by announcement date
    op.create_index(
        'idx_financial_reports_announced',
        'financial_reports',
        ['ticker', sa.text('announced_at DESC'), 'report_type']
    )
    
    # === News and Sentiment Optimization ===
    
    # News source and language filtering
    op.create_index(
        'idx_news_source_lang',
        'news_articles',
        ['source', 'language', sa.text('published_at DESC')]
    )
    
    # Sentiment analysis queries
    op.create_index(
        'idx_news_sentiment_score',
        'news_articles',
        ['sentiment_label', sa.text('sentiment_score DESC'), sa.text('published_at DESC')],
        postgresql_where=sa.text('sentiment_score IS NOT NULL')
    )
    
    # Stock news relevance optimization
    op.create_index(
        'idx_stock_news_relevance',
        'stock_news_link',
        ['ticker', sa.text('relevance_score DESC'), 'article_id']
    )
    
    # === AI Analysis Cache Optimization ===
    
    # Analysis cache by cost and performance
    op.create_index(
        'idx_ai_analysis_cost',
        'ai_analysis_cache',
        ['ticker', 'analysis_type', sa.text('cost_usd DESC')]
    )
    
    # Analysis cache by processing time
    op.create_index(
        'idx_ai_analysis_performance',
        'ai_analysis_cache',
        ['analysis_type', sa.text('processing_time_ms ASC'), 'ticker']
    )
    
    # Analysis cache by confidence
    op.create_index(
        'idx_ai_analysis_confidence',
        'ai_analysis_cache',
        ['ticker', sa.text('confidence_score DESC'), 'analysis_date']
    )
    
    # === API Usage and Monitoring Optimization ===
    
    # API usage by provider and cost
    op.create_index(
        'idx_api_usage_provider_cost',
        'api_usage_logs',
        ['api_provider', sa.text('cost_usd DESC'), sa.text('request_timestamp DESC')]
    )
    
    # API usage by endpoint performance
    op.create_index(
        'idx_api_usage_endpoint_perf',
        'api_usage_logs',
        ['endpoint', sa.text('response_time_ms ASC'), sa.text('request_timestamp DESC')]
    )
    
    # API usage by status code for error monitoring
    op.create_index(
        'idx_api_usage_status_errors',
        'api_usage_logs',
        ['status_code', sa.text('request_timestamp DESC')],
        postgresql_where=sa.text('status_code >= 400')
    )
    
    # Daily usage aggregation
    op.create_index(
        'idx_api_usage_daily_agg',
        'api_usage_logs',
        ['user_id', sa.text("date_trunc('day', to_timestamp(request_timestamp, 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'))"), 'api_provider']
    )
    
    # === Stock Price History Advanced Optimization ===
    
    # Price history for technical analysis
    op.create_index(
        'idx_price_history_technical',
        'stock_price_history',
        ['ticker', sa.text('date DESC'), 'close', 'high', 'low', 'volume']
    )
    
    # Price history for volatility calculations
    op.create_index(
        'idx_price_history_volatility',
        'stock_price_history',
        ['ticker', sa.text('date DESC'), sa.text('(high - low) DESC')]
    )
    
    # === Watchlist Optimization ===
    
    # Watchlist with stock info
    op.create_index(
        'idx_watchlist_with_notes',
        'user_watchlists',
        ['user_id', sa.text('created_at DESC')],
        postgresql_where=sa.text('notes IS NOT NULL')
    )
    
    # === Composite Indexes for Complex Queries ===
    
    # Stock analysis dashboard query
    op.create_index(
        'idx_stock_dashboard_composite',
        'stocks',
        ['is_active', 'sector_jp', 'industry_jp', 'ticker'],
        postgresql_where=sa.text('is_active = true')
    )
    
    # Recent price with metrics
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recent_price_with_metrics
        ON stock_price_history (ticker, date DESC, close, volume)
        WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    """)
    
    # Recent financial reports
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recent_financial_reports
        ON financial_reports (ticker, fiscal_year DESC, fiscal_period, announced_at DESC)
        WHERE fiscal_year >= EXTRACT(YEAR FROM CURRENT_DATE) - 2
    """)
    
    # === Statistics Collection for Query Planner ===
    
    # Update table statistics for better query planning
    op.execute("ANALYZE stocks")
    op.execute("ANALYZE stock_price_history")
    op.execute("ANALYZE stock_daily_metrics")
    op.execute("ANALYZE financial_reports")
    op.execute("ANALYZE news_articles")
    op.execute("ANALYZE ai_analysis_cache")
    op.execute("ANALYZE api_usage_logs")


def downgrade() -> None:
    """Remove query optimization indexes."""
    
    # Drop concurrent indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_recent_financial_reports")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_recent_price_with_metrics")
    
    # Drop regular indexes
    op.drop_index('idx_stock_dashboard_composite', table_name='stocks')
    op.drop_index('idx_watchlist_with_notes', table_name='user_watchlists')
    op.drop_index('idx_price_history_volatility', table_name='stock_price_history')
    op.drop_index('idx_price_history_technical', table_name='stock_price_history')
    op.drop_index('idx_api_usage_daily_agg', table_name='api_usage_logs')
    op.drop_index('idx_api_usage_status_errors', table_name='api_usage_logs')
    op.drop_index('idx_api_usage_endpoint_perf', table_name='api_usage_logs')
    op.drop_index('idx_api_usage_provider_cost', table_name='api_usage_logs')
    op.drop_index('idx_ai_analysis_confidence', table_name='ai_analysis_cache')
    op.drop_index('idx_ai_analysis_performance', table_name='ai_analysis_cache')
    op.drop_index('idx_ai_analysis_cost', table_name='ai_analysis_cache')
    op.drop_index('idx_stock_news_relevance', table_name='stock_news_link')
    op.drop_index('idx_news_sentiment_score', table_name='news_articles')
    op.drop_index('idx_news_source_lang', table_name='news_articles')
    op.drop_index('idx_financial_reports_announced', table_name='financial_reports')
    op.drop_index('idx_financial_line_items_metric', table_name='financial_report_line_items')
    op.drop_index('idx_subscriptions_period', table_name='subscriptions')
    op.drop_index('idx_plans_active_lookup', table_name='plans')
    op.drop_index('idx_user_profiles_timezone', table_name='user_profiles')
    op.drop_index('idx_oauth_provider_lookup', table_name='user_oauth_identities')