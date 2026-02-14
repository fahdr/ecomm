"""Store webhook business logic.

Handles CRUD operations for store-owned webhooks and event dispatching.
Store owners can register HTTP endpoints that receive real-time
notifications when events occur (e.g. order.created, product.updated).

**For Developers:**
    Webhooks use HMAC-SHA256 signatures to ensure payload integrity.
    ``trigger_webhook_event`` finds all webhooks subscribed to the event
    and dispatches HTTP POST requests. In the current implementation,
    dispatching is logged rather than sent over the network (production
    would use a background task queue). ``sign_payload`` generates the
    HMAC signature header.

**For QA Engineers:**
    - ``create_webhook`` generates a secret if none is provided.
    - ``trigger_webhook_event`` filters webhooks by event subscription.
    - ``sign_payload`` produces a hex-encoded HMAC-SHA256 digest.
    - ``get_webhook_deliveries`` returns delivery attempt logs (when
      the delivery model is available).
    - Webhook secrets are never exposed in list responses.

**For Project Managers:**
    This service powers the webhook portion of Feature 23 (API & Webhooks)
    from the backlog. It enables store owners to integrate their store
    with external systems via event-driven notifications.

**For End Users:**
    Set up webhooks to receive real-time notifications when events happen
    in your store (e.g. new orders, product updates). Point them at your
    own server to automate workflows like inventory sync or fulfillment.
"""

import hashlib
import hmac
import json
import logging
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Webhook models -- import conditionally.
# ---------------------------------------------------------------------------
try:
    from app.models.webhook import StoreWebhook, WebhookDelivery
except ImportError:
    StoreWebhook = None  # type: ignore[assignment,misc]
    WebhookDelivery = None  # type: ignore[assignment,misc]


def generate_webhook_secret() -> str:
    """Generate a cryptographically secure webhook signing secret.

    Returns:
        A ``whsec_``-prefixed hex string (40 characters total).
    """
    return f"whsec_{secrets.token_hex(20)}"


def sign_payload(payload: str | bytes, secret: str) -> str:
    """Create an HMAC-SHA256 signature for a webhook payload.

    Args:
        payload: The JSON payload string or bytes to sign.
        secret: The webhook secret key.

    Returns:
        The hex-encoded HMAC-SHA256 digest string.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def create_webhook(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    url: str,
    events: list[str],
    secret: str | None = None,
) -> "StoreWebhook":
    """Create a new webhook endpoint for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        url: The HTTP endpoint URL that will receive webhook payloads.
        events: List of event types to subscribe to (e.g.
            ``["order.created", "product.updated"]``).
        secret: Optional signing secret. If not provided, one is generated.

    Returns:
        The newly created StoreWebhook ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or the URL is empty.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if not url or not url.strip():
        raise ValueError("Webhook URL cannot be empty")

    if not events:
        raise ValueError("At least one event must be specified")

    webhook = StoreWebhook(
        store_id=store_id,
        url=url.strip(),
        events=events,
        secret=secret or generate_webhook_secret(),
        is_active=True,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def list_webhooks(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list:
    """List all webhooks for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        A list of StoreWebhook ORM instances.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(StoreWebhook)
        .where(StoreWebhook.store_id == store_id)
        .order_by(StoreWebhook.created_at.desc())
    )
    return list(result.scalars().all())


async def update_webhook(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    webhook_id: uuid.UUID,
    **kwargs,
) -> "StoreWebhook":
    """Update a webhook's fields (partial update).

    Only provided (non-None) keyword arguments are applied.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        webhook_id: The UUID of the webhook to update.
        **kwargs: Keyword arguments for fields to update (url, events,
            is_active, secret).

    Returns:
        The updated StoreWebhook ORM instance.

    Raises:
        ValueError: If the store or webhook doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(StoreWebhook).where(
            StoreWebhook.id == webhook_id,
            StoreWebhook.store_id == store_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise ValueError("Webhook not found")

    for key, value in kwargs.items():
        if value is not None:
            setattr(webhook, key, value)

    await db.flush()
    await db.refresh(webhook)
    return webhook


async def delete_webhook(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    webhook_id: uuid.UUID,
) -> None:
    """Permanently delete a webhook.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        webhook_id: The UUID of the webhook to delete.

    Raises:
        ValueError: If the store or webhook doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(StoreWebhook).where(
            StoreWebhook.id == webhook_id,
            StoreWebhook.store_id == store_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise ValueError("Webhook not found")

    await db.delete(webhook)
    await db.flush()


async def trigger_webhook_event(
    db: AsyncSession,
    store_id: uuid.UUID,
    event: str,
    payload: dict,
) -> None:
    """Trigger a webhook event for all matching subscribers.

    Finds all active webhooks for the store that subscribe to the given
    event type and dispatches the payload. In the current implementation,
    dispatching is logged (in production, this would be sent via an
    HTTP POST with HMAC signature in a background task).

    Args:
        db: Async database session.
        store_id: The store's UUID.
        event: The event type string (e.g. ``"order.created"``).
        payload: The event payload dict to send.
    """
    result = await db.execute(
        select(StoreWebhook).where(
            StoreWebhook.store_id == store_id,
            StoreWebhook.is_active.is_(True),
        )
    )
    webhooks = list(result.scalars().all())

    for webhook in webhooks:
        # Check if this webhook subscribes to the event
        if event not in webhook.events:
            continue

        # Build the full payload
        full_payload = json.dumps({
            "event": event,
            "store_id": str(store_id),
            "data": payload,
        })

        # Sign the payload
        signature = sign_payload(full_payload, webhook.secret)

        # In production: send HTTP POST with headers:
        #   X-Webhook-Signature: sha256={signature}
        #   Content-Type: application/json
        # Using httpx or aiohttp in a background task.
        #
        # For now, log the dispatch for development.
        logger.info(
            "Webhook dispatch: event=%s url=%s signature=%s",
            event,
            webhook.url,
            signature[:16] + "...",
        )

        # Record delivery attempt (if model exists)
        if WebhookDelivery is not None:
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event=event,
                payload=full_payload,
                response_status=200,  # Mocked in dev
                success=True,
            )
            db.add(delivery)

    await db.flush()


async def get_webhook_deliveries(
    db: AsyncSession,
    webhook_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list, int]:
    """Get delivery attempt history for a webhook.

    Args:
        db: Async database session.
        webhook_id: The UUID of the webhook.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (deliveries list, total count).
    """
    if WebhookDelivery is None:
        return [], 0

    query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook_id)
    count_query = select(func.count(WebhookDelivery.id)).where(
        WebhookDelivery.webhook_id == webhook_id
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(WebhookDelivery.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    deliveries = list(result.scalars().all())

    return deliveries, total
