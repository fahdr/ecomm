"""
Store connection API endpoints for linking external e-commerce platforms.

Provides CRUD operations for store connections, plus a test endpoint
to verify that credentials work.

For Developers:
    All endpoints require authentication via ``get_current_user``.
    Connection credentials are stored as-is in the MVP (encryption TBD).
    The test endpoint simulates a connection check.

For QA Engineers:
    Test: create, list, get, update, delete, test connection,
    duplicate platform+store_url rejection, deactivation, 404 handling.

For Project Managers:
    Store connections bridge FlowSend and the user's e-commerce platform.
    They enable contact import and event-driven automations.

For End Users:
    Connect your Shopify, WooCommerce, or other store to automatically
    sync customer data and trigger email flows.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.schemas.email import PaginatedResponse

router = APIRouter(prefix="/connections", tags=["connections"])


# ── Schemas ───────────────────────────────────────────────────────────────


class StoreConnectionCreate(BaseModel):
    """
    Request body for creating a store connection.

    Attributes:
        platform: E-commerce platform ("shopify", "woocommerce", "bigcommerce").
        store_url: The store's base URL.
        api_key: API key for the store (will be stored encrypted in production).
        api_secret: API secret (optional, depending on platform).
    """

    platform: str = Field(..., min_length=1, max_length=50)
    store_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1)
    api_secret: str = ""


class StoreConnectionUpdate(BaseModel):
    """
    Request body for updating a store connection.

    All fields are optional — only provided fields are updated.

    Attributes:
        api_key: Updated API key.
        api_secret: Updated API secret.
        is_active: Whether the connection is active.
    """

    api_key: str | None = None
    api_secret: str | None = None
    is_active: bool | None = None


class StoreConnectionResponse(BaseModel):
    """
    Store connection data returned from the API.

    Credentials are masked for security.

    Attributes:
        id: Connection UUID.
        user_id: Owning user UUID.
        platform: E-commerce platform name.
        store_url: Store base URL.
        is_active: Whether the connection is active.
        last_synced_at: Last successful sync timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    platform: str
    store_url: str
    is_active: bool
    last_synced_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ConnectionTestResponse(BaseModel):
    """
    Result of testing a store connection.

    Attributes:
        success: Whether the connection test succeeded.
        message: Human-readable result message.
    """

    success: bool
    message: str


# ── Helper functions ─────────────────────────────────────────────────────


def _connection_to_response(conn: StoreConnection) -> dict:
    """
    Convert a StoreConnection model to a response dict.

    Masks credentials and serializes datetimes to ISO format.

    Args:
        conn: The StoreConnection model instance.

    Returns:
        Dict suitable for StoreConnectionResponse.
    """
    return {
        "id": conn.id,
        "user_id": conn.user_id,
        "platform": conn.platform,
        "store_url": conn.store_url,
        "is_active": conn.is_active,
        "last_synced_at": conn.last_synced_at.isoformat() if conn.last_synced_at else None,
        "created_at": conn.created_at.isoformat() if conn.created_at else "",
        "updated_at": conn.updated_at.isoformat() if conn.updated_at else "",
    }


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("", response_model=StoreConnectionResponse, status_code=201)
async def create_connection(
    body: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new store connection.

    Args:
        body: Connection creation data (platform, store_url, credentials).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created store connection (credentials masked).
    """
    conn = StoreConnection(
        user_id=current_user.id,
        platform=body.platform.lower(),
        store_url=body.store_url.rstrip("/"),
        api_key_encrypted=body.api_key,
        api_secret_encrypted=body.api_secret,
    )
    db.add(conn)
    await db.flush()
    return _connection_to_response(conn)


@router.get("", response_model=PaginatedResponse[StoreConnectionResponse])
async def list_connections(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List store connections for the authenticated user.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of store connections.
    """
    count_result = await db.execute(
        select(func.count(StoreConnection.id)).where(
            StoreConnection.user_id == current_user.id
        )
    )
    total = count_result.scalar() or 0

    query = (
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    connections = list(result.scalars().all())

    return PaginatedResponse(
        items=[_connection_to_response(c) for c in connections],
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
        The store connection data.

    Raises:
        HTTPException 404: If connection not found.
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
    return _connection_to_response(conn)


@router.patch("/{connection_id}", response_model=StoreConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    body: StoreConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a store connection's credentials or active status.

    Args:
        connection_id: The connection's UUID.
        body: Update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated store connection.

    Raises:
        HTTPException 404: If connection not found.
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

    if body.api_key is not None:
        conn.api_key_encrypted = body.api_key
    if body.api_secret is not None:
        conn.api_secret_encrypted = body.api_secret
    if body.is_active is not None:
        conn.is_active = body.is_active

    await db.flush()
    return _connection_to_response(conn)


@router.delete("/{connection_id}", status_code=204)
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
        HTTPException 404: If connection not found.
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


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test a store connection by simulating an API call.

    In the MVP, this always returns success if the connection exists.
    In production, this would make a real API call to the store.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ConnectionTestResponse with success status and message.

    Raises:
        HTTPException 404: If connection not found.
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

    # MVP: simulate a successful test
    return ConnectionTestResponse(
        success=True,
        message=f"Successfully connected to {conn.platform} store at {conn.store_url}",
    )
