"""Order business logic.

Handles order creation, listing, retrieval, and status updates for
store-scoped orders. All store-owner functions verify ownership before
performing operations.

**For Developers:**
    ``create_order_from_checkout`` is called internally during checkout
    to create a pending order. ``confirm_order`` is called by the Stripe
    webhook handler when payment succeeds. Store-owner endpoints use
    ``list_orders``, ``get_order``, and ``update_order_status``.

**For QA Engineers:**
    - ``create_order_from_checkout`` validates that all products are active
      and in-stock before creating the order.
    - ``confirm_order`` transitions the order from ``pending`` to ``paid``.
    - ``list_orders`` supports pagination and optional status filtering.
    - Store ownership is verified for all store-owner operations.

**For End Users:**
    Orders are automatically created when you proceed to checkout and
    confirmed when payment is successful via Stripe.
"""

import math
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductStatus, ProductVariant
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


async def validate_and_build_order_items(
    db: AsyncSession,
    store_id: uuid.UUID,
    items: list[dict],
) -> tuple[list[dict], Decimal]:
    """Validate cart items against the database and build order item data.

    Checks that each product exists, is active, belongs to the store,
    and that variants (if specified) exist and have sufficient stock.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        items: List of dicts with product_id, variant_id, and quantity.

    Returns:
        A tuple of (order_item_dicts, total_amount).

    Raises:
        ValueError: If any product is invalid, out of stock, or doesn't
            belong to the store.
    """
    order_items = []
    total = Decimal("0.00")

    for item in items:
        product_id = item["product_id"]
        variant_id = item.get("variant_id")
        quantity = item["quantity"]

        result = await db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.store_id == store_id,
                Product.status == ProductStatus.active,
            )
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise ValueError(f"Product {product_id} not found or not available")

        unit_price = product.price
        variant_name = None

        if variant_id:
            variant_result = await db.execute(
                select(ProductVariant).where(
                    ProductVariant.id == variant_id,
                    ProductVariant.product_id == product_id,
                )
            )
            variant = variant_result.scalar_one_or_none()
            if variant is None:
                raise ValueError(f"Variant {variant_id} not found")
            if variant.inventory_count < quantity:
                raise ValueError(
                    f"Insufficient stock for variant '{variant.name}' "
                    f"(available: {variant.inventory_count}, requested: {quantity})"
                )
            if variant.price is not None:
                unit_price = variant.price
            variant_name = variant.name

        line_total = unit_price * quantity
        total += line_total

        order_items.append({
            "product_id": product_id,
            "variant_id": variant_id,
            "product_title": product.title,
            "variant_name": variant_name,
            "quantity": quantity,
            "unit_price": unit_price,
        })

    return order_items, total


async def create_order_from_checkout(
    db: AsyncSession,
    store_id: uuid.UUID,
    customer_email: str,
    items_data: list[dict],
    total: Decimal,
    stripe_session_id: str | None = None,
    customer_id: uuid.UUID | None = None,
) -> Order:
    """Create a pending order from validated checkout data.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        customer_email: Customer's email address.
        items_data: Validated order item dicts from ``validate_and_build_order_items``.
        total: Pre-calculated total amount.
        stripe_session_id: Optional Stripe session ID.
        customer_id: Optional customer UUID (None for guest checkout).

    Returns:
        The newly created Order ORM instance with items loaded.
    """
    order = Order(
        store_id=store_id,
        customer_email=customer_email,
        customer_id=customer_id,
        status=OrderStatus.pending,
        total=total,
        stripe_session_id=stripe_session_id,
    )
    db.add(order)
    await db.flush()

    for item_data in items_data:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data["product_id"],
            variant_id=item_data.get("variant_id"),
            product_title=item_data["product_title"],
            variant_name=item_data.get("variant_name"),
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
        )
        db.add(order_item)

    await db.flush()
    await db.refresh(order)
    return order


async def confirm_order(
    db: AsyncSession,
    stripe_session_id: str,
) -> Order | None:
    """Confirm an order by transitioning from pending to paid.

    Called by the Stripe webhook handler when payment succeeds.
    Also decrements variant inventory counts.

    Args:
        db: Async database session.
        stripe_session_id: The Stripe Checkout session ID.

    Returns:
        The confirmed Order, or None if no matching pending order found.
    """
    result = await db.execute(
        select(Order).where(
            Order.stripe_session_id == stripe_session_id,
            Order.status == OrderStatus.pending,
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        return None

    order.status = OrderStatus.paid

    # Decrement inventory for variants
    for item in order.items:
        if item.variant_id:
            variant_result = await db.execute(
                select(ProductVariant).where(ProductVariant.id == item.variant_id)
            )
            variant = variant_result.scalar_one_or_none()
            if variant:
                variant.inventory_count = max(0, variant.inventory_count - item.quantity)

    await db.flush()
    await db.refresh(order)
    return order


async def list_orders(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    status_filter: OrderStatus | None = None,
) -> tuple[list[Order], int]:
    """List orders for a store with pagination and optional status filtering.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        status_filter: Optional status to filter by.

    Returns:
        A tuple of (orders list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Order).where(Order.store_id == store_id)
    count_query = select(func.count(Order.id)).where(Order.store_id == store_id)

    if status_filter is not None:
        query = query.where(Order.status == status_filter)
        count_query = count_query.where(Order.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    orders = list(result.scalars().all())

    return orders, total


async def get_order(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    order_id: uuid.UUID,
) -> Order:
    """Retrieve a single order, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        order_id: The UUID of the order to retrieve.

    Returns:
        The Order ORM instance with items loaded.

    Raises:
        ValueError: If the store or order doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.store_id == store_id,
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise ValueError("Order not found")
    return order


async def update_order_status(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    order_id: uuid.UUID,
    new_status: OrderStatus,
) -> Order:
    """Update an order's status.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        order_id: The UUID of the order to update.
        new_status: The new order status.

    Returns:
        The updated Order ORM instance.

    Raises:
        ValueError: If the store or order doesn't exist, or the store
            belongs to another user.
    """
    order = await get_order(db, store_id, user_id, order_id)
    order.status = new_status
    await db.flush()
    await db.refresh(order)
    return order
