"""Pydantic schemas for customer endpoints.

These schemas validate incoming requests and shape outgoing responses for
customer authentication, profile management, and dashboard customer views.

**For Developers:**
    ``CustomerRegisterRequest`` and ``CustomerLoginRequest`` handle storefront
    auth. ``CustomerResponse`` uses ``from_attributes`` for ORM serialization.
    ``CustomerDetailResponse`` adds aggregated order stats for the dashboard.

**For QA Engineers:**
    - ``CustomerRegisterRequest.password`` must be at least 8 characters.
    - ``CustomerRegisterRequest.email`` must be a valid email.
    - ``CustomerDetailResponse`` includes ``order_count`` and ``total_spent``.

**For End Users:**
    Register with your email and password. Optionally add your name and
    phone number to your profile.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class CustomerRegisterRequest(BaseModel):
    """Schema for customer registration on a storefront.

    Attributes:
        email: Valid email address.
        password: Password (minimum 8 characters).
        first_name: Optional first name.
        last_name: Optional last name.
    """

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str | None = Field(None, max_length=255)
    last_name: str | None = Field(None, max_length=255)


class CustomerLoginRequest(BaseModel):
    """Schema for customer login.

    Attributes:
        email: Registered email address.
        password: Account password.
    """

    email: EmailStr
    password: str


class CustomerTokenResponse(BaseModel):
    """Schema for customer auth token responses.

    Attributes:
        access_token: Short-lived JWT access token.
        refresh_token: Long-lived JWT refresh token.
        token_type: Token type (always "bearer").
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CustomerRefreshRequest(BaseModel):
    """Schema for refreshing customer tokens.

    Attributes:
        refresh_token: The refresh token to exchange.
    """

    refresh_token: str


class CustomerResponse(BaseModel):
    """Schema for returning customer profile data.

    Attributes:
        id: Customer UUID.
        store_id: Store UUID this customer belongs to.
        email: Customer email.
        first_name: Optional first name.
        last_name: Optional last name.
        phone: Optional phone number.
        is_active: Whether the account is active.
        created_at: Account creation timestamp.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    phone: str | None
    is_active: bool
    created_at: datetime


class CustomerUpdateRequest(BaseModel):
    """Schema for updating customer profile fields.

    Attributes:
        first_name: New first name (optional).
        last_name: New last name (optional).
        phone: New phone number (optional).
    """

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class CustomerDetailResponse(CustomerResponse):
    """Extended customer response with order statistics for the dashboard.

    Attributes:
        order_count: Total number of orders placed by this customer.
        total_spent: Total amount spent across all orders.
    """

    order_count: int = 0
    total_spent: Decimal = Decimal("0.00")


class PaginatedCustomerResponse(BaseModel):
    """Schema for paginated customer list responses.

    Attributes:
        items: List of customers on this page.
        total: Total number of customers matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[CustomerResponse]
    total: int
    page: int
    per_page: int
    pages: int
