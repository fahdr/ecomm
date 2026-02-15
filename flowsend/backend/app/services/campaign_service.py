"""
Campaign management service.

Handles CRUD operations for email campaigns, including scheduling,
mock sending, and event tracking.

For Developers:
    - Campaign lifecycle: draft -> scheduled -> sending -> sent (or failed).
    - `send_campaign` creates mock EmailEvent records for all contacts in the list.
    - In production, this would integrate with an ESP (e.g. SendGrid, SES).
    - Event tracking updates denormalized counters on the Campaign record.

For QA Engineers:
    Test: campaign CRUD, scheduling, mock send (verify events created),
    status transitions, analytics correctness, draft-only updates.

For Project Managers:
    Campaigns are the primary email sending mechanism. Analytics (open/click/bounce)
    are derived from EmailEvent records.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, EmailEvent
from app.models.contact import Contact
from app.models.user import User


async def create_campaign(
    db: AsyncSession, user: User, name: str, subject: str,
    template_id: uuid.UUID | None = None, list_id: uuid.UUID | None = None,
    scheduled_at: datetime | None = None,
) -> Campaign:
    """
    Create a new email campaign.

    Args:
        db: Async database session.
        user: The owning user.
        name: Campaign display name.
        subject: Email subject line.
        template_id: UUID of the template to use (optional).
        list_id: UUID of the target contact list (optional).
        scheduled_at: Scheduled send time (optional).

    Returns:
        The newly created Campaign in "draft" status.
    """
    status = "scheduled" if scheduled_at else "draft"

    campaign = Campaign(
        user_id=user.id,
        name=name,
        subject=subject,
        template_id=template_id,
        list_id=list_id,
        status=status,
        scheduled_at=scheduled_at,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def get_campaigns(
    db: AsyncSession, user_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
    status: str | None = None,
) -> tuple[list[Campaign], int]:
    """
    List campaigns with pagination and optional status filter.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        page: Page number (1-indexed).
        page_size: Items per page.
        status: Optional status filter.

    Returns:
        Tuple of (list of Campaign, total count).
    """
    query = select(Campaign).where(Campaign.user_id == user_id)
    count_query = select(func.count(Campaign.id)).where(Campaign.user_id == user_id)

    if status:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Campaign.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    campaigns = list(result.scalars().all())

    return campaigns, total


async def get_campaign(
    db: AsyncSession, user_id: uuid.UUID, campaign_id: uuid.UUID
) -> Campaign | None:
    """
    Get a single campaign by ID, scoped to user.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        campaign_id: The campaign's UUID.

    Returns:
        The Campaign if found, None otherwise.
    """
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_campaign(
    db: AsyncSession, campaign: Campaign,
    name: str | None = None, subject: str | None = None,
    template_id: uuid.UUID | None = None, list_id: uuid.UUID | None = None,
    scheduled_at: datetime | None = None,
) -> Campaign:
    """
    Update a draft campaign.

    Only campaigns in "draft" status can be updated.

    Args:
        db: Async database session.
        campaign: The campaign to update.
        name: Updated name (optional).
        subject: Updated subject (optional).
        template_id: Updated template UUID (optional).
        list_id: Updated list UUID (optional).
        scheduled_at: Updated scheduled time (optional).

    Returns:
        The updated Campaign.

    Raises:
        ValueError: If campaign is not in "draft" status.
    """
    if campaign.status not in ("draft", "scheduled"):
        raise ValueError("Can only update draft or scheduled campaigns")

    if name is not None:
        campaign.name = name
    if subject is not None:
        campaign.subject = subject
    if template_id is not None:
        campaign.template_id = template_id
    if list_id is not None:
        campaign.list_id = list_id
    if scheduled_at is not None:
        campaign.scheduled_at = scheduled_at
        campaign.status = "scheduled"

    await db.flush()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(db: AsyncSession, campaign: Campaign) -> None:
    """
    Delete a campaign and its events.

    Only draft or scheduled campaigns can be deleted.

    Args:
        db: Async database session.
        campaign: The campaign to delete.

    Raises:
        ValueError: If campaign has already been sent.
    """
    if campaign.status in ("sending", "sent"):
        raise ValueError("Cannot delete a campaign that has been sent")

    await db.delete(campaign)
    await db.flush()


async def send_campaign_mock(db: AsyncSession, campaign: Campaign) -> Campaign:
    """
    Mock send a campaign by creating email events for all user contacts.

    In production, this would queue actual email delivery via an ESP.
    Here we simulate by creating "sent" and some "delivered" events.

    Args:
        db: Async database session.
        campaign: The campaign to send.

    Returns:
        The updated Campaign with sent status and counts.

    Raises:
        ValueError: If campaign is not in draft/scheduled status.
    """
    if campaign.status not in ("draft", "scheduled"):
        raise ValueError("Campaign must be in draft or scheduled status to send")

    campaign.status = "sending"
    await db.flush()

    # Get all subscribed contacts for this user
    result = await db.execute(
        select(Contact).where(
            Contact.user_id == campaign.user_id,
            Contact.is_subscribed.is_(True),
        )
    )
    contacts = list(result.scalars().all())

    now = datetime.now(UTC)
    sent_count = 0

    for contact in contacts:
        # Create "sent" event
        event = EmailEvent(
            campaign_id=campaign.id,
            contact_id=contact.id,
            event_type="sent",
            extra_metadata={"subject": campaign.subject},
            created_at=now,
        )
        db.add(event)
        sent_count += 1

        # Simulate ~80% delivery
        if sent_count % 5 != 0:
            delivered_event = EmailEvent(
                campaign_id=campaign.id,
                contact_id=contact.id,
                event_type="delivered",
                created_at=now,
            )
            db.add(delivered_event)

    campaign.total_recipients = len(contacts)
    campaign.sent_count = sent_count
    campaign.sent_at = now
    campaign.status = "sent"

    await db.flush()
    await db.refresh(campaign)
    return campaign


async def get_campaign_events(
    db: AsyncSession, campaign_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
    event_type: str | None = None,
) -> tuple[list[EmailEvent], int]:
    """
    List email events for a campaign with pagination.

    Args:
        db: Async database session.
        campaign_id: The campaign's UUID.
        page: Page number (1-indexed).
        page_size: Items per page.
        event_type: Optional event type filter.

    Returns:
        Tuple of (list of EmailEvent, total count).
    """
    query = select(EmailEvent).where(EmailEvent.campaign_id == campaign_id)
    count_query = select(func.count(EmailEvent.id)).where(
        EmailEvent.campaign_id == campaign_id
    )

    if event_type:
        query = query.where(EmailEvent.event_type == event_type)
        count_query = count_query.where(EmailEvent.event_type == event_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(EmailEvent.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    events = list(result.scalars().all())

    return events, total
