"""Add GDPR compliance fields to users table

Revision ID: 004
Revises: 003
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Add GDPR compliance fields to users table."""
    
    # Add GDPR compliance fields to users table
    op.add_column('users', sa.Column('gdpr_consents', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('deleted_at', sa.String(), nullable=True))
    op.add_column('users', sa.Column('data_retention_until', sa.String(), nullable=True))
    
    # Add anonymized flag to api_usage_logs table
    op.add_column('api_usage_logs', sa.Column('anonymized', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add anonymized flag to ai_analysis_cache table if it exists
    try:
        op.add_column('ai_analysis_cache', sa.Column('requested_by', sa.String(), nullable=True))
        op.add_column('ai_analysis_cache', sa.Column('anonymized', sa.Boolean(), nullable=False, server_default='false'))
    except Exception:
        # Table might not exist yet, skip
        pass
    
    # Create index for soft-deleted users
    op.create_index('ix_users_is_deleted', 'users', ['is_deleted'])


def downgrade():
    """Remove GDPR compliance fields from users table."""
    
    # Remove indexes
    op.drop_index('ix_users_is_deleted', table_name='users')
    
    # Remove columns from ai_analysis_cache table
    try:
        op.drop_column('ai_analysis_cache', 'anonymized')
        op.drop_column('ai_analysis_cache', 'requested_by')
    except Exception:
        # Table might not exist, skip
        pass
    
    # Remove column from api_usage_logs table
    op.drop_column('api_usage_logs', 'anonymized')
    
    # Remove GDPR compliance fields from users table
    op.drop_column('users', 'data_retention_until')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'is_deleted')
    op.drop_column('users', 'gdpr_consents')