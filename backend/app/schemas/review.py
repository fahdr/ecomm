"""Pydantic schemas for product review endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/products/{product_id}/reviews/*`` routes.

**For Developers:**
    ``CreateReviewRequest`` is the public-facing input schema (submitted
    via the storefront). ``UpdateReviewStatusRequest`` is admin-only for
    moderation. ``ReviewResponse`` uses ``from_attributes``.
    ``ReviewStatsResponse`` aggregates star-rating distribution.

**For QA Engineers:**
    - ``CreateReviewRequest.rating`` must be 1-5 inclusive.
    - ``CreateReviewRequest.customer_name`` is required (1-255 chars).
    - ``UpdateReviewStatusRequest.status`` should be ``"approved"``,
      ``"rejected"``, or ``"pending"``.
    - ``ReviewStatsResponse.rating_distribution`` keys are ``"1"``
      through ``"5"``.

**For Project Managers:**
    Product reviews build social proof. Reviews go through a moderation
    queue (``pending`` -> ``approved``/``rejected``). Verified-purchase
    reviews are flagged automatically when the reviewer's email matches
    a past order.

**For End Users:**
    Leave a review on any product you have purchased. Provide a 1-5
    star rating, an optional title, and your feedback.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CreateReviewRequest(BaseModel):
    """Schema for submitting a new product review.

    Attributes:
        rating: Star rating from 1 (worst) to 5 (best).
        title: Optional short headline for the review.
        body: Optional detailed review text.
        customer_name: Display name of the reviewer (1-255 characters).
        customer_email: Email address of the reviewer (used to check
            verified-purchase status).
    """

    rating: int = Field(
        ..., ge=1, le=5, description="Star rating (1-5)"
    )
    title: str | None = Field(
        None, max_length=255, description="Review headline"
    )
    body: str | None = Field(
        None, max_length=5000, description="Detailed review text"
    )
    customer_name: str = Field(
        ..., min_length=1, max_length=255, description="Reviewer display name"
    )
    customer_email: EmailStr = Field(
        ..., description="Reviewer email address"
    )


class UpdateReviewStatusRequest(BaseModel):
    """Schema for moderating a review (admin-only).

    Attributes:
        status: New moderation status: ``"approved"``, ``"rejected"``,
            or ``"pending"``.
    """

    status: str = Field(
        ..., description='Moderation status: "approved", "rejected", or "pending"'
    )


class ReviewResponse(BaseModel):
    """Schema for returning review data in API responses.

    Attributes:
        id: The review's unique identifier.
        store_id: The parent store's UUID.
        product_id: The reviewed product's UUID.
        customer_id: The customer account UUID (may be null for
            guest reviews).
        customer_name: Display name of the reviewer.
        rating: Star rating (1-5).
        title: Review headline (may be null).
        body: Detailed review text (may be null).
        status: Moderation status (``"pending"``, ``"approved"``,
            ``"rejected"``).
        is_verified_purchase: Whether the reviewer has a confirmed
            order for this product.
        created_at: When the review was submitted.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID
    customer_id: uuid.UUID | None
    customer_name: str
    rating: int
    title: str | None
    body: str | None
    status: str
    is_verified_purchase: bool
    created_at: datetime


class PaginatedReviewResponse(BaseModel):
    """Schema for paginated review list responses.

    Attributes:
        items: List of reviews on this page.
        total: Total number of reviews matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[ReviewResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ReviewStatsResponse(BaseModel):
    """Schema for aggregated review statistics for a product.

    Attributes:
        average_rating: Mean star rating across all approved reviews.
        total_reviews: Total number of approved reviews.
        rating_distribution: Breakdown of reviews by star level.
            Keys are ``"1"`` through ``"5"``; values are counts.
    """

    average_rating: float
    total_reviews: int
    rating_distribution: dict[str, int]
