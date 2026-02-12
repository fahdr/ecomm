"""
Pydantic schemas for competitors, products, alerts, scans, and source matches.

Defines all request and response models for the SpyDrop feature-specific
API endpoints. Uses Pydantic v2 with strict validation and from_attributes
for ORM model compatibility.

For Developers:
    All response schemas set `model_config = {"from_attributes": True}` to
    allow direct serialization from SQLAlchemy model instances. Request
    schemas use Field() for validation constraints and descriptions.

For QA Engineers:
    Test validation by sending invalid payloads (e.g., empty name, invalid
    platform, out-of-range threshold). Verify 422 responses with clear
    error messages.

For Project Managers:
    These schemas define the API contract. The response shapes determine
    what data the dashboard and external integrations receive.

For End Users:
    These schemas define the data you send to and receive from the API.
    See the interactive docs at /docs for examples.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Competitor Schemas ──────────────────────────────────────────────


class CompetitorCreate(BaseModel):
    """
    Request schema for creating a new competitor.

    Attributes:
        name: Human-readable name for the competitor store.
        url: The competitor's store URL (e.g., https://competitor.com).
        platform: E-commerce platform type ('shopify', 'woocommerce', 'custom').
    """

    name: str = Field(..., min_length=1, max_length=255, description="Competitor store name")
    url: str = Field(..., min_length=1, max_length=2048, description="Store URL")
    platform: str = Field(
        default="custom",
        description="E-commerce platform: shopify, woocommerce, or custom",
    )


class CompetitorUpdate(BaseModel):
    """
    Request schema for updating a competitor.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated store name.
        url: Updated store URL.
        platform: Updated platform type.
        status: Updated monitoring status ('active', 'paused').
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    url: str | None = Field(None, min_length=1, max_length=2048)
    platform: str | None = None
    status: str | None = None


class CompetitorResponse(BaseModel):
    """
    Response schema for a competitor record.

    Attributes:
        id: Unique identifier.
        name: Competitor store name.
        url: Store URL.
        platform: E-commerce platform type.
        last_scanned: Timestamp of most recent scan (null if never scanned).
        status: Monitoring status.
        product_count: Number of tracked products.
        created_at: When the competitor was added.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    name: str
    url: str
    platform: str
    last_scanned: datetime | None
    status: str
    product_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorListResponse(BaseModel):
    """
    Paginated list of competitors.

    Attributes:
        items: List of competitor records.
        total: Total number of competitors matching the query.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[CompetitorResponse]
    total: int
    page: int
    per_page: int


# ── Competitor Product Schemas ──────────────────────────────────────


class PriceHistoryEntry(BaseModel):
    """
    A single entry in a product's price history.

    Attributes:
        date: The date of the price observation.
        price: The product price at that date.
    """

    date: str
    price: float


class CompetitorProductResponse(BaseModel):
    """
    Response schema for a competitor's product.

    Attributes:
        id: Unique identifier.
        competitor_id: Parent competitor ID.
        title: Product title.
        url: Product page URL.
        image_url: Product image URL (optional).
        price: Current product price.
        currency: Price currency code.
        first_seen: When the product was first discovered.
        last_seen: When the product was last seen in a scan.
        price_history: List of historical price entries.
        status: Product availability status.
        competitor_name: Name of the parent competitor (for display).
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    competitor_id: uuid.UUID
    title: str
    url: str
    image_url: str | None
    price: float | None
    currency: str
    first_seen: datetime
    last_seen: datetime
    price_history: list[PriceHistoryEntry] = []
    status: str
    competitor_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorProductListResponse(BaseModel):
    """
    Paginated list of competitor products.

    Attributes:
        items: List of product records.
        total: Total number of products matching the query.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[CompetitorProductResponse]
    total: int
    page: int
    per_page: int


# ── Alert Schemas ───────────────────────────────────────────────────


class AlertCreate(BaseModel):
    """
    Request schema for creating a price alert.

    Attributes:
        competitor_product_id: Optional product to monitor (for product-specific alerts).
        competitor_id: Optional competitor to monitor (for store-wide alerts).
        alert_type: Type of alert ('price_drop', 'price_increase', 'new_product',
            'out_of_stock', 'back_in_stock').
        threshold: Percentage threshold for price-based alerts (e.g., 10.0 = 10%).
    """

    competitor_product_id: uuid.UUID | None = None
    competitor_id: uuid.UUID | None = None
    alert_type: str = Field(
        ...,
        description="Alert type: price_drop, price_increase, new_product, out_of_stock, back_in_stock",
    )
    threshold: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentage threshold for price alerts (0-100)",
    )


class AlertUpdate(BaseModel):
    """
    Request schema for updating an alert.

    Attributes:
        alert_type: Updated alert type.
        threshold: Updated threshold percentage.
        is_active: Whether the alert is active.
    """

    alert_type: str | None = None
    threshold: float | None = None
    is_active: bool | None = None


class AlertResponse(BaseModel):
    """
    Response schema for a price alert.

    Attributes:
        id: Unique identifier.
        user_id: Owning user ID.
        competitor_product_id: Monitored product ID (optional).
        competitor_id: Monitored competitor ID (optional).
        alert_type: Type of alert.
        threshold: Percentage threshold.
        is_active: Whether the alert is active.
        last_triggered: When the alert was last triggered.
        created_at: Creation timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    competitor_product_id: uuid.UUID | None
    competitor_id: uuid.UUID | None
    alert_type: str
    threshold: float | None
    is_active: bool
    last_triggered: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """
    Paginated list of alerts.

    Attributes:
        items: List of alert records.
        total: Total number of alerts.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[AlertResponse]
    total: int
    page: int
    per_page: int


class AlertHistoryResponse(BaseModel):
    """
    Response schema for an alert history entry.

    Attributes:
        id: Unique identifier.
        alert_id: Parent alert ID.
        message: Human-readable alert message.
        data: Contextual data (JSON dict).
        created_at: When the alert was triggered.
    """

    id: uuid.UUID
    alert_id: uuid.UUID
    message: str
    data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryListResponse(BaseModel):
    """
    Paginated list of alert history entries.

    Attributes:
        items: List of alert history entries.
        total: Total number of entries.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[AlertHistoryResponse]
    total: int
    page: int
    per_page: int


# ── Scan Schemas ────────────────────────────────────────────────────


class ScanResultResponse(BaseModel):
    """
    Response schema for a scan result.

    Attributes:
        id: Unique identifier.
        competitor_id: Scanned competitor ID.
        competitor_name: Name of the scanned competitor (for display).
        new_products_count: New products discovered.
        removed_products_count: Products removed since last scan.
        price_changes_count: Products with price changes.
        scanned_at: When the scan was performed.
        duration_seconds: Scan duration in seconds.
    """

    id: uuid.UUID
    competitor_id: uuid.UUID
    competitor_name: str | None = None
    new_products_count: int
    removed_products_count: int
    price_changes_count: int
    scanned_at: datetime
    duration_seconds: float | None

    model_config = {"from_attributes": True}


class ScanResultListResponse(BaseModel):
    """
    Paginated list of scan results.

    Attributes:
        items: List of scan result records.
        total: Total number of results.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[ScanResultResponse]
    total: int
    page: int
    per_page: int


class ScanTriggerResponse(BaseModel):
    """
    Response after triggering a competitor scan.

    Attributes:
        message: Status message.
        scan_id: ID of the created scan result.
        competitor_id: ID of the competitor being scanned.
    """

    message: str
    scan_id: uuid.UUID
    competitor_id: uuid.UUID


# ── Source Match Schemas ────────────────────────────────────────────


class SourceMatchResponse(BaseModel):
    """
    Response schema for a source match.

    Attributes:
        id: Unique identifier.
        competitor_product_id: Matched product ID.
        supplier: Supplier name.
        supplier_url: Supplier product listing URL.
        cost: Supplier's cost for the product.
        currency: Cost currency code.
        confidence_score: Match confidence (0.0-1.0).
        margin_percent: Potential profit margin percentage.
        created_at: When the match was found.
    """

    id: uuid.UUID
    competitor_product_id: uuid.UUID
    supplier: str
    supplier_url: str
    cost: float | None
    currency: str
    confidence_score: float
    margin_percent: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceMatchListResponse(BaseModel):
    """
    Paginated list of source matches.

    Attributes:
        items: List of source match records.
        total: Total number of matches.
        page: Current page number.
        per_page: Number of items per page.
    """

    items: list[SourceMatchResponse]
    total: int
    page: int
    per_page: int


class SourceFindResponse(BaseModel):
    """
    Response after triggering source finding for a product.

    Attributes:
        message: Status message.
        product_id: ID of the product being sourced.
        matches_found: Number of source matches found.
        matches: List of source match records.
    """

    message: str
    product_id: uuid.UUID
    matches_found: int
    matches: list[SourceMatchResponse]
