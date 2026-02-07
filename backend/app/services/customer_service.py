"""Customer management business logic for the dashboard.

Provides queries for store owners to view their customers: listing with
search and pagination, customer detail with order stats, and a customer's
order history.

**For Developers:**
    All functions verify store ownership before returning data. Use the
    same ``_verify_store_ownership`` pattern from ``order_service``.

**For QA Engineers:**
    - ``list_customers`` supports optional search by email or name.
    - ``get_customer_detail`` returns order_count and total_spent.
    - Store ownership is verified for all operations (404 if mismatch).

**For End Users:**
    Store owners can view their customer list and individual customer
    details from the dashboard.
"""

import math
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
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


async def list_customers(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[Customer], int]:
    """List customers for a store with pagination and optional search.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        search: Optional search term to filter by email or name.

    Returns:
        A tuple of (customers list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    base_filter = [Customer.store_id == store_id]
    if search:
        search_term = f"%{search}%"
        base_filter.append(
            (Customer.email.ilike(search_term))
            | (Customer.first_name.ilike(search_term))
            | (Customer.last_name.ilike(search_term))
        )

    count_result = await db.execute(
        select(func.count(Customer.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Customer)
        .where(*base_filter)
        .order_by(Customer.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    customers = list(result.scalars().all())

    return customers, total


async def get_customer_detail(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> dict:
    """Get customer details with order statistics.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        customer_id: The customer's UUID.

    Returns:
        A dict with customer data, order_count, and total_spent.

    Raises:
        ValueError: If the store or customer doesn't exist, or store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.store_id == store_id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise ValueError("Customer not found")

    # Count orders and total spent
    stats_result = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total), Decimal("0.00")),
        ).where(
            Order.customer_id == customer_id,
            Order.store_id == store_id,
            Order.status != OrderStatus.cancelled,
        )
    )
    row = stats_result.one()
    order_count = row[0]
    total_spent = row[1]

    return {
        "customer": customer,
        "order_count": order_count,
        "total_spent": total_spent,
    }


async def list_customer_orders(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    customer_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Order], int]:
    """List orders for a specific customer in a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        customer_id: The customer's UUID.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (orders list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    base_filter = [
        Order.store_id == store_id,
        Order.customer_id == customer_id,
    ]

    count_result = await db.execute(
        select(func.count(Order.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Order)
        .where(*base_filter)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())

    return orders, total
