"""
Chat analytics model for session-level performance metrics.

Stores per-session analytics data including satisfaction scores,
topic classification, resolution status, and response timing.
These records are created when a chat session ends or is rated,
providing the raw data for the analytics dashboard.

For Developers:
    Each ChatAnalytics record corresponds to a single conversation
    session. The ``topic`` field is extracted from conversation content
    (keyword-based or LLM-classified). The ``resolved`` flag indicates
    whether the visitor's question was answered satisfactorily.

For Project Managers:
    Analytics records power the dashboard metrics: total sessions,
    average satisfaction, resolution rate, top topics, and response
    time tracking. These help users understand chatbot performance.

For QA Engineers:
    Test analytics recording on session end, satisfaction rating
    updates, and summary aggregation queries. Verify null handling
    for optional fields (satisfaction_score, feedback_text).

For End Users:
    View your chatbot performance metrics on the Analytics page
    to understand how well your AI assistant is helping customers.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChatAnalytics(Base):
    """
    Session-level analytics for a chat conversation.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the chatbot owner.
        session_id: Foreign key to the conversation (session).
        satisfaction_score: Visitor satisfaction rating (1.0-5.0, nullable).
        feedback_text: Optional text feedback from the visitor.
        topic: Extracted topic or category of the conversation.
        resolved: Whether the visitor's question was resolved.
        response_time_avg_ms: Average response time in milliseconds.
        message_count: Total messages exchanged in the session.
        created_at: Record creation timestamp.
    """

    __tablename__ = "chat_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    satisfaction_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    feedback_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    topic: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    response_time_avg_ms: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    message_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
