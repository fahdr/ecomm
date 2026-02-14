"""
Store connection API endpoints for SourcePilot.

Handles connecting, listing, updating, and disconnecting dropshipping
stores. Users must connect at least one store before importing products.

For Developers:
    All endpoints require JWT authentication. The first store connection
    is automatically set as the default import target.

For QA Engineers:
    Test CRUD operations. Verify the is_default constraint. Test that
    deleting the default promotes the next connection.

For Project Managers:
    These endpoints manage the store connections that enable product imports.

For End Users:
    Connect your dropshipping stores to import products directly.
    Set a default store for quick one-click imports.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.connections import (
    StoreConnectionCreate,
    StoreConnectionListResponse,
    StoreConnectionResponse,
    StoreConnectionUpdate,
)
from app.services.connection_service import (
    create_connection,
    delete_connection,
    get_connection,
    get_connections,
    set_default_connection,
    update_connection,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("", response_model=StoreConnectionResponse, status_code=201)
async def connect_store(
    body: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect a new dropshipping store.

    Creates a store connection record. The first connection is
    automatically set as the default import target.

    Args:
        body: Store connection creation data (store_id, store_name, store_url).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionResponse with the new connection.
    """
    try:
        connection = await create_connection(db, current_user.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return connection


@router.get("", response_model=StoreConnectionListResponse)
async def list_store_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all connected stores for the authenticated user.

    Returns connections ordered by default status (default first),
    then by store name.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionListResponse with all connections.
    """
    connections = await get_connections(db, current_user.id)
    return StoreConnectionListResponse(
        items=[StoreConnectionResponse.model_validate(c) for c in connections]
    )


@router.put("/{conn_id}", response_model=StoreConnectionResponse)
async def update_store_connection(
    conn_id: uuid.UUID,
    body: StoreConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing store connection.

    Only provided fields are updated. Setting is_default=True clears
    the default flag on all other connections.

    Args:
        conn_id: The store connection's UUID.
        body: Update data with optional fields.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionResponse with updated data.

    Raises:
        HTTPException 404: If connection not found or not owned by user.
    """
    connection = await update_connection(db, conn_id, current_user.id, body)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )
    return connection


@router.delete("/{conn_id}", status_code=204)
async def disconnect_store(
    conn_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect (delete) a store connection.

    If the deleted connection was the default, the next remaining
    connection is promoted to default.

    Args:
        conn_id: The store connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If connection not found or not owned by user.
    """
    deleted = await delete_connection(db, conn_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )


@router.post("/{conn_id}/default", status_code=200)
async def set_default(
    conn_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set a store connection as the default import target.

    Clears the default flag on all other connections for the user
    and sets the specified connection as the new default.

    Args:
        conn_id: The store connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If connection not found or not owned by user.
    """
    result = await set_default_connection(db, conn_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )
    return {"status": "ok"}
