"""
Service layer for SMS campaign operations in FlowSend.

Developer:
    Provides async functions for creating, listing, sending, and analyzing
    SMS campaigns. All functions accept an AsyncSession and user_id for
    multi-tenant isolation. The send function uses the pluggable SmsSender
    abstraction (console in dev, Twilio/SNS in production).

Project Manager:
    Core business logic for the SMS marketing feature. Covers campaign CRUD,
    bulk send orchestration, and per-campaign delivery analytics.

QA Engineer:
    Test each function in isolation with a test schema DB session. Verify:
    - Campaigns are created with channel="sms"
    - Listing filters by channel and user
    - Send creates SmsEvent per contact, updates counts
    - Analytics aggregates event types correctly
    - ValueError raised when campaign not found

End User:
    Powers the SMS campaign workflows: create a campaign, target a contact
    list, send messages, and review delivery statistics.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.sms_event import SmsEvent
from app.services.sms_sender import get_sms_sender


async def create_sms_campaign(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    sms_body: str,
    list_id: UUID | None = None,
    scheduled_at: datetime | None = None,
) -> Campaign:
    """Create a new SMS campaign record.

    Sets the campaign channel to "sms" and uses the name as the subject
    field for compatibility with shared campaign infrastructure.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user who owns the campaign.
        name: Human-readable campaign name.
        sms_body: The SMS message content (max 1600 chars enforced at schema level).
        list_id: Optional contact list UUID to target.
        scheduled_at: Optional future datetime to schedule the send.

    Returns:
        The newly created Campaign ORM instance.
    """
    campaign = Campaign(
        user_id=user_id,
        name=name,
        subject=name,
        channel="sms",
        sms_body=sms_body,
        list_id=list_id,
        status="draft",
        scheduled_at=scheduled_at,
        total_recipients=0,
        sent_count=0,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_sms_campaigns(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> list[Campaign]:
    """List SMS campaigns for a user with pagination.

    Filters campaigns to channel="sms" and orders by creation date descending.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user.
        page: Page number (1-indexed).
        page_size: Number of campaigns per page.

    Returns:
        List of Campaign ORM instances for the requested page.
    """
    offset = (page - 1) * page_size
    stmt = (
        select(Campaign)
        .where(Campaign.user_id == user_id, Campaign.channel == "sms")
        .order_by(Campaign.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_sms_campaign(
    db: AsyncSession,
    user_id: UUID,
    campaign_id: UUID,
) -> Campaign:
    """Retrieve a single SMS campaign by ID.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user.
        campaign_id: UUID of the campaign to retrieve.

    Returns:
        The Campaign ORM instance.

    Raises:
        ValueError: If the campaign does not exist, does not belong to the user,
            or is not an SMS campaign.
    """
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.user_id == user_id,
        Campaign.channel == "sms",
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise ValueError(f"SMS campaign {campaign_id} not found")
    return campaign


async def send_sms_campaign_mock(
    db: AsyncSession,
    campaign: Campaign,
) -> Campaign:
    """Mock-send an SMS campaign to all subscribed contacts in its list.

    Retrieves contacts who have sms_subscribed=True (and belong to the campaign's
    list if one is set), creates an SmsEvent for each, and updates the campaign's
    sent counts. Uses the pluggable SMS sender for console/provider output.

    Args:
        db: Async database session.
        campaign: The Campaign ORM instance to send.

    Returns:
        The updated Campaign ORM instance with sent counts and status.
    """
    sender = get_sms_sender()

    # Build contact query — filter by list if specified
    contact_query = select(Contact).where(
        Contact.user_id == campaign.user_id,
        Contact.sms_subscribed.is_(True),
    )
    if campaign.list_id is not None:
        contact_query = contact_query.where(Contact.list_id == campaign.list_id)

    result = await db.execute(contact_query)
    contacts = list(result.scalars().all())

    sent_count = 0
    for contact in contacts:
        if not contact.phone_number:
            continue

        # Use the sender abstraction (console logging in dev)
        await sender.send(
            to=contact.phone_number,
            body=campaign.sms_body or "",
        )

        # Record the delivery event
        event = SmsEvent(
            campaign_id=campaign.id,
            contact_id=contact.id,
            event_type="sent",
            provider_message_id=f"mock-{campaign.id}-{contact.id}",
        )
        db.add(event)
        sent_count += 1

    # Update campaign status and counts
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Campaign)
        .where(Campaign.id == campaign.id)
        .values(
            status="sent",
            sent_at=now,
            total_recipients=len(contacts),
            sent_count=sent_count,
        )
    )
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_sms_campaign_analytics(
    db: AsyncSession,
    user_id: UUID,
    campaign_id: UUID,
) -> dict:
    """Aggregate SMS delivery event counts for a campaign.

    Verifies the campaign belongs to the user, then groups SmsEvent records
    by event_type and returns a summary dictionary.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user.
        campaign_id: UUID of the campaign to analyze.

    Returns:
        Dictionary with keys: campaign_id, total_sent, delivered, failed,
        and a breakdown dict mapping event_type to count.

    Raises:
        ValueError: If the campaign does not exist or does not belong to the user.
    """
    # Verify ownership
    campaign = await get_sms_campaign(db, user_id, campaign_id)

    # Aggregate event counts by type
    stmt = (
        select(SmsEvent.event_type, func.count(SmsEvent.id))
        .where(SmsEvent.campaign_id == campaign.id)
        .group_by(SmsEvent.event_type)
    )
    result = await db.execute(stmt)
    breakdown = {row[0]: row[1] for row in result.all()}

    return {
        "campaign_id": str(campaign.id),
        "total_sent": breakdown.get("sent", 0),
        "delivered": breakdown.get("delivered", 0),
        "failed": breakdown.get("failed", 0),
        "breakdown": breakdown,
    }
