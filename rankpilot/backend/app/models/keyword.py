"""
Keyword tracking model for SEO rank monitoring.

Tracks keyword positions in search engine results over time. Users can add
keywords they want to monitor, and the system periodically checks their
ranking position. Keyword count is limited by the plan's max_secondary limit.

For Developers:
    `current_rank` and `previous_rank` allow calculating rank changes.
    `search_volume` and `difficulty` are populated by the rank checking task.
    The background task `update_keyword_ranks` periodically refreshes ranks.
    Keywords are tracked per-site, not globally.

For QA Engineers:
    Test keyword CRUD via /api/v1/keywords.
    Verify plan limits: free gets 20 keywords, pro gets 200, enterprise unlimited.
    Verify rank change calculations (current_rank - previous_rank).
    Test with None ranks (new keyword, not yet checked).

For Project Managers:
    Keyword tracking is the secondary monetization lever — higher tiers
    allow more keywords. Rank data helps users measure SEO effectiveness.

For End Users:
    Track how your target keywords rank in search results. See trends
    over time with up/down indicators showing rank improvements.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KeywordTracking(Base):
    """
    A keyword being tracked for search engine ranking.

    Attributes:
        id: Unique identifier (UUID v4).
        site_id: Foreign key to the parent site.
        keyword: The search keyword/phrase being tracked.
        current_rank: Current search result position (1 = top, None = not ranked).
        previous_rank: Previous search result position for trend tracking.
        search_volume: Estimated monthly search volume for this keyword.
        difficulty: SEO difficulty score from 0.0 to 100.0.
        tracked_since: When this keyword was first added for tracking.
        last_checked: When the rank was last checked/updated.
        site: Related Site record.
    """

    __tablename__ = "keyword_tracking"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    current_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    tracked_since: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    site = relationship("Site", back_populates="keyword_trackings", lazy="selectin")
    history_entries = relationship(
        "KeywordHistory", back_populates="keyword_tracking", cascade="all, delete-orphan", lazy="selectin"
    )
