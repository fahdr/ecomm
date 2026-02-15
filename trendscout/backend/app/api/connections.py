"""
Store connection API endpoints for TrendScout.

Manages connections to external e-commerce platforms (Shopify, WooCommerce,
platform).  Users configure store connections to enable product imports
from the watchlist and product data fetching during research runs.

For Developers:
    All endpoints require JWT authentication via ``get_current_user``.
    API credentials are stored encrypted and never returned in responses.
    The ``/test`` endpoint performs a lightweight connectivity check.

For QA Engineers:
    Test CRUD operations: create connection, list connections, delete
    connection, test connectivity.  Verify that credentials are never
    leaked in responses (only ``has_api_key`` / ``has_api_secret`` flags).
    Verify invalid platforms are rejected with 400.

For Project Managers:
    Store connections enable the import-to-store workflow.  Users must
    connect at least one store before they can push products from
    their watchlist.

For End Users:
    Connect your Shopify, WooCommerce, or platform store under the
    Connections tab.  This allows you to push winning products
    directly from your research results into your store catalog.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.research import (
    StoreConnectionCreate,
    StoreConnectionListResponse,
    StoreConnectionResponse,
    StoreConnectionTestResponse,
)
from app.services.research_service import (
    create_store_connection,
    delete_store_connection,
    get_store_connections,
    test_store_connection,
)

router = APIRouter(prefix="/connections", tags=["connections"])


def _build_connection_response(conn) -> StoreConnectionResponse:
    """
    Build a StoreConnectionResponse from a StoreConnection ORM object.

    Redacts credentials — only reports whether they have been set.

    Args:
        conn: StoreConnection ORM instance.

    Returns:
        StoreConnectionResponse with has_api_key/has_api_secret flags.
    """
    return StoreConnectionResponse(
        id=conn.id,
        user_id=conn.user_id,
        platform=conn.platform,
        store_url=conn.store_url,
        has_api_key=bool(conn.api_key_encrypted),
        has_api_secret=bool(conn.api_secret_encrypted),
        is_active=conn.is_active,
        last_synced_at=conn.last_synced_at,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


@router.post("", response_model=StoreConnectionResponse, status_code=201)
async def create_connection(
    body: StoreConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new store connection.

    Validates the platform identifier and stores encrypted API credentials.

    Args:
        body: Connection creation data (platform, store_url, api_key, api_secret).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionResponse with credentials redacted.

    Raises:
        HTTPException 400: If the platform is not valid.
    """
    try:
        connection = await create_store_connection(
            db,
            user_id=current_user.id,
            platform=body.platform,
            store_url=body.store_url,
            api_key_encrypted=body.api_key,
            api_secret_encrypted=body.api_secret,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return _build_connection_response(connection)


@router.get("", response_model=StoreConnectionListResponse)
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all store connections for the authenticated user.

    Returns all connections ordered by platform name. Credentials are redacted.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionListResponse with all user connections.
    """
    connections = await get_store_connections(db, current_user.id)
    return StoreConnectionListResponse(
        items=[_build_connection_response(c) for c in connections],
    )


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a store connection.

    Removes the connection and its stored credentials permanently.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If connection not found or not owned by user.
    """
    deleted = await delete_store_connection(db, connection_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )


@router.post("/{connection_id}/test", response_model=StoreConnectionTestResponse)
async def test_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test connectivity to a store connection.

    Attempts a lightweight health check against the store's API
    and reports success or failure with a descriptive message.

    Args:
        connection_id: The connection's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StoreConnectionTestResponse with success flag and message.

    Raises:
        HTTPException 404: If connection not found or not owned by user.
    """
    success, message = await test_store_connection(
        db, connection_id, current_user.id
    )
    if not success and message == "Connection not found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store connection not found",
        )

    return StoreConnectionTestResponse(success=success, message=message)
