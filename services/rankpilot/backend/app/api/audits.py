"""
SEO audit API routes.

Provides endpoints for running SEO audits and viewing audit history.
Audits analyze a site against SEO best practices and generate a health
score with categorized issues and actionable recommendations.

For Developers:
    The `POST /run` endpoint creates and runs an audit synchronously (mock).
    In production, this would trigger a Celery task for async processing.
    Audit history is paginated and sorted by most recent first.

For QA Engineers:
    Test audit creation, verify score is 0-100, check that issues have
    severity/category/message fields, and test pagination.

For Project Managers:
    Audits drive user engagement — regular audits show SEO improvements
    over time, encouraging continued platform usage.

For End Users:
    Run SEO audits to get a health score and specific recommendations.
    Track your progress by comparing audit scores over time.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.seo import SeoAuditResponse, SeoAuditRun
from app.services.audit_service import get_audit, list_audits, run_audit
from app.services.site_service import get_site

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("/run", response_model=SeoAuditResponse, status_code=status.HTTP_201_CREATED)
async def run_audit_endpoint(
    body: SeoAuditRun,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run an SEO audit on a site (mock implementation).

    Analyzes the site against SEO best practices and generates a score,
    issues list, and recommendations. The audit is stored in history.

    Args:
        body: SeoAuditRun with site_id.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The SeoAuditResponse with score, issues, and recommendations.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, body.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    audit = await run_audit(db, site)
    return audit


@router.get("", response_model=dict)
async def list_audits_endpoint(
    site_id: uuid.UUID = Query(..., description="Site ID to list audits for"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List SEO audit history for a site with pagination.

    Returns audits sorted by most recent first.

    Args:
        site_id: The site's UUID (required).
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated response with items, total, page, and per_page.

    Raises:
        HTTPException 404: If the site is not found.
    """
    site = await get_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    audits, total = await list_audits(db, site_id, page, per_page)
    return {
        "items": [SeoAuditResponse.model_validate(a) for a in audits],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{audit_id}", response_model=SeoAuditResponse)
async def get_audit_endpoint(
    audit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single SEO audit by ID.

    Args:
        audit_id: The audit's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The SeoAuditResponse.

    Raises:
        HTTPException 404: If the audit is not found.
    """
    audit = await get_audit(db, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    # Verify the user owns the site this audit belongs to
    site = await get_site(db, audit.site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Audit not found")

    return audit
