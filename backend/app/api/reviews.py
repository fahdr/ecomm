"""Reviews API router.

Provides endpoints for managing product reviews. Store owners can list,
moderate (approve/reject), and view review statistics. Public endpoints
allow customers to submit and view approved reviews.

**For Developers:**
    Admin routes are nested under ``/stores/{store_id}/reviews/...`` and
    ``/stores/{store_id}/products/{product_id}/reviews/...``.
    Public routes are under ``/public/stores/{slug}/products/{product_slug}/reviews``.
    The ``get_current_user`` dependency is used for admin authentication.

**For QA Engineers:**
    - Admin endpoints return 401 without a valid token.
    - Public GET only returns approved reviews.
    - Public POST requires customer_email and validates the customer has purchased.
    - Review stats include average rating, count, and distribution.
    - PATCH status accepts ``approved``, ``rejected``, ``pending``.

**For End Users:**
    - Customers can leave reviews on products they have purchased.
    - Store owners moderate reviews from the dashboard.
    - Review statistics help customers make purchase decisions.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.review import (
    CreateReviewRequest,
    PaginatedReviewResponse,
    ReviewResponse,
    ReviewStatsResponse,
    UpdateReviewStatusRequest,
)

router = APIRouter(tags=["reviews"])


# ---------------------------------------------------------------------------
# Local schemas (not present in app.schemas.review)
# ---------------------------------------------------------------------------


class PublicReviewResponse(BaseModel):
    """Public-facing review response (no admin fields).

    Attributes:
        id: Review identifier.
        customer_name: Reviewer's display name.
        rating: Star rating (1-5).
        title: Optional review title.
        body: Review text body.
        is_verified_purchase: Whether the reviewer purchased the product.
        created_at: When the review was submitted.
    """

    id: uuid.UUID
    customer_name: Optional[str] = None
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    is_verified_purchase: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPublicReviewResponse(BaseModel):
    """Paginated list of public reviews.

    Attributes:
        items: List of public review records.
        total: Total number of approved reviews.
        page: Current page number.
        per_page: Number of items per page.
        pages: Total number of pages.
        average_rating: Average star rating for this product.
    """

    items: list[PublicReviewResponse]
    total: int
    page: int
    per_page: int
    pages: int
    average_rating: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# Admin route handlers (store-scoped, authenticated)
# ---------------------------------------------------------------------------


@router.get(
    "/stores/{store_id}/reviews",
    response_model=PaginatedReviewResponse,
)
async def list_store_reviews_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    review_status: Optional[str] = Query(
        None, alias="status", description="Filter by moderation status"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedReviewResponse:
    """List all reviews for a store (admin).

    Returns all reviews across all products in the store, filterable
    by moderation status. Used by store owners to manage reviews.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        review_status: Optional status filter (pending, approved, rejected).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedReviewResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import review_service

    try:
        reviews, total = await review_service.list_reviews(
            db,
            store_id=store_id,
            status_filter=review_status,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedReviewResponse(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/stores/{store_id}/products/{product_id}/reviews",
    response_model=PaginatedReviewResponse,
)
async def list_product_reviews_admin_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    review_status: Optional[str] = Query(
        None, alias="status", description="Filter by moderation status"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedReviewResponse:
    """List reviews for a specific product (admin).

    Returns all reviews for a single product, filterable by status.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        review_status: Optional status filter.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedReviewResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store or product is not found.
    """
    from app.services import review_service

    try:
        reviews, total = await review_service.list_reviews(
            db,
            store_id=store_id,
            product_id=product_id,
            status_filter=review_status,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedReviewResponse(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch(
    "/stores/{store_id}/reviews/{review_id}",
    response_model=ReviewResponse,
)
async def update_review_status_endpoint(
    store_id: uuid.UUID,
    review_id: uuid.UUID,
    request: UpdateReviewStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Update a review's moderation status (approve/reject).

    Store owners use this to moderate reviews. Approved reviews become
    visible on the public storefront.

    Args:
        store_id: The UUID of the store.
        review_id: The UUID of the review to update.
        request: Status update payload with new status and optional note.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ReviewResponse with the updated review data.

    Raises:
        HTTPException 404: If the store or review is not found.
    """
    from app.services import review_service

    try:
        review = await review_service.update_review_status(
            db,
            store_id=store_id,
            user_id=current_user.id,
            review_id=review_id,
            status=request.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return ReviewResponse.model_validate(review)


@router.get(
    "/stores/{store_id}/products/{product_id}/reviews/stats",
    response_model=ReviewStatsResponse,
)
async def get_review_stats_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewStatsResponse:
    """Get aggregated review statistics for a product.

    Returns the average rating, total review count, and star-level
    distribution for approved reviews on a product.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ReviewStatsResponse with aggregated statistics.

    Raises:
        HTTPException 404: If the store or product is not found.
    """
    from app.services import review_service

    try:
        stats = await review_service.get_review_stats(
            db,
            store_id=store_id,
            product_id=product_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    # Convert rating_distribution keys from int to str (schema expects string keys)
    if "rating_distribution" in stats:
        stats["rating_distribution"] = {
            str(k): v for k, v in stats["rating_distribution"].items()
        }
    return ReviewStatsResponse(**stats)


# ---------------------------------------------------------------------------
# Public route handlers (no authentication required)
# ---------------------------------------------------------------------------


@router.get(
    "/public/stores/{slug}/products/{product_slug}/reviews",
    response_model=PaginatedPublicReviewResponse,
)
async def list_public_product_reviews_endpoint(
    slug: str,
    product_slug: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPublicReviewResponse:
    """List approved reviews for a product (public).

    Returns only approved reviews visible to customers on the storefront.
    Includes the average rating for the product.

    Args:
        slug: The store's URL slug.
        product_slug: The product's URL slug.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedPublicReviewResponse with approved reviews and average rating.

    Raises:
        HTTPException 404: If the store or product is not found.
    """
    from app.services import review_service

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

        reviews, total = await review_service.get_public_reviews(
            db,
            store_id=store.id,
            product_id=product.id,
            page=page,
            per_page=per_page,
        )

        # Get average rating
        stats = await review_service.get_review_stats(
            db,
            store_id=store.id,
            product_id=product.id,
        )
        avg_rating = stats.get("average_rating")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedPublicReviewResponse(
        items=[PublicReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        average_rating=avg_rating,
    )


@router.post(
    "/public/stores/{slug}/products/{product_slug}/reviews",
    response_model=PublicReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_public_review_endpoint(
    slug: str,
    product_slug: str,
    request: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> PublicReviewResponse:
    """Submit a review for a product (public, customer-facing).

    Customers can submit reviews for products. Reviews start in
    ``pending`` status and become visible after store owner approval.
    Purchase verification is performed automatically.

    Args:
        slug: The store's URL slug.
        product_slug: The product's URL slug.
        request: Review submission payload.
        db: Async database session injected by FastAPI.

    Returns:
        PublicReviewResponse with the submitted review data.

    Raises:
        HTTPException 404: If the store or product is not found.
        HTTPException 400: If the customer has already reviewed this product.
    """
    from app.services import review_service
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

        review = await review_service.create_review(
            db,
            store_id=store.id,
            product_id=product.id,
            customer_id=None,
            customer_name=request.customer_name or "Anonymous",
            customer_email=request.customer_email,
            rating=request.rating,
            title=request.title,
            body=request.body,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return PublicReviewResponse.model_validate(review)
