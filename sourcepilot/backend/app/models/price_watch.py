"""
Price watch model for monitoring supplier product price changes.

PriceWatch entries track specific products on supplier platforms and
alert users when prices change. A background Celery task periodically
checks all active watches and updates the current_price field.

For Developers:
    Use ``Numeric(10, 2)`` for price fields to avoid floating-point
    precision issues. The ``price_changed`` flag is set by the sync
    task when a price difference is detected. Reset it when the user
    acknowledges the change.

    The ``store_id`` column doubles as ``connection_id`` in the API.
    The ``product_url`` column stores the user-provided URL; it is
    separate from the legacy ``source_url`` which was auto-resolved.

For Project Managers:
    Price watches are a secondary metered resource. They help users
    maintain competitive pricing by tracking supplier cost changes.

For QA Engineers:
    Test price change detection logic. Verify that deactivated watches
    are skipped during sync. Test filtering by connection_id (store_id).

For End Users:
    Add price watches to stay informed when supplier prices change.
    You'll see a notification in the dashboard when a tracked product's
    price goes up or down.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PriceWatch(Base):
    """
    A price monitoring entry for a supplier product.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        store_id: UUID of the store/connection this watch is associated with (nullable).
        source: Supplier platform where the product is listed.
        source_product_id: Product identifier on the supplier platform (nullable).
        product_url: User-provided URL of the product to monitor.
        source_url: Legacy resolved URL of the product on the supplier platform.
        threshold_percent: Percentage change that triggers an alert (default 10.0).
        last_price: The price recorded when the watch was created or last synced (nullable).
        current_price: The most recently observed price (may differ from last_price).
        price_changed: Whether the current price differs from the last known price.
        last_checked_at: Timestamp of the most recent price check.
        is_active: Whether the watch is currently enabled.
        created_at: Watch creation timestamp.
        updated_at: Last modification timestamp.
        owner: Back-reference to the owning User.
    """

    __tablename__ = "price_watches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    source_product_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    product_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.0"), server_default="10.0"
    )
    last_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    price_changed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="price_watches", lazy="selectin")

    @property
    def connection_id(self) -> uuid.UUID | None:
        """Alias for store_id exposed as connection_id in API responses.

        Returns:
            The store_id value, representing the connection identifier.
        """
        return self.store_id
