"""
Supplier account service for managing supplier platform connections.

Handles CRUD operations for supplier accounts, including creating,
listing, updating, and deleting supplier credential records.

For Developers:
    All functions accept an AsyncSession and operate within the caller's
    transaction. Credentials should be encrypted before storage
    in production (currently stored as-is for development).

For Project Managers:
    This service manages the user's connections to supplier platforms,
    enabling automated product discovery and import.

For QA Engineers:
    Test CRUD operations. Verify duplicate detection by name+platform
    per user. Test update with partial field changes.

For End Users:
    The supplier service manages your connections to platforms like
    AliExpress, CJ Dropshipping, and Spocket.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier_account import SupplierAccount
from app.schemas.suppliers import SupplierAccountCreate, SupplierAccountUpdate

logger = logging.getLogger(__name__)


async def create_supplier_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: SupplierAccountCreate,
) -> SupplierAccount:
    """
    Create a new supplier account connection.

    Checks for duplicate name+platform per user before creating.

    Args:
        db: Async database session.
        user_id: UUID of the owning user.
        data: Supplier account creation data.

    Returns:
        The newly created SupplierAccount.

    Raises:
        ValueError: If a duplicate name+platform combination exists for the user.
    """
    # Check for duplicate name+platform per user
    existing = await db.execute(
        select(SupplierAccount).where(
            SupplierAccount.user_id == user_id,
            SupplierAccount.name == data.name,
            SupplierAccount.platform == data.platform,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(
            f"Supplier account with name '{data.name}' and platform "
            f"'{data.platform}' already exists."
        )

    account = SupplierAccount(
        user_id=user_id,
        name=data.name,
        platform=data.platform,
        credentials=data.credentials,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


async def get_supplier_accounts(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[SupplierAccount]:
    """
    Get all supplier accounts for a user.

    Returns accounts ordered by platform and then by name.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of SupplierAccount records.
    """
    result = await db.execute(
        select(SupplierAccount)
        .where(SupplierAccount.user_id == user_id)
        .order_by(SupplierAccount.platform, SupplierAccount.name)
    )
    return list(result.scalars().all())


async def get_supplier_account(
    db: AsyncSession,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SupplierAccount | None:
    """
    Get a single supplier account by ID, scoped to the requesting user.

    Args:
        db: Async database session.
        account_id: The supplier account's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The SupplierAccount if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(SupplierAccount).where(
            SupplierAccount.id == account_id,
            SupplierAccount.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_supplier_account(
    db: AsyncSession,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    data: SupplierAccountUpdate,
) -> SupplierAccount | None:
    """
    Update an existing supplier account's fields.

    Only provided (non-None) fields are updated. Credentials can be
    rotated by providing new values.

    Args:
        db: Async database session.
        account_id: The supplier account's UUID.
        user_id: The requesting user's UUID (for ownership check).
        data: Update data with optional fields.

    Returns:
        The updated SupplierAccount, or None if not found/not owned.
    """
    account = await get_supplier_account(db, account_id, user_id)
    if not account:
        return None

    if data.name is not None:
        account.name = data.name
    if data.platform is not None:
        account.platform = data.platform
    if data.credentials is not None:
        account.credentials = data.credentials
    if data.is_active is not None:
        account.is_active = data.is_active

    await db.flush()
    await db.refresh(account)
    return account


async def delete_supplier_account(
    db: AsyncSession,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a supplier account.

    Args:
        db: Async database session.
        account_id: The supplier account's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    account = await get_supplier_account(db, account_id, user_id)
    if not account:
        return False

    await db.delete(account)
    await db.flush()
    return True
