"""Fraud API router.

Provides endpoints for reviewing fraud detection results. The platform
automatically runs fraud checks on orders; store owners can view flagged
orders and update their review status.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/fraud-checks/...``
    (full path: ``/api/v1/stores/{store_id}/fraud-checks/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``fraud_service`` handle fraud scoring and checks.
    Fraud checks are created automatically when orders are placed.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - GET list supports ``?page=``, ``?per_page=``, ``?flagged_only=`` params.
    - Fraud risk levels: ``low``, ``medium``, ``high``, ``critical``.
    - Review statuses: ``pending``, ``approved``, ``rejected``.
    - Fraud signals include: mismatched billing/shipping, velocity checks,
      proxy detection, disposable email detection.

**For End Users:**
    - Review flagged orders before fulfillment.
    - See fraud risk scores and contributing signals.
    - Approve or reject suspicious orders.
    - Protect your business from fraudulent transactions.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.fraud import (
    FraudCheckResponse,
    PaginatedFraudCheckResponse,
    ReviewFraudRequest,
)

router = APIRouter(prefix="/stores/{store_id}/fraud-checks", tags=["fraud"])


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedFraudCheckResponse)
async def list_fraud_checks_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    flagged_only: bool = Query(
        False, description="Show only flagged (medium+ risk) checks"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedFraudCheckResponse:
    """List fraud checks for a store with pagination.

    Returns fraud check records for orders, optionally filtered to
    show only flagged (medium risk or higher) checks.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        flagged_only: If true, only return medium+ risk checks.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedFraudCheckResponse with items and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import fraud_service

    try:
        checks, total = await fraud_service.list_fraud_checks(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            flagged_only=flagged_only,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedFraudCheckResponse(
        items=[FraudCheckResponse.model_validate(c) for c in checks],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{check_id}", response_model=FraudCheckResponse)
async def get_fraud_check_endpoint(
    store_id: uuid.UUID,
    check_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FraudCheckResponse:
    """Retrieve a single fraud check with detailed signals.

    Returns the full fraud check including all detected signals
    and their severity levels.

    Args:
        store_id: The UUID of the store.
        check_id: The UUID of the fraud check.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        FraudCheckResponse with detailed fraud signals and risk assessment.

    Raises:
        HTTPException 404: If the store or fraud check is not found.
    """
    from app.services import fraud_service

    # The service doesn't have a get_fraud_check function, so we
    # verify ownership then query inline.
    from sqlalchemy import select as sa_select
    from app.models.store import Store, StoreStatus

    result = await db.execute(sa_select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )
    if store.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    try:
        from app.models.fraud import FraudCheck

        check_result = await db.execute(
            sa_select(FraudCheck).where(
                FraudCheck.id == check_id,
                FraudCheck.store_id == store_id,
            )
        )
        check = check_result.scalar_one_or_none()
        if check is None:
            raise ValueError("Fraud check not found")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return FraudCheckResponse.model_validate(check)


@router.patch("/{check_id}", response_model=FraudCheckResponse)
async def review_fraud_check_endpoint(
    store_id: uuid.UUID,
    check_id: uuid.UUID,
    request: ReviewFraudRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FraudCheckResponse:
    """Review a fraud check (approve or reject).

    Store owners review flagged orders and decide whether to proceed
    with fulfillment (approve) or cancel the order (reject).

    Args:
        store_id: The UUID of the store.
        check_id: The UUID of the fraud check to review.
        request: Review payload with decision and optional note.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        FraudCheckResponse with the updated review status.

    Raises:
        HTTPException 404: If the store or fraud check is not found.
        HTTPException 400: If the check has already been reviewed.
    """
    from app.services import fraud_service

    try:
        # Schema ReviewFraudRequest has is_flagged and notes fields
        # which match the service function parameters directly
        check = await fraud_service.review_fraud_check(
            db,
            store_id=store_id,
            user_id=current_user.id,
            check_id=check_id,
            is_flagged=request.is_flagged,
            notes=request.notes,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return FraudCheckResponse.model_validate(check)
