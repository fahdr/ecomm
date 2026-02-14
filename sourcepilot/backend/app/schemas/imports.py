"""
Pydantic schemas for import job endpoints.

Defines request/response data structures for creating, listing, previewing,
and managing product import jobs.

For Developers:
    - Create schemas validate user input with constraints.
    - Response schemas use ``from_attributes = True`` for ORM-to-Pydantic mapping.
    - Paginated responses follow the standard envelope:
      { "items": [...], "total": N, "page": 1, "per_page": 20 }

For Project Managers:
    These schemas define the API contract for all import-related endpoints.
    Changes here affect both the backend validation and the dashboard integration.

For QA Engineers:
    Test validation by sending invalid payloads (missing product_url, invalid
    source types, negative page numbers). Verify response shapes match schemas.

For End Users:
    These data structures describe the information you send when importing
    products and the format of the status updates you receive back.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Import Job Schemas ─────────────────────────────────────────────


class ImportJobCreate(BaseModel):
    """
    Request body for creating a new import job.

    Attributes:
        product_url: URL of the product on the supplier platform.
        source: Supplier platform identifier.
        store_id: Optional UUID of the target store connection.
        config: Optional import settings (markup_percent, tags, compare_at_discount).
    """

    product_url: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="URL of the product on the supplier platform",
    )
    source: str = Field(
        ...,
        description="Supplier platform: aliexpress, cjdropship, spocket, manual",
    )
    store_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the target store connection (optional, uses default store)",
    )
    config: dict | None = Field(
        default=None,
        description="Import settings: markup_percent, tags, compare_at_discount, etc.",
    )


class ImportJobResponse(BaseModel):
    """
    Response schema for a single import job.

    Attributes:
        id: Import job unique identifier.
        user_id: Owning user identifier.
        store_id: Target store connection identifier.
        source: Supplier platform.
        product_url: Product URL on the supplier (mapped from source_url).
        source_product_id: Product ID on the supplier.
        status: Current job status.
        product_data: Raw supplier product data.
        config: Import configuration.
        error_message: Error description if failed.
        created_product_id: UUID of the created store product.
        progress_percent: Import progress (0-100).
        created_at: Job creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    store_id: uuid.UUID | None = None
    source: str
    product_url: str | None = Field(default=None, validation_alias="source_url")
    source_product_id: str | None = None
    status: str
    product_data: dict | None = None
    config: dict | None = None
    error_message: str | None = None
    created_product_id: uuid.UUID | None = None
    progress_percent: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ImportJobList(BaseModel):
    """
    Paginated list of import jobs.

    Attributes:
        items: List of import jobs for the current page.
        total: Total number of jobs matching the query.
        page: Current page number (1-indexed).
        per_page: Number of items per page.
    """

    items: list[ImportJobResponse]
    total: int
    page: int
    per_page: int


class BulkImportCreate(BaseModel):
    """
    Request body for creating multiple import jobs at once.

    Attributes:
        product_urls: List of product URLs to import.
        source: Supplier platform identifier (same for all URLs).
        store_id: Optional UUID of the target store connection.
        config: Optional import settings applied to all jobs.
    """

    product_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of product URLs to import (max 50)",
    )
    source: str = Field(
        ...,
        description="Supplier platform: aliexpress, cjdropship, spocket, manual",
    )
    store_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the target store connection (optional)",
    )
    config: dict | None = Field(
        default=None,
        description="Import settings applied to all jobs",
    )


class ImportPreviewRequest(BaseModel):
    """
    Request body for previewing a product before importing.

    Attributes:
        source_url: URL of the product on the supplier platform.
        source: Supplier platform identifier.
    """

    source_url: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="URL of the product to preview",
    )
    source: str = Field(
        ...,
        description="Supplier platform: aliexpress, cjdropship, spocket",
    )


class ImportPreviewResponse(BaseModel):
    """
    Response schema for a product preview before importing.

    Attributes:
        title: Product title from the supplier.
        description: Product description (may be truncated).
        price: Product price on the supplier platform.
        currency: Price currency code.
        images: List of product image URLs.
        variants: Summary of available product variants.
        supplier_name: Name of the supplier/store.
        shipping_info: Shipping cost and estimated delivery time.
        source: Supplier platform identifier.
        source_url: Original product URL.
        source_product_id: Product ID on the supplier platform.
        raw_data: Complete product data from the supplier.
    """

    title: str
    description: str | None = None
    price: float
    currency: str = "USD"
    images: list[str] = Field(default_factory=list)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    supplier_name: str | None = None
    shipping_info: dict | None = None
    source: str
    source_url: str
    source_product_id: str | None = None
    raw_data: dict | None = None
