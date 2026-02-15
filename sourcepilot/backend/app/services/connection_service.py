"""
Store connection service for managing links to dropshipping stores.

Handles CRUD operations for store connections, including creating,
listing, updating, deleting, and managing the default store selection.

For Developers:
    All functions accept an AsyncSession and operate within the caller's
    transaction. When setting ``is_default=True``, the service automatically
    clears the default flag on all other connections for the same user.

For Project Managers:
    Store connections link the SourcePilot service to the user's
    dropshipping stores, enabling one-click product imports.

For QA Engineers:
    Test CRUD operations. Verify the ``is_default`` constraint (only one
    default per user). Test that setting a new default clears the old one.

For End Users:
    Connect your dropshipping stores to import products directly.
    Set a default store for quick one-click imports.
"""

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store_connection import StoreConnection
from app.schemas.connections import StoreConnectionCreate, StoreConnectionUpdate

logger = logging.getLogger(__name__)


async def create_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: StoreConnectionCreate,
) -> StoreConnection:
    """
    Create a new store connection for the user.

    If this is the user's first connection, it is automatically set
    as the default import target.

    Args:
        db: Async database session.
        user_id: UUID of the owning user.
        data: Store connection creation data.

    Returns:
        The newly created StoreConnection.
    """
    # Check for duplicate store URL for this user
    dup = await db.execute(
        select(StoreConnection).where(
            StoreConnection.user_id == user_id,
            StoreConnection.store_url == data.store_url,
        ).limit(1)
    )
    if dup.scalar_one_or_none() is not None:
        raise ValueError(f"Store URL already connected: {data.store_url}")

    # Check if user has any existing connections
    existing = await db.execute(
        select(StoreConnection).where(StoreConnection.user_id == user_id).limit(1)
    )
    is_first = existing.scalar_one_or_none() is None

    connection = StoreConnection(
        user_id=user_id,
        store_name=data.store_name,
        platform=data.platform,
        store_url=data.store_url,
        api_key=data.api_key,
        is_default=is_first,  # First connection becomes default
    )
    db.add(connection)
    await db.flush()
    await db.refresh(connection)
    return connection


async def get_connections(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[StoreConnection]:
    """
    Get all store connections for a user.

    Returns connections ordered by default status (default first),
    then by store name.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of StoreConnection records.
    """
    result = await db.execute(
        select(StoreConnection)
        .where(StoreConnection.user_id == user_id)
        .order_by(StoreConnection.is_default.desc(), StoreConnection.store_name)
    )
    return list(result.scalars().all())


async def get_connection(
    db: AsyncSession,
    conn_id: uuid.UUID,
    user_id: uuid.UUID,
) -> StoreConnection | None:
    """
    Get a single store connection by ID, scoped to the requesting user.

    Args:
        db: Async database session.
        conn_id: The store connection's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The StoreConnection if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(StoreConnection).where(
            StoreConnection.id == conn_id,
            StoreConnection.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_connection(
    db: AsyncSession,
    conn_id: uuid.UUID,
    user_id: uuid.UUID,
    data: StoreConnectionUpdate,
) -> StoreConnection | None:
    """
    Update an existing store connection's fields.

    When setting ``is_default=True``, all other connections for the
    same user have their default flag cleared first.

    Args:
        db: Async database session.
        conn_id: The store connection's UUID.
        user_id: The requesting user's UUID (for ownership check).
        data: Update data with optional fields.

    Returns:
        The updated StoreConnection, or None if not found/not owned.
    """
    connection = await get_connection(db, conn_id, user_id)
    if not connection:
        return None

    if data.store_name is not None:
        connection.store_name = data.store_name
    if data.store_url is not None:
        connection.store_url = data.store_url

    if data.is_default is True:
        # Clear default flag on all other connections for this user
        await db.execute(
            update(StoreConnection)
            .where(
                StoreConnection.user_id == user_id,
                StoreConnection.id != conn_id,
            )
            .values(is_default=False)
        )
        connection.is_default = True
    elif data.is_default is False:
        connection.is_default = False

    await db.flush()
    await db.refresh(connection)
    return connection


async def delete_connection(
    db: AsyncSession,
    conn_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a store connection.

    If the deleted connection was the default, the next remaining
    connection (if any) is promoted to default.

    Args:
        db: Async database session.
        conn_id: The store connection's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    connection = await get_connection(db, conn_id, user_id)
    if not connection:
        return False

    was_default = connection.is_default
    await db.delete(connection)
    await db.flush()

    # If we deleted the default, promote the next connection
    if was_default:
        remaining = await db.execute(
            select(StoreConnection)
            .where(StoreConnection.user_id == user_id)
            .order_by(StoreConnection.created_at)
            .limit(1)
        )
        next_conn = remaining.scalar_one_or_none()
        if next_conn:
            next_conn.is_default = True
            await db.flush()

    return True


async def set_default_connection(
    db: AsyncSession,
    conn_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Set a store connection as the default import target.

    Clears the default flag on all other connections for the user
    and sets the specified connection as the new default.

    Args:
        db: Async database session.
        conn_id: The store connection's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if the default was set, False if connection not found/not owned.
    """
    connection = await get_connection(db, conn_id, user_id)
    if not connection:
        return False

    # Clear default on all other connections
    await db.execute(
        update(StoreConnection)
        .where(
            StoreConnection.user_id == user_id,
            StoreConnection.id != conn_id,
        )
        .values(is_default=False)
    )
    connection.is_default = True
    await db.flush()
    return True
