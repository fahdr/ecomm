"""
Source configuration model for external data source credentials.

Each user can configure one or more data sources (AliExpress, TikTok,
Google Trends, Reddit) with their own API credentials and settings.
SourceConfig records are used at research-run time to authenticate
against external APIs.

For Developers:
    The `credentials` JSON column stores sensitive data (API keys, tokens).
    In production this should be encrypted at rest. The `settings` JSON
    column holds source-specific configuration (regions, categories, etc.).
    The `is_active` flag lets users temporarily disable a source without
    deleting its credentials.

For Project Managers:
    Source configs control which external APIs are available for research.
    Free-tier users can only use AliExpress and Google Trends; paid tiers
    unlock all sources including TikTok and Reddit.

For QA Engineers:
    Test CRUD operations on source configs. Verify that deactivated
    sources are excluded from research runs. Test that credentials are
    never returned in plain text in API responses.

For End Users:
    Connect your external accounts (AliExpress, TikTok, etc.) under the
    Sources tab. Toggle sources on/off and configure regional settings.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SourceConfig(Base):
    """
    User-specific configuration for an external data source.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        source_type: Identifier for the source — 'aliexpress', 'tiktok',
                     'google_trends', or 'reddit'.
        credentials: JSON dict with source-specific auth credentials
                     (API keys, OAuth tokens, etc.). Sensitive — do not expose.
        settings: JSON dict with source-specific settings (region, category
                  filters, language, etc.).
        is_active: Whether the source is currently enabled for research runs.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Back-reference to the owning User.
    """

    __tablename__ = "source_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    credentials: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    settings: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="source_configs", lazy="selectin")
