"""Pydantic schemas for customer segment endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/segments/*`` routes.

**For Developers:**
    ``CreateSegmentRequest`` and ``UpdateSegmentRequest`` are input schemas.
    ``SegmentResponse`` uses ``from_attributes``. Segments can be
    ``"manual"`` (hand-picked customers) or ``"dynamic"`` (rule-based
    filters evaluated at query time).

**For QA Engineers:**
    - ``CreateSegmentRequest.name`` is required, 1-255 characters.
    - ``segment_type`` must be ``"manual"`` or ``"dynamic"``.
    - ``rules`` is a freeform dict for dynamic segments (e.g.
      ``{"min_orders": 3, "country": "US"}``).
    - ``AddCustomersToSegmentRequest`` only applies to manual segments.

**For Project Managers:**
    Customer segments enable targeted marketing. Dynamic segments
    auto-update based on rules (e.g. "customers with 3+ orders").
    Manual segments are curated lists. Segments integrate with
    email marketing and discount targeting.

**For End Users:**
    Store owners create customer segments on the dashboard to organise
    their customer base for targeted promotions and communications.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateSegmentRequest(BaseModel):
    """Schema for creating a new customer segment.

    Attributes:
        name: Display name of the segment (1-255 characters).
        description: Optional description of the segment's purpose.
        segment_type: Either ``"manual"`` (hand-picked) or ``"dynamic"``
            (rule-based auto-updating).
        rules: Optional rule definitions for dynamic segments. Structure
            depends on segment_type. Example:
            ``{"min_orders": 3, "country": "US"}``.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Segment name"
    )
    description: str | None = Field(
        None, max_length=1000, description="Segment description"
    )
    segment_type: str = Field(
        ..., description='Segment type: "manual" or "dynamic"'
    )
    rules: dict | None = Field(
        None, description="Dynamic segment rules"
    )


class UpdateSegmentRequest(BaseModel):
    """Schema for updating an existing segment (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        name: New segment name.
        description: New description.
        segment_type: New segment type.
        rules: New rule definitions.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    segment_type: str | None = None
    rules: dict | None = None


class SegmentResponse(BaseModel):
    """Schema for returning segment data in API responses.

    Attributes:
        id: The segment's unique identifier.
        store_id: The parent store's UUID.
        name: Display name of the segment.
        description: Segment description (may be null).
        segment_type: ``"manual"`` or ``"dynamic"``.
        rules: Dynamic segment rules (may be null for manual segments).
        customer_count: Number of customers currently in this segment.
        created_at: When the segment was created.
        updated_at: When the segment was last modified.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    description: str | None
    segment_type: str
    rules: dict | None
    customer_count: int
    created_at: datetime
    updated_at: datetime


class PaginatedSegmentResponse(BaseModel):
    """Schema for paginated segment list responses.

    Attributes:
        items: List of segments on this page.
        total: Total number of segments matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[SegmentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AddCustomersToSegmentRequest(BaseModel):
    """Schema for adding customers to a manual segment.

    Attributes:
        customer_ids: List of customer UUIDs to add to the segment.
    """

    customer_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Customer UUIDs to add"
    )
