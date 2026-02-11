"""Pydantic schemas for order endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/orders/*`` routes and the public checkout
endpoint.

**For Developers:**
    ``CheckoutItemRequest`` validates individual cart items for checkout.
    ``CheckoutRequest`` wraps the full cart submission including shipping
    address, optional discount code, and optional gift card code.
    ``OrderResponse`` and ``OrderItemResponse`` use ``from_attributes``
    to serialize ORM instances. Pagination is handled via
    ``PaginatedOrderResponse``.

**For QA Engineers:**
    - ``CheckoutItemRequest.quantity`` must be >= 1.
    - ``CheckoutRequest.customer_email`` must be a valid email.
    - ``ShippingAddress`` requires name, line1, city, postal_code, country.
    - ``OrderResponse`` includes nested order items and financial breakdown.
    - ``UpdateOrderStatusRequest`` only allows valid status transitions.

**For Project Managers:**
    These schemas define the data contracts for the checkout flow and order
    management APIs. The checkout request now collects full shipping details
    and supports discount codes and gift cards.

**For End Users:**
    When checking out, provide your email, shipping address, and the items
    in your cart. You can optionally apply a discount code or gift card.
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


from app.models.order import OrderStatus


class ShippingAddress(BaseModel):
    """Schema for a customer's shipping address.

    Attributes:
        name: Full name of the recipient.
        line1: Street address line 1.
        line2: Optional street address line 2 (apartment, suite, etc.).
        city: City name.
        state: Optional state or province.
        postal_code: Postal or ZIP code.
        country: ISO 3166-1 alpha-2 country code (e.g. "US", "GB").
        phone: Optional phone number for delivery contact.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Recipient full name")
    line1: str = Field(..., min_length=1, max_length=300, description="Street address line 1")
    line2: str | None = Field(None, max_length=300, description="Street address line 2")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str | None = Field(None, max_length=100, description="State or province")
    postal_code: str = Field(..., min_length=1, max_length=20, description="Postal/ZIP code")
    country: str = Field(..., min_length=2, max_length=2, description="ISO 2-letter country code")
    phone: str | None = Field(None, max_length=30, description="Phone number")


class CheckoutItemRequest(BaseModel):
    """Schema for a single item in a checkout request.

    Attributes:
        product_id: UUID of the product to purchase.
        variant_id: Optional UUID of the specific variant.
        quantity: Number of units to purchase (>= 1).
    """

    product_id: uuid.UUID = Field(..., description="Product UUID")
    variant_id: uuid.UUID | None = Field(None, description="Variant UUID")
    quantity: int = Field(..., ge=1, description="Quantity to purchase")


class CheckoutRequest(BaseModel):
    """Schema for creating a checkout session.

    Attributes:
        customer_email: Email address for order confirmation.
        items: List of items to purchase.
        shipping_address: The customer's shipping address.
        discount_code: Optional coupon/promo code to apply.
        gift_card_code: Optional gift card code to apply.
    """

    customer_email: EmailStr = Field(..., description="Customer email address")
    items: list[CheckoutItemRequest] = Field(
        ..., min_length=1, description="Cart items"
    )
    shipping_address: ShippingAddress = Field(..., description="Shipping address")
    discount_code: str | None = Field(None, description="Optional discount/coupon code")
    gift_card_code: str | None = Field(None, description="Optional gift card code")


class ValidateDiscountRequest(BaseModel):
    """Schema for validating a discount code before checkout.

    Attributes:
        code: The discount code to validate.
        subtotal: The cart subtotal for discount calculation.
        product_ids: Optional product IDs for targeted discount validation.
    """

    code: str = Field(..., min_length=1, description="Discount code")
    subtotal: Decimal = Field(..., ge=0, description="Cart subtotal")
    product_ids: list[uuid.UUID] | None = Field(None, description="Product IDs in cart")


class ValidateDiscountResponse(BaseModel):
    """Schema for discount validation response.

    Attributes:
        valid: Whether the discount code is valid.
        discount_type: Type of discount (percentage, fixed_amount, free_shipping).
        value: The discount value (percentage or fixed amount).
        discount_amount: The calculated discount amount for the given subtotal.
        message: Human-readable validation message.
    """

    valid: bool
    discount_type: str | None = None
    value: Decimal | None = None
    discount_amount: Decimal = Decimal("0.00")
    message: str


class CalculateTaxRequest(BaseModel):
    """Schema for calculating tax before checkout.

    Attributes:
        subtotal: The cart subtotal (after discounts) for tax calculation.
        country: ISO 2-letter country code.
        state: Optional state or province.
        postal_code: Optional postal/ZIP code.
    """

    subtotal: Decimal = Field(..., ge=0, description="Subtotal after discounts")
    country: str = Field(..., min_length=2, max_length=2, description="Country code")
    state: str | None = Field(None, description="State or province")
    postal_code: str | None = Field(None, description="Postal/ZIP code")


class CalculateTaxResponse(BaseModel):
    """Schema for tax calculation response.

    Attributes:
        tax_amount: Total tax amount.
        effective_rate: Effective tax rate as a percentage.
        breakdown: List of individual tax rate contributions.
    """

    tax_amount: Decimal
    effective_rate: Decimal
    breakdown: list[dict] = []


class OrderItemResponse(BaseModel):
    """Schema for returning order item data in API responses.

    Attributes:
        id: The order item's unique identifier.
        order_id: The parent order's UUID.
        product_id: The product's UUID (may be null if product was deleted).
        variant_id: The variant's UUID (may be null).
        product_title: Product title at time of purchase.
        variant_name: Variant name at time of purchase (may be null).
        quantity: Number of units purchased.
        unit_price: Price per unit at time of purchase.
        created_at: When the item was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID | None
    variant_id: uuid.UUID | None
    product_title: str
    variant_name: str | None
    quantity: int
    unit_price: Decimal
    created_at: datetime


class OrderResponse(BaseModel):
    """Schema for returning order data in API responses.

    Includes full financial breakdown (subtotal, discount, tax, gift card,
    total) and structured shipping address.

    Attributes:
        id: The order's unique identifier.
        store_id: The store's UUID.
        customer_email: Customer's email address.
        status: Current order status.
        subtotal: Sum of line item totals before adjustments.
        discount_code: Discount code applied (if any).
        discount_amount: Amount deducted by discount.
        tax_amount: Tax amount charged.
        gift_card_amount: Amount deducted by gift card.
        total: Final total (subtotal - discount + tax - gift card).
        currency: Three-letter currency code.
        stripe_session_id: Stripe Checkout session ID (may be null).
        shipping_address: Structured shipping address (may be null).
        created_at: When the order was created.
        updated_at: When the order was last modified.
        items: List of order line items.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    customer_email: str
    status: OrderStatus
    subtotal: Decimal | None = None
    discount_code: str | None = None
    discount_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    gift_card_amount: Decimal | None = None
    total: Decimal
    currency: str = "USD"
    stripe_session_id: str | None = None
    shipping_address: dict | None = None
    notes: str | None = None
    tracking_number: str | None = None
    carrier: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    @classmethod
    def from_order(cls, order) -> "OrderResponse":
        """Create an OrderResponse from an Order ORM instance.

        Parses the shipping_address JSON string into a dict if present.

        Args:
            order: The Order ORM instance.

        Returns:
            OrderResponse with parsed shipping address.
        """
        address = None
        if order.shipping_address:
            try:
                address = json.loads(order.shipping_address)
            except (json.JSONDecodeError, TypeError):
                address = {"raw": order.shipping_address}

        return cls(
            id=order.id,
            store_id=order.store_id,
            customer_email=order.customer_email,
            status=order.status,
            subtotal=order.subtotal,
            discount_code=order.discount_code,
            discount_amount=order.discount_amount,
            tax_amount=order.tax_amount,
            gift_card_amount=order.gift_card_amount,
            total=order.total,
            currency=order.currency,
            stripe_session_id=order.stripe_session_id,
            shipping_address=address,
            notes=order.notes,
            tracking_number=order.tracking_number,
            carrier=order.carrier,
            shipped_at=order.shipped_at,
            delivered_at=order.delivered_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[OrderItemResponse.model_validate(item) for item in order.items],
        )


class PaginatedOrderResponse(BaseModel):
    """Schema for paginated order list responses.

    Attributes:
        items: List of orders on this page.
        total: Total number of orders matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[OrderResponse]
    total: int
    page: int
    per_page: int
    pages: int


class UpdateOrderStatusRequest(BaseModel):
    """Schema for updating an order's status and optional notes.

    Attributes:
        status: The new order status (optional if only updating notes).
        notes: Optional internal memo/notes for the order.
    """

    status: OrderStatus | None = Field(None, description="New order status")
    notes: str | None = Field(None, description="Internal notes")


class FulfillOrderRequest(BaseModel):
    """Schema for fulfilling (shipping) an order.

    Attributes:
        tracking_number: The shipment tracking number.
        carrier: Optional shipping carrier name (e.g. "USPS", "FedEx").
    """

    tracking_number: str = Field(..., min_length=1, max_length=255, description="Tracking number")
    carrier: str | None = Field(None, max_length=100, description="Shipping carrier")


class CheckoutResponse(BaseModel):
    """Schema for the checkout session creation response.

    Includes the full financial breakdown so the storefront can display
    the order summary before redirecting to Stripe.

    Attributes:
        checkout_url: The Stripe Checkout URL to redirect the customer to.
        session_id: The Stripe Checkout session ID.
        order_id: The UUID of the created pending order.
        subtotal: Sum of line item totals.
        discount_amount: Amount deducted by discount code.
        tax_amount: Tax amount calculated from shipping address.
        gift_card_amount: Amount deducted by gift card.
        total: Final total charged.
    """

    checkout_url: str
    session_id: str
    order_id: uuid.UUID
    subtotal: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    gift_card_amount: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
