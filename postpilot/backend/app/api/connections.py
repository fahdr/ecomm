"""
Store connection management API routes.

Provides CRUD endpoints for connecting, updating, listing, and removing
external e-commerce store connections. All endpoints require authentication.

For Developers:
    Store connections allow users to link their Shopify/WooCommerce stores
    for product import. The encrypted credential fields are never returned
    in API responses.

For QA Engineers:
    Test: create connection (201), list connections (200), get single (200),
    update connection (200), delete connection (204), and unauthenticated
    access (401).

For Project Managers:
    Store connections enable the product import workflow that feeds into
    the automated content generation pipeline.

For End Users:
    Connect your online store to import products for automatic social
    media post generation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.schemas.social import (
    StoreConnectionCreate,
    StoreConnectionResponse,
    StoreConnectionUpdate,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post(
    "",
    response_model=StoreConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a store connection",
)
async def create_connection(
    payload: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new external store connection.

    Stores encrypted API credentials for future product imports.

    Args:
        payload: Connection details (platform, store_url, api_key, api_secret).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created StoreConnectionResponse.
    """
    connection = StoreConnection(
        user_id=current_user.id,
        platform=payload.platform,
        store_url=payload.store_url,
        api_key_encrypted=payload.api_key,
        api_secret_encrypted=payload.api_secret,
        is_active=True,
    )
    db.add(connection)
    await db.flush()
    return connection


@router.get(
    "",
    response_model=list[StoreConnectionResponse],
    summary="List store connections",
)
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all store connections for the authenticated user.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of StoreConnectionResponse records.
    """
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/{connection_id}",
    response_model=StoreConnectionResponse,
    summary="Get a store connection",
)
async def get_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single store connection by ID.

    Args:
        connection_id: UUID of the connection.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The StoreConnectionResponse.

    Raises:
        HTTPException 404: If connection not found or doesn't belong to user.
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


@router.patch(
    "/{connection_id}",
    response_model=StoreConnectionResponse,
    summary="Update a store connection",
)
async def update_connection(
    connection_id: uuid.UUID,
    payload: StoreConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing store connection (partial update).

    Args:
        connection_id: UUID of the connection to update.
        payload: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated StoreConnectionResponse.

    Raises:
        HTTPException 404: If connection not found.
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

    if payload.store_url is not None:
        connection.store_url = payload.store_url
    if payload.api_key is not None:
        connection.api_key_encrypted = payload.api_key
    if payload.api_secret is not None:
        connection.api_secret_encrypted = payload.api_secret
    if payload.is_active is not None:
        connection.is_active = payload.is_active

    await db.flush()
    await db.refresh(connection)
    return connection


@router.delete(
    "/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a store connection",
)
async def delete_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a store connection permanently.

    Args:
        connection_id: UUID of the connection to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If connection not found.
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
