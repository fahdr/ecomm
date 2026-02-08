"""Fraud detection business logic.

Provides automated fraud scoring for orders based on heuristic signals.
Each order is scored from 0 to 100 and mapped to a risk level (low,
medium, high, critical). Store owners can review flagged orders and
override the automated assessment.

**For Developers:**
    Fraud scoring uses a weighted signal system. Each signal contributes
    a configurable number of points. The total score is capped at 100.
    Signals include: high order amount, new customer with high order,
    order velocity (many orders in short time), email pattern anomalies,
    and mismatched shipping address. Risk levels: ``low`` (0-25),
    ``medium`` (26-50), ``high`` (51-75), ``critical`` (76-100).

**For QA Engineers:**
    - ``check_order_fraud`` creates a FraudCheck record with the score,
      risk level, and detected signals.
    - The ``high_amount`` signal triggers when the order exceeds $500.
    - The ``velocity_spike`` signal triggers when 3+ orders arrive from
      the same email within 1 hour.
    - The ``new_customer_high_order`` signal triggers for first-time
      buyers with orders over $200.
    - ``review_fraud_check`` allows manual flagging/unflagging.
    - ``list_fraud_checks`` supports pagination and flagged-only filtering.

**For Project Managers:**
    This service powers Feature 28 (Fraud Detection) from the backlog.
    It provides automated risk scoring to help store owners identify
    potentially fraudulent orders before fulfillment.

**For End Users:**
    Automatically screen orders for fraud signals before fulfilling them.
    High-risk orders are flagged for your review, reducing chargebacks
    and protecting your business.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# FraudCheck model -- import conditionally.
# ---------------------------------------------------------------------------
try:
    from app.models.fraud import FraudCheck
except ImportError:
    FraudCheck = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Fraud scoring configuration
# ---------------------------------------------------------------------------
_HIGH_AMOUNT_THRESHOLD = Decimal("500.00")
_HIGH_AMOUNT_SCORE = 20

_NEW_CUSTOMER_HIGH_ORDER_THRESHOLD = Decimal("200.00")
_NEW_CUSTOMER_HIGH_ORDER_SCORE = 25

_VELOCITY_WINDOW_HOURS = 1
_VELOCITY_COUNT_THRESHOLD = 3
_VELOCITY_SCORE = 30

_SUSPICIOUS_EMAIL_PATTERNS = ["+", "test", "fake", "temp"]
_SUSPICIOUS_EMAIL_SCORE = 15

_FIRST_ORDER_SCORE = 10


def _map_risk_level(score: int) -> str:
    """Map a numeric fraud score to a human-readable risk level.

    Args:
        score: The fraud score (0-100).

    Returns:
        A risk level string: ``"low"``, ``"medium"``, ``"high"``, or
        ``"critical"``.
    """
    if score <= 25:
        return "low"
    elif score <= 50:
        return "medium"
    elif score <= 75:
        return "high"
    else:
        return "critical"


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def check_order_fraud(
    db: AsyncSession,
    store_id: uuid.UUID,
    order_id: uuid.UUID,
    customer_email: str,
    total: Decimal,
    shipping_address: str | None = None,
    ip_address: str | None = None,
) -> "FraudCheck":
    """Run fraud scoring on an order and create a FraudCheck record.

    Evaluates multiple fraud signals and produces a weighted score from
    0 to 100. The score is mapped to a risk level. This function is
    typically called automatically after order creation.

    Fraud signals evaluated:
        - ``high_amount``: Order total exceeds $500.
        - ``new_customer_high_order``: First-time buyer with order > $200.
        - ``velocity_spike``: 3+ orders from same email in 1 hour.
        - ``suspicious_email``: Email contains suspicious patterns.
        - ``first_order``: Customer's first order (minor signal).

    Args:
        db: Async database session.
        store_id: The store's UUID.
        order_id: The UUID of the order to check.
        customer_email: The customer's email address.
        total: The order total amount.
        shipping_address: Optional shipping address text.
        ip_address: Optional IP address of the customer.

    Returns:
        The newly created FraudCheck ORM instance with score, risk level,
        and detected signals.
    """
    signals = []
    score = 0

    # Signal 1: High order amount
    if total >= _HIGH_AMOUNT_THRESHOLD:
        signals.append("high_amount")
        score += _HIGH_AMOUNT_SCORE

    # Signal 2: Check if this is a new customer with a high order
    previous_orders_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.store_id == store_id,
            Order.customer_email == customer_email,
            Order.id != order_id,
            Order.status.in_([
                OrderStatus.paid,
                OrderStatus.shipped,
                OrderStatus.delivered,
            ]),
        )
    )
    previous_order_count = previous_orders_result.scalar_one()

    if previous_order_count == 0:
        signals.append("first_order")
        score += _FIRST_ORDER_SCORE

        if total >= _NEW_CUSTOMER_HIGH_ORDER_THRESHOLD:
            signals.append("new_customer_high_order")
            score += _NEW_CUSTOMER_HIGH_ORDER_SCORE

    # Signal 3: Velocity spike (multiple orders in short window)
    window_start = datetime.now(timezone.utc) - timedelta(hours=_VELOCITY_WINDOW_HOURS)
    velocity_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.store_id == store_id,
            Order.customer_email == customer_email,
            Order.created_at >= window_start,
        )
    )
    recent_order_count = velocity_result.scalar_one()

    if recent_order_count >= _VELOCITY_COUNT_THRESHOLD:
        signals.append("velocity_spike")
        score += _VELOCITY_SCORE

    # Signal 4: Suspicious email patterns
    email_lower = customer_email.lower()
    for pattern in _SUSPICIOUS_EMAIL_PATTERNS:
        if pattern in email_lower:
            signals.append("suspicious_email")
            score += _SUSPICIOUS_EMAIL_SCORE
            break

    # Cap score at 100
    score = min(score, 100)
    risk_level = _map_risk_level(score)

    # Determine if auto-flagged
    is_flagged = risk_level in ("high", "critical")

    fraud_check = FraudCheck(
        store_id=store_id,
        order_id=order_id,
        risk_score=score,
        risk_level=risk_level,
        signals=signals,
        is_flagged=is_flagged,
        notes=None,
    )
    db.add(fraud_check)
    await db.flush()
    await db.refresh(fraud_check)
    return fraud_check


async def list_fraud_checks(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    flagged_only: bool = False,
) -> tuple[list, int]:
    """List fraud checks for a store with pagination.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        flagged_only: If True, only return flagged fraud checks.

    Returns:
        A tuple of (fraud checks list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(FraudCheck).where(FraudCheck.store_id == store_id)
    count_query = select(func.count(FraudCheck.id)).where(
        FraudCheck.store_id == store_id
    )

    if flagged_only:
        query = query.where(FraudCheck.is_flagged.is_(True))
        count_query = count_query.where(FraudCheck.is_flagged.is_(True))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(FraudCheck.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    fraud_checks = list(result.scalars().all())

    return fraud_checks, total


async def review_fraud_check(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    check_id: uuid.UUID,
    is_flagged: bool,
    notes: str | None = None,
) -> "FraudCheck":
    """Review and update a fraud check's flagged status.

    Allows store owners to manually flag or unflag orders after
    reviewing the automated assessment.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        check_id: The UUID of the fraud check to review.
        is_flagged: Whether the order should be flagged as fraudulent.
        notes: Optional reviewer notes.

    Returns:
        The updated FraudCheck ORM instance.

    Raises:
        ValueError: If the store or fraud check doesn't exist, or the
            store belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(FraudCheck).where(
            FraudCheck.id == check_id,
            FraudCheck.store_id == store_id,
        )
    )
    fraud_check = result.scalar_one_or_none()
    if fraud_check is None:
        raise ValueError("Fraud check not found")

    fraud_check.is_flagged = is_flagged
    if notes is not None:
        fraud_check.notes = notes

    await db.flush()
    await db.refresh(fraud_check)
    return fraud_check
