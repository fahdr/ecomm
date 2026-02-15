"""
Content generation job and result models.

Tracks generation jobs (from URL, CSV, or manual input) and their
generated content outputs (titles, descriptions, meta tags, etc.).

For Developers:
    GenerationJob is the parent record for a generation request. It tracks
    the source input data, template used, and status. Each job produces
    multiple GeneratedContent records, one per content_type.

    Status transitions: pending -> processing -> completed | failed

    Use `source_type` to determine how to parse `source_data`:
    - "url": source_url has the URL, source_data has scraped product info
    - "csv": source_data has parsed CSV rows
    - "manual": source_data has user-provided product details

For QA Engineers:
    Test the full lifecycle: create job (pending) -> process (processing) ->
    complete (completed) with generated content records.
    Verify plan limits are enforced (free tier: 10 generations/month).
    Test failure path: job transitions to "failed" with error_message.

For Project Managers:
    Generation jobs are the core feature of ContentForge. Each job consumes
    one generation from the user's monthly quota. The generated content
    includes titles, descriptions, SEO meta tags, keywords, and bullet points.

For End Users:
    Each time you generate content for a product, a job is created. You can
    track its progress and view all generated content from the History page.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GenerationJob(Base):
    """
    A content generation job representing a single generation request.

    Each job takes product input data (from URL, CSV, or manual entry),
    applies a template, and produces multiple content items via the AI engine.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        source_url: Product URL to scrape (for URL-based generation).
        source_type: Input method — "url", "csv", or "manual".
        source_data: JSON blob of raw input data (product name, price, features, etc.).
        template_id: Optional FK to the template used for generation.
        status: Job state — "pending", "processing", "completed", or "failed".
        error_message: Error details if the job failed.
        created_at: Job creation timestamp.
        completed_at: Timestamp when job finished processing.
        content_items: List of generated content records.
        image_items: List of associated image processing records.
        template: The template used (if any).
        user: The owning user.
    """

    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )
    source_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    content_items = relationship(
        "GeneratedContent",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    image_items = relationship(
        "ImageJob",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    template = relationship("Template", lazy="selectin")
    user = relationship("User", lazy="selectin")


class GeneratedContent(Base):
    """
    A single piece of generated content for a generation job.

    Each GenerationJob can produce multiple content items of different types
    (e.g., title, description, meta_description, keywords, bullet_points).
    Multiple versions of the same content type can exist (for regeneration).

    Attributes:
        id: Unique identifier (UUID v4).
        job_id: Foreign key to the parent generation job.
        content_type: The type of content — "title", "description",
            "meta_description", "keywords", or "bullet_points".
        content: The generated text content.
        version: Version number for supporting regeneration (starts at 1).
        word_count: Number of words in the generated content.
        created_at: Content creation timestamp.
        job: The parent GenerationJob.
    """

    __tablename__ = "generated_content"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    job = relationship("GenerationJob", back_populates="content_items")
