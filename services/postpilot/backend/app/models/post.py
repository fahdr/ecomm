"""
Post model representing a social media post to be published.

Posts go through a lifecycle: draft -> scheduled -> posted (or failed).
Each post is associated with a social account and optionally scheduled
for a future publish time. Media URLs and hashtags are stored as
PostgreSQL arrays for flexible multi-media content.

For Developers:
    The `status` field is a PostgreSQL Enum with the lifecycle states.
    `scheduled_for` is used by the Celery beat scheduler to pick up
    posts ready for publishing. `media_urls` stores CDN-accessible
    URLs for images or videos. `ARRAY(String)` stores hashtags without
    the `#` prefix (added at render time).

For QA Engineers:
    Test the full post lifecycle: create draft -> schedule -> publish.
    Verify plan limit enforcement on `max_items` (posts per month).
    Test scheduling edge cases: past dates, timezone handling.

For Project Managers:
    Posts are the core content unit. The scheduling system allows users
    to queue content in advance, and the Celery worker publishes them
    at the scheduled time.

For End Users:
    Create posts with text, images, and hashtags. Schedule them for the
    best time, or publish immediately. Track the status of each post
    in the Queue or Calendar view.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PostStatus(str, enum.Enum):
    """
    Lifecycle status of a social media post.

    Attributes:
        draft: Post is being composed but not yet scheduled.
        scheduled: Post has a future publish time set.
        posted: Post was successfully published to the platform.
        failed: Post publication failed (see error_message for details).
    """

    draft = "draft"
    scheduled = "scheduled"
    posted = "posted"
    failed = "failed"


class Post(Base):
    """
    A social media post associated with a connected account.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        account_id: Foreign key to the social account this post targets.
        content: Post caption/text content.
        media_urls: List of media URLs (images, videos) to attach.
        hashtags: List of hashtags (without # prefix).
        platform: Target platform (denormalized from account for quick queries).
        status: Current lifecycle status (draft, scheduled, posted, failed).
        scheduled_for: When the post should be published (None = draft/immediate).
        posted_at: When the post was actually published (None if not yet posted).
        error_message: Error details if publishing failed (None on success).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        account: Related SocialAccount record.
        metrics: Related PostMetrics record.
    """

    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    hashtags: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus), default=PostStatus.draft, nullable=False
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    account = relationship("SocialAccount", back_populates="posts", lazy="selectin")
    metrics = relationship(
        "PostMetrics", back_populates="post", uselist=False, lazy="selectin"
    )
