"""
Chatbot model for the ShopChat service.

Each user can create multiple chatbots, each with its own personality,
welcome message, visual theme, and embeddable widget key. Chatbots are
the top-level entity that conversations and knowledge bases attach to.

For Developers:
    The `widget_key` is a unique, URL-safe string generated at creation
    time. It is used in the public widget embed to identify the chatbot
    without requiring authentication. The `theme_config` JSON column
    stores widget appearance settings (colors, position, size).

For QA Engineers:
    Test chatbot creation via POST /api/v1/chatbots.
    Verify that widget_key is unique across all chatbots.
    Test personality and theme_config validation (enum values, JSON shape).

For Project Managers:
    Chatbots are the primary product unit — each chatbot is an independent
    AI assistant that can be embedded on a store or website.

For End Users:
    Create chatbots to embed an AI shopping assistant on your store.
    Customize the personality, welcome message, and visual theme.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Chatbot(Base):
    """
    AI chatbot instance owned by a user.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Human-readable chatbot name (e.g. "Store Assistant").
        personality: Chatbot personality style.
        welcome_message: Greeting shown when a visitor opens the widget.
        theme_config: JSON dict with widget appearance (colors, position, size).
        is_active: Whether the chatbot is currently serving conversations.
        widget_key: Unique URL-safe key for embedding the widget (public identifier).
        created_at: Chatbot creation timestamp.
        updated_at: Last modification timestamp.
        knowledge_entries: Related knowledge base entries.
        conversations: Related conversations.
    """

    __tablename__ = "chatbots"

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
    personality: Mapped[str] = mapped_column(
        String(50), nullable=False, default="friendly"
    )
    welcome_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Hi there! How can I help you today?",
    )
    theme_config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "primary_color": "#6366f1",
            "text_color": "#ffffff",
            "position": "bottom-right",
            "size": "medium",
        },
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    widget_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="chatbots", lazy="selectin")
    knowledge_entries = relationship(
        "KnowledgeBase",
        back_populates="chatbot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conversations = relationship(
        "Conversation",
        back_populates="chatbot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
