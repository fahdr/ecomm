"""Pydantic schemas for tax rate and tax calculation endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/tax-rates`` and
``/api/v1/stores/{store_id}/tax/calculate`` routes.

**For Developers:**
    ``CreateTaxRateRequest`` and ``UpdateTaxRateRequest`` manage tax rules.
    ``TaxCalculationRequest`` / ``TaxCalculationResponse`` handle on-the-fly
    tax computation at checkout. ``TaxRateResponse`` uses ``from_attributes``.

**For QA Engineers:**
    - ``CreateTaxRateRequest.rate`` must be >= 0 (percentage, e.g. 8.25).
    - ``CreateTaxRateRequest.country`` is a 2-letter ISO code.
    - ``TaxCalculationResponse.applied_rates`` shows each applied rule.
    - ``is_inclusive`` means tax is already included in the listed price.
    - ``priority`` determines the order of application.

**For Project Managers:**
    Tax compliance is required for any e-commerce platform. Store owners
    define tax rates by country/state/zip. The system calculates the
    correct tax at checkout based on the shipping address.

**For End Users:**
    Tax is automatically calculated at checkout based on your shipping
    address. The order summary shows a breakdown of applied taxes.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateTaxRateRequest(BaseModel):
    """Schema for creating a new tax rate rule.

    Attributes:
        name: Display name for the tax rate (e.g. ``"CA State Tax"``).
        rate: Tax rate as a percentage (e.g. ``8.25`` for 8.25%).
        country: 2-letter ISO country code (e.g. ``"US"``).
        state: Optional state or province code (e.g. ``"CA"``).
        zip_code: Optional postal/zip code for locality-specific rates.
        priority: Order of application when multiple rates match.
            Lower numbers are applied first. Defaults to 0.
        is_inclusive: Whether this tax is already included in the listed
            price (VAT-style). Defaults to False.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Tax rate name"
    )
    rate: Decimal = Field(
        ..., ge=0, description="Tax rate percentage (e.g. 8.25)"
    )
    country: str = Field(
        ..., min_length=2, max_length=2, description="2-letter ISO country code"
    )
    state: str | None = Field(
        None, max_length=10, description="State/province code"
    )
    zip_code: str | None = Field(
        None, max_length=20, description="Postal/zip code"
    )
    priority: int = Field(
        0, ge=0, description="Application priority (lower = first)"
    )
    is_inclusive: bool = Field(
        False, description="Inclusive tax (already included in price)"
    )


class UpdateTaxRateRequest(BaseModel):
    """Schema for updating an existing tax rate (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        name: New tax rate name.
        rate: New tax rate percentage.
        country: New country code.
        state: New state code.
        zip_code: New zip code.
        is_active: Whether the tax rate is active.
        priority: New application priority.
        is_inclusive: Whether the tax is inclusive.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    rate: Decimal | None = Field(None, ge=0)
    country: str | None = Field(None, min_length=2, max_length=2)
    state: str | None = Field(None, max_length=10)
    zip_code: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    priority: int | None = Field(None, ge=0)
    is_inclusive: bool | None = None


class TaxRateResponse(BaseModel):
    """Schema for returning tax rate data in API responses.

    Attributes:
        id: The tax rate unique identifier.
        store_id: The parent store UUID.
        name: Display name of the tax rate.
        rate: Tax rate percentage.
        country: 2-letter ISO country code.
        state: State/province code (may be null).
        zip_code: Postal/zip code (may be null).
        is_active: Whether the tax rate is currently applied.
        priority: Application priority order.
        is_inclusive: Whether this is an inclusive (VAT-style) tax.
        created_at: When the tax rate was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    rate: Decimal
    country: str
    state: str | None
    zip_code: str | None
    is_active: bool
    priority: int
    is_inclusive: bool
    created_at: datetime


class TaxCalculationItem(BaseModel):
    """Schema for a single line item in a tax calculation request.

    Attributes:
        product_id: UUID of the product being purchased.
        quantity: Number of units for this line item.
        unit_price: Price per unit before tax.
    """

    product_id: str = Field(..., description="Product UUID")
    quantity: int = Field(..., ge=1, description="Number of units")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")


class TaxCalculationRequest(BaseModel):
    """Schema for requesting a tax calculation at checkout.

    Accepts a country code and a list of cart items with quantities and
    prices. The service calculates the applicable tax for each item based
    on matching tax rates for the given country/state.

    Attributes:
        country: 2-letter ISO country code of the shipping address.
        state: Optional state/province code.
        zip_code: Optional postal/zip code.
        items: List of cart items to calculate tax for.
    """

    country: str = Field(
        ..., min_length=2, max_length=2, description="Shipping country code"
    )
    state: str | None = Field(
        None, max_length=10, description="Shipping state code"
    )
    zip_code: str | None = Field(
        None, max_length=20, description="Shipping zip/postal code"
    )
    items: list[TaxCalculationItem] = Field(
        ..., min_length=1, description="Cart items to calculate tax for"
    )


class TaxCalculationLineItem(BaseModel):
    """Schema for a single line item in the tax calculation response.

    Attributes:
        product_id: UUID of the product.
        quantity: Number of units.
        unit_price: Price per unit before tax.
        subtotal: Line item subtotal (quantity * unit_price).
        tax: Tax amount for this line item.
        total: Subtotal plus tax for this line item.
    """

    product_id: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


class AppliedRate(BaseModel):
    """Schema for an applied tax rate in the calculation response.

    Attributes:
        name: Display name of the tax rate.
        rate: Tax rate percentage.
        amount: Tax amount contributed by this rate.
    """

    name: str
    rate: Decimal
    amount: Decimal


class TaxCalculationResponse(BaseModel):
    """Schema for the result of a tax calculation.

    Attributes:
        subtotal: The original cart subtotal (sum of all line items).
        tax_total: Total tax to be charged.
        total: Subtotal plus tax.
        line_items: Per-item breakdown with tax amounts.
        applied_rates: List of applied tax rates with their contributions.
    """

    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    line_items: list[TaxCalculationLineItem]
    applied_rates: list[AppliedRate]
