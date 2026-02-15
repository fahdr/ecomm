"""Category API router.

Provides CRUD endpoints for managing product categories within a store.
Categories support hierarchical (tree) structures via optional parent
references. Products can be assigned to and removed from categories.

Public endpoints allow storefront visitors to browse categories and
their products without authentication.

**For Developers:**
    Admin routes are nested under ``/stores/{store_id}/categories/...``
    (full path: ``/api/v1/stores/{store_id}/categories/...``).
    Public routes are under ``/public/stores/{slug}/categories/...``.
    The ``get_current_user`` dependency is used for admin authentication.
    Service functions in ``category_service`` handle all business logic.

**For QA Engineers:**
    - Admin endpoints return 401 without a valid token.
    - Admin endpoints return 404 if the store doesn't exist or belongs to another user.
    - GET list supports ``?page=``, ``?per_page=``, ``?tree=true`` query params.
    - ``tree=true`` returns categories in a nested tree structure.
    - POST create returns 201 with the full category data.
    - DELETE returns 204 with no content.
    - Assigning a product to a category is idempotent.
    - Public GET endpoints require no authentication.
    - Public category products only returns active products.

**For End Users:**
    - Organize your products into categories and subcategories.
    - Build a category tree for navigation in your storefront.
    - Assign and remove products from categories to control storefront layout.
    - Customers can browse categories and products on the public storefront.
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
from app.schemas.category import (
    CategoryResponse,
    CreateCategoryRequest,
    PaginatedCategoryResponse,
    UpdateCategoryRequest,
)

router = APIRouter(tags=["categories"])


# ---------------------------------------------------------------------------
# Local schemas (not present in app.schemas.category)
# ---------------------------------------------------------------------------


class AssignProductsRequest(BaseModel):
    """Request body for assigning products to a category.

    Attributes:
        product_ids: List of product UUIDs to assign.
    """

    product_ids: list[uuid.UUID]


class CategoryProductsResponse(BaseModel):
    """Response confirming product assignment.

    Attributes:
        category_id: The category products were assigned to.
        product_ids: The list of product IDs that were assigned.
        message: Human-readable confirmation message.
    """

    category_id: uuid.UUID
    product_ids: list[uuid.UUID]
    message: str


class PublicCategoryResponse(BaseModel):
    """Public-facing category response (no admin fields).

    Attributes:
        id: Category identifier.
        name: Display name.
        slug: URL-friendly slug.
        description: Optional description.
        image_url: Optional category image.
        parent_id: Parent category ID (null for top-level).
        product_count: Number of active products in this category.
    """

    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    product_count: int = 0

    model_config = {"from_attributes": True}


class PublicCategoryProductResponse(BaseModel):
    """Public-facing product response within a category listing.

    Attributes:
        id: Product UUID.
        title: Product title.
        slug: Product URL slug.
        price: Product selling price.
        compare_at_price: Original price before discount.
        images: Product image URLs.
        description: Product description.
    """

    id: uuid.UUID
    title: str
    slug: str
    price: Decimal
    compare_at_price: Optional[Decimal] = None
    images: list[str] = []
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class PaginatedPublicCategoryProductResponse(BaseModel):
    """Paginated public products within a category.

    Attributes:
        items: List of product records.
        total: Total number of products in this category.
        page: Current page number.
        per_page: Number of items per page.
        pages: Total number of pages.
        category: The category these products belong to.
    """

    items: list[PublicCategoryProductResponse]
    total: int
    page: int
    per_page: int
    pages: int
    category: PublicCategoryResponse


# ---------------------------------------------------------------------------
# Admin route handlers (store-scoped, authenticated)
# ---------------------------------------------------------------------------



def _category_to_response(category) -> CategoryResponse:
    """Convert a Category ORM instance to a CategoryResponse.

    Avoids accessing the lazy-loaded ``children`` relationship which
    can cause greenlet errors in async contexts.

    Args:
        category: The Category ORM instance.

    Returns:
        A CategoryResponse schema instance.
    """
    return CategoryResponse(
        id=category.id,
        store_id=category.store_id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        image_url=category.image_url,
        parent_id=category.parent_id,
        position=category.position,
        is_active=category.is_active,
        product_count=getattr(category, 'product_count', 0),
        created_at=category.created_at,
        updated_at=category.updated_at,
        children=None,
    )


@router.post(
    "/stores/{store_id}/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_endpoint(
    store_id: uuid.UUID,
    request: CreateCategoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Create a new category in a store.

    Creates a category with the specified name, optional slug, description,
    and parent reference for building hierarchical category trees.

    Args:
        store_id: The UUID of the store.
        request: Category creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        CategoryResponse with the newly created category data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the parent category does not exist or slug conflicts.
    """
    from app.services import category_service

    try:
        category = await category_service.create_category(
            db,
            store_id=store_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            image_url=request.image_url,
            parent_id=request.parent_id,
            position=request.position,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already exists" in detail or "parent" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return _category_to_response(category)


@router.get("/stores/{store_id}/categories", response_model=PaginatedCategoryResponse)
async def list_categories_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    tree: bool = Query(False, description="Return as nested tree structure"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCategoryResponse:
    """List categories for a store with pagination.

    When ``tree=true``, returns categories arranged in a nested tree
    structure. Otherwise returns a flat paginated list.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        tree: If true, return nested tree structure.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedCategoryResponse with items, total count, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import category_service

    try:
        categories, total = await category_service.list_categories(
            db,
            store_id=store_id,
            page=page,
            per_page=per_page,
            include_children=tree,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedCategoryResponse(
        items=[_category_to_response(c) for c in categories],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/stores/{store_id}/categories/{category_id}", response_model=CategoryResponse
)
async def get_category_endpoint(
    store_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Retrieve a single category by ID.

    Args:
        store_id: The UUID of the store.
        category_id: The UUID of the category to retrieve.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        CategoryResponse with the category data.

    Raises:
        HTTPException 404: If the store or category is not found.
    """
    from app.services import category_service

    try:
        category = await category_service.get_category(
            db, store_id=store_id, category_id=category_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return _category_to_response(category)


@router.patch(
    "/stores/{store_id}/categories/{category_id}", response_model=CategoryResponse
)
async def update_category_endpoint(
    store_id: uuid.UUID,
    category_id: uuid.UUID,
    request: UpdateCategoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Update a category's fields (partial update).

    Only provided fields are updated. You can change the name, slug,
    description, parent, or position.

    Args:
        store_id: The UUID of the store.
        category_id: The UUID of the category to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        CategoryResponse with the updated category data.

    Raises:
        HTTPException 404: If the store or category is not found.
        HTTPException 400: If the update creates a circular parent reference.
    """
    from app.services import category_service

    try:
        category = await category_service.update_category(
            db,
            store_id=store_id,
            user_id=current_user.id,
            category_id=category_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "circular" in detail.lower() or "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return _category_to_response(category)


@router.delete(
    "/stores/{store_id}/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category_endpoint(
    store_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a category.

    Child categories are re-parented to the deleted category's parent
    (or become top-level). Product associations are removed.

    Args:
        store_id: The UUID of the store.
        category_id: The UUID of the category to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or category is not found.
    """
    from app.services import category_service

    try:
        await category_service.delete_category(
            db, store_id=store_id, user_id=current_user.id, category_id=category_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/stores/{store_id}/categories/{category_id}/products",
    response_model=CategoryProductsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_products_endpoint(
    store_id: uuid.UUID,
    category_id: uuid.UUID,
    request: AssignProductsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategoryProductsResponse:
    """Assign products to a category.

    This operation is idempotent: products already in the category are
    silently skipped.

    Args:
        store_id: The UUID of the store.
        category_id: The UUID of the category.
        request: List of product UUIDs to assign.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        CategoryProductsResponse confirming the assignment.

    Raises:
        HTTPException 404: If the store, category, or any product is not found.
    """
    from app.services import category_service

    try:
        await category_service.assign_products_to_category(
            db,
            store_id=store_id,
            user_id=current_user.id,
            category_id=category_id,
            product_ids=request.product_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return CategoryProductsResponse(
        category_id=category_id,
        product_ids=request.product_ids,
        message=f"Assigned {len(request.product_ids)} product(s) to category",
    )


@router.delete(
    "/stores/{store_id}/categories/{category_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_product_from_category_endpoint(
    store_id: uuid.UUID,
    category_id: uuid.UUID,
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a product from a category.

    Args:
        store_id: The UUID of the store.
        category_id: The UUID of the category.
        product_id: The UUID of the product to remove.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store, category, or product association is not found.
    """
    from app.services import category_service

    try:
        await category_service.remove_product_from_category(
            db,
            store_id=store_id,
            user_id=current_user.id,
            category_id=category_id,
            product_id=product_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Public route handlers (no authentication required)
# ---------------------------------------------------------------------------


@router.get(
    "/public/stores/{slug}/categories",
    response_model=list[PublicCategoryResponse],
)
async def list_public_categories_endpoint(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> list[PublicCategoryResponse]:
    """List all active categories for a store (public).

    Returns all active categories for a store, visible to customers on
    the storefront. No authentication required.

    Args:
        slug: The store's URL slug.
        db: Async database session injected by FastAPI.

    Returns:
        List of PublicCategoryResponse objects sorted by position then name.

    Raises:
        HTTPException 404: If the store is not found or is not active.
    """
    from app.models.category import Category, ProductCategory
    from app.models.product import Product, ProductStatus
    from app.models.store import Store, StoreStatus
    from sqlalchemy import func

    # Resolve store
    store_result = await db.execute(
        select(Store).where(
            Store.slug == slug,
            Store.status == StoreStatus.active,
        )
    )
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # Fetch active categories with product counts
    result = await db.execute(
        select(Category)
        .where(
            Category.store_id == store.id,
            Category.is_active.is_(True),
        )
        .order_by(Category.position, Category.name)
    )
    categories = list(result.scalars().all())

    # Count active products per category
    responses = []
    for cat in categories:
        count_result = await db.execute(
            select(func.count(Product.id))
            .join(ProductCategory, ProductCategory.product_id == Product.id)
            .where(
                ProductCategory.category_id == cat.id,
                Product.store_id == store.id,
                Product.status == ProductStatus.active,
            )
        )
        product_count = count_result.scalar_one()

        responses.append(
            PublicCategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                image_url=cat.image_url,
                parent_id=cat.parent_id,
                product_count=product_count,
            )
        )

    return responses


@router.get(
    "/public/stores/{slug}/categories/{category_slug}/products",
    response_model=PaginatedPublicCategoryProductResponse,
)
async def list_public_category_products_endpoint(
    slug: str,
    category_slug: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPublicCategoryProductResponse:
    """List active products in a category (public).

    Returns paginated active products within a specific category.
    No authentication required.

    Args:
        slug: The store's URL slug.
        category_slug: The category's URL slug.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedPublicCategoryProductResponse with products and category info.

    Raises:
        HTTPException 404: If the store or category is not found.
    """
    from app.models.category import Category, ProductCategory
    from app.models.product import Product, ProductStatus
    from app.models.store import Store, StoreStatus
    from sqlalchemy import func

    # Resolve store
    store_result = await db.execute(
        select(Store).where(
            Store.slug == slug,
            Store.status == StoreStatus.active,
        )
    )
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # Resolve category by slug
    cat_result = await db.execute(
        select(Category).where(
            Category.store_id == store.id,
            Category.slug == category_slug,
            Category.is_active.is_(True),
        )
    )
    category = cat_result.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    # Count total products
    count_result = await db.execute(
        select(func.count(Product.id))
        .join(ProductCategory, ProductCategory.product_id == Product.id)
        .where(
            ProductCategory.category_id == category.id,
            Product.store_id == store.id,
            Product.status == ProductStatus.active,
        )
    )
    total = count_result.scalar_one()

    # Fetch paginated products
    offset = (page - 1) * per_page
    products_result = await db.execute(
        select(Product)
        .join(ProductCategory, ProductCategory.product_id == Product.id)
        .where(
            ProductCategory.category_id == category.id,
            Product.store_id == store.id,
            Product.status == ProductStatus.active,
        )
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    products = list(products_result.scalars().all())

    pages_count = math.ceil(total / per_page) if total > 0 else 1

    # Build product count for category response
    cat_response = PublicCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        image_url=category.image_url,
        parent_id=category.parent_id,
        product_count=total,
    )

    return PaginatedPublicCategoryProductResponse(
        items=[
            PublicCategoryProductResponse(
                id=p.id,
                title=p.title,
                slug=p.slug,
                price=p.price,
                compare_at_price=p.compare_at_price,
                images=p.images or [],
                description=p.description,
            )
            for p in products
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages_count,
        category=cat_response,
    )
