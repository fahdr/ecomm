"""Webhook delivery Celery tasks.

Dispatches HTTP POST requests to store-owner-configured webhook endpoints
when business events occur. Payloads are signed with HMAC-SHA256 for
authenticity verification.

**For Developers:**
    The task queries active ``StoreWebhook`` rows subscribed to the event,
    signs the payload with each webhook's secret, and sends an HTTP POST
    via ``httpx.Client``. Delivery attempts are recorded in
    ``WebhookDelivery``. Webhooks are auto-disabled after 10 consecutive
    failures.

**For QA Engineers:**
    - The ``X-Webhook-Signature`` header contains ``sha256=<hex_digest>``.
    - A delivery is considered successful if the HTTP status is 2xx.
    - ``failure_count`` increments on each failed delivery and resets to
      0 on success.
    - Webhooks with ``failure_count >= 10`` are set to ``is_active=False``.

**For Project Managers:**
    This task powers the webhook delivery system (Feature 23) enabling
    store owners to integrate their store with external services via
    real-time event notifications.

**For End Users:**
    When events happen in your store (new orders, product updates, etc.),
    webhooks automatically notify your connected external services so you
    can automate inventory sync, fulfillment, and other workflows.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.webhook_tasks.dispatch_webhook_event",
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_webhook_event(self, store_id: str, event: str, payload: dict) -> dict:
    """Dispatch a webhook event to all subscribed endpoints for a store.

    Finds all active webhooks for the store that subscribe to the given
    event, signs the payload, sends HTTP POST requests, and records
    delivery results.

    Args:
        store_id: UUID string of the store.
        event: The event type string (e.g. ``"order.paid"``).
        payload: The event payload dict to deliver.

    Returns:
        Dict with ``delivery_count``, ``success_count``, and
        ``failure_count`` keys.
    """
    from app.models.webhook import StoreWebhook, WebhookDelivery
    from app.services.webhook_service import sign_payload

    session = SyncSessionFactory()
    try:
        webhooks = (
            session.query(StoreWebhook)
            .filter(
                StoreWebhook.store_id == uuid.UUID(store_id),
                StoreWebhook.is_active.is_(True),
            )
            .all()
        )

        # Filter to webhooks subscribed to this event
        matching = [w for w in webhooks if event in (w.events or [])]

        if not matching:
            return {"delivery_count": 0, "success_count": 0, "failure_count": 0}

        success_count = 0
        failure_count = 0

        full_payload = {
            "event": event,
            "store_id": store_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        payload_json = json.dumps(full_payload, default=str)

        for webhook in matching:
            signature = sign_payload(payload_json, webhook.secret)
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={signature}",
                "X-Webhook-Event": event,
            }

            response_status = None
            response_body = None
            success = False

            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        webhook.url,
                        content=payload_json,
                        headers=headers,
                    )
                    response_status = resp.status_code
                    response_body = resp.text[:1000]
                    success = 200 <= resp.status_code < 300
            except httpx.TimeoutException:
                response_body = "Timeout after 10s"
                logger.warning(
                    "Webhook timeout: url=%s event=%s", webhook.url, event
                )
            except Exception as e:
                response_body = str(e)[:1000]
                logger.warning(
                    "Webhook delivery failed: url=%s event=%s error=%s",
                    webhook.url, event, str(e)[:200],
                )

            # Record the delivery attempt
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event=event,
                payload=full_payload,
                response_status=response_status,
                response_body=response_body,
                success=success,
            )
            session.add(delivery)

            # Update webhook state
            webhook.last_triggered_at = datetime.now(timezone.utc)
            if success:
                webhook.failure_count = 0
                success_count += 1
            else:
                webhook.failure_count = (webhook.failure_count or 0) + 1
                failure_count += 1
                # Auto-disable after 10 consecutive failures
                if webhook.failure_count >= 10:
                    webhook.is_active = False
                    logger.warning(
                        "Webhook auto-disabled after 10 failures: id=%s url=%s",
                        webhook.id, webhook.url,
                    )

        session.commit()
        logger.info(
            "Webhook dispatch: event=%s store=%s matched=%d success=%d failed=%d",
            event, store_id[:8], len(matching), success_count, failure_count,
        )
        return {
            "delivery_count": len(matching),
            "success_count": success_count,
            "failure_count": failure_count,
        }
    except Exception as exc:
        session.rollback()
        logger.error("dispatch_webhook_event failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()
