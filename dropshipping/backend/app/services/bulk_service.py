"""Bulk operations business logic.

Handles batch operations on products including bulk updates, deletes,
and price adjustments. Operations are executed transactionally with
per-item error tracking.

**For Developers:**
    All bulk functions return a summary dict with ``total``, ``succeeded``,
    ``failed``, and ``errors`` (list of per-item error details). Each item
    is processed independently so a failure on one product does not block
    others. The caller is responsible for committing the transaction.

**For QA Engineers:**
    - ``bulk_update_products`` applies the same field updates to all
      specified products.
    - ``bulk_delete_products`` performs soft-delete (sets status to
      ``archived``).
    - ``bulk_update_prices`` supports ``"percentage"`` and ``"fixed"``
      adjustment types, and prevents negative prices.
    - All functions verify store ownership before processing.
    - Products not belonging to the store are reported as errors.

**For Project Managers:**
    This service powers Feature 26 (Bulk Operations) from the backlog.
    It enables store owners to efficiently manage large product catalogs
    by performing batch updates, deletes, and price adjustments.

**For End Users:**
    Select multiple products and apply changes in bulk -- update fields,
    adjust prices by a percentage or fixed amount, or archive products
    that are no longer sold.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductStatus
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


async def bulk_update_products(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_ids: list[uuid.UUID],
    updates: dict,
) -> dict:
    """Apply the same field updates to multiple products.

    Processes each product independently. Products that don't exist or
    don't belong to the store are reported as errors.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_ids: List of product UUIDs to update.
        updates: Dict of field names to new values to apply to each product.

    Returns:
        A summary dict with ``total`` (int), ``succeeded`` (int),
        ``failed`` (int), and ``errors`` (list of dicts with ``product_id``
        and ``error`` for each failure).
    """
    await _verify_store_ownership(db, store_id, user_id)

    succeeded = 0
    failed = 0
    errors = []

    for product_id in product_ids:
        try:
            result = await db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.store_id == store_id,
                )
            )
            product = result.scalar_one_or_none()
            if product is None:
                raise ValueError("Product not found in this store")

            for key, value in updates.items():
                if value is not None and hasattr(product, key):
                    setattr(product, key, value)

            succeeded += 1
        except Exception as e:
            failed += 1
            errors.append({
                "product_id": str(product_id),
                "error": str(e),
            })

    await db.flush()

    return {
        "total": len(product_ids),
        "succeeded": succeeded,
        "failed": failed,
        "errors": errors,
    }


async def bulk_delete_products(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_ids: list[uuid.UUID],
) -> dict:
    """Soft-delete multiple products by setting status to ``archived``.

    Processes each product independently. Products that don't exist or
    don't belong to the store are reported as errors.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_ids: List of product UUIDs to archive.

    Returns:
        A summary dict with ``total`` (int), ``succeeded`` (int),
        ``failed`` (int), and ``errors`` (list of dicts with ``product_id``
        and ``error`` for each failure).
    """
    await _verify_store_ownership(db, store_id, user_id)

    succeeded = 0
    failed = 0
    errors = []

    for product_id in product_ids:
        try:
            result = await db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.store_id == store_id,
                )
            )
            product = result.scalar_one_or_none()
            if product is None:
                raise ValueError("Product not found in this store")

            if product.status == ProductStatus.archived:
                raise ValueError("Product is already archived")

            product.status = ProductStatus.archived
            succeeded += 1
        except Exception as e:
            failed += 1
            errors.append({
                "product_id": str(product_id),
                "error": str(e),
            })

    await db.flush()

    return {
        "total": len(product_ids),
        "succeeded": succeeded,
        "failed": failed,
        "errors": errors,
    }


async def bulk_update_prices(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_ids: list[uuid.UUID],
    adjustment_type: str,
    adjustment_value: Decimal,
) -> dict:
    """Adjust prices for multiple products by percentage or fixed amount.

    Supports two adjustment types:
    - ``"percentage"``: e.g. ``+10`` means increase by 10%, ``-15`` means
      decrease by 15%.
    - ``"fixed"``: e.g. ``+5.00`` means add $5.00, ``-3.00`` means
      subtract $3.00.

    The resulting price is clamped to a minimum of $0.01 to prevent
    negative or zero prices.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_ids: List of product UUIDs to adjust.
        adjustment_type: Either ``"percentage"`` or ``"fixed"``.
        adjustment_value: The adjustment amount (positive to increase,
            negative to decrease).

    Returns:
        A summary dict with ``total`` (int), ``succeeded`` (int),
        ``failed`` (int), and ``errors`` (list of dicts with ``product_id``
        and ``error`` for each failure).

    Raises:
        ValueError: If the adjustment_type is not ``"percentage"`` or
            ``"fixed"``.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if adjustment_type not in ("percentage", "fixed"):
        raise ValueError(
            f"Invalid adjustment type: '{adjustment_type}'. "
            f"Must be 'percentage' or 'fixed'."
        )

    succeeded = 0
    failed = 0
    errors = []

    for product_id in product_ids:
        try:
            result = await db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.store_id == store_id,
                )
            )
            product = result.scalar_one_or_none()
            if product is None:
                raise ValueError("Product not found in this store")

            if adjustment_type == "percentage":
                # Calculate percentage adjustment
                multiplier = Decimal("1") + (adjustment_value / Decimal("100"))
                new_price = product.price * multiplier
            else:
                # Fixed adjustment
                new_price = product.price + adjustment_value

            # Ensure price doesn't go below minimum
            new_price = max(new_price, Decimal("0.01"))
            new_price = new_price.quantize(Decimal("0.01"))

            product.price = new_price
            succeeded += 1
        except Exception as e:
            failed += 1
            errors.append({
                "product_id": str(product_id),
                "error": str(e),
            })

    await db.flush()

    return {
        "total": len(product_ids),
        "succeeded": succeeded,
        "failed": failed,
        "errors": errors,
    }
