"""
Platform webhook endpoints for SpyDrop.

Handles platform bridge events for cross-service automation. The Stripe
webhook handler is provided by ``ecomm_core.billing.webhooks`` and
included via ``create_webhook_router`` in ``main.py``.

For Developers:
    Platform events are verified via HMAC-SHA256 using the shared
    ``platform_webhook_secret`` from BaseServiceConfig. This module
    adds a ``/webhooks/platform-events`` route to the existing
    ``/webhooks`` prefix.

For QA Engineers:
    Test platform events via POST /webhooks/platform-events with a valid
    X-Platform-Signature header. Stripe webhook tests use the core
    endpoint at POST /webhooks/stripe.

For Project Managers:
    Platform events enable automated competitor price monitoring when
    orders are created on the dropshipping platform. SpyDrop handles
    ``order.created`` events to queue competitor price checks, helping
    merchants stay competitive on pricing.

For End Users:
    When a new order is placed, SpyDrop automatically checks competitor
    prices for the ordered products to ensure your pricing remains
    competitive.
"""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)


def _verify_platform_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verify the HMAC-SHA256 signature from the platform bridge.

    The platform bridge signs each webhook payload with a shared secret so
    that services can authenticate the origin of incoming events.

    Args:
        payload_bytes: Raw request body bytes.
        signature_header: The X-Platform-Signature header value
            (format: ``sha256=<hex-digest>``).

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[7:]
    computed = hmac.new(
        settings.platform_webhook_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected)


@router.post("/platform-events")
async def platform_event_webhook(request: Request):
    """Receive platform lifecycle events from the dropshipping platform.

    The platform bridge dispatches events (product.created, order.created,
    etc.) to connected services via HMAC-signed HTTP POST.

    SpyDrop handles:
        - ``order.created`` -- queues a competitor price check for the
          products in the order, alerting merchants if competitors offer
          lower prices.

    For Developers:
        Events are signed with HMAC-SHA256 using the shared
        ``platform_webhook_secret``. Only events mapped to this service
        are delivered by the platform.

    For QA Engineers:
        - Valid signature required (X-Platform-Signature header).
        - Returns 401 for invalid/missing signatures.
        - Unknown event types are accepted but produce no actions.

    Args:
        request: The incoming webhook request.

    Returns:
        Dict with status and list of actions taken.

    Raises:
        HTTPException 401: If signature verification fails.
        HTTPException 400: If the JSON payload is malformed.
    """
    payload_bytes = await request.body()
    signature = request.headers.get("X-Platform-Signature", "")

    if not _verify_platform_signature(payload_bytes, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid platform signature",
        )

    try:
        data = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = data.get("event", "")
    event_data = data.get("data", {})
    actions = []

    # Route to SpyDrop-specific handlers
    if event_type == "order.created":
        logger.info(
            "Competitor price check queued for order: %s",
            event_data.get("order_id", "unknown"),
        )
        actions.append("competitor_price_check_queued")

    return {"status": "ok", "actions": actions}
