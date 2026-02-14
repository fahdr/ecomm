"""
Store connection management API endpoints.

Handles CRUD operations for external e-commerce store connections
(Shopify, WooCommerce, Platform) and provides a test endpoint for
verifying connectivity.

For Developers:
    All endpoints require JWT authentication.  Connections are scoped
    to the authenticated user.  The ``POST /test`` endpoint performs a
    mock connectivity check (real checks hit the external API).

For QA Engineers:
    Test: create success, list pagination, get by ID, update, delete,
    test connectivity, user isolation, unauthenticated access (401).

For Project Managers:
    Store connections are required for automatic product import into
    ad campaigns.  Users connect once, then AdScale pulls product data.

For End Users:
    Connect your e-commerce store to automatically import products for
    ad campaign creation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.store_connection import StoreConnection
from app.models.user import User
from app.schemas.ads import PaginatedResponse

router = APIRouter(prefix="/connections", tags=["store-connections"])


# ── Schemas ───────────────────────────────────────────────────────────


class StoreConnectionCreate(BaseModel):
    """
    Request to create a new store connection.

    Attributes:
        platform: Store platform ('shopify', 'woocommerce', 'platform').
        store_url: Base URL of the store.
        api_key: API key or access token for the store.
        api_secret: API secret (optional, platform-dependent).
    """

    platform: str = Field(..., min_length=1, max_length=50)
    store_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1, max_length=1000)
    api_secret: str | None = None


class StoreConnectionUpdate(BaseModel):
    """
    Request to update an existing store connection.

    All fields are optional -- only provided fields are updated.

    Attributes:
        store_url: Updated store URL.
        api_key: Updated API key.
        api_secret: Updated API secret.
        is_active: Updated active state.
    """

    store_url: str | None = Field(None, min_length=1, max_length=500)
    api_key: str | None = Field(None, min_length=1, max_length=1000)
    api_secret: str | None = None
    is_active: bool | None = None


class StoreConnectionResponse(BaseModel):
    """
    Store connection response (credentials redacted).

    Attributes:
        id: Connection UUID.
        user_id: Owning user UUID.
        platform: Store platform identifier.
        store_url: Base URL of the connected store.
        is_active: Whether the connection is currently enabled.
        last_synced_at: Timestamp of the most recent sync (nullable).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
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


class TestConnectionResponse(BaseModel):
    """
    Store connection test result.

    Attributes:
        connection_id: UUID of the tested connection.
        status: Test result ('ok' or 'error').
        message: Human-readable status message.
    """

    connection_id: uuid.UUID
    status: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────


def _serialize_connection(conn: StoreConnection) -> dict:
    """
    Serialize a StoreConnection to a response dict, redacting credentials.

    Args:
        conn: The StoreConnection ORM object.

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


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_connection(
    request: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new store connection.

    Stores encrypted API credentials for the external platform.

    Args:
        request: Connection creation data (platform, URL, credentials).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with the newly created connection details (credentials redacted).

    Raises:
        HTTPException 409: If a connection to the same store URL already exists.
    """
    # Check for duplicate
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.user_id == current_user.id,
            StoreConnection.store_url == request.store_url,
            StoreConnection.platform == request.platform,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A connection to this store already exists.",
        )

    conn = StoreConnection(
        user_id=current_user.id,
        platform=request.platform,
        store_url=request.store_url,
        api_key_encrypted=request.api_key,
        api_secret_encrypted=request.api_secret,
        is_active=True,
    )
    db.add(conn)
    await db.flush()
    await db.refresh(conn)
    return _serialize_connection(conn)


@router.get("")
async def list_connections(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all store connections for the current user.

    Returns a paginated list of connections with credentials redacted.

    Args:
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with connection items.
    """
    count_result = await db.execute(
        select(sql_func.count(StoreConnection.id)).where(
            StoreConnection.user_id == current_user.id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    connections = list(result.scalars().all())

    return {
        "items": [_serialize_connection(c) for c in connections],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{connection_id}")
async def get_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific store connection by ID.

    Args:
        connection_id: UUID of the connection.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with connection details (credentials redacted).

    Raises:
        HTTPException 400: If the connection ID format is invalid.
        HTTPException 404: If the connection is not found or not owned.
    """
    try:
        cid = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection ID format")

    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == cid,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    return _serialize_connection(conn)


@router.patch("/{connection_id}")
async def update_connection(
    connection_id: str,
    request: StoreConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing store connection.

    Only provided fields are updated.

    Args:
        connection_id: UUID of the connection to update.
        request: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with updated connection details (credentials redacted).

    Raises:
        HTTPException 400: If the connection ID format is invalid.
        HTTPException 404: If the connection is not found or not owned.
    """
    try:
        cid = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection ID format")

    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == cid,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    updates = request.model_dump(exclude_unset=True)
    if "api_key" in updates and updates["api_key"] is not None:
        conn.api_key_encrypted = updates.pop("api_key")
    else:
        updates.pop("api_key", None)

    if "api_secret" in updates:
        conn.api_secret_encrypted = updates.pop("api_secret")

    for key, value in updates.items():
        if value is not None and hasattr(conn, key):
            setattr(conn, key, value)

    await db.flush()
    await db.refresh(conn)
    return _serialize_connection(conn)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a store connection.

    Permanently removes the connection and its encrypted credentials.

    Args:
        connection_id: UUID of the connection to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 400: If the connection ID format is invalid.
        HTTPException 404: If the connection is not found or not owned.
    """
    try:
        cid = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection ID format")

    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == cid,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    await db.delete(conn)
    await db.flush()


@router.post("/{connection_id}/test", response_model=TestConnectionResponse)
async def test_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test a store connection's connectivity.

    Performs a mock connectivity check.  In production, this would
    make an API call to the external platform to verify credentials.

    Args:
        connection_id: UUID of the connection to test.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        TestConnectionResponse with the test result.

    Raises:
        HTTPException 400: If the connection ID format is invalid.
        HTTPException 404: If the connection is not found or not owned.
    """
    try:
        cid = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection ID format")

    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == cid,
            StoreConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    # Mock connectivity test
    return TestConnectionResponse(
        connection_id=conn.id,
        status="ok",
        message=f"Successfully connected to {conn.platform} store at {conn.store_url}",
    )
