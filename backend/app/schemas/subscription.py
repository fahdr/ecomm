"""Pydantic schemas for subscription and billing endpoints.

**For Developers:**
    ``PlanInfo`` is used for the public pricing page. ``SubscriptionResponse``
    serialises the ORM model (``from_attributes = True``). ``BillingOverviewResponse``
    combines plan, subscription, and usage into a single response.

**For QA Engineers:**
    - ``CreateCheckoutRequest.plan`` must be a paid tier (starter/growth/pro).
    - ``UsageResponse`` limits of ``-1`` mean unlimited.
    - ``BillingOverviewResponse.subscription`` is ``null`` for free-tier users.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.constants.plans import PlanTier
from app.models.subscription import SubscriptionStatus


class PlanInfo(BaseModel):
    """Public plan information for the pricing page.

    Attributes:
        tier: Plan tier identifier.
        name: Human-readable plan name.
        price_monthly_cents: Monthly price in US cents.
        max_stores: Store limit (``-1`` = unlimited).
        max_products_per_store: Product-per-store limit (``-1`` = unlimited).
        max_orders_per_month: Monthly order limit (``-1`` = unlimited).
        trial_days: Number of free-trial days.
    """

    tier: PlanTier
    name: str
    price_monthly_cents: int
    max_stores: int
    max_products_per_store: int
    max_orders_per_month: int
    trial_days: int


class CreateCheckoutRequest(BaseModel):
    """Request to create a subscription checkout session.

    Attributes:
        plan: The plan tier to subscribe to (must be a paid tier).
    """

    plan: PlanTier = Field(..., description="Plan tier to subscribe to")


class CheckoutSessionResponse(BaseModel):
    """Response containing the Stripe Checkout session URL.

    Attributes:
        checkout_url: URL to redirect the user to for payment.
        session_id: Stripe Checkout Session ID.
    """

    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    """Response containing the Stripe Customer Portal URL.

    Attributes:
        portal_url: URL to redirect the user to for subscription management.
    """

    portal_url: str


class SubscriptionResponse(BaseModel):
    """Full subscription details for the billing page.

    Attributes:
        id: Subscription record ID.
        user_id: Owning user ID.
        stripe_subscription_id: Stripe Subscription object ID.
        plan: The plan tier granted by this subscription.
        status: Current Stripe subscription status.
        current_period_start: Start of the current billing period.
        current_period_end: End of the current billing period.
        cancel_at_period_end: Whether cancellation is pending.
        trial_start: Start of trial period (if any).
        trial_end: End of trial period (if any).
        created_at: Record creation timestamp.
        updated_at: Record last-update timestamp.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    stripe_subscription_id: str
    plan: PlanTier
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    trial_start: datetime | None
    trial_end: datetime | None
    created_at: datetime
    updated_at: datetime


class UsageResponse(BaseModel):
    """Current resource usage against plan limits.

    Attributes:
        stores_used: Number of non-deleted stores the user owns.
        stores_limit: Maximum stores allowed (``-1`` = unlimited).
        products_used: Total products across all stores.
        products_limit_per_store: Maximum products per store (``-1`` = unlimited).
        orders_this_month: Total orders this calendar month across all stores.
        orders_limit: Maximum monthly orders (``-1`` = unlimited).
    """

    stores_used: int
    stores_limit: int
    products_used: int
    products_limit_per_store: int
    orders_this_month: int
    orders_limit: int


class BillingOverviewResponse(BaseModel):
    """Billing page overview combining plan, subscription, and usage.

    Attributes:
        current_plan: The user's current plan tier.
        plan_name: Human-readable plan name.
        subscription: Active subscription details, or ``null`` for free tier.
        usage: Current resource usage against plan limits.
    """

    current_plan: PlanTier
    plan_name: str
    subscription: SubscriptionResponse | None
    usage: UsageResponse
