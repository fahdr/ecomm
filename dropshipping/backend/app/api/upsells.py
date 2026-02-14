"""Upsell API router.

Provides CRUD endpoints for managing upsell and cross-sell rules. Store owners
can define product recommendations that appear on product pages and during
checkout to increase average order value.

**For Developers:**
    Admin routes are nested under ``/stores/{store_id}/upsells/...``.
    Public routes are under ``/public/stores/{slug}/products/{product_slug}/upsells``.
    The ``get_current_user`` dependency is used for admin authentication.
    Service functions in ``upsell_service`` handle all business logic.

**For QA Engineers:**
    - Admin endpoints return 401 without a valid token.
    - POST create returns 201 with the upsell rule data.
    - DELETE returns 204 with no content.
    - Public endpoint returns only active upsell recommendations.
    - Upsell types: ``upsell``, ``cross_sell``, ``bundle``.

**For End Users:**
    - Create upsell rules to recommend related or higher-value products.
    - Define cross-sell rules to suggest complementary products.
    - Build product bundles for discounted combined purchases.
    - Upsell suggestions appear on your storefront product pages.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.upsell import (
    CreateUpsellRequest,
    PaginatedUpsellResponse,
    UpdateUpsellRequest,
    UpsellResponse,
)

router = APIRouter(tags=["upsells"])


# ---------------------------------------------------------------------------
# Additional response schemas used only by the API layer
# ---------------------------------------------------------------------------


class PublicUpsellResponse(BaseModel):
    """Public-facing upsell recommendation (no admin fields).

    Attributes:
        target_product_id: The recommended product UUID.
        target_product_title: Product title.
        target_product_slug: Product slug for linking.
        target_product_price: Product price.
        target_product_image: Primary product image URL.
        upsell_type: Type of recommendation.
        title: Display title for the recommendation.
        description: Description text.
        discount_percentage: Optional discount percentage.
    """

    target_product_id: uuid.UUID
    target_product_title: str
    target_product_slug: str
    target_product_price: Decimal
    target_product_image: Optional[str] = None
    upsell_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    discount_percentage: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Admin route handlers
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/upsells",
    response_model=UpsellResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_upsell_endpoint(
    store_id: uuid.UUID,
    request: CreateUpsellRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpsellResponse:
    """Create a new upsell rule for a store.

    Defines a product recommendation that links a source product to a
    target product. The recommendation appears on the source product's
    page in the storefront.

    Args:
        store_id: The UUID of the store.
        request: Upsell rule creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        UpsellResponse with the newly created upsell rule data.

    Raises:
        HTTPException 404: If the store or products are not found.
        HTTPException 400: If source and target products are the same.
    """
    from app.services import upsell_service

    try:
        upsell = await upsell_service.create_upsell(
            db,
            store_id=store_id,
            user_id=current_user.id,
            **request.model_dump(),
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "same" in detail.lower() or "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return UpsellResponse.model_validate(upsell)


@router.get("/stores/{store_id}/upsells", response_model=PaginatedUpsellResponse)
async def list_upsells_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedUpsellResponse:
    """List upsell rules for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedUpsellResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import upsell_service

    try:
        upsells, total = await upsell_service.list_upsells(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedUpsellResponse(
        items=[UpsellResponse.model_validate(u) for u in upsells],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch(
    "/stores/{store_id}/upsells/{upsell_id}", response_model=UpsellResponse
)
async def update_upsell_endpoint(
    store_id: uuid.UUID,
    upsell_id: uuid.UUID,
    request: UpdateUpsellRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpsellResponse:
    """Update an upsell rule's fields (partial update).

    Only provided fields are updated.

    Args:
        store_id: The UUID of the store.
        upsell_id: The UUID of the upsell rule to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        UpsellResponse with the updated upsell rule data.

    Raises:
        HTTPException 404: If the store or upsell rule is not found.
    """
    from app.services import upsell_service

    try:
        upsell = await upsell_service.update_upsell(
            db,
            store_id=store_id,
            user_id=current_user.id,
            upsell_id=upsell_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return UpsellResponse.model_validate(upsell)


@router.delete(
    "/stores/{store_id}/upsells/{upsell_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_upsell_endpoint(
    store_id: uuid.UUID,
    upsell_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete an upsell rule.

    Args:
        store_id: The UUID of the store.
        upsell_id: The UUID of the upsell rule to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or upsell rule is not found.
    """
    from app.services import upsell_service

    try:
        await upsell_service.delete_upsell(
            db, store_id=store_id, user_id=current_user.id, upsell_id=upsell_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Public route handlers
# ---------------------------------------------------------------------------


@router.get(
    "/public/stores/{slug}/products/{product_slug}/upsells",
    response_model=list[PublicUpsellResponse],
)
async def get_public_product_upsells_endpoint(
    slug: str,
    product_slug: str,
    db: AsyncSession = Depends(get_db),
) -> list[PublicUpsellResponse]:
    """Get upsell recommendations for a product (public).

    Returns active upsell and cross-sell recommendations for a product
    on the storefront. Only active rules with active target products
    are included.

    Args:
        slug: The store's URL slug.
        product_slug: The product's URL slug.
        db: Async database session injected by FastAPI.

    Returns:
        List of PublicUpsellResponse objects sorted by priority.

    Raises:
        HTTPException 404: If the store or product is not found.
    """
    from app.services import upsell_service
    from app.models.store import Store, StoreStatus
    from app.models.product import Product, ProductStatus

    try:
        # Resolve store and product from slugs
        store_result = await db.execute(
            select(Store).where(
                Store.slug == slug,
                Store.status != StoreStatus.deleted,
            )
        )
        store = store_result.scalar_one_or_none()
        if store is None:
            raise ValueError("Store not found")

        product_result = await db.execute(
            select(Product).where(
                Product.store_id == store.id,
                Product.slug == product_slug,
                Product.status == ProductStatus.active,
            )
        )
        product = product_result.scalar_one_or_none()
        if product is None:
            raise ValueError("Product not found")

        upsells = await upsell_service.get_product_upsells(
            db, store_id=store.id, product_id=product.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return [PublicUpsellResponse.model_validate(u) for u in upsells]
