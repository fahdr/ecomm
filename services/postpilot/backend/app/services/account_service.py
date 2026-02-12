"""
Social account management service.

Handles connecting, disconnecting, and listing social media accounts.
In the current implementation, OAuth is mocked — connecting an account
creates a record with simulated tokens. Real OAuth integration would
redirect users to platform-specific authorization URLs.

For Developers:
    All functions accept a `db: AsyncSession` and `user: User`. Account
    creation checks the plan limit on `max_secondary` (social accounts).
    The `disconnect_account` function soft-disconnects by setting
    `is_connected=False` rather than deleting the record.

For QA Engineers:
    Test plan limits: free tier allows 1 account, pro allows 10.
    Test disconnect/reconnect flow. Verify that disconnected accounts
    cannot be used for new posts.

For Project Managers:
    Social account management is the first step in the PostPilot workflow.
    Users must connect at least one account before posting.

For End Users:
    Connect your Instagram, Facebook, or TikTok accounts from the
    Accounts page. You can disconnect at any time without losing your
    post history.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.user import User


async def connect_account(
    db: AsyncSession,
    user: User,
    platform: SocialPlatform,
    account_name: str,
    account_id_external: str | None = None,
) -> SocialAccount:
    """
    Connect a new social media account for the user.

    Simulates the OAuth flow by creating a record with mock tokens.
    Enforces the plan's max_secondary limit on total connected accounts.

    Args:
        db: Async database session.
        user: The authenticated user.
        platform: Social platform to connect.
        account_name: Display name for the account.
        account_id_external: Optional external platform ID (auto-generated if None).

    Returns:
        The newly created SocialAccount.

    Raises:
        ValueError: If the user has reached their plan's account limit.
    """
    # Check plan limit for social accounts
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_secondary != -1:
        result = await db.execute(
            select(func.count(SocialAccount.id)).where(
                SocialAccount.user_id == user.id,
                SocialAccount.is_connected.is_(True),
            )
        )
        current_count = result.scalar() or 0
        if current_count >= plan_limits.max_secondary:
            raise ValueError(
                f"Account limit reached ({plan_limits.max_secondary} accounts). "
                "Upgrade your plan to connect more accounts."
            )

    # Generate mock external ID if not provided
    if not account_id_external:
        account_id_external = f"{platform.value}_{uuid.uuid4().hex[:12]}"

    account = SocialAccount(
        user_id=user.id,
        platform=platform,
        account_name=account_name,
        account_id_external=account_id_external,
        access_token_enc=f"mock_access_{uuid.uuid4().hex[:16]}",
        refresh_token_enc=f"mock_refresh_{uuid.uuid4().hex[:16]}",
        is_connected=True,
        connected_at=datetime.now(UTC),
    )
    db.add(account)
    await db.flush()
    return account


async def disconnect_account(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> SocialAccount:
    """
    Disconnect a social media account (soft disconnect).

    Sets `is_connected=False` and clears tokens. The account record is
    preserved for historical reference (post history, metrics).

    Args:
        db: Async database session.
        user: The authenticated user.
        account_id: UUID of the account to disconnect.

    Returns:
        The updated SocialAccount.

    Raises:
        ValueError: If the account is not found or doesn't belong to the user.
    """
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise ValueError("Account not found")

    account.is_connected = False
    account.access_token_enc = None
    account.refresh_token_enc = None
    await db.flush()
    return account


async def list_accounts(
    db: AsyncSession,
    user: User,
) -> list[SocialAccount]:
    """
    List all social accounts for the user (connected and disconnected).

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        List of SocialAccount records ordered by creation date descending.
    """
    result = await db.execute(
        select(SocialAccount)
        .where(SocialAccount.user_id == user.id)
        .order_by(SocialAccount.created_at.desc())
    )
    return list(result.scalars().all())


async def get_account(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> SocialAccount | None:
    """
    Get a single social account by ID.

    Args:
        db: Async database session.
        user: The authenticated user.
        account_id: UUID of the account to retrieve.

    Returns:
        The SocialAccount if found and belongs to user, None otherwise.
    """
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()
