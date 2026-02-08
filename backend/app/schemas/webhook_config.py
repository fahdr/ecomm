"""Pydantic schemas for store webhook configuration endpoints (Feature 23).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/webhooks/*`` routes.

**For Developers:**
    ``CreateWebhookRequest`` and ``UpdateWebhookRequest`` are input schemas.
    ``WebhookResponse`` uses ``from_attributes``. ``WebhookDeliveryResponse``
    logs each delivery attempt for debugging.

**For QA Engineers:**
    - ``CreateWebhookRequest.url`` must be a valid HTTPS URL.
    - ``CreateWebhookRequest.events`` is a list of event names (e.g.
      ``["order.created", "order.paid"]``).
    - ``WebhookResponse.failure_count`` tracks consecutive delivery
      failures; webhooks are disabled after a threshold.
    - ``WebhookDeliveryResponse.success`` is ``true`` when the target
      returned a 2xx status code.

**For Project Managers:**
    Webhooks allow merchants and third-party integrators to receive
    real-time event notifications via HTTP callbacks. This powers
    integrations with external order management, accounting, and
    fulfilment systems.

**For End Users:**
    Configure webhook URLs in the dashboard to receive real-time
    notifications when events occur in your store (e.g. new orders,
    payment confirmations).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateWebhookRequest(BaseModel):
    """Schema for registering a new webhook endpoint.

    Attributes:
        url: The HTTPS URL to receive webhook payloads.
        events: List of event types to subscribe to (e.g.
            ``["order.created", "order.paid", "product.updated"]``).
        secret: Optional signing secret. If provided, each delivery
            includes an HMAC signature header for verification.
    """

    url: str = Field(
        ..., min_length=1, max_length=2048, description="Webhook endpoint URL"
    )
    events: list[str] = Field(
        ..., min_length=1, description="Event types to subscribe to"
    )
    secret: str | None = Field(
        None, max_length=255, description="Signing secret for HMAC verification"
    )


class UpdateWebhookRequest(BaseModel):
    """Schema for updating an existing webhook (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        url: New endpoint URL.
        events: New list of subscribed event types.
        is_active: Whether the webhook is active (can be used to
            pause/resume delivery).
    """

    url: str | None = Field(None, min_length=1, max_length=2048)
    events: list[str] | None = Field(None, min_length=1)
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    """Schema for returning webhook configuration in API responses.

    Attributes:
        id: The webhook's unique identifier.
        store_id: The parent store's UUID.
        url: The endpoint URL.
        events: List of subscribed event types.
        is_active: Whether the webhook is active.
        last_triggered_at: When the webhook was last triggered (may be
            null if never triggered).
        failure_count: Number of consecutive delivery failures.
        created_at: When the webhook was registered.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    url: str
    events: list[str]
    is_active: bool
    last_triggered_at: datetime | None
    failure_count: int
    created_at: datetime


class PaginatedWebhookResponse(BaseModel):
    """Schema for paginated webhook list responses.

    Attributes:
        items: List of webhooks on this page.
        total: Total number of webhooks matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[WebhookResponse]
    total: int
    page: int
    per_page: int
    pages: int


class WebhookDeliveryResponse(BaseModel):
    """Schema for returning a webhook delivery attempt log entry.

    Attributes:
        id: The delivery attempt's unique identifier.
        webhook_id: The parent webhook's UUID.
        event: The event type that was delivered.
        payload: The JSON payload that was sent.
        response_status: HTTP status code returned by the target
            (may be null if the request failed to connect).
        success: Whether the delivery was successful (2xx response).
        created_at: When the delivery was attempted.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    webhook_id: uuid.UUID
    event: str
    payload: dict
    response_status: int | None
    success: bool
    created_at: datetime
