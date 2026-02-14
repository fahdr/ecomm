"""Bridge delivery tracking model.

Records every platform event delivery attempt to external SaaS services.
Each row represents one HTTP POST to one service for one event, enabling
the dashboard to show service activity feeds, per-resource status panels,
and delivery failure diagnostics.

**For Developers:**
    Import via ``app.models`` for Alembic discovery. The ``BridgeDelivery``
    model is written by the ``dispatch_platform_event`` Celery task and
    queried by ``app.services.bridge_service`` for dashboard display.

**For QA Engineers:**
    - Each ``dispatch_platform_event`` call creates one ``BridgeDelivery``
      row per matched service.
    - ``success=True`` means HTTP 2xx response; ``False`` otherwise.
    - ``resource_type`` is one of: "product", "order", "customer".
    - ``latency_ms`` measures the round-trip time to the external service.

**For Project Managers:**
    This model powers the Service Activity dashboard: store overview widget,
    service detail activity tab, product/order service status panels, and
    the full activity log page.

**For End Users:**
    See which AI tools were notified when you create products, receive
    orders, or gain new customers — and whether those notifications
    succeeded or failed.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.service_integration import ServiceName


class BridgeDelivery(Base):
    """Tracks a single platform event delivery attempt to an external service.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: The platform user who triggered the event.
        store_id: Optional store scope for the event.
        integration_id: The ServiceIntegration used for delivery.
        service_name: Which external service received the event.
        event: The event type string (e.g. ``"product.created"``).
        resource_id: UUID string of the resource that triggered the event.
        resource_type: Type of resource (``"product"``, ``"order"``,
            ``"customer"``).
        payload: The full JSON envelope sent to the service.
        response_status: HTTP status code from the service (null on
            timeout/connection error).
        response_body: First 1000 chars of the service's response body.
        success: Whether the delivery was successful (HTTP 2xx).
        error_message: Human-readable error description if delivery failed.
        latency_ms: Round-trip time in milliseconds.
        created_at: When the delivery was attempted.
    """

    __tablename__ = "bridge_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_name: Mapped[ServiceName] = mapped_column(
        Enum(ServiceName, name="servicename", create_type=False),
        nullable=False,
        index=True,
    )
    event: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        doc="Event type, e.g. 'product.created'"
    )
    resource_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        doc="UUID of the product/order/customer that triggered this event"
    )
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        doc="Type of resource: 'product', 'order', 'customer'"
    )
    payload: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        doc="Full JSON envelope sent to the service"
    )
    response_status: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        doc="HTTP status code (null on timeout/error)"
    )
    response_body: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="First 1000 chars of the response body"
    )
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Human-readable error if delivery failed"
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        doc="Round-trip time in milliseconds"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
