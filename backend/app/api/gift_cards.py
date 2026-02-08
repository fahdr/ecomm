"""Gift Cards API router.

Provides endpoints for managing gift cards. Store owners can create,
list, validate, and disable gift cards. Gift cards can be used as a
payment method during checkout.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/gift-cards/...``
    (full path: ``/api/v1/stores/{store_id}/gift-cards/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``gift_card_service`` handle all business logic.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST create returns 201 with the gift card data including generated code.
    - Validate endpoint checks balance, expiry, and active status.
    - Disabled gift cards cannot be used for purchases.
    - Gift card codes are unique across the store.

**For End Users:**
    - Create gift cards with a monetary balance and optional expiry.
    - Gift cards are generated with unique codes for customers.
    - Track gift card usage and remaining balances.
    - Disable compromised or unwanted gift cards.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.gift_card import (
    ApplyGiftCardRequest,
    ApplyGiftCardResponse,
    CreateGiftCardRequest,
    GiftCardResponse,
    PaginatedGiftCardResponse,
)

router = APIRouter(tags=["gift-cards"])


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/gift-cards",
    response_model=GiftCardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gift_card_endpoint(
    store_id: uuid.UUID,
    request: CreateGiftCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GiftCardResponse:
    """Create a new gift card for a store.

    Creates a gift card with the specified balance and optional
    customizations. If no code is provided, a unique code is
    auto-generated.

    Args:
        store_id: The UUID of the store.
        request: Gift card creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        GiftCardResponse with the newly created gift card data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the code already exists in this store.
    """
    from app.services import gift_card_service

    try:
        gift_card = await gift_card_service.create_gift_card(
            db,
            store_id=store_id,
            user_id=current_user.id,
            initial_balance=request.initial_balance,
            customer_email=request.customer_email,
            expires_at=request.expires_at,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already exists" in detail
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return GiftCardResponse.model_validate(gift_card)


@router.get("/stores/{store_id}/gift-cards", response_model=PaginatedGiftCardResponse)
async def list_gift_cards_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedGiftCardResponse:
    """List gift cards for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedGiftCardResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import gift_card_service

    try:
        cards, total = await gift_card_service.list_gift_cards(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedGiftCardResponse(
        items=[GiftCardResponse.model_validate(c) for c in cards],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/stores/{store_id}/gift-cards/{card_id}", response_model=GiftCardResponse)
async def get_gift_card_endpoint(
    store_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GiftCardResponse:
    """Retrieve a single gift card by ID.

    Args:
        store_id: The UUID of the store.
        card_id: The UUID of the gift card to retrieve.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        GiftCardResponse with the gift card data.

    Raises:
        HTTPException 404: If the store or gift card is not found.
    """
    from app.services import gift_card_service

    try:
        card = await gift_card_service.get_gift_card(
            db, store_id=store_id, user_id=current_user.id, gift_card_id=card_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return GiftCardResponse.model_validate(card)


@router.post("/stores/{store_id}/gift-cards/{card_id}/disable", response_model=GiftCardResponse)
async def disable_gift_card_endpoint(
    store_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GiftCardResponse:
    """Disable a gift card.

    Deactivates the gift card so it can no longer be used for purchases.
    The remaining balance is preserved but inaccessible.

    Args:
        store_id: The UUID of the store.
        card_id: The UUID of the gift card to disable.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        GiftCardResponse with the disabled gift card data.

    Raises:
        HTTPException 404: If the store or gift card is not found.
        HTTPException 400: If the gift card is already disabled.
    """
    from app.services import gift_card_service

    try:
        card = await gift_card_service.disable_gift_card(
            db, store_id=store_id, user_id=current_user.id, gift_card_id=card_id
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return GiftCardResponse.model_validate(card)


@router.post("/stores/{store_id}/gift-cards/validate", response_model=ApplyGiftCardResponse)
async def validate_gift_card_endpoint(
    store_id: uuid.UUID,
    request: ApplyGiftCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplyGiftCardResponse:
    """Validate a gift card code.

    Checks whether the provided code is valid, active, not expired,
    and has a remaining balance. Used during checkout to verify
    gift card applicability.

    Args:
        store_id: The UUID of the store.
        request: Validation payload with the gift card code.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ValidateGiftCardResponse with validity status and gift card details.

    Raises:
        HTTPException 404: If the store is not found.
    """
    from app.services import gift_card_service

    try:
        result = await gift_card_service.validate_gift_card(
            db,
            store_id=store_id,
            code=request.code,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return ApplyGiftCardResponse(**result)


# ---------------------------------------------------------------------------
# Public route handlers (no authentication required)
# ---------------------------------------------------------------------------


@router.post(
    "/public/stores/{slug}/gift-cards/validate",
    response_model=ApplyGiftCardResponse,
)
async def public_validate_gift_card_endpoint(
    slug: str,
    request: ApplyGiftCardRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplyGiftCardResponse:
    """Validate a gift card code (public, customer-facing).

    Allows storefront customers to check a gift card code during
    checkout without authentication. Returns validity and balance.

    Args:
        slug: The store's URL slug.
        request: Validation payload with the gift card code.
        db: Async database session injected by FastAPI.

    Returns:
        PublicValidateGiftCardResponse with validity status and balance.

    Raises:
        HTTPException 404: If the store is not found.
    """
    from app.models.store import Store, StoreStatus
    from app.services import gift_card_service

    # Resolve store from slug
    store_result = await db.execute(
        select(Store).where(
            Store.slug == slug,
            Store.status == StoreStatus.active,
        )
    )
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    result = await gift_card_service.validate_gift_card(
        db,
        store_id=store.id,
        code=request.code,
    )
    return ApplyGiftCardResponse(**result)
