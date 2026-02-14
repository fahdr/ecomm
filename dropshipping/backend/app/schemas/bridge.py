"""Pydantic schemas for the ServiceBridge platform event API.

Request and response models for the bridge activity endpoints, manual
dispatch, and per-resource service status queries.

**For Developers:**
    These schemas serialize ``BridgeDelivery`` ORM objects into JSON for
    the REST API and validate incoming dispatch requests. Import from
    ``app.schemas.bridge`` when building API endpoints or tests.

**For QA Engineers:**
    - ``BridgeDeliveryResponse`` maps 1:1 to ``BridgeDelivery`` DB columns.
    - ``BridgeActivityResponse`` wraps a paginated list with ``total`` and
      ``pages`` metadata.
    - ``BridgeDispatchRequest`` requires ``event``, ``resource_id``,
      ``resource_type``, and ``payload``.

**For Project Managers:**
    These schemas define the data contract between the backend API and the
    dashboard UI for the service activity feature.

**For End Users:**
    These schemas power the "Service Activity" views in your dashboard,
    showing which AI tools were notified about your products and orders.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BridgeDeliveryResponse(BaseModel):
    """Serialized view of a single bridge delivery attempt.

    Attributes:
        id: Unique delivery identifier.
        service_name: Which service received the event.
        event: Event type string (e.g. ``"product.created"``).
        resource_id: UUID of the triggering resource.
        resource_type: Type of resource (``"product"``, ``"order"``,
            ``"customer"``).
        success: Whether the delivery was successful.
        error_message: Error description if delivery failed.
        response_status: HTTP status code from the service.
        latency_ms: Round-trip time in milliseconds.
        created_at: When the delivery was attempted.
    """

    id: str
    service_name: str
    event: str
    resource_id: str
    resource_type: str
    success: bool
    error_message: str | None = None
    response_status: int | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BridgeActivityResponse(BaseModel):
    """Paginated list of bridge delivery records.

    Attributes:
        items: List of delivery records for the current page.
        total: Total number of matching deliveries.
        page: Current page number (1-based).
        per_page: Items per page.
        pages: Total number of pages.
    """

    items: list[BridgeDeliveryResponse]
    total: int
    page: int
    per_page: int
    pages: int


class BridgeDispatchRequest(BaseModel):
    """Request body for manually dispatching a platform event.

    Used by the admin/debug endpoint to fire an event without going
    through the normal product/order lifecycle.

    Attributes:
        event: Event type to fire (e.g. ``"product.created"``).
        resource_id: UUID string of the resource.
        resource_type: Type of resource.
        store_id: Optional store UUID string.
        payload: The event data dict.
    """

    event: str = Field(..., description="Event type, e.g. 'product.created'")
    resource_id: str = Field(..., description="UUID of the triggering resource")
    resource_type: str = Field(..., description="product, order, or customer")
    store_id: str | None = Field(None, description="Optional store UUID")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event data payload",
    )


class ServiceSummaryResponse(BaseModel):
    """Per-service delivery summary for the last 24 hours.

    Attributes:
        service_name: The service identifier.
        last_event_at: ISO timestamp of the most recent delivery.
        last_success: Whether the most recent delivery succeeded.
        failure_count_24h: Number of failed deliveries in the last 24 hours.
    """

    service_name: str
    last_event_at: str | None = None
    last_success: bool | None = None
    failure_count_24h: int = 0
