"""Customer account API router.

Provides endpoints for authenticated storefront customers to view their
order history and manage their wishlist. All endpoints require a valid
customer access token.

**For Developers:**
    Mounted at ``/api/v1/public/stores/{slug}/account``. Uses
    ``require_current_customer`` for auth and validates that the customer
    belongs to the store identified by the slug.

**For QA Engineers:**
    - All endpoints return 401 without a valid customer token.
    - Order listing only shows orders linked to this customer (not guest orders).
    - Wishlist add returns 409 for duplicates and 404 for invalid products.
    - Wishlist delete returns 404 if the item doesn't belong to the customer.

**For End Users:**
    View your past orders and manage your wishlist from your account.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_current_customer
from app.api.store_lookup import get_active_store
from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.order import OrderResponse, PaginatedOrderResponse
from app.schemas.public import PublicProductResponse
from app.schemas.wishlist import (
    PaginatedWishlistResponse,
    WishlistAddRequest,
    WishlistItemResponse,
)
from app.services import wishlist_service

router = APIRouter(
    prefix="/public/stores/{slug}/account", tags=["customer-account"]
)


@router.get("/orders", response_model=PaginatedOrderResponse)
async def list_customer_orders(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    customer: Customer = Depends(require_current_customer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedOrderResponse:
    """List the current customer's orders for this store.

    Args:
        slug: The store's URL slug.
        page: Page number (1-based).
        per_page: Items per page.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        PaginatedOrderResponse with the customer's orders.
    """
    store = await get_active_store(db, slug)

    # Verify customer belongs to this store
    if customer.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    base_filter = [
        Order.store_id == store.id,
        Order.customer_id == customer.id,
    ]

    count_result = await db.execute(
        select(func.count(Order.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Order)
        .where(*base_filter)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())
    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedOrderResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_customer_order(
    slug: str,
    order_id: uuid.UUID,
    customer: Customer = Depends(require_current_customer),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get a specific order belonging to the current customer.

    Args:
        slug: The store's URL slug.
        order_id: The order's UUID.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        OrderResponse with the order data.

    Raises:
        HTTPException: 404 if the order doesn't exist or doesn't belong
            to this customer.
    """
    store = await get_active_store(db, slug)

    if customer.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.store_id == store.id,
            Order.customer_id == customer.id,
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderResponse.model_validate(order)


@router.get("/wishlist", response_model=PaginatedWishlistResponse)
async def list_customer_wishlist(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    customer: Customer = Depends(require_current_customer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedWishlistResponse:
    """List the current customer's wishlist items.

    Args:
        slug: The store's URL slug.
        page: Page number (1-based).
        per_page: Items per page.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        PaginatedWishlistResponse with wishlisted products.
    """
    store = await get_active_store(db, slug)

    if customer.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    items, total = await wishlist_service.list_wishlist(
        db, customer.id, page, per_page
    )
    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedWishlistResponse(
        items=[
            WishlistItemResponse(
                id=item.id,
                customer_id=item.customer_id,
                product_id=item.product_id,
                created_at=item.created_at,
                product=PublicProductResponse.model_validate(item.product),
            )
            for item in items
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post(
    "/wishlist",
    response_model=WishlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_wishlist(
    slug: str,
    body: WishlistAddRequest,
    customer: Customer = Depends(require_current_customer),
    db: AsyncSession = Depends(get_db),
) -> WishlistItemResponse:
    """Add a product to the customer's wishlist.

    Args:
        slug: The store's URL slug.
        body: Product ID to add.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        WishlistItemResponse with the newly created wishlist item.

    Raises:
        HTTPException: 404 if the product doesn't exist or is not active.
        HTTPException: 409 if the product is already in the wishlist.
    """
    store = await get_active_store(db, slug)

    if customer.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    try:
        item = await wishlist_service.add_to_wishlist(
            db, customer.id, body.product_id, store.id
        )
    except ValueError as e:
        error_msg = str(e)
        if "already in wishlist" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        )

    # Commit now so the item is visible to subsequent requests.
    await db.commit()

    return WishlistItemResponse(
        id=item.id,
        customer_id=item.customer_id,
        product_id=item.product_id,
        created_at=item.created_at,
        product=PublicProductResponse.model_validate(item.product),
    )


@router.delete("/wishlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    slug: str,
    item_id: uuid.UUID,
    customer: Customer = Depends(require_current_customer),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an item from the customer's wishlist.

    Args:
        slug: The store's URL slug.
        item_id: The wishlist item's UUID.
        customer: The authenticated customer.
        db: Async database session.

    Raises:
        HTTPException: 404 if the item doesn't exist or doesn't belong
            to this customer.
    """
    store = await get_active_store(db, slug)

    if customer.store_id != store.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    try:
        await wishlist_service.remove_from_wishlist(db, customer.id, item_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Commit now so subsequent fetches see the deletion.
    await db.commit()
