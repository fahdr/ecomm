"""
SMS event model for delivery tracking.

For Developers:
    SmsEvent tracks the lifecycle of individual SMS messages:
    sent, delivered, failed, opted_out. Events can be linked
    to a campaign or flow for analytics.

For QA Engineers:
    Test: event creation, provider message ID storage, error codes.

For Project Managers:
    SMS event tracking provides visibility into delivery success
    rates and helps identify issues early.

For End Users:
    Track the delivery status of your SMS messages in real-time.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SmsEvent(Base):
    """
    Individual SMS delivery event for tracking engagement.

    Tracks the delivery lifecycle of an SMS message: sent -> delivered,
    or failed / opted_out. Events are linked to campaigns or flows.

    Attributes:
        id: Unique identifier (UUID v4).
        campaign_id: Foreign key to the campaign (optional).
        flow_id: Foreign key to the flow (optional).
        contact_id: Foreign key to the recipient contact.
        event_type: Type of event ("sent", "delivered", "failed", "opted_out").
        provider_message_id: Provider-assigned message ID (e.g., Twilio SID).
        error_code: Provider error code on failure (optional).
        extra_metadata: Additional event data (JSON).
        created_at: Event timestamp.
    """

    __tablename__ = "sms_events"

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
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
