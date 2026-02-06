"""Pydantic schemas for order endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/orders/*`` routes and the public checkout
endpoint.

**For Developers:**
    ``CheckoutItemRequest`` validates individual cart items for checkout.
    ``CheckoutRequest`` wraps the full cart submission.
    ``OrderResponse`` and ``OrderItemResponse`` use ``from_attributes``
    to serialize ORM instances. Pagination is handled via
    ``PaginatedOrderResponse``.

**For QA Engineers:**
    - ``CheckoutItemRequest.quantity`` must be >= 1.
    - ``CheckoutRequest.customer_email`` must be a valid email.
    - ``OrderResponse`` includes nested order items.
    - ``UpdateOrderStatusRequest`` only allows valid status transitions.

**For End Users:**
    When checking out, provide your email and the items in your cart.
    Each item needs a product ID, optional variant ID, and quantity.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.order import OrderStatus


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
    """

    customer_email: EmailStr = Field(..., description="Customer email address")
    items: list[CheckoutItemRequest] = Field(
        ..., min_length=1, description="Cart items"
    )


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

    Attributes:
        id: The order's unique identifier.
        store_id: The store's UUID.
        customer_email: Customer's email address.
        status: Current order status.
        total: Total order amount.
        stripe_session_id: Stripe Checkout session ID (may be null).
        shipping_address: Shipping address (may be null).
        created_at: When the order was created.
        updated_at: When the order was last modified.
        items: List of order line items.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    customer_email: str
    status: OrderStatus
    total: Decimal
    stripe_session_id: str | None
    shipping_address: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []


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
    """Schema for updating an order's status.

    Attributes:
        status: The new order status.
    """

    status: OrderStatus = Field(..., description="New order status")


class CheckoutResponse(BaseModel):
    """Schema for the checkout session creation response.

    Attributes:
        checkout_url: The Stripe Checkout URL to redirect the customer to.
        session_id: The Stripe Checkout session ID.
        order_id: The UUID of the created pending order.
    """

    checkout_url: str
    session_id: str
    order_id: uuid.UUID
