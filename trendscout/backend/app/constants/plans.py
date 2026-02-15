"""
TrendScout plan tier definitions and limits.

Uses shared PlanLimits from ecomm_core with service-specific values.

For Developers:
    Modify PLAN_LIMITS to change tier limits for TrendScout.
    max_items = research runs/month, max_secondary = watchlist items.

For QA Engineers:
    Test plan enforcement by creating users on different tiers.
"""

from ecomm_core.models.user import PlanTier
from ecomm_core.plans import PlanLimits, init_price_ids, resolve_plan_from_price_id

# TrendScout plan limits
PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.free: PlanLimits(
        max_items=5,
        max_secondary=25,
        price_monthly_cents=0,
        stripe_price_id="",
        trial_days=0,
        api_access=False,
    ),
    PlanTier.pro: PlanLimits(
        max_items=50,
        max_secondary=500,
        price_monthly_cents=2900,
        stripe_price_id="",
        trial_days=14,
        api_access=True,
    ),
    PlanTier.enterprise: PlanLimits(
        max_items=-1,
        max_secondary=-1,
        price_monthly_cents=9900,
        stripe_price_id="",
        trial_days=14,
        api_access=True,
    ),
}

__all__ = ["PLAN_LIMITS", "PlanLimits", "init_price_ids", "resolve_plan_from_price_id"]
