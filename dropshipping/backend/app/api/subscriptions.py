"""Subscription API router.

Provides endpoints for managing platform subscriptions (SaaS billing).
Includes plan listing (public), checkout session creation, Customer
Portal, and billing overview.

**For Developers:**
    Mounted at ``/api/v1/subscriptions``. Uses ``subscription_service``
    for all business logic. The ``/plans`` endpoint is unauthenticated
    (used by the pricing page). All other endpoints require a valid JWT.

**For QA Engineers:**
    - ``GET /plans`` returns all 4 tiers (free/starter/growth/pro).
    - ``POST /checkout`` rejects free-tier requests (400) and users who
      already have an active subscription (400).
    - ``POST /portal`` returns 400 if the user has no Stripe customer.
    - ``GET /billing`` returns usage stats and subscription details.

**For End Users:**
    View available plans, subscribe, manage your billing, and check
    your current usage from these endpoints (or via the Dashboard UI).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.constants.plans import PLAN_DISPLAY_NAMES, PLAN_LIMITS, PlanTier
from app.database import get_db
from app.models.user import User
from app.schemas.subscription import (
    BillingOverviewResponse,
    CheckoutSessionResponse,
    CreateCheckoutRequest,
    PlanInfo,
    PortalSessionResponse,
    SubscriptionResponse,
    UsageResponse,
)
from app.services import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans() -> list[PlanInfo]:
    """List all available subscription plans with limits and pricing.

    No authentication required. Used by the pricing page.

    Returns:
        A list of ``PlanInfo`` objects, one per tier.
    """
    plans = []
    for tier, limits in PLAN_LIMITS.items():
        plans.append(
            PlanInfo(
                tier=tier,
                name=PLAN_DISPLAY_NAMES.get(tier, tier.value.title()),
                price_monthly_cents=limits.price_monthly_cents,
                max_stores=limits.max_stores,
                max_products_per_store=limits.max_products_per_store,
                max_orders_per_month=limits.max_orders_per_month,
                trial_days=limits.trial_days,
            )
        )
    return plans


@router.post(
    "/checkout",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session for subscribing to a plan.

    Redirects the user to Stripe's hosted checkout page. On successful
    payment, Stripe fires a webhook that provisions the subscription.

    Args:
        request: The plan to subscribe to.
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        ``CheckoutSessionResponse`` with the checkout URL and session ID.

    Raises:
        HTTPException: 400 if the plan is free or the user already
            has an active subscription.
    """
    try:
        result = await subscription_service.create_subscription_checkout(
            db, current_user, request.plan
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return CheckoutSessionResponse(**result)


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalSessionResponse:
    """Create a Stripe Customer Portal session for managing subscription.

    Redirects the user to Stripe's hosted portal where they can change
    plans, update payment methods, or cancel.

    Args:
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        ``PortalSessionResponse`` with the portal URL.

    Raises:
        HTTPException: 400 if the user has no billing account.
    """
    try:
        result = await subscription_service.create_portal_session(db, current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return PortalSessionResponse(**result)


@router.get("/current", response_model=SubscriptionResponse | None)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse | None:
    """Get the current user's active subscription, or null if on free plan.

    Args:
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        ``SubscriptionResponse`` if a subscription exists, otherwise ``null``.
    """
    sub = await subscription_service.get_subscription(db, current_user.id)
    if sub is None:
        return None
    return SubscriptionResponse.model_validate(sub)


@router.get("/billing", response_model=BillingOverviewResponse)
async def get_billing_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingOverviewResponse:
    """Get billing overview with current plan, usage stats, and subscription.

    Args:
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        ``BillingOverviewResponse`` combining plan, subscription, and usage.
    """
    overview = await subscription_service.get_billing_overview(db, current_user)

    sub_response = None
    if overview["subscription"]:
        sub_response = SubscriptionResponse.model_validate(overview["subscription"])

    return BillingOverviewResponse(
        current_plan=overview["current_plan"],
        plan_name=overview["plan_name"],
        subscription=sub_response,
        usage=UsageResponse(**overview["usage"]),
    )
