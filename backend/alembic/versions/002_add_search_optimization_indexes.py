"""Add search optimization indexes

Revision ID: 002
Revises: 001
Create Date: 2025-01-23 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes optimized for stock search functionality."""
    
    # Full-text search indexes for company names
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stocks_company_name_jp_gin 
        ON stocks USING gin(to_tsvector('japanese', company_name_jp))
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stocks_company_name_en_gin 
        ON stocks USING gin(to_tsvector('english', coalesce(company_name_en, '')))
        WHERE company_name_en IS NOT NULL
    """)
    
    # Trigram indexes for fuzzy matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    
    op.create_index(
        'idx_stocks_company_name_jp_trgm',
        'stocks',
        ['company_name_jp'],
        postgresql_using='gin',
        postgresql_ops={'company_name_jp': 'gin_trgm_ops'}
    )
    
    op.create_index(
        'idx_stocks_company_name_en_trgm',
        'stocks',
        ['company_name_en'],
        postgresql_using='gin',
        postgresql_ops={'company_name_en': 'gin_trgm_ops'},
        postgresql_where=sa.text('company_name_en IS NOT NULL')
    )
    
    # Sector and industry search indexes
    op.create_index(
        'idx_stocks_sector_trgm',
        'stocks',
        ['sector_jp'],
        postgresql_using='gin',
        postgresql_ops={'sector_jp': 'gin_trgm_ops'},
        postgresql_where=sa.text('sector_jp IS NOT NULL')
    )
    
    op.create_index(
        'idx_stocks_industry_trgm',
        'stocks',
        ['industry_jp'],
        postgresql_using='gin',
        postgresql_ops={'industry_jp': 'gin_trgm_ops'},
        postgresql_where=sa.text('industry_jp IS NOT NULL')
    )
    
    # Ticker prefix search optimization
    op.create_index(
        'idx_stocks_ticker_prefix',
        'stocks',
        [sa.text('ticker varchar_pattern_ops')]
    )
    
    # Composite index for active stock searches
    op.create_index(
        'idx_stocks_active_search',
        'stocks',
        ['is_active', 'ticker', 'company_name_jp'],
        postgresql_where=sa.text('is_active = true')
    )
    
    # Hot stocks performance indexes
    op.create_index(
        'idx_price_history_latest_by_ticker',
        'stock_price_history',
        ['ticker', sa.text('date DESC'), 'close', 'volume']
    )
    
    # Index for volume-based queries (most traded)
    op.create_index(
        'idx_price_history_volume_desc',
        'stock_price_history',
        [sa.text('date DESC'), sa.text('volume DESC'), 'ticker']
    )
    
    # Index for price change calculations
    op.create_index(
        'idx_price_history_change_calc',
        'stock_price_history',
        ['ticker', sa.text('date DESC'), 'close', 'open']
    )
    
    # Market metrics indexes for hot stocks
    op.create_index(
        'idx_daily_metrics_latest',
        'stock_daily_metrics',
        [sa.text('date DESC'), 'ticker', 'market_cap', 'pe_ratio']
    )


def downgrade() -> None:
    """Remove search optimization indexes."""
    
    # Drop custom indexes
    op.drop_index('idx_daily_metrics_latest', table_name='stock_daily_metrics')
    op.drop_index('idx_price_history_change_calc', table_name='stock_price_history')
    op.drop_index('idx_price_history_volume_desc', table_name='stock_price_history')
    op.drop_index('idx_price_history_latest_by_ticker', table_name='stock_price_history')
    op.drop_index('idx_stocks_active_search', table_name='stocks')
    op.drop_index('idx_stocks_ticker_prefix', table_name='stocks')
    op.drop_index('idx_stocks_industry_trgm', table_name='stocks')
    op.drop_index('idx_stocks_sector_trgm', table_name='stocks')
    op.drop_index('idx_stocks_company_name_en_trgm', table_name='stocks')
    op.drop_index('idx_stocks_company_name_jp_trgm', table_name='stocks')
    
    # Drop full-text search indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_stocks_company_name_en_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_stocks_company_name_jp_gin")