"""
Keyword tracking service for the RankPilot SEO engine.

Handles adding/removing keywords, updating search rankings (mock),
and calculating rank changes for trend indicators.

For Developers:
    Rank updates use mock data with random variations. In production,
    this would call a rank-tracking API (e.g., SerpAPI, DataForSEO).
    The `update_ranks` function is called by the Celery beat task.

For QA Engineers:
    Test keyword CRUD and plan limit enforcement (max_secondary).
    Verify rank change calculations and that mock data looks realistic.

For Project Managers:
    Keyword tracking is the secondary monetization lever. Users
    can track more keywords on higher tiers.

For End Users:
    Monitor where your target keywords rank in search results.
    Track improvements over time with trend indicators.
"""

import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import KeywordTracking


async def add_keyword(
    db: AsyncSession,
    site_id: uuid.UUID,
    keyword: str,
) -> KeywordTracking:
    """
    Add a keyword to track for a site.

    Checks for duplicate keywords within the same site.

    Args:
        db: Async database session.
        site_id: The parent site's UUID.
        keyword: The search keyword to track.

    Returns:
        The newly created KeywordTracking record.

    Raises:
        ValueError: If this keyword is already being tracked for this site.
    """
    # Check for duplicate
    result = await db.execute(
        select(KeywordTracking).where(
            KeywordTracking.site_id == site_id,
            KeywordTracking.keyword == keyword,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError(f"Keyword '{keyword}' is already being tracked for this site")

    tracking = KeywordTracking(
        site_id=site_id,
        keyword=keyword,
    )
    db.add(tracking)
    await db.flush()
    return tracking


async def list_keywords(
    db: AsyncSession,
    site_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[KeywordTracking], int]:
    """
    List tracked keywords for a site with pagination.

    Args:
        db: Async database session.
        site_id: The site's UUID.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of KeywordTrackings, total count).
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(KeywordTracking)
        .where(KeywordTracking.site_id == site_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(KeywordTracking)
        .where(KeywordTracking.site_id == site_id)
        .order_by(KeywordTracking.tracked_since.desc())
        .offset(offset)
        .limit(per_page)
    )
    keywords = list(result.scalars().all())
    return keywords, total


async def get_keyword(
    db: AsyncSession,
    keyword_id: uuid.UUID,
    site_id: uuid.UUID,
) -> KeywordTracking | None:
    """
    Get a single tracked keyword by ID.

    Args:
        db: Async database session.
        keyword_id: The keyword tracking UUID.
        site_id: The parent site's UUID for authorization.

    Returns:
        The KeywordTracking if found, None otherwise.
    """
    result = await db.execute(
        select(KeywordTracking).where(
            KeywordTracking.id == keyword_id,
            KeywordTracking.site_id == site_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_keyword(
    db: AsyncSession,
    tracking: KeywordTracking,
) -> None:
    """
    Remove a keyword from tracking.

    Args:
        db: Async database session.
        tracking: The KeywordTracking to delete.
    """
    await db.delete(tracking)
    await db.flush()


async def count_site_keywords(
    db: AsyncSession,
    site_id: uuid.UUID,
) -> int:
    """
    Count the number of keywords tracked for a site.

    Args:
        db: Async database session.
        site_id: The site's UUID.

    Returns:
        Number of keywords tracked for the site.
    """
    result = await db.execute(
        select(func.count())
        .select_from(KeywordTracking)
        .where(KeywordTracking.site_id == site_id)
    )
    return result.scalar() or 0


async def count_user_keywords(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """
    Count total keywords tracked across all of a user's sites.

    Used for plan limit enforcement (max_secondary = total keywords).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Total keyword count across all user's sites.
    """
    from app.models.site import Site

    result = await db.execute(
        select(func.count())
        .select_from(KeywordTracking)
        .join(Site, KeywordTracking.site_id == Site.id)
        .where(Site.user_id == user_id)
    )
    return result.scalar() or 0


async def update_keyword_ranks_for_site(
    db: AsyncSession,
    site_id: uuid.UUID,
) -> list[KeywordTracking]:
    """
    Update search rankings for all keywords in a site (mock implementation).

    In production, this would call a rank-tracking API. The mock generates
    realistic-looking random rank data with gradual changes.

    Args:
        db: Async database session.
        site_id: The site's UUID.

    Returns:
        List of updated KeywordTracking records.
    """
    result = await db.execute(
        select(KeywordTracking).where(KeywordTracking.site_id == site_id)
    )
    keywords = list(result.scalars().all())
    now = datetime.now(UTC)

    for kw in keywords:
        # Save previous rank
        kw.previous_rank = kw.current_rank

        if kw.current_rank is None:
            # New keyword — assign initial rank (simulate first check)
            kw.current_rank = random.randint(5, 80)
        else:
            # Simulate rank change: small random movement
            change = random.randint(-5, 5)
            new_rank = max(1, kw.current_rank + change)
            kw.current_rank = min(new_rank, 100)

        # Set/update search volume and difficulty if not set
        if kw.search_volume is None:
            kw.search_volume = random.randint(100, 50000)
        if kw.difficulty is None:
            kw.difficulty = round(random.uniform(10.0, 90.0), 1)

        kw.last_checked = now

    await db.flush()
    return keywords
