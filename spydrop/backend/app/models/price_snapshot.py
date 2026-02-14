"""
PriceSnapshot model for the SpyDrop service.

Records individual price observations for competitor products over time.
Unlike the JSON-based price_history on CompetitorProduct, PriceSnapshot
provides a proper relational table for efficient querying, aggregation,
and indexing of historical price data.

For Developers:
    Each PriceSnapshot represents a single price observation at a point
    in time. Use the ``price_service`` functions to create snapshots and
    query price history. The ``captured_at`` field uses timezone-aware
    timestamps for accurate time-series analysis.

For QA Engineers:
    Test that snapshots are created during scans, that the price history
    query returns the correct time range, and that the price change
    detection identifies significant price movements.

For Project Managers:
    PriceSnapshot enables the price trend charts and price change
    detection features. It stores granular price data that supports
    analytics like "average price over 30 days" and "biggest price drops."

For End Users:
    View price history charts for competitor products. SpyDrop tracks
    every price change so you can see trends and make informed decisions.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PriceSnapshot(Base):
    """
    A single price observation for a competitor product.

    Captures the price at a specific point in time, enabling time-series
    analysis, trend detection, and price change alerting.

    Attributes:
        id: Unique identifier (UUID v4).
        competitor_product_id: Foreign key to the tracked CompetitorProduct.
        price: The observed price at capture time.
        currency: Currency code (default 'USD').
        captured_at: Timestamp when the price was recorded.
        product: Related CompetitorProduct record.
    """

    __tablename__ = "price_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitor_products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    price: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Observed product price"
    )
    currency: Mapped[str] = mapped_column(
        String(10), default="USD", nullable=False, doc="Currency code"
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the price was captured",
    )

    # Relationships
    product: Mapped["CompetitorProduct"] = relationship(
        "CompetitorProduct", lazy="selectin"
    )


# Avoid circular import
from app.models.competitor import CompetitorProduct  # noqa: E402
