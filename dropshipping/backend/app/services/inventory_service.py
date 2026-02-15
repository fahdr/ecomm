"""Inventory management business logic.

Handles warehouse CRUD, inventory level tracking, stock adjustments,
and reservation management for ecommerce and hybrid stores.

**For Developers:**
    All functions take ``store_id`` to enforce store scoping. The
    ``adjust_inventory`` function is the sole entry point for changing
    stock levels — it creates an InventoryAdjustment audit record for
    every change. ``reserve_stock`` and ``release_stock`` manage the
    reserved_quantity for order lifecycle.

**For QA Engineers:**
    - Creating an ecommerce store auto-creates a default warehouse.
    - Setting a warehouse as default unsets the previous default.
    - Inventory adjustments are immutable audit records.
    - Reserved quantity cannot exceed total quantity.
    - ``get_low_stock_items`` returns items at or below reorder_point.

**For Project Managers:**
    Core inventory operations enabling real-time stock management.
    Supports multi-warehouse, reorder alerts, and full audit trail.

**For End Users:**
    Manage your product stock across warehouses. Track every stock
    change with automatic audit logging.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    AdjustmentReason,
    InventoryAdjustment,
    InventoryLevel,
    Warehouse,
)
from app.models.product import ProductVariant
from app.models.store import Store


# ---------------------------------------------------------------------------
# Warehouse operations
# ---------------------------------------------------------------------------


async def create_warehouse(
    db: AsyncSession,
    store_id: uuid.UUID,
    name: str,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str = "US",
    zip_code: str | None = None,
    is_default: bool = False,
) -> Warehouse:
    """Create a new warehouse for a store.

    If ``is_default`` is True, unsets any existing default warehouse
    for the store first.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        name: Warehouse display name.
        address: Street address (optional).
        city: City name (optional).
        state: State/province (optional).
        country: ISO 3166-1 alpha-2 country code.
        zip_code: Postal code (optional).
        is_default: Whether this is the default warehouse.

    Returns:
        The newly created Warehouse ORM instance.
    """
    if is_default:
        await _unset_default_warehouse(db, store_id)

    warehouse = Warehouse(
        store_id=store_id,
        name=name,
        address=address,
        city=city,
        state=state,
        country=country,
        zip_code=zip_code,
        is_default=is_default,
    )
    db.add(warehouse)
    await db.flush()
    await db.refresh(warehouse)
    return warehouse


async def list_warehouses(
    db: AsyncSession, store_id: uuid.UUID
) -> list[Warehouse]:
    """List all warehouses for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.

    Returns:
        List of Warehouse ORM instances ordered by name.
    """
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.store_id == store_id)
        .order_by(Warehouse.is_default.desc(), Warehouse.name)
    )
    return list(result.scalars().all())


async def get_warehouse(
    db: AsyncSession, store_id: uuid.UUID, warehouse_id: uuid.UUID
) -> Warehouse:
    """Retrieve a single warehouse, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        warehouse_id: The warehouse's UUID.

    Returns:
        The Warehouse ORM instance.

    Raises:
        ValueError: If the warehouse doesn't exist or belongs to another store.
    """
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.store_id == store_id,
        )
    )
    warehouse = result.scalar_one_or_none()
    if warehouse is None:
        raise ValueError("Warehouse not found")
    return warehouse


async def update_warehouse(
    db: AsyncSession,
    store_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    **fields,
) -> Warehouse:
    """Update a warehouse's fields.

    If ``is_default`` is set to True, unsets the previous default first.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        warehouse_id: The warehouse's UUID.
        **fields: Keyword arguments for fields to update.

    Returns:
        The updated Warehouse ORM instance.

    Raises:
        ValueError: If the warehouse doesn't exist or belongs to another store.
    """
    warehouse = await get_warehouse(db, store_id, warehouse_id)

    if fields.get("is_default") is True:
        await _unset_default_warehouse(db, store_id)

    for key, value in fields.items():
        if value is not None:
            setattr(warehouse, key, value)

    await db.flush()
    await db.refresh(warehouse)
    return warehouse


async def delete_warehouse(
    db: AsyncSession, store_id: uuid.UUID, warehouse_id: uuid.UUID
) -> None:
    """Delete a warehouse and all its inventory levels.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        warehouse_id: The warehouse's UUID.

    Raises:
        ValueError: If the warehouse doesn't exist, belongs to another store,
            or is the only default warehouse.
    """
    warehouse = await get_warehouse(db, store_id, warehouse_id)

    if warehouse.is_default:
        raise ValueError("Cannot delete the default warehouse")

    await db.delete(warehouse)
    await db.flush()


async def _unset_default_warehouse(
    db: AsyncSession, store_id: uuid.UUID
) -> None:
    """Unset any existing default warehouse for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
    """
    await db.execute(
        update(Warehouse)
        .where(Warehouse.store_id == store_id, Warehouse.is_default.is_(True))
        .values(is_default=False)
    )


async def create_default_warehouse(
    db: AsyncSession, store_id: uuid.UUID
) -> Warehouse:
    """Create the default warehouse for a new ecommerce store.

    Called automatically when an ecommerce or hybrid store is created.

    Args:
        db: Async database session.
        store_id: The store's UUID.

    Returns:
        The newly created default Warehouse.
    """
    return await create_warehouse(
        db,
        store_id=store_id,
        name="Main Warehouse",
        is_default=True,
    )


# ---------------------------------------------------------------------------
# Inventory Level operations
# ---------------------------------------------------------------------------


async def set_inventory_level(
    db: AsyncSession,
    store_id: uuid.UUID,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int = 0,
    reorder_point: int = 0,
    reorder_quantity: int = 0,
) -> InventoryLevel:
    """Set the inventory level for a variant at a warehouse.

    Creates the InventoryLevel if it doesn't exist, or updates it.
    Also creates an adjustment record for the quantity change.

    Args:
        db: Async database session.
        store_id: The store's UUID (for warehouse ownership check).
        variant_id: The product variant's UUID.
        warehouse_id: The warehouse's UUID.
        quantity: Total quantity to set.
        reorder_point: Low-stock alert threshold.
        reorder_quantity: Suggested reorder amount.

    Returns:
        The created or updated InventoryLevel.

    Raises:
        ValueError: If the warehouse doesn't belong to the store.
    """
    await get_warehouse(db, store_id, warehouse_id)

    result = await db.execute(
        select(InventoryLevel).where(
            InventoryLevel.variant_id == variant_id,
            InventoryLevel.warehouse_id == warehouse_id,
        )
    )
    level = result.scalar_one_or_none()

    if level is None:
        level = InventoryLevel(
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity,
        )
        db.add(level)
        await db.flush()
        await db.refresh(level)

        if quantity > 0:
            adjustment = InventoryAdjustment(
                inventory_level_id=level.id,
                quantity_change=quantity,
                reason=AdjustmentReason.received,
                notes="Initial inventory set",
            )
            db.add(adjustment)
            await db.flush()
    else:
        old_qty = level.quantity
        level.quantity = quantity
        level.reorder_point = reorder_point
        level.reorder_quantity = reorder_quantity
        await db.flush()
        await db.refresh(level)

        delta = quantity - old_qty
        if delta != 0:
            adjustment = InventoryAdjustment(
                inventory_level_id=level.id,
                quantity_change=delta,
                reason=AdjustmentReason.correction,
                notes="Inventory level set via API",
            )
            db.add(adjustment)
            await db.flush()

    return level


async def adjust_inventory(
    db: AsyncSession,
    inventory_level_id: uuid.UUID,
    quantity_change: int,
    reason: AdjustmentReason,
    reference_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> InventoryLevel:
    """Apply a quantity adjustment to an inventory level.

    Creates an immutable adjustment record and updates the level's
    quantity accordingly.

    Args:
        db: Async database session.
        inventory_level_id: The inventory level to adjust.
        quantity_change: Signed delta to apply.
        reason: Categorized reason for the adjustment.
        reference_id: Optional UUID of related entity.
        notes: Optional human-readable notes.

    Returns:
        The updated InventoryLevel.

    Raises:
        ValueError: If the inventory level doesn't exist or if the
            adjustment would result in negative quantity.
    """
    result = await db.execute(
        select(InventoryLevel).where(InventoryLevel.id == inventory_level_id)
    )
    level = result.scalar_one_or_none()
    if level is None:
        raise ValueError("Inventory level not found")

    new_qty = level.quantity + quantity_change
    if new_qty < 0:
        raise ValueError(
            f"Cannot adjust: would result in negative quantity "
            f"(current={level.quantity}, change={quantity_change})"
        )

    level.quantity = new_qty

    adjustment = InventoryAdjustment(
        inventory_level_id=level.id,
        quantity_change=quantity_change,
        reason=reason,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(level)
    return level


async def get_inventory_levels(
    db: AsyncSession, store_id: uuid.UUID, warehouse_id: uuid.UUID | None = None
) -> list[InventoryLevel]:
    """List inventory levels for a store, optionally filtered by warehouse.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        warehouse_id: Optional warehouse filter.

    Returns:
        List of InventoryLevel ORM instances.
    """
    query = (
        select(InventoryLevel)
        .join(Warehouse, InventoryLevel.warehouse_id == Warehouse.id)
        .where(Warehouse.store_id == store_id)
    )
    if warehouse_id:
        query = query.where(InventoryLevel.warehouse_id == warehouse_id)

    result = await db.execute(query.order_by(InventoryLevel.created_at.desc()))
    return list(result.scalars().all())


async def get_inventory_level(
    db: AsyncSession, inventory_level_id: uuid.UUID
) -> InventoryLevel:
    """Retrieve a single inventory level by ID.

    Args:
        db: Async database session.
        inventory_level_id: The inventory level's UUID.

    Returns:
        The InventoryLevel ORM instance.

    Raises:
        ValueError: If the inventory level doesn't exist.
    """
    result = await db.execute(
        select(InventoryLevel).where(InventoryLevel.id == inventory_level_id)
    )
    level = result.scalar_one_or_none()
    if level is None:
        raise ValueError("Inventory level not found")
    return level


async def get_adjustments(
    db: AsyncSession,
    inventory_level_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> list[InventoryAdjustment]:
    """List adjustment history for an inventory level.

    Args:
        db: Async database session.
        inventory_level_id: The inventory level to get history for.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        List of InventoryAdjustment records ordered newest first.
    """
    offset = (page - 1) * page_size
    result = await db.execute(
        select(InventoryAdjustment)
        .where(InventoryAdjustment.inventory_level_id == inventory_level_id)
        .order_by(InventoryAdjustment.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Stock reservation (order lifecycle)
# ---------------------------------------------------------------------------


async def reserve_stock(
    db: AsyncSession,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    order_id: uuid.UUID | None = None,
) -> InventoryLevel:
    """Reserve stock for a pending order.

    Increments ``reserved_quantity`` without changing the total quantity.
    Creates an adjustment record with reason=reserved.

    Args:
        db: Async database session.
        variant_id: The variant to reserve stock for.
        warehouse_id: The warehouse to reserve from.
        quantity: Number of units to reserve.
        order_id: Optional order UUID for the reference.

    Returns:
        The updated InventoryLevel.

    Raises:
        ValueError: If insufficient available stock.
    """
    result = await db.execute(
        select(InventoryLevel).where(
            InventoryLevel.variant_id == variant_id,
            InventoryLevel.warehouse_id == warehouse_id,
        )
    )
    level = result.scalar_one_or_none()
    if level is None:
        raise ValueError("No inventory level found for this variant/warehouse")

    if level.available_quantity < quantity:
        raise ValueError(
            f"Insufficient stock: available={level.available_quantity}, "
            f"requested={quantity}"
        )

    level.reserved_quantity += quantity

    adjustment = InventoryAdjustment(
        inventory_level_id=level.id,
        quantity_change=-quantity,
        reason=AdjustmentReason.reserved,
        reference_id=order_id,
        notes=f"Reserved {quantity} units for order",
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(level)
    return level


async def release_stock(
    db: AsyncSession,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    order_id: uuid.UUID | None = None,
) -> InventoryLevel:
    """Release reserved stock (order cancelled or adjusted).

    Decrements ``reserved_quantity``. Does not change total quantity.

    Args:
        db: Async database session.
        variant_id: The variant to release stock for.
        warehouse_id: The warehouse.
        quantity: Number of units to release.
        order_id: Optional order UUID for the reference.

    Returns:
        The updated InventoryLevel.

    Raises:
        ValueError: If release quantity exceeds reserved quantity.
    """
    result = await db.execute(
        select(InventoryLevel).where(
            InventoryLevel.variant_id == variant_id,
            InventoryLevel.warehouse_id == warehouse_id,
        )
    )
    level = result.scalar_one_or_none()
    if level is None:
        raise ValueError("No inventory level found for this variant/warehouse")

    if level.reserved_quantity < quantity:
        raise ValueError(
            f"Cannot release more than reserved: "
            f"reserved={level.reserved_quantity}, release={quantity}"
        )

    level.reserved_quantity -= quantity

    adjustment = InventoryAdjustment(
        inventory_level_id=level.id,
        quantity_change=quantity,
        reason=AdjustmentReason.unreserved,
        reference_id=order_id,
        notes=f"Released {quantity} reserved units",
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(level)
    return level


async def fulfill_stock(
    db: AsyncSession,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    order_id: uuid.UUID | None = None,
) -> InventoryLevel:
    """Fulfill reserved stock (order shipped).

    Decrements both ``quantity`` and ``reserved_quantity``. Creates
    an adjustment record with reason=sold.

    Args:
        db: Async database session.
        variant_id: The variant to fulfill.
        warehouse_id: The warehouse.
        quantity: Number of units fulfilled.
        order_id: Optional order UUID.

    Returns:
        The updated InventoryLevel.

    Raises:
        ValueError: If insufficient reserved or total stock.
    """
    result = await db.execute(
        select(InventoryLevel).where(
            InventoryLevel.variant_id == variant_id,
            InventoryLevel.warehouse_id == warehouse_id,
        )
    )
    level = result.scalar_one_or_none()
    if level is None:
        raise ValueError("No inventory level found for this variant/warehouse")

    if level.reserved_quantity < quantity:
        raise ValueError("Cannot fulfill more than reserved")
    if level.quantity < quantity:
        raise ValueError("Cannot fulfill more than total quantity")

    level.quantity -= quantity
    level.reserved_quantity -= quantity

    adjustment = InventoryAdjustment(
        inventory_level_id=level.id,
        quantity_change=-quantity,
        reason=AdjustmentReason.sold,
        reference_id=order_id,
        notes=f"Fulfilled {quantity} units",
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(level)
    return level


# ---------------------------------------------------------------------------
# Summary & alerts
# ---------------------------------------------------------------------------


async def get_low_stock_items(
    db: AsyncSession, store_id: uuid.UUID
) -> list[InventoryLevel]:
    """Get all inventory levels at or below their reorder point.

    Args:
        db: Async database session.
        store_id: The store's UUID.

    Returns:
        List of low-stock InventoryLevel records.
    """
    result = await db.execute(
        select(InventoryLevel)
        .join(Warehouse, InventoryLevel.warehouse_id == Warehouse.id)
        .where(
            Warehouse.store_id == store_id,
            InventoryLevel.reorder_point > 0,
            (InventoryLevel.quantity - InventoryLevel.reserved_quantity)
            <= InventoryLevel.reorder_point,
        )
    )
    return list(result.scalars().all())


async def get_inventory_summary(
    db: AsyncSession, store_id: uuid.UUID
) -> dict:
    """Get aggregated inventory statistics for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.

    Returns:
        Dictionary with total_warehouses, total_variants_tracked,
        total_in_stock, total_reserved, low_stock_count.
    """
    # Count active warehouses
    wh_result = await db.execute(
        select(func.count(Warehouse.id)).where(
            Warehouse.store_id == store_id,
            Warehouse.is_active.is_(True),
        )
    )
    total_warehouses = wh_result.scalar() or 0

    # Aggregate inventory levels
    inv_result = await db.execute(
        select(
            func.count(InventoryLevel.id),
            func.coalesce(func.sum(InventoryLevel.quantity), 0),
            func.coalesce(func.sum(InventoryLevel.reserved_quantity), 0),
        )
        .join(Warehouse, InventoryLevel.warehouse_id == Warehouse.id)
        .where(Warehouse.store_id == store_id)
    )
    row = inv_result.one()
    total_tracked = row[0] or 0
    total_in_stock = row[1] or 0
    total_reserved = row[2] or 0

    # Count low-stock items
    low_stock = await get_low_stock_items(db, store_id)

    return {
        "total_warehouses": total_warehouses,
        "total_variants_tracked": total_tracked,
        "total_in_stock": int(total_in_stock),
        "total_reserved": int(total_reserved),
        "low_stock_count": len(low_stock),
    }
