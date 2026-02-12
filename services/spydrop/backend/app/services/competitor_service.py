"""
Competitor service — CRUD operations with plan limit enforcement.

Handles creating, reading, updating, and deleting competitor records,
including plan-based limit checks to prevent exceeding tier quotas.

For Developers:
    All functions take an AsyncSession and user_id for scoping. The
    `create_competitor` function checks the user's plan limits before
    allowing creation. Use `list_competitors` with pagination for
    efficient large-result-set handling.

For QA Engineers:
    Test plan limit enforcement by creating competitors up to the tier
    limit and verifying the next creation fails with 403. Test CRUD
    operations for correctness and authorization (users can only access
    their own competitors).

For Project Managers:
    This service enforces the business rules around competitor monitoring
    limits per plan tier (free=3, pro=25, enterprise=unlimited).

For End Users:
    You can add, edit, pause, and remove competitor stores from monitoring.
    The number of competitors you can track depends on your subscription plan.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.competitor import Competitor, CompetitorProduct
from app.models.user import User


async def get_competitor_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Count the number of competitors owned by a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Integer count of the user's competitors.
    """
    result = await db.execute(
        select(func.count(Competitor.id)).where(Competitor.user_id == user_id)
    )
    return result.scalar_one()


async def check_plan_limit(db: AsyncSession, user: User) -> bool:
    """
    Check if the user can create another competitor under their plan limits.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can create another competitor, False if at limit.
    """
    limits = PLAN_LIMITS[user.plan]
    if limits.max_items == -1:
        return True  # Unlimited
    current_count = await get_competitor_count(db, user.id)
    return current_count < limits.max_items


async def create_competitor(
    db: AsyncSession, user: User, name: str, url: str, platform: str = "custom"
) -> Competitor:
    """
    Create a new competitor for the given user.

    Validates the user's plan limits before creating. The competitor
    starts with 'active' status and zero product count.

    Args:
        db: Async database session.
        user: The authenticated user.
        name: Competitor store name.
        url: Competitor store URL.
        platform: E-commerce platform type.

    Returns:
        The newly created Competitor record.

    Raises:
        ValueError: If the user has reached their plan's competitor limit.
    """
    can_create = await check_plan_limit(db, user)
    if not can_create:
        raise ValueError(
            f"Plan limit reached. Your {user.plan.value} plan allows "
            f"{PLAN_LIMITS[user.plan].max_items} competitors."
        )

    competitor = Competitor(
        user_id=user.id,
        name=name,
        url=url,
        platform=platform,
    )
    db.add(competitor)
    await db.flush()
    return competitor


async def list_competitors(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Competitor], int]:
    """
    List competitors for a user with pagination.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Tuple of (list of Competitor records, total count).
    """
    # Count total
    count_result = await db.execute(
        select(func.count(Competitor.id)).where(Competitor.user_id == user_id)
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Competitor)
        .where(Competitor.user_id == user_id)
        .order_by(Competitor.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    competitors = list(result.scalars().all())

    return competitors, total


async def get_competitor(
    db: AsyncSession, user_id: uuid.UUID, competitor_id: uuid.UUID
) -> Competitor | None:
    """
    Get a single competitor by ID, scoped to the user.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        competitor_id: The competitor's UUID.

    Returns:
        The Competitor record if found and owned by the user, None otherwise.
    """
    result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_competitor(
    db: AsyncSession,
    user_id: uuid.UUID,
    competitor_id: uuid.UUID,
    name: str | None = None,
    url: str | None = None,
    platform: str | None = None,
    status: str | None = None,
) -> Competitor | None:
    """
    Update a competitor's fields.

    Only provided (non-None) fields are updated. The competitor must be
    owned by the specified user.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        competitor_id: The competitor's UUID.
        name: Updated name (optional).
        url: Updated URL (optional).
        platform: Updated platform (optional).
        status: Updated status (optional).

    Returns:
        The updated Competitor record, or None if not found.
    """
    competitor = await get_competitor(db, user_id, competitor_id)
    if not competitor:
        return None

    if name is not None:
        competitor.name = name
    if url is not None:
        competitor.url = url
    if platform is not None:
        competitor.platform = platform
    if status is not None:
        competitor.status = status

    await db.flush()
    return competitor


async def delete_competitor(
    db: AsyncSession, user_id: uuid.UUID, competitor_id: uuid.UUID
) -> bool:
    """
    Delete a competitor and all its associated data.

    Cascading deletes will remove products, scan results, alerts, and
    source matches associated with this competitor.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        competitor_id: The competitor's UUID.

    Returns:
        True if the competitor was deleted, False if not found.
    """
    competitor = await get_competitor(db, user_id, competitor_id)
    if not competitor:
        return False

    await db.delete(competitor)
    await db.flush()
    return True


async def list_competitor_products(
    db: AsyncSession,
    user_id: uuid.UUID,
    competitor_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[CompetitorProduct], int]:
    """
    List products for a specific competitor with pagination.

    Verifies the competitor is owned by the user before returning products.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        competitor_id: The competitor's UUID.
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Tuple of (list of CompetitorProduct records, total count).
    """
    # Verify ownership
    competitor = await get_competitor(db, user_id, competitor_id)
    if not competitor:
        return [], 0

    count_result = await db.execute(
        select(func.count(CompetitorProduct.id)).where(
            CompetitorProduct.competitor_id == competitor_id
        )
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(CompetitorProduct)
        .where(CompetitorProduct.competitor_id == competitor_id)
        .order_by(CompetitorProduct.last_seen.desc())
        .offset(offset)
        .limit(per_page)
    )
    products = list(result.scalars().all())

    return products, total


async def list_all_products(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    status_filter: str | None = None,
    sort_by: str = "last_seen",
) -> tuple[list[CompetitorProduct], int]:
    """
    List all products across all of a user's competitors with pagination.

    Supports filtering by product status and sorting by various fields.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-based).
        per_page: Items per page.
        status_filter: Optional status filter ('active', 'removed').
        sort_by: Sort field ('last_seen', 'price', 'first_seen', 'title').

    Returns:
        Tuple of (list of CompetitorProduct records, total count).
    """
    # Get user's competitor IDs
    comp_result = await db.execute(
        select(Competitor.id).where(Competitor.user_id == user_id)
    )
    competitor_ids = [row[0] for row in comp_result.all()]

    if not competitor_ids:
        return [], 0

    # Build base query
    base_filter = CompetitorProduct.competitor_id.in_(competitor_ids)
    if status_filter:
        base_filter = base_filter & (CompetitorProduct.status == status_filter)

    # Count
    count_result = await db.execute(
        select(func.count(CompetitorProduct.id)).where(base_filter)
    )
    total = count_result.scalar_one()

    # Sort
    sort_map = {
        "last_seen": CompetitorProduct.last_seen.desc(),
        "first_seen": CompetitorProduct.first_seen.desc(),
        "price": CompetitorProduct.price.asc(),
        "title": CompetitorProduct.title.asc(),
    }
    order = sort_map.get(sort_by, CompetitorProduct.last_seen.desc())

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(CompetitorProduct)
        .where(base_filter)
        .order_by(order)
        .offset(offset)
        .limit(per_page)
    )
    products = list(result.scalars().all())

    return products, total


async def get_product(
    db: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID
) -> CompetitorProduct | None:
    """
    Get a single product by ID, verifying user ownership via competitor.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        product_id: The product's UUID.

    Returns:
        The CompetitorProduct if found and owned by the user, None otherwise.
    """
    result = await db.execute(
        select(CompetitorProduct)
        .join(Competitor)
        .where(
            CompetitorProduct.id == product_id,
            Competitor.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
