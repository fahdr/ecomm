"""
Store Connection model for the SpyDrop service.

StoreConnection represents a link between a SpyDrop user and their own
e-commerce store (Shopify, WooCommerce, or the ecomm platform). This
allows SpyDrop to import the user's own catalog for comparison against
competitor products.

For Developers:
    The ``api_key_encrypted`` and ``api_secret_encrypted`` fields store
    encrypted credentials. In production, use a proper encryption layer
    (e.g., Fernet or AWS KMS). For now, values are stored as-is.

    The ``platform`` field determines which API connector is used when
    syncing the user's catalog.

For QA Engineers:
    Test connection CRUD via /api/v1/connections endpoints.
    Verify that API keys are never returned in plain text in responses.
    Test the connection test endpoint (POST /connections/{id}/test).

For Project Managers:
    Store connections enable the "compare my store vs competitors"
    workflow. Users link their store, then SpyDrop can automatically
    identify overlapping products and pricing gaps.

For End Users:
    Connect your store to SpyDrop so we can compare your products and
    prices against your competitors. We never modify your store data.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreConnection(Base):
    """
    A connection between a SpyDrop user and their own e-commerce store.

    Stores the platform type, store URL, and encrypted API credentials
    needed to access the user's store catalog via the platform's API.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: E-commerce platform ('shopify', 'woocommerce', 'platform').
        store_url: The user's store URL.
        api_key_encrypted: Encrypted API key for the store's API.
        api_secret_encrypted: Encrypted API secret for the store's API.
        is_active: Whether the connection is currently active.
        last_synced_at: Timestamp of the most recent catalog sync.
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
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="E-commerce platform: shopify, woocommerce, platform"
    )
    store_url: Mapped[str] = mapped_column(
        String(2048), nullable=False, doc="The user's store URL"
    )
    api_key_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, doc="Encrypted API key"
    )
    api_secret_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, doc="Encrypted API secret"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, doc="Whether the connection is active"
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Last catalog sync timestamp"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", lazy="selectin")


# Avoid circular import
from app.models.user import User  # noqa: E402
