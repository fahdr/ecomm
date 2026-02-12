"""
Ad account connection service.

Handles connecting, listing, and disconnecting external advertising
platform accounts (Google Ads, Meta Ads). Uses mock OAuth in
development mode.

For Developers:
    The `connect_account` function simulates an OAuth flow by accepting
    an access token directly. In production, this would redirect to
    the platform's OAuth consent screen and exchange a code for a token.

For QA Engineers:
    Test connecting accounts (duplicate detection), listing per user,
    and disconnecting (verify is_connected flips to False).

For Project Managers:
    Ad accounts must be connected before users can create campaigns.
    This service manages the lifecycle of those connections.

For End Users:
    Connect your advertising accounts to manage campaigns from AdScale.
"""

import uuid

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_account import AccountStatus, AdAccount, AdPlatform


async def connect_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    platform: AdPlatform,
    account_id_external: str,
    account_name: str,
    access_token: str | None = None,
) -> AdAccount:
    """
    Connect a new advertising platform account.

    Creates an AdAccount record linking the user to an external ad platform.
    If the access_token is not provided, a mock token is generated.

    Args:
        db: Async database session.
        user_id: UUID of the user connecting the account.
        platform: The advertising platform (google or meta).
        account_id_external: The platform's own account identifier.
        account_name: Human-readable account name.
        access_token: OAuth access token (optional, mocked in dev).

    Returns:
        The newly created AdAccount.

    Raises:
        ValueError: If an account with the same external ID already exists for this user.
    """
    # Check for duplicate
    result = await db.execute(
        select(AdAccount).where(
            AdAccount.user_id == user_id,
            AdAccount.account_id_external == account_id_external,
            AdAccount.platform == platform,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError(
            f"Account {account_id_external} on {platform.value} is already connected."
        )

    # Mock token if not provided
    token_enc = access_token or f"mock_token_{uuid.uuid4().hex[:16]}"

    account = AdAccount(
        user_id=user_id,
        platform=platform,
        account_id_external=account_id_external,
        account_name=account_name,
        access_token_enc=token_enc,
        is_connected=True,
        status=AccountStatus.active,
    )
    db.add(account)
    await db.flush()
    return account


async def list_accounts(
    db: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[AdAccount], int]:
    """
    List all ad accounts for a user with pagination.

    Args:
        db: Async database session.
        user_id: UUID of the user.
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50).

    Returns:
        Tuple of (list of AdAccounts, total count).
    """
    # Count total
    count_result = await db.execute(
        select(sql_func.count(AdAccount.id)).where(AdAccount.user_id == user_id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(AdAccount)
        .where(AdAccount.user_id == user_id)
        .order_by(AdAccount.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    accounts = list(result.scalars().all())

    return accounts, total


async def get_account(
    db: AsyncSession,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AdAccount | None:
    """
    Get a specific ad account by ID, scoped to the user.

    Args:
        db: Async database session.
        account_id: UUID of the ad account.
        user_id: UUID of the owning user.

    Returns:
        The AdAccount if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(AdAccount).where(
            AdAccount.id == account_id,
            AdAccount.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def disconnect_account(
    db: AsyncSession,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Disconnect an ad account (soft disconnect — marks as disconnected).

    Sets is_connected to False and status to paused. Does not delete
    the record so historical campaign data is preserved.

    Args:
        db: Async database session.
        account_id: UUID of the ad account.
        user_id: UUID of the owning user.

    Returns:
        True if the account was found and disconnected, False if not found.
    """
    account = await get_account(db, account_id, user_id)
    if not account:
        return False

    account.is_connected = False
    account.status = AccountStatus.paused
    account.access_token_enc = None
    await db.flush()
    return True
