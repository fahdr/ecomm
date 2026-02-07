"""Wishlist business logic.

Handles adding, removing, and listing products in a customer's wishlist.

**For Developers:**
    All functions expect a valid customer_id. Product validation checks
    that the product is active and belongs to the same store as the customer.

**For QA Engineers:**
    - Adding a duplicate product returns ValueError (→ 409).
    - Adding a product from a different store returns ValueError (→ 404).
    - Adding an archived/draft product returns ValueError (→ 404).
    - Removing a nonexistent item returns ValueError (→ 404).

**For End Users:**
    Save products you like to your wishlist. You can view and manage
    your wishlist from your account page.
"""

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductStatus
from app.models.wishlist import WishlistItem


async def list_wishlist(
    db: AsyncSession,
    customer_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[WishlistItem], int]:
    """List wishlist items for a customer with pagination.

    Args:
        db: Async database session.
        customer_id: The customer's UUID.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (wishlist items list, total count).
    """
    base_filter = [WishlistItem.customer_id == customer_id]

    count_result = await db.execute(
        select(func.count(WishlistItem.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(WishlistItem)
        .where(*base_filter)
        .order_by(WishlistItem.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = list(result.scalars().all())

    return items, total


async def add_to_wishlist(
    db: AsyncSession,
    customer_id: uuid.UUID,
    product_id: uuid.UUID,
    store_id: uuid.UUID,
) -> WishlistItem:
    """Add a product to the customer's wishlist.

    Args:
        db: Async database session.
        customer_id: The customer's UUID.
        product_id: The product's UUID.
        store_id: The store's UUID (for validation).

    Returns:
        The newly created WishlistItem.

    Raises:
        ValueError: If the product doesn't exist, is not active, belongs
            to a different store, or is already in the wishlist.
    """
    # Validate product exists, is active, and belongs to the same store
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
            Product.status == ProductStatus.active,
        )
    )
    product = product_result.scalar_one_or_none()
    if product is None:
        raise ValueError("Product not found")

    # Check for duplicate
    existing_result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.customer_id == customer_id,
            WishlistItem.product_id == product_id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise ValueError("Product already in wishlist")

    item = WishlistItem(
        customer_id=customer_id,
        product_id=product_id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def remove_from_wishlist(
    db: AsyncSession,
    customer_id: uuid.UUID,
    item_id: uuid.UUID,
) -> None:
    """Remove an item from the customer's wishlist.

    Args:
        db: Async database session.
        customer_id: The customer's UUID (ownership check).
        item_id: The wishlist item's UUID.

    Raises:
        ValueError: If the item doesn't exist or doesn't belong
            to the customer.
    """
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.id == item_id,
            WishlistItem.customer_id == customer_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise ValueError("Wishlist item not found")

    await db.delete(item)
    await db.flush()
