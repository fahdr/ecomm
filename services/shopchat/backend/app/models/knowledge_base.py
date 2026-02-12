"""
Knowledge Base model for the ShopChat service.

Knowledge base entries store the information that the AI chatbot uses
to answer visitor questions. Entries can come from product catalogs,
policy pages, FAQs, custom text, or external URLs.

For Developers:
    Each entry belongs to a chatbot. The `source_type` field categorizes
    the origin of the content. The `content` field holds the full text
    that is searched during chat to provide context-aware answers.
    The `metadata` JSON field can store extra info (e.g. product IDs,
    URLs, structured data).

For QA Engineers:
    Test knowledge base CRUD via /api/v1/knowledge endpoints.
    Verify plan limits on the number of knowledge base pages.
    Test each source_type value is accepted.

For Project Managers:
    The knowledge base is the "brain" of each chatbot. More pages
    give the chatbot more context to answer questions accurately.
    Plan limits control how many pages a user can create.

For End Users:
    Add product info, policies, and FAQs to your knowledge base
    so the chatbot can answer customer questions accurately.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KnowledgeBase(Base):
    """
    Knowledge base entry for a chatbot.

    Attributes:
        id: Unique identifier (UUID v4).
        chatbot_id: Foreign key to the parent chatbot.
        source_type: Origin type of the content.
        title: Human-readable title for the entry.
        content: Full text content used for search and AI context.
        metadata: Optional JSON with extra structured data.
        is_active: Whether this entry is included in AI context.
        created_at: Entry creation timestamp.
        updated_at: Last modification timestamp.
        chatbot: Related Chatbot record.
    """

    __tablename__ = "knowledge_base"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="custom_text"
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    chatbot = relationship("Chatbot", back_populates="knowledge_entries")
