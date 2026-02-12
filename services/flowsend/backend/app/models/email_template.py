"""
Email template model for reusable campaign content.

Templates store HTML email content that can be reused across campaigns
and automated flows. System templates (user_id=None) are available to
all users; custom templates are scoped to the creating user.

For Developers:
    - `user_id` is nullable: NULL means a system template available to all.
    - `html_content` and `text_content` use Text columns for large content.
    - `category` drives template filtering in the UI.
    - `thumbnail_url` can point to a stored preview image.

For QA Engineers:
    Test: CRUD for custom templates, read-only access to system templates,
    category filtering, template preview rendering.

For Project Managers:
    Templates accelerate campaign creation. System templates provide
    ready-made designs; users can create custom templates for their brand.

For End Users:
    Use templates to quickly create professional-looking emails.
    Choose from system templates or create your own.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EmailTemplate(Base):
    """
    An email template for campaigns and flows.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user (NULL for system templates).
        name: Template display name.
        subject: Default email subject line.
        html_content: HTML body of the email.
        text_content: Plain-text fallback body (optional).
        thumbnail_url: Preview image URL (optional).
        is_system: Whether this is a system-provided template.
        category: Template category for filtering
            ("welcome", "cart", "promo", "newsletter", "transactional").
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record (None for system templates).
    """

    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="newsletter", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="email_templates")
