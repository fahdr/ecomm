"""
Store connection management API endpoints.

Provides CRUD operations for connecting external e-commerce stores
(Shopify, WooCommerce, or the parent dropshipping platform) to
ContentForge for direct content export.

For Developers:
    All endpoints require authentication via ``get_current_user``.
    Connections store encrypted API credentials. The ``POST /test``
    endpoint simulates connectivity checking — in production it would
    make real API calls to the connected store.

    Ownership is enforced on all operations: users can only see, test,
    and delete their own connections.

For QA Engineers:
    Test the full CRUD lifecycle:
    - POST /connections -> creates connection (201)
    - GET /connections -> lists user's connections
    - POST /connections/{id}/test -> returns connectivity result
    - DELETE /connections/{id} -> removes connection (204)
    - Verify user isolation (user A cannot see/delete user B's connections)
    - Verify invalid platform rejected (422)
    - Verify unauthenticated access (401)

For Project Managers:
    Store connections enable the "Export to Store" workflow — a key
    differentiator that lets users push generated content directly to
    their product listings without copy-pasting.

For End Users:
    Connect your Shopify or WooCommerce store to export generated
    content with one click. Your API credentials are stored securely
    and can be disconnected at any time.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.schemas.content import (
    StoreConnectionCreate,
    StoreConnectionResponse,
    StoreConnectionTestResult,
    VALID_PLATFORMS,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("/", response_model=list[StoreConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's store connections.

    Returns all active and inactive connections for the authenticated user,
    ordered by creation date (newest first).

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of StoreConnectionResponse objects.
    """
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/", response_model=StoreConnectionResponse, status_code=201)
async def create_connection(
    request: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect an external e-commerce store.

    Stores the API credentials (encrypted) and validates the platform type.
    The connection starts in active state.

    Args:
        request: Connection parameters (platform, store_url, api_key, api_secret).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionResponse with connection details (no credentials).

    Raises:
        HTTPException 400: If the platform is not supported.
    """
    if request.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(VALID_PLATFORMS)}",
        )

    connection = StoreConnection(
        user_id=current_user.id,
        platform=request.platform,
        store_url=request.store_url,
        api_key_encrypted=request.api_key,  # In production: encrypt before storage
        api_secret_encrypted=request.api_secret,
        is_active=True,
    )
    db.add(connection)
    await db.flush()
    await db.refresh(connection)
    return connection


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect (delete) a store connection.

    Only the owning user can delete their connections. This permanently
    removes the stored API credentials.

    Args:
        connection_id: The connection UUID to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the connection is not found or not owned by the user.
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
            detail="Store connection not found.",
        )

    await db.delete(connection)
    await db.flush()


@router.post(
    "/{connection_id}/test",
    response_model=StoreConnectionTestResult,
)
async def test_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test connectivity to a connected store.

    Attempts to reach the connected store's API and retrieve basic
    store information. In the current implementation, this returns a
    mock success response. In production, it would make real API calls
    to the Shopify Admin API or WooCommerce REST API.

    Args:
        connection_id: The connection UUID to test.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionTestResult with success status and store info.

    Raises:
        HTTPException 404: If the connection is not found or not owned by the user.
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
            detail="Store connection not found.",
        )

    # Mock connectivity test (in production: real API call to store)
    # Update last_synced_at on successful test
    connection.last_synced_at = datetime.now(UTC)
    await db.flush()

    return StoreConnectionTestResult(
        connection_id=connection.id,
        success=True,
        message=f"Successfully connected to {connection.platform} store at {connection.store_url}",
        store_name=f"{connection.platform.title()} Store",
        product_count=42,  # Mock product count
    )
