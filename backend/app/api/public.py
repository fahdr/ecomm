"""Public API router for unauthenticated storefront endpoints.

Provides read-only access to store and product data for the public-facing
storefront. No authentication is required — these endpoints are consumed
by the Next.js storefront app via server-side rendering.

**For Developers:**
    The router is prefixed with ``/public`` (full path:
    ``/api/v1/public/...``). Stores are looked up by slug, not UUID.
    Products are scoped to a store slug and only active products are returned.

**For QA Engineers:**
    - Only stores with ``status == active`` are returned.
    - Only products with ``status == active`` are returned.
    - Paused and deleted stores return 404.
    - No ``user_id`` or ``cost`` is exposed in product responses.

**For End Users:**
    These endpoints power the public storefront. When you visit a store
    URL, the storefront fetches store and product data from here.
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import Order
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.schemas.order import CheckoutRequest, CheckoutResponse, OrderResponse
from app.schemas.public import (
    PaginatedPublicProductResponse,
    PublicProductResponse,
    PublicStoreResponse,
)
from app.services import order_service
from app.services.stripe_service import create_checkout_session

router = APIRouter(prefix="/public", tags=["public"])


async def _get_active_store(db: AsyncSession, slug: str) -> Store:
    """Retrieve an active store by slug or raise 404.

    Args:
        db: Async database session.
        slug: The store's URL slug.

    Returns:
        The Store ORM instance.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


@router.get("/stores/{slug}", response_model=PublicStoreResponse)
async def get_public_store(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicStoreResponse:
    """Retrieve a store by its slug for public display.

    Only active stores are returned. Paused or deleted stores will
    result in a 404 response.

    Args:
        slug: The URL-friendly store slug (e.g. ``my-awesome-store``).
        db: Async database session injected by FastAPI.

    Returns:
        PublicStoreResponse with the store's public-facing data.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    store = await _get_active_store(db, slug)
    return PublicStoreResponse.model_validate(store)


@router.get(
    "/stores/{slug}/products",
    response_model=PaginatedPublicProductResponse,
)
async def list_public_products(
    slug: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPublicProductResponse:
    """List active products for a store (public, paginated).

    Only products with ``status == active`` are returned. The response
    does not include ``cost`` or ``store_id``.

    Args:
        slug: The store's URL slug.
        page: Page number (1-based, default 1).
        per_page: Items per page (1–100, default 20).
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedPublicProductResponse with product items and pagination metadata.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    store = await _get_active_store(db, slug)

    base_filter = [
        Product.store_id == store.id,
        Product.status == ProductStatus.active,
    ]

    count_result = await db.execute(
        select(func.count(Product.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Product)
        .where(*base_filter)
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    products = list(result.scalars().all())

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedPublicProductResponse(
        items=[PublicProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/stores/{slug}/products/{product_slug}",
    response_model=PublicProductResponse,
)
async def get_public_product(
    slug: str,
    product_slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicProductResponse:
    """Retrieve a single active product by its slug (public).

    Args:
        slug: The store's URL slug.
        product_slug: The product's URL slug.
        db: Async database session injected by FastAPI.

    Returns:
        PublicProductResponse with the product's public-facing data.

    Raises:
        HTTPException: 404 if the store or product does not exist or is not active.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(Product).where(
            Product.store_id == store.id,
            Product.slug == product_slug,
            Product.status == ProductStatus.active,
        )
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return PublicProductResponse.model_validate(product)


@router.post(
    "/stores/{slug}/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    slug: str,
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a checkout session for a store.

    Validates cart items, creates a pending order, and returns a Stripe
    Checkout URL for the customer to complete payment. No authentication
    required — this is a public endpoint for store customers.

    Args:
        slug: The store's URL slug.
        body: Checkout request with customer email and cart items.
        db: Async database session injected by FastAPI.

    Returns:
        CheckoutResponse with the checkout URL, session ID, and order ID.

    Raises:
        HTTPException: 404 if the store doesn't exist or is not active.
        HTTPException: 400 if any cart item is invalid or out of stock.
    """
    store = await _get_active_store(db, slug)

    items = [
        {
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity,
        }
        for item in body.items
    ]

    try:
        order_items, total = await order_service.validate_and_build_order_items(
            db, store.id, items
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    stripe_data = create_checkout_session(
        order_id=None,  # Will be set after order creation
        items=order_items,
        customer_email=body.customer_email,
        store_name=store.name,
    )

    order = await order_service.create_order_from_checkout(
        db=db,
        store_id=store.id,
        customer_email=body.customer_email,
        items_data=order_items,
        total=total,
        stripe_session_id=stripe_data["session_id"],
    )

    return CheckoutResponse(
        checkout_url=stripe_data["checkout_url"],
        session_id=stripe_data["session_id"],
        order_id=order.id,
    )


@router.get(
    "/stores/{slug}/orders/{order_id}",
    response_model=OrderResponse,
)
async def get_public_order(
    slug: str,
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Retrieve an order by ID for the order confirmation page.

    This public endpoint allows customers to view their order status
    after checkout without requiring authentication.

    Args:
        slug: The store's URL slug.
        order_id: The order's UUID.
        db: Async database session injected by FastAPI.

    Returns:
        OrderResponse with the order data and items.

    Raises:
        HTTPException: 404 if the store or order doesn't exist.
    """
    store = await _get_active_store(db, slug)

    import uuid as uuid_mod
    try:
        oid = uuid_mod.UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    result = await db.execute(
        select(Order).where(
            Order.id == oid,
            Order.store_id == store.id,
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderResponse.model_validate(order)
