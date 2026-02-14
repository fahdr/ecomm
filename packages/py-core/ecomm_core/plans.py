"""
Plan tier definitions and limits for ecomm SaaS services.

Provides the PlanLimits dataclass and helper functions for managing
subscription tiers across all services.

For Developers:
    Each service defines its own PLAN_LIMITS dict with service-specific
    resource limits. Use `create_default_plan_limits()` as a starting point.

For QA Engineers:
    Test plan enforcement by creating users on different tiers and
    verifying that limits are enforced on resource creation endpoints.
"""

from dataclasses import dataclass

from ecomm_core.models.user import PlanTier


@dataclass(frozen=True)
class PlanLimits:
    """
    Resource limits for a subscription plan tier.

    Attributes:
        max_items: Maximum primary resource items (-1 = unlimited).
        max_secondary: Maximum secondary resource items (-1 = unlimited).
        price_monthly_cents: Monthly price in USD cents.
        stripe_price_id: Stripe Price ID (set at runtime via init_price_ids).
        trial_days: Number of free trial days.
        api_access: Whether API key access is enabled.
    """

    max_items: int
    max_secondary: int
    price_monthly_cents: int
    stripe_price_id: str
    trial_days: int
    api_access: bool


def create_default_plan_limits(
    free_items: int = 10,
    free_secondary: int = 25,
    pro_items: int = 100,
    pro_secondary: int = 500,
    pro_price_cents: int = 2900,
    enterprise_price_cents: int = 9900,
) -> dict[PlanTier, PlanLimits]:
    """
    Create default plan limits with customizable values.

    Args:
        free_items: Free tier primary item limit.
        free_secondary: Free tier secondary item limit.
        pro_items: Pro tier primary item limit.
        pro_secondary: Pro tier secondary item limit.
        pro_price_cents: Pro tier monthly price in cents.
        enterprise_price_cents: Enterprise tier monthly price in cents.

    Returns:
        Dict mapping PlanTier to PlanLimits.
    """
    return {
        PlanTier.free: PlanLimits(
            max_items=free_items,
            max_secondary=free_secondary,
            price_monthly_cents=0,
            stripe_price_id="",
            trial_days=0,
            api_access=False,
        ),
        PlanTier.pro: PlanLimits(
            max_items=pro_items,
            max_secondary=pro_secondary,
            price_monthly_cents=pro_price_cents,
            stripe_price_id="",
            trial_days=14,
            api_access=True,
        ),
        PlanTier.enterprise: PlanLimits(
            max_items=-1,
            max_secondary=-1,
            price_monthly_cents=enterprise_price_cents,
            stripe_price_id="",
            trial_days=14,
            api_access=True,
        ),
    }


def init_price_ids(
    plan_limits: dict[PlanTier, PlanLimits],
    pro_price_id: str = "",
    enterprise_price_id: str = "",
) -> dict[PlanTier, PlanLimits]:
    """
    Initialize Stripe Price IDs on plan limits.

    Creates new PlanLimits instances with the given price IDs set.

    Args:
        plan_limits: The current plan limits dict.
        pro_price_id: Stripe Price ID for Pro tier.
        enterprise_price_id: Stripe Price ID for Enterprise tier.

    Returns:
        Updated plan limits dict with price IDs set.
    """
    result = dict(plan_limits)
    if pro_price_id:
        old = result[PlanTier.pro]
        result[PlanTier.pro] = PlanLimits(
            max_items=old.max_items,
            max_secondary=old.max_secondary,
            price_monthly_cents=old.price_monthly_cents,
            stripe_price_id=pro_price_id,
            trial_days=old.trial_days,
            api_access=old.api_access,
        )
    if enterprise_price_id:
        old = result[PlanTier.enterprise]
        result[PlanTier.enterprise] = PlanLimits(
            max_items=old.max_items,
            max_secondary=old.max_secondary,
            price_monthly_cents=old.price_monthly_cents,
            stripe_price_id=enterprise_price_id,
            trial_days=old.trial_days,
            api_access=old.api_access,
        )
    return result


def resolve_plan_from_price_id(
    plan_limits: dict[PlanTier, PlanLimits], price_id: str
) -> PlanTier | None:
    """
    Map a Stripe Price ID back to its PlanTier.

    Args:
        plan_limits: The plan limits dict to search.
        price_id: The Stripe Price ID to look up.

    Returns:
        The matching PlanTier, or None if not found.
    """
    for tier, limits in plan_limits.items():
        if limits.stripe_price_id and limits.stripe_price_id == price_id:
            return tier
    return None
