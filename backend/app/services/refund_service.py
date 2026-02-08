"""Refund business logic.

Handles refund request creation, listing, status updates, and processing
for store orders. In a dropshipping context, refunds are purely monetary
(no physical returns to process).

**For Developers:**
    All functions take ``store_id`` and ``user_id`` to enforce store
    ownership. ``create_refund`` validates that the refund amount does not
    exceed the order total minus any previously completed refunds.
    ``process_refund`` marks the refund as completed and would trigger a
    Stripe refund in production (mock in dev mode).

**For QA Engineers:**
    - ``create_refund`` checks that the order belongs to the store and
      that the cumulative refund amount does not exceed the order total.
    - ``update_refund`` allows status transitions and admin notes.
    - ``process_refund`` transitions status to ``completed`` and updates
      the order's refund status if applicable.
    - Partial refunds are supported (amount < order total).

**For Project Managers:**
    This service powers Feature 14 (Refunds & Returns) from the backlog.
    It enables store owners to process customer refund requests through
    a structured workflow.

**For End Users:**
    When a customer requests a refund, it appears in your Refunds dashboard.
    Review the reason, approve or reject the request, and process the
    refund. Since dropshipping stores don't hold inventory, there is no
    physical return process.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.refund import Refund, RefundReason, RefundStatus
from app.models.store import Store, StoreStatus


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


async def create_refund(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    order_id: uuid.UUID,
    reason: RefundReason,
    reason_details: str | None = None,
    amount: Decimal | None = None,
) -> Refund:
    """Create a new refund request for an order.

    Validates that the order belongs to the store and that the refund
    amount does not exceed the order total minus previously completed
    refunds. If no amount is provided, defaults to the full order total.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        order_id: The UUID of the order to refund.
        reason: The predefined reason for the refund.
        reason_details: Optional free-text elaboration on the reason.
        amount: The refund amount. Defaults to the full order total.

    Returns:
        The newly created Refund ORM instance.

    Raises:
        ValueError: If the store or order doesn't exist, the order
            doesn't belong to the store, or the refund amount exceeds
            the refundable balance.
    """
    await _verify_store_ownership(db, store_id, user_id)

    # Verify order belongs to the store
    order_result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.store_id == store_id,
        )
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise ValueError("Order not found in this store")

    # Calculate already-refunded amount
    refunded_result = await db.execute(
        select(func.coalesce(func.sum(Refund.amount), Decimal("0.00"))).where(
            Refund.order_id == order_id,
            Refund.status == RefundStatus.completed,
        )
    )
    already_refunded = refunded_result.scalar_one()

    refundable_balance = order.total - already_refunded
    refund_amount = amount if amount is not None else refundable_balance

    if refund_amount <= Decimal("0.00"):
        raise ValueError("Refund amount must be greater than zero")

    if refund_amount > refundable_balance:
        raise ValueError(
            f"Refund amount (${refund_amount}) exceeds refundable balance "
            f"(${refundable_balance})"
        )

    refund = Refund(
        store_id=store_id,
        order_id=order_id,
        customer_email=order.customer_email,
        reason=reason,
        reason_details=reason_details,
        amount=refund_amount,
        status=RefundStatus.pending,
    )
    db.add(refund)
    await db.flush()
    await db.refresh(refund)
    return refund


async def list_refunds(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    status_filter: RefundStatus | None = None,
) -> tuple[list[Refund], int]:
    """List refunds for a store with pagination and optional status filtering.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        status_filter: Optional status to filter by (pending, approved,
            rejected, completed).

    Returns:
        A tuple of (refunds list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Refund).where(Refund.store_id == store_id)
    count_query = select(func.count(Refund.id)).where(Refund.store_id == store_id)

    if status_filter is not None:
        query = query.where(Refund.status == status_filter)
        count_query = count_query.where(Refund.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Refund.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    refunds = list(result.scalars().all())

    return refunds, total


async def get_refund(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    refund_id: uuid.UUID,
) -> Refund:
    """Retrieve a single refund, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        refund_id: The UUID of the refund to retrieve.

    Returns:
        The Refund ORM instance with relationships loaded.

    Raises:
        ValueError: If the store or refund doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Refund).where(
            Refund.id == refund_id,
            Refund.store_id == store_id,
        )
    )
    refund = result.scalar_one_or_none()
    if refund is None:
        raise ValueError("Refund not found")
    return refund


async def update_refund(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    refund_id: uuid.UUID,
    status: RefundStatus | None = None,
    admin_notes: str | None = None,
) -> Refund:
    """Update a refund's status and/or admin notes.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        refund_id: The UUID of the refund to update.
        status: Optional new status for the refund.
        admin_notes: Optional private notes from the store owner.

    Returns:
        The updated Refund ORM instance.

    Raises:
        ValueError: If the store or refund doesn't exist, or the store
            belongs to another user.
    """
    refund = await get_refund(db, store_id, user_id, refund_id)

    if status is not None:
        refund.status = status
    if admin_notes is not None:
        refund.admin_notes = admin_notes

    await db.flush()
    await db.refresh(refund)
    return refund


async def process_refund(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    refund_id: uuid.UUID,
) -> Refund:
    """Process a refund by marking it as completed.

    In production, this would also trigger a Stripe refund API call.
    In dev mode, it generates a mock Stripe refund ID. After completion,
    if the cumulative refund amount equals or exceeds the order total,
    the order status is updated to ``cancelled``.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        refund_id: The UUID of the refund to process.

    Returns:
        The completed Refund ORM instance with the stripe_refund_id set.

    Raises:
        ValueError: If the store or refund doesn't exist, the store
            belongs to another user, or the refund is not in a processable
            state (must be pending or approved).
    """
    refund = await get_refund(db, store_id, user_id, refund_id)

    if refund.status not in (RefundStatus.pending, RefundStatus.approved):
        raise ValueError(
            f"Cannot process a refund with status '{refund.status.value}'. "
            f"Only pending or approved refunds can be processed."
        )

    # In production, call Stripe refund API here
    # For now, generate a mock refund ID
    import uuid as uuid_module
    refund.stripe_refund_id = f"re_mock_{uuid_module.uuid4().hex[:12]}"
    refund.status = RefundStatus.completed

    # Check if order is fully refunded
    order_result = await db.execute(
        select(Order).where(Order.id == refund.order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is not None:
        total_refunded_result = await db.execute(
            select(func.coalesce(func.sum(Refund.amount), Decimal("0.00"))).where(
                Refund.order_id == order.id,
                Refund.status == RefundStatus.completed,
            )
        )
        total_refunded = total_refunded_result.scalar_one()
        if total_refunded >= order.total:
            order.status = OrderStatus.cancelled

    await db.flush()
    await db.refresh(refund)
    return refund
