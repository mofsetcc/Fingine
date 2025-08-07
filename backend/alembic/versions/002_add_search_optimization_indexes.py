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
    
    # Basic search indexes for development (simplified)
    op.create_index('idx_stocks_company_name_jp', 'stocks', ['company_name_jp'])
    op.create_index('idx_stocks_company_name_en', 'stocks', ['company_name_en'])
    
    # Basic indexes for development (trigram indexes commented out)
    # op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    
    # Basic sector and industry indexes
    op.create_index('idx_stocks_sector_jp', 'stocks', ['sector_jp'])
    op.create_index('idx_stocks_industry_jp', 'stocks', ['industry_jp'])
    
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
    op.drop_index('idx_stocks_industry_jp', table_name='stocks')
    op.drop_index('idx_stocks_sector_jp', table_name='stocks')
    
    # Drop basic search indexes
    op.drop_index('idx_stocks_company_name_en', table_name='stocks')
    op.drop_index('idx_stocks_company_name_jp', table_name='stocks')