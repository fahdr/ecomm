"""
Plan tier definitions and limits for the FlowSend service.

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


# FlowSend plan limits
# max_items = emails/month, max_secondary = contacts
PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.free: PlanLimits(
        max_items=500,         # 500 emails/mo
        max_secondary=250,     # 250 contacts
        price_monthly_cents=0,
        stripe_price_id="",
        trial_days=0,
        api_access=False,
    ),
    PlanTier.pro: PlanLimits(
        max_items=25000,       # 25,000 emails/mo
        max_secondary=10000,   # 10,000 contacts
        price_monthly_cents=3900,
        stripe_price_id="",
        trial_days=14,
        api_access=True,
    ),
    PlanTier.enterprise: PlanLimits(
        max_items=-1,          # Unlimited emails
        max_secondary=-1,      # Unlimited contacts
        price_monthly_cents=14900,
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
