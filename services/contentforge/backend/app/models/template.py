"""
Content generation template model.

Templates define the tone, style, and content types for AI content generation.
System templates are pre-built and cannot be modified or deleted by users.
Users can create custom templates with their preferred settings.

For Developers:
    Templates control the AI prompt parameters. The `tone` and `style` fields
    influence the generated text character. `content_types` is a PostgreSQL
    ARRAY that specifies which content pieces to generate (e.g., title,
    description, meta_description, keywords, bullet_points).

    System templates (is_system=True) are seeded at startup and shared
    across all users. Custom templates (user_id set) are private to the user.

    The `prompt_override` field allows advanced users to provide a custom
    AI prompt that replaces the default generation prompt entirely.

For QA Engineers:
    Test system template visibility (all users should see them).
    Verify system templates cannot be updated or deleted.
    Test custom template CRUD — create, list, update, delete.
    Verify content_types array validation (only allowed types).

For Project Managers:
    Templates are a key differentiator — they let users customize AI output
    to match their brand voice. System templates cover common use cases
    (Professional, Casual, Luxury, SEO-Focused). Pro/Enterprise users
    can create unlimited custom templates.

For End Users:
    Templates control how your product content sounds. Choose a system
    template or create your own with custom tone and style settings.
    Templates can be reused across all your content generation jobs.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Template(Base):
    """
    A content generation template defining tone, style, and output types.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user (NULL for system templates).
        name: Template display name.
        description: Optional description of the template's purpose.
        tone: Writing tone — "professional", "casual", "luxury", "playful", "technical".
        style: Content structure style — "concise", "detailed", "storytelling", "list-based".
        prompt_override: Optional custom AI prompt (replaces default prompt).
        content_types: Array of content types to generate (e.g., ["title", "description"]).
        is_default: Whether this is the default template for new jobs.
        is_system: Whether this is a system template (cannot be edited/deleted by users).
        created_at: Template creation timestamp.
        updated_at: Last modification timestamp.
        owner: The owning user (None for system templates).
    """

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str] = mapped_column(
        String(30), nullable=False, default="professional"
    )
    style: Mapped[str] = mapped_column(
        String(30), nullable=False, default="detailed"
    )
    prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_types: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=lambda: ["title", "description", "meta_description", "keywords", "bullet_points"],
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", lazy="selectin")
