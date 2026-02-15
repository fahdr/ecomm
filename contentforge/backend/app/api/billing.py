"""
Billing API endpoints for subscription management.

Handles plan listing, checkout session creation, portal access,
current subscription retrieval, and billing overview.

For Developers:
    Plans are served from constants/plans.py. Checkout creates a Stripe
    session (or mock). Portal redirects to Stripe's customer portal.

For QA Engineers:
    Test: plans listing (public), checkout (auth required, mock mode),
    portal access, billing overview with usage metrics.

For End Users:
    View plans at /billing/plans, subscribe via /billing/checkout,
    manage your subscription at /billing/portal.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.constants.plans import PLAN_LIMITS
from app.database import get_db
from app.models.user import PlanTier, User
from app.schemas.billing import (
    BillingOverviewResponse,
    CheckoutSessionResponse,
    CreateCheckoutRequest,
    PlanInfo,
    PortalSessionResponse,
    SubscriptionResponse,
    UsageMetric,
    UsageResponse,
)
from app.services.billing_service import (
    create_portal_session,
    create_subscription_checkout,
    get_billing_overview,
    get_subscription,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans():
    """
    List all available subscription plans.

    Public endpoint — no authentication required.

    Returns:
        List of PlanInfo with tier details and pricing.
    """
    plans = []
    for tier, limits in PLAN_LIMITS.items():
        plans.append(
            PlanInfo(
                tier=tier,
                name=tier.value.title(),
                price_monthly_cents=limits.price_monthly_cents,
                max_items=limits.max_items,
                max_secondary=limits.max_secondary,
                trial_days=limits.trial_days,
                api_access=limits.api_access,
            )
        )
    return plans


@router.post("/checkout", response_model=CheckoutSessionResponse, status_code=201)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout session for subscribing to a plan.

    Redirects the user to Stripe's hosted checkout page.

    Args:
        request: The plan tier to subscribe to.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CheckoutSessionResponse with checkout URL and session ID.

    Raises:
        HTTPException 400: If plan is free or user already subscribed.
    """
    try:
        result = await create_subscription_checkout(db, current_user, request.plan)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CheckoutSessionResponse(**result)


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Customer Portal session.

    Allows users to manage their subscription, update payment method,
    or cancel their plan.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PortalSessionResponse with portal URL.

    Raises:
        HTTPException 400: If user has no Stripe customer.
    """
    try:
        result = await create_portal_session(db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PortalSessionResponse(**result)


@router.get("/current", response_model=SubscriptionResponse | None)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the user's current subscription details.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SubscriptionResponse if subscribed, null otherwise.
    """
    return await get_subscription(db, current_user.id)


@router.get("/overview", response_model=BillingOverviewResponse)
async def billing_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete billing overview including plan, subscription, and usage.

    Powers the billing dashboard page with all billing-related information.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        BillingOverviewResponse with plan, subscription, and usage data.
    """
    overview = await get_billing_overview(db, current_user)

    # Convert usage dict to schema
    usage_data = overview["usage"]
    usage = UsageResponse(
        plan=usage_data["plan"],
        period_start=usage_data["period_start"],
        period_end=usage_data["period_end"],
        metrics=[UsageMetric(**m) for m in usage_data["metrics"]],
    )

    sub = overview["subscription"]
    return BillingOverviewResponse(
        current_plan=overview["current_plan"],
        plan_name=overview["plan_name"],
        subscription=SubscriptionResponse.model_validate(sub) if sub else None,
        usage=usage,
    )
