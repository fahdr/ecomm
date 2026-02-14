"""
Store connection model for linking FlowSend to external e-commerce platforms.

Stores encrypted API credentials for Shopify, WooCommerce, and other
e-commerce platforms. Used to import contacts, sync order data, and
trigger automated flows based on store events.

For Developers:
    - ``api_key_encrypted`` and ``api_secret_encrypted`` should be encrypted
      at rest. For the MVP, they are stored as-is (encryption wrapper TBD).
    - ``platform`` is a free-text string: "shopify", "woocommerce", "bigcommerce".
    - ``last_synced_at`` tracks the most recent successful data sync.
    - Multi-tenant isolation: all queries must filter by ``user_id``.

For QA Engineers:
    Test: CRUD operations, connection test endpoint, unique constraint
    (user + platform + store_url), deactivation, sync timestamp updates.

For Project Managers:
    Store connections are the bridge between FlowSend and the user's
    e-commerce platform. They enable contact import and event-driven flows.

For End Users:
    Connect your online store to automatically import customers and
    trigger email sequences based on orders and browsing behavior.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreConnection(Base):
    """
    A connection to an external e-commerce store.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: E-commerce platform name ("shopify", "woocommerce", etc.).
        store_url: The store's base URL (e.g., "https://mystore.myshopify.com").
        api_key_encrypted: Encrypted API key for the store.
        api_secret_encrypted: Encrypted API secret for the store.
        is_active: Whether this connection is currently active.
        last_synced_at: Timestamp of the last successful data sync.
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
    store_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
