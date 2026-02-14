"""
Pydantic models for normalized supplier product data.

For Developers:
    These models provide a common, supplier-agnostic representation of
    products, variants, shipping info, and ratings. All supplier clients
    must normalize their API responses into these models.

For QA Engineers:
    Validation is enforced at the Pydantic level: prices use ``Decimal``,
    required fields raise ``ValidationError`` if missing, and ``fetched_at``
    defaults to the current UTC time.

For End Users:
    These models define the product information imported from external
    suppliers (AliExpress, CJDropship, etc.) into your store catalog.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SupplierVariant(BaseModel):
    """
    A single variant of a supplier product (e.g. color/size combination).

    For Developers:
        Each variant maps to a distinct purchasable SKU on the supplier
        platform. The ``attributes`` dict holds structured key-value pairs
        for faceted filtering.

    Attributes:
        name: Human-readable variant label, e.g. "Color: Red, Size: L".
        sku: Stock-keeping unit identifier on the supplier platform, if available.
        price: Variant price in the product's currency.
        stock: Number of units in stock, or None if stock is unknown.
        image_url: URL to a variant-specific image, or None.
        attributes: Structured variant attributes, e.g. {"color": "Red", "size": "L"}.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    sku: str | None = None
    price: Decimal
    stock: int | None = None
    image_url: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class ShippingInfo(BaseModel):
    """
    Estimated shipping details for a supplier product.

    For Developers:
        Shipping info is optional on ``SupplierProduct`` because not all
        supplier APIs expose shipping estimates at the product level.

    Attributes:
        estimated_days_min: Minimum estimated delivery days.
        estimated_days_max: Maximum estimated delivery days.
        shipping_cost: Shipping cost in USD (Decimal for precision).
        shipping_method: Shipping method name, e.g. "ePacket", "AliExpress Standard".
        ships_from: Origin country or warehouse, e.g. "CN", "US".
    """

    model_config = ConfigDict(frozen=True)

    estimated_days_min: int
    estimated_days_max: int
    shipping_cost: Decimal
    shipping_method: str
    ships_from: str


class SupplierRating(BaseModel):
    """
    Aggregated customer rating for a supplier product.

    For Developers:
        Ratings are optional on ``SupplierProduct`` because not all
        supplier APIs expose rating data.

    Attributes:
        average: Average star rating (typically 0.0 to 5.0).
        count: Total number of ratings/reviews.
        positive_percent: Percentage of positive reviews, or None if unavailable.
    """

    model_config = ConfigDict(frozen=True)

    average: float
    count: int
    positive_percent: float | None = None


class SupplierProduct(BaseModel):
    """
    Normalized representation of a product from an external supplier.

    For Developers:
        This is the canonical model that all supplier clients must produce.
        The ``raw_data`` field preserves the original API response for
        debugging and for fields not yet mapped to the common schema.

    For QA Engineers:
        Verify that ``source`` matches the supplier client that produced
        the product, and that ``price`` is a valid non-negative Decimal.

    Attributes:
        source: Supplier platform identifier, e.g. "aliexpress", "cjdropship", "spocket".
        source_id: Product ID on the supplier platform.
        source_url: Direct URL to the product on the supplier's website.
        title: Product title / name.
        description: Full product description (may contain HTML).
        price: Supplier cost in USD as a Decimal.
        currency: ISO 4217 currency code (default "USD").
        images: List of product image URLs.
        variants: List of product variants (color, size, etc.).
        shipping_info: Estimated shipping details, or None if unavailable.
        ratings: Aggregated customer ratings, or None if unavailable.
        raw_data: Original unmodified payload from the supplier API.
        fetched_at: UTC timestamp of when the data was retrieved.
    """

    model_config = ConfigDict(frozen=True)

    source: str
    source_id: str
    source_url: str
    title: str
    description: str
    price: Decimal
    currency: str = "USD"
    images: list[str] = Field(default_factory=list)
    variants: list[SupplierVariant] = Field(default_factory=list)
    shipping_info: ShippingInfo | None = None
    ratings: SupplierRating | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductSearchResult(BaseModel):
    """
    Paginated search result from a supplier product query.

    For Developers:
        Returned by ``BaseSupplierClient.search_products()``. Use
        ``page`` and ``page_size`` to implement pagination in the UI.

    Attributes:
        products: List of matching supplier products for the current page.
        total_count: Total number of matching products across all pages.
        page: Current page number (1-indexed).
        page_size: Number of products per page.
    """

    products: list[SupplierProduct] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 20
