"""
Pydantic schemas for product search and preview endpoints.

Defines request/response data structures for searching supplier catalogs
and previewing products before import.

For Developers:
    ProductSearchRequest supports pagination and filtering by source.
    ProductPreview is a lightweight summary for search result display.

For Project Managers:
    These schemas power the product discovery interface, allowing users
    to search supplier catalogs before importing.

For QA Engineers:
    Test search pagination, empty results, and invalid source types.
    Verify preview data matches the supplier product data.

For End Users:
    Search for products across supplier platforms and preview details
    before deciding to import.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ProductSearchRequest(BaseModel):
    """
    Request parameters for searching supplier product catalogs.

    Attributes:
        query: Search query string.
        source: Supplier platform to search.
        page: Page number (1-indexed).
        page_size: Number of results per page.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string",
    )
    source: str = Field(
        ...,
        description="Supplier platform to search: aliexpress, cjdropship, spocket",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of results per page",
    )


class ProductPreview(BaseModel):
    """
    Lightweight product summary for search results and previews.

    Attributes:
        title: Product title.
        price: Product price.
        currency: Price currency code.
        images: List of product image URLs.
        variants_summary: Summary of available variants (e.g., colors, sizes).
        source: Supplier platform.
        source_url: Product URL on the supplier.
        source_product_id: Product ID on the supplier.
        rating: Average product rating (0-5).
        order_count: Total orders/sales count.
        supplier_name: Name of the supplier/store.
        shipping_cost: Estimated shipping cost.
        shipping_days: Estimated delivery time in days.
    """

    title: str
    price: float
    currency: str = "USD"
    images: list[str] = Field(default_factory=list)
    variants_summary: list[dict[str, Any]] = Field(default_factory=list)
    source: str
    source_url: str | None = None
    source_product_id: str | None = None
    rating: float | None = None
    order_count: int | None = None
    supplier_name: str | None = None
    shipping_cost: float | None = None
    shipping_days: int | None = None


class ProductSearchResponse(BaseModel):
    """
    Paginated list of product search results.

    Attributes:
        products: List of product previews for the current page.
        total: Total number of products matching the query.
        page: Current page number.
        page_size: Number of results per page.
        source: Supplier platform that was searched.
    """

    products: list[ProductPreview]
    total: int
    page: int
    page_size: int
    source: str
