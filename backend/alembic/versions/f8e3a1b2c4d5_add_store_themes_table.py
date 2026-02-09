"""add_store_themes_table

Revision ID: f8e3a1b2c4d5
Revises: c95d1ba47018
Create Date: 2026-02-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8e3a1b2c4d5'
down_revision: Union[str, Sequence[str], None] = 'c95d1ba47018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the store_themes table for per-store visual customization."""
    op.create_table(
        'store_themes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_preset', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('colors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('typography', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('styles', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('blocks', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('favicon_url', sa.String(length=500), nullable=True),
        sa.Column('custom_css', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_store_themes_store_id'), 'store_themes', ['store_id'], unique=False)


def downgrade() -> None:
    """Drop the store_themes table."""
    op.drop_index(op.f('ix_store_themes_store_id'), table_name='store_themes')
    op.drop_table('store_themes')
