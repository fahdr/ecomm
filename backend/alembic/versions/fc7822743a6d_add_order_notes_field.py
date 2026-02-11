"""Add order notes field.

Revision ID: fc7822743a6d
Revises: 08742fa19426
Create Date: 2026-02-11

Adds an internal notes/memo text field to the orders table.
Store owners can use this for internal communication that
is not visible to customers.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fc7822743a6d"
down_revision = "08742fa19426"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add notes column to orders table."""
    op.add_column("orders", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove notes column from orders table."""
    op.drop_column("orders", "notes")
