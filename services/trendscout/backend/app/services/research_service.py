"""
Core research service for TrendScout.

Handles CRUD operations for research runs, results, watchlist items,
and source configurations. Enforces plan-based resource limits.

For Developers:
    All functions accept an AsyncSession and operate within the caller's
    transaction. Use `await db.flush()` after mutations to get IDs without
    committing. The `check_run_limit` function counts runs in the current
    billing period and compares against the plan's max_items.

    Watchlist operations enforce the max_secondary plan limit.

For Project Managers:
    This service is the central business logic layer. It sits between
    the API routes and the database models, enforcing plan limits and
    business rules.

For QA Engineers:
    Test plan limit enforcement by creating runs/watchlist items up to
    the limit and verifying the next attempt is rejected with 403.
    Test pagination with varying page/per_page values.
    Test cascading deletes when runs or watchlist items are removed.

For End Users:
    The research service powers all product research functionality:
    starting runs, viewing results, managing your watchlist, and
    configuring data sources.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.research import ResearchResult, ResearchRun
from app.models.source_config import SourceConfig
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.utils.helpers import get_current_billing_period


# ─── Research Runs ───────────────────────────────────────────────────

async def check_run_limit(db: AsyncSession, user: User) -> bool:
    """
    Check whether the user has remaining research runs in the current period.

    Counts runs created by this user within the current billing month
    and compares against the plan's max_items limit.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can create another run, False if limit reached.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items == -1:
        return True  # Unlimited

    period_start, period_end = get_current_billing_period()
    result = await db.execute(
        select(func.count(ResearchRun.id)).where(
            ResearchRun.user_id == user.id,
            ResearchRun.created_at >= datetime.combine(period_start, datetime.min.time()),
            ResearchRun.created_at < datetime.combine(period_end, datetime.min.time()),
        )
    )
    count = result.scalar_one()
    return count < plan_limits.max_items


async def get_run_count_this_period(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Get the number of research runs created by the user this billing period.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Count of runs in the current billing period.
    """
    period_start, period_end = get_current_billing_period()
    result = await db.execute(
        select(func.count(ResearchRun.id)).where(
            ResearchRun.user_id == user_id,
            ResearchRun.created_at >= datetime.combine(period_start, datetime.min.time()),
            ResearchRun.created_at < datetime.combine(period_end, datetime.min.time()),
        )
    )
    return result.scalar_one()


async def create_research_run(
    db: AsyncSession,
    user: User,
    keywords: list[str],
    sources: list[str],
    score_config: dict | None = None,
) -> ResearchRun:
    """
    Create a new research run and prepare it for background execution.

    Validates plan limits before creation. The actual data fetching and
    scoring happens in the Celery task dispatched by the API route.

    Args:
        db: Async database session.
        user: The authenticated user creating the run.
        keywords: List of search keywords to research.
        sources: List of data source identifiers to scan.
        score_config: Optional custom scoring weight overrides.

    Returns:
        The newly created ResearchRun in 'pending' status.

    Raises:
        ValueError: If the user has exceeded their plan's run limit.
    """
    can_run = await check_run_limit(db, user)
    if not can_run:
        raise ValueError(
            f"Research run limit reached for {user.plan.value} plan. "
            f"Upgrade your plan for more runs."
        )

    # Validate sources
    valid_sources = {"aliexpress", "tiktok", "google_trends", "reddit"}
    sanitized_sources = [s for s in sources if s in valid_sources]
    if not sanitized_sources:
        sanitized_sources = ["aliexpress", "google_trends"]

    run = ResearchRun(
        user_id=user.id,
        keywords=[k.strip() for k in keywords if k.strip()],
        sources=sanitized_sources,
        score_config=score_config,
        status="pending",
    )
    db.add(run)
    await db.flush()
    return run


async def get_research_runs(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ResearchRun], int]:
    """
    Get a paginated list of research runs for a user.

    Ordered by creation date (newest first). Does not load results —
    use `get_research_run` for full details.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of ResearchRun, total count).
    """
    # Count total
    count_result = await db.execute(
        select(func.count(ResearchRun.id)).where(
            ResearchRun.user_id == user_id
        )
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ResearchRun)
        .where(ResearchRun.user_id == user_id)
        .order_by(ResearchRun.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    runs = list(result.scalars().all())
    return runs, total


async def get_research_run(
    db: AsyncSession,
    run_id: uuid.UUID,
) -> ResearchRun | None:
    """
    Get a single research run with its results eagerly loaded.

    Args:
        db: Async database session.
        run_id: The run's UUID.

    Returns:
        The ResearchRun if found, None otherwise.
    """
    result = await db.execute(
        select(ResearchRun).where(ResearchRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def get_result(
    db: AsyncSession,
    result_id: uuid.UUID,
) -> ResearchResult | None:
    """
    Get a single research result by ID.

    Args:
        db: Async database session.
        result_id: The result's UUID.

    Returns:
        The ResearchResult if found, None otherwise.
    """
    result = await db.execute(
        select(ResearchResult).where(ResearchResult.id == result_id)
    )
    return result.scalar_one_or_none()


async def delete_research_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a research run and all its results.

    Only the owning user can delete their runs. Results are cascade-deleted
    by the database foreign key constraint.

    Args:
        db: Async database session.
        run_id: The run's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned by user.
    """
    result = await db.execute(
        select(ResearchRun).where(
            ResearchRun.id == run_id,
            ResearchRun.user_id == user_id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        return False

    await db.delete(run)
    await db.flush()
    return True


# ─── Watchlist ───────────────────────────────────────────────────────

async def check_watchlist_limit(db: AsyncSession, user: User) -> bool:
    """
    Check whether the user has remaining watchlist capacity.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can add another item, False if limit reached.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_secondary == -1:
        return True  # Unlimited

    result = await db.execute(
        select(func.count(WatchlistItem.id)).where(
            WatchlistItem.user_id == user.id
        )
    )
    count = result.scalar_one()
    return count < plan_limits.max_secondary


async def get_watchlist_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Get the total number of watchlist items for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Total count of watchlist items.
    """
    result = await db.execute(
        select(func.count(WatchlistItem.id)).where(
            WatchlistItem.user_id == user_id
        )
    )
    return result.scalar_one()


async def add_to_watchlist(
    db: AsyncSession,
    user: User,
    result_id: uuid.UUID,
    notes: str | None = None,
) -> WatchlistItem:
    """
    Add a research result to the user's watchlist.

    Checks plan limits and prevents duplicate entries for the same result.

    Args:
        db: Async database session.
        user: The authenticated user.
        result_id: UUID of the ResearchResult to save.
        notes: Optional notes.

    Returns:
        The newly created WatchlistItem.

    Raises:
        ValueError: If plan limit reached or result already in watchlist.
    """
    # Check plan limit
    can_add = await check_watchlist_limit(db, user)
    if not can_add:
        raise ValueError(
            f"Watchlist limit reached for {user.plan.value} plan. "
            f"Upgrade your plan for more watchlist items."
        )

    # Check for duplicate
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.result_id == result_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("This result is already in your watchlist")

    # Verify result exists
    res = await db.execute(
        select(ResearchResult).where(ResearchResult.id == result_id)
    )
    if not res.scalar_one_or_none():
        raise ValueError("Research result not found")

    item = WatchlistItem(
        user_id=user.id,
        result_id=result_id,
        notes=notes,
        status="watching",
    )
    db.add(item)
    await db.flush()

    # Re-fetch with relationships loaded
    refreshed = await db.execute(
        select(WatchlistItem).where(WatchlistItem.id == item.id)
    )
    return refreshed.scalar_one()


async def get_watchlist_items(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[WatchlistItem], int]:
    """
    Get a paginated list of watchlist items for a user.

    Optionally filter by status (watching, imported, dismissed).

    Args:
        db: Async database session.
        user_id: The user's UUID.
        status: Optional status filter.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of WatchlistItem, total count).
    """
    # Build base query
    base_filter = [WatchlistItem.user_id == user_id]
    if status:
        base_filter.append(WatchlistItem.status == status)

    # Count total
    count_result = await db.execute(
        select(func.count(WatchlistItem.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(WatchlistItem)
        .where(*base_filter)
        .order_by(WatchlistItem.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = list(result.scalars().all())
    return items, total


async def update_watchlist_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str | None = None,
    notes: str | None = ...,
) -> WatchlistItem | None:
    """
    Update a watchlist item's status and/or notes.

    Uses the Ellipsis sentinel pattern: passing notes=... means "not provided"
    (leave unchanged), while notes=None explicitly clears the notes field.

    Args:
        db: Async database session.
        item_id: The watchlist item's UUID.
        user_id: The requesting user's UUID (for ownership check).
        status: New status value (optional).
        notes: New notes value (Ellipsis = unchanged, None = clear).

    Returns:
        The updated WatchlistItem, or None if not found/not owned.
    """
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return None

    valid_statuses = {"watching", "imported", "dismissed"}
    if status and status in valid_statuses:
        item.status = status
    if notes is not ...:
        item.notes = notes

    await db.flush()
    return item


async def delete_watchlist_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Remove an item from the user's watchlist.

    Args:
        db: Async database session.
        item_id: The watchlist item's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False

    await db.delete(item)
    await db.flush()
    return True


# ─── Source Configs ──────────────────────────────────────────────────

async def create_source_config(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_type: str,
    credentials: dict,
    settings: dict,
) -> SourceConfig:
    """
    Create a new source configuration for the user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        source_type: External source identifier.
        credentials: Source-specific authentication credentials.
        settings: Source-specific settings.

    Returns:
        The newly created SourceConfig.
    """
    config = SourceConfig(
        user_id=user_id,
        source_type=source_type,
        credentials=credentials,
        settings=settings,
    )
    db.add(config)
    await db.flush()
    return config


async def get_source_configs(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[SourceConfig]:
    """
    Get all source configurations for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of all SourceConfig records for the user.
    """
    result = await db.execute(
        select(SourceConfig)
        .where(SourceConfig.user_id == user_id)
        .order_by(SourceConfig.source_type)
    )
    return list(result.scalars().all())


async def update_source_config(
    db: AsyncSession,
    config_id: uuid.UUID,
    user_id: uuid.UUID,
    credentials: dict | None = None,
    settings: dict | None = None,
    is_active: bool | None = None,
) -> SourceConfig | None:
    """
    Update an existing source configuration.

    Args:
        db: Async database session.
        config_id: The config's UUID.
        user_id: The requesting user's UUID (for ownership check).
        credentials: Updated credentials (optional).
        settings: Updated settings (optional).
        is_active: Toggle active state (optional).

    Returns:
        The updated SourceConfig, or None if not found/not owned.
    """
    result = await db.execute(
        select(SourceConfig).where(
            SourceConfig.id == config_id,
            SourceConfig.user_id == user_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return None

    if credentials is not None:
        config.credentials = credentials
    if settings is not None:
        config.settings = settings
    if is_active is not None:
        config.is_active = is_active

    await db.flush()
    return config


async def delete_source_config(
    db: AsyncSession,
    config_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a source configuration.

    Args:
        db: Async database session.
        config_id: The config's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    result = await db.execute(
        select(SourceConfig).where(
            SourceConfig.id == config_id,
            SourceConfig.user_id == user_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return False

    await db.delete(config)
    await db.flush()
    return True
