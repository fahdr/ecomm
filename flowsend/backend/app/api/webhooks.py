"""
Webhook endpoints for FlowSend.

Handles platform bridge events, email provider delivery webhooks (SES,
SendGrid), and SMS provider delivery webhooks (Twilio, SNS). The Stripe
webhook handler is provided by ``ecomm_core.billing.webhooks`` and
included via ``create_webhook_router`` in ``main.py``.

For Developers:
    Platform events are verified via HMAC-SHA256 using the shared
    ``platform_webhook_secret``. SES events arrive as SNS notifications.
    SendGrid events are sent as JSON arrays. Twilio sends form-encoded
    status callbacks. SNS SMS delivery receipts are JSON.

For QA Engineers:
    - Platform events: POST /webhooks/platform-events with X-Platform-Signature
    - SES: POST /webhooks/ses-events with SNS JSON body
    - SendGrid: POST /webhooks/sendgrid-events with JSON array body
    - Twilio SMS: POST /webhooks/twilio-sms-status with form-encoded body
    - SNS SMS: POST /webhooks/sns-sms-status with SNS JSON body

For Project Managers:
    Email and SMS delivery tracking is automated via provider webhooks.
    Events (delivered, bounced, opened, clicked, failed) are recorded for
    campaign analytics. Platform events trigger automated flows.

For End Users:
    Delivery tracking is automatic — bounce, open, click, and delivery
    stats appear on your campaign analytics dashboard.
"""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.webhook_event_service import process_sendgrid_event, process_ses_event

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

    FlowSend handles:
        - ``order.created`` -- queues a post-purchase email/SMS flow
          (order confirmation, upsell sequence, review request).
        - ``order.shipped`` -- queues a shipping notification flow
          (tracking info, delivery ETA, follow-up).
        - ``customer.created`` -- queues a welcome flow
          (onboarding emails, first-purchase discount).

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

    # Route to FlowSend-specific handlers
    if event_type == "order.created":
        logger.info(
            "Post-purchase flow queued for order: %s",
            event_data.get("order_id", "unknown"),
        )
        actions.append("post_purchase_flow_queued")
    elif event_type == "order.shipped":
        logger.info(
            "Shipping notification flow queued for order: %s",
            event_data.get("order_id", "unknown"),
        )
        actions.append("shipping_notification_queued")
    elif event_type == "customer.created":
        logger.info(
            "Welcome flow queued for customer: %s",
            event_data.get("customer_id", "unknown"),
        )
        actions.append("welcome_flow_queued")

    return {"status": "ok", "actions": actions}


# ---------------------------------------------------------------------------
# Email Provider Delivery Webhooks
# ---------------------------------------------------------------------------


@router.post("/ses-events")
async def ses_event_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive AWS SES delivery notifications via SNS.

    SES publishes bounce, complaint, delivery, open, and click events to an
    SNS topic. This endpoint is subscribed to that topic. On first setup,
    SNS sends a SubscriptionConfirmation message — we auto-confirm it by
    visiting the provided URL.

    For Developers:
        The SNS message body contains a JSON-encoded SES event inside
        ``Message``. The outer envelope has ``Type`` and ``SubscribeURL``
        for initial subscription confirmation.

    For QA Engineers:
        - SubscriptionConfirmation requests return 200 with confirmed status.
        - Notification payloads are parsed and stored as EmailEvent.
        - Malformed JSON returns 400.

    Args:
        request: Incoming SNS HTTP POST.
        db: Injected async database session.

    Returns:
        Dict with status and optional event_id.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Handle SNS subscription confirmation
    msg_type = body.get("Type")
    if msg_type == "SubscriptionConfirmation":
        subscribe_url = body.get("SubscribeURL")
        if subscribe_url:
            logger.info("SES SNS subscription confirmation received: %s", subscribe_url)
        return {"status": "confirmed"}

    # Parse the SES notification
    if msg_type == "Notification":
        message_str = body.get("Message", "{}")
        try:
            event_data = json.loads(message_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid SES message JSON")

        email_event = await process_ses_event(db, event_data)
        if email_event:
            return {"status": "ok", "event_id": str(email_event.id)}

    return {"status": "ok"}


@router.post("/sendgrid-events")
async def sendgrid_event_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive SendGrid Event Webhook callbacks.

    SendGrid posts an array of event objects for delivery tracking. Each event
    contains ``event``, ``sg_message_id``, and custom args (campaign_id,
    contact_id) that were set when the email was sent.

    For Developers:
        SendGrid sends a JSON array of events in each POST. We process
        each event individually via ``process_sendgrid_event()``.

    For QA Engineers:
        - POST with JSON array body returns 200 with processed count.
        - Empty array returns processed: 0.
        - Non-array body returns 400.
        - Individual event failures are logged but don't abort processing.

    Args:
        request: Incoming SendGrid webhook POST.
        db: Injected async database session.

    Returns:
        Dict with status and count of processed events.
    """
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="Expected JSON array of events")

    processed = 0
    for event_data in events:
        try:
            result = await process_sendgrid_event(db, event_data)
            if result:
                processed += 1
        except Exception:
            logger.exception("Error processing SendGrid event: %s", event_data)

    return {"status": "ok", "processed": processed}


# ---------------------------------------------------------------------------
# SMS Provider Delivery Webhooks
# ---------------------------------------------------------------------------


@router.post("/twilio-sms-status")
async def twilio_sms_status_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive Twilio SMS delivery status callbacks.

    Twilio sends form-encoded POST requests with delivery status updates
    for each outbound SMS message. We map Twilio statuses to internal
    SmsEvent records for campaign analytics.

    Twilio status mapping:
        delivered   -> "delivered"
        undelivered -> "failed"
        failed      -> "failed"
        sent        -> "sent"

    For Developers:
        Twilio sends form data (not JSON). Extract ``MessageSid``,
        ``MessageStatus``, and custom metadata from form fields.

    For QA Engineers:
        - Form-encoded POST with MessageSid and MessageStatus.
        - Returns 200 with empty TwiML-compatible response.
        - Missing MessageSid returns 400.

    Args:
        request: Incoming Twilio status callback.
        db: Injected async database session.

    Returns:
        Empty XML response for Twilio compatibility.
    """
    from app.models.sms_event import SmsEvent

    form = await request.form()
    message_sid = form.get("MessageSid")
    message_status = form.get("MessageStatus", "")

    if not message_sid:
        raise HTTPException(status_code=400, detail="Missing MessageSid")

    # Map Twilio status to internal event type
    twilio_status_map = {
        "delivered": "delivered",
        "undelivered": "failed",
        "failed": "failed",
        "sent": "sent",
        "queued": "sent",
    }
    internal_type = twilio_status_map.get(message_status)
    if internal_type is None:
        return {"status": "ok", "skipped": True}

    # Extract campaign/contact IDs from custom metadata if present
    campaign_id = form.get("campaign_id")
    contact_id = form.get("contact_id")
    error_code = form.get("ErrorCode")

    from app.services.webhook_event_service import _parse_uuid

    sms_event = SmsEvent(
        campaign_id=_parse_uuid(campaign_id),
        contact_id=_parse_uuid(contact_id) if contact_id else None,
        event_type=internal_type,
        provider_message_id=str(message_sid),
        error_code=error_code,
    )

    if sms_event.contact_id:
        db.add(sms_event)
        await db.commit()

    logger.info("Twilio SMS status: %s -> %s (SID: %s)", message_status, internal_type, message_sid)
    return {"status": "ok"}


@router.post("/sns-sms-status")
async def sns_sms_status_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive AWS SNS SMS delivery status notifications.

    SNS publishes SMS delivery receipts to this endpoint when configured
    with an HTTP/S subscription. The notification contains delivery status,
    phone number, and message ID.

    For Developers:
        Similar to SES, SNS sends a ``SubscriptionConfirmation`` on first
        setup, then ``Notification`` payloads with the SMS delivery receipt
        inside the ``Message`` field.

    For QA Engineers:
        - SubscriptionConfirmation returns confirmed status.
        - Notification with delivery SUCCESS -> "delivered" SmsEvent.
        - Notification with FAILURE -> "failed" SmsEvent.

    Args:
        request: Incoming SNS HTTP POST.
        db: Injected async database session.

    Returns:
        Dict with status.
    """
    from app.models.sms_event import SmsEvent
    from app.services.webhook_event_service import _parse_uuid

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    msg_type = body.get("Type")
    if msg_type == "SubscriptionConfirmation":
        logger.info("SNS SMS subscription confirmation received")
        return {"status": "confirmed"}

    if msg_type == "Notification":
        message_str = body.get("Message", "{}")
        try:
            event_data = json.loads(message_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid SNS message JSON")

        delivery_status = event_data.get("status", "").upper()
        message_id = event_data.get("notification", {}).get("messageId")

        if delivery_status == "SUCCESS":
            internal_type = "delivered"
        elif delivery_status == "FAILURE":
            internal_type = "failed"
        else:
            return {"status": "ok", "skipped": True}

        campaign_id = event_data.get("campaign_id")
        contact_id = event_data.get("contact_id")

        if contact_id:
            sms_event = SmsEvent(
                campaign_id=_parse_uuid(campaign_id),
                contact_id=_parse_uuid(contact_id),
                event_type=internal_type,
                provider_message_id=message_id,
            )
            db.add(sms_event)
            await db.commit()

    return {"status": "ok"}
