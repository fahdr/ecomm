"""Product API router.

Provides CRUD endpoints for managing products within a store. All endpoints
require authentication and enforce store ownership — users can only manage
products in their own stores.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/products/...``
    (full path: ``/api/v1/stores/{store_id}/products/...``).
    The ``get_current_user`` dependency is used for authentication.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - All endpoints return 404 if the store doesn't exist or belongs to another user.
    - GET list supports ``?page=``, ``?per_page=``, ``?search=``, ``?status=`` query params.
    - DELETE performs a soft-delete (status set to ``archived``).
    - Creating a product returns 201 with the full product data including slug.
    - Image upload accepts multipart form data and saves to ``/uploads/``.

**For End Users:**
    - Add products to your store with a title, price, description, and images.
    - Search and filter products by status.
    - Soft-delete products you no longer want to sell.
"""

import math
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_product_limit, get_current_user
from app.database import get_db
from app.models.product import ProductStatus
from app.models.user import User
from app.schemas.product import (
    CreateProductRequest,
    PaginatedProductResponse,
    ProductResponse,
    UpdateProductRequest,
)
from app.services.product_service import (
    create_product,
    delete_product,
    get_product,
    list_products,
    update_product,
)

router = APIRouter(prefix="/stores/{store_id}/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product_endpoint(
    store_id: uuid.UUID,
    request: CreateProductRequest,
    current_user: User = Depends(check_product_limit),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Create a new product in a store.

    Plan enforcement: the ``check_product_limit`` dependency verifies
    the user has not exceeded their plan's per-store product limit.
    Returns 403 if the limit is reached.

    Args:
        store_id: The UUID of the store to add the product to.
        request: Product creation payload.
        current_user: The authenticated user (verified within plan limits).
        db: Async database session injected by FastAPI.

    Returns:
        ProductResponse with the newly created product data.

    Raises:
        HTTPException: 404 if the store is not found or belongs to another user.
    """
    try:
        variants = None
        if request.variants:
            variants = [v.model_dump() for v in request.variants]

        product = await create_product(
            db,
            store_id=store_id,
            user_id=current_user.id,
            title=request.title,
            price=request.price,
            description=request.description,
            compare_at_price=request.compare_at_price,
            cost=request.cost,
            images=request.images,
            status=request.status,
            seo_title=request.seo_title,
            seo_description=request.seo_description,
            variants=variants,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # Notify connected services about the new product
    from app.services.bridge_service import fire_platform_event
    fire_platform_event(
        user_id=current_user.id,
        store_id=store_id,
        event="product.created",
        resource_id=product.id,
        resource_type="product",
        payload={
            "product_id": str(product.id),
            "title": product.title,
            "price": str(product.price),
            "status": product.status.value if product.status else None,
        },
    )

    return ProductResponse.model_validate(product)


@router.get("", response_model=PaginatedProductResponse)
async def list_products_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by title"),
    product_status: ProductStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedProductResponse:
    """List products in a store with pagination, search, and filtering.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1–100, default 20).
        search: Optional search term to filter by title.
        product_status: Optional status filter (draft, active, archived).
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedProductResponse with items, total count, and pagination metadata.

    Raises:
        HTTPException: 404 if the store is not found or belongs to another user.
    """
    try:
        products, total = await list_products(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            search=search,
            status_filter=product_status,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedProductResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Retrieve a single product by ID.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product to retrieve.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        ProductResponse with the product data and variants.

    Raises:
        HTTPException: 404 if the store or product is not found.
    """
    try:
        product = await get_product(
            db, store_id=store_id, user_id=current_user.id, product_id=product_id
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    request: UpdateProductRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update a product's fields (partial update).

    Only provided fields are updated. If variants are provided, existing
    variants are replaced entirely.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product to update.
        request: Partial update payload.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        ProductResponse with the updated product data.

    Raises:
        HTTPException: 404 if the store or product is not found.
    """
    try:
        update_data = request.model_dump(exclude_unset=True)
        if "variants" in update_data and update_data["variants"] is not None:
            update_data["variants"] = [
                v.model_dump() for v in request.variants  # type: ignore
            ]

        product = await update_product(
            db,
            store_id=store_id,
            user_id=current_user.id,
            product_id=product_id,
            **update_data,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Notify connected services about the product update
    from app.services.bridge_service import fire_platform_event
    fire_platform_event(
        user_id=current_user.id,
        store_id=store_id,
        event="product.updated",
        resource_id=product_id,
        resource_type="product",
        payload={
            "product_id": str(product_id),
            "title": product.title,
            "price": str(product.price),
            "updated_fields": list(update_data.keys()),
        },
    )

    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", response_model=ProductResponse)
async def delete_product_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Soft-delete a product (set status to ``archived``).

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product to delete.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        ProductResponse with the archived product data.

    Raises:
        HTTPException: 404 if the store or product is not found.
    """
    try:
        product = await delete_product(
            db, store_id=store_id, user_id=current_user.id, product_id=product_id
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return ProductResponse.model_validate(product)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    store_id: uuid.UUID,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a product image to local filesystem.

    Saves the uploaded file to ``/uploads/{store_id}/`` with a unique filename.
    Returns the URL path to access the uploaded image.

    Args:
        store_id: The UUID of the store.
        file: The uploaded image file.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        A dict with the ``url`` key containing the image path.

    Raises:
        HTTPException: 404 if the store is not found or belongs to another user.
        HTTPException: 400 if the file type is not an allowed image format.
    """
    from app.services.product_service import _verify_store_ownership

    try:
        await _verify_store_ownership(db, store_id, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_types)}",
        )

    import tempfile
    base_dir = os.environ.get("UPLOAD_DIR", os.path.join(tempfile.gettempdir(), "uploads"))
    upload_dir = os.path.join(base_dir, str(store_id))
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "image.png")[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{store_id}/{filename}"}
