"""
Store connection model for linking to dropshipping stores.

Each StoreConnection represents a user's link to a dropshipping store
where imported products will be published. Users can connect multiple
stores and set one as the default import target.

For Developers:
    The ``store_id`` is an external reference to the dropshipping platform's
    store table. The ``is_default`` flag identifies the primary store for
    quick imports. Only one connection per user should have ``is_default=True``.

For Project Managers:
    Store connections enable the import-to-store workflow. Users must
    connect at least one store before importing products.

For QA Engineers:
    Test CRUD operations. Verify the ``is_default`` constraint (only one
    default per user). Test cascading deletes when the owning user is removed.

For End Users:
    Connect your dropshipping stores under the Connections tab.
    Set a default store for one-click product imports.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreConnection(Base):
    """
    A user's connection to a dropshipping store.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        store_name: Human-readable name of the connected store.
        platform: E-commerce platform type (shopify, woocommerce, etc.).
        store_url: URL of the connected store.
        api_key: Encrypted API key for authenticating with the store's API.
        is_default: Whether this is the user's default import target.
        created_at: Connection creation timestamp.
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
    store_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    store_url: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    api_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="store_connections", lazy="selectin")
