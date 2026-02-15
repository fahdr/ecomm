"""ServiceBridge platform event dispatch Celery task.

Delivers platform lifecycle events (product.created, order.shipped, etc.) to
connected SaaS microservices via HMAC-signed HTTP POST requests. Each delivery
attempt is recorded as a ``BridgeDelivery`` row for dashboard visibility.

**For Developers:**
    The task queries ``ServiceIntegration`` for the user's active services,
    filters by ``EVENT_SERVICE_MAP``, and delivers the event payload via
    sync ``httpx.Client``. Uses ``SyncSessionFactory`` (psycopg2) because
    Celery workers run synchronously. Follow the same pattern as
    ``webhook_tasks.py``.

**For QA Engineers:**
    - ``EVENT_SERVICE_MAP`` defines which events go to which services.
    - The ``X-Platform-Signature`` header contains ``sha256=<hmac_hex>``.
    - A delivery is successful when the service responds with HTTP 2xx.
    - Each dispatch creates one ``BridgeDelivery`` row per matched service.
    - If no integrations match, the task returns early with zero counts.

**For Project Managers:**
    This is the core "glue" that automatically notifies connected AI tools
    when store owners create products, receive orders, or gain customers.
    It replaces manual copy-paste across tools with real-time automation.

**For End Users:**
    When you create a product or receive an order, your connected AI tools
    are automatically notified so they can generate content, send emails,
    track trends, and more — all without any manual effort.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

import httpx

from app.models.service_integration import ServiceName
from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event-to-service mapping
# ---------------------------------------------------------------------------

EVENT_SERVICE_MAP: dict[str, list[ServiceName]] = {
    "product.created": [
        ServiceName.contentforge,
        ServiceName.rankpilot,
        ServiceName.trendscout,
        ServiceName.postpilot,
        ServiceName.adscale,
        ServiceName.shopchat,
    ],
    "product.updated": [
        ServiceName.contentforge,
        ServiceName.rankpilot,
        ServiceName.shopchat,
    ],
    "order.created": [
        ServiceName.flowsend,
        ServiceName.spydrop,
    ],
    "order.shipped": [
        ServiceName.flowsend,
    ],
    "customer.created": [
        ServiceName.flowsend,
    ],
}
"""Maps platform event names to the list of services that should be notified.

Each service in the list will receive an HTTP POST when the corresponding
event fires, provided the user has an active integration for that service.
"""


# ---------------------------------------------------------------------------
# Service base URL lookup (mirrors SERVICE_CATALOG)
# ---------------------------------------------------------------------------

def _get_service_base_url(service_name: ServiceName) -> str:
    """Return the base URL for a service, using the SERVICE_CATALOG.

    Lazy-imports ``SERVICE_CATALOG`` to avoid circular import issues at
    module load time.

    Args:
        service_name: The service to look up.

    Returns:
        The base URL string (e.g. ``"http://localhost:8101"``).
    """
    from app.services.service_integration_service import SERVICE_CATALOG
    catalog = SERVICE_CATALOG.get(service_name, {})
    return catalog.get("base_url", "")


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.tasks.bridge_tasks.dispatch_platform_event",
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_platform_event(
    self,
    user_id: str,
    store_id: str | None,
    event: str,
    resource_id: str,
    resource_type: str,
    payload: dict,
) -> dict:
    """Dispatch a platform event to all matching connected services.

    Finds all active service integrations for the user, filters to those
    subscribed to the event type via ``EVENT_SERVICE_MAP``, delivers the
    payload via HTTP POST with HMAC-SHA256 signing, and records a
    ``BridgeDelivery`` row for each attempt.

    Args:
        user_id: UUID string of the platform user.
        store_id: UUID string of the store (may be None).
        event: Event type (e.g. ``"product.created"``).
        resource_id: UUID string of the resource that triggered the event.
        resource_type: Type string (``"product"``, ``"order"``,
            ``"customer"``).
        payload: The event data dict.

    Returns:
        Dict with ``delivery_count``, ``success_count``, and
        ``failure_count`` keys.
    """
    from app.models.bridge_delivery import BridgeDelivery
    from app.models.service_integration import ServiceIntegration
    from app.services.bridge_service import sign_bridge_payload

    # Look up which services care about this event
    target_services = EVENT_SERVICE_MAP.get(event, [])
    if not target_services:
        logger.info("No services mapped for event %s", event)
        return {"delivery_count": 0, "success_count": 0, "failure_count": 0}

    session = SyncSessionFactory()
    try:
        # Find user's active integrations for the target services
        integrations = (
            session.query(ServiceIntegration)
            .filter(
                ServiceIntegration.user_id == uuid.UUID(user_id),
                ServiceIntegration.is_active.is_(True),
                ServiceIntegration.service_name.in_(target_services),
            )
            .all()
        )

        if not integrations:
            logger.info(
                "No active integrations for user %s event %s",
                user_id[:8], event,
            )
            return {"delivery_count": 0, "success_count": 0, "failure_count": 0}

        # Build the full event envelope
        full_payload = {
            "event": event,
            "store_id": store_id,
            "user_id": user_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        payload_json = json.dumps(full_payload, default=str)

        success_count = 0
        failure_count = 0

        for integration in integrations:
            base_url = _get_service_base_url(integration.service_name)
            if not base_url:
                logger.warning(
                    "No base_url for service %s, skipping",
                    integration.service_name.value,
                )
                continue

            url = f"{base_url}/api/v1/webhooks/platform-events"
            # Use the platform shared secret for HMAC signing so the
            # receiving service can verify without a per-user DB lookup.
            from app.config import settings as platform_settings
            signing_secret = platform_settings.platform_webhook_secret
            signature = sign_bridge_payload(payload_json, signing_secret)
            headers = {
                "Content-Type": "application/json",
                "X-Platform-Signature": f"sha256={signature}",
                "X-Platform-Event": event,
            }

            response_status = None
            response_body = None
            success = False
            error_message = None
            start_time = time.monotonic()

            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, content=payload_json, headers=headers)
                    response_status = resp.status_code
                    response_body = resp.text[:1000]
                    success = 200 <= resp.status_code < 300
                    if not success:
                        error_message = f"HTTP {resp.status_code}"
            except httpx.TimeoutException:
                error_message = "Timeout after 10s"
                logger.warning(
                    "Bridge timeout: service=%s event=%s",
                    integration.service_name.value, event,
                )
            except Exception as e:
                error_message = str(e)[:500]
                response_body = str(e)[:1000]
                logger.warning(
                    "Bridge delivery failed: service=%s event=%s error=%s",
                    integration.service_name.value, event, str(e)[:200],
                )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Record the delivery attempt
            delivery = BridgeDelivery(
                user_id=uuid.UUID(user_id),
                store_id=uuid.UUID(store_id) if store_id else None,
                integration_id=integration.id,
                service_name=integration.service_name,
                event=event,
                resource_id=resource_id,
                resource_type=resource_type,
                payload=full_payload,
                response_status=response_status,
                response_body=response_body,
                success=success,
                error_message=error_message,
                latency_ms=elapsed_ms,
            )
            session.add(delivery)

            if success:
                success_count += 1
            else:
                failure_count += 1

        session.commit()

        total = success_count + failure_count
        logger.info(
            "Bridge dispatch: event=%s user=%s matched=%d success=%d failed=%d",
            event, user_id[:8], total, success_count, failure_count,
        )
        return {
            "delivery_count": total,
            "success_count": success_count,
            "failure_count": failure_count,
        }
    except Exception as exc:
        session.rollback()
        logger.error("dispatch_platform_event failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()
