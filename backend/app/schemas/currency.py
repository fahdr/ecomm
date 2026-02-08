"""Pydantic schemas for multi-currency endpoints (Feature 21).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/currencies/*`` routes.

**For Developers:**
    ``CurrencyRateResponse`` represents a single currency with its
    exchange rate. ``StoreCurrencySettingsRequest`` configures which
    currencies a store supports. ``PriceConversionResponse`` returns
    converted amounts for storefront display.

**For QA Engineers:**
    - ``CurrencyRateResponse.code`` is a 3-letter ISO 4217 code
      (e.g. ``"USD"``, ``"EUR"``, ``"GBP"``).
    - ``StoreCurrencySettingsRequest.default_currency`` must be a
      valid ISO 4217 code.
    - ``PriceConversionResponse.rate`` is the exchange rate applied.
    - All monetary amounts use ``Decimal`` for precision.

**For Project Managers:**
    Multi-currency support broadens the addressable market. Store
    owners set a default currency and enable additional currencies.
    Prices are automatically converted for international customers
    based on current exchange rates.

**For End Users:**
    See prices in your local currency when browsing a store. The
    store owner determines which currencies are supported.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class CurrencyRateResponse(BaseModel):
    """Schema for returning a single currency and its exchange rate.

    Attributes:
        code: 3-letter ISO 4217 currency code (e.g. ``"USD"``).
        name: Human-readable currency name (e.g. ``"US Dollar"``).
        symbol: Currency symbol (e.g. ``"$"``, ``"\u20ac"``, ``"\u00a3"``).
        rate: Exchange rate relative to the store's base currency.
            Base currency rate is always ``1.0``.
    """

    code: str
    name: str
    symbol: str
    rate: Decimal


class StoreCurrencySettingsRequest(BaseModel):
    """Schema for configuring a store's currency settings.

    Attributes:
        default_currency: The store's base currency (3-letter ISO 4217
            code). All prices in the database are stored in this currency.
        enabled_currencies: List of additional ISO 4217 codes that
            customers may view prices in.
    """

    default_currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Default ISO 4217 currency code",
    )
    enabled_currencies: list[str] = Field(
        ...,
        min_length=1,
        description="Enabled ISO 4217 currency codes",
    )


class PriceConversionResponse(BaseModel):
    """Schema for the result of a price conversion.

    Attributes:
        original_amount: The price in the store's base currency.
        original_currency: The store's base currency code.
        converted_amount: The price in the target currency.
        target_currency: The target currency code.
        rate: The exchange rate that was applied.
    """

    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    target_currency: str
    rate: Decimal
