"""
Keyword tracking service for the RankPilot SEO engine.

Handles adding/removing keywords, updating search rankings (mock),
calculating rank changes for trend indicators, and recording rank
history for time-series analysis.

For Developers:
    Rank updates use mock data with random variations. In production,
    this would call a rank-tracking API (e.g., SerpAPI, DataForSEO).
    The ``update_ranks`` function is called by the Celery beat task.
    Each rank update also creates a ``KeywordHistory`` entry for
    the historical rank chart.

    ``check_keyword_rank(keyword, domain)`` simulates a single SERP
    rank check. ``get_rank_history(keyword_id)`` returns historical
    positions for graphing. ``get_rank_change(keyword_id)`` computes
    deltas vs 7 days ago and 30 days ago.

For QA Engineers:
    Test keyword CRUD and plan limit enforcement (max_secondary).
    Verify rank change calculations and that mock data looks realistic.
    Verify that history entries are created on each rank update.

For Project Managers:
    Keyword tracking is the secondary monetization lever. Users
    can track more keywords on higher tiers. Rank history charts
    drive engagement by showing progress over time.

For End Users:
    Monitor where your target keywords rank in search results.
    Track improvements over time with trend indicators and charts.
"""

import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import KeywordTracking
from app.models.keyword_history import KeywordHistory


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
    realistic-looking random rank data with gradual changes. Also records
    a history entry for each keyword.

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
    # Use naive datetime for KeywordTracking.last_checked (DateTime without tz)
    now_naive = datetime.now(UTC).replace(tzinfo=None)
    # Use aware datetime for KeywordHistory.checked_at (DateTime with tz)
    now_aware = datetime.now(UTC)

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

        kw.last_checked = now_naive

        # Record history entry
        history = KeywordHistory(
            keyword_id=kw.id,
            rank_position=kw.current_rank,
            checked_at=now_aware,
        )
        db.add(history)

    await db.flush()
    return keywords


async def check_keyword_rank(keyword: str, domain: str) -> int | None:
    """
    Simulate checking the rank of a keyword for a given domain.

    In production, this would call a SERP API (e.g., SerpAPI, DataForSEO)
    to get the actual search result position. The mock returns a random
    position or None (not ranked).

    Args:
        keyword: The search keyword/phrase to check.
        domain: The domain to find in search results.

    Returns:
        An integer rank position (1-100), or None if not in top 100.
    """
    # Simulate: 85% chance of being ranked, 15% chance of not ranking
    if random.random() < 0.15:
        return None
    return random.randint(1, 100)


async def get_rank_history(
    db: AsyncSession,
    keyword_id: uuid.UUID,
    limit: int = 90,
) -> list[dict]:
    """
    Get historical rank positions for a tracked keyword.

    Returns the most recent history entries, ordered by check time
    (newest first). Each entry contains the rank position and timestamp.

    Args:
        db: Async database session.
        keyword_id: The keyword tracking UUID.
        limit: Maximum number of history entries to return (default 90).

    Returns:
        List of dicts with 'rank_position' and 'checked_at' fields.
    """
    result = await db.execute(
        select(KeywordHistory)
        .where(KeywordHistory.keyword_id == keyword_id)
        .order_by(KeywordHistory.checked_at.desc())
        .limit(limit)
    )
    entries = list(result.scalars().all())

    return [
        {
            "id": str(entry.id),
            "rank_position": entry.rank_position,
            "checked_at": entry.checked_at.isoformat() if entry.checked_at else None,
        }
        for entry in entries
    ]


async def get_rank_change(
    db: AsyncSession,
    keyword_id: uuid.UUID,
) -> dict:
    """
    Calculate rank change for a keyword compared to 7 and 30 days ago.

    Finds the most recent history entry before each time boundary and
    computes the delta (negative = improved, positive = declined).

    Args:
        db: Async database session.
        keyword_id: The keyword tracking UUID.

    Returns:
        Dict with 'current_rank', 'change_7d', 'change_30d' fields.
        Changes are None if no history exists for that period.
    """
    # Get current keyword data
    kw_result = await db.execute(
        select(KeywordTracking).where(KeywordTracking.id == keyword_id)
    )
    kw = kw_result.scalar_one_or_none()
    if not kw:
        return {"current_rank": None, "change_7d": None, "change_30d": None}

    now = datetime.now(UTC)

    # Find rank from ~7 days ago
    seven_days_ago = now - timedelta(days=7)
    result_7d = await db.execute(
        select(KeywordHistory)
        .where(
            KeywordHistory.keyword_id == keyword_id,
            KeywordHistory.checked_at <= seven_days_ago,
        )
        .order_by(KeywordHistory.checked_at.desc())
        .limit(1)
    )
    entry_7d = result_7d.scalar_one_or_none()

    # Find rank from ~30 days ago
    thirty_days_ago = now - timedelta(days=30)
    result_30d = await db.execute(
        select(KeywordHistory)
        .where(
            KeywordHistory.keyword_id == keyword_id,
            KeywordHistory.checked_at <= thirty_days_ago,
        )
        .order_by(KeywordHistory.checked_at.desc())
        .limit(1)
    )
    entry_30d = result_30d.scalar_one_or_none()

    # Calculate changes (negative = improvement, as lower rank is better)
    change_7d = None
    if entry_7d and entry_7d.rank_position is not None and kw.current_rank is not None:
        change_7d = kw.current_rank - entry_7d.rank_position

    change_30d = None
    if entry_30d and entry_30d.rank_position is not None and kw.current_rank is not None:
        change_30d = kw.current_rank - entry_30d.rank_position

    return {
        "current_rank": kw.current_rank,
        "change_7d": change_7d,
        "change_30d": change_30d,
    }
