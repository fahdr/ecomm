"""
Campaign management API endpoints.

Provides CRUD for email campaigns, plus scheduling, sending, and
per-campaign analytics.

For Developers:
    Campaign sending is mocked: `send_campaign_mock` creates EmailEvent
    records for all subscribed contacts. In production, this would
    queue actual email delivery via a Celery task.

For QA Engineers:
    Test: create, list, get, update (draft only), delete, send (mock),
    analytics endpoint, status transitions.

For Project Managers:
    Campaigns drive email marketing ROI. The send + analytics flow
    is the core user workflow.

For End Users:
    Create campaigns, choose a template and contact list, schedule
    or send immediately, then track performance.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.email import (
    CampaignAnalytics,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    EmailEventResponse,
    PaginatedResponse,
)
from app.services.analytics_service import get_campaign_analytics
from app.services.campaign_service import (
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_events,
    get_campaigns,
    send_campaign_mock,
    update_campaign,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign_endpoint(
    body: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new email campaign.

    If `scheduled_at` is provided, the campaign is created in "scheduled" status.
    Otherwise, it starts as "draft".

    Args:
        body: Campaign creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created campaign.
    """
    campaign = await create_campaign(
        db, current_user, body.name, body.subject,
        template_id=body.template_id, list_id=body.list_id,
        scheduled_at=body.scheduled_at,
    )
    return campaign


@router.get("", response_model=PaginatedResponse[CampaignResponse])
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    campaign_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List campaigns with pagination and optional status filter.

    Args:
        page: Page number.
        page_size: Items per page.
        campaign_status: Optional status filter.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of campaigns.
    """
    campaigns, total = await get_campaigns(
        db, current_user.id, page=page, page_size=page_size,
        status=campaign_status,
    )
    return PaginatedResponse(
        items=campaigns, total=total, page=page, page_size=page_size
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign_endpoint(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single campaign by ID.

    Args:
        campaign_id: The campaign's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The campaign data.

    Raises:
        HTTPException 404: If campaign not found.
    """
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign_endpoint(
    campaign_id: uuid.UUID,
    body: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a campaign (draft or scheduled only).

    Args:
        campaign_id: The campaign's UUID.
        body: Update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated campaign.

    Raises:
        HTTPException 404: If campaign not found.
        HTTPException 400: If campaign is not in draft/scheduled status.
    """
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        updated = await update_campaign(
            db, campaign,
            name=body.name, subject=body.subject,
            template_id=body.template_id, list_id=body.list_id,
            scheduled_at=body.scheduled_at,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign_endpoint(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a campaign (draft or scheduled only).

    Args:
        campaign_id: The campaign's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If campaign not found.
        HTTPException 400: If campaign has already been sent.
    """
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        await delete_campaign(db, campaign)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{campaign_id}/send", response_model=CampaignResponse)
async def send_campaign_endpoint(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a campaign (mock: creates email events for all subscribed contacts).

    Args:
        campaign_id: The campaign's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated campaign with sent status and counts.

    Raises:
        HTTPException 404: If campaign not found.
        HTTPException 400: If campaign is not in sendable status.
    """
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        sent = await send_campaign_mock(db, campaign)
        return sent
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalytics)
async def get_campaign_analytics_endpoint(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics for a single campaign.

    Args:
        campaign_id: The campaign's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Campaign analytics with rates and totals.

    Raises:
        HTTPException 404: If campaign not found.
    """
    analytics = await get_campaign_analytics(db, current_user.id, campaign_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return analytics


@router.get("/{campaign_id}/events", response_model=PaginatedResponse[EmailEventResponse])
async def list_campaign_events(
    campaign_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List email events for a campaign with pagination.

    Args:
        campaign_id: The campaign's UUID.
        page: Page number.
        page_size: Items per page.
        event_type: Optional event type filter.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of email events.

    Raises:
        HTTPException 404: If campaign not found.
    """
    campaign = await get_campaign(db, current_user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    events, total = await get_campaign_events(
        db, campaign_id, page=page, page_size=page_size,
        event_type=event_type,
    )
    return PaginatedResponse(
        items=events, total=total, page=page, page_size=page_size
    )
