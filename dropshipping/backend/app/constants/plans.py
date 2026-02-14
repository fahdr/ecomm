"""Subscription plan tier definitions and resource limits.

Centralises all plan-related constants so they can be referenced by
plan enforcement dependencies, the subscription service, and tests.

**For Developers:**
    Import ``PlanTier`` for enum values and ``get_plan_limits()`` for
    the limits associated with a tier. Stripe price IDs are injected
    at startup from ``settings`` — see ``init_price_ids()``.

**For Project Managers:**
    The four tiers (Free / Starter / Growth / Pro) are defined here
    with their pricing and resource caps. Changing a limit is a
    single-line edit in the ``PLAN_LIMITS`` dict.

**For QA Engineers:**
    - A limit of ``-1`` means unlimited.
    - ``trial_days`` only applies to paid plans.
    - ``stripe_price_id`` is empty for the free tier and for local dev
      (mock mode).
"""

import enum
from dataclasses import dataclass


class PlanTier(str, enum.Enum):
    """Available subscription plan tiers.

    Values are stored in the database and used as Stripe metadata.
    """

    free = "free"
    starter = "starter"
    growth = "growth"
    pro = "pro"


@dataclass(frozen=True)
class PlanLimits:
    """Resource limits for a subscription plan.

    Attributes:
        max_stores: Maximum number of stores a user can create (``-1`` = unlimited).
        max_products_per_store: Maximum products per store (``-1`` = unlimited).
        max_orders_per_month: Maximum orders across all stores per calendar month (``-1`` = unlimited).
        price_monthly_cents: Monthly price in US cents (used for display).
        stripe_price_id: Stripe Price object ID. Empty string for free tier / mock mode.
        trial_days: Number of free-trial days for new subscribers.
    """

    max_stores: int
    max_products_per_store: int
    max_orders_per_month: int
    price_monthly_cents: int
    stripe_price_id: str
    trial_days: int


PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.free: PlanLimits(
        max_stores=1,
        max_products_per_store=25,
        max_orders_per_month=50,
        price_monthly_cents=0,
        stripe_price_id="",
        trial_days=0,
    ),
    PlanTier.starter: PlanLimits(
        max_stores=3,
        max_products_per_store=100,
        max_orders_per_month=500,
        price_monthly_cents=2900,
        stripe_price_id="",
        trial_days=14,
    ),
    PlanTier.growth: PlanLimits(
        max_stores=10,
        max_products_per_store=500,
        max_orders_per_month=5000,
        price_monthly_cents=7900,
        stripe_price_id="",
        trial_days=14,
    ),
    PlanTier.pro: PlanLimits(
        max_stores=-1,
        max_products_per_store=-1,
        max_orders_per_month=-1,
        price_monthly_cents=19900,
        stripe_price_id="",
        trial_days=14,
    ),
}

# Display names for each tier (used in API responses and UI).
PLAN_DISPLAY_NAMES: dict[PlanTier, str] = {
    PlanTier.free: "Free",
    PlanTier.starter: "Starter",
    PlanTier.growth: "Growth",
    PlanTier.pro: "Pro",
}


def get_plan_limits(plan: PlanTier) -> PlanLimits:
    """Return the resource limits for a given plan tier.

    Args:
        plan: The plan tier to look up.

    Returns:
        A frozen ``PlanLimits`` dataclass with the tier's limits.
    """
    return PLAN_LIMITS[plan]


def init_price_ids(
    starter_price_id: str,
    growth_price_id: str,
    pro_price_id: str,
) -> None:
    """Inject Stripe Price IDs from application settings.

    Called once at startup to populate the ``stripe_price_id`` fields
    in ``PLAN_LIMITS``. This avoids importing ``settings`` at module
    level (which complicates testing).

    Args:
        starter_price_id: Stripe Price ID for the Starter plan.
        growth_price_id: Stripe Price ID for the Growth plan.
        pro_price_id: Stripe Price ID for the Pro plan.
    """
    global PLAN_LIMITS
    PLAN_LIMITS = {
        PlanTier.free: PLAN_LIMITS[PlanTier.free],
        PlanTier.starter: PlanLimits(
            max_stores=PLAN_LIMITS[PlanTier.starter].max_stores,
            max_products_per_store=PLAN_LIMITS[PlanTier.starter].max_products_per_store,
            max_orders_per_month=PLAN_LIMITS[PlanTier.starter].max_orders_per_month,
            price_monthly_cents=PLAN_LIMITS[PlanTier.starter].price_monthly_cents,
            stripe_price_id=starter_price_id,
            trial_days=PLAN_LIMITS[PlanTier.starter].trial_days,
        ),
        PlanTier.growth: PlanLimits(
            max_stores=PLAN_LIMITS[PlanTier.growth].max_stores,
            max_products_per_store=PLAN_LIMITS[PlanTier.growth].max_products_per_store,
            max_orders_per_month=PLAN_LIMITS[PlanTier.growth].max_orders_per_month,
            price_monthly_cents=PLAN_LIMITS[PlanTier.growth].price_monthly_cents,
            stripe_price_id=growth_price_id,
            trial_days=PLAN_LIMITS[PlanTier.growth].trial_days,
        ),
        PlanTier.pro: PlanLimits(
            max_stores=PLAN_LIMITS[PlanTier.pro].max_stores,
            max_products_per_store=PLAN_LIMITS[PlanTier.pro].max_products_per_store,
            max_orders_per_month=PLAN_LIMITS[PlanTier.pro].max_orders_per_month,
            price_monthly_cents=PLAN_LIMITS[PlanTier.pro].price_monthly_cents,
            stripe_price_id=pro_price_id,
            trial_days=PLAN_LIMITS[PlanTier.pro].trial_days,
        ),
    }


def resolve_plan_from_price_id(price_id: str) -> PlanTier | None:
    """Map a Stripe Price ID back to a ``PlanTier``.

    Args:
        price_id: The Stripe Price ID to look up.

    Returns:
        The matching ``PlanTier``, or ``None`` if not found.
    """
    for tier, limits in PLAN_LIMITS.items():
        if limits.stripe_price_id and limits.stripe_price_id == price_id:
            return tier
    return None
