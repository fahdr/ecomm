"""
Image processing job model.

Tracks image downloads, optimization, and format conversion for product
images associated with content generation jobs.

For Developers:
    ImageJob records are created when a generation job includes product images.
    Each image is downloaded from its original URL, resized, converted to the
    target format (default WebP), and stored at an optimized URL.

    Status transitions: pending -> processing -> completed | failed

    The `size_bytes` field tracks the optimized file size. Compare with the
    original to show compression savings in the dashboard.

For QA Engineers:
    Test image processing with valid and invalid URLs.
    Verify status transitions and that failed images have error messages.
    In mock mode, images are not actually downloaded — dimensions and
    sizes are simulated.

For Project Managers:
    Image optimization reduces page load times for storefronts. Each
    processed image counts against the user's monthly image quota
    (5 for free, 100 for pro, unlimited for enterprise).

For End Users:
    When you generate content from a product URL, any product images
    are automatically optimized and converted to WebP format for faster
    loading on your store.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ImageJob(Base):
    """
    An image processing record for a generation job.

    Attributes:
        id: Unique identifier (UUID v4).
        job_id: Foreign key to the parent generation job.
        original_url: The source image URL to process.
        optimized_url: The resulting optimized image URL (after processing).
        format: Output image format (default "webp").
        width: Output image width in pixels.
        height: Output image height in pixels.
        size_bytes: Output file size in bytes.
        status: Processing state — "pending", "processing", "completed", "failed".
        error_message: Error details if processing failed.
        created_at: Record creation timestamp.
        job: The parent GenerationJob.
    """

    __tablename__ = "image_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="webp")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    job = relationship("GenerationJob", back_populates="image_items")
