"""
Social account management API routes.

Provides endpoints for connecting, disconnecting, and listing social media
accounts. All endpoints require authentication via JWT Bearer token.

For Developers:
    All routes use `get_current_user` dependency for auth. Account
    connection simulates OAuth. Disconnect is a soft operation that
    preserves the record but clears tokens.

For QA Engineers:
    Test: connect account (201), list accounts (200), disconnect (200),
    plan limit enforcement (403), and unauthenticated access (401).

For Project Managers:
    These endpoints power the Accounts page in the dashboard where
    users manage their social media connections.

For End Users:
    Connect your Instagram, Facebook, or TikTok accounts to start
    scheduling posts through PostPilot.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.social import SocialAccountConnect, SocialAccountResponse
from app.services.account_service import (
    connect_account,
    disconnect_account,
    list_accounts,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post(
    "",
    response_model=SocialAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a social media account",
)
async def connect_social_account(
    payload: SocialAccountConnect,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect a new social media account.

    Simulates the OAuth flow by creating a record with mock tokens.
    Enforces the plan's account limit (max_secondary).

    Args:
        payload: Connection request with platform and account name.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly connected SocialAccountResponse.

    Raises:
        HTTPException 403: If the user has reached their account limit.
    """
    try:
        account = await connect_account(
            db=db,
            user=current_user,
            platform=payload.platform,
            account_name=payload.account_name,
            account_id_external=payload.account_id_external,
        )
        return account
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get(
    "",
    response_model=list[SocialAccountResponse],
    summary="List all social accounts",
)
async def get_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all social accounts for the authenticated user.

    Returns both connected and disconnected accounts, ordered by
    creation date (newest first).

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of SocialAccountResponse records.
    """
    return await list_accounts(db=db, user=current_user)


@router.delete(
    "/{account_id}",
    response_model=SocialAccountResponse,
    summary="Disconnect a social account",
)
async def disconnect_social_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect a social media account.

    Soft-disconnects by setting is_connected=False and clearing tokens.
    The account record is preserved for post history and analytics.

    Args:
        account_id: UUID of the account to disconnect.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated SocialAccountResponse with is_connected=False.

    Raises:
        HTTPException 404: If the account is not found or doesn't belong to the user.
    """
    try:
        account = await disconnect_account(
            db=db, user=current_user, account_id=account_id
        )
        return account
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
