"""
Site management API routes.

Provides CRUD endpoints for managing sites (domains) that the user
wants to optimize for SEO, including domain verification.

For Developers:
    All endpoints require JWT authentication via the `get_current_user` dep.
    Sites are scoped to the authenticated user. Plan limits for site count
    are not enforced here (only on the frontend) to keep it simple.

For QA Engineers:
    Test all CRUD operations, 404 for non-existent sites, 403 for other
    users' sites, and the verification endpoint.

For Project Managers:
    Sites are the top-level resource. Users must create a site before
    they can add blog posts, keywords, audits, or schema configs.

For End Users:
    Register your website domain, verify ownership, and start optimizing.
    Access via: GET/POST /api/v1/sites, GET/PATCH/DELETE /api/v1/sites/{id}
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.seo import SiteCreate, SiteResponse, SiteUpdate
from app.services.site_service import (
    count_user_sites,
    create_site,
    delete_site,
    get_site,
    list_sites,
    update_site,
    verify_site,
)

router = APIRouter(prefix="/sites", tags=["sites"])


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site_endpoint(
    body: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new site (domain) for SEO tracking.

    The site is created in 'pending' status. Verify ownership to activate it.

    Args:
        body: SiteCreate with domain and optional sitemap_url.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created SiteResponse.

    Raises:
        HTTPException 400: If the user already has a site with this domain.
    """
    try:
        site = await create_site(
            db, current_user, body.domain, body.sitemap_url
        )
        return site
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=dict)
async def list_sites_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all sites for the authenticated user with pagination.

    Args:
        page: Page number (1-indexed).
        per_page: Number of items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated response with items, total, page, and per_page.
    """
    sites, total = await list_sites(db, current_user.id, page, per_page)
    return {
        "items": [SiteResponse.model_validate(s) for s in sites],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site_endpoint(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single site by ID.

    Args:
        site_id: The site's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The SiteResponse.

    Raises:
        HTTPException 404: If the site is not found or not owned by user.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site_endpoint(
    site_id: uuid.UUID,
    body: SiteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a site's fields.

    Only the fields provided in the request body will be updated.

    Args:
        site_id: The site's UUID.
        body: SiteUpdate with optional fields to change.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated SiteResponse.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    updated = await update_site(
        db,
        site,
        domain=body.domain,
        sitemap_url=body.sitemap_url if body.sitemap_url is not None else ...,
        status=body.status,
    )
    return updated


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site_endpoint(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a site and all associated data (blog posts, keywords, audits, schema).

    Args:
        site_id: The site's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    await delete_site(db, site)


@router.post("/{site_id}/verify", response_model=SiteResponse)
async def verify_site_endpoint(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify domain ownership for a site (mock — always succeeds).

    In production, this would verify via DNS TXT record, meta tag,
    or uploaded file. The mock implementation always succeeds.

    Args:
        site_id: The site's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The verified SiteResponse with is_verified=True.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    verified = await verify_site(db, site)
    return verified
