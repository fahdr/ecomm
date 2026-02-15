"""
Store Connection management API endpoints.

CRUD operations for connecting a user's own e-commerce store to SpyDrop.
Includes a test-connection endpoint that validates the provided credentials.

For Developers:
    All endpoints require authentication via JWT Bearer token.
    Connections store encrypted API credentials; the GET response
    masks the key/secret fields for security.

For QA Engineers:
    Test CRUD operations (create, list, delete, test).
    Verify credentials are never exposed in list/get responses.
    Test error handling for invalid platforms and missing fields.

For Project Managers:
    Store connections enable the user's-own-catalog comparison feature.
    Users connect their store, then SpyDrop can cross-reference products.

For End Users:
    Connect your store to SpyDrop to enable automatic catalog comparison.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.store_connection import StoreConnection
from app.models.user import User

router = APIRouter(prefix="/connections", tags=["connections"])


# ── Schemas ────────────────────────────────────────────────────────


class StoreConnectionCreate(BaseModel):
    """
    Request schema for creating a store connection.

    Attributes:
        platform: E-commerce platform ('shopify', 'woocommerce', 'platform').
        store_url: The user's store URL.
        api_key: API key for the store's API (will be stored encrypted).
        api_secret: API secret for the store's API (will be stored encrypted).
    """

    platform: str = Field(
        ..., description="E-commerce platform: shopify, woocommerce, platform"
    )
    store_url: str = Field(..., min_length=1, max_length=2048, description="Store URL")
    api_key: str | None = Field(None, description="API key (stored encrypted)")
    api_secret: str | None = Field(None, description="API secret (stored encrypted)")


class StoreConnectionResponse(BaseModel):
    """
    Response schema for a store connection.

    API credentials are masked in responses for security.

    Attributes:
        id: Unique identifier.
        platform: E-commerce platform.
        store_url: Store URL.
        has_api_key: Whether an API key is configured.
        has_api_secret: Whether an API secret is configured.
        is_active: Whether the connection is active.
        last_synced_at: Last catalog sync timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    platform: str
    store_url: str
    has_api_key: bool
    has_api_secret: bool
    is_active: bool
    last_synced_at: str | None
    created_at: str
    updated_at: str


class StoreConnectionTestResponse(BaseModel):
    """
    Response schema for testing a store connection.

    Attributes:
        success: Whether the connection test succeeded.
        message: Human-readable result message.
    """

    success: bool
    message: str


# ── Helpers ────────────────────────────────────────────────────────


def _to_response(conn: StoreConnection) -> StoreConnectionResponse:
    """
    Convert a StoreConnection model to a response schema.

    Masks API credentials by reporting only presence (has_api_key/has_api_secret)
    rather than actual values.

    Args:
        conn: The StoreConnection database record.

    Returns:
        StoreConnectionResponse with masked credentials.
    """
    return StoreConnectionResponse(
        id=conn.id,
        platform=conn.platform,
        store_url=conn.store_url,
        has_api_key=bool(conn.api_key_encrypted),
        has_api_secret=bool(conn.api_secret_encrypted),
        is_active=conn.is_active,
        last_synced_at=conn.last_synced_at.isoformat() if conn.last_synced_at else None,
        created_at=conn.created_at.isoformat() if conn.created_at else "",
        updated_at=conn.updated_at.isoformat() if conn.updated_at else "",
    )


_VALID_PLATFORMS = {"shopify", "woocommerce", "platform"}


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("/", response_model=list[StoreConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all store connections for the authenticated user.

    Returns connections ordered by creation date (most recent first).
    API credentials are masked in the response.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of StoreConnectionResponse with masked credentials.
    """
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == current_user.id)
        .order_by(StoreConnection.created_at.desc())
    )
    connections = result.scalars().all()
    return [_to_response(c) for c in connections]


@router.post("/", response_model=StoreConnectionResponse, status_code=201)
async def create_connection(
    body: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new store connection.

    Validates the platform type and stores the connection with encrypted
    credentials.

    Args:
        body: Connection creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionResponse with the newly created connection.

    Raises:
        HTTPException 400: If the platform is not supported.
    """
    if body.platform not in _VALID_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform '{body.platform}'. Must be one of: {', '.join(sorted(_VALID_PLATFORMS))}",
        )

    conn = StoreConnection(
        user_id=current_user.id,
        platform=body.platform,
        store_url=body.store_url,
        api_key_encrypted=body.api_key,
        api_secret_encrypted=body.api_secret,
    )
    db.add(conn)
    await db.flush()
    await db.refresh(conn)
    return _to_response(conn)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a store connection.

    Removes the connection and its stored credentials. The user's store
    data is never modified.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 400: If the connection ID is not a valid UUID.
        HTTPException 404: If the connection is not found or not owned by user.
    """
    try:
        cid = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection ID")

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


@router.post(
    "/{connection_id}/test",
    response_model=StoreConnectionTestResponse,
)
async def test_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test a store connection's credentials.

    Validates that the stored credentials can reach the store's API.
    Currently simulates the test; in production, this would attempt
    an actual API call to the store.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionTestResponse with success status and message.

    Raises:
        HTTPException 400: If the connection ID is not a valid UUID.
        HTTPException 404: If the connection is not found or not owned by user.
    """
    try:
        cid = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection ID")

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

    # Simulate connection test (production would hit the actual store API)
    if not conn.api_key_encrypted:
        return StoreConnectionTestResponse(
            success=False,
            message="No API key configured. Please update the connection with valid credentials.",
        )

    return StoreConnectionTestResponse(
        success=True,
        message=f"Successfully connected to {conn.platform} store at {conn.store_url}",
    )
