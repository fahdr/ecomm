"""merge heads

Revision ID: cf8e9cba6be5
Revises: 067876d001ca, fc7822743a6d
Create Date: 2026-02-11 17:40:29.318918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf8e9cba6be5'
down_revision: Union[str, Sequence[str], None] = ('067876d001ca', 'fc7822743a6d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
