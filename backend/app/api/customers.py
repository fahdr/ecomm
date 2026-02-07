"""Dashboard customer management API router.

Provides endpoints for store owners to view their customers and customer
order history from the dashboard.

**For Developers:**
    Mounted at ``/api/v1/stores/{store_id}/customers``. Uses
    ``get_current_user`` for authentication and ``customer_service``
    for all queries. Store ownership is verified for all operations.

**For QA Engineers:**
    - All endpoints require user (store owner) authentication.
    - ``GET /`` supports search by email or name.
    - ``GET /{customer_id}`` returns order_count and total_spent.
    - Store ownership mismatch returns 404.

**For End Users (Store Owners):**
    View your store's customer list and their order history from the dashboard.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.customer import (
    CustomerDetailResponse,
    CustomerResponse,
    PaginatedCustomerResponse,
)
from app.schemas.order import OrderResponse, PaginatedOrderResponse
from app.services import customer_service

router = APIRouter(
    prefix="/stores/{store_id}/customers", tags=["customers"]
)


@router.get("/", response_model=PaginatedCustomerResponse)
async def list_customers(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by email or name"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCustomerResponse:
    """List customers for a store with pagination and optional search.

    Args:
        store_id: The store's UUID.
        page: Page number (1-based).
        per_page: Items per page.
        search: Optional search term.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        PaginatedCustomerResponse with customers.

    Raises:
        HTTPException: 404 if the store doesn't exist or belongs to another user.
    """
    try:
        customers, total = await customer_service.list_customers(
            db, store_id, current_user.id, page, per_page, search
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedCustomerResponse(
        items=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer_detail(
    store_id: uuid.UUID,
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerDetailResponse:
    """Get customer details with order statistics.

    Args:
        store_id: The store's UUID.
        customer_id: The customer's UUID.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        CustomerDetailResponse with profile and order stats.

    Raises:
        HTTPException: 404 if the store or customer doesn't exist.
    """
    try:
        detail = await customer_service.get_customer_detail(
            db, store_id, current_user.id, customer_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    customer = detail["customer"]
    return CustomerDetailResponse(
        id=customer.id,
        store_id=customer.store_id,
        email=customer.email,
        first_name=customer.first_name,
        last_name=customer.last_name,
        phone=customer.phone,
        is_active=customer.is_active,
        created_at=customer.created_at,
        order_count=detail["order_count"],
        total_spent=detail["total_spent"],
    )


@router.get("/{customer_id}/orders", response_model=PaginatedOrderResponse)
async def list_customer_orders(
    store_id: uuid.UUID,
    customer_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedOrderResponse:
    """List orders for a specific customer.

    Args:
        store_id: The store's UUID.
        customer_id: The customer's UUID.
        page: Page number (1-based).
        per_page: Items per page.
        current_user: The authenticated store owner.
        db: Async database session.

    Returns:
        PaginatedOrderResponse with the customer's orders.

    Raises:
        HTTPException: 404 if the store doesn't exist or belongs to another user.
    """
    try:
        orders, total = await customer_service.list_customer_orders(
            db, store_id, current_user.id, customer_id, page, per_page
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedOrderResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
