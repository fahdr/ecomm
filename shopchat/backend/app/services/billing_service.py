"""
Billing service for Stripe subscription management.

Handles Stripe customer creation, checkout sessions, portal sessions,
and webhook event processing. Supports mock mode for local development.

For Developers:
    Mock mode is active when STRIPE_SECRET_KEY is empty. In mock mode,
    subscription records are created directly without Stripe API calls.
    Real mode uses the Stripe Python SDK.

For QA Engineers:
    All tests run in mock mode. Test the full lifecycle: checkout → webhook
    → subscription active → portal → cancel → webhook → plan downgrade.

For Project Managers:
    This service manages all revenue-related operations. Stripe handles
    payment processing; we sync state via webhooks.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants.plans import PLAN_LIMITS, resolve_plan_from_price_id
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import PlanTier, User


def _is_mock_mode() -> bool:
    """Check if Stripe is in mock mode (no API key configured)."""
    return not settings.stripe_secret_key


async def get_or_create_stripe_customer(db: AsyncSession, user: User) -> str:
    """
    Get or create a Stripe Customer for the user.

    Idempotent: returns existing stripe_customer_id if set.

    Args:
        db: Async database session.
        user: The user to get/create a Stripe customer for.

    Returns:
        Stripe Customer ID string.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    if _is_mock_mode():
        customer_id = f"cus_mock_{uuid.uuid4().hex[:16]}"
    else:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"service": settings.service_name, "user_id": str(user.id)},
        )
        customer_id = customer.id

    user.stripe_customer_id = customer_id
    await db.flush()
    return customer_id


async def create_subscription_checkout(
    db: AsyncSession, user: User, plan: PlanTier
) -> dict:
    """
    Create a Stripe Checkout session for subscribing to a plan.

    In mock mode, creates the subscription directly and returns a mock URL.

    Args:
        db: Async database session.
        user: The user subscribing.
        plan: The plan tier to subscribe to.

    Returns:
        Dict with 'session_id' and 'checkout_url'.

    Raises:
        ValueError: If plan is free or user already has active subscription.
    """
    if plan == PlanTier.free:
        raise ValueError("Cannot checkout for free plan")

    # Check existing subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status.in_(
                [SubscriptionStatus.active, SubscriptionStatus.trialing]
            ),
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("User already has an active subscription")

    plan_limits = PLAN_LIMITS[plan]
    customer_id = await get_or_create_stripe_customer(db, user)

    if _is_mock_mode():
        # Create subscription directly in mock mode
        now = datetime.now(UTC)
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_mock_{uuid.uuid4().hex[:16]}",
            stripe_price_id=plan_limits.stripe_price_id or f"price_mock_{plan.value}",
            plan=plan,
            status=SubscriptionStatus.active,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db.add(subscription)
        user.plan = plan
        await db.flush()

        return {
            "session_id": f"cs_mock_{uuid.uuid4().hex[:16]}",
            "checkout_url": settings.stripe_billing_success_url,
        }

    import stripe

    stripe.api_key = settings.stripe_secret_key
    session_params = {
        "customer": customer_id,
        "mode": "subscription",
        "line_items": [{"price": plan_limits.stripe_price_id, "quantity": 1}],
        "success_url": settings.stripe_billing_success_url,
        "cancel_url": settings.stripe_billing_cancel_url,
        "metadata": {"user_id": str(user.id), "plan": plan.value},
    }
    if plan_limits.trial_days > 0:
        session_params["subscription_data"] = {
            "trial_period_days": plan_limits.trial_days
        }

    session = stripe.checkout.Session.create(**session_params)
    return {"session_id": session.id, "checkout_url": session.url}


async def create_portal_session(db: AsyncSession, user: User) -> dict:
    """
    Create a Stripe Customer Portal session for subscription management.

    Args:
        db: Async database session.
        user: The user requesting portal access.

    Returns:
        Dict with 'portal_url'.

    Raises:
        ValueError: If user has no Stripe customer ID.
    """
    if not user.stripe_customer_id:
        raise ValueError("User has no billing account")

    if _is_mock_mode():
        return {"portal_url": settings.stripe_billing_success_url}

    import stripe

    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.stripe_billing_success_url,
    )
    return {"portal_url": session.url}


async def sync_subscription_from_event(
    db: AsyncSession, event_data: dict
) -> Subscription | None:
    """
    Upsert a Subscription from a Stripe webhook event.

    Handles customer.subscription.created, updated, and deleted events.
    Updates the user's denormalized plan field based on subscription status.

    Args:
        db: Async database session.
        event_data: The subscription object from the Stripe event.

    Returns:
        The upserted Subscription, or None if plan resolution fails.
    """
    stripe_sub_id = event_data.get("id")
    stripe_price_id = event_data.get("items", {}).get("data", [{}])[0].get(
        "price", {}
    ).get("id", "")
    status_str = event_data.get("status", "active")
    customer_id = event_data.get("customer")

    plan = resolve_plan_from_price_id(stripe_price_id)
    if not plan:
        plan = PlanTier.pro  # Default fallback

    # Find user by stripe customer ID
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Upsert subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    )
    subscription = result.scalar_one_or_none()

    status = SubscriptionStatus(status_str) if status_str in SubscriptionStatus.__members__ else SubscriptionStatus.active

    now = datetime.now(UTC)
    period_start = datetime.fromtimestamp(
        event_data.get("current_period_start", now.timestamp()), tz=UTC
    )
    period_end = datetime.fromtimestamp(
        event_data.get("current_period_end", (now + timedelta(days=30)).timestamp()),
        tz=UTC,
    )

    if subscription:
        subscription.stripe_price_id = stripe_price_id
        subscription.plan = plan
        subscription.status = status
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = event_data.get(
            "cancel_at_period_end", False
        )
    else:
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_sub_id,
            stripe_price_id=stripe_price_id,
            plan=plan,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            cancel_at_period_end=event_data.get("cancel_at_period_end", False),
        )
        db.add(subscription)

    # Update denormalized plan on user
    if status in (SubscriptionStatus.active, SubscriptionStatus.trialing):
        user.plan = plan
    elif status == SubscriptionStatus.canceled:
        user.plan = PlanTier.free

    await db.flush()
    return subscription


async def get_subscription(
    db: AsyncSession, user_id: uuid.UUID
) -> Subscription | None:
    """
    Get the user's current subscription.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The most recent Subscription, or None.
    """
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    )
    return result.scalar_one_or_none()


async def get_billing_overview(db: AsyncSession, user: User) -> dict:
    """
    Get complete billing overview for the dashboard.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        Dict with current_plan, plan_name, subscription, and usage data.
    """
    subscription = await get_subscription(db, user.id)
    usage = await get_usage(db, user)

    return {
        "current_plan": user.plan,
        "plan_name": user.plan.value.title(),
        "subscription": subscription,
        "usage": usage,
    }


async def get_usage(db: AsyncSession, user: User) -> dict:
    """
    Get current resource usage for the billing period.

    This is a template method — each service overrides with specific metrics.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        Dict with plan, period dates, and metrics list.
    """
    from datetime import date

    today = date.today()
    period_start = today.replace(day=1)
    if today.month == 12:
        period_end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        period_end = today.replace(month=today.month + 1, day=1)

    plan_limits = PLAN_LIMITS[user.plan]

    # Template metrics — services override with actual counts
    return {
        "plan": user.plan,
        "period_start": period_start,
        "period_end": period_end,
        "metrics": [
            {
                "name": "items_used",
                "label": "Items Used",
                "used": 0,
                "limit": plan_limits.max_items,
            },
            {
                "name": "secondary_used",
                "label": "Secondary Items",
                "used": 0,
                "limit": plan_limits.max_secondary,
            },
        ],
    }
