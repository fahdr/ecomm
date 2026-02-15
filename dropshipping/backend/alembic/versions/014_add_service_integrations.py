"""Add service_integrations table.

Revision ID: 014_service_integrations
Revises: cf8e9cba6be5
Create Date: 2026-02-12

Creates the ``service_integrations`` table for tracking user connections
to external SaaS microservices (TrendScout, ContentForge, RankPilot,
FlowSend, SpyDrop, PostPilot, AdScale, ShopChat). Also creates the
``servicename`` and ``servicetier`` PostgreSQL enums.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "014_service_integrations"
down_revision = "cf8e9cba6be5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create service_integrations table with servicename/servicetier enums."""
    op.create_table(
        "service_integrations",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "service_name",
            sa.Enum(
                "trendscout", "contentforge", "rankpilot", "flowsend",
                "spydrop", "postpilot", "adscale", "shopchat",
                name="servicename",
            ),
            nullable=False,
        ),
        sa.Column("service_user_id", sa.String(length=255), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column(
            "tier",
            sa.Enum("free", "starter", "growth", "pro", name="servicetier"),
            nullable=False,
            server_default="free",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("store_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "provisioned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "service_name", name="uq_user_service"),
    )
    op.create_index(
        op.f("ix_service_integrations_user_id"),
        "service_integrations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_service_integrations_store_id"),
        "service_integrations",
        ["store_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop service_integrations table and enums."""
    op.drop_index(
        op.f("ix_service_integrations_store_id"),
        table_name="service_integrations",
    )
    op.drop_index(
        op.f("ix_service_integrations_user_id"),
        table_name="service_integrations",
    )
    op.drop_table("service_integrations")

    # Drop enum types created by create_table
    sa.Enum(name="servicetier").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="servicename").drop(op.get_bind(), checkfirst=True)
