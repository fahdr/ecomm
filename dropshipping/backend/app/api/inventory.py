"""Inventory management API router.

Provides warehouse CRUD and inventory level management endpoints for
ecommerce and hybrid stores. All endpoints are scoped under
``/stores/{store_id}/`` to enforce store ownership.

**For Developers:**
    The router is mounted at ``/stores/{store_id}`` — warehouse endpoints
    use ``/warehouses/*`` and inventory endpoints use ``/inventory/*``.
    All endpoints verify store ownership via ``get_current_user``.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - Store ownership is verified (404 for non-owned stores).
    - Warehouse and inventory CRUD follows standard REST patterns.
    - Deleting the default warehouse returns 400.
    - Adjusting below zero quantity returns 400.

**For Project Managers:**
    These endpoints power the inventory management dashboard for
    ecommerce mode stores. Warehouses and stock levels are managed
    entirely through this API.

**For End Users:**
    Manage your warehouses and product stock levels. Set reorder
    points for automatic low-stock alerts. View adjustment history
    for full audit trails.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.inventory import (
    AdjustInventoryRequest,
    CreateWarehouseRequest,
    InventoryAdjustmentResponse,
    InventoryLevelResponse,
    InventorySummaryResponse,
    SetInventoryRequest,
    UpdateWarehouseRequest,
    WarehouseResponse,
)
from app.services.inventory_service import (
    adjust_inventory,
    create_warehouse,
    delete_warehouse,
    get_adjustments,
    get_inventory_level,
    get_inventory_levels,
    get_inventory_summary,
    get_low_stock_items,
    get_warehouse,
    list_warehouses,
    set_inventory_level,
    update_warehouse,
)
from app.services.store_service import get_store

router = APIRouter(tags=["inventory"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _verify_store_access(
    db: AsyncSession, user_id: uuid.UUID, store_id: uuid.UUID
):
    """Verify the user owns the store. Raises HTTPException 404 on failure.

    Args:
        db: Async database session.
        user_id: The authenticated user's UUID.
        store_id: The store's UUID to verify.
    """
    try:
        await get_store(db, user_id, store_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )


# ---------------------------------------------------------------------------
# Warehouse endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_warehouse_endpoint(
    store_id: uuid.UUID,
    request: CreateWarehouseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WarehouseResponse:
    """Create a new warehouse for a store.

    Args:
        store_id: The store's UUID.
        request: Warehouse creation payload.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The newly created warehouse.
    """
    await _verify_store_access(db, current_user.id, store_id)
    warehouse = await create_warehouse(
        db,
        store_id=store_id,
        name=request.name,
        address=request.address,
        city=request.city,
        state=request.state,
        country=request.country,
        zip_code=request.zip_code,
        is_default=request.is_default,
    )
    return WarehouseResponse.model_validate(warehouse)


@router.get(
    "/stores/{store_id}/warehouses",
    response_model=list[WarehouseResponse],
)
async def list_warehouses_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WarehouseResponse]:
    """List all warehouses for a store.

    Args:
        store_id: The store's UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of warehouses ordered by default status then name.
    """
    await _verify_store_access(db, current_user.id, store_id)
    warehouses = await list_warehouses(db, store_id)
    return [WarehouseResponse.model_validate(w) for w in warehouses]


@router.get(
    "/stores/{store_id}/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
)
async def get_warehouse_endpoint(
    store_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WarehouseResponse:
    """Retrieve a single warehouse.

    Args:
        store_id: The store's UUID.
        warehouse_id: The warehouse's UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The warehouse data.
    """
    await _verify_store_access(db, current_user.id, store_id)
    try:
        warehouse = await get_warehouse(db, store_id, warehouse_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseResponse.model_validate(warehouse)


@router.patch(
    "/stores/{store_id}/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
)
async def update_warehouse_endpoint(
    store_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    request: UpdateWarehouseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WarehouseResponse:
    """Update a warehouse's details.

    Args:
        store_id: The store's UUID.
        warehouse_id: The warehouse's UUID.
        request: Partial update payload.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The updated warehouse.
    """
    await _verify_store_access(db, current_user.id, store_id)
    try:
        warehouse = await update_warehouse(
            db,
            store_id=store_id,
            warehouse_id=warehouse_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return WarehouseResponse.model_validate(warehouse)


@router.delete(
    "/stores/{store_id}/warehouses/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_warehouse_endpoint(
    store_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a warehouse and all its inventory levels.

    Cannot delete the default warehouse — reassign default first.

    Args:
        store_id: The store's UUID.
        warehouse_id: The warehouse's UUID.
        current_user: Authenticated user.
        db: Database session.
    """
    await _verify_store_access(db, current_user.id, store_id)
    try:
        await delete_warehouse(db, store_id, warehouse_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Inventory Level endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/inventory",
    response_model=InventoryLevelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_inventory_endpoint(
    store_id: uuid.UUID,
    request: SetInventoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryLevelResponse:
    """Set inventory level for a variant at a warehouse.

    Creates or updates the inventory level record. Generates an
    adjustment record for any quantity change.

    Args:
        store_id: The store's UUID.
        request: Inventory set payload with variant_id, warehouse_id, quantity.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The created or updated inventory level.
    """
    await _verify_store_access(db, current_user.id, store_id)
    try:
        level = await set_inventory_level(
            db,
            store_id=store_id,
            variant_id=request.variant_id,
            warehouse_id=request.warehouse_id,
            quantity=request.quantity,
            reorder_point=request.reorder_point,
            reorder_quantity=request.reorder_quantity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return InventoryLevelResponse.model_validate(level)


@router.get(
    "/stores/{store_id}/inventory",
    response_model=list[InventoryLevelResponse],
)
async def list_inventory_endpoint(
    store_id: uuid.UUID,
    warehouse_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryLevelResponse]:
    """List inventory levels for a store, optionally filtered by warehouse.

    Args:
        store_id: The store's UUID.
        warehouse_id: Optional warehouse filter.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of inventory levels.
    """
    await _verify_store_access(db, current_user.id, store_id)
    levels = await get_inventory_levels(db, store_id, warehouse_id)
    return [InventoryLevelResponse.model_validate(lv) for lv in levels]


@router.post(
    "/stores/{store_id}/inventory/{inventory_level_id}/adjust",
    response_model=InventoryLevelResponse,
)
async def adjust_inventory_endpoint(
    store_id: uuid.UUID,
    inventory_level_id: uuid.UUID,
    request: AdjustInventoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryLevelResponse:
    """Apply a quantity adjustment to an inventory level.

    Args:
        store_id: The store's UUID.
        inventory_level_id: The inventory level to adjust.
        request: Adjustment payload with quantity_change, reason, notes.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        The updated inventory level.
    """
    await _verify_store_access(db, current_user.id, store_id)
    try:
        level = await adjust_inventory(
            db,
            inventory_level_id=inventory_level_id,
            quantity_change=request.quantity_change,
            reason=request.reason,
            reference_id=request.reference_id,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return InventoryLevelResponse.model_validate(level)


@router.get(
    "/stores/{store_id}/inventory/{inventory_level_id}/adjustments",
    response_model=list[InventoryAdjustmentResponse],
)
async def list_adjustments_endpoint(
    store_id: uuid.UUID,
    inventory_level_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryAdjustmentResponse]:
    """List adjustment history for an inventory level.

    Args:
        store_id: The store's UUID.
        inventory_level_id: The inventory level.
        page: Page number.
        page_size: Items per page.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of adjustment records ordered newest first.
    """
    await _verify_store_access(db, current_user.id, store_id)
    adjustments = await get_adjustments(db, inventory_level_id, page, page_size)
    return [InventoryAdjustmentResponse.model_validate(a) for a in adjustments]


# ---------------------------------------------------------------------------
# Summary & Alerts
# ---------------------------------------------------------------------------


@router.get(
    "/stores/{store_id}/inventory/summary",
    response_model=InventorySummaryResponse,
)
async def inventory_summary_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventorySummaryResponse:
    """Get aggregated inventory statistics for a store.

    Args:
        store_id: The store's UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Summary with warehouse count, total stock, reserved stock,
        and low-stock item count.
    """
    await _verify_store_access(db, current_user.id, store_id)
    summary = await get_inventory_summary(db, store_id)
    return InventorySummaryResponse(**summary)


@router.get(
    "/stores/{store_id}/inventory/low-stock",
    response_model=list[InventoryLevelResponse],
)
async def low_stock_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryLevelResponse]:
    """Get inventory levels that are at or below their reorder point.

    Args:
        store_id: The store's UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of low-stock inventory levels.
    """
    await _verify_store_access(db, current_user.id, store_id)
    items = await get_low_stock_items(db, store_id)
    return [InventoryLevelResponse.model_validate(item) for item in items]
