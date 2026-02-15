"""
Post engagement metrics model for tracking social media performance.

Stores aggregated engagement data fetched from social platform APIs.
Metrics are updated periodically by the Celery task `fetch_metrics`.
Each Post has at most one PostMetrics record (one-to-one relationship).

For Developers:
    Metrics are fetched via platform APIs and stored here. The `fetched_at`
    timestamp tracks when the data was last refreshed. In mock mode, random
    data is generated to simulate real engagement metrics.

For QA Engineers:
    Test that metrics are created when `fetch_metrics` task runs.
    Verify that engagement rate calculations are correct:
    `engagement_rate = (likes + comments + shares) / impressions`.

For Project Managers:
    These metrics power the Analytics dashboard, helping users understand
    which posts perform best and optimize their content strategy.

For End Users:
    Track how each post performs with metrics like impressions, reach,
    likes, comments, shares, and clicks. View detailed analytics in
    the Analytics page.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PostMetrics(Base):
    """
    Engagement metrics for a single published post.

    Attributes:
        id: Unique identifier (UUID v4).
        post_id: Foreign key to the associated post (one-to-one).
        impressions: Number of times the post was displayed.
        reach: Number of unique users who saw the post.
        likes: Number of likes/reactions on the post.
        comments: Number of comments on the post.
        shares: Number of shares/reposts of the post.
        clicks: Number of link clicks in the post.
        fetched_at: Timestamp of the last metrics refresh.
        post: Related Post record.
    """

    __tablename__ = "post_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    post = relationship("Post", back_populates="metrics", lazy="selectin")
