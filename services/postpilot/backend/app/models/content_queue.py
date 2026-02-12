"""
Content queue model for AI-assisted post generation workflow.

The content queue allows users to feed product data (from their dropshipping
store or manual input) and receive AI-generated captions and hashtag suggestions.
Queue items go through a review workflow: pending -> approved -> posted (or rejected).

For Developers:
    `product_data` is a JSON dict that stores arbitrary product information
    (title, description, price, images, etc.) used as input for AI caption
    generation. `ai_generated_content` stores the raw AI output. `platforms`
    is a PostgreSQL ARRAY indicating which platforms the content targets.

For QA Engineers:
    Test the queue workflow: create item -> generate AI content -> approve/reject.
    Verify that approved items can be converted to scheduled posts.
    Test with various product data shapes to ensure the AI generation handles
    edge cases gracefully.

For Project Managers:
    The content queue is a key differentiator — it automates the creative
    process by generating captions from product data, reducing the time
    from product import to social media post.

For End Users:
    Add your products to the content queue, and PostPilot will generate
    engaging captions automatically. Review, edit, and approve them before
    scheduling for publication.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String

from app.models.base import Base


class QueueStatus(str, enum.Enum):
    """
    Lifecycle status of a content queue item.

    Attributes:
        pending: Waiting for AI generation or manual review.
        approved: Reviewed and approved for scheduling.
        rejected: Rejected during review, will not be published.
        posted: Content has been converted to a post and published.
    """

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    posted = "posted"


class ContentQueue(Base):
    """
    A content queue item for AI-assisted post generation.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        product_data: JSON dict with product information for AI input.
        ai_generated_content: AI-generated caption text (None before generation).
        platforms: Target social platforms for this content.
        status: Current queue status (pending, approved, rejected, posted).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
    """

    __tablename__ = "content_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ai_generated_content: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    platforms: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus), default=QueueStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="content_queue_items", lazy="selectin")
