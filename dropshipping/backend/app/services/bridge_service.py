"""ServiceBridge helper functions.

Provides HMAC signing for platform event payloads and convenience wrappers
for firing events via Celery and querying delivery history for the dashboard.

**For Developers:**
    ``fire_platform_event`` is the main entry point called from API endpoints.
    It constructs the Celery task arguments and calls ``.delay()``.
    Query functions (``get_recent_activity``, ``get_resource_deliveries``,
    ``get_service_activity``) are used by ``app.api.bridge`` endpoints to
    feed the dashboard UI.

**For QA Engineers:**
    - ``sign_bridge_payload`` uses HMAC-SHA256 identical to
      ``webhook_service.sign_payload``.
    - ``fire_platform_event`` is fire-and-forget (async via Celery).
    - Query functions return ``(items, total)`` tuples for pagination.

**For Project Managers:**
    This module connects the API layer to the Celery bridge task and
    provides the data layer for all Service Activity dashboard widgets.

**For End Users:**
    This is the behind-the-scenes logic that notifies your connected
    AI tools when events happen in your store.
"""

import hashlib
import hmac
import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bridge_delivery import BridgeDelivery
from app.models.service_integration import ServiceName

logger = logging.getLogger(__name__)


def sign_bridge_payload(payload_json: str, secret: str) -> str:
    """Create an HMAC-SHA256 signature for a platform event payload.

    Uses the same algorithm as ``webhook_service.sign_payload`` for
    consistency across the platform's webhook signing mechanisms.

    Args:
        payload_json: The JSON string to sign.
        secret: The shared secret (service API key).

    Returns:
        The hex-encoded HMAC-SHA256 digest.
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def fire_platform_event(
    user_id: uuid.UUID,
    store_id: uuid.UUID | None,
    event: str,
    resource_id: uuid.UUID,
    resource_type: str,
    payload: dict[str, Any],
) -> None:
    """Fire a platform event asynchronously via Celery.

    Lazy-imports the Celery task to avoid circular imports and calls
    ``.delay()`` with all arguments serialized as strings (UUIDs).

    Args:
        user_id: The platform user who triggered the event.
        store_id: The store scope (may be None for customer events).
        event: Event type string (e.g. ``"product.created"``).
        resource_id: UUID of the triggering resource.
        resource_type: Type string (``"product"``, ``"order"``,
            ``"customer"``).
        payload: The event data dict to deliver to services.
    """
    from app.tasks.bridge_tasks import dispatch_platform_event

    dispatch_platform_event.delay(
        user_id=str(user_id),
        store_id=str(store_id) if store_id else None,
        event=event,
        resource_id=str(resource_id),
        resource_type=resource_type,
        payload=payload,
    )
    logger.info(
        "Fired platform event %s for %s %s (user=%s)",
        event, resource_type, resource_id, user_id,
    )


async def get_recent_activity(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    event_filter: str | None = None,
    service_filter: str | None = None,
    status_filter: str | None = None,
) -> tuple[list[BridgeDelivery], int]:
    """Query recent bridge deliveries for a user with optional filters.

    Args:
        db: Async database session.
        user_id: The user to query deliveries for.
        page: Page number (1-based).
        per_page: Items per page.
        event_filter: Optional event type filter (e.g. ``"product.created"``).
        service_filter: Optional service name filter (e.g. ``"contentforge"``).
        status_filter: Optional status filter (``"success"`` or ``"failed"``).

    Returns:
        A tuple of (deliveries list, total count).
    """
    query = select(BridgeDelivery).where(BridgeDelivery.user_id == user_id)
    count_query = select(func.count(BridgeDelivery.id)).where(
        BridgeDelivery.user_id == user_id
    )

    if event_filter:
        query = query.where(BridgeDelivery.event == event_filter)
        count_query = count_query.where(BridgeDelivery.event == event_filter)

    if service_filter:
        try:
            svc = ServiceName(service_filter)
            query = query.where(BridgeDelivery.service_name == svc)
            count_query = count_query.where(BridgeDelivery.service_name == svc)
        except ValueError:
            pass

    if status_filter == "success":
        query = query.where(BridgeDelivery.success.is_(True))
        count_query = count_query.where(BridgeDelivery.success.is_(True))
    elif status_filter == "failed":
        query = query.where(BridgeDelivery.success.is_(False))
        count_query = count_query.where(BridgeDelivery.success.is_(False))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query.order_by(BridgeDelivery.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(query)
    deliveries = list(result.scalars().all())

    return deliveries, total


async def get_resource_deliveries(
    db: AsyncSession,
    resource_id: str,
    resource_type: str,
) -> list[BridgeDelivery]:
    """Query all deliveries for a specific resource (product, order, customer).

    Args:
        db: Async database session.
        resource_id: UUID string of the resource.
        resource_type: Type of resource (``"product"``, ``"order"``,
            ``"customer"``).

    Returns:
        List of BridgeDelivery rows ordered by most recent first.
    """
    result = await db.execute(
        select(BridgeDelivery)
        .where(
            BridgeDelivery.resource_id == resource_id,
            BridgeDelivery.resource_type == resource_type,
        )
        .order_by(BridgeDelivery.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def get_service_activity(
    db: AsyncSession,
    user_id: uuid.UUID,
    service_name: str,
    limit: int = 10,
) -> list[BridgeDelivery]:
    """Query recent deliveries for a specific service.

    Args:
        db: Async database session.
        user_id: The user to query for.
        service_name: The service name string (e.g. ``"contentforge"``).
        limit: Max items to return.

    Returns:
        List of BridgeDelivery rows ordered by most recent first.
    """
    try:
        svc = ServiceName(service_name)
    except ValueError:
        return []

    result = await db.execute(
        select(BridgeDelivery)
        .where(
            BridgeDelivery.user_id == user_id,
            BridgeDelivery.service_name == svc,
        )
        .order_by(BridgeDelivery.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_service_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict[str, dict[str, Any]]:
    """Get per-service delivery summary for the last 24 hours.

    Returns a dict keyed by service name with last_event_at,
    last_success status, and failure count in the last 24 hours.

    Args:
        db: Async database session.
        user_id: The user to query for.

    Returns:
        Dict mapping service name to summary dict with keys:
        ``last_event_at``, ``last_success``, ``failure_count_24h``.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    result = await db.execute(
        select(BridgeDelivery)
        .where(
            BridgeDelivery.user_id == user_id,
            BridgeDelivery.created_at >= since,
        )
        .order_by(BridgeDelivery.created_at.desc())
    )
    deliveries = result.scalars().all()

    summary: dict[str, dict[str, Any]] = {}
    for d in deliveries:
        svc = d.service_name.value
        if svc not in summary:
            summary[svc] = {
                "last_event_at": d.created_at.isoformat() if d.created_at else None,
                "last_success": d.success,
                "failure_count_24h": 0,
            }
        if not d.success:
            summary[svc]["failure_count_24h"] += 1

    return summary
