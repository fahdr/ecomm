"""Subscription business logic.

Handles the full subscription lifecycle: creating Stripe checkout sessions,
managing Customer Portal sessions, syncing webhook events, and querying
current subscription state and resource usage.

**For Developers:**
    All functions are async. Stripe SDK calls are synchronous but wrapped
    in this service layer. Mock mode is supported: when
    ``settings.stripe_secret_key`` is empty, ``create_subscription_checkout``
    creates the subscription record directly (simulating what a webhook
    would do) and returns a mock redirect URL.

**For QA Engineers:**
    - ``create_subscription_checkout`` rejects users who already have an
      active or trialing subscription (returns 400).
    - ``sync_subscription_from_event`` is idempotent (upserts by
      ``stripe_subscription_id``).
    - ``get_usage`` counts stores (non-deleted), products (non-archived),
      and orders (current calendar month).

**For End Users:**
    Subscribe to a plan from the Pricing page. Your plan determines how
    many stores and products you can create, and how many orders your
    stores can process per month.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants.plans import (
    PLAN_DISPLAY_NAMES,
    PLAN_LIMITS,
    PlanTier,
    get_plan_limits,
    resolve_plan_from_price_id,
)
from app.models.order import Order
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.services.stripe_service import (
    create_billing_portal_session,
    create_stripe_customer,
    create_subscription_session,
)

logger = logging.getLogger(__name__)


async def get_or_create_stripe_customer(
    db: AsyncSession,
    user: User,
) -> str:
    """Return the user's Stripe Customer ID, creating one if needed.

    Idempotent: if ``user.stripe_customer_id`` is already set, returns
    it without calling Stripe.

    Args:
        db: Async database session.
        user: The user who needs a Stripe Customer.

    Returns:
        The Stripe Customer ID string.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer_id = create_stripe_customer(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer_id
    await db.flush()
    await db.refresh(user)
    return customer_id


async def create_subscription_checkout(
    db: AsyncSession,
    user: User,
    plan: PlanTier,
) -> dict:
    """Create a Stripe Checkout session for subscribing to a plan.

    In mock mode (no Stripe keys), creates the subscription record
    directly and returns a mock redirect URL.

    Args:
        db: Async database session.
        user: The authenticated user.
        plan: The plan tier to subscribe to.

    Returns:
        A dict with ``session_id`` and ``checkout_url``.

    Raises:
        ValueError: If the plan is free, or the user already has an
            active/trialing subscription.
    """
    if plan == PlanTier.free:
        raise ValueError("Cannot subscribe to the free plan")

    # Check for existing active subscription
    existing = await _get_active_subscription(db, user.id)
    if existing:
        raise ValueError(
            "User already has an active subscription. "
            "Use the Customer Portal to change plans."
        )

    limits = get_plan_limits(plan)
    customer_id = await get_or_create_stripe_customer(db, user)

    # Mock mode: create subscription directly
    if not settings.stripe_secret_key:
        now = datetime.now(timezone.utc)
        mock_sub_id = f"sub_mock_{uuid.uuid4().hex[:12]}"
        mock_price_id = f"price_mock_{plan.value}"

        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=mock_sub_id,
            stripe_price_id=mock_price_id,
            plan=plan,
            status=SubscriptionStatus.active,
            current_period_start=now,
            current_period_end=datetime(
                now.year, now.month + 1 if now.month < 12 else 1,
                now.day, tzinfo=timezone.utc,
            ),
            cancel_at_period_end=False,
        )
        db.add(subscription)

        user.plan = plan
        await db.flush()
        await db.refresh(subscription)
        await db.refresh(user)

        return {
            "session_id": f"cs_sub_mock_{uuid.uuid4().hex[:12]}",
            "checkout_url": settings.stripe_billing_success_url,
        }

    # Real Stripe mode
    result = create_subscription_session(
        customer_id=customer_id,
        price_id=limits.stripe_price_id,
        trial_days=limits.trial_days,
        success_url=settings.stripe_billing_success_url,
        cancel_url=settings.stripe_billing_cancel_url,
        metadata={"user_id": str(user.id), "plan": plan.value},
    )
    return result


async def create_portal_session(
    db: AsyncSession,
    user: User,
) -> dict:
    """Create a Stripe Customer Portal session for managing a subscription.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        A dict with ``portal_url``.

    Raises:
        ValueError: If the user has no Stripe Customer ID.
    """
    if not user.stripe_customer_id:
        raise ValueError("No billing account found. Subscribe to a plan first.")

    result = create_billing_portal_session(
        customer_id=user.stripe_customer_id,
        return_url=settings.stripe_billing_success_url,
    )
    return result


async def sync_subscription_from_event(
    db: AsyncSession,
    event_data: dict,
) -> Subscription | None:
    """Sync subscription state from a Stripe webhook event payload.

    Handles ``customer.subscription.created``, ``.updated``, and
    ``.deleted`` events. Upserts the subscription record by
    ``stripe_subscription_id`` and updates the user's denormalised
    ``plan`` field.

    Args:
        db: Async database session.
        event_data: The ``event.data.object`` dict from Stripe.

    Returns:
        The upserted Subscription instance, or None if the user
        could not be resolved.
    """
    stripe_sub_id = event_data.get("id", "")
    stripe_customer_id = event_data.get("customer", "")
    stripe_status = event_data.get("status", "")
    price_id = ""

    # Extract price ID from items
    items = event_data.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")

    # Find the user by stripe_customer_id
    result = await db.execute(
        select(User).where(User.stripe_customer_id == stripe_customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(
            "No user found for Stripe customer %s (sub %s)",
            stripe_customer_id,
            stripe_sub_id,
        )
        return None

    # Resolve plan tier from price ID
    plan = resolve_plan_from_price_id(price_id)
    if not plan:
        # Fallback: check metadata
        metadata = event_data.get("metadata", {})
        plan_str = metadata.get("plan", "")
        try:
            plan = PlanTier(plan_str)
        except ValueError:
            plan = PlanTier.starter  # default fallback

    # Map Stripe status to our enum
    try:
        sub_status = SubscriptionStatus(stripe_status)
    except ValueError:
        sub_status = SubscriptionStatus.active

    # Parse timestamps
    period_start = _from_timestamp(event_data.get("current_period_start"))
    period_end = _from_timestamp(event_data.get("current_period_end"))
    trial_start = _from_timestamp(event_data.get("trial_start"))
    trial_end = _from_timestamp(event_data.get("trial_end"))
    cancel_at_period_end = event_data.get("cancel_at_period_end", False)

    # Upsert subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.stripe_price_id = price_id
        subscription.plan = plan
        subscription.status = sub_status
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = cancel_at_period_end
        subscription.trial_start = trial_start
        subscription.trial_end = trial_end
    else:
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_sub_id,
            stripe_price_id=price_id,
            plan=plan,
            status=sub_status,
            current_period_start=period_start,
            current_period_end=period_end,
            cancel_at_period_end=cancel_at_period_end,
            trial_start=trial_start,
            trial_end=trial_end,
        )
        db.add(subscription)

    # Update denormalised user plan
    if sub_status in (SubscriptionStatus.active, SubscriptionStatus.trialing):
        user.plan = plan
    elif sub_status == SubscriptionStatus.canceled:
        user.plan = PlanTier.free

    await db.flush()
    await db.refresh(subscription)
    await db.refresh(user)

    logger.info(
        "Synced subscription %s for user %s: plan=%s status=%s",
        stripe_sub_id,
        user.id,
        plan.value,
        sub_status.value,
    )
    return subscription


async def handle_payment_failed(
    db: AsyncSession,
    event_data: dict,
) -> None:
    """Handle an ``invoice.payment_failed`` event.

    Updates the subscription status to ``past_due`` if a matching
    subscription is found.

    Args:
        db: Async database session.
        event_data: The ``event.data.object`` dict from Stripe (invoice).
    """
    stripe_sub_id = event_data.get("subscription", "")
    if not stripe_sub_id:
        return

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription:
        subscription.status = SubscriptionStatus.past_due
        await db.flush()
        await db.refresh(subscription)
        logger.warning(
            "Payment failed for subscription %s, status set to past_due",
            stripe_sub_id,
        )


async def get_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Subscription | None:
    """Get the user's current subscription (if any).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The Subscription instance, or None if the user has no subscription.
    """
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_billing_overview(
    db: AsyncSession,
    user: User,
) -> dict:
    """Build a billing overview response for the current user.

    Combines the user's plan, active subscription, and resource usage.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        A dict matching ``BillingOverviewResponse`` fields.
    """
    subscription = await get_subscription(db, user.id)
    usage = await get_usage(db, user)
    plan = PlanTier(user.plan)

    return {
        "current_plan": plan,
        "plan_name": PLAN_DISPLAY_NAMES.get(plan, plan.value.title()),
        "subscription": subscription,
        "usage": usage,
    }


async def get_usage(db: AsyncSession, user: User) -> dict:
    """Count current resource usage for the user's plan limits.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        A dict matching ``UsageResponse`` fields.
    """
    plan = PlanTier(user.plan)
    limits = get_plan_limits(plan)

    # Count non-deleted stores
    stores_result = await db.execute(
        select(func.count(Store.id)).where(
            Store.user_id == user.id,
            Store.status != StoreStatus.deleted,
        )
    )
    stores_used = stores_result.scalar_one()

    # Count non-archived products across all user's stores
    products_result = await db.execute(
        select(func.count(Product.id))
        .join(Store, Product.store_id == Store.id)
        .where(
            Store.user_id == user.id,
            Store.status != StoreStatus.deleted,
            Product.status != ProductStatus.archived,
        )
    )
    products_used = products_result.scalar_one()

    # Count orders this calendar month across all user's stores
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    orders_result = await db.execute(
        select(func.count(Order.id))
        .join(Store, Order.store_id == Store.id)
        .where(
            Store.user_id == user.id,
            Order.created_at >= month_start,
        )
    )
    orders_this_month = orders_result.scalar_one()

    return {
        "stores_used": stores_used,
        "stores_limit": limits.max_stores,
        "products_used": products_used,
        "products_limit_per_store": limits.max_products_per_store,
        "orders_this_month": orders_this_month,
        "orders_limit": limits.max_orders_per_month,
    }


async def _get_active_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Subscription | None:
    """Check if the user has an active or trialing subscription.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The active Subscription, or None.
    """
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_([
                SubscriptionStatus.active,
                SubscriptionStatus.trialing,
            ]),
        )
    )
    return result.scalar_one_or_none()


def _from_timestamp(ts: int | None) -> datetime:
    """Convert a Unix timestamp to a timezone-aware datetime.

    Args:
        ts: Unix timestamp (seconds since epoch), or None.

    Returns:
        A UTC datetime. Defaults to now if ``ts`` is None.
    """
    if ts is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(ts, tz=timezone.utc)
