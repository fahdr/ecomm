"""
Keyword tracking API routes.

Provides endpoints for adding, listing, and removing tracked keywords.
Keyword count is subject to plan limits (max_secondary = total keywords).

For Developers:
    Keywords are scoped to a site. Plan limit enforcement uses the
    total keyword count across all of the user's sites, not per-site.

For QA Engineers:
    Test add/list/delete, duplicate keyword rejection, plan limit
    enforcement, and pagination.

For Project Managers:
    Keyword tracking is the secondary usage metric. Users tracking
    many keywords are encouraged to upgrade to higher tiers.

For End Users:
    Track your target keywords and monitor their search rankings.
    Upgrade your plan to track more keywords.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.constants.plans import PLAN_LIMITS
from app.database import get_db
from app.models.user import User
from app.schemas.seo import KeywordTrackingCreate, KeywordTrackingResponse
from app.services.keyword_service import (
    add_keyword,
    count_user_keywords,
    delete_keyword,
    get_keyword,
    list_keywords,
    update_keyword_ranks_for_site,
)
from app.services.site_service import get_site

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.post("", response_model=KeywordTrackingResponse, status_code=status.HTTP_201_CREATED)
async def add_keyword_endpoint(
    body: KeywordTrackingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a keyword to track for a site.

    Checks plan limits (max_secondary) before adding. Rejects duplicates
    within the same site.

    Args:
        body: KeywordTrackingCreate with site_id and keyword.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created KeywordTrackingResponse.

    Raises:
        HTTPException 404: If the referenced site is not found.
        HTTPException 403: If the keyword limit is reached.
        HTTPException 400: If the keyword is already tracked for this site.
    """
    # Verify site ownership
    site = await get_site(db, body.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check plan limit
    plan_limits = PLAN_LIMITS[current_user.plan]
    if plan_limits.max_secondary != -1:
        total_keywords = await count_user_keywords(db, current_user.id)
        if total_keywords >= plan_limits.max_secondary:
            raise HTTPException(
                status_code=403,
                detail=f"Keyword tracking limit reached ({plan_limits.max_secondary}). "
                f"Upgrade your plan to track more keywords.",
            )

    try:
        tracking = await add_keyword(db, body.site_id, body.keyword)
        return tracking
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=dict)
async def list_keywords_endpoint(
    site_id: uuid.UUID = Query(..., description="Site ID to list keywords for"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List tracked keywords for a site with pagination.

    Args:
        site_id: The site's UUID (required).
        page: Page number (1-indexed).
        per_page: Items per page (max 200).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated response with items, total, page, and per_page.

    Raises:
        HTTPException 404: If the site is not found.
    """
    # Verify site ownership
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    keywords, total = await list_keywords(db, site_id, page, per_page)
    return {
        "items": [KeywordTrackingResponse.model_validate(k) for k in keywords],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword_endpoint(
    keyword_id: uuid.UUID,
    site_id: uuid.UUID = Query(..., description="Parent site ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a keyword from tracking.

    Args:
        keyword_id: The keyword tracking UUID.
        site_id: Parent site UUID for authorization.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the site or keyword is not found.
    """
    # Verify site ownership
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    tracking = await get_keyword(db, keyword_id, site_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await delete_keyword(db, tracking)


@router.post("/refresh", response_model=dict)
async def refresh_keyword_ranks_endpoint(
    site_id: uuid.UUID = Query(..., description="Site ID to refresh ranks for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh keyword rankings for a site (mock implementation).

    Triggers a rank update for all tracked keywords. In production,
    this would call external rank-checking APIs.

    Args:
        site_id: The site's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with updated keyword count.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    updated = await update_keyword_ranks_for_site(db, site_id)
    return {"updated": len(updated), "message": "Keyword ranks refreshed"}
