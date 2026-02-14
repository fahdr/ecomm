"""
Product cache model for storing fetched supplier product data.

The ProductCache provides a time-limited cache of supplier product data
to reduce redundant API calls. Cached entries expire after a configurable
TTL (default 24 hours).

For Developers:
    The ``expires_at`` column determines cache validity. Query with
    ``expires_at > now()`` to get only valid entries. The
    ``source + source_product_id`` combination forms a logical unique
    key for lookups.

For Project Managers:
    The product cache reduces supplier API call volume and improves
    response times for repeated product previews. Cache entries are
    automatically invalidated after 24 hours.

For QA Engineers:
    Test cache hit/miss scenarios. Verify expired entries are not
    returned. Test that new fetches update the cache correctly.

For End Users:
    Product previews load faster after the first view because data
    is cached for up to 24 hours.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.import_job import ImportSource


class ProductCache(Base):
    """
    Cached supplier product data with time-based expiration.

    Attributes:
        id: Unique identifier (UUID v4).
        source: Supplier platform the product was fetched from.
        source_product_id: Product identifier on the supplier platform.
        source_url: URL of the product on the supplier platform.
        product_data: Full product data as fetched from the supplier API.
        expires_at: Cache expiration timestamp (entries invalid after this).
        created_at: Cache entry creation timestamp.
    """

    __tablename__ = "product_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[ImportSource] = mapped_column(
        Enum(ImportSource), nullable=False, index=True
    )
    source_product_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    product_data: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
