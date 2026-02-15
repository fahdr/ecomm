"""Supplier API router.

Provides CRUD endpoints for managing suppliers and linking them to products.
In a dropshipping model, suppliers fulfill orders directly to customers.
This router lets store owners track supplier information and associate
suppliers with products for fulfillment routing.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/suppliers/...``
    and ``/stores/{store_id}/products/{product_id}/suppliers/...``
    (full path: ``/api/v1/stores/{store_id}/...``).
    The ``get_current_user`` dependency is used for authentication.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - All endpoints return 404 if the store doesn't exist or belongs to another user.
    - Linking a supplier to a product is idempotent.
    - Suppliers can be linked to multiple products and vice versa.
    - DELETE returns 204 with no content.

**For End Users:**
    - Add supplier details (name, website, contact info, lead times).
    - Link suppliers to products so the platform knows where to route orders.
    - Track supplier reliability and costs.
"""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.supplier import (
    CreateSupplierRequest,
    LinkProductSupplierRequest,
    PaginatedSupplierResponse,
    ProductSupplierResponse,
    SupplierResponse,
    UpdateSupplierRequest,
)

router = APIRouter(prefix="/stores/{store_id}", tags=["suppliers"])


# ---------------------------------------------------------------------------
# Supplier CRUD routes
# ---------------------------------------------------------------------------


@router.post(
    "/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED
)
async def create_supplier_endpoint(
    store_id: uuid.UUID,
    request: CreateSupplierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupplierResponse:
    """Create a new supplier for a store.

    Adds a supplier record with contact details and fulfillment
    information. Suppliers can later be linked to products.

    Args:
        store_id: The UUID of the store.
        request: Supplier creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        SupplierResponse with the newly created supplier data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import supplier_service

    try:
        supplier = await supplier_service.create_supplier(
            db,
            store_id=store_id,
            user_id=current_user.id,
            name=request.name,
            website=request.website,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return SupplierResponse.model_validate(supplier)


@router.get("/suppliers", response_model=PaginatedSupplierResponse)
async def list_suppliers_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSupplierResponse:
    """List suppliers for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedSupplierResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import supplier_service

    try:
        suppliers, total = await supplier_service.list_suppliers(
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

    return PaginatedSupplierResponse(
        items=[SupplierResponse.model_validate(s) for s in suppliers],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier_endpoint(
    store_id: uuid.UUID,
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupplierResponse:
    """Retrieve a single supplier by ID.

    Args:
        store_id: The UUID of the store.
        supplier_id: The UUID of the supplier to retrieve.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        SupplierResponse with the supplier data.

    Raises:
        HTTPException 404: If the store or supplier is not found.
    """
    from app.services import supplier_service

    try:
        supplier = await supplier_service.get_supplier(
            db, store_id=store_id, user_id=current_user.id, supplier_id=supplier_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return SupplierResponse.model_validate(supplier)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier_endpoint(
    store_id: uuid.UUID,
    supplier_id: uuid.UUID,
    request: UpdateSupplierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupplierResponse:
    """Update a supplier's fields (partial update).

    Only provided fields are updated.

    Args:
        store_id: The UUID of the store.
        supplier_id: The UUID of the supplier to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        SupplierResponse with the updated supplier data.

    Raises:
        HTTPException 404: If the store or supplier is not found.
    """
    from app.services import supplier_service

    try:
        supplier = await supplier_service.update_supplier(
            db,
            store_id=store_id,
            user_id=current_user.id,
            supplier_id=supplier_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return SupplierResponse.model_validate(supplier)


@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier_endpoint(
    store_id: uuid.UUID,
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a supplier and all its product associations.

    Args:
        store_id: The UUID of the store.
        supplier_id: The UUID of the supplier to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or supplier is not found.
    """
    from app.services import supplier_service

    try:
        await supplier_service.delete_supplier(
            db, store_id=store_id, user_id=current_user.id, supplier_id=supplier_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Product-Supplier linking routes
# ---------------------------------------------------------------------------


@router.post(
    "/products/{product_id}/suppliers",
    response_model=ProductSupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_supplier_to_product_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    request: LinkProductSupplierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductSupplierResponse:
    """Link a supplier to a product.

    Associates a supplier with a product for fulfillment routing.
    Optionally specify the supplier's cost and whether this is the
    primary supplier. This operation is idempotent.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product.
        request: Link payload with supplier_id, cost, and primary flag.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ProductSupplierResponse confirming the link.

    Raises:
        HTTPException 404: If the store, product, or supplier is not found.
    """
    from app.services import supplier_service

    try:
        link = await supplier_service.link_product_supplier(
            db,
            store_id=store_id,
            user_id=current_user.id,
            product_id=product_id,
            supplier_id=request.supplier_id,
            supplier_url=request.supplier_url,
            supplier_sku=request.supplier_sku,
            supplier_cost=request.supplier_cost,
            is_primary=request.is_primary,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return ProductSupplierResponse.model_validate(link)


@router.delete(
    "/products/{product_id}/suppliers/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_supplier_from_product_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Unlink a supplier from a product.

    Removes the association between a supplier and a product.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product.
        supplier_id: The UUID of the supplier to unlink.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the link is not found.
    """
    from app.services import supplier_service

    try:
        await supplier_service.unlink_product_supplier(
            db,
            store_id=store_id,
            user_id=current_user.id,
            product_id=product_id,
            supplier_id=supplier_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/products/{product_id}/suppliers",
    response_model=list[ProductSupplierResponse],
)
async def get_product_suppliers_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductSupplierResponse]:
    """Get all suppliers linked to a product.

    Returns all supplier associations for a given product, including
    cost and primary-supplier flags.

    Args:
        store_id: The UUID of the store.
        product_id: The UUID of the product.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        List of ProductSupplierResponse objects.

    Raises:
        HTTPException 404: If the store or product is not found.
    """
    from app.services import supplier_service

    try:
        links = await supplier_service.get_product_suppliers(
            db,
            store_id=store_id,
            product_id=product_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return [ProductSupplierResponse.model_validate(link) for link in links]
