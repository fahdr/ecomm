"""
Ad group management API endpoints.

Handles CRUD operations for ad groups within campaigns, including
targeting configuration and bid strategy management.

For Developers:
    Ad groups are the secondary billable resource (max_secondary plan limit).
    All endpoints require JWT auth and validate ownership through the
    campaign -> user relationship.

For QA Engineers:
    Test: CRUD, plan limit enforcement for ad groups, campaign ownership
    validation, JSON targeting data, bid strategy options.

For Project Managers:
    Ad groups let users segment audiences within campaigns.
    Free tier allows 5 ad groups, Pro allows 100.

For End Users:
    Create ad groups to target different audiences within your campaigns.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.constants.plans import PLAN_LIMITS
from app.database import get_db
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.ads import (
    AdGroupCreate,
    AdGroupResponse,
    AdGroupUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/ad-groups", tags=["ad-groups"])


async def _check_ad_group_limit(db: AsyncSession, user: User) -> None:
    """
    Check whether the user has reached their ad group limit.

    Args:
        db: Async database session.
        user: The authenticated user.

    Raises:
        ValueError: If the user has reached their plan's ad group limit.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_secondary == -1:
        return  # Unlimited

    # Count ad groups across all user's campaigns
    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == user.id)
    count_result = await db.execute(
        select(sql_func.count(AdGroup.id)).where(
            AdGroup.campaign_id.in_(campaign_ids_query)
        )
    )
    current_count = count_result.scalar() or 0

    if current_count >= plan_limits.max_secondary:
        raise ValueError(
            f"Ad group limit reached ({plan_limits.max_secondary} ad groups on "
            f"{user.plan.value} plan). Upgrade to create more."
        )


async def _validate_campaign_ownership(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Campaign:
    """
    Validate that a campaign exists and belongs to the user.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign.
        user_id: UUID of the user.

    Returns:
        The validated Campaign.

    Raises:
        ValueError: If campaign not found or not owned.
    """
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found or not owned by this user.")
    return campaign


@router.post("", response_model=AdGroupResponse, status_code=201)
async def create_ad_group_endpoint(
    request: AdGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new ad group within a campaign.

    Validates campaign ownership and enforces plan ad group limits.

    Args:
        request: Ad group creation data (campaign, name, targeting, bid).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AdGroupResponse with the newly created ad group details.

    Raises:
        HTTPException 403: If plan ad group limit is reached.
        HTTPException 400: If campaign not found or invalid data.
    """
    try:
        await _validate_campaign_ownership(db, request.campaign_id, current_user.id)
        await _check_ad_group_limit(db, current_user)
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

    ad_group = AdGroup(
        campaign_id=request.campaign_id,
        name=request.name,
        targeting=request.targeting,
        bid_strategy=request.bid_strategy,
        bid_amount=request.bid_amount,
        status=request.status,
    )
    db.add(ad_group)
    await db.flush()
    return ad_group


@router.get("", response_model=PaginatedResponse)
async def list_ad_groups_endpoint(
    campaign_id: str | None = Query(None, description="Filter by campaign UUID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List ad groups, optionally filtered by campaign.

    Args:
        campaign_id: Optional UUID string to filter by campaign.
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with ad group items.
    """
    # Build base query scoped to user's campaigns
    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == current_user.id)

    query = select(AdGroup).where(AdGroup.campaign_id.in_(campaign_ids_query))
    count_query = select(sql_func.count(AdGroup.id)).where(
        AdGroup.campaign_id.in_(campaign_ids_query)
    )

    if campaign_id:
        try:
            cid = uuid.UUID(campaign_id)
            query = query.where(AdGroup.campaign_id == cid)
            count_query = count_query.where(AdGroup.campaign_id == cid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(AdGroup.created_at.desc()).offset(offset).limit(limit)
    )
    ad_groups = list(result.scalars().all())

    return PaginatedResponse(
        items=[AdGroupResponse.model_validate(ag) for ag in ad_groups],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{ad_group_id}", response_model=AdGroupResponse)
async def get_ad_group_endpoint(
    ad_group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific ad group by ID.

    Args:
        ad_group_id: UUID of the ad group.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AdGroupResponse with ad group details.

    Raises:
        HTTPException 404: If ad group not found or not owned.
    """
    try:
        agid = uuid.UUID(ad_group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ad group ID format")

    # Verify ownership through campaign
    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == current_user.id)
    result = await db.execute(
        select(AdGroup).where(
            AdGroup.id == agid,
            AdGroup.campaign_id.in_(campaign_ids_query),
        )
    )
    ad_group = result.scalar_one_or_none()
    if not ad_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad group not found",
        )
    return ad_group


@router.patch("/{ad_group_id}", response_model=AdGroupResponse)
async def update_ad_group_endpoint(
    ad_group_id: str,
    request: AdGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing ad group.

    Only provided fields are updated.

    Args:
        ad_group_id: UUID of the ad group to update.
        request: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AdGroupResponse with updated ad group details.

    Raises:
        HTTPException 404: If ad group not found or not owned.
    """
    try:
        agid = uuid.UUID(ad_group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ad group ID format")

    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == current_user.id)
    result = await db.execute(
        select(AdGroup).where(
            AdGroup.id == agid,
            AdGroup.campaign_id.in_(campaign_ids_query),
        )
    )
    ad_group = result.scalar_one_or_none()
    if not ad_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad group not found",
        )

    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if value is not None and hasattr(ad_group, key):
            setattr(ad_group, key, value)

    await db.flush()
    return ad_group


@router.delete("/{ad_group_id}", status_code=204)
async def delete_ad_group_endpoint(
    ad_group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an ad group and all its creatives.

    Args:
        ad_group_id: UUID of the ad group to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If ad group not found or not owned.
    """
    try:
        agid = uuid.UUID(ad_group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ad group ID format")

    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == current_user.id)
    result = await db.execute(
        select(AdGroup).where(
            AdGroup.id == agid,
            AdGroup.campaign_id.in_(campaign_ids_query),
        )
    )
    ad_group = result.scalar_one_or_none()
    if not ad_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad group not found",
        )

    await db.delete(ad_group)
    await db.flush()
