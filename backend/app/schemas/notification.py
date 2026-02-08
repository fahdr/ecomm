"""Pydantic schemas for notification endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/notifications/*`` routes.

**For Developers:**
    ``NotificationResponse`` uses ``from_attributes``. ``MarkReadRequest``
    accepts a batch of notification IDs. ``UnreadCountResponse`` is a
    lightweight schema for the notification badge counter.

**For QA Engineers:**
    - ``NotificationResponse.notification_type`` values include
      ``"order_placed"``, ``"order_shipped"``, ``"low_stock"``,
      ``"review_submitted"``, ``"refund_requested"``, etc.
    - ``MarkReadRequest.notification_ids`` must contain at least one UUID.
    - ``UnreadCountResponse.count`` is a non-negative integer.
    - ``metadata`` is a freeform dict with type-specific extra data.

**For Project Managers:**
    In-app notifications keep store owners informed of important events
    (new orders, reviews, refund requests, low stock alerts). The unread
    badge drives engagement with the dashboard.

**For End Users:**
    Receive real-time notifications about your store activity. Mark
    them as read individually or in bulk.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """Schema for returning notification data in API responses.

    Attributes:
        id: The notification's unique identifier.
        user_id: The recipient user's UUID.
        store_id: The related store's UUID (may be null for
            account-level notifications).
        notification_type: Event type that triggered the notification
            (e.g. ``"order_placed"``, ``"review_submitted"``).
        title: Short notification title.
        message: Notification body text.
        is_read: Whether the user has read the notification.
        action_url: Optional URL to navigate to when clicked.
        metadata: Optional type-specific extra data (freeform dict).
        created_at: When the notification was created.
    """

    model_config = {"from_attributes": True, "populate_by_name": True}

    id: uuid.UUID
    user_id: uuid.UUID
    store_id: uuid.UUID | None
    notification_type: str
    title: str
    message: str
    is_read: bool
    action_url: str | None
    metadata: dict | None = Field(None, validation_alias="metadata_")
    created_at: datetime


class PaginatedNotificationResponse(BaseModel):
    """Schema for paginated notification list responses.

    Attributes:
        items: List of notifications on this page.
        total: Total number of notifications matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[NotificationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class MarkReadRequest(BaseModel):
    """Schema for marking one or more notifications as read.

    Attributes:
        notification_ids: List of notification UUIDs to mark as read.
    """

    notification_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Notification UUIDs to mark as read"
    )


class UnreadCountResponse(BaseModel):
    """Schema for the unread notification count (badge counter).

    Attributes:
        count: Number of unread notifications for the current user.
    """

    count: int
