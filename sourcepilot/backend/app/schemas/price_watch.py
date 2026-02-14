"""
Pydantic schemas for price watch endpoints.

Defines request/response data structures for creating, listing,
and managing supplier price monitoring entries.

For Developers:
    Price values use float in schemas (converted to/from Decimal in the model).
    The ``connection_id`` field in the API maps to ``store_id`` in the model.
    The ``product_url`` field stores the user-provided URL for the product.

For Project Managers:
    These schemas define the API contract for the price monitoring feature.

For QA Engineers:
    Test price watch creation with valid/invalid data. Verify the sync
    trigger endpoint works correctly. Test filtering by connection_id.

For End Users:
    Add price watches to track supplier price changes for your imported
    products. View which prices have changed since your last check.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PriceWatchCreate(BaseModel):
    """
    Request body for adding a new price watch.

    Attributes:
        product_url: URL of the product to monitor on the supplier platform.
        source: Supplier platform where the product is listed.
        threshold_percent: Percentage change threshold to trigger an alert (default 10.0).
        connection_id: Optional UUID of the store connection this watch belongs to.
    """

    product_url: str = Field(
        ...,
        max_length=2000,
        description="URL of the product to monitor on the supplier platform",
    )
    source: str = Field(
        ...,
        description="Supplier platform: aliexpress, cjdropship, spocket",
    )
    threshold_percent: float = Field(
        default=10.0,
        ge=0,
        description="Price change threshold percentage to trigger alerts",
    )
    connection_id: uuid.UUID | None = Field(
        default=None,
        description="Optional UUID of the store connection",
    )


class PriceWatchResponse(BaseModel):
    """
    Response schema for a single price watch.

    Attributes:
        id: Price watch unique identifier.
        user_id: Owning user identifier.
        product_url: URL of the monitored product.
        source: Supplier platform.
        threshold_percent: Alert threshold percentage.
        connection_id: Associated store connection identifier (nullable).
        store_id: Legacy alias for connection_id (nullable).
        is_active: Whether the watch is enabled.
        source_product_id: Product ID on the supplier (nullable, legacy).
        source_url: Resolved product URL on the supplier (nullable, legacy).
        last_price: Last known price (nullable).
        current_price: Most recently observed price (nullable).
        price_changed: Whether price differs from last known.
        last_checked_at: Last price check timestamp.
        created_at: Watch creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    product_url: str | None = None
    source: str
    threshold_percent: float = 10.0
    connection_id: uuid.UUID | None = None
    store_id: uuid.UUID | None = None
    is_active: bool = True
    source_product_id: str | None = None
    source_url: str | None = None
    last_price: float | None = None
    current_price: float | None = None
    price_changed: bool = False
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PriceWatchList(BaseModel):
    """
    List of price watches with optional filtering.

    Attributes:
        items: List of price watches.
        total: Total number of watches matching the query.
    """

    items: list[PriceWatchResponse]
    total: int
