"""
Pydantic schemas for SMS marketing features in FlowSend.

Developer:
    Defines request/response models for SMS campaigns, templates, and events.
    All schemas use Pydantic v2 with model_config for ORM compatibility.
    SMS body fields enforce a 1600-character limit (standard concatenated SMS).

Project Manager:
    These schemas power the SMS marketing API surface — campaign creation,
    template management, and delivery event tracking.

QA Engineer:
    Validate field constraints: sms_body max 1600 chars, category defaults to
    "promotional", optional fields accept None. All Response schemas must
    round-trip from SQLAlchemy model instances via from_attributes.

End User:
    Merchants interact with these data shapes when creating SMS campaigns,
    managing reusable templates, and reviewing delivery events in the dashboard.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SmsCampaignCreate(BaseModel):
    """Request schema for creating a new SMS campaign.

    Args:
        name: Human-readable campaign name.
        sms_body: The SMS message content, limited to 1600 characters.
        list_id: Optional contact list to target. If None, targets all SMS-subscribed contacts.
        scheduled_at: Optional future send time. If None, campaign is sent immediately on trigger.
    """

    name: str = Field(..., min_length=1, max_length=255)
    sms_body: str = Field(..., min_length=1, max_length=1600)
    list_id: UUID | None = None
    scheduled_at: datetime | None = None


class SmsCampaignResponse(BaseModel):
    """Response schema for an SMS campaign record.

    Attributes:
        id: Unique campaign identifier.
        user_id: Owner of the campaign.
        name: Campaign name.
        channel: Always "sms" for SMS campaigns.
        sms_body: The SMS message content.
        status: Current campaign status (draft, sending, sent, failed).
        scheduled_at: Scheduled send time, if any.
        sent_at: Actual send time, if campaign has been sent.
        total_recipients: Number of contacts targeted.
        sent_count: Number of messages successfully dispatched.
        created_at: Record creation timestamp.
        updated_at: Record last-update timestamp.
    """

    id: UUID
    user_id: UUID
    name: str
    channel: str = "sms"
    sms_body: str | None = None
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    total_recipients: int = 0
    sent_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SmsTemplateCreate(BaseModel):
    """Request schema for creating a reusable SMS template.

    Args:
        name: Template name for identification.
        body: The SMS message body, limited to 1600 characters.
        category: Template category — defaults to "promotional".
    """

    name: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=1600)
    category: str = Field(default="promotional", max_length=50)


class SmsTemplateUpdate(BaseModel):
    """Request schema for partially updating an SMS template.

    All fields are optional; only provided fields are applied.

    Args:
        name: Updated template name.
        body: Updated message body, limited to 1600 characters.
        category: Updated category.
    """

    name: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, max_length=1600)
    category: str | None = Field(default=None, max_length=50)


class SmsTemplateResponse(BaseModel):
    """Response schema for an SMS template record.

    Attributes:
        id: Unique template identifier.
        user_id: Owner of the template.
        name: Template name.
        body: SMS message body.
        category: Template category (e.g., promotional, transactional).
        created_at: Record creation timestamp.
        updated_at: Record last-update timestamp.
    """

    id: UUID
    user_id: UUID
    name: str
    body: str
    category: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SmsEventResponse(BaseModel):
    """Response schema for an SMS delivery event.

    Attributes:
        id: Unique event identifier.
        contact_id: The contact who received the SMS.
        event_type: Type of event (sent, delivered, failed, etc.).
        provider_message_id: Message ID from the SMS provider.
        error_code: Provider error code if the event represents a failure.
        created_at: When the event was recorded.
    """

    id: UUID
    contact_id: UUID
    event_type: str
    provider_message_id: str | None = None
    error_code: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
