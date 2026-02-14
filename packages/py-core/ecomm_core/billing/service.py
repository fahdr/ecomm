"""
Billing service for Stripe subscription management.

Handles Stripe customer creation, checkout sessions, portal sessions,
and webhook event processing. Supports mock mode for local development.

For Developers:
    Mock mode is active when stripe_secret_key is empty. In mock mode,
    subscription records are created directly without Stripe API calls.
    All functions accept plan_limits as a parameter to avoid globals.

For QA Engineers:
    All tests run in mock mode. Test the full lifecycle: checkout -> webhook
    -> subscription active -> portal -> cancel -> webhook -> plan downgrade.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.models.subscription import Subscription, SubscriptionStatus
from ecomm_core.models.user import PlanTier, User
from ecomm_core.plans import PlanLimits


async def get_or_create_stripe_customer(
    db: AsyncSession, user: User, *, stripe_secret_key: str = "", service_name: str = "svc"
) -> str:
    """
    Get or create a Stripe Customer for the user.

    Args:
        db: Async database session.
        user: The user to get/create a Stripe customer for.
        stripe_secret_key: Stripe API key (empty = mock mode).
        service_name: Service identifier for metadata.

    Returns:
        Stripe Customer ID string.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    if not stripe_secret_key:
        customer_id = f"cus_mock_{uuid.uuid4().hex[:16]}"
    else:
        import stripe
        stripe.api_key = stripe_secret_key
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"service": service_name, "user_id": str(user.id)},
        )
        customer_id = customer.id

    user.stripe_customer_id = customer_id
    await db.flush()
    return customer_id


async def create_subscription_checkout(
    db: AsyncSession,
    user: User,
    plan: PlanTier,
    plan_limits: dict[PlanTier, PlanLimits],
    *,
    stripe_secret_key: str = "",
    success_url: str = "",
    cancel_url: str = "",
    service_name: str = "svc",
) -> dict:
    """
    Create a Stripe Checkout session for subscribing to a plan.

    In mock mode, creates the subscription directly and returns a mock URL.

    Args:
        db: Async database session.
        user: The user subscribing.
        plan: The plan tier to subscribe to.
        plan_limits: Plan limits configuration.
        stripe_secret_key: Stripe API key (empty = mock mode).
        success_url: Redirect URL after successful subscription.
        cancel_url: Redirect URL if subscription cancelled.
        service_name: Service identifier for metadata.

    Returns:
        Dict with 'session_id' and 'checkout_url'.

    Raises:
        ValueError: If plan is free or user already has active subscription.
    """
    if plan == PlanTier.free:
        raise ValueError("Cannot checkout for free plan")

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

    limits = plan_limits[plan]
    customer_id = await get_or_create_stripe_customer(
        db, user, stripe_secret_key=stripe_secret_key, service_name=service_name
    )

    if not stripe_secret_key:
        now = datetime.now(UTC)
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=f"sub_mock_{uuid.uuid4().hex[:16]}",
            stripe_price_id=limits.stripe_price_id or f"price_mock_{plan.value}",
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
            "checkout_url": success_url,
        }

    import stripe
    stripe.api_key = stripe_secret_key
    session_params = {
        "customer": customer_id,
        "mode": "subscription",
        "line_items": [{"price": limits.stripe_price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"user_id": str(user.id), "plan": plan.value},
    }
    if limits.trial_days > 0:
        session_params["subscription_data"] = {
            "trial_period_days": limits.trial_days
        }

    session = stripe.checkout.Session.create(**session_params)
    return {"session_id": session.id, "checkout_url": session.url}


async def create_portal_session(
    db: AsyncSession, user: User, *, stripe_secret_key: str = "", success_url: str = ""
) -> dict:
    """
    Create a Stripe Customer Portal session for subscription management.

    Args:
        db: Async database session.
        user: The user requesting portal access.
        stripe_secret_key: Stripe API key (empty = mock mode).
        success_url: Return URL after portal.

    Returns:
        Dict with 'portal_url'.

    Raises:
        ValueError: If user has no Stripe customer ID.
    """
    if not user.stripe_customer_id:
        raise ValueError("User has no billing account")

    if not stripe_secret_key:
        return {"portal_url": success_url}

    import stripe
    stripe.api_key = stripe_secret_key
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=success_url,
    )
    return {"portal_url": session.url}


async def sync_subscription_from_event(
    db: AsyncSession,
    event_data: dict,
    plan_limits: dict[PlanTier, PlanLimits],
) -> Subscription | None:
    """
    Upsert a Subscription from a Stripe webhook event.

    Args:
        db: Async database session.
        event_data: The subscription object from the Stripe event.
        plan_limits: Plan limits for price ID resolution.

    Returns:
        The upserted Subscription, or None if user not found.
    """
    from ecomm_core.plans import resolve_plan_from_price_id

    stripe_sub_id = event_data.get("id")
    stripe_price_id = event_data.get("items", {}).get("data", [{}])[0].get(
        "price", {}
    ).get("id", "")
    status_str = event_data.get("status", "active")
    customer_id = event_data.get("customer")

    plan = resolve_plan_from_price_id(plan_limits, stripe_price_id)
    if not plan:
        plan = PlanTier.pro

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return None

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    )
    subscription = result.scalar_one_or_none()

    sub_status = SubscriptionStatus(status_str) if status_str in SubscriptionStatus.__members__ else SubscriptionStatus.active

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
        subscription.status = sub_status
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = event_data.get("cancel_at_period_end", False)
    else:
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_sub_id,
            stripe_price_id=stripe_price_id,
            plan=plan,
            status=sub_status,
            current_period_start=period_start,
            current_period_end=period_end,
            cancel_at_period_end=event_data.get("cancel_at_period_end", False),
        )
        db.add(subscription)

    if sub_status in (SubscriptionStatus.active, SubscriptionStatus.trialing):
        user.plan = plan
    elif sub_status == SubscriptionStatus.canceled:
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


async def get_billing_overview(
    db: AsyncSession, user: User, plan_limits: dict[PlanTier, PlanLimits]
) -> dict:
    """
    Get complete billing overview for the dashboard.

    Args:
        db: Async database session.
        user: The authenticated user.
        plan_limits: Plan limits configuration.

    Returns:
        Dict with current_plan, plan_name, subscription, and usage data.
    """
    subscription = await get_subscription(db, user.id)
    usage = await get_usage(db, user, plan_limits)

    return {
        "current_plan": user.plan,
        "plan_name": user.plan.value.title(),
        "subscription": subscription,
        "usage": usage,
    }


async def get_usage(
    db: AsyncSession, user: User, plan_limits: dict[PlanTier, PlanLimits]
) -> dict:
    """
    Get current resource usage for the billing period.

    This is a template method — each service overrides with specific metrics.

    Args:
        db: Async database session.
        user: The authenticated user.
        plan_limits: Plan limits configuration.

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

    limits = plan_limits[user.plan]

    return {
        "plan": user.plan,
        "period_start": period_start,
        "period_end": period_end,
        "metrics": [
            {
                "name": "items_used",
                "label": "Items Used",
                "used": 0,
                "limit": limits.max_items,
            },
            {
                "name": "secondary_used",
                "label": "Secondary Items",
                "used": 0,
                "limit": limits.max_secondary,
            },
        ],
    }
