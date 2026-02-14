"""
Store connection model for linking external e-commerce platforms.

Stores encrypted credentials for connecting to external platforms
(Shopify, WooCommerce, BigCommerce, etc.) so that RankPilot can
fetch product data, page URLs, and metadata for SEO analysis.

For Developers:
    API keys and secrets are stored in encrypted form (api_key_encrypted,
    api_secret_encrypted). In production, use a proper encryption layer
    (e.g., Fernet) before persisting. The ``is_active`` flag controls
    whether the connection is currently usable. ``last_synced_at`` tracks
    the most recent data sync.

For QA Engineers:
    Test CRUD via /api/v1/connections endpoints.
    Verify that encrypted fields are stored (not exposed in plain text).
    Test the connection test endpoint (mock always succeeds).

For Project Managers:
    Store connections enable RankPilot to pull real product/page data
    for more accurate SEO audits and content generation.

For End Users:
    Connect your e-commerce store to RankPilot to enable automatic
    product data import for SEO optimization.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreConnection(Base):
    """
    An external e-commerce store connection for data import.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: E-commerce platform name ('shopify', 'woocommerce', 'bigcommerce', 'custom').
        store_url: The store's base URL (e.g., 'https://myshop.myshopify.com').
        api_key_encrypted: Encrypted API key for store access.
        api_secret_encrypted: Encrypted API secret for store access.
        is_active: Whether the connection is currently active/usable.
        last_synced_at: Timestamp of the most recent data sync.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
    """

    __tablename__ = "store_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    store_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="store_connections", lazy="selectin")
