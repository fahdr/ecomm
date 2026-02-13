"""Refund API router.

Provides endpoints for managing refund requests. Store owners can create,
list, update, and process refunds for orders. In a dropshipping model,
refunds are handled between the store owner and customer (the supplier
relationship is separate).

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/refunds/...``
    (full path: ``/api/v1/stores/{store_id}/refunds/...``).
    The ``get_current_user`` dependency is used for authentication.
    The ``refund_service`` handles refund logic including Stripe integration.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST create returns 201 with the refund data.
    - Processing a refund triggers Stripe refund (or mock in dev).
    - Refund statuses: pending, approved, processed, rejected.
    - Cannot process an already-processed refund (returns 400).

**For End Users:**
    - Create refund requests for orders from your dashboard.
    - Track refund status and add notes.
    - Process refunds to issue the payment back to the customer.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.refund import (
    CreateRefundRequest,
    PaginatedRefundResponse,
    RefundResponse,
    UpdateRefundRequest,
)

router = APIRouter(prefix="/stores/{store_id}/refunds", tags=["refunds"])


# ---------------------------------------------------------------------------
# Local schemas (not present in app.schemas.refund)
# ---------------------------------------------------------------------------


class ProcessRefundResponse(BaseModel):
    """Response after processing a refund.

    Attributes:
        refund: The updated refund record.
        message: Human-readable status message.
    """

    refund: RefundResponse
    message: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund_endpoint(
    store_id: uuid.UUID,
    request: CreateRefundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Create a new refund request for an order.

    Creates a refund in ``pending`` status. The refund amount can be
    partial or full. The order must belong to the specified store.

    Args:
        store_id: The UUID of the store.
        request: Refund creation payload with order_id, amount, and reason.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        RefundResponse with the newly created refund data.

    Raises:
        HTTPException 404: If the store or order is not found.
        HTTPException 400: If the refund amount exceeds the order total
            or a refund already exists for this order.
    """
    from app.services import refund_service

    try:
        from app.models.refund import RefundReason

        # Map the free-text reason to a RefundReason enum value.
        # Default to "other" if the provided reason doesn't match an enum member.
        reason_text = request.reason
        try:
            reason_enum = RefundReason(reason_text)
        except ValueError:
            reason_enum = RefundReason.other if hasattr(RefundReason, "other") else list(RefundReason)[0]

        refund = await refund_service.create_refund(
            db,
            store_id=store_id,
            user_id=current_user.id,
            order_id=request.order_id,
            reason=reason_enum,
            reason_details=request.reason_details,
            amount=request.amount,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "exceeds" in detail.lower() or "already" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return RefundResponse.model_validate(refund)


@router.get("", response_model=PaginatedRefundResponse)
async def list_refunds_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    refund_status: Optional[str] = Query(
        None, alias="status", description="Filter by refund status"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRefundResponse:
    """List refunds for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        refund_status: Optional status filter.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedRefundResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import refund_service

    try:
        refunds, total = await refund_service.list_refunds(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            status_filter=refund_status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedRefundResponse(
        items=[RefundResponse.model_validate(r) for r in refunds],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund_endpoint(
    store_id: uuid.UUID,
    refund_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Retrieve a single refund by ID.

    Args:
        store_id: The UUID of the store.
        refund_id: The UUID of the refund to retrieve.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        RefundResponse with the refund data.

    Raises:
        HTTPException 404: If the store or refund is not found.
    """
    from app.services import refund_service

    try:
        refund = await refund_service.get_refund(
            db, store_id=store_id, user_id=current_user.id, refund_id=refund_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return RefundResponse.model_validate(refund)


@router.patch("/{refund_id}", response_model=RefundResponse)
async def update_refund_endpoint(
    store_id: uuid.UUID,
    refund_id: uuid.UUID,
    request: UpdateRefundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Update a refund's status or notes.

    Use this to approve or reject a refund, or add internal notes.
    To actually process the refund (issue payment), use the
    ``/process`` endpoint instead.

    Args:
        store_id: The UUID of the store.
        refund_id: The UUID of the refund to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        RefundResponse with the updated refund data.

    Raises:
        HTTPException 404: If the store or refund is not found.
        HTTPException 400: If the status transition is invalid.
    """
    from app.services import refund_service

    try:
        update_data = request.model_dump(exclude_unset=True)

        refund = await refund_service.update_refund(
            db,
            store_id=store_id,
            user_id=current_user.id,
            refund_id=refund_id,
            **update_data,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower() or "cannot" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return RefundResponse.model_validate(refund)


@router.post("/{refund_id}/process", response_model=ProcessRefundResponse)
async def process_refund_endpoint(
    store_id: uuid.UUID,
    refund_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProcessRefundResponse:
    """Process a refund and issue the payment back to the customer.

    Triggers the actual refund through Stripe (or mock in development).
    The refund must be in ``approved`` status to be processed. After
    processing, the status changes to ``processed``.

    Args:
        store_id: The UUID of the store.
        refund_id: The UUID of the refund to process.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ProcessRefundResponse with the updated refund and a status message.

    Raises:
        HTTPException 404: If the store or refund is not found.
        HTTPException 400: If the refund is not in an approved state
            or has already been processed.
    """
    from app.services import refund_service

    try:
        refund = await refund_service.process_refund(
            db,
            store_id=store_id,
            user_id=current_user.id,
            refund_id=refund_id,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower() or "must be" in detail.lower() or "cannot" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)

    # Dispatch background tasks for refund notifications
    from app.tasks.email_tasks import send_refund_notification
    from app.tasks.webhook_tasks import dispatch_webhook_event

    send_refund_notification.delay(str(refund_id))
    dispatch_webhook_event.delay(str(store_id), "refund.completed", {
        "refund_id": str(refund_id),
        "order_id": str(refund.order_id),
        "amount": str(refund.amount),
    })

    return ProcessRefundResponse(
        refund=RefundResponse.model_validate(refund),
        message="Refund processed successfully",
    )
