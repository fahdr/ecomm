"""Orders API router for store owners.

Provides authenticated endpoints for store owners to view and manage
orders placed on their stores.

**For Developers:**
    The router is prefixed with ``/stores/{store_id}/orders`` (full path:
    ``/api/v1/stores/{store_id}/orders``). All endpoints require JWT
    authentication and verify store ownership.

**For QA Engineers:**
    - Only the store owner can view orders for their store.
    - Orders are listed in reverse chronological order.
    - Pagination uses ``page`` and ``per_page`` query parameters.
    - Status can be filtered with the ``status`` query parameter.
    - Order status can be updated via PATCH.

**For End Users:**
    View all orders placed on your store from the dashboard. You can
    filter by status and update order statuses as you process them.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import (
    OrderResponse,
    PaginatedOrderResponse,
    UpdateOrderStatusRequest,
)
from app.services import order_service

router = APIRouter(
    prefix="/stores/{store_id}/orders",
    tags=["orders"],
)


@router.get("", response_model=PaginatedOrderResponse)
async def list_orders(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: OrderStatus | None = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedOrderResponse:
    """List orders for a store with pagination.

    Args:
        store_id: The store's UUID.
        page: Page number (1-based, default 1).
        per_page: Items per page (1–100, default 20).
        status_filter: Optional order status filter.
        db: Async database session injected by FastAPI.
        current_user: Authenticated user from JWT.

    Returns:
        PaginatedOrderResponse with order items and pagination metadata.

    Raises:
        HTTPException: 404 if the store doesn't exist or doesn't belong
            to the current user.
    """
    try:
        orders, total = await order_service.list_orders(
            db, store_id, current_user.id, page, per_page, status_filter
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedOrderResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    store_id: uuid.UUID,
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """Retrieve a single order by ID.

    Args:
        store_id: The store's UUID.
        order_id: The order's UUID.
        db: Async database session injected by FastAPI.
        current_user: Authenticated user from JWT.

    Returns:
        OrderResponse with the order's data and items.

    Raises:
        HTTPException: 404 if the store or order doesn't exist,
            or the store doesn't belong to the current user.
    """
    try:
        order = await order_service.get_order(
            db, store_id, current_user.id, order_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return OrderResponse.model_validate(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order_status(
    store_id: uuid.UUID,
    order_id: uuid.UUID,
    body: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """Update an order's status.

    Args:
        store_id: The store's UUID.
        order_id: The order's UUID.
        body: Request body with the new status.
        db: Async database session injected by FastAPI.
        current_user: Authenticated user from JWT.

    Returns:
        OrderResponse with the updated order data.

    Raises:
        HTTPException: 404 if the store or order doesn't exist,
            or the store doesn't belong to the current user.
    """
    try:
        order = await order_service.update_order_status(
            db, store_id, current_user.id, order_id, body.status
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return OrderResponse.model_validate(order)
