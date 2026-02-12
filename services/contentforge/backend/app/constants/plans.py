"""
Plan tier definitions and limits for the ContentForge service.

Each service defines its own plan tiers with specific resource limits.
These limits are enforced at the API layer via dependency injection.

For Developers:
    Modify PLAN_LIMITS to change tier limits. The `init_price_ids()` function
    is called at startup to bind Stripe Price IDs from environment config.
    Use `resolve_plan_from_price_id()` in webhook handlers.

For Project Managers:
    Plan limits control what each tier can do. Free tier has restricted
    access, Pro unlocks full features, Enterprise adds API access and
    unlimited usage.

For QA Engineers:
    Test plan enforcement by creating users on different tiers and
    verifying that limits are enforced on resource creation endpoints.
"""

from dataclasses import dataclass

from app.models.user import PlanTier


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


# ContentForge plan limits
# max_items = content generations/month, max_secondary = images/month
PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.free: PlanLimits(
        max_items=10,          # 10 generations/mo
        max_secondary=5,       # 5 images
        price_monthly_cents=0,
        stripe_price_id="",
        trial_days=0,
        api_access=False,
    ),
    PlanTier.pro: PlanLimits(
        max_items=200,         # 200 generations/mo
        max_secondary=100,     # 100 images
        price_monthly_cents=1900,
        stripe_price_id="",
        trial_days=14,
        api_access=True,
    ),
    PlanTier.enterprise: PlanLimits(
        max_items=-1,          # Unlimited generations
        max_secondary=-1,      # Unlimited images
        price_monthly_cents=7900,
        stripe_price_id="",
        trial_days=14,
        api_access=True,
    ),
}


def init_price_ids(pro_price_id: str = "", enterprise_price_id: str = "") -> None:
    """
    Initialize Stripe Price IDs from configuration at startup.

    Called in main.py after loading settings. Mutates PLAN_LIMITS
    to set stripe_price_id for paid tiers.

    Args:
        pro_price_id: Stripe Price ID for Pro tier.
        enterprise_price_id: Stripe Price ID for Enterprise tier.
    """
    global PLAN_LIMITS
    if pro_price_id:
        old = PLAN_LIMITS[PlanTier.pro]
        PLAN_LIMITS[PlanTier.pro] = PlanLimits(
            max_items=old.max_items,
            max_secondary=old.max_secondary,
            price_monthly_cents=old.price_monthly_cents,
            stripe_price_id=pro_price_id,
            trial_days=old.trial_days,
            api_access=old.api_access,
        )
    if enterprise_price_id:
        old = PLAN_LIMITS[PlanTier.enterprise]
        PLAN_LIMITS[PlanTier.enterprise] = PlanLimits(
            max_items=old.max_items,
            max_secondary=old.max_secondary,
            price_monthly_cents=old.price_monthly_cents,
            stripe_price_id=enterprise_price_id,
            trial_days=old.trial_days,
            api_access=old.api_access,
        )


def resolve_plan_from_price_id(price_id: str) -> PlanTier | None:
    """
    Map a Stripe Price ID back to its PlanTier.

    Used in webhook handlers to determine which plan a subscription belongs to.

    Args:
        price_id: The Stripe Price ID to look up.

    Returns:
        The matching PlanTier, or None if not found.
    """
    for tier, limits in PLAN_LIMITS.items():
        if limits.stripe_price_id and limits.stripe_price_id == price_id:
            return tier
    return None
