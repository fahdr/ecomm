"""
Campaign management API endpoints.

Handles CRUD operations for advertising campaigns, including
plan limit enforcement and budget management.

For Developers:
    All endpoints require JWT authentication. Campaign creation
    checks plan limits (max_items). The platform field is auto-set
    from the ad account.

For QA Engineers:
    Test: CRUD success paths, plan limit enforcement (403 when at limit),
    ownership validation (can't access other user's campaigns),
    invalid campaign IDs (404), pagination.

For Project Managers:
    Campaigns are the core billable resource. Free tier allows 2,
    Pro allows 25, Enterprise is unlimited.

For End Users:
    Create and manage your advertising campaigns from this section.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ads import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    PaginatedResponse,
)
from app.services.campaign_service import (
    create_campaign,
    delete_campaign,
    get_campaign,
    list_campaigns,
    update_campaign,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign_endpoint(
    request: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new advertising campaign.

    Validates ad account ownership and enforces plan campaign limits.

    Args:
        request: Campaign creation data (name, objective, budget, dates).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CampaignResponse with the newly created campaign details.

    Raises:
        HTTPException 403: If plan campaign limit is reached.
        HTTPException 400: If ad account not found or invalid data.
    """
    try:
        campaign = await create_campaign(
            db,
            user=current_user,
            ad_account_id=request.ad_account_id,
            name=request.name,
            objective=request.objective.value,
            budget_daily=request.budget_daily,
            budget_lifetime=request.budget_lifetime,
            status=request.status.value,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return campaign
    except ValueError as e:
        error_msg = str(e)
        if "limit" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.get("", response_model=PaginatedResponse)
async def list_campaigns_endpoint(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all campaigns for the current user.

    Returns a paginated list of campaigns with status and budget info.

    Args:
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with campaign items.
    """
    campaigns, total = await list_campaigns(db, current_user.id, offset, limit)
    return PaginatedResponse(
        items=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign_endpoint(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific campaign by ID.

    Args:
        campaign_id: UUID of the campaign.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CampaignResponse with campaign details.

    Raises:
        HTTPException 404: If campaign not found or not owned.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    campaign = await get_campaign(db, cid, current_user.id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign_endpoint(
    campaign_id: str,
    request: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing campaign.

    Only provided fields are updated. Null fields are left unchanged.

    Args:
        campaign_id: UUID of the campaign to update.
        request: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CampaignResponse with updated campaign details.

    Raises:
        HTTPException 404: If campaign not found or not owned.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    updates = request.model_dump(exclude_unset=True)
    # Convert enum values to their string representation
    if "objective" in updates and updates["objective"] is not None:
        updates["objective"] = updates["objective"].value
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value

    campaign = await update_campaign(db, cid, current_user.id, **updates)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign_endpoint(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a campaign and all its related resources.

    Cascade deletes ad groups, creatives, and metrics.

    Args:
        campaign_id: UUID of the campaign to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If campaign not found or not owned.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    success = await delete_campaign(db, cid, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
