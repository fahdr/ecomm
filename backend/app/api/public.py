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
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.schemas.public import (
    PaginatedPublicProductResponse,
    PublicProductResponse,
    PublicStoreResponse,
)

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
