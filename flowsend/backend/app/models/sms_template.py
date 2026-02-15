"""
SMS template model for reusable message content.

For Developers:
    SMS templates store pre-written message bodies that can be used
    across campaigns and flows. Category helps organize templates.

For QA Engineers:
    Test: template CRUD, body length validation, category filtering.

For Project Managers:
    SMS templates reduce content creation time and ensure
    consistent messaging across campaigns.

For End Users:
    Create reusable SMS message templates for your campaigns.
    Templates save you time and keep your messaging consistent.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SmsTemplate(Base):
    """
    A reusable SMS message template.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Template display name.
        body: SMS message body (max ~1600 chars for concatenated SMS).
        category: Template category for organization.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
    """

    __tablename__ = "sms_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="promotional", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner = relationship("User", backref="sms_templates", lazy="selectin")
