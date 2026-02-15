"""
FastAPI router for SMS marketing endpoints in FlowSend.

Developer:
    All endpoints are prefixed with /sms and require JWT authentication via
    get_current_user. Campaign endpoints delegate to sms_campaign_service;
    template endpoints perform inline CRUD on the SmsTemplate model.
    Error handling converts ValueError to 404 responses.

Project Manager:
    Exposes the full SMS marketing API: campaign CRUD + send + analytics,
    and template CRUD. This router should be registered on the main FastAPI
    app to activate SMS features.

QA Engineer:
    Test matrix:
    - Auth required on every endpoint (401 without token)
    - POST /sms/campaigns returns 201 with SmsCampaignResponse
    - GET /sms/campaigns supports page/page_size query params
    - GET /sms/campaigns/{id} returns 404 for missing/wrong-user campaigns
    - POST /sms/campaigns/{id}/send transitions status to "sent"
    - Template CRUD: 201 on create, 200 on list/get/update, 204 on delete
    - DELETE /sms/templates/{id} returns empty body

End User:
    Merchants use these endpoints (via the dashboard) to create SMS campaigns,
    manage message templates, trigger sends, and review delivery analytics.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.sms_template import SmsTemplate
from app.models.user import User
from app.schemas.sms import (
    SmsCampaignCreate,
    SmsCampaignResponse,
    SmsEventResponse,
    SmsTemplateCreate,
    SmsTemplateResponse,
    SmsTemplateUpdate,
)
from app.services.sms_campaign_service import (
    create_sms_campaign,
    get_sms_campaign,
    get_sms_campaign_analytics,
    get_sms_campaigns,
    send_sms_campaign_mock,
)

router = APIRouter(prefix="/sms", tags=["sms"])


# ---------------------------------------------------------------------------
# SMS Campaign Endpoints
# ---------------------------------------------------------------------------


@router.post("/campaigns", response_model=SmsCampaignResponse, status_code=201)
async def create_campaign(
    data: SmsCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmsCampaignResponse:
    """Create a new SMS campaign.

    Args:
        data: Campaign creation payload with name, sms_body, optional list_id
            and scheduled_at.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        The newly created SMS campaign.
    """
    campaign = await create_sms_campaign(
        db=db,
        user_id=current_user.id,
        name=data.name,
        sms_body=data.sms_body,
        list_id=data.list_id,
        scheduled_at=data.scheduled_at,
    )
    return campaign


@router.get("/campaigns", response_model=list[SmsCampaignResponse])
async def list_campaigns(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SmsCampaignResponse]:
    """List SMS campaigns for the authenticated user.

    Args:
        page: Page number, starting from 1.
        page_size: Number of campaigns per page (max 100).
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        Paginated list of SMS campaigns ordered by creation date descending.
    """
    campaigns = await get_sms_campaigns(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=SmsCampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmsCampaignResponse:
    """Retrieve a single SMS campaign by ID.

    Args:
        campaign_id: UUID of the campaign to retrieve.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        The requested SMS campaign.

    Raises:
        HTTPException: 404 if campaign not found or not owned by user.
    """
    try:
        campaign = await get_sms_campaign(db, current_user.id, campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="SMS campaign not found")
    return campaign


@router.post("/campaigns/{campaign_id}/send", response_model=SmsCampaignResponse)
async def send_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmsCampaignResponse:
    """Send an SMS campaign (mock delivery in development).

    Dispatches the campaign's SMS body to all subscribed contacts in the
    target list. Updates campaign status to "sent" with delivery counts.

    Args:
        campaign_id: UUID of the campaign to send.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        The updated campaign with sent status and counts.

    Raises:
        HTTPException: 404 if campaign not found.
    """
    try:
        campaign = await get_sms_campaign(db, current_user.id, campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="SMS campaign not found")

    updated = await send_sms_campaign_mock(db, campaign)
    return updated


@router.get("/campaigns/{campaign_id}/analytics")
async def campaign_analytics(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get delivery analytics for an SMS campaign.

    Returns aggregated event counts: total_sent, delivered, failed, plus
    a full breakdown by event_type.

    Args:
        campaign_id: UUID of the campaign to analyze.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        Analytics dictionary with campaign_id, total_sent, delivered,
        failed, and breakdown.

    Raises:
        HTTPException: 404 if campaign not found.
    """
    try:
        analytics = await get_sms_campaign_analytics(db, current_user.id, campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="SMS campaign not found")
    return analytics


# ---------------------------------------------------------------------------
# SMS Template Endpoints
# ---------------------------------------------------------------------------


@router.post("/templates", response_model=SmsTemplateResponse, status_code=201)
async def create_template(
    data: SmsTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmsTemplateResponse:
    """Create a reusable SMS template.

    Args:
        data: Template creation payload with name, body, and optional category.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        The newly created SMS template.
    """
    template = SmsTemplate(
        user_id=current_user.id,
        name=data.name,
        body=data.body,
        category=data.category,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/templates", response_model=list[SmsTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SmsTemplateResponse]:
    """List all SMS templates for the authenticated user.

    Args:
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        List of SMS templates ordered by creation date descending.
    """
    stmt = (
        select(SmsTemplate)
        .where(SmsTemplate.user_id == current_user.id)
        .order_by(SmsTemplate.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/templates/{template_id}", response_model=SmsTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmsTemplateResponse:
    """Retrieve a single SMS template by ID.

    Args:
        template_id: UUID of the template to retrieve.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        The requested SMS template.

    Raises:
        HTTPException: 404 if template not found or not owned by user.
    """
    stmt = select(SmsTemplate).where(
        SmsTemplate.id == template_id,
        SmsTemplate.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="SMS template not found")
    return template


@router.patch("/templates/{template_id}", response_model=SmsTemplateResponse)
async def update_template(
    template_id: UUID,
    data: SmsTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmsTemplateResponse:
    """Partially update an SMS template.

    Only fields provided in the request body are updated; others remain unchanged.

    Args:
        template_id: UUID of the template to update.
        data: Partial update payload with optional name, body, category.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Returns:
        The updated SMS template.

    Raises:
        HTTPException: 404 if template not found or not owned by user.
    """
    stmt = select(SmsTemplate).where(
        SmsTemplate.id == template_id,
        SmsTemplate.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="SMS template not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(
            update(SmsTemplate)
            .where(SmsTemplate.id == template_id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(template)

    return template


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an SMS template.

    Args:
        template_id: UUID of the template to delete.
        db: Injected async database session.
        current_user: Authenticated user from JWT token.

    Raises:
        HTTPException: 404 if template not found or not owned by user.
    """
    stmt = select(SmsTemplate).where(
        SmsTemplate.id == template_id,
        SmsTemplate.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="SMS template not found")

    await db.delete(template)
    await db.commit()
