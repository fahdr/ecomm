"""CSV export API endpoints.

Provides download endpoints for exporting store data (orders, products,
customers) as CSV files. All endpoints require authentication and verify
store ownership.

**For Developers:**
    Each endpoint returns a ``StreamingResponse`` with
    ``text/csv`` content type and a ``Content-Disposition`` header that
    triggers a file download in the browser.

**For QA Engineers:**
    - ``GET /stores/{store_id}/exports/orders`` → orders CSV download
    - ``GET /stores/{store_id}/exports/products`` → products CSV download
    - ``GET /stores/{store_id}/exports/customers`` → customers CSV download
    - All endpoints require valid JWT authentication.
    - Returns 404 if the store doesn't exist or belong to the user.

**For Project Managers:**
    Implements Feature 5A (CSV Export) from the Phase 5 polish plan.

@module api/exports
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.export_service import (
    export_orders_csv,
    export_products_csv,
    export_customers_csv,
)

router = APIRouter(
    prefix="/stores/{store_id}/exports",
    tags=["exports"],
)


@router.get("/orders")
async def export_orders(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export all orders for a store as a CSV file download.

    Args:
        store_id: The store UUID from the URL path.
        current_user: The authenticated user (injected by dependency).
        db: Database session (injected by dependency).

    Returns:
        A CSV file response with orders data.

    Raises:
        HTTPException: 404 if store not found or access denied.
    """
    try:
        csv_content = await export_orders_csv(db, store_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=orders-{store_id}.csv",
        },
    )


@router.get("/products")
async def export_products(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export all products for a store as a CSV file download.

    Args:
        store_id: The store UUID from the URL path.
        current_user: The authenticated user (injected by dependency).
        db: Database session (injected by dependency).

    Returns:
        A CSV file response with products data.

    Raises:
        HTTPException: 404 if store not found or access denied.
    """
    try:
        csv_content = await export_products_csv(db, store_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=products-{store_id}.csv",
        },
    )


@router.get("/customers")
async def export_customers(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export all customer accounts for a store as a CSV file download.

    Args:
        store_id: The store UUID from the URL path.
        current_user: The authenticated user (injected by dependency).
        db: Database session (injected by dependency).

    Returns:
        A CSV file response with customers data.

    Raises:
        HTTPException: 404 if store not found or access denied.
    """
    try:
        csv_content = await export_customers_csv(db, store_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=customers-{store_id}.csv",
        },
    )
