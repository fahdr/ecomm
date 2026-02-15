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
    FulfillOrderRequest,
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
        items=[OrderResponse.from_order(o) for o in orders],
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

    return OrderResponse.from_order(order)


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
            db,
            store_id,
            current_user.id,
            order_id,
            new_status=body.status,
            notes=body.notes if body.notes is not None else ...,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return OrderResponse.from_order(order)


@router.post("/{order_id}/fulfill", response_model=OrderResponse)
async def fulfill_order(
    store_id: uuid.UUID,
    order_id: uuid.UUID,
    body: FulfillOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """Mark an order as shipped with tracking information.

    Transitions a paid order to shipped status and stores the tracking
    number and carrier.

    Args:
        store_id: The store's UUID.
        order_id: The order's UUID.
        body: Request body with tracking_number and optional carrier.
        db: Async database session injected by FastAPI.
        current_user: Authenticated user from JWT.

    Returns:
        OrderResponse with the updated order data.

    Raises:
        HTTPException: 404 if not found, 400 if order is not in paid status.
    """
    try:
        order = await order_service.fulfill_order(
            db, store_id, current_user.id, order_id,
            body.tracking_number, body.carrier,
        )
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_400_BAD_REQUEST if "Cannot fulfill" in detail else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=detail)

    # Dispatch background tasks for shipped notifications
    from app.tasks.email_tasks import send_order_shipped
    from app.tasks.notification_tasks import create_order_notification
    from app.tasks.webhook_tasks import dispatch_webhook_event

    send_order_shipped.delay(str(order_id), body.tracking_number)
    dispatch_webhook_event.delay(str(store_id), "order.shipped", {
        "order_id": str(order_id),
        "tracking_number": body.tracking_number,
        "carrier": body.carrier,
    })
    create_order_notification.delay(str(store_id), str(order_id), "order_shipped")

    # Notify connected services about the shipment
    from app.services.bridge_service import fire_platform_event
    fire_platform_event(
        user_id=current_user.id,
        store_id=store_id,
        event="order.shipped",
        resource_id=order_id,
        resource_type="order",
        payload={
            "order_id": str(order_id),
            "tracking_number": body.tracking_number,
            "carrier": body.carrier,
        },
    )

    return OrderResponse.from_order(order)


@router.post("/{order_id}/deliver", response_model=OrderResponse)
async def deliver_order(
    store_id: uuid.UUID,
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """Mark a shipped order as delivered.

    Transitions a shipped order to delivered status.

    Args:
        store_id: The store's UUID.
        order_id: The order's UUID.
        db: Async database session injected by FastAPI.
        current_user: Authenticated user from JWT.

    Returns:
        OrderResponse with the updated order data.

    Raises:
        HTTPException: 404 if not found, 400 if order is not in shipped status.
    """
    try:
        order = await order_service.deliver_order(
            db, store_id, current_user.id, order_id,
        )
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_400_BAD_REQUEST if "Cannot deliver" in detail else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=detail)

    # Dispatch background tasks for delivery notifications
    from app.tasks.email_tasks import send_order_delivered
    from app.tasks.notification_tasks import create_order_notification
    from app.tasks.webhook_tasks import dispatch_webhook_event

    send_order_delivered.delay(str(order_id))
    dispatch_webhook_event.delay(str(store_id), "order.delivered", {
        "order_id": str(order_id),
    })
    create_order_notification.delay(str(store_id), str(order_id), "order_delivered")

    return OrderResponse.from_order(order)
