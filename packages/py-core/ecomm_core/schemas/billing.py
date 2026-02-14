"""
Billing and subscription schemas.

Defines data structures for plan information, subscription management,
usage tracking, and Stripe checkout/portal integration.

For Developers:
    PlanInfo is returned from the public /plans endpoint.
    UsageResponse shows current resource consumption per metric.
    BillingOverviewResponse aggregates plan + subscription + usage.

For QA Engineers:
    Verify that usage metrics correctly reflect resource counts.
    Test that plan limits match the values in constants/plans.py.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from ecomm_core.models.subscription import SubscriptionStatus
from ecomm_core.models.user import PlanTier


class PlanInfo(BaseModel):
    """
    Public plan tier information.

    Attributes:
        tier: Plan tier identifier.
        name: Human-readable plan name.
        price_monthly_cents: Monthly price in USD cents.
        max_items: Maximum primary resource limit (-1 = unlimited).
        max_secondary: Maximum secondary resource limit (-1 = unlimited).
        trial_days: Free trial duration in days.
        api_access: Whether API key access is enabled.
    """

    tier: PlanTier
    name: str
    price_monthly_cents: int
    max_items: int
    max_secondary: int
    trial_days: int
    api_access: bool


class CreateCheckoutRequest(BaseModel):
    """
    Request to create a Stripe Checkout session for subscription.

    Attributes:
        plan: The plan tier to subscribe to.
    """

    plan: PlanTier


class CheckoutSessionResponse(BaseModel):
    """
    Stripe Checkout session URL response.

    Attributes:
        checkout_url: URL to redirect the user to for payment.
        session_id: Stripe session identifier.
    """

    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    """
    Stripe Customer Portal session URL response.

    Attributes:
        portal_url: URL to redirect the user to for billing management.
    """

    portal_url: str


class SubscriptionResponse(BaseModel):
    """
    Subscription details response.

    Attributes:
        id: Subscription record ID.
        user_id: Owning user ID.
        stripe_subscription_id: Stripe subscription identifier.
        plan: Subscribed plan tier.
        status: Current subscription status.
        current_period_start: Billing period start.
        current_period_end: Billing period end.
        cancel_at_period_end: Whether cancellation is pending.
        trial_start: Trial start date (if applicable).
        trial_end: Trial end date (if applicable).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

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

    model_config = {"from_attributes": True}


class UsageMetric(BaseModel):
    """
    Single usage metric with current value and limit.

    Attributes:
        name: Metric identifier (e.g., 'research_runs').
        label: Human-readable label (e.g., 'Research Runs').
        used: Current usage count.
        limit: Maximum allowed (-1 = unlimited).
    """

    name: str
    label: str
    used: int
    limit: int


class UsageResponse(BaseModel):
    """
    Usage reporting response for the current billing period.

    Attributes:
        plan: Current plan tier.
        period_start: Billing period start date.
        period_end: Billing period end date.
        metrics: List of usage metrics with current values and limits.
    """

    plan: PlanTier
    period_start: date
    period_end: date
    metrics: list[UsageMetric]


class BillingOverviewResponse(BaseModel):
    """
    Complete billing overview for the dashboard.

    Attributes:
        current_plan: Current plan tier identifier.
        plan_name: Human-readable plan name.
        subscription: Active subscription details (if any).
        usage: Current usage metrics.
    """

    current_plan: PlanTier
    plan_name: str
    subscription: SubscriptionResponse | None
    usage: UsageResponse
