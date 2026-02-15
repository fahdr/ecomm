"""Pydantic schemas for refund endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/refunds/*`` routes.

**For Developers:**
    ``CreateRefundRequest`` initiates a refund. ``UpdateRefundRequest`` is
    used by store admins to approve/reject. ``RefundResponse`` uses
    ``from_attributes`` to serialize ORM instances.

**For QA Engineers:**
    - ``CreateRefundRequest.amount`` must be > 0.
    - ``CreateRefundRequest.reason`` is required (1-255 characters).
    - ``UpdateRefundRequest.status`` should be ``"approved"``,
      ``"rejected"``, or ``"processing"``.
    - ``RefundResponse.stripe_refund_id`` is populated only after the
      refund has been processed through Stripe.

**For Project Managers:**
    Refunds follow a review workflow: requested -> approved/rejected.
    Approved refunds are processed through Stripe. In a dropshipping
    model there are no physical returns -- the supplier cost may or
    may not be recoverable.

**For End Users:**
    Request a refund through your order history. Provide a reason and
    the amount. The store owner will review and approve or reject.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateRefundRequest(BaseModel):
    """Schema for requesting a refund on an order.

    Attributes:
        order_id: UUID of the order to refund.
        reason: Short reason for the refund request (1-255 characters).
        reason_details: Optional extended explanation.
        amount: Refund amount (must be > 0 and <= order total).
    """

    order_id: uuid.UUID = Field(..., description="Order UUID to refund")
    reason: str = Field(
        ..., min_length=1, max_length=255, description="Refund reason"
    )
    reason_details: str | None = Field(
        None, max_length=2000, description="Extended explanation"
    )
    amount: Decimal = Field(
        ..., gt=0, description="Refund amount"
    )


class UpdateRefundRequest(BaseModel):
    """Schema for updating a refund status (admin action).

    Attributes:
        status: New refund status (``"approved"``, ``"rejected"``,
            or ``"processing"``).
        admin_notes: Optional notes from the admin about the decision.
    """

    status: str = Field(
        ..., description='New status: "approved", "rejected", or "processing"'
    )
    admin_notes: str | None = Field(
        None, max_length=2000, description="Admin notes"
    )


class RefundResponse(BaseModel):
    """Schema for returning refund data in API responses.

    Attributes:
        id: The refund's unique identifier.
        store_id: The parent store's UUID.
        order_id: The associated order's UUID.
        customer_email: Email of the customer who requested the refund.
        reason: Short refund reason.
        reason_details: Extended explanation (may be null).
        amount: Refund amount.
        status: Current status (``"pending"``, ``"approved"``,
            ``"rejected"``, ``"processing"``, ``"completed"``).
        stripe_refund_id: Stripe Refund object ID (may be null if
            not yet processed).
        admin_notes: Notes from admin review (may be null).
        created_at: When the refund was requested.
        updated_at: When the refund was last modified.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    order_id: uuid.UUID
    customer_email: str
    reason: str
    reason_details: str | None
    amount: Decimal
    status: str
    stripe_refund_id: str | None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedRefundResponse(BaseModel):
    """Schema for paginated refund list responses.

    Attributes:
        items: List of refunds on this page.
        total: Total number of refunds matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[RefundResponse]
    total: int
    page: int
    per_page: int
    pages: int
