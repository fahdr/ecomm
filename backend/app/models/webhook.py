"""StoreWebhook and WebhookDelivery database models.

Defines the ``store_webhooks`` and ``webhook_deliveries`` tables for
managing store-owner-configured webhook endpoints. Store owners can
subscribe to specific events and receive HTTP POST callbacks when those
events occur.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``events`` JSON column stores a list of
    event type strings that this webhook subscribes to. The ``secret``
    column contains an HMAC secret used to sign webhook payloads so the
    receiver can verify authenticity. ``WebhookDelivery`` records every
    delivery attempt for debugging and retry logic.

    Note: This model is for store-owner webhooks (Feature 23), not to be
    confused with ``backend/app/api/webhooks.py`` which handles incoming
    Stripe webhooks.

**For QA Engineers:**
    - ``events`` is a JSON array of event strings matching
      ``WebhookEvent`` values (e.g. ``["order.created", "order.paid"]``).
    - ``failure_count`` increments on each failed delivery; webhooks
      should be auto-disabled after a threshold (e.g. 10 failures).
    - ``last_triggered_at`` updates on each delivery attempt.
    - ``WebhookDelivery`` captures the full request/response cycle:
      payload sent, HTTP status received, response body, and success flag.
    - ``is_active`` can be toggled to pause webhook deliveries.

**For End Users:**
    Webhooks let you connect your store to external services by
    automatically sending data when events happen (e.g. when an order is
    placed or a product is updated). Configure a URL, choose which events
    to listen for, and your external service will receive real-time
    notifications.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WebhookEvent(str, enum.Enum):
    """Supported webhook event types.

    Attributes:
        order_created: Fired when a new order is placed.
        order_paid: Fired when an order's payment is confirmed.
        order_shipped: Fired when an order is marked as shipped.
        order_delivered: Fired when an order is marked as delivered.
        order_cancelled: Fired when an order is cancelled.
        product_created: Fired when a new product is created.
        product_updated: Fired when a product is modified.
        customer_created: Fired when a new customer account is created.
        refund_requested: Fired when a refund request is submitted.
        refund_completed: Fired when a refund is processed.
    """

    order_created = "order.created"
    order_paid = "order.paid"
    order_shipped = "order.shipped"
    order_delivered = "order.delivered"
    order_cancelled = "order.cancelled"
    product_created = "product.created"
    product_updated = "product.updated"
    customer_created = "customer.created"
    refund_requested = "refund.requested"
    refund_completed = "refund.completed"


class StoreWebhook(Base):
    """SQLAlchemy model representing a store-owner-configured webhook endpoint.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the webhook to its store.
        url: The HTTPS URL to send webhook payloads to.
        secret: HMAC secret used to sign payloads for verification.
        events: JSON array of event type strings this webhook subscribes to.
        is_active: Whether the webhook is currently delivering events.
        last_triggered_at: Timestamp of the most recent delivery attempt.
        failure_count: Running count of consecutive delivery failures.
        created_at: Timestamp when the webhook was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        deliveries: One-to-many relationship to WebhookDelivery records.
    """

    __tablename__ = "store_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="webhooks", lazy="selectin")
    deliveries = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class WebhookDelivery(Base):
    """Audit record capturing each webhook delivery attempt.

    Stores the full payload sent and the response received for debugging,
    retry logic, and delivery monitoring.

    Attributes:
        id: Unique identifier (UUID v4).
        webhook_id: Foreign key to the parent StoreWebhook.
        event: The event type string that triggered this delivery.
        payload: The full JSON payload that was sent.
        response_status: The HTTP status code received (null if network error).
        response_body: The response body received (truncated if very large).
        success: Whether the delivery was successful (2xx status).
        created_at: Timestamp when the delivery was attempted.
        webhook: Relationship back to the parent StoreWebhook.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    webhook = relationship("StoreWebhook", back_populates="deliveries")
