"""
Scan result model for the SpyDrop service.

Each scan of a competitor store produces a ScanResult that summarizes
what changed: how many new products were found, how many were removed,
and how many had price changes.

For Developers:
    ScanResult records are created by the `scan_competitor` Celery task.
    They provide an audit trail of all scanning activity and are displayed
    in the Scans page timeline.

For QA Engineers:
    Test scan triggering via POST /api/v1/scans/{competitor_id}/trigger.
    Verify scan results are created with correct counts.
    Check the scan history endpoint returns results in reverse chronological order.

For Project Managers:
    Scans are the engine that powers SpyDrop. Each scan discovers new
    products, detects price changes, and identifies removed items.
    Scan frequency depends on the user's plan tier.

For End Users:
    View your scan history to see what changed in each competitor's store.
    Trigger manual scans from the Scans page.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScanResult(Base):
    """
    Summary of a single competitor store scan.

    Attributes:
        id: Unique identifier (UUID v4).
        competitor_id: Foreign key to the scanned competitor.
        new_products_count: Number of new products discovered.
        removed_products_count: Number of products no longer available.
        price_changes_count: Number of products with price changes.
        scanned_at: Timestamp when the scan was performed.
        duration_seconds: How long the scan took (in seconds).
        competitor: Related Competitor record.
    """

    __tablename__ = "scan_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    new_products_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    removed_products_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    price_changes_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship(
        "Competitor", back_populates="scan_results", lazy="selectin"
    )


from app.models.competitor import Competitor  # noqa: E402
