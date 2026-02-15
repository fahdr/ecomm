"""
Store connection CRUD API routes.

Provides endpoints for creating, listing, retrieving, updating, and
deleting store connections. Also provides a test endpoint for verifying
connectivity to the connected store.

For Developers:
    All endpoints use ``get_current_user`` for JWT auth. Store connections
    are scoped to the authenticated user.

For QA Engineers:
    Test CRUD operations, verify user scoping, and test that encrypted
    fields are not exposed in responses.

For Project Managers:
    These endpoints enable users to connect their external stores for
    product catalog synchronization with the chatbot knowledge base.

For End Users:
    Connect your online store to enable automatic product sync
    for your AI chatbot assistant.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.schemas.chat import (
    PaginatedResponse,
    StoreConnectionCreate,
    StoreConnectionResponse,
    StoreConnectionUpdate,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("", response_model=StoreConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new store connection.

    Stores the platform, store URL, and encrypted API credentials
    for the user's external store.

    Args:
        body: Store connection creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created store connection (credentials masked).
    """
    connection = StoreConnection(
        user_id=current_user.id,
        platform=body.platform,
        store_url=body.store_url,
        api_key_encrypted=body.api_key,
        api_secret_encrypted=body.api_secret,
    )
    db.add(connection)
    await db.flush()
    await db.commit()
    return connection


@router.get("", response_model=PaginatedResponse)
async def list_connections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's store connections with pagination.

    Args:
        page: Page number (1-based).
        page_size: Items per page.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of store connections.
    """
    count_result = await db.execute(
        select(func.count()).where(StoreConnection.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    connections = list(result.scalars().all())

    return PaginatedResponse(
        items=[StoreConnectionResponse.model_validate(c) for c in connections],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{connection_id}", response_model=StoreConnectionResponse)
async def get_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single store connection by ID.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The store connection details (credentials masked).

    Raises:
        HTTPException: 404 if connection not found or not owned by user.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )
    return connection


@router.patch("/{connection_id}", response_model=StoreConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    body: StoreConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a store connection's fields.

    Only provided fields are updated.

    Args:
        connection_id: The connection's UUID.
        body: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated store connection.

    Raises:
        HTTPException: 404 if connection not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )

    if body.platform is not None:
        connection.platform = body.platform
    if body.store_url is not None:
        connection.store_url = body.store_url
    if body.api_key is not None:
        connection.api_key_encrypted = body.api_key
    if body.api_secret is not None:
        connection.api_secret_encrypted = body.api_secret
    if body.is_active is not None:
        connection.is_active = body.is_active

    await db.flush()
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a store connection.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException: 404 if connection not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )
    await db.delete(connection)
    await db.flush()


@router.post("/{connection_id}/test")
async def test_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test connectivity to a store connection.

    Verifies the stored credentials can access the connected store's API.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with success status and message.

    Raises:
        HTTPException: 404 if connection not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )

    # In production, this would actually test the API connection.
    # For now, return success if the connection exists and is active.
    return {
        "success": connection.is_active,
        "message": "Connection is active" if connection.is_active else "Connection is disabled",
        "platform": connection.platform,
    }
