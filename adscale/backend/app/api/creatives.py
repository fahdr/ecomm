"""
Ad creative management API endpoints.

Handles CRUD operations for ad creatives and provides AI-powered
ad copy generation.

For Developers:
    Creatives belong to ad groups. Ownership is validated through the
    ad_group -> campaign -> user chain. The AI generate-copy endpoint
    uses a mock implementation for development.

For QA Engineers:
    Test: CRUD, AI copy generation (returns valid copy), ownership
    validation through the relationship chain, status transitions.

For Project Managers:
    AI copy generation is a premium feature that differentiates AdScale.
    It uses Claude to generate compelling ad text from product descriptions.

For End Users:
    Create ad creatives manually or let AI generate compelling copy
    for your products. Just provide a product name and description.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.ad_creative import AdCreative
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.ads import (
    CreativeCreate,
    CreativeResponse,
    CreativeUpdate,
    GenerateCopyRequest,
    GenerateCopyResponse,
    PaginatedResponse,
)
from app.services.creative_service import (
    create_creative,
    delete_creative,
    generate_ad_copy,
    get_creative,
    list_creatives,
    update_creative,
)

router = APIRouter(prefix="/creatives", tags=["creatives"])


def _user_ad_group_ids_query(user_id: uuid.UUID):
    """
    Build a subquery for ad group IDs owned by a user.

    Chains through campaign -> user to resolve ownership.

    Args:
        user_id: UUID of the user.

    Returns:
        SQLAlchemy select statement for matching ad group IDs.
    """
    campaign_ids = select(Campaign.id).where(Campaign.user_id == user_id)
    return select(AdGroup.id).where(AdGroup.campaign_id.in_(campaign_ids))


@router.post("", response_model=CreativeResponse, status_code=201)
async def create_creative_endpoint(
    request: CreativeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new ad creative within an ad group.

    Validates ad group ownership through the campaign relationship.

    Args:
        request: Creative creation data (headline, description, URL, CTA).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CreativeResponse with the newly created creative details.

    Raises:
        HTTPException 400: If ad group not found or not owned.
    """
    # Validate ownership
    ag_ids_query = _user_ad_group_ids_query(current_user.id)
    result = await db.execute(
        select(AdGroup).where(
            AdGroup.id == request.ad_group_id,
            AdGroup.id.in_(ag_ids_query),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ad group not found or not owned by this user.",
        )

    try:
        creative = await create_creative(
            db,
            ad_group_id=request.ad_group_id,
            headline=request.headline,
            description=request.description,
            destination_url=request.destination_url,
            image_url=request.image_url,
            call_to_action=request.call_to_action,
            status=request.status.value,
        )
        return creative
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=PaginatedResponse)
async def list_creatives_endpoint(
    ad_group_id: str | None = Query(None, description="Filter by ad group UUID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List ad creatives, optionally filtered by ad group.

    Only returns creatives belonging to the authenticated user.

    Args:
        ad_group_id: Optional UUID string to filter by ad group.
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with creative items.
    """
    ag_ids_query = _user_ad_group_ids_query(current_user.id)

    query = select(AdCreative).where(AdCreative.ad_group_id.in_(ag_ids_query))
    count_query = select(sql_func.count(AdCreative.id)).where(
        AdCreative.ad_group_id.in_(ag_ids_query)
    )

    if ad_group_id:
        try:
            agid = uuid.UUID(ad_group_id)
            query = query.where(AdCreative.ad_group_id == agid)
            count_query = count_query.where(AdCreative.ad_group_id == agid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ad group ID format")

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(AdCreative.created_at.desc()).offset(offset).limit(limit)
    )
    creatives = list(result.scalars().all())

    return PaginatedResponse(
        items=[CreativeResponse.model_validate(c) for c in creatives],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{creative_id}", response_model=CreativeResponse)
async def get_creative_endpoint(
    creative_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific ad creative by ID.

    Args:
        creative_id: UUID of the creative.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CreativeResponse with creative details.

    Raises:
        HTTPException 404: If creative not found or not owned.
    """
    try:
        cid = uuid.UUID(creative_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid creative ID format")

    creative = await get_creative(db, cid)
    if not creative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative not found",
        )

    # Verify ownership
    ag_ids_query = _user_ad_group_ids_query(current_user.id)
    result = await db.execute(
        select(AdCreative).where(
            AdCreative.id == cid,
            AdCreative.ad_group_id.in_(ag_ids_query),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative not found",
        )

    return creative


@router.patch("/{creative_id}", response_model=CreativeResponse)
async def update_creative_endpoint(
    creative_id: str,
    request: CreativeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing ad creative.

    Only provided fields are updated.

    Args:
        creative_id: UUID of the creative to update.
        request: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CreativeResponse with updated creative details.

    Raises:
        HTTPException 404: If creative not found or not owned.
    """
    try:
        cid = uuid.UUID(creative_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid creative ID format")

    # Verify ownership
    ag_ids_query = _user_ad_group_ids_query(current_user.id)
    result = await db.execute(
        select(AdCreative).where(
            AdCreative.id == cid,
            AdCreative.ad_group_id.in_(ag_ids_query),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative not found",
        )

    updates = request.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value

    creative = await update_creative(db, cid, **updates)
    if not creative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative not found",
        )
    return creative


@router.delete("/{creative_id}", status_code=204)
async def delete_creative_endpoint(
    creative_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an ad creative.

    Args:
        creative_id: UUID of the creative to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If creative not found or not owned.
    """
    try:
        cid = uuid.UUID(creative_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid creative ID format")

    # Verify ownership
    ag_ids_query = _user_ad_group_ids_query(current_user.id)
    result = await db.execute(
        select(AdCreative).where(
            AdCreative.id == cid,
            AdCreative.ad_group_id.in_(ag_ids_query),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative not found",
        )

    success = await delete_creative(db, cid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative not found",
        )


@router.post("/generate-copy", response_model=GenerateCopyResponse)
async def generate_copy_endpoint(
    request: GenerateCopyRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate AI ad copy for a product.

    Uses Claude AI (mock in dev) to generate compelling headlines,
    descriptions, and calls-to-action based on product information.

    Args:
        request: Product info for AI generation (name, description, audience, tone).
        current_user: The authenticated user (required for auth).

    Returns:
        GenerateCopyResponse with AI-generated headline, description, and CTA.
    """
    result = generate_ad_copy(
        product_name=request.product_name,
        product_description=request.product_description,
        target_audience=request.target_audience,
        tone=request.tone,
    )
    return GenerateCopyResponse(**result)
