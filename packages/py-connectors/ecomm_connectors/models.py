"""
SQLAlchemy model mixin for store connections.

For Developers:
    Import ``StoreConnectionMixin`` and apply it to your service's
    declarative base to add the ``store_connections`` table. This keeps
    the schema consistent across all services that support store linking.

    Example::

        from ecomm_connectors.models import StoreConnectionMixin
        from ecomm_core.models.base import Base

        class StoreConnection(StoreConnectionMixin, Base):
            __tablename__ = "store_connections"

For QA Engineers:
    Each service that uses store connections will have an identical
    ``store_connections`` table structure.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ecomm_connectors.base import PlatformType


class StoreConnectionMixin:
    """
    Mixin providing store connection columns.

    For Developers:
        Combine with a SQLAlchemy ``Base`` class to create the table.
        Credentials are stored as a JSON-encoded string in the
        ``credentials_encrypted`` text column. Encryption is handled
        at the application layer.

    Attributes:
        id: Primary key UUID.
        user_id: The owning user's UUID (FK to ``users.id``).
        platform: Ecommerce platform type (shopify, woocommerce, platform).
        store_url: The store's base URL.
        store_name: Human-friendly display name.
        credentials_encrypted: Encrypted JSON blob of API credentials.
        is_active: Whether this connection is enabled.
        last_synced_at: Timestamp of last successful data sync.
        created_at: When the connection was created.
        updated_at: When the connection was last modified.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(
        Enum(PlatformType, name="platform_type", create_constraint=False),
        nullable=False,
    )
    store_url: Mapped[str] = mapped_column(String(512), nullable=False)
    store_name: Mapped[str] = mapped_column(String(255), default="")
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
