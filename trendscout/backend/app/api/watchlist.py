"""
Watchlist API endpoints for TrendScout.

Manages the user's product watchlist — adding research results for
ongoing monitoring, updating tracking status, and removing items.

For Developers:
    All endpoints require JWT authentication. Watchlist capacity is
    limited by the user's plan tier (max_secondary in PLAN_LIMITS).
    Duplicate prevention is enforced at both the service and database
    (unique constraint on user_id + result_id) level.

For QA Engineers:
    Test: add to watchlist (success + duplicate + plan limit), list
    with status filter, update status/notes, delete. Verify cascading
    behavior when the linked result's run is deleted.

For Project Managers:
    The watchlist is how users save promising products from research
    results. It's the secondary metered resource (free = 25 items,
    pro = 500, enterprise = unlimited).

For End Users:
    Save interesting products to your watchlist for tracking.
    Change status to 'imported' after pushing to your store,
    or 'dismissed' to filter out products you've decided against.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.research import (
    WatchlistImportRequest,
    WatchlistImportResponse,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistItemUpdate,
    WatchlistListResponse,
    WatchlistResultSnapshot,
)
from app.services.research_service import (
    add_to_watchlist,
    delete_watchlist_item,
    get_store_connection,
    get_watchlist_items,
    update_watchlist_item,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _build_watchlist_response(item) -> WatchlistItemResponse:
    """
    Build a WatchlistItemResponse from a WatchlistItem ORM object.

    Includes the linked ResearchResult as a snapshot if available.

    Args:
        item: WatchlistItem ORM instance with result relationship loaded.

    Returns:
        WatchlistItemResponse with inline result snapshot.
    """
    result_snapshot = None
    if item.result:
        result_snapshot = WatchlistResultSnapshot(
            id=item.result.id,
            source=item.result.source,
            product_title=item.result.product_title,
            product_url=item.result.product_url,
            image_url=item.result.image_url,
            price=item.result.price,
            currency=item.result.currency,
            score=item.result.score,
        )

    return WatchlistItemResponse(
        id=item.id,
        user_id=item.user_id,
        result_id=item.result_id,
        status=item.status,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
        result=result_snapshot,
    )


@router.post("", response_model=WatchlistItemResponse, status_code=201)
async def add_item(
    body: WatchlistItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a research result to the user's watchlist.

    Enforces plan limits on total watchlist items. Prevents duplicate
    entries for the same result.

    Args:
        body: Watchlist item creation data (result_id, optional notes).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        WatchlistItemResponse with the new watchlist entry.

    Raises:
        HTTPException 403: If watchlist capacity limit reached.
        HTTPException 409: If result is already in the user's watchlist.
        HTTPException 404: If the referenced result does not exist.
    """
    try:
        item = await add_to_watchlist(
            db,
            user=current_user,
            result_id=body.result_id,
            notes=body.notes,
        )
    except ValueError as e:
        error_msg = str(e)
        if "limit reached" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg,
            )
        elif "already in your watchlist" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )

    return _build_watchlist_response(item)


@router.get("", response_model=WatchlistListResponse)
async def list_items(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: watching, imported, dismissed",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the user's watchlist items with optional status filtering.

    Returns items ordered by creation date (newest first).
    Each item includes an inline snapshot of the linked research result.

    Args:
        status_filter: Optional status filter (watching, imported, dismissed).
        page: Page number (1-indexed, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        WatchlistListResponse with paginated items.
    """
    items, total = await get_watchlist_items(
        db,
        user_id=current_user.id,
        status=status_filter,
        page=page,
        per_page=per_page,
    )
    return WatchlistListResponse(
        items=[_build_watchlist_response(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/{item_id}", response_model=WatchlistItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: WatchlistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a watchlist item's status and/or notes.

    Valid statuses: 'watching', 'imported', 'dismissed'.

    Args:
        item_id: The watchlist item's UUID.
        body: Fields to update (status, notes — both optional).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        WatchlistItemResponse with the updated item.

    Raises:
        HTTPException 404: If item not found or not owned by user.
    """
    # Use Ellipsis sentinel if notes not provided
    notes_value = body.notes if body.notes is not None else ...

    item = await update_watchlist_item(
        db,
        item_id=item_id,
        user_id=current_user.id,
        status=body.status,
        notes=notes_value,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        )
    return _build_watchlist_response(item)


@router.delete("/{item_id}", status_code=204)
async def remove_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove an item from the user's watchlist.

    Does not delete the underlying research result — only the watchlist entry.

    Args:
        item_id: The watchlist item's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If item not found or not owned by user.
    """
    deleted = await delete_watchlist_item(db, item_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        )


@router.post("/{item_id}/import", response_model=WatchlistImportResponse)
async def import_to_store(
    item_id: uuid.UUID,
    body: WatchlistImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import a watchlist item to a connected store.

    Pushes the product data from a watchlist item to the specified
    store connection.  On success, the watchlist item's status is
    updated to 'imported'.

    For Developers:
        Currently simulates the push to the store.  Replace the mock
        logic with real HTTP calls to Shopify/WooCommerce/platform
        product creation APIs once store integrations are built.

    For QA Engineers:
        Verify: successful import updates status to 'imported',
        import to non-existent connection returns 404, import to
        inactive connection returns 400, import without auth returns 401.

    For End Users:
        Push a product from your watchlist directly into your
        connected store's catalog with one click.

    Args:
        item_id: The watchlist item's UUID.
        body: Import request with the target connection_id.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        WatchlistImportResponse with success flag and details.

    Raises:
        HTTPException 404: If watchlist item or connection not found.
        HTTPException 400: If the connection is inactive.
    """
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import selectinload
    from app.models.watchlist import WatchlistItem as WLItem

    # Verify watchlist item ownership, eagerly loading the result
    # relationship to prevent MissingGreenlet during attribute access.
    wl_result = await db.execute(
        sa_select(WLItem)
        .options(selectinload(WLItem.result))
        .where(
            WLItem.id == item_id,
            WLItem.user_id == current_user.id,
        )
    )
    wl_item = wl_result.scalar_one_or_none()
    if not wl_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        )

    # Verify store connection ownership and status
    connection = await get_store_connection(db, body.connection_id, current_user.id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )

    if not connection.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store connection is not active",
        )

    # Simulate pushing the product to the store
    # In production, this would call the store's product creation API
    import uuid as uuid_mod
    external_id = str(uuid_mod.uuid4())[:8]

    product_title = "Unknown Product"
    if wl_item.result:
        product_title = wl_item.result.product_title

    # Update watchlist item status to 'imported'
    wl_item.status = "imported"
    await db.flush()

    return WatchlistImportResponse(
        success=True,
        message=f"Successfully imported '{product_title}' to {connection.platform} store at {connection.store_url}",
        external_product_id=external_id,
    )
