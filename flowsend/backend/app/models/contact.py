"""
Contact and ContactList models for email marketing.

Contacts represent individual email recipients. ContactLists group contacts
for targeted campaigns — either as static lists or dynamic segments based on rules.

For Developers:
    - `tags` uses PostgreSQL ARRAY(String) for fast tag-based filtering.
    - `custom_fields` uses JSON for flexible per-contact metadata.
    - ContactList `list_type` is either "static" (manually managed) or
      "dynamic" (auto-populated by filter rules stored in `rules` JSON).
    - Both models have `user_id` FK to enforce multi-tenant isolation.

For QA Engineers:
    Test: contact CRUD, import, tag management, subscribe/unsubscribe,
    list creation with static/dynamic types, contact count tracking.

For Project Managers:
    Contacts are the core audience data. Contact limits are enforced
    per plan tier via `max_secondary` in PLAN_LIMITS.

For End Users:
    Add your email subscribers as contacts, organize them into lists,
    and tag them for targeted campaigns.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Contact(Base):
    """
    An email contact (subscriber) belonging to a user.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        email: Contact's email address.
        first_name: Contact's first name (optional).
        last_name: Contact's last name (optional).
        tags: List of string tags for segmentation.
        custom_fields: Arbitrary key-value metadata.
        is_subscribed: Whether the contact is opted-in to receive emails.
        subscribed_at: Timestamp when the contact subscribed.
        unsubscribed_at: Timestamp when the contact unsubscribed (if applicable).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
    """

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="contacts", lazy="selectin")


class ContactList(Base):
    """
    A named list of contacts for campaign targeting.

    Lists can be "static" (manually managed membership) or "dynamic"
    (automatically populated based on filter rules stored as JSON).

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Human-readable list name.
        description: Optional description of the list's purpose.
        list_type: Either "static" or "dynamic".
        rules: Filter rules for dynamic lists (JSON, null for static).
        contact_count: Cached count of contacts in this list.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
    """

    __tablename__ = "contact_lists"

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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    list_type: Mapped[str] = mapped_column(
        String(20), default="static", nullable=False
    )
    rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contact_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="contact_lists", lazy="selectin")
