"""
Competitor management API endpoints.

CRUD operations for competitor stores that the user wants to monitor.
Includes plan limit enforcement and product listing per competitor.

For Developers:
    All endpoints require authentication via JWT Bearer token.
    Plan limits are checked on creation. Products are listed via a
    sub-resource pattern: GET /competitors/{id}/products.

For QA Engineers:
    Test CRUD operations, plan limit enforcement (create beyond limit
    should return 403), pagination, and authorization (users can only
    access their own competitors).

For Project Managers:
    Competitors are the primary resource in SpyDrop. Users add competitor
    stores, then scan them for products and price changes.

For End Users:
    Use these endpoints to manage the competitor stores you want to monitor.
    Add competitors, view their products, update settings, or remove them.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorListResponse,
    CompetitorProductListResponse,
    CompetitorProductResponse,
    CompetitorResponse,
    CompetitorUpdate,
)
from app.services.competitor_service import (
    create_competitor,
    delete_competitor,
    get_competitor,
    list_competitor_products,
    list_competitors,
    update_competitor,
)

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.post("/", response_model=CompetitorResponse, status_code=201)
async def create_competitor_endpoint(
    request: CompetitorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new competitor to monitor.

    Validates the user's plan limits before creating. The competitor
    starts with 'active' status and zero product count.

    Args:
        request: Competitor creation data (name, url, platform).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorResponse with the newly created competitor.

    Raises:
        HTTPException 403: If the user has reached their plan's competitor limit.
    """
    try:
        competitor = await create_competitor(
            db,
            current_user,
            name=request.name,
            url=request.url,
            platform=request.platform,
        )
        return competitor
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get("/", response_model=CompetitorListResponse)
async def list_competitors_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all competitors for the authenticated user.

    Returns a paginated list of competitors ordered by creation date
    (most recent first).

    Args:
        page: Page number (1-based).
        per_page: Number of items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorListResponse with paginated competitors.
    """
    competitors, total = await list_competitors(
        db, current_user.id, page=page, per_page=per_page
    )
    return CompetitorListResponse(
        items=competitors, total=total, page=page, per_page=per_page
    )


@router.get("/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor_endpoint(
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single competitor by ID.

    Args:
        competitor_id: The competitor's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorResponse with competitor details.

    Raises:
        HTTPException 404: If the competitor is not found or not owned by user.
    """
    import uuid

    try:
        cid = uuid.UUID(competitor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid competitor ID")

    competitor = await get_competitor(db, current_user.id, cid)
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    return competitor


@router.patch("/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor_endpoint(
    competitor_id: str,
    request: CompetitorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a competitor's settings.

    Only provided fields are updated. The competitor must be owned
    by the authenticated user.

    Args:
        competitor_id: The competitor's UUID.
        request: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorResponse with updated competitor.

    Raises:
        HTTPException 404: If the competitor is not found.
    """
    import uuid

    try:
        cid = uuid.UUID(competitor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid competitor ID")

    competitor = await update_competitor(
        db,
        current_user.id,
        cid,
        name=request.name,
        url=request.url,
        platform=request.platform,
        status=request.status,
    )
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )
    return competitor


@router.delete("/{competitor_id}", status_code=204)
async def delete_competitor_endpoint(
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a competitor and all associated data.

    Cascading deletes will remove products, scan results, alerts,
    and source matches.

    Args:
        competitor_id: The competitor's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the competitor is not found.
    """
    import uuid

    try:
        cid = uuid.UUID(competitor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid competitor ID")

    deleted = await delete_competitor(db, current_user.id, cid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found",
        )


@router.get(
    "/{competitor_id}/products",
    response_model=CompetitorProductListResponse,
)
async def list_competitor_products_endpoint(
    competitor_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List products for a specific competitor.

    Returns a paginated list of products ordered by last seen date
    (most recent first).

    Args:
        competitor_id: The competitor's UUID.
        page: Page number (1-based).
        per_page: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorProductListResponse with paginated products.
    """
    import uuid

    try:
        cid = uuid.UUID(competitor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid competitor ID")

    products, total = await list_competitor_products(
        db, current_user.id, cid, page=page, per_page=per_page
    )

    # Enrich with competitor name
    competitor = await get_competitor(db, current_user.id, cid)
    items = []
    for p in products:
        resp = CompetitorProductResponse.model_validate(p)
        resp.competitor_name = competitor.name if competitor else None
        items.append(resp)

    return CompetitorProductListResponse(
        items=items, total=total, page=page, per_page=per_page
    )
