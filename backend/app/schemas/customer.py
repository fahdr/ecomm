"""Pydantic schemas for customer account API endpoints.

Defines request and response models for customer registration, login,
profile management, addresses, wishlist, and order history.

**For Developers:**
    All schemas use Pydantic v2 ``model_config`` style. Datetime fields
    use ``datetime`` type and are serialised as ISO 8601 strings.

**For QA Engineers:**
    - ``CustomerRegisterRequest`` requires email, password (min 6 chars).
    - ``CustomerLoginRequest`` requires email and password.
    - ``CustomerAddressRequest`` requires name, line1, city, postal_code, country.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---

class CustomerRegisterRequest(BaseModel):
    """Request body for customer registration."""
    email: EmailStr
    password: str = Field(min_length=6)
    first_name: str | None = None
    last_name: str | None = None


class CustomerLoginRequest(BaseModel):
    """Request body for customer login."""
    email: EmailStr
    password: str


class CustomerTokenResponse(BaseModel):
    """Response containing access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    customer: "CustomerProfileResponse"


class CustomerRefreshRequest(BaseModel):
    """Request body for refreshing an access token."""
    refresh_token: str


class CustomerTokenRefreshResponse(BaseModel):
    """Response after refreshing an access token."""
    access_token: str
    token_type: str = "bearer"


# --- Profile ---

class CustomerProfileResponse(BaseModel):
    """Customer profile data."""
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerUpdateRequest(BaseModel):
    """Request body for updating customer profile."""
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None


class CustomerChangePasswordRequest(BaseModel):
    """Request body for changing password."""
    current_password: str
    new_password: str = Field(min_length=6)


class CustomerForgotPasswordRequest(BaseModel):
    """Request body for forgot password."""
    email: EmailStr


class CustomerResetPasswordRequest(BaseModel):
    """Request body for resetting password with token."""
    token: str
    new_password: str = Field(min_length=6)


# --- Addresses ---

class CustomerAddressRequest(BaseModel):
    """Request body for creating/updating an address."""
    label: str = Field(default="Home", max_length=50)
    name: str = Field(max_length=255)
    line1: str = Field(max_length=255)
    line2: str | None = None
    city: str = Field(max_length=100)
    state: str | None = None
    postal_code: str = Field(max_length=20)
    country: str = Field(max_length=2, description="ISO 3166-1 alpha-2")
    phone: str | None = None
    is_default: bool = False


class CustomerAddressResponse(BaseModel):
    """Response for a customer address."""
    id: uuid.UUID
    label: str
    name: str
    line1: str
    line2: str | None
    city: str
    state: str | None
    postal_code: str
    country: str
    phone: str | None
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Orders ---

class CustomerOrderItemResponse(BaseModel):
    """Order item in customer order history."""
    id: uuid.UUID
    product_title: str
    variant_name: str | None
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class CustomerOrderResponse(BaseModel):
    """Order in customer order history."""
    id: uuid.UUID
    status: str
    total: Decimal
    subtotal: Decimal | None
    discount_code: str | None
    discount_amount: Decimal | None
    tax_amount: Decimal | None
    gift_card_amount: Decimal | None
    currency: str
    shipping_address: str | None
    tracking_number: str | None = None
    carrier: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    items: list[CustomerOrderItemResponse] = []

    model_config = {"from_attributes": True}


# --- Wishlist ---

class WishlistItemResponse(BaseModel):
    """A product in the customer's wishlist."""
    id: uuid.UUID
    product_id: uuid.UUID
    product_title: str | None = None
    product_slug: str | None = None
    product_price: Decimal | None = None
    product_image: str | None = None
    added_at: datetime

    model_config = {"from_attributes": True}
