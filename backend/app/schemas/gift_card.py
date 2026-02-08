"""Pydantic schemas for gift card endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/gift-cards/*`` routes.

**For Developers:**
    ``CreateGiftCardRequest`` is the input schema. ``GiftCardResponse``
    uses ``from_attributes``. ``ApplyGiftCardRequest`` /
    ``ApplyGiftCardResponse`` handle gift card validation at checkout.
    ``GiftCardTransactionResponse`` tracks balance changes.

**For QA Engineers:**
    - ``CreateGiftCardRequest.initial_balance`` must be > 0.
    - Gift card codes are auto-generated (16-char alphanumeric).
    - ``GiftCardResponse.current_balance`` must be <= ``initial_balance``.
    - ``ApplyGiftCardResponse.valid`` indicates whether the card is usable.
    - ``GiftCardTransactionResponse.transaction_type`` is ``"debit"``
      or ``"credit"``.

**For Project Managers:**
    Gift cards are a revenue driver and retention tool. Store owners
    issue gift cards with a set balance. Customers redeem them at
    checkout, and the balance decreases per transaction.

**For End Users:**
    Purchase or receive a gift card, then enter the code at checkout
    to apply the balance toward your order.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class CreateGiftCardRequest(BaseModel):
    """Schema for creating a new gift card.

    Attributes:
        initial_balance: The starting balance of the gift card (> 0).
        customer_email: Optional email of the recipient. If provided,
            the gift card is sent to this address.
        expires_at: Optional expiration datetime. ``None`` means the
            card does not expire.
    """

    initial_balance: Decimal = Field(
        ..., gt=0, description="Starting balance"
    )
    customer_email: EmailStr | None = Field(
        None, description="Recipient email address"
    )
    expires_at: datetime | None = Field(
        None, description="Expiration datetime"
    )


class GiftCardResponse(BaseModel):
    """Schema for returning gift card data in API responses.

    Attributes:
        id: The gift card's unique identifier.
        store_id: The parent store's UUID.
        code: The 16-character alphanumeric redemption code.
        initial_balance: The original balance when issued.
        current_balance: The remaining balance.
        status: Current status (``"active"``, ``"depleted"``,
            ``"expired"``, ``"disabled"``).
        customer_email: Recipient email (may be null).
        expires_at: Expiration datetime (may be null).
        created_at: When the gift card was issued.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    code: str
    initial_balance: Decimal
    current_balance: Decimal
    status: str
    customer_email: str | None
    expires_at: datetime | None
    created_at: datetime


class PaginatedGiftCardResponse(BaseModel):
    """Schema for paginated gift card list responses.

    Attributes:
        items: List of gift cards on this page.
        total: Total number of gift cards matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[GiftCardResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ApplyGiftCardRequest(BaseModel):
    """Schema for applying a gift card code at checkout.

    Attributes:
        code: The gift card redemption code.
    """

    code: str = Field(
        ..., min_length=1, max_length=50, description="Gift card code"
    )


class ApplyGiftCardResponse(BaseModel):
    """Schema for the result of applying a gift card code.

    Attributes:
        valid: Whether the gift card code is valid and has a balance.
        balance: Remaining balance on the card (null if invalid).
        message: Human-readable message explaining the result.
    """

    valid: bool
    balance: Decimal | None = None
    message: str


class GiftCardTransactionResponse(BaseModel):
    """Schema for returning a gift card balance transaction.

    Attributes:
        id: The transaction's unique identifier.
        gift_card_id: The associated gift card's UUID.
        order_id: The order that triggered this transaction (may be null
            for manual adjustments).
        amount: Transaction amount (positive for credits, negative for
            debits).
        transaction_type: ``"debit"`` (checkout usage) or ``"credit"``
            (refund or manual top-up).
        note: Optional note explaining the transaction.
        created_at: When the transaction occurred.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    gift_card_id: uuid.UUID
    order_id: uuid.UUID | None
    amount: Decimal
    transaction_type: str
    note: str | None
    created_at: datetime
