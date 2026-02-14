"""
Price watch API endpoints for SourcePilot.

Handles creating, listing, deleting, and syncing price watches for
monitoring supplier product price changes.

For Developers:
    All endpoints require JWT authentication. The sync endpoint triggers
    an immediate price check for all active watches. The periodic sync
    runs via Celery beat. The ``connection_id`` query/body parameter maps
    to the ``store_id`` column in the database.

For QA Engineers:
    Test CRUD operations. Verify the sync endpoint updates price data.
    Test filtering by connection_id. Verify deleted watches are not synced.

For Project Managers:
    These endpoints power the Price Monitoring feature in the dashboard.

For End Users:
    Add price watches to stay informed when supplier prices change.
    Trigger a manual sync to check prices immediately.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.price_watch import (
    PriceWatchCreate,
    PriceWatchList,
    PriceWatchResponse,
)
from app.services.price_watch_service import (
    create_price_watch,
    delete_price_watch,
    get_price_watches,
    sync_all_prices,
)

router = APIRouter(prefix="/price-watches", tags=["price-watches"])


@router.post("", response_model=PriceWatchResponse, status_code=201)
async def add_price_watch(
    body: PriceWatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new price watch for a supplier product.

    Creates a watch that tracks the product's price on the supplier
    platform. The system periodically checks for price changes.

    Args:
        body: Price watch creation data with product_url, source,
              threshold_percent, and optional connection_id.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PriceWatchResponse with the new watch details.

    Raises:
        HTTPException 400: If the creation data is invalid.
    """
    try:
        watch = await create_price_watch(db, current_user.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return watch


@router.get("", response_model=PriceWatchList)
async def list_price_watches(
    connection_id: uuid.UUID | None = Query(
        None, description="Filter by store connection ID"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all price watches for the authenticated user.

    Optionally filter by connection_id. Returns watches ordered by
    creation date (newest first).

    Args:
        connection_id: Optional connection (store) ID filter.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PriceWatchList with all matching watches and total count.
    """
    watches = await get_price_watches(
        db, current_user.id, connection_id=connection_id
    )
    return PriceWatchList(
        items=[PriceWatchResponse.model_validate(w) for w in watches],
        total=len(watches),
    )


@router.delete("/{watch_id}", status_code=204)
async def remove_price_watch(
    watch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a price watch.

    Deletes the price watch, stopping future price monitoring.

    Args:
        watch_id: The price watch's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If watch not found or not owned by user.
    """
    deleted = await delete_price_watch(db, watch_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price watch not found",
        )


@router.post("/sync", status_code=200)
async def trigger_price_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an immediate price sync for all active watches.

    Checks current prices for all active price watches and updates
    the price_changed flag where differences are detected.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with sync results: total_checked, total_changed, total_errors.
    """
    result = await sync_all_prices(db)
    return result
