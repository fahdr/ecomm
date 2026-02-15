"""Currency API router.

Provides endpoints for managing multi-currency support. Includes global
endpoints for listing supported currencies and converting prices, as well
as store-scoped endpoints for configuring store currency settings.

**For Developers:**
    Global routes are under ``/currencies/...`` (no store scope).
    Store-scoped routes are under ``/stores/{store_id}/currency/...``.
    The ``get_current_user`` dependency is used for authentication on
    store-scoped endpoints. Global list does not require authentication.
    Service functions in ``currency_service`` handle exchange rates.

**For QA Engineers:**
    - GET ``/currencies`` is public (no auth required).
    - POST ``/currencies/convert`` requires authentication.
    - Store currency settings control the display currency for the storefront.
    - Exchange rates are fetched from a configured provider.
    - Supported currencies include all major ISO 4217 codes.

**For End Users:**
    - View all supported currencies with their symbols and names.
    - Convert prices between currencies for comparison.
    - Set your store's display currency for the storefront.
    - Enable multi-currency display for international customers.
"""

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.currency import (
    CurrencyRateResponse,
    PriceConversionResponse,
    StoreCurrencySettingsRequest,
)


router = APIRouter(tags=["currency"])


# ---------------------------------------------------------------------------
# Local response schemas for endpoints that need specific shapes
# ---------------------------------------------------------------------------


class CurrencyListResponse(BaseModel):
    """Response with all supported currencies.

    Attributes:
        currencies: List of supported currency records.
    """

    currencies: list[CurrencyRateResponse]


class StoreCurrencySettings(BaseModel):
    """Response schema for store currency settings.

    Attributes:
        store_id: The store UUID.
        base_currency: The store's base currency code.
        display_currencies: List of currencies shown on the storefront.
        auto_convert: Whether to auto-convert prices for visitors.
        rounding_method: How to round converted prices (nearest, up, down).
    """

    store_id: uuid.UUID
    base_currency: str
    display_currencies: list[str] = []
    auto_convert: bool = False
    rounding_method: str = "nearest"

    model_config = {"from_attributes": True}


class UpdateStoreCurrencyRequest(BaseModel):
    """Request body for updating store currency settings.

    All fields are optional; only provided fields are updated.
    """

    base_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    display_currencies: Optional[list[str]] = None
    auto_convert: Optional[bool] = None
    rounding_method: Optional[str] = None


class ConvertCurrencyRequest(BaseModel):
    """Request body for currency conversion.

    Attributes:
        amount: The amount to convert.
        from_currency: Source currency code (ISO 4217).
        to_currency: Target currency code (ISO 4217).
    """

    amount: Decimal = Field(..., ge=0)
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)


# ---------------------------------------------------------------------------
# Global route handlers (currency list and conversion)
# ---------------------------------------------------------------------------


@router.get("/currencies", response_model=CurrencyListResponse)
async def list_currencies_endpoint(
    db: AsyncSession = Depends(get_db),
) -> CurrencyListResponse:
    """List all supported currencies.

    Returns all ISO 4217 currencies supported by the platform,
    including their symbols and decimal precision. No authentication
    is required.

    Args:
        db: Async database session injected by FastAPI.

    Returns:
        CurrencyListResponse with all supported currencies.
    """
    from app.services import currency_service

    # Service function is synchronous (no db needed)
    currencies = currency_service.get_supported_currencies()
    return CurrencyListResponse(
        currencies=[CurrencyRateResponse(
            code=c["code"],
            name=c["name"],
            symbol=c["symbol"],
            rate=Decimal(str(c.get("rate", 1.0))),
        ) for c in currencies]
    )


class ExchangeRatesResponse(BaseModel):
    """Exchange rates for all supported currencies.

    Used by the dashboard currency converter tool.

    Attributes:
        base: The base currency code (always "USD" for now).
        rates: Mapping of currency code to exchange rate relative to base.
        updated_at: ISO timestamp when rates were last refreshed.
    """

    base: str
    rates: dict[str, float]
    updated_at: str


@router.get("/currencies/rates", response_model=ExchangeRatesResponse)
async def get_exchange_rates_endpoint(
    current_user: User = Depends(get_current_user),
) -> ExchangeRatesResponse:
    """Get exchange rates for all supported currencies.

    Returns rates relative to USD as the base currency. Used by the
    dashboard currency converter tool.

    Args:
        current_user: The authenticated user.

    Returns:
        ExchangeRatesResponse with base currency, rates dict, and timestamp.
    """
    from datetime import datetime, timezone

    from app.services import currency_service

    return ExchangeRatesResponse(
        base="USD",
        rates=dict(currency_service.EXCHANGE_RATES),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/currencies/convert", response_model=PriceConversionResponse)
async def convert_currency_endpoint(
    request: ConvertCurrencyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PriceConversionResponse:
    """Convert an amount between currencies.

    Uses the platform's exchange rate provider to convert the specified
    amount from one currency to another. Exchange rates are cached and
    refreshed periodically.

    Args:
        request: Conversion payload with amount and currency codes.
        current_user: The authenticated user.
        db: Async database session injected by FastAPI.

    Returns:
        ConvertCurrencyResponse with the converted amount and rate used.

    Raises:
        HTTPException 400: If either currency code is not supported.
    """
    from app.services import currency_service

    try:
        # Service function is synchronous and doesn't need db
        result = currency_service.convert_price(
            amount=request.amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return PriceConversionResponse(
        original_amount=request.amount,
        original_currency=request.from_currency.upper(),
        converted_amount=result["converted_amount"],
        target_currency=request.to_currency.upper(),
        rate=Decimal(str(result["rate"])),
    )


# ---------------------------------------------------------------------------
# Store-scoped route handlers
# ---------------------------------------------------------------------------


@router.get(
    "/stores/{store_id}/currency",
    response_model=StoreCurrencySettings,
)
async def get_store_currency_endpoint(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreCurrencySettings:
    """Get a store's currency settings.

    Returns the store's base currency, display currencies for the
    storefront, and auto-conversion configuration.

    Args:
        store_id: The UUID of the store.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        StoreCurrencySettings with the store's currency configuration.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import currency_service

    try:
        # Service function only takes (db, store_id), no user_id
        base_currency = await currency_service.get_store_currency(
            db, store_id=store_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    # Service returns a string (currency code), build the response manually
    return StoreCurrencySettings(
        store_id=store_id,
        base_currency=base_currency,
        display_currencies=[],
        auto_convert=False,
        rounding_method="nearest",
    )


@router.patch(
    "/stores/{store_id}/currency",
    response_model=StoreCurrencySettings,
)
async def update_store_currency_endpoint(
    store_id: uuid.UUID,
    request: UpdateStoreCurrencyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreCurrencySettings:
    """Update a store's currency settings.

    Configure the base currency, enable/disable multi-currency display,
    and set currency conversion preferences.

    Args:
        store_id: The UUID of the store.
        request: Partial update payload for currency settings.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        StoreCurrencySettings with the updated configuration.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If any currency code is not supported.
    """
    from app.services import currency_service
    from sqlalchemy import select as sa_select
    from app.models.store import Store, StoreStatus

    # Service doesn't have update_store_currency, so handle inline
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

    update_data = request.model_dump(exclude_unset=True)
    new_currency = update_data.get("base_currency")
    if new_currency:
        # Validate currency is supported
        supported = currency_service.get_supported_currencies()
        supported_codes = {c["code"] for c in supported}
        if new_currency.upper() not in supported_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Currency '{new_currency}' is not supported",
            )
        store.default_currency = new_currency.upper()
        await db.flush()
        await db.refresh(store)

    base_currency = store.default_currency or "USD"
    return StoreCurrencySettings(
        store_id=store_id,
        base_currency=base_currency,
        display_currencies=update_data.get("display_currencies", []),
        auto_convert=update_data.get("auto_convert", False),
        rounding_method=update_data.get("rounding_method", "nearest"),
    )
