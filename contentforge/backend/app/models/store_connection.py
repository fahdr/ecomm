"""
Store connection model for linking user accounts to external e-commerce platforms.

Tracks connections to Shopify, WooCommerce, or the parent dropshipping platform
so that generated content can be exported directly to product listings.

For Developers:
    StoreConnection stores encrypted API credentials for each connected store.
    The ``platform`` field uses a string enum ('shopify', 'woocommerce', 'platform').
    API keys are stored encrypted at rest — the ``api_key_encrypted`` and
    ``api_secret_encrypted`` fields hold the ciphertext. In the current
    scaffold, encryption is handled at the application layer before storage.

    Foreign key: ``user_id`` references the ``users`` table with CASCADE delete.

For QA Engineers:
    Test CRUD operations on connections:
    - Create connection with all required fields
    - List connections (only returns current user's)
    - Delete connection by ID
    - Test connectivity endpoint (mock external API call)
    - Verify user isolation (user A cannot see user B's connections)

For Project Managers:
    Store connections enable the "Export to Store" feature — users can push
    generated content directly to their Shopify or WooCommerce product listings
    without copy-pasting. This is a high-value differentiator for Pro/Enterprise.

For End Users:
    Connect your Shopify or WooCommerce store to ContentForge so you can
    export generated content directly to your product listings with one click.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreConnection(Base):
    """
    An external e-commerce store connection for content export.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: E-commerce platform — 'shopify', 'woocommerce', or 'platform'.
        store_url: The store's public URL (e.g., 'mystore.myshopify.com').
        api_key_encrypted: Encrypted API key for store authentication.
        api_secret_encrypted: Encrypted API secret for store authentication.
        is_active: Whether the connection is currently active and usable.
        last_synced_at: Timestamp of the last successful data sync.
        created_at: Connection creation timestamp.
        updated_at: Last modification timestamp.
        user: The owning user (loaded via selectin for eager access).
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
    platform: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    store_url: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    api_key_encrypted: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    api_secret_encrypted: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
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
    user = relationship("User", lazy="selectin")
