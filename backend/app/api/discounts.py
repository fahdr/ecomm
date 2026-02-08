"""Discount API router.

Provides CRUD endpoints for managing discount codes and percentage/fixed
discounts within a store. Store owners can create, list, update, and delete
discounts. A validation endpoint is available for checkout preview.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/discounts/...``
    (full path: ``/api/v1/stores/{store_id}/discounts/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``discount_service`` handle all business logic.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - All endpoints return 404 if the store doesn't exist or belongs to another user.
    - GET list supports ``?page=``, ``?per_page=``, ``?status=`` query params.
    - POST create returns 201 with the full discount data.
    - DELETE returns 204 with no content.
    - Validate endpoint checks code validity, expiry, and usage limits.

**For End Users:**
    - Create discount codes (percentage or fixed amount) with optional
      expiry dates and usage limits.
    - Apply discounts during checkout to reduce order totals.
    - Track which discounts are active and how many times they've been used.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/stores/{store_id}/discounts", tags=["discounts"])


# ---------------------------------------------------------------------------
# Imports from app.schemas.discount
# ---------------------------------------------------------------------------
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.discount import (
    ApplyDiscountRequest,
    ApplyDiscountResponse,
    CreateDiscountRequest,
    DiscountResponse,
    PaginatedDiscountResponse,
    UpdateDiscountRequest,
)


class ValidateDiscountRequest(BaseModel):
    """Request body for validating a discount code at checkout.

    Attributes:
        code: The coupon code to validate.
        order_total: The current cart/order total for minimum-check.
    """

    code: str
    order_total: Decimal = Field(..., ge=0)


class ValidateDiscountResponse(BaseModel):
    """Response for discount validation.

    Attributes:
        valid: Whether the discount code is valid.
        discount: The discount details if valid.
        discount_amount: Computed discount amount for the given order total.
        message: Human-readable validation message.
    """

    valid: bool
    discount: Optional[DiscountResponse] = None
    discount_amount: Optional[Decimal] = None
    message: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
async def create_discount_endpoint(
    store_id: uuid.UUID,
    request: CreateDiscountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscountResponse:
    """Create a new discount code for a store.

    Creates a discount with the specified code, type (percentage or fixed),
    value, and optional constraints such as minimum order amount, maximum
    uses, and expiry date.

    Args:
        store_id: The UUID of the store to create the discount in.
        request: Discount creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        DiscountResponse with the newly created discount data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the discount code already exists in this store.
    """
    from app.services import discount_service

    try:
        discount = await discount_service.create_discount(
            db,
            store_id=store_id,
            user_id=current_user.id,
            code=request.code,
            description=request.description,
            discount_type=request.discount_type,
            value=request.value,
            minimum_order_amount=request.minimum_order_amount,
            max_uses=request.max_uses,
            starts_at=request.starts_at,
            expires_at=request.expires_at,
            applies_to=request.applies_to,
            product_ids=request.product_ids,
            category_ids=request.category_ids,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already exists" in detail
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return DiscountResponse.model_validate(discount)


@router.get("", response_model=PaginatedDiscountResponse)
async def list_discounts_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    discount_status: Optional[str] = Query(
        None, alias="status", description="Filter by discount status"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedDiscountResponse:
    """List discounts for a store with pagination and optional status filter.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        discount_status: Optional status filter (active, expired, disabled).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedDiscountResponse with items, total count, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import discount_service

    try:
        discounts, total = await discount_service.list_discounts(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            status_filter=discount_status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedDiscountResponse(
        items=[DiscountResponse.model_validate(d) for d in discounts],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{discount_id}", response_model=DiscountResponse)
async def get_discount_endpoint(
    store_id: uuid.UUID,
    discount_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscountResponse:
    """Retrieve a single discount by ID.

    Args:
        store_id: The UUID of the store.
        discount_id: The UUID of the discount to retrieve.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        DiscountResponse with the discount data.

    Raises:
        HTTPException 404: If the store or discount is not found.
    """
    from app.services import discount_service

    try:
        discount = await discount_service.get_discount(
            db, store_id=store_id, user_id=current_user.id, discount_id=discount_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return DiscountResponse.model_validate(discount)


@router.patch("/{discount_id}", response_model=DiscountResponse)
async def update_discount_endpoint(
    store_id: uuid.UUID,
    discount_id: uuid.UUID,
    request: UpdateDiscountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscountResponse:
    """Update a discount's fields (partial update).

    Only provided fields are updated. You can change the code, value,
    type, constraints, or status.

    Args:
        store_id: The UUID of the store.
        discount_id: The UUID of the discount to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        DiscountResponse with the updated discount data.

    Raises:
        HTTPException 404: If the store or discount is not found.
        HTTPException 400: If the update contains invalid data.
    """
    from app.services import discount_service

    try:
        update_data = request.model_dump(exclude_unset=True)

        discount = await discount_service.update_discount(
            db,
            store_id=store_id,
            user_id=current_user.id,
            discount_id=discount_id,
            **update_data,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return DiscountResponse.model_validate(discount)


@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discount_endpoint(
    store_id: uuid.UUID,
    discount_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a discount permanently.

    Args:
        store_id: The UUID of the store.
        discount_id: The UUID of the discount to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or discount is not found.
    """
    from app.services import discount_service

    try:
        await discount_service.delete_discount(
            db, store_id=store_id, user_id=current_user.id, discount_id=discount_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/validate", response_model=ValidateDiscountResponse)
async def validate_discount_endpoint(
    store_id: uuid.UUID,
    request: ValidateDiscountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ValidateDiscountResponse:
    """Validate a discount code for checkout preview.

    Checks whether the provided code is valid for the given order total,
    including expiry, usage limits, and minimum order amount. Returns
    the computed discount amount if valid.

    Args:
        store_id: The UUID of the store.
        request: Validation payload with code and order total.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ValidateDiscountResponse with validity status, discount details,
        and computed discount amount.

    Raises:
        HTTPException 404: If the store is not found.
    """
    from app.services import discount_service

    try:
        # Service uses 'subtotal' not 'order_total', and doesn't take user_id
        result = await discount_service.validate_discount(
            db,
            store_id=store_id,
            code=request.code,
            subtotal=request.order_total,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return ValidateDiscountResponse(**result)
