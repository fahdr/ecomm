"""
Ad account connection API endpoints.

Handles connecting, listing, and disconnecting external advertising
platform accounts (Google Ads, Meta Ads).

For Developers:
    All endpoints require JWT authentication via `get_current_user`.
    The connect endpoint simulates OAuth by accepting an access token directly.

For QA Engineers:
    Test: connect success, duplicate account (409), list pagination,
    disconnect success, disconnect nonexistent (404), unauthenticated (401).

For Project Managers:
    Users must connect at least one ad account before creating campaigns.

For End Users:
    Connect your Google Ads or Meta Ads account to start managing campaigns.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ads import AdAccountConnect, AdAccountResponse, PaginatedResponse
from app.services.account_service import (
    connect_account,
    disconnect_account,
    list_accounts,
)

router = APIRouter(prefix="/accounts", tags=["ad-accounts"])


@router.post("", response_model=AdAccountResponse, status_code=201)
async def connect_ad_account(
    request: AdAccountConnect,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect a new advertising platform account.

    Links an external Google Ads or Meta Ads account to the user's
    AdScale account for campaign management.

    Args:
        request: Account connection data (platform, external ID, name).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AdAccountResponse with the newly connected account details.

    Raises:
        HTTPException 409: If the account is already connected.
    """
    try:
        account = await connect_account(
            db,
            user_id=current_user.id,
            platform=request.platform,
            account_id_external=request.account_id_external,
            account_name=request.account_name,
            access_token=request.access_token,
        )
        return account
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("", response_model=PaginatedResponse)
async def list_ad_accounts(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all connected ad accounts for the current user.

    Returns a paginated list of ad accounts with connection status.

    Args:
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with ad account items.
    """
    accounts, total = await list_accounts(db, current_user.id, offset, limit)
    return PaginatedResponse(
        items=[AdAccountResponse.model_validate(a) for a in accounts],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.delete("/{account_id}", status_code=204)
async def disconnect_ad_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect an ad account (soft delete).

    Marks the account as disconnected and removes the access token.
    Campaign history is preserved for reporting.

    Args:
        account_id: UUID of the ad account to disconnect.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the account is not found or not owned.
    """
    import uuid

    try:
        aid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account ID format")

    success = await disconnect_account(db, aid, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad account not found",
        )
