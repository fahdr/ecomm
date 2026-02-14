"""
Message model for the ShopChat service.

Individual chat messages within a conversation. Each message has a role
(user or assistant) and content. The extra_metadata JSON field stores additional
context like product references and clickable links.

For Developers:
    Messages are created in pairs: user sends a message, the AI generates
    a response. The `extra_metadata` field can contain product suggestions,
    links, and other structured data embedded in the response.

For QA Engineers:
    Test message creation via the widget chat endpoint.
    Verify that messages are ordered by created_at within a conversation.
    Check that extra_metadata contains valid product references when applicable.

For Project Managers:
    Messages are the atomic unit of chat. Message counts contribute
    to conversation analytics and usage tracking.

For End Users:
    Messages are the individual exchanges between your customers
    and the AI assistant. View them in the conversation detail page.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Message(Base):
    """
    Individual message in a conversation.

    Attributes:
        id: Unique identifier (UUID v4).
        conversation_id: Foreign key to the parent conversation.
        role: Message sender role ("user" or "assistant").
        content: Full message text content.
        extra_metadata: Optional JSON with product references, links, etc.
        created_at: Message creation timestamp.
        conversation: Related Conversation record.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
