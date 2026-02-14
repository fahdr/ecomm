"""
Pydantic schemas for FlowSend email marketing features.

Defines request/response models for contacts, contact lists, email templates,
flows, campaigns, email events, and analytics.

For Developers:
    All schemas use Pydantic v2 with `model_config = {"from_attributes": True}`
    for ORM compatibility. Create/Update schemas omit auto-generated fields.
    Response schemas include all fields. Paginated responses use PaginatedResponse[T].

For QA Engineers:
    Test validation: invalid emails return 422, required fields enforce presence,
    enum values are restricted to defined choices.

For Project Managers:
    These schemas define the API contract. Frontend and backend must agree
    on these data structures for seamless integration.

For End Users:
    These define the shape of data you send to and receive from the API.
"""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


# ── Pagination ───────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Attributes:
        items: List of items for the current page.
        total: Total number of items across all pages.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    items: list[T]
    total: int
    page: int
    page_size: int


# ── Contact Schemas ──────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    """
    Request body for creating a new contact.

    Attributes:
        email: Contact's email address (required, validated).
        first_name: Contact's first name (optional).
        last_name: Contact's last name (optional).
        tags: List of tags for segmentation (optional, defaults to empty).
        custom_fields: Arbitrary metadata key-value pairs (optional).
    """

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class ContactUpdate(BaseModel):
    """
    Request body for updating an existing contact.

    All fields are optional — only provided fields are updated.

    Attributes:
        email: Updated email address.
        first_name: Updated first name.
        last_name: Updated last name.
        tags: Updated tag list (replaces existing).
        custom_fields: Updated custom fields (replaces existing).
        is_subscribed: Whether the contact is opted-in.
    """

    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    is_subscribed: bool | None = None


class ContactResponse(BaseModel):
    """
    Contact data returned from the API.

    Attributes:
        id: Contact UUID.
        user_id: Owning user UUID.
        email: Contact email.
        first_name: First name.
        last_name: Last name.
        tags: List of tags.
        custom_fields: Custom metadata.
        is_subscribed: Subscription status.
        subscribed_at: When the contact subscribed.
        unsubscribed_at: When unsubscribed (if applicable).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    tags: list[str]
    custom_fields: dict
    is_subscribed: bool
    subscribed_at: datetime
    unsubscribed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactImportRequest(BaseModel):
    """
    Request body for bulk contact import.

    Provide either a list of email strings or CSV-formatted data.
    Duplicate emails (within the user's contacts) are skipped.

    Attributes:
        emails: List of email addresses to import.
        csv_data: Raw CSV string with 'email', 'first_name', 'last_name' columns.
        tags: Tags to apply to all imported contacts.
    """

    emails: list[EmailStr] = Field(default_factory=list)
    csv_data: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContactImportResponse(BaseModel):
    """
    Result of a bulk contact import operation.

    Attributes:
        imported: Number of new contacts successfully created.
        skipped: Number of duplicate emails skipped.
        total: Total number of emails processed.
    """

    imported: int
    skipped: int
    total: int


# ── ContactList Schemas ──────────────────────────────────────────────────

class ContactListCreate(BaseModel):
    """
    Request body for creating a contact list.

    Attributes:
        name: List display name (required).
        description: Optional list description.
        list_type: "static" or "dynamic" (default: "static").
        rules: Filter rules for dynamic lists (JSON).
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    list_type: str = "static"
    rules: dict | None = None


class ContactListResponse(BaseModel):
    """
    Contact list data returned from the API.

    Attributes:
        id: List UUID.
        user_id: Owning user UUID.
        name: List name.
        description: List description.
        list_type: "static" or "dynamic".
        rules: Filter rules (for dynamic lists).
        contact_count: Number of contacts in the list.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    list_type: str
    rules: dict | None
    contact_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── EmailTemplate Schemas ────────────────────────────────────────────────

class EmailTemplateCreate(BaseModel):
    """
    Request body for creating an email template.

    Attributes:
        name: Template display name (required).
        subject: Default subject line (required).
        html_content: HTML body content (required).
        text_content: Plain-text fallback (optional).
        category: Template category
            ("welcome", "cart", "promo", "newsletter", "transactional").
    """

    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=500)
    html_content: str = Field(..., min_length=1)
    text_content: str | None = None
    category: str = "newsletter"


class EmailTemplateUpdate(BaseModel):
    """
    Request body for updating an email template.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated template name.
        subject: Updated subject line.
        html_content: Updated HTML content.
        text_content: Updated plain-text content.
        category: Updated category.
    """

    name: str | None = None
    subject: str | None = None
    html_content: str | None = None
    text_content: str | None = None
    category: str | None = None


class EmailTemplateResponse(BaseModel):
    """
    Email template data returned from the API.

    Attributes:
        id: Template UUID.
        user_id: Owning user UUID (None for system templates).
        name: Template name.
        subject: Default subject line.
        html_content: HTML body.
        text_content: Plain-text fallback.
        thumbnail_url: Preview image URL.
        is_system: Whether system-provided.
        category: Template category.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    subject: str
    html_content: str
    text_content: str | None
    thumbnail_url: str | None
    is_system: bool
    category: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Flow Schemas ─────────────────────────────────────────────────────────

class FlowCreate(BaseModel):
    """
    Request body for creating an automated flow.

    Attributes:
        name: Flow display name (required).
        description: Optional flow description.
        trigger_type: Event trigger
            ("signup", "purchase", "abandoned_cart", "custom", "scheduled").
        trigger_config: Trigger-specific settings (JSON).
        steps: List of flow step definitions (JSON).
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    trigger_type: str = Field(
        ...,
        description="One of: signup, purchase, abandoned_cart, custom, scheduled",
    )
    trigger_config: dict = Field(default_factory=dict)
    steps: list[dict] = Field(default_factory=list)


class FlowUpdate(BaseModel):
    """
    Request body for updating an existing flow.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated flow name.
        description: Updated description.
        trigger_type: Updated trigger type.
        trigger_config: Updated trigger configuration.
        steps: Updated step definitions.
    """

    name: str | None = None
    description: str | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    steps: list[dict] | None = None


class FlowResponse(BaseModel):
    """
    Flow data returned from the API.

    Attributes:
        id: Flow UUID.
        user_id: Owning user UUID.
        name: Flow name.
        description: Flow description.
        trigger_type: Trigger event type.
        trigger_config: Trigger configuration.
        status: Current status (draft/active/paused).
        steps: List of step definitions.
        stats: Aggregate performance stats.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict
    status: str
    steps: list[dict] | dict
    stats: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlowExecutionResponse(BaseModel):
    """
    Flow execution tracking data returned from the API.

    Attributes:
        id: Execution UUID.
        flow_id: Parent flow UUID.
        contact_id: Contact UUID.
        current_step: Current step index (0-based).
        status: Execution status (running/completed/failed/canceled).
        started_at: When the execution started.
        completed_at: When the execution completed.
    """

    id: uuid.UUID
    flow_id: uuid.UUID
    contact_id: uuid.UUID
    current_step: int
    status: str
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Campaign Schemas ─────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    """
    Request body for creating an email campaign.

    Attributes:
        name: Campaign display name (required).
        template_id: UUID of the email template to use.
        list_id: UUID of the contact list to target (optional).
        subject: Email subject line (required).
        scheduled_at: Optional scheduled send time (ISO 8601).
    """

    name: str = Field(..., min_length=1, max_length=255)
    template_id: uuid.UUID | None = None
    list_id: uuid.UUID | None = None
    subject: str = Field(..., min_length=1, max_length=500)
    scheduled_at: datetime | None = None


class CampaignUpdate(BaseModel):
    """
    Request body for updating a campaign.

    Only draft campaigns can be updated.

    Attributes:
        name: Updated campaign name.
        template_id: Updated template UUID.
        list_id: Updated list UUID.
        subject: Updated subject line.
        scheduled_at: Updated scheduled time.
    """

    name: str | None = None
    template_id: uuid.UUID | None = None
    list_id: uuid.UUID | None = None
    subject: str | None = None
    scheduled_at: datetime | None = None


class CampaignResponse(BaseModel):
    """
    Campaign data returned from the API.

    Attributes:
        id: Campaign UUID.
        user_id: Owning user UUID.
        name: Campaign name.
        template_id: Template UUID.
        list_id: Contact list UUID.
        subject: Email subject line.
        status: Campaign status.
        scheduled_at: Scheduled send time.
        sent_at: Actual send time.
        total_recipients: Total intended recipients.
        sent_count: Successfully sent count.
        open_count: Unique opens.
        click_count: Unique clicks.
        bounce_count: Bounced emails.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    template_id: uuid.UUID | None
    list_id: uuid.UUID | None
    subject: str
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    total_recipients: int
    sent_count: int
    open_count: int
    click_count: int
    bounce_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Email Event Schemas ──────────────────────────────────────────────────

class EmailEventResponse(BaseModel):
    """
    Email event tracking data returned from the API.

    Attributes:
        id: Event UUID.
        campaign_id: Campaign UUID (if campaign event).
        flow_id: Flow UUID (if flow event).
        contact_id: Contact UUID.
        event_type: Event type (sent/delivered/opened/clicked/bounced/unsubscribed).
        metadata: Additional event metadata.
        created_at: Event timestamp.
    """

    id: uuid.UUID
    campaign_id: uuid.UUID | None
    flow_id: uuid.UUID | None
    contact_id: uuid.UUID
    event_type: str
    metadata: dict | None = Field(None, validation_alias="extra_metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Analytics Schemas ────────────────────────────────────────────────────

class CampaignAnalytics(BaseModel):
    """
    Aggregated analytics for a single campaign.

    Attributes:
        campaign_id: Campaign UUID.
        campaign_name: Campaign display name.
        total_sent: Total emails sent.
        total_opened: Total unique opens.
        total_clicked: Total unique clicks.
        total_bounced: Total bounces.
        open_rate: Open rate as a percentage (0-100).
        click_rate: Click rate as a percentage (0-100).
        bounce_rate: Bounce rate as a percentage (0-100).
    """

    campaign_id: uuid.UUID
    campaign_name: str
    total_sent: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    open_rate: float
    click_rate: float
    bounce_rate: float


class AggregateAnalytics(BaseModel):
    """
    Aggregate analytics across all campaigns and flows.

    Attributes:
        total_emails_sent: Total emails sent across all campaigns.
        total_opens: Total unique opens.
        total_clicks: Total unique clicks.
        total_bounces: Total bounces.
        total_contacts: Total contact count.
        total_campaigns: Total campaign count.
        total_flows: Total flow count.
        overall_open_rate: Average open rate (0-100).
        overall_click_rate: Average click rate (0-100).
        overall_bounce_rate: Average bounce rate (0-100).
        campaigns: Per-campaign analytics breakdown.
    """

    total_emails_sent: int
    total_opens: int
    total_clicks: int
    total_bounces: int
    total_contacts: int
    total_campaigns: int
    total_flows: int
    overall_open_rate: float
    overall_click_rate: float
    overall_bounce_rate: float
    campaigns: list[CampaignAnalytics]
