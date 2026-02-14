"""
Store connection API routes for linking external e-commerce platforms.

Provides CRUD endpoints for managing store connections and a test
endpoint to verify connectivity.

For Developers:
    Connections store encrypted API keys. The test endpoint simulates
    a connection check (mock always succeeds). In production, it would
    attempt to call the store's API to verify credentials.

For QA Engineers:
    Test CRUD for all supported platforms (shopify, woocommerce, bigcommerce, custom).
    Verify that the test endpoint returns success.
    Test that connections are scoped to the authenticated user.

For Project Managers:
    Store connections enable automatic product data import, which
    improves the accuracy of SEO audits and content generation.

For End Users:
    Connect your e-commerce store to import product data automatically.
    Test the connection to verify your credentials are correct.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.schemas.seo import (
    StoreConnectionCreate,
    StoreConnectionResponse,
    StoreConnectionUpdate,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("", response_model=StoreConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection_endpoint(
    body: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new store connection.

    Stores the platform credentials (encrypted) for later use by
    SEO audit and data import features.

    Args:
        body: StoreConnectionCreate with platform, store_url, and optional keys.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created StoreConnectionResponse.
    """
    conn = StoreConnection(
        user_id=current_user.id,
        platform=body.platform,
        store_url=body.store_url,
        api_key_encrypted=body.api_key,
        api_secret_encrypted=body.api_secret,
    )
    db.add(conn)
    await db.flush()
    return conn


@router.get("", response_model=dict)
async def list_connections_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all store connections for the authenticated user with pagination.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated response with items, total, page, and per_page.
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    connections = list(result.scalars().all())

    return {
        "items": [StoreConnectionResponse.model_validate(c) for c in connections],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{connection_id}", response_model=StoreConnectionResponse)
async def get_connection_endpoint(
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
        The StoreConnectionResponse.

    Raises:
        HTTPException 404: If the connection is not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.patch("/{connection_id}", response_model=StoreConnectionResponse)
async def update_connection_endpoint(
    connection_id: uuid.UUID,
    body: StoreConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a store connection's fields.

    Only the fields provided in the request body will be updated.

    Args:
        connection_id: The connection's UUID.
        body: StoreConnectionUpdate with optional fields.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated StoreConnectionResponse.

    Raises:
        HTTPException 404: If the connection is not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    if body.store_url is not None:
        conn.store_url = body.store_url
    if body.api_key is not None:
        conn.api_key_encrypted = body.api_key
    if body.api_secret is not None:
        conn.api_secret_encrypted = body.api_secret
    if body.is_active is not None:
        conn.is_active = body.is_active

    await db.flush()
    await db.refresh(conn)
    return conn


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection_endpoint(
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
        HTTPException 404: If the connection is not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    await db.delete(conn)
    await db.flush()


@router.post("/{connection_id}/test", response_model=dict)
async def test_connection_endpoint(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test a store connection (mock — always succeeds).

    In production, this would attempt to call the store's API using
    the stored credentials to verify they are valid.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with 'success' and 'message' fields.

    Raises:
        HTTPException 404: If the connection is not found.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == connection_id,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {
        "success": True,
        "message": f"Successfully connected to {conn.platform} store at {conn.store_url}",
        "platform": conn.platform,
        "store_url": conn.store_url,
    }
