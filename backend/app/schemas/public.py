"""Pydantic schemas for public (unauthenticated) API endpoints.

These schemas shape the responses returned by the public-facing storefront
API. They intentionally omit sensitive fields like ``user_id`` and ``cost``
that should not be exposed to anonymous visitors.

**For Developers:**
    ``PublicStoreResponse`` is the serialisation shape for
    ``GET /api/v1/public/stores/{slug}``. It uses ``from_attributes`` for
    direct ORM-to-schema conversion. ``PublicProductResponse`` and
    ``PublicVariantResponse`` are used for public product endpoints.

**For QA Engineers:**
    - ``PublicStoreResponse`` must never include ``user_id``.
    - ``PublicProductResponse`` must never include ``cost`` or ``store_id``.
    - Only active stores/products should be returned by public endpoints.

**For End Users:**
    These are the data shapes you receive when browsing a store on the
    public storefront.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PublicStoreResponse(BaseModel):
    """Public-facing store data returned to storefront visitors.

    Attributes:
        id: The store's unique identifier.
        name: Display name of the store.
        slug: URL-friendly unique slug used in the storefront URL.
        niche: The product niche or category.
        description: Optional longer description of the store.
        created_at: When the store was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    niche: str
    description: str | None
    created_at: datetime


class PublicVariantResponse(BaseModel):
    """Public-facing variant data (excludes internal fields).

    Attributes:
        id: The variant's unique identifier.
        name: Display name of the variant.
        sku: Stock-keeping unit identifier (may be null).
        price: Price override (may be null).
        inventory_count: Units in stock.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    sku: str | None
    price: Decimal | None
    inventory_count: int


class PublicProductResponse(BaseModel):
    """Public-facing product data (excludes cost and store_id).

    Attributes:
        id: The product's unique identifier.
        title: Display title of the product.
        slug: URL-friendly slug (unique within the store).
        description: Product description (may be null).
        price: Selling price.
        compare_at_price: Compare-at price (may be null).
        images: List of image URL strings.
        seo_title: SEO title (may be null).
        seo_description: SEO meta description (may be null).
        created_at: When the product was created.
        variants: List of product variants.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    slug: str
    description: str | None
    price: Decimal
    compare_at_price: Decimal | None
    images: list[str] | None
    seo_title: str | None
    seo_description: str | None
    created_at: datetime
    variants: list[PublicVariantResponse] = []


class PaginatedPublicProductResponse(BaseModel):
    """Schema for paginated public product list responses.

    Attributes:
        items: List of products on this page.
        total: Total number of products matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[PublicProductResponse]
    total: int
    page: int
    per_page: int
    pages: int
