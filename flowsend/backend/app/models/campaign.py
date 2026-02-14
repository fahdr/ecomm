"""
Campaign and EmailEvent models for email marketing campaigns.

Campaigns represent bulk email sends to a contact list using a template.
EmailEvents track individual delivery events (sent, opened, clicked, etc.)
for both campaigns and flow-triggered emails.

For Developers:
    - Campaign status lifecycle: draft -> scheduled -> sending -> sent (or failed).
    - `template_id` references the EmailTemplate used for content.
    - `list_id` references the ContactList for recipients (optional for test sends).
    - Email counts (sent_count, open_count, etc.) are denormalized from EmailEvents
      for fast dashboard display.
    - EmailEvent `event_type` covers the full delivery lifecycle.

For QA Engineers:
    Test: campaign CRUD, scheduling, mock sending (creates events),
    analytics aggregation, status transitions, event tracking.

For Project Managers:
    Campaigns are the primary revenue-driving feature. Open rates,
    click rates, and bounce rates are key metrics for user retention.

For End Users:
    Create email campaigns to send newsletters, promotions, and updates
    to your contact lists. Track performance with real-time analytics.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Campaign(Base):
    """
    An email campaign targeting a contact list with a template.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Campaign display name.
        template_id: Foreign key to the email template.
        list_id: Foreign key to the target contact list (optional).
        subject: Email subject line (can override template default).
        status: Campaign lifecycle state
            ("draft", "scheduled", "sending", "sent", "failed").
        scheduled_at: When the campaign is scheduled to send (optional).
        sent_at: When the campaign was actually sent (set after sending).
        total_recipients: Total number of intended recipients.
        sent_count: Number of emails successfully sent.
        open_count: Number of unique opens tracked.
        click_count: Number of unique clicks tracked.
        bounce_count: Number of bounced emails.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
        template: Related EmailTemplate record.
        events: Related EmailEvent records.
    """

    __tablename__ = "campaigns"

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
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    list_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contact_lists.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bounce_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="campaigns", lazy="selectin")
    template = relationship("EmailTemplate", lazy="selectin")
    events = relationship(
        "EmailEvent",
        back_populates="campaign",
        cascade="all, delete-orphan",
        foreign_keys="EmailEvent.campaign_id",
        lazy="selectin",
    )


class EmailEvent(Base):
    """
    Individual email delivery event for tracking engagement.

    Tracks the full lifecycle of an email: sent -> delivered -> opened ->
    clicked, plus bounces and unsubscribes. Events can belong to a campaign
    or a flow (or both, but typically one).

    Attributes:
        id: Unique identifier (UUID v4).
        campaign_id: Foreign key to the campaign (optional).
        flow_id: Foreign key to the flow (optional).
        contact_id: Foreign key to the recipient contact.
        event_type: Type of event
            ("sent", "delivered", "opened", "clicked", "bounced", "unsubscribed").
        extra_metadata: Additional event data (e.g. link URL for clicks).
        created_at: Event timestamp.
        campaign: Related Campaign record (if campaign event).
    """

    __tablename__ = "email_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    flow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flows.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="events", lazy="selectin")
