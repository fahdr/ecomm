"""
Conversation model for the ShopChat service.

Tracks chat sessions between visitors and the AI chatbot. Each
conversation groups a series of messages exchanged during a single
session, along with metadata like visitor identity, timing, and
satisfaction rating.

For Developers:
    Conversations are created when a visitor sends their first message
    via the widget. The `visitor_id` is a session/cookie-based identifier
    (not authenticated). The `status` field tracks the conversation
    lifecycle: active -> ended/abandoned.

For QA Engineers:
    Test conversation creation via the widget endpoint.
    Verify message_count increments with each message.
    Test conversation ending and satisfaction rating.

For Project Managers:
    Conversations are the primary billing metric (max_items = conversations/month).
    Analytics are derived from conversation data (volume, satisfaction, timing).

For End Users:
    View your chatbot conversations in the dashboard to see what
    customers are asking and how satisfied they are.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Conversation(Base):
    """
    Chat conversation between a visitor and a chatbot.

    Attributes:
        id: Unique identifier (UUID v4).
        chatbot_id: Foreign key to the chatbot handling this conversation.
        visitor_id: Session/cookie-based visitor identifier.
        visitor_name: Optional visitor name (if provided).
        started_at: Conversation start timestamp.
        ended_at: Conversation end timestamp (None if still active).
        message_count: Total messages exchanged in this conversation.
        satisfaction_score: Visitor satisfaction rating (1.0-5.0, None if not rated).
        status: Conversation lifecycle status.
        chatbot: Related Chatbot record.
        messages: Related Message records.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    visitor_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    visitor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    satisfaction_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )

    # Relationships
    chatbot = relationship("Chatbot", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )
