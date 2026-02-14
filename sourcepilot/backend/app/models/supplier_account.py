"""
Supplier account model for managing connections to supplier platforms.

Each SupplierAccount stores the user's credentials for a specific
supplier platform, enabling automated product fetching and price monitoring.

For Developers:
    The ``credentials`` JSON column stores platform-specific credentials
    that should be encrypted at the application layer in production. Use the
    ``is_active`` flag to temporarily disable an account without deleting it.

For Project Managers:
    Supplier accounts let users connect their supplier platform credentials
    for automated product discovery and import. Multiple accounts per
    platform are supported.

For QA Engineers:
    Test CRUD operations on supplier accounts. Verify that credentials are
    never returned in plain text in responses. Test cascading deletes
    when the owning user is removed.

For End Users:
    Connect your supplier accounts (AliExpress, CJ Dropshipping, Spocket)
    to enable automated product searching and one-click imports.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SupplierAccount(Base):
    """
    A user's connection to a supplier platform with credentials.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Human-readable display name for the account.
        platform: Supplier platform identifier (aliexpress, cjdropshipping, etc.).
        credentials: JSON dict of platform-specific credentials (api_key, api_secret, etc.).
        is_active: Whether the account is currently enabled.
        last_synced_at: Timestamp of the most recent sync with the supplier.
        created_at: Account creation timestamp.
        updated_at: Last modification timestamp.
        owner: Back-reference to the owning User.
    """

    __tablename__ = "supplier_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    credentials: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
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
    owner = relationship("User", backref="supplier_accounts", lazy="selectin")
