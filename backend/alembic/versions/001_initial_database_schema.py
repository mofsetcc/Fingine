"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-01-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('email_verified_at', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(length=50), nullable=True),
        sa.Column('avatar_url', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create user_oauth_identities table
    op.create_table('user_oauth_identities',
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('provider', 'provider_user_id')
    )

    # Create plans table
    op.create_table('plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_name', sa.String(length=50), nullable=False),
        sa.Column('price_monthly', sa.Integer(), nullable=False),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('api_quota_daily', sa.Integer(), nullable=False),
        sa.Column('ai_analysis_quota_daily', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plans_plan_name'), 'plans', ['plan_name'], unique=True)

    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_period_start', sa.String(), nullable=False),
        sa.Column('current_period_end', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive', 'cancelled', 'expired')", name='check_subscription_status'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)

    # Create stocks table
    op.create_table('stocks',
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('company_name_jp', sa.String(length=255), nullable=False),
        sa.Column('company_name_en', sa.String(length=255), nullable=True),
        sa.Column('sector_jp', sa.String(length=100), nullable=True),
        sa.Column('industry_jp', sa.String(length=100), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('logo_url', sa.String(length=255), nullable=True),
        sa.Column('listing_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('ticker')
    )

    # Create stock_daily_metrics table
    op.create_table('stock_daily_metrics',
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('market_cap', sa.BigInteger(), nullable=True),
        sa.Column('pe_ratio', postgresql.NUMERIC(precision=10, scale=2), nullable=True),
        sa.Column('pb_ratio', postgresql.NUMERIC(precision=10, scale=2), nullable=True),
        sa.Column('dividend_yield', postgresql.NUMERIC(precision=5, scale=4), nullable=True),
        sa.Column('shares_outstanding', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('ticker', 'date')
    )

    # Create stock_price_history table
    op.create_table('stock_price_history',
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', postgresql.NUMERIC(precision=14, scale=4), nullable=False),
        sa.Column('high', postgresql.NUMERIC(precision=14, scale=4), nullable=False),
        sa.Column('low', postgresql.NUMERIC(precision=14, scale=4), nullable=False),
        sa.Column('close', postgresql.NUMERIC(precision=14, scale=4), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('adjusted_close', postgresql.NUMERIC(precision=14, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('ticker', 'date')
    )

    # Create financial_reports table
    op.create_table('financial_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_period', sa.String(length=10), nullable=False),
        sa.Column('report_type', sa.String(length=20), nullable=False),
        sa.Column('announced_at', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4', 'FY')", name='check_fiscal_period'),
        sa.CheckConstraint("report_type IN ('quarterly', 'annual')", name='check_report_type'),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_financial_reports_ticker_fiscal'), 'financial_reports', ['ticker', 'fiscal_year', 'fiscal_period'], unique=True)

    # Create financial_report_line_items table
    op.create_table('financial_report_line_items',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', postgresql.NUMERIC(precision=20, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('period_type', sa.String(length=10), nullable=True),
        sa.CheckConstraint("period_type IN ('quarterly', 'annual', 'ytd')", name='check_period_type'),
        sa.ForeignKeyConstraint(['report_id'], ['financial_reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('report_id', 'metric_name')
    )

    # Create news_articles table
    op.create_table('news_articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_url', sa.String(length=512), nullable=True),
        sa.Column('headline', sa.String(), nullable=False),
        sa.Column('content_summary', sa.String(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('published_at', sa.String(), nullable=False),
        sa.Column('sentiment_label', sa.String(length=20), nullable=True),
        sa.Column('sentiment_score', postgresql.NUMERIC(precision=5, scale=4), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("sentiment_label IN ('positive', 'negative', 'neutral')", name='check_sentiment_label'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_articles_article_url'), 'news_articles', ['article_url'], unique=True)

    # Create stock_news_link table
    op.create_table('stock_news_link',
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('relevance_score', postgresql.NUMERIC(precision=3, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['news_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('article_id', 'ticker')
    )

    # Create ai_analysis_cache table
    op.create_table('ai_analysis_cache',
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('analysis_type', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=True),
        sa.Column('analysis_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', postgresql.NUMERIC(precision=3, scale=2), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('cost_usd', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("analysis_type IN ('short_term', 'mid_term', 'long_term', 'comprehensive')", name='check_analysis_type'),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('ticker', 'analysis_date', 'analysis_type', 'model_version')
    )

    # Create api_usage_logs table
    op.create_table('api_usage_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('api_provider', sa.String(length=50), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('request_type', sa.String(length=50), nullable=True),
        sa.Column('cost_usd', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('request_timestamp', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_watchlists table
    op.create_table('user_watchlists',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'ticker')
    )

    # Create performance indexes
    op.create_index('idx_stock_price_ticker_date', 'stock_price_history', ['ticker', sa.text('date DESC')])
    op.create_index('idx_stock_daily_metrics_ticker_date', 'stock_daily_metrics', ['ticker', sa.text('date DESC')])
    op.create_index('idx_financial_reports_ticker_year', 'financial_reports', ['ticker', sa.text('fiscal_year DESC'), 'fiscal_period'])
    op.create_index('idx_news_published_at', 'news_articles', [sa.text('published_at DESC')])
    op.create_index('idx_stock_news_ticker', 'stock_news_link', ['ticker', 'article_id'])
    op.create_index('idx_ai_analysis_lookup', 'ai_analysis_cache', ['ticker', sa.text('analysis_date DESC'), 'analysis_type'])
    op.create_index('idx_user_watchlist_user_id', 'user_watchlists', ['user_id'])
    op.create_index('idx_api_usage_user_timestamp', 'api_usage_logs', ['user_id', sa.text('request_timestamp DESC')])
    
    # Composite indexes for complex queries
    op.create_index('idx_news_sentiment_published', 'news_articles', ['sentiment_label', sa.text('published_at DESC')], 
                   postgresql_where=sa.text('sentiment_label IS NOT NULL'))
    
    # Partial indexes for active data
    op.create_index('idx_active_stocks', 'stocks', ['ticker'], postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_active_subscriptions', 'subscriptions', ['user_id', 'status'], 
                   postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_active_subscriptions', table_name='subscriptions')
    op.drop_index('idx_active_stocks', table_name='stocks')
    op.drop_index('idx_news_sentiment_published', table_name='news_articles')
    op.drop_index('idx_api_usage_user_timestamp', table_name='api_usage_logs')
    op.drop_index('idx_user_watchlist_user_id', table_name='user_watchlists')
    op.drop_index('idx_ai_analysis_lookup', table_name='ai_analysis_cache')
    op.drop_index('idx_stock_news_ticker', table_name='stock_news_link')
    op.drop_index('idx_news_published_at', table_name='news_articles')
    op.drop_index('idx_financial_reports_ticker_year', table_name='financial_reports')
    op.drop_index('idx_stock_daily_metrics_ticker_date', table_name='stock_daily_metrics')
    op.drop_index('idx_stock_price_ticker_date', table_name='stock_price_history')
    
    # Drop tables in reverse order
    op.drop_table('user_watchlists')
    op.drop_table('api_usage_logs')
    op.drop_table('ai_analysis_cache')
    op.drop_table('stock_news_link')
    op.drop_table('news_articles')
    op.drop_table('financial_report_line_items')
    op.drop_table('financial_reports')
    op.drop_table('stock_price_history')
    op.drop_table('stock_daily_metrics')
    op.drop_table('stocks')
    op.drop_table('subscriptions')
    op.drop_table('plans')
    op.drop_table('user_oauth_identities')
    op.drop_table('user_profiles')
    op.drop_table('users')