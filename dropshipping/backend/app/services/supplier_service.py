"""Supplier business logic.

Handles CRUD operations for dropshipping suppliers and product-supplier
linkages. Suppliers represent the upstream companies that ship products
directly to customers on behalf of the store owner.

**For Developers:**
    All functions take ``store_id`` and ``user_id`` to enforce store
    ownership. The ``product_suppliers`` junction table stores per-supplier
    metadata (cost, SKU, source URL) for each product. The ``is_primary``
    flag on ``ProductSupplier`` marks the default fulfillment source.

**For QA Engineers:**
    - ``create_supplier`` defaults to ``active`` status.
    - ``link_product_supplier`` validates that both the product and supplier
      exist and belong to the same store.
    - When ``is_primary`` is True, any existing primary link for the same
      product is demoted.
    - ``delete_supplier`` is a hard delete; cascade removes product links.
    - ``list_suppliers`` supports optional status filtering.

**For Project Managers:**
    This service powers Feature 10 (Supplier Management) from the backlog.
    It lets store owners track supplier contacts, reliability, and per-product
    sourcing costs for profit calculation.

**For End Users:**
    Manage the suppliers who fulfill your orders. Track contact information,
    shipping times, and per-product costs to optimise your margins and
    identify reliable sourcing partners.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.store import Store, StoreStatus
from app.models.supplier import ProductSupplier, Supplier, SupplierStatus


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


async def create_supplier(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    website: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    notes: str | None = None,
) -> Supplier:
    """Create a new supplier for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        name: Display name of the supplier (e.g. company name).
        website: Optional URL for the supplier's website or platform.
        contact_email: Optional email address for communications.
        contact_phone: Optional phone number.
        notes: Optional free-text notes about the supplier.

    Returns:
        The newly created Supplier ORM instance.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    supplier = Supplier(
        store_id=store_id,
        name=name,
        website=website,
        contact_email=contact_email,
        contact_phone=contact_phone,
        notes=notes,
        status=SupplierStatus.active,
    )
    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)
    return supplier


async def list_suppliers(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    status_filter: SupplierStatus | None = None,
) -> tuple[list[Supplier], int]:
    """List suppliers for a store with pagination and optional status filtering.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        status_filter: Optional status to filter by (active, inactive,
            blacklisted).

    Returns:
        A tuple of (suppliers list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Supplier).where(Supplier.store_id == store_id)
    count_query = select(func.count(Supplier.id)).where(Supplier.store_id == store_id)

    if status_filter is not None:
        query = query.where(Supplier.status == status_filter)
        count_query = count_query.where(Supplier.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Supplier.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    suppliers = list(result.scalars().all())

    return suppliers, total


async def get_supplier(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Supplier:
    """Retrieve a single supplier, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        supplier_id: The UUID of the supplier to retrieve.

    Returns:
        The Supplier ORM instance with relationships loaded.

    Raises:
        ValueError: If the store or supplier doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.store_id == store_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if supplier is None:
        raise ValueError("Supplier not found")
    return supplier


async def update_supplier(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    supplier_id: uuid.UUID,
    **kwargs,
) -> Supplier:
    """Update a supplier's fields (partial update).

    Only provided (non-None) keyword arguments are applied.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        supplier_id: The UUID of the supplier to update.
        **kwargs: Keyword arguments for fields to update (name, website,
            contact_email, contact_phone, notes, status, avg_shipping_days,
            reliability_score).

    Returns:
        The updated Supplier ORM instance.

    Raises:
        ValueError: If the store or supplier doesn't exist, or the store
            belongs to another user.
    """
    supplier = await get_supplier(db, store_id, user_id, supplier_id)

    for key, value in kwargs.items():
        if value is not None:
            setattr(supplier, key, value)

    await db.flush()
    await db.refresh(supplier)
    return supplier


async def delete_supplier(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> None:
    """Permanently delete a supplier and all product links.

    Cascade deletes will remove associated ``ProductSupplier`` records.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        supplier_id: The UUID of the supplier to delete.

    Raises:
        ValueError: If the store or supplier doesn't exist, or the store
            belongs to another user.
    """
    supplier = await get_supplier(db, store_id, user_id, supplier_id)
    await db.delete(supplier)
    await db.flush()


async def link_product_supplier(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
    supplier_url: str | None = None,
    supplier_sku: str | None = None,
    supplier_cost: Decimal = Decimal("0.00"),
    is_primary: bool = False,
) -> ProductSupplier:
    """Link a product to a supplier with sourcing metadata.

    If ``is_primary`` is True, any existing primary link for the same
    product is demoted to non-primary. Validates that both the product
    and supplier exist and belong to the store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_id: The UUID of the product.
        supplier_id: The UUID of the supplier.
        supplier_url: Optional URL to the product on the supplier's site.
        supplier_sku: Optional supplier-side SKU or item identifier.
        supplier_cost: The cost charged by the supplier (default 0.00).
        is_primary: Whether this is the default supplier for the product.

    Returns:
        The newly created ProductSupplier link record.

    Raises:
        ValueError: If the store, product, or supplier doesn't exist, the
            store belongs to another user, or the link already exists.
    """
    await _verify_store_ownership(db, store_id, user_id)

    # Verify product belongs to the store
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
        )
    )
    if product_result.scalar_one_or_none() is None:
        raise ValueError("Product not found in this store")

    # Verify supplier belongs to the store
    supplier_result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.store_id == store_id,
        )
    )
    if supplier_result.scalar_one_or_none() is None:
        raise ValueError("Supplier not found in this store")

    # Check for existing link
    existing = await db.execute(
        select(ProductSupplier).where(
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("This product is already linked to this supplier")

    # Demote existing primary if setting a new one
    if is_primary:
        existing_primary = await db.execute(
            select(ProductSupplier).where(
                ProductSupplier.product_id == product_id,
                ProductSupplier.is_primary.is_(True),
            )
        )
        for link in existing_primary.scalars().all():
            link.is_primary = False

    product_supplier = ProductSupplier(
        product_id=product_id,
        supplier_id=supplier_id,
        supplier_url=supplier_url,
        supplier_sku=supplier_sku,
        supplier_cost=supplier_cost,
        is_primary=is_primary,
    )
    db.add(product_supplier)
    await db.flush()
    await db.refresh(product_supplier)
    return product_supplier


async def unlink_product_supplier(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> None:
    """Remove the link between a product and a supplier.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_id: The UUID of the product.
        supplier_id: The UUID of the supplier.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or the product-supplier link doesn't exist.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(ProductSupplier).where(
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise ValueError("Product-supplier link not found")

    await db.delete(link)
    await db.flush()


async def get_product_suppliers(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
) -> list[ProductSupplier]:
    """Get all suppliers linked to a specific product.

    Does not require ownership verification as it may be used internally
    for order fulfillment and profit calculations.

    Args:
        db: Async database session.
        store_id: The store's UUID (for scoping verification).
        product_id: The UUID of the product.

    Returns:
        A list of ProductSupplier link records with supplier relationships
        loaded, ordered with the primary supplier first.
    """
    # Verify product belongs to the store
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
        )
    )
    if product_result.scalar_one_or_none() is None:
        raise ValueError("Product not found in this store")

    result = await db.execute(
        select(ProductSupplier)
        .where(ProductSupplier.product_id == product_id)
        .order_by(ProductSupplier.is_primary.desc(), ProductSupplier.created_at)
    )
    return list(result.scalars().all())
