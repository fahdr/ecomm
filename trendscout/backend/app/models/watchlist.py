"""
Watchlist model for tracking promising product research results.

Users add ResearchResult records to their Watchlist for ongoing monitoring.
Each WatchlistItem tracks the user's intent: watching (monitoring),
imported (pushed to storefront), or dismissed (rejected).

For Developers:
    WatchlistItem has a unique constraint on (user_id, result_id) to prevent
    duplicates. The status field drives the tab-based UI in the dashboard.
    Notes is a free-text field for user annotations.

For Project Managers:
    Watchlist items are the secondary metered resource. Free-tier users are
    limited to 25 items; Pro gets 500; Enterprise is unlimited.

For QA Engineers:
    Test: adding a result to watchlist, preventing duplicates (409),
    updating status, filtering by status, and plan limit enforcement.

For End Users:
    Save interesting products from your research results to the Watchlist.
    Organize by status: Watching, Imported, or Dismissed.
    Add notes to remember why you saved a product.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WatchlistItem(Base):
    """
    A user's watchlist entry linking to a specific ResearchResult.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        result_id: Foreign key to the saved ResearchResult.
        status: Tracking status — 'watching', 'imported', or 'dismissed'.
        notes: Optional free-text notes from the user.
        created_at: Timestamp when the item was added to the watchlist.
        updated_at: Timestamp of the last status or notes change.
        result: Eagerly loaded ResearchResult for display.
        owner: Back-reference to the owning User.
    """

    __tablename__ = "watchlist_items"

    __table_args__ = (
        UniqueConstraint("user_id", "result_id", name="uq_watchlist_user_result"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_results.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="watching", nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    result = relationship(
        "ResearchResult", lazy="selectin"
    )
    owner = relationship("User", backref="watchlist_items", lazy="selectin")
