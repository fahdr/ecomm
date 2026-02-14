"""
Keyword rank history model for tracking position changes over time.

Stores historical rank positions for each tracked keyword, enabling
trend analysis, comparison across time periods, and rank change
calculations (e.g., current vs 7 days ago, current vs 30 days ago).

For Developers:
    Each row records a single rank check result. A ``rank_position``
    of None means the keyword was not found in the search results
    (i.e., ranked beyond position 100). The ``checked_at`` timestamp
    enables time-series queries for graphing rank history.

For QA Engineers:
    Verify that rank checks create history entries.
    Test rank change calculations (7d, 30d deltas).
    Test with None positions (keyword not ranked).

For Project Managers:
    Keyword history enables the "rank over time" chart feature,
    which is a key engagement driver for returning users.

For End Users:
    View how your keyword rankings have changed over time.
    Track improvements after implementing SEO recommendations.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KeywordHistory(Base):
    """
    A historical rank position record for a tracked keyword.

    Attributes:
        id: Unique identifier (UUID v4).
        keyword_id: Foreign key to the parent KeywordTracking record.
        rank_position: Search result position at check time (None = not ranked).
        checked_at: Timestamp when the rank was checked.
        keyword_tracking: Related KeywordTracking record.
    """

    __tablename__ = "keyword_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    keyword_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_tracking.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    keyword_tracking = relationship("KeywordTracking", back_populates="history_entries", lazy="selectin")
