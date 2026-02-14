"""
Supplier account management API endpoints for SourcePilot.

Handles CRUD operations for supplier platform accounts (AliExpress,
CJ Dropshipping, Spocket). Credentials are redacted in responses.

For Developers:
    All endpoints require JWT authentication. Credentials stored in
    the ``credentials`` JSON column are returned as-is (redaction
    should be handled at the application layer in production).

For QA Engineers:
    Test CRUD operations. Verify credentials handling in responses.
    Test duplicate name+platform detection.

For Project Managers:
    These endpoints let users manage their supplier API connections
    for automated product imports.

For End Users:
    Connect your supplier accounts to enable product searching and
    one-click imports from platforms like AliExpress.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.suppliers import (
    SupplierAccountCreate,
    SupplierAccountListResponse,
    SupplierAccountResponse,
    SupplierAccountUpdate,
)
from app.services.supplier_service import (
    create_supplier_account,
    delete_supplier_account,
    get_supplier_accounts,
    update_supplier_account,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _account_to_response(account) -> SupplierAccountResponse:
    """
    Convert a SupplierAccount model to a response schema.

    Uses from_attributes mode since the model field names now match
    the response schema field names directly.

    Args:
        account: The SupplierAccount model instance.

    Returns:
        SupplierAccountResponse with matching field names.
    """
    return SupplierAccountResponse.model_validate(account)


@router.post("/accounts", response_model=SupplierAccountResponse, status_code=201)
async def connect_supplier(
    body: SupplierAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect a new supplier account.

    Creates a supplier account record with the provided credentials.
    Duplicate name+platform combinations per user are rejected.

    Args:
        body: Supplier account creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SupplierAccountResponse with account details.

    Raises:
        HTTPException 400: If a duplicate name+platform combination exists.
    """
    try:
        account = await create_supplier_account(db, current_user.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return _account_to_response(account)


@router.get("/accounts", response_model=SupplierAccountListResponse)
async def list_supplier_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all connected supplier accounts for the authenticated user.

    Returns accounts ordered by platform and name.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SupplierAccountListResponse with all accounts.
    """
    accounts = await get_supplier_accounts(db, current_user.id)
    return SupplierAccountListResponse(
        items=[_account_to_response(a) for a in accounts]
    )


@router.put("/accounts/{account_id}", response_model=SupplierAccountResponse)
async def update_supplier(
    account_id: uuid.UUID,
    body: SupplierAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing supplier account.

    Only provided fields are updated. Credentials can be rotated by
    providing new values.

    Args:
        account_id: The supplier account's UUID.
        body: Update data with optional fields.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        SupplierAccountResponse with updated data.

    Raises:
        HTTPException 404: If account not found or not owned by user.
    """
    account = await update_supplier_account(
        db, account_id, current_user.id, body
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier account not found",
        )
    return _account_to_response(account)


@router.delete("/accounts/{account_id}", status_code=204)
async def disconnect_supplier(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect (delete) a supplier account.

    Removes the supplier account and its stored credentials.

    Args:
        account_id: The supplier account's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If account not found or not owned by user.
    """
    deleted = await delete_supplier_account(db, account_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier account not found",
        )
