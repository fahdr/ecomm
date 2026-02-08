"""Tax API router.

Provides endpoints for managing tax rates and calculating tax for carts.
Store owners can configure tax rates by region/country and calculate
applicable taxes during checkout.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/tax-rates/...``
    and ``/stores/{store_id}/tax/calculate``.
    (full path: ``/api/v1/stores/{store_id}/...``).
    The ``get_current_user`` dependency is used for authentication.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST create returns 201 with the tax rate data.
    - DELETE returns 204 with no content.
    - Tax calculation considers country, state, and product categories.
    - Duplicate region+country combinations are rejected with 400.

**For End Users:**
    - Set up tax rates for different regions where you sell.
    - Automatically calculate tax at checkout based on customer location.
    - Manage inclusive vs. exclusive tax display settings.
"""

import math
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.tax import (
    AppliedRate,
    CreateTaxRateRequest,
    TaxCalculationLineItem,
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxRateResponse,
    UpdateTaxRateRequest,
)

router = APIRouter(prefix="/stores/{store_id}", tags=["tax"])


# ---------------------------------------------------------------------------
# Additional response schemas used only by the API layer
# ---------------------------------------------------------------------------


class PaginatedTaxRateResponse(BaseModel):
    """Paginated list of tax rates.

    Attributes:
        items: List of tax rate records.
        total: Total number of tax rates.
        page: Current page number.
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[TaxRateResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post(
    "/tax-rates", response_model=TaxRateResponse, status_code=status.HTTP_201_CREATED
)
async def create_tax_rate_endpoint(
    store_id: uuid.UUID,
    request: CreateTaxRateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxRateResponse:
    """Create a new tax rate for a store.

    Defines a tax rate for a specific country and optional state/province.
    Multiple tax rates can be stacked using priority ordering.

    Args:
        store_id: The UUID of the store.
        request: Tax rate creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        TaxRateResponse with the newly created tax rate data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If a duplicate region combination exists.
    """
    from app.services import tax_service

    try:
        tax_rate = await tax_service.create_tax_rate(
            db,
            store_id=store_id,
            user_id=current_user.id,
            **request.model_dump(),
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already exists" in detail or "duplicate" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return TaxRateResponse.model_validate(tax_rate)


@router.get("/tax-rates", response_model=PaginatedTaxRateResponse)
async def list_tax_rates_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTaxRateResponse:
    """List tax rates for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedTaxRateResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import tax_service

    try:
        all_rates = await tax_service.list_tax_rates(
            db,
            store_id=store_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    total = len(all_rates)
    pages = math.ceil(total / per_page) if total > 0 else 1
    offset = (page - 1) * per_page
    rates = all_rates[offset : offset + per_page]

    return PaginatedTaxRateResponse(
        items=[TaxRateResponse.model_validate(r) for r in rates],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch("/tax-rates/{rate_id}", response_model=TaxRateResponse)
async def update_tax_rate_endpoint(
    store_id: uuid.UUID,
    rate_id: uuid.UUID,
    request: UpdateTaxRateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxRateResponse:
    """Update a tax rate's fields (partial update).

    Only provided fields are updated.

    Args:
        store_id: The UUID of the store.
        rate_id: The UUID of the tax rate to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        TaxRateResponse with the updated tax rate data.

    Raises:
        HTTPException 404: If the store or tax rate is not found.
    """
    from app.services import tax_service

    try:
        tax_rate = await tax_service.update_tax_rate(
            db,
            store_id=store_id,
            user_id=current_user.id,
            tax_rate_id=rate_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return TaxRateResponse.model_validate(tax_rate)


@router.delete("/tax-rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_rate_endpoint(
    store_id: uuid.UUID,
    rate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a tax rate.

    Args:
        store_id: The UUID of the store.
        rate_id: The UUID of the tax rate to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or tax rate is not found.
    """
    from app.services import tax_service

    try:
        await tax_service.delete_tax_rate(
            db, store_id=store_id, user_id=current_user.id, tax_rate_id=rate_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/tax/calculate", response_model=TaxCalculationResponse)
async def calculate_tax_endpoint(
    store_id: uuid.UUID,
    request: TaxCalculationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxCalculationResponse:
    """Calculate tax for a cart based on customer location.

    Applies matching tax rates for the given country and state to
    each cart item. Returns per-item tax breakdown and totals.

    Args:
        store_id: The UUID of the store.
        request: Tax calculation payload with location and cart items.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        TaxCalculationResponse with subtotal, tax breakdown, and total.

    Raises:
        HTTPException 404: If the store is not found.
        HTTPException 400: If the request is invalid.
    """
    from app.services import tax_service

    # Compute subtotal from cart items
    subtotal = Decimal("0.00")
    for item in request.items:
        subtotal += item.unit_price * item.quantity

    try:
        result = await tax_service.calculate_tax(
            db,
            store_id=store_id,
            subtotal=subtotal,
            country=request.country,
            state=request.state,
            zip_code=request.zip_code,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower() or "item" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)

    # Build response from service result
    tax_amount = result.get("tax_amount", Decimal("0.00"))
    effective_rate_pct = result.get("effective_rate", Decimal("0.00"))
    breakdown = result.get("breakdown", [])

    # Build line items with per-item tax
    line_items = []
    for item in request.items:
        item_subtotal = item.unit_price * item.quantity
        if subtotal > 0:
            item_tax = (tax_amount * item_subtotal / subtotal).quantize(
                Decimal("0.01")
            )
        else:
            item_tax = Decimal("0.00")
        line_items.append(
            TaxCalculationLineItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item_subtotal,
                tax=item_tax,
                total=item_subtotal + item_tax,
            )
        )

    # Build applied rates
    applied_rates = []
    for rate_info in breakdown:
        applied_rates.append(
            AppliedRate(
                name=rate_info["name"],
                rate=rate_info["rate"],
                amount=rate_info["tax_amount"],
            )
        )

    return TaxCalculationResponse(
        subtotal=subtotal,
        tax_total=tax_amount,
        total=subtotal + tax_amount,
        line_items=line_items,
        applied_rates=applied_rates,
    )
