"""Store API router.

Provides CRUD endpoints for managing dropshipping stores. All endpoints
require authentication and enforce tenant isolation — users can only
access their own stores.

**For Developers:**
    The router is prefixed with ``/stores`` (full path: ``/api/v1/stores/...``).
    The ``get_current_user`` dependency is used for authentication.

**For End Users:**
    - Create a new store by providing a name, niche, and optional description.
    - View all your stores or a single store by its ID.
    - Update store settings or soft-delete a store you no longer need.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - GET/PATCH/DELETE on a non-existent or another user's store returns 404.
    - DELETE performs a soft-delete (status set to ``deleted``).
    - Creating a store returns 201 with the full store data including slug.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_store_limit, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.store import (
    CloneStoreRequest,
    CloneStoreResponse,
    CreateStoreRequest,
    StoreResponse,
    UpdateStoreRequest,
)
from app.services.clone_service import clone_store
from app.services.store_service import (
    create_store,
    delete_store,
    get_store,
    list_stores,
    update_store,
)

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store_endpoint(
    request: CreateStoreRequest,
    current_user: User = Depends(check_store_limit),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Create a new store for the authenticated user.

    Plan enforcement: the ``check_store_limit`` dependency verifies
    the user has not exceeded their plan's store limit before allowing
    creation. Returns 403 if the limit is reached.

    Args:
        request: Store creation payload with name, niche, and optional description.
        current_user: The authenticated user (verified within plan limits).
        db: Async database session injected by FastAPI.

    Returns:
        StoreResponse with the newly created store data, including the
        auto-generated slug.
    """
    store = await create_store(
        db,
        user_id=current_user.id,
        name=request.name,
        niche=request.niche,
        description=request.description,
        store_type=request.store_type,
    )
    return StoreResponse.model_validate(store)


@router.get("", response_model=list[StoreResponse])
async def list_stores_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StoreResponse]:
    """List all non-deleted stores belonging to the authenticated user.

    Args:
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        A list of StoreResponse objects ordered by creation date (newest first).
    """
    stores = await list_stores(db, user_id=current_user.id)
    return [StoreResponse.model_validate(s) for s in stores]


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Retrieve a single store by ID, verifying ownership.

    Args:
        store_id: The UUID of the store to retrieve.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        StoreResponse with the store data.

    Raises:
        HTTPException: 404 if the store is not found or belongs to another user.
    """
    try:
        store = await get_store(db, user_id=current_user.id, store_id=store_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return StoreResponse.model_validate(store)


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store_endpoint(
    store_id: uuid.UUID,
    request: UpdateStoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Update a store's settings (partial update).

    Only provided fields are updated. The slug is regenerated if the
    name changes.

    Args:
        store_id: The UUID of the store to update.
        request: Partial update payload.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        StoreResponse with the updated store data.

    Raises:
        HTTPException: 404 if the store is not found or belongs to another user.
    """
    try:
        store = await update_store(
            db,
            user_id=current_user.id,
            store_id=store_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return StoreResponse.model_validate(store)


@router.delete("/{store_id}", response_model=StoreResponse)
async def delete_store_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Soft-delete a store (set status to ``deleted``).

    Args:
        store_id: The UUID of the store to delete.
        current_user: The authenticated user, injected by dependency.
        db: Async database session injected by FastAPI.

    Returns:
        StoreResponse with the soft-deleted store data (status will be ``deleted``).

    Raises:
        HTTPException: 404 if the store is not found or belongs to another user.
    """
    try:
        store = await delete_store(db, user_id=current_user.id, store_id=store_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return StoreResponse.model_validate(store)


@router.post(
    "/{store_id}/clone",
    response_model=CloneStoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_store_endpoint(
    store_id: uuid.UUID,
    request: CloneStoreRequest,
    current_user: User = Depends(check_store_limit),
    db: AsyncSession = Depends(get_db),
) -> CloneStoreResponse:
    """Clone an existing store with all its products, themes, and settings.

    Creates a deep copy of the source store including products, variants,
    themes, discounts, categories, tax rules, and suppliers. Orders,
    reviews, customers, and analytics are NOT cloned.

    Plan enforcement: the ``check_store_limit`` dependency verifies
    the user has not exceeded their plan's store limit.

    Args:
        store_id: The UUID of the store to clone.
        request: Optional name override for the cloned store.
        current_user: The authenticated user (verified within plan limits).
        db: Async database session injected by FastAPI.

    Returns:
        CloneStoreResponse with the new store and the source store ID.

    Raises:
        HTTPException: 404 if the source store is not found or belongs to
            another user.
    """
    try:
        new_store = await clone_store(
            db,
            user_id=current_user.id,
            source_store_id=store_id,
            new_name=request.new_name,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return CloneStoreResponse(
        store=StoreResponse.model_validate(new_store),
        source_store_id=store_id,
    )
