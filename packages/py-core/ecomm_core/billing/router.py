"""
Billing API router factory.

Creates a FastAPI router with standard billing endpoints: plans, checkout,
portal, current subscription, and billing overview.

For Developers:
    Use `create_billing_router(get_db, get_current_user, plan_limits)`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.billing.service import (
    create_portal_session,
    create_subscription_checkout,
    get_billing_overview,
    get_subscription,
)
from ecomm_core.models.user import PlanTier, User
from ecomm_core.plans import PlanLimits
from ecomm_core.schemas.billing import (
    BillingOverviewResponse,
    CheckoutSessionResponse,
    CreateCheckoutRequest,
    PlanInfo,
    PortalSessionResponse,
    SubscriptionResponse,
    UsageMetric,
    UsageResponse,
)


def create_billing_router(
    get_db,
    get_current_user,
    plan_limits: dict[PlanTier, PlanLimits],
) -> APIRouter:
    """
    Factory to create the billing router bound to service dependencies.

    Args:
        get_db: FastAPI dependency for database session.
        get_current_user: FastAPI dependency for JWT auth.
        plan_limits: Service-specific plan limits.

    Returns:
        Configured APIRouter with all billing endpoints.
    """
    router = APIRouter(prefix="/billing", tags=["billing"])

    @router.get("/plans", response_model=list[PlanInfo])
    async def list_plans():
        """List all available subscription plans (public, no auth)."""
        plans = []
        for tier, limits in plan_limits.items():
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
        """Create a Stripe Checkout session for subscribing to a plan."""
        from app.config import settings

        try:
            result = await create_subscription_checkout(
                db, current_user, request.plan, plan_limits,
                stripe_secret_key=settings.stripe_secret_key,
                success_url=settings.stripe_billing_success_url,
                cancel_url=settings.stripe_billing_cancel_url,
                service_name=settings.service_name,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        return CheckoutSessionResponse(**result)

    @router.post("/portal", response_model=PortalSessionResponse)
    async def create_portal(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Create a Stripe Customer Portal session."""
        from app.config import settings

        try:
            result = await create_portal_session(
                db, current_user,
                stripe_secret_key=settings.stripe_secret_key,
                success_url=settings.stripe_billing_success_url,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        return PortalSessionResponse(**result)

    @router.get("/current", response_model=SubscriptionResponse | None)
    async def get_current_subscription(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Get the user's current subscription details."""
        return await get_subscription(db, current_user.id)

    @router.get("/overview", response_model=BillingOverviewResponse)
    async def billing_overview(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Get complete billing overview including plan, subscription, and usage."""
        overview = await get_billing_overview(db, current_user, plan_limits)

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

    return router
