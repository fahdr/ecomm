"""Pydantic schemas for fraud detection endpoints (Feature 28).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/fraud-checks/*`` routes.

**For Developers:**
    ``FraudCheckResponse`` uses ``from_attributes``. Fraud checks are
    created automatically when orders are placed. ``ReviewFraudRequest``
    is the admin action to flag/unflag orders after manual review.

**For QA Engineers:**
    - ``FraudCheckResponse.risk_level`` is ``"low"``, ``"medium"``,
      or ``"high"``.
    - ``FraudCheckResponse.risk_score`` is 0-100 (higher = riskier).
    - ``FraudCheckResponse.signals`` is a list of triggered risk
      indicators (e.g. ``["ip_country_mismatch", "high_order_value"]``).
    - ``ReviewFraudRequest.is_flagged`` is a boolean (flag or clear).

**For Project Managers:**
    Fraud detection protects merchants from chargebacks and losses.
    The system automatically scores each order based on risk signals
    (IP mismatch, velocity, amount thresholds). High-risk orders are
    flagged for manual review before fulfilment.

**For End Users:**
    Orders are automatically screened for fraud. Flagged orders appear
    in a review queue on the dashboard where you can approve or block
    them before fulfilling.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FraudCheckResponse(BaseModel):
    """Schema for returning fraud check data in API responses.

    Attributes:
        id: The fraud check's unique identifier.
        store_id: The parent store's UUID.
        order_id: The associated order's UUID.
        risk_level: Overall risk assessment (``"low"``, ``"medium"``,
            or ``"high"``).
        risk_score: Numeric risk score from 0 (safe) to 100 (fraudulent).
        signals: List of triggered risk indicators (e.g.
            ``["ip_country_mismatch", "high_order_value"]``).
        is_flagged: Whether the order has been manually flagged for
            review.
        reviewed_by: UUID of the admin who reviewed (null if unreviewed).
        reviewed_at: When the review was completed (null if unreviewed).
        notes: Admin review notes (may be null).
        created_at: When the fraud check was performed.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    order_id: uuid.UUID
    risk_level: str
    risk_score: float
    signals: list[str]
    is_flagged: bool
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    notes: str | None
    created_at: datetime


class ReviewFraudRequest(BaseModel):
    """Schema for manually reviewing a fraud check (admin action).

    Attributes:
        is_flagged: Whether to flag (``true``) or clear (``false``)
            the fraud flag on the order.
        notes: Optional notes about the review decision.
    """

    is_flagged: bool = Field(
        ..., description="Flag or clear the fraud flag"
    )
    notes: str | None = Field(
        None, max_length=2000, description="Review notes"
    )


class PaginatedFraudCheckResponse(BaseModel):
    """Schema for paginated fraud check list responses.

    Attributes:
        items: List of fraud checks on this page.
        total: Total number of fraud checks matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[FraudCheckResponse]
    total: int
    page: int
    per_page: int
    pages: int
