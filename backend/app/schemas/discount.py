"""Pydantic schemas for discount and coupon endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/discounts/*`` routes.

**For Developers:**
    ``CreateDiscountRequest`` and ``UpdateDiscountRequest`` are input schemas.
    ``DiscountResponse`` uses ``from_attributes`` to serialize ORM instances.
    ``ApplyDiscountRequest`` / ``ApplyDiscountResponse`` handle coupon
    validation at checkout. Pagination is handled via
    ``PaginatedDiscountResponse``.

**For QA Engineers:**
    - ``CreateDiscountRequest.code`` is required, 1-50 characters.
    - ``CreateDiscountRequest.value`` must be > 0.
    - ``discount_type`` must be ``"percentage"`` or ``"fixed_amount"``.
    - ``applies_to`` defaults to ``"all"``; may be ``"specific_products"``
      or ``"specific_categories"``.
    - ``ApplyDiscountResponse.valid`` indicates whether the coupon is usable.

**For Project Managers:**
    Discounts drive promotional campaigns. Merchants can create
    percentage-based or fixed-amount coupons with usage limits, date
    ranges, and product/category targeting.

**For End Users:**
    Enter a discount code at checkout to apply a coupon. The system will
    tell you whether the code is valid and how much you save.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateDiscountRequest(BaseModel):
    """Schema for creating a new discount / coupon code.

    Attributes:
        code: The coupon code that customers will enter (1-50 chars, unique
            within the store).
        description: Optional human-readable description of the promotion.
        discount_type: Either ``"percentage"`` (e.g. 10% off) or
            ``"fixed_amount"`` (e.g. $5 off).
        value: The numeric discount value (percentage points or currency
            amount). Must be greater than zero.
        minimum_order_amount: Optional minimum cart subtotal required to
            use the coupon.
        max_uses: Optional maximum number of times the coupon may be
            redeemed. ``None`` means unlimited.
        starts_at: When the coupon becomes active.
        expires_at: Optional expiration datetime. ``None`` means the
            coupon does not expire.
        applies_to: Targeting scope: ``"all"``, ``"specific_products"``,
            or ``"specific_categories"``.
        product_ids: List of product UUIDs when ``applies_to`` is
            ``"specific_products"``.
        category_ids: List of category UUIDs when ``applies_to`` is
            ``"specific_categories"``.
    """

    code: str = Field(
        ..., min_length=1, max_length=50, description="Coupon code"
    )
    description: str | None = Field(
        None, max_length=500, description="Promotion description"
    )
    discount_type: str = Field(
        ..., description='Either "percentage" or "fixed_amount"'
    )
    value: Decimal = Field(..., gt=0, description="Discount value")
    minimum_order_amount: Decimal | None = Field(
        None, ge=0, description="Minimum order subtotal"
    )
    max_uses: int | None = Field(
        None, ge=1, description="Maximum total redemptions"
    )
    starts_at: datetime = Field(..., description="Activation datetime")
    expires_at: datetime | None = Field(
        None, description="Expiration datetime"
    )
    applies_to: str = Field(
        "all",
        description='Targeting: "all", "specific_products", or "specific_categories"',
    )
    product_ids: list[uuid.UUID] | None = Field(
        None, description="Targeted product UUIDs"
    )
    category_ids: list[uuid.UUID] | None = Field(
        None, description="Targeted category UUIDs"
    )


class UpdateDiscountRequest(BaseModel):
    """Schema for updating an existing discount (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        code: New coupon code (1-50 chars).
        description: New description.
        discount_type: New type (``"percentage"`` or ``"fixed_amount"``).
        value: New discount value (> 0).
        minimum_order_amount: New minimum order subtotal.
        max_uses: New maximum redemptions.
        starts_at: New activation datetime.
        expires_at: New expiration datetime.
        applies_to: New targeting scope.
        product_ids: New targeted product UUIDs.
        category_ids: New targeted category UUIDs.
    """

    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)
    discount_type: str | None = None
    value: Decimal | None = Field(None, gt=0)
    minimum_order_amount: Decimal | None = Field(None, ge=0)
    max_uses: int | None = Field(None, ge=1)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    status: str | None = Field(
        None, description='New status: "active", "expired", or "disabled"'
    )
    applies_to: str | None = None
    product_ids: list[uuid.UUID] | None = None
    category_ids: list[uuid.UUID] | None = None


class DiscountResponse(BaseModel):
    """Schema for returning discount data in API responses.

    Attributes:
        id: The discount's unique identifier.
        store_id: The parent store's UUID.
        code: The coupon code.
        description: Human-readable description (may be null).
        discount_type: ``"percentage"`` or ``"fixed_amount"``.
        value: Numeric discount value.
        minimum_order_amount: Minimum order subtotal (may be null).
        max_uses: Maximum redemptions (may be null for unlimited).
        times_used: How many times the coupon has been redeemed.
        starts_at: When the coupon becomes active.
        expires_at: When the coupon expires (may be null).
        status: Current status (``"active"``, ``"expired"``, ``"disabled"``).
        applies_to: Targeting scope.
        created_at: When the discount was created.
        updated_at: When the discount was last modified.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    code: str
    description: str | None
    discount_type: str
    value: Decimal
    minimum_order_amount: Decimal | None
    max_uses: int | None
    times_used: int
    starts_at: datetime
    expires_at: datetime | None
    status: str
    applies_to: str
    created_at: datetime
    updated_at: datetime


class ApplyDiscountRequest(BaseModel):
    """Schema for applying a discount code at checkout.

    Attributes:
        code: The coupon code to validate and apply.
    """

    code: str = Field(
        ..., min_length=1, max_length=50, description="Coupon code to apply"
    )


class ApplyDiscountResponse(BaseModel):
    """Schema for the result of applying a discount code.

    Attributes:
        valid: Whether the coupon code is valid and can be applied.
        discount_type: The type of discount (``"percentage"`` or
            ``"fixed_amount"``), or null if invalid.
        value: The discount value, or null if invalid.
        message: Human-readable message explaining the result.
    """

    valid: bool
    discount_type: str | None = None
    value: Decimal | None = None
    message: str


class PaginatedDiscountResponse(BaseModel):
    """Schema for paginated discount list responses.

    Attributes:
        items: List of discounts on this page.
        total: Total number of discounts matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[DiscountResponse]
    total: int
    page: int
    per_page: int
    pages: int
