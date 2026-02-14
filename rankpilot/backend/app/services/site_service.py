"""
Site management service for the RankPilot SEO engine.

Handles all business logic for creating, reading, updating, and deleting
sites, as well as verifying domain ownership.

For Developers:
    All functions accept an async SQLAlchemy session and return model
    instances or raise exceptions. Plan limits for site count should be
    checked at the API layer, not here.

For QA Engineers:
    Test CRUD operations, domain uniqueness per user, and verification flow.
    Verify that the mock verification always succeeds.

For Project Managers:
    Site management is the foundation — all other features depend on having
    at least one site registered.

For End Users:
    Register your domains, verify ownership, and start optimizing.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import Site
from app.models.user import User


async def create_site(
    db: AsyncSession,
    user: User,
    domain: str,
    sitemap_url: str | None = None,
) -> Site:
    """
    Create a new site for the user.

    Args:
        db: Async database session.
        user: The owning user.
        domain: Website domain (e.g. 'example.com').
        sitemap_url: Optional XML sitemap URL.

    Returns:
        The newly created Site.

    Raises:
        ValueError: If the user already has a site with this domain.
    """
    # Check for duplicate domain under same user
    result = await db.execute(
        select(Site).where(Site.user_id == user.id, Site.domain == domain)
    )
    if result.scalar_one_or_none():
        raise ValueError(f"You already have a site registered for '{domain}'")

    site = Site(
        user_id=user.id,
        domain=domain,
        sitemap_url=sitemap_url,
        status="pending",
    )
    db.add(site)
    await db.flush()
    return site


async def get_site(
    db: AsyncSession,
    site_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Site | None:
    """
    Get a single site by ID, scoped to the user.

    Args:
        db: Async database session.
        site_id: The site's UUID.
        user_id: The requesting user's UUID.

    Returns:
        The Site if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_sites(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Site], int]:
    """
    List all sites for a user with pagination.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of Sites, total count).
    """
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(Site).where(Site.user_id == user_id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Site)
        .where(Site.user_id == user_id)
        .order_by(Site.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    sites = list(result.scalars().all())
    return sites, total


async def update_site(
    db: AsyncSession,
    site: Site,
    domain: str | None = None,
    sitemap_url: str | None = ...,  # type: ignore[assignment]
    status: str | None = None,
) -> Site:
    """
    Update a site's fields.

    Uses the sentinel pattern (Ellipsis) for sitemap_url to distinguish
    between 'not provided' and 'set to None'.

    Args:
        db: Async database session.
        site: The Site to update.
        domain: New domain (optional).
        sitemap_url: New sitemap URL (Ellipsis = not provided, None = clear).
        status: New status (optional).

    Returns:
        The updated Site.
    """
    if domain is not None:
        site.domain = domain
    if sitemap_url is not ...:
        site.sitemap_url = sitemap_url
    if status is not None:
        site.status = status

    await db.flush()
    await db.refresh(site)
    return site


async def delete_site(db: AsyncSession, site: Site) -> None:
    """
    Delete a site and all associated data.

    Args:
        db: Async database session.
        site: The Site to delete.
    """
    await db.delete(site)
    await db.flush()


async def verify_site(db: AsyncSession, site: Site) -> Site:
    """
    Verify domain ownership for a site (mock implementation).

    In production, this would check a DNS TXT record, meta tag, or
    uploaded verification file. The mock always succeeds.

    Args:
        db: Async database session.
        site: The Site to verify.

    Returns:
        The verified Site with is_verified=True and status='active'.
    """
    site.is_verified = True
    site.verification_method = "mock_verification"
    site.status = "active"
    await db.flush()
    await db.refresh(site)
    return site


async def count_user_sites(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Count the number of sites owned by a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Number of sites owned by the user.
    """
    result = await db.execute(
        select(func.count()).select_from(Site).where(Site.user_id == user_id)
    )
    return result.scalar() or 0
