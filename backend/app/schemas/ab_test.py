"""Pydantic schemas for A/B testing endpoints (Feature 29).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/ab-tests/*`` routes.

**For Developers:**
    ``CreateABTestRequest`` includes nested ``ABTestVariantInput`` items.
    ``ABTestResponse`` uses ``from_attributes`` and includes nested
    ``ABTestVariantResponse`` items with computed ``conversion_rate``.
    ``RecordEventRequest`` captures impressions and conversions.

**For QA Engineers:**
    - ``ABTestVariantInput.weight`` controls traffic allocation (0-100).
    - Exactly one variant should have ``is_control=True``.
    - ``RecordEventRequest.event_type`` must be ``"impression"`` or
      ``"conversion"``.
    - ``ABTestVariantResponse.conversion_rate`` is computed as
      ``conversions / impressions`` (0.0 if no impressions).
    - ``ABTestResponse.status`` cycles through ``"draft"``, ``"running"``,
      ``"paused"``, ``"completed"``.

**For Project Managers:**
    A/B testing enables data-driven storefront optimization. Merchants
    test different product pages, pricing, or copy and measure impact
    on conversion rates and revenue. Statistical significance is
    tracked to declare winners.

**For End Users:**
    Create experiments to test different versions of your storefront.
    Track impressions, conversions, and revenue to find what works best.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ABTestVariantInput(BaseModel):
    """Schema for defining a variant when creating an A/B test.

    Attributes:
        name: Display name of the variant (e.g. ``"Control"``,
            ``"New Hero Image"``).
        description: Optional description of what this variant changes.
        weight: Traffic allocation weight (0-100). Weights across all
            variants in a test should sum to 100.
        is_control: Whether this is the control (baseline) variant.
            Exactly one variant per test should be the control.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Variant name"
    )
    description: str | None = Field(
        None, max_length=1000, description="Variant description"
    )
    weight: int = Field(
        50, ge=0, le=100, description="Traffic weight (0-100)"
    )
    is_control: bool = Field(
        False, description="Is this the control variant?"
    )


class CreateABTestRequest(BaseModel):
    """Schema for creating a new A/B test.

    Attributes:
        name: Display name of the experiment (1-255 characters).
        description: Optional description of the experiment's hypothesis.
        metric: The primary metric to measure (e.g. ``"conversion_rate"``,
            ``"revenue_per_visitor"``, ``"add_to_cart_rate"``).
        variants: List of variant definitions (minimum 2).
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Experiment name"
    )
    description: str | None = Field(
        None, max_length=1000, description="Experiment hypothesis"
    )
    metric: str = Field(
        ..., description="Primary metric to measure"
    )
    variants: list[ABTestVariantInput] = Field(
        ..., min_length=2, description="Variant definitions"
    )


class UpdateABTestRequest(BaseModel):
    """Schema for updating an existing A/B test (partial update).

    Attributes:
        name: New experiment name.
        status: New status (``"draft"``, ``"running"``, ``"paused"``,
            ``"completed"``).
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = None


class ABTestVariantResponse(BaseModel):
    """Schema for returning variant data with performance metrics.

    Attributes:
        id: The variant's unique identifier.
        name: Display name of the variant.
        weight: Traffic allocation weight.
        is_control: Whether this is the control variant.
        impressions: Total number of impressions (views).
        conversions: Total number of conversions.
        revenue: Total revenue attributed to this variant.
        conversion_rate: Computed conversion rate (conversions /
            impressions). Returns 0.0 if no impressions.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    weight: int
    is_control: bool
    impressions: int
    conversions: int
    revenue: Decimal
    conversion_rate: float


class ABTestResponse(BaseModel):
    """Schema for returning A/B test data in API responses.

    Attributes:
        id: The test's unique identifier.
        store_id: The parent store's UUID.
        name: Experiment name.
        description: Experiment hypothesis (may be null).
        status: Current status (``"draft"``, ``"running"``, ``"paused"``,
            ``"completed"``).
        metric: Primary metric being measured.
        started_at: When the test was started (null if still draft).
        ended_at: When the test was stopped (null if still running).
        variants: List of variants with their performance metrics.
        created_at: When the test was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    description: str | None
    status: str
    metric: str
    started_at: datetime | None
    ended_at: datetime | None
    variants: list[ABTestVariantResponse] = []
    created_at: datetime


class PaginatedABTestResponse(BaseModel):
    """Schema for paginated A/B test list responses.

    Attributes:
        items: List of A/B tests on this page.
        total: Total number of tests matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[ABTestResponse]
    total: int
    page: int
    per_page: int
    pages: int


class RecordEventRequest(BaseModel):
    """Schema for recording an A/B test event (impression or conversion).

    Attributes:
        variant_id: UUID of the variant the event is attributed to.
        event_type: Type of event: ``"impression"`` (page view) or
            ``"conversion"`` (desired action completed).
        revenue: Optional revenue amount associated with a conversion
            event.
    """

    variant_id: uuid.UUID = Field(..., description="Variant UUID")
    event_type: str = Field(
        ..., description='Event type: "impression" or "conversion"'
    )
    revenue: Decimal | None = Field(
        None, ge=0, description="Revenue for conversion events"
    )
