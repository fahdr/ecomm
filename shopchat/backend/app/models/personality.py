"""
Chat personality configuration model for the ShopChat service.

Stores per-user personality configuration that controls how the AI
chatbot responds to visitors. Includes greeting messages, tone settings,
bot naming, escalation rules, and response language preferences.

For Developers:
    Each user has at most one personality configuration. If none exists,
    defaults are used. The ``escalation_rules`` JSON field stores
    structured rules for when to escalate to a human agent.

For Project Managers:
    Personality configuration lets users customize their AI assistant's
    behavior without technical knowledge. It directly affects customer
    experience through tone, greeting, and language settings.

For QA Engineers:
    Test CRUD operations, verify defaults when no config exists,
    test that personality settings influence the system prompt
    generated for the AI.

For End Users:
    Customize your AI assistant's personality in the Settings page.
    Set the greeting, tone, name, and language to match your brand.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChatPersonality(Base):
    """
    Personality configuration for a user's AI chatbot.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user (one per user).
        greeting_message: Custom greeting shown at conversation start.
        tone: Response tone style (friendly, professional, casual).
        bot_name: Display name for the AI assistant.
        escalation_rules: JSON rules for human escalation triggers.
        response_language: Preferred response language (ISO 639-1 code).
        custom_instructions: Additional instructions for the AI system prompt.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Back-reference to the owning User.
    """

    __tablename__ = "chat_personalities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    greeting_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Hi there! How can I help you today?",
    )
    tone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="friendly"
    )
    bot_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="ShopChat Assistant"
    )
    escalation_rules: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    response_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en"
    )
    custom_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="chat_personality", lazy="selectin")
