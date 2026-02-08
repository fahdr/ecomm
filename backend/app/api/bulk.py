"""Bulk Operations API router.

Provides endpoints for performing bulk operations on products. Store owners
can update, delete, or adjust prices for multiple products in a single
request, reducing round trips for large catalog management tasks.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/bulk/...``
    (full path: ``/api/v1/stores/{store_id}/bulk/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``bulk_service`` handle batch processing.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - Maximum 100 products per bulk operation.
    - Partial failures return 200 with a results array showing per-item status.
    - Price adjustment supports both percentage and fixed amount changes.
    - Bulk delete performs soft-delete (status set to archived).

**For End Users:**
    - Update multiple products at once (status, title, etc.).
    - Delete multiple products in a single action.
    - Adjust prices across your catalog with percentage or fixed changes.
    - Save time managing large product catalogs.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.bulk import (
    BulkOperationResponse,
    BulkPriceUpdateRequest,
    BulkProductDeleteRequest,
    BulkProductUpdateRequest,
)

router = APIRouter(prefix="/stores/{store_id}/bulk", tags=["bulk-operations"])


# ---------------------------------------------------------------------------
# Local response schema for per-item results (not in app.schemas.bulk)
# ---------------------------------------------------------------------------


class BulkItemResult(BaseModel):
    """Result for a single item in a bulk operation.

    Attributes:
        product_id: The product UUID.
        success: Whether the operation succeeded for this product.
        message: Status message or error detail.
    """

    product_id: uuid.UUID
    success: bool
    message: str


class BulkItemOperationResponse(BaseModel):
    """Response for a bulk operation with per-item results.

    Attributes:
        total: Total number of products in the operation.
        succeeded: Number of successful operations.
        failed: Number of failed operations.
        results: Per-product operation results.
    """

    total: int
    succeeded: int
    failed: int
    results: list[BulkItemResult]


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("/products/update", response_model=BulkItemOperationResponse)
async def bulk_update_products_endpoint(
    store_id: uuid.UUID,
    request: BulkProductUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkItemOperationResponse:
    """Bulk update multiple products in a single request.

    Applies individual update payloads to each specified product.
    Partial failures are allowed: products that fail to update are
    reported in the results array while successful updates proceed.

    Args:
        store_id: The UUID of the store.
        request: Bulk update payload with per-product changes.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        BulkOperationResponse with per-product success/failure results.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import bulk_service

    try:
        # BulkProductUpdateRequest has product_ids and updates (dict)
        # which match the service function parameters directly
        summary = await bulk_service.bulk_update_products(
            db,
            store_id=store_id,
            user_id=current_user.id,
            product_ids=request.product_ids,
            updates=request.updates,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    # Build per-item results from the summary
    error_ids = {e["product_id"] for e in summary.get("errors", [])}
    error_map = {e["product_id"]: e["error"] for e in summary.get("errors", [])}
    results = []
    for pid in request.product_ids:
        pid_str = str(pid)
        if pid_str in error_ids:
            results.append(BulkItemResult(
                product_id=pid, success=False, message=error_map[pid_str]
            ))
        else:
            results.append(BulkItemResult(
                product_id=pid, success=True, message="Updated successfully"
            ))

    return BulkItemOperationResponse(
        total=summary["total"],
        succeeded=summary["succeeded"],
        failed=summary["failed"],
        results=results,
    )


@router.post("/products/delete", response_model=BulkItemOperationResponse)
async def bulk_delete_products_endpoint(
    store_id: uuid.UUID,
    request: BulkProductDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkItemOperationResponse:
    """Bulk soft-delete multiple products.

    Sets the status of each specified product to ``archived``.
    Partial failures are allowed and reported in the results array.

    Args:
        store_id: The UUID of the store.
        request: Bulk delete payload with product IDs.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        BulkOperationResponse with per-product success/failure results.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import bulk_service

    try:
        # Service returns a summary dict: {total, succeeded, failed, errors}
        summary = await bulk_service.bulk_delete_products(
            db,
            store_id=store_id,
            user_id=current_user.id,
            product_ids=request.product_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    # Build per-item results from the summary
    error_ids = {e["product_id"] for e in summary.get("errors", [])}
    error_map = {e["product_id"]: e["error"] for e in summary.get("errors", [])}
    results = []
    for pid in request.product_ids:
        pid_str = str(pid)
        if pid_str in error_ids:
            results.append(BulkItemResult(
                product_id=pid, success=False, message=error_map[pid_str]
            ))
        else:
            results.append(BulkItemResult(
                product_id=pid, success=True, message="Deleted successfully"
            ))

    return BulkItemOperationResponse(
        total=summary["total"],
        succeeded=summary["succeeded"],
        failed=summary["failed"],
        results=results,
    )


@router.post("/products/price", response_model=BulkItemOperationResponse)
async def bulk_price_adjustment_endpoint(
    store_id: uuid.UUID,
    request: BulkPriceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkItemOperationResponse:
    """Bulk adjust prices for multiple products.

    Applies a percentage or fixed amount adjustment to each product's
    price. Supports both increases (positive value) and decreases
    (negative value). An optional minimum price floor prevents prices
    from going below zero or a specified threshold.

    Args:
        store_id: The UUID of the store.
        request: Price adjustment payload with product IDs and adjustment.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        BulkOperationResponse with per-product success/failure results.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the adjustment parameters are invalid.
    """
    from app.services import bulk_service

    try:
        # Service function is bulk_update_prices with adjustment_value (not value)
        # Service does not accept min_price parameter
        # BulkPriceUpdateRequest has product_ids, adjustment_type, adjustment_value
        # which match the service function parameters directly
        summary = await bulk_service.bulk_update_prices(
            db,
            store_id=store_id,
            user_id=current_user.id,
            product_ids=request.product_ids,
            adjustment_type=request.adjustment_type,
            adjustment_value=request.adjustment_value,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)

    # Build per-item results from the summary
    error_ids = {e["product_id"] for e in summary.get("errors", [])}
    error_map = {e["product_id"]: e["error"] for e in summary.get("errors", [])}
    results = []
    for pid in request.product_ids:
        pid_str = str(pid)
        if pid_str in error_ids:
            results.append(BulkItemResult(
                product_id=pid, success=False, message=error_map[pid_str]
            ))
        else:
            results.append(BulkItemResult(
                product_id=pid, success=True, message="Price adjusted successfully"
            ))

    return BulkItemOperationResponse(
        total=summary["total"],
        succeeded=summary["succeeded"],
        failed=summary["failed"],
        results=results,
    )
