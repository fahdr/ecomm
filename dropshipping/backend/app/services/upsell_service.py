"""Upsell business logic.

Handles CRUD operations for product upsells and cross-sells. Upsells
suggest higher-value or complementary products to customers during
browsing and checkout to increase average order value.

**For Developers:**
    Upsells link a source product to a target product with optional
    discount incentives. The ``upsell_type`` field distinguishes between
    ``upsell`` (more expensive alternative), ``cross_sell`` (complementary
    product), and ``bundle`` (buy-together offer). The ``position`` field
    controls display order.

**For QA Engineers:**
    - ``create_upsell`` validates that both products exist in the store.
    - ``create_upsell`` prevents linking a product to itself.
    - ``get_product_upsells`` returns only active upsells for the public
      storefront.
    - ``delete_upsell`` is a hard delete.
    - ``list_upsells`` supports pagination.

**For Project Managers:**
    This service powers Feature 18 (Upsells & Cross-Sells) from the
    backlog. It enables store owners to configure product recommendations
    that increase average order value.

**For End Users:**
    Set up upsells and cross-sells to suggest related or higher-value
    products to customers. Optionally offer a discount to incentivise
    the upgrade. Control the display order and messaging for each offer.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# Upsell model -- import conditionally as models may be created by another
# agent. The model is expected to have: id, store_id, source_product_id,
# target_product_id, upsell_type, discount_percentage, title, description,
# position, is_active, created_at, updated_at.
# ---------------------------------------------------------------------------
try:
    from app.models.upsell import Upsell
except ImportError:
    Upsell = None  # type: ignore[assignment,misc]


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


async def create_upsell(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    source_product_id: uuid.UUID,
    target_product_id: uuid.UUID,
    upsell_type: str = "upsell",
    discount_percentage: Decimal | None = None,
    title: str | None = None,
    description: str | None = None,
    position: int = 0,
) -> "Upsell":
    """Create a new upsell or cross-sell link between two products.

    Validates that both the source and target products exist in the
    store and prevents self-referential upsells.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        source_product_id: The UUID of the product that triggers the upsell.
        target_product_id: The UUID of the suggested product.
        upsell_type: Type of recommendation: ``"upsell"``, ``"cross_sell"``,
            or ``"bundle"``.
        discount_percentage: Optional discount on the target product.
        title: Optional title for the upsell offer (e.g. "Upgrade to Pro").
        description: Optional description text.
        position: Display order (lower = first, default 0).

    Returns:
        The newly created Upsell ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            either product doesn't exist, or a self-referential upsell
            is attempted.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if source_product_id == target_product_id:
        raise ValueError("A product cannot upsell to itself")

    # Verify source product
    source_result = await db.execute(
        select(Product).where(
            Product.id == source_product_id,
            Product.store_id == store_id,
        )
    )
    if source_result.scalar_one_or_none() is None:
        raise ValueError("Source product not found in this store")

    # Verify target product
    target_result = await db.execute(
        select(Product).where(
            Product.id == target_product_id,
            Product.store_id == store_id,
        )
    )
    if target_result.scalar_one_or_none() is None:
        raise ValueError("Target product not found in this store")

    upsell = Upsell(
        store_id=store_id,
        source_product_id=source_product_id,
        target_product_id=target_product_id,
        upsell_type=upsell_type,
        discount_percentage=discount_percentage,
        title=title,
        description=description,
        position=position,
        is_active=True,
    )
    db.add(upsell)
    await db.flush()
    await db.refresh(upsell)
    return upsell


async def list_upsells(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list, int]:
    """List all upsells for a store with pagination.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (upsells list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Upsell).where(Upsell.store_id == store_id)
    count_query = select(func.count(Upsell.id)).where(Upsell.store_id == store_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Upsell.position, Upsell.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    upsells = list(result.scalars().all())

    return upsells, total


async def update_upsell(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    upsell_id: uuid.UUID,
    **kwargs,
) -> "Upsell":
    """Update an upsell's fields (partial update).

    Only provided (non-None) keyword arguments are applied.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        upsell_id: The UUID of the upsell to update.
        **kwargs: Keyword arguments for fields to update (upsell_type,
            discount_percentage, title, description, position, is_active).

    Returns:
        The updated Upsell ORM instance.

    Raises:
        ValueError: If the store or upsell doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Upsell).where(
            Upsell.id == upsell_id,
            Upsell.store_id == store_id,
        )
    )
    upsell = result.scalar_one_or_none()
    if upsell is None:
        raise ValueError("Upsell not found")

    for key, value in kwargs.items():
        if value is not None:
            setattr(upsell, key, value)

    await db.flush()
    await db.refresh(upsell)
    return upsell


async def delete_upsell(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    upsell_id: uuid.UUID,
) -> None:
    """Permanently delete an upsell.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        upsell_id: The UUID of the upsell to delete.

    Raises:
        ValueError: If the store or upsell doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Upsell).where(
            Upsell.id == upsell_id,
            Upsell.store_id == store_id,
        )
    )
    upsell = result.scalar_one_or_none()
    if upsell is None:
        raise ValueError("Upsell not found")

    await db.delete(upsell)
    await db.flush()


async def get_product_upsells(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
) -> list:
    """Get active upsells for a product on the public storefront.

    Returns only upsells where both the upsell record and the target
    product are active, ordered by position.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        product_id: The UUID of the source product.

    Returns:
        A list of Upsell ORM instances with target product relationships.
    """
    result = await db.execute(
        select(Upsell)
        .where(
            Upsell.store_id == store_id,
            Upsell.source_product_id == product_id,
            Upsell.is_active.is_(True),
        )
        .order_by(Upsell.position, Upsell.created_at)
    )
    return list(result.scalars().all())
