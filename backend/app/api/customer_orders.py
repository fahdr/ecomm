"""Customer order history API router.

Provides endpoints for customers to view their order history and
order details from the storefront.

**For Developers:**
    Orders are matched by ``customer_email`` (not a customer_id FK).
    This means guest orders are also visible to customers who register
    with the same email.

**For QA Engineers:**
    - Only orders for the customer's email in the current store are returned.
    - Pagination is supported via ``page`` and ``per_page`` params.
    - Order detail includes line items.

**For End Users:**
    View your past orders and their details from your account page.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import CustomerAccount
from app.models.order import Order
from app.models.store import Store, StoreStatus
from app.api.deps import get_current_customer
from app.schemas.customer import CustomerOrderResponse

router = APIRouter(
    prefix="/public/stores/{slug}/customers/me/orders",
    tags=["customer-orders"],
)


async def _get_active_store(db: AsyncSession, slug: str) -> Store:
    """Resolve an active store by slug."""
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("", response_model=list[CustomerOrderResponse])
async def list_orders(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """List the customer's orders for the current store.

    Orders are matched by email address, so guest orders placed before
    registration are also included.

    Args:
        slug: The store's URL slug.
        page: Page number (1-indexed).
        per_page: Items per page.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        Paginated list of orders with line items.
    """
    store = await _get_active_store(db, slug)
    offset = (page - 1) * per_page

    result = await db.execute(
        select(Order)
        .where(
            Order.store_id == store.id,
            Order.customer_email == customer.email,
        )
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = result.scalars().all()

    return [CustomerOrderResponse.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=CustomerOrderResponse)
async def get_order(
    slug: str,
    order_id: uuid.UUID,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order by ID.

    Args:
        slug: The store's URL slug.
        order_id: The order's UUID.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        Order detail with line items.

    Raises:
        HTTPException: 404 if the order is not found or doesn't belong to this customer.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.store_id == store.id,
            Order.customer_email == customer.email,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return CustomerOrderResponse.model_validate(order)
