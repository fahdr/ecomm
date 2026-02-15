"""
Store connection model for linking external e-commerce platforms.

Each StoreConnection represents a user's link to an external store
(Shopify, WooCommerce, or the dropshipping platform itself).  The
connection stores encrypted API credentials and tracks sync status.

For Developers:
    ``api_key_encrypted`` and ``api_secret_encrypted`` hold the encrypted
    credentials.  In production, use application-level encryption (e.g.
    Fernet) before writing to these columns.  The ``platform`` column
    uses a constrained string rather than an enum so new platforms can
    be added without migrations.

    The ``is_active`` flag lets users temporarily disable a connection
    without deleting credentials.  ``last_synced_at`` records the most
    recent successful product sync timestamp.

For Project Managers:
    Store connections enable the "import to store" workflow.  Users
    connect their Shopify/WooCommerce store, then push winning
    products from the watchlist directly into their catalog.

For QA Engineers:
    Test CRUD operations on connections.  Verify that encrypted fields
    are never returned in plain text in API responses.  Test the
    ``/test`` endpoint for connectivity validation.  Test cascading
    deletes when the owning user is removed.

For End Users:
    Connect your online store under the Connections tab to enable
    one-click product imports from your watchlist.  Supported
    platforms: Shopify, WooCommerce, and the dropshipping platform.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreConnection(Base):
    """
    A user's connection to an external e-commerce store.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: Store platform identifier — 'shopify', 'woocommerce',
                  or 'platform' (the dropshipping platform itself).
        store_url: Base URL of the connected store
                   (e.g. 'https://my-shop.myshopify.com').
        api_key_encrypted: Encrypted API key / access token.
        api_secret_encrypted: Encrypted API secret (optional, platform-dependent).
        is_active: Whether the connection is currently enabled.
        last_synced_at: Timestamp of the most recent successful sync.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Back-reference to the owning User.
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
        String(50), nullable=False, index=True
    )
    store_url: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    api_key_encrypted: Mapped[str] = mapped_column(
        String(1000), nullable=False
    )
    api_secret_encrypted: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
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
    owner = relationship("User", backref="store_connections", lazy="selectin")
