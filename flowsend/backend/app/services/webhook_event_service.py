"""
Service for processing inbound email delivery webhooks from SES and SendGrid.

Developer:
    Two entry points: process_ses_event() and process_sendgrid_event(). Each
    accepts raw webhook payload data (dict), maps provider-specific event types
    to the internal EmailEvent model, and persists the record. Both functions
    are async and require an AsyncSession.

    SES event mapping (from SNS notification):
        Bounce    -> "bounced"
        Complaint -> "bounced"
        Delivery  -> "delivered"
        Open      -> "opened"
        Click     -> "clicked"

    SendGrid event mapping:
        delivered   -> "delivered"
        bounce      -> "bounced"
        open        -> "opened"
        click       -> "clicked"
        unsubscribe -> "unsubscribed"

Project Manager:
    Enables real-time email delivery tracking by ingesting webhook callbacks
    from AWS SES and SendGrid. Events are stored as EmailEvent records for
    campaign analytics and contact engagement scoring.

QA Engineer:
    Test with sample webhook payloads from SES and SendGrid docs. Verify:
    - Correct event_type mapping for each provider event
    - EmailEvent record created with correct contact_id and campaign_id
    - Unknown event types return None (no record created)
    - Missing fields handled gracefully without exceptions

End User:
    Automatic behind-the-scenes tracking — merchants see delivery, bounce,
    open, and click stats on their campaign analytics dashboard without
    any manual action.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import EmailEvent

# SES SNS notification type -> internal event type
SES_EVENT_MAP: dict[str, str] = {
    "Bounce": "bounced",
    "Complaint": "bounced",
    "Delivery": "delivered",
    "Open": "opened",
    "Click": "clicked",
}

# SendGrid webhook event -> internal event type
SENDGRID_EVENT_MAP: dict[str, str] = {
    "delivered": "delivered",
    "bounce": "bounced",
    "open": "opened",
    "click": "clicked",
    "unsubscribe": "unsubscribed",
}


async def process_ses_event(
    db: AsyncSession,
    event_data: dict,
) -> EmailEvent | None:
    """Process an AWS SES delivery notification received via SNS.

    Parses the SES event structure, maps the notification type to an internal
    event type, and creates an EmailEvent record.

    Expected event_data structure (SNS message body, already parsed to dict):
        {
            "notificationType": "Bounce" | "Complaint" | "Delivery" | "Open" | "Click",
            "mail": {
                "messageId": "...",
                "tags": {
                    "campaign_id": ["<uuid>"],
                    "contact_id": ["<uuid>"]
                }
            },
            "bounce": { ... },   # present for Bounce
            "complaint": { ... } # present for Complaint
        }

    Args:
        db: Async database session.
        event_data: Parsed SES SNS notification payload.

    Returns:
        The created EmailEvent if the event type is recognized, or None if
        the notification type is not mapped.
    """
    notification_type = event_data.get("notificationType")
    if not notification_type:
        return None

    internal_type = SES_EVENT_MAP.get(notification_type)
    if internal_type is None:
        return None

    # Extract identifiers from the mail object
    mail = event_data.get("mail", {})
    message_id = mail.get("messageId")
    tags = mail.get("tags", {})

    campaign_id_list = tags.get("campaign_id", [])
    contact_id_list = tags.get("contact_id", [])

    campaign_id = _parse_uuid(campaign_id_list[0]) if campaign_id_list else None
    contact_id = _parse_uuid(contact_id_list[0]) if contact_id_list else None

    if contact_id is None:
        return None

    # Extract error details for bounce/complaint
    error_code = None
    if notification_type == "Bounce":
        bounce = event_data.get("bounce", {})
        error_code = bounce.get("bounceType")
    elif notification_type == "Complaint":
        complaint = event_data.get("complaint", {})
        error_code = complaint.get("complaintFeedbackType")

    email_event = EmailEvent(
        campaign_id=campaign_id,
        contact_id=contact_id,
        event_type=internal_type,
        provider_message_id=message_id,
        error_code=error_code,
    )
    db.add(email_event)
    await db.commit()
    await db.refresh(email_event)
    return email_event


async def process_sendgrid_event(
    db: AsyncSession,
    event_data: dict,
) -> EmailEvent | None:
    """Process a SendGrid Event Webhook payload.

    Maps SendGrid event types to internal EmailEvent types and persists
    the record.

    Expected event_data structure (single event from SendGrid webhook array):
        {
            "event": "delivered" | "bounce" | "open" | "click" | "unsubscribe",
            "sg_message_id": "...",
            "campaign_id": "<uuid>",
            "contact_id": "<uuid>",
            "reason": "..."  # present for bounce events
        }

    Args:
        db: Async database session.
        event_data: A single parsed SendGrid webhook event dict.

    Returns:
        The created EmailEvent if the event type is recognized, or None if
        the event type is not mapped.
    """
    sg_event = event_data.get("event")
    if not sg_event:
        return None

    internal_type = SENDGRID_EVENT_MAP.get(sg_event)
    if internal_type is None:
        return None

    contact_id = _parse_uuid(event_data.get("contact_id"))
    if contact_id is None:
        return None

    campaign_id = _parse_uuid(event_data.get("campaign_id"))
    message_id = event_data.get("sg_message_id")

    # Extract error info for bounces
    error_code = None
    if sg_event == "bounce":
        error_code = event_data.get("reason")

    email_event = EmailEvent(
        campaign_id=campaign_id,
        contact_id=contact_id,
        event_type=internal_type,
        provider_message_id=message_id,
        error_code=error_code,
    )
    db.add(email_event)
    await db.commit()
    await db.refresh(email_event)
    return email_event


def _parse_uuid(value: str | None) -> UUID | None:
    """Safely parse a string to UUID, returning None on failure.

    Args:
        value: A string that may represent a UUID.

    Returns:
        Parsed UUID or None if the value is None or not a valid UUID.
    """
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None
