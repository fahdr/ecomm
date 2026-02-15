"""
Optimization rule management and execution service.

Handles CRUD operations for optimization rules and evaluates rules
against campaign metrics to execute automated actions.

For Developers:
    Rules are evaluated by comparing campaign metrics against the
    rule threshold. The `evaluate_and_execute` function processes
    all active rules for a user and returns execution results.
    Actions are mocked — in production, these would call ad platform APIs.

For QA Engineers:
    Test rule CRUD, threshold evaluation logic, execution counting,
    and the execute-now functionality. Verify rules only trigger
    when their conditions are met.

For Project Managers:
    Optimization rules automate tedious campaign management tasks
    like pausing underperforming campaigns or scaling winners.

For End Users:
    Set up rules to automatically manage your campaigns. For example,
    pause campaigns with ROAS below 1.0 or increase budget for
    campaigns with ROAS above 3.0.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_metrics import CampaignMetrics
from app.models.optimization_rule import OptimizationRule, RuleType


async def create_rule(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    rule_type: RuleType,
    conditions: dict,
    threshold: float,
    is_active: bool = True,
) -> OptimizationRule:
    """
    Create a new optimization rule.

    Args:
        db: Async database session.
        user_id: UUID of the owning user.
        name: Human-readable rule name.
        rule_type: Type of optimization action.
        conditions: JSON dict with evaluation conditions.
        threshold: Numeric threshold value.
        is_active: Whether the rule starts enabled (default True).

    Returns:
        The newly created OptimizationRule.
    """
    rule = OptimizationRule(
        user_id=user_id,
        name=name,
        rule_type=rule_type,
        conditions=conditions,
        threshold=threshold,
        is_active=is_active,
    )
    db.add(rule)
    await db.flush()
    return rule


async def list_rules(
    db: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[OptimizationRule], int]:
    """
    List all optimization rules for a user with pagination.

    Args:
        db: Async database session.
        user_id: UUID of the user.
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50).

    Returns:
        Tuple of (list of OptimizationRules, total count).
    """
    count_result = await db.execute(
        select(sql_func.count(OptimizationRule.id)).where(
            OptimizationRule.user_id == user_id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(OptimizationRule)
        .where(OptimizationRule.user_id == user_id)
        .order_by(OptimizationRule.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rules = list(result.scalars().all())

    return rules, total


async def get_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    user_id: uuid.UUID,
) -> OptimizationRule | None:
    """
    Get a specific optimization rule by ID, scoped to the user.

    Args:
        db: Async database session.
        rule_id: UUID of the rule.
        user_id: UUID of the owning user.

    Returns:
        The OptimizationRule if found, None otherwise.
    """
    result = await db.execute(
        select(OptimizationRule).where(
            OptimizationRule.id == rule_id,
            OptimizationRule.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    user_id: uuid.UUID,
    **updates,
) -> OptimizationRule | None:
    """
    Update an existing optimization rule.

    Only provided (non-None) fields are updated.

    Args:
        db: Async database session.
        rule_id: UUID of the rule to update.
        user_id: UUID of the owning user.
        **updates: Keyword arguments with field names and new values.

    Returns:
        The updated OptimizationRule, or None if not found.
    """
    rule = await get_rule(db, rule_id, user_id)
    if not rule:
        return None

    for key, value in updates.items():
        if value is not None and hasattr(rule, key):
            setattr(rule, key, value)

    await db.flush()
    return rule


async def delete_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete an optimization rule.

    Args:
        db: Async database session.
        rule_id: UUID of the rule to delete.
        user_id: UUID of the owning user.

    Returns:
        True if the rule was found and deleted, False if not found.
    """
    rule = await get_rule(db, rule_id, user_id)
    if not rule:
        return False

    await db.delete(rule)
    await db.flush()
    return True


async def evaluate_and_execute(
    db: AsyncSession,
    rule_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    """
    Evaluate an optimization rule and execute its action if threshold is met.

    Checks all active campaigns for the user, evaluates each campaign's
    recent metrics against the rule threshold, and takes the appropriate
    action (mock implementation).

    Args:
        db: Async database session.
        rule_id: UUID of the rule to evaluate.
        user_id: UUID of the owning user.

    Returns:
        Dict with 'rule_id', 'campaigns_affected', and 'actions_taken'.

    Raises:
        ValueError: If the rule is not found or not owned by the user.
    """
    rule = await get_rule(db, rule_id, user_id)
    if not rule:
        raise ValueError("Rule not found.")

    # Get active campaigns
    result = await db.execute(
        select(Campaign).where(
            Campaign.user_id == user_id,
            Campaign.status == CampaignStatus.active,
        )
    )
    campaigns = list(result.scalars().all())

    campaigns_affected = 0
    actions_taken = []

    for campaign in campaigns:
        # Get most recent metrics for this campaign
        metrics_result = await db.execute(
            select(CampaignMetrics)
            .where(CampaignMetrics.campaign_id == campaign.id)
            .order_by(CampaignMetrics.date.desc())
            .limit(7)
        )
        recent_metrics = list(metrics_result.scalars().all())

        if not recent_metrics:
            continue

        # Calculate average ROAS for recent metrics
        total_spend = sum(m.spend for m in recent_metrics)
        total_revenue = sum(m.revenue for m in recent_metrics)
        avg_roas = (total_revenue / total_spend) if total_spend > 0 else 0.0

        # Evaluate based on rule type
        should_act = False
        action_description = ""

        if rule.rule_type == RuleType.pause_low_roas:
            if avg_roas < rule.threshold:
                should_act = True
                campaign.status = CampaignStatus.paused
                action_description = (
                    f"Paused campaign '{campaign.name}' — "
                    f"ROAS {avg_roas:.2f} below threshold {rule.threshold}"
                )

        elif rule.rule_type == RuleType.scale_high_roas:
            if avg_roas > rule.threshold and campaign.budget_daily:
                should_act = True
                old_budget = campaign.budget_daily
                campaign.budget_daily = round(old_budget * 1.2, 2)
                action_description = (
                    f"Scaled campaign '{campaign.name}' budget "
                    f"${old_budget:.2f} -> ${campaign.budget_daily:.2f} — "
                    f"ROAS {avg_roas:.2f} above threshold {rule.threshold}"
                )

        elif rule.rule_type == RuleType.adjust_bid:
            if avg_roas < rule.threshold:
                should_act = True
                action_description = (
                    f"Adjusted bids for campaign '{campaign.name}' — "
                    f"ROAS {avg_roas:.2f} below target {rule.threshold}"
                )

        elif rule.rule_type == RuleType.increase_budget:
            if avg_roas > rule.threshold and campaign.budget_daily:
                should_act = True
                old_budget = campaign.budget_daily
                campaign.budget_daily = round(old_budget * 1.15, 2)
                action_description = (
                    f"Increased budget for campaign '{campaign.name}' "
                    f"${old_budget:.2f} -> ${campaign.budget_daily:.2f} — "
                    f"ROAS {avg_roas:.2f} exceeds threshold {rule.threshold}"
                )

        if should_act:
            campaigns_affected += 1
            actions_taken.append(action_description)

    # Update rule execution tracking
    rule.last_executed = datetime.now(UTC)
    rule.executions_count += 1
    await db.flush()

    return {
        "rule_id": rule.id,
        "campaigns_affected": campaigns_affected,
        "actions_taken": actions_taken,
    }
