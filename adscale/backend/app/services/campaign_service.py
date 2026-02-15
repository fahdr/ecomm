"""
Campaign management service.

Handles CRUD operations for advertising campaigns, including plan limit
enforcement, budget management, and status transitions.

For Developers:
    Campaigns are the primary billable resource. The `create_campaign`
    function checks plan limits before allowing creation. Campaign
    platform is automatically set from the ad account.

For QA Engineers:
    Test CRUD, plan limit enforcement (free: 2, pro: 25, enterprise: unlimited),
    ownership validation, and the relationship between campaigns and ad accounts.

For Project Managers:
    This service manages the core entity — campaigns. Plan limits ensure
    users on free tier can only run 2 campaigns simultaneously.

For End Users:
    Create and manage your advertising campaigns through the dashboard.
"""

import uuid

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.ad_account import AdAccount
from app.models.campaign import Campaign, CampaignStatus
from app.models.user import PlanTier, User


async def check_campaign_limit(db: AsyncSession, user: User) -> None:
    """
    Check whether the user has reached their campaign limit.

    Enforces the `max_items` plan limit. Counts all non-completed campaigns.

    Args:
        db: Async database session.
        user: The authenticated user.

    Raises:
        ValueError: If the user has reached their plan's campaign limit.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items == -1:
        return  # Unlimited

    count_result = await db.execute(
        select(sql_func.count(Campaign.id)).where(
            Campaign.user_id == user.id,
            Campaign.status != CampaignStatus.completed,
        )
    )
    current_count = count_result.scalar() or 0

    if current_count >= plan_limits.max_items:
        raise ValueError(
            f"Campaign limit reached ({plan_limits.max_items} campaigns on "
            f"{user.plan.value} plan). Upgrade to create more."
        )


async def create_campaign(
    db: AsyncSession,
    user: User,
    ad_account_id: uuid.UUID,
    name: str,
    objective: str,
    budget_daily: float | None = None,
    budget_lifetime: float | None = None,
    status: str = "draft",
    start_date=None,
    end_date=None,
) -> Campaign:
    """
    Create a new advertising campaign.

    Validates the ad account belongs to the user and enforces plan limits.
    The platform field is automatically populated from the ad account.

    Args:
        db: Async database session.
        user: The authenticated user.
        ad_account_id: UUID of the ad account to run the campaign on.
        name: Campaign name.
        objective: Campaign objective (traffic, conversions, awareness, sales).
        budget_daily: Daily budget in USD (optional).
        budget_lifetime: Lifetime budget in USD (optional).
        status: Initial campaign status (default: draft).
        start_date: Campaign start date (optional).
        end_date: Campaign end date (optional).

    Returns:
        The newly created Campaign.

    Raises:
        ValueError: If plan limit reached or ad account not found/not owned.
    """
    # Check plan limit
    await check_campaign_limit(db, user)

    # Validate ad account ownership
    result = await db.execute(
        select(AdAccount).where(
            AdAccount.id == ad_account_id,
            AdAccount.user_id == user.id,
        )
    )
    ad_account = result.scalar_one_or_none()
    if not ad_account:
        raise ValueError("Ad account not found or not owned by this user.")

    campaign = Campaign(
        user_id=user.id,
        ad_account_id=ad_account_id,
        name=name,
        platform=ad_account.platform.value,
        objective=objective,
        budget_daily=budget_daily,
        budget_lifetime=budget_lifetime,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(campaign)
    await db.flush()
    return campaign


async def list_campaigns(
    db: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Campaign], int]:
    """
    List all campaigns for a user with pagination.

    Args:
        db: Async database session.
        user_id: UUID of the user.
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50).

    Returns:
        Tuple of (list of Campaigns, total count).
    """
    count_result = await db.execute(
        select(sql_func.count(Campaign.id)).where(Campaign.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Campaign)
        .where(Campaign.user_id == user_id)
        .order_by(Campaign.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    campaigns = list(result.scalars().all())

    return campaigns, total


async def get_campaign(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Campaign | None:
    """
    Get a specific campaign by ID, scoped to the user.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign.
        user_id: UUID of the owning user.

    Returns:
        The Campaign if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_campaign(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
    **updates,
) -> Campaign | None:
    """
    Update an existing campaign.

    Only provided (non-None) fields are updated.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign to update.
        user_id: UUID of the owning user.
        **updates: Keyword arguments with field names and new values.

    Returns:
        The updated Campaign, or None if not found.
    """
    campaign = await get_campaign(db, campaign_id, user_id)
    if not campaign:
        return None

    for key, value in updates.items():
        if value is not None and hasattr(campaign, key):
            setattr(campaign, key, value)

    await db.flush()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a campaign and all its related resources.

    Cascade delete removes ad groups, creatives, and metrics.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign to delete.
        user_id: UUID of the owning user.

    Returns:
        True if the campaign was found and deleted, False if not found.
    """
    campaign = await get_campaign(db, campaign_id, user_id)
    if not campaign:
        return False

    await db.delete(campaign)
    await db.flush()
    return True


async def count_campaigns(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Count total campaigns for a user (non-completed).

    Args:
        db: Async database session.
        user_id: UUID of the user.

    Returns:
        Number of active (non-completed) campaigns.
    """
    result = await db.execute(
        select(sql_func.count(Campaign.id)).where(
            Campaign.user_id == user_id,
            Campaign.status != CampaignStatus.completed,
        )
    )
    return result.scalar() or 0
