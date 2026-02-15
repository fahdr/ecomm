"""Pydantic schemas for product endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/products/*`` routes.

**For Developers:**
    ``CreateProductRequest`` and ``UpdateProductRequest`` are input schemas.
    ``ProductResponse`` and ``VariantResponse`` use ``from_attributes`` to
    serialize ORM instances. Pagination is handled via ``PaginatedProductResponse``.

**For QA Engineers:**
    - ``CreateProductRequest.title`` is required, 1–500 characters.
    - ``CreateProductRequest.price`` must be >= 0.
    - ``UpdateProductRequest`` is fully optional (partial updates via PATCH).
    - ``ProductResponse`` includes nested variants.
    - Pagination defaults to page=1, per_page=20.

**For End Users:**
    When adding a product, provide a title and price at minimum. You can
    add images, variants, and SEO metadata to enhance your product listing.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.product import ProductStatus


class VariantRequest(BaseModel):
    """Schema for creating or updating a product variant.

    Attributes:
        name: Display name of the variant (e.g. "Large", "Blue").
        sku: Optional stock-keeping unit identifier.
        price: Optional price override; if null, uses the product's base price.
        inventory_count: Number of units in stock (defaults to 0).
    """

    name: str = Field(..., min_length=1, max_length=255, description="Variant name")
    sku: str | None = Field(None, max_length=100, description="SKU identifier")
    price: Decimal | None = Field(None, ge=0, description="Price override")
    inventory_count: int = Field(0, ge=0, description="Units in stock")


class VariantResponse(BaseModel):
    """Schema for returning variant data in API responses.

    Attributes:
        id: The variant's unique identifier.
        product_id: The parent product's UUID.
        name: Display name of the variant.
        sku: Stock-keeping unit identifier (may be null).
        price: Price override (may be null, meaning use product base price).
        inventory_count: Number of units in stock.
        created_at: When the variant was created.
        updated_at: When the variant was last modified.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    product_id: uuid.UUID
    name: str
    sku: str | None
    price: Decimal | None
    inventory_count: int
    created_at: datetime
    updated_at: datetime


class CreateProductRequest(BaseModel):
    """Schema for creating a new product.

    Attributes:
        title: Display title of the product (1–500 characters).
        description: Optional longer description.
        price: Selling price (>= 0).
        compare_at_price: Optional "was" price for showing discounts.
        cost: Optional supplier cost (private).
        images: Optional list of image URL strings.
        status: Product status (defaults to draft).
        seo_title: Optional custom SEO title.
        seo_description: Optional custom SEO meta description.
        variants: Optional list of variants to create with the product.
    """

    title: str = Field(..., min_length=1, max_length=500, description="Product title")
    description: str | None = Field(None, description="Product description")
    price: Decimal = Field(..., ge=0, description="Selling price")
    compare_at_price: Decimal | None = Field(None, ge=0, description="Compare-at price")
    cost: Decimal | None = Field(None, ge=0, description="Supplier cost")
    images: list[str] | None = Field(None, description="Image URLs")
    status: ProductStatus = Field(ProductStatus.draft, description="Product status")
    seo_title: str | None = Field(None, max_length=255, description="SEO title")
    seo_description: str | None = Field(None, description="SEO meta description")
    variants: list[VariantRequest] | None = Field(None, description="Product variants")


class UpdateProductRequest(BaseModel):
    """Schema for updating an existing product (partial update).

    All fields are optional — only provided fields will be updated.

    Attributes:
        title: New display title (1–500 characters).
        description: New description.
        price: New selling price (>= 0).
        compare_at_price: New compare-at price.
        cost: New supplier cost.
        images: New list of image URLs.
        status: New product status.
        seo_title: New SEO title.
        seo_description: New SEO meta description.
        variants: New list of variants (replaces existing variants).
    """

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    compare_at_price: Decimal | None = Field(None, ge=0)
    cost: Decimal | None = Field(None, ge=0)
    images: list[str] | None = None
    status: ProductStatus | None = None
    seo_title: str | None = Field(None, max_length=255)
    seo_description: str | None = None
    variants: list[VariantRequest] | None = None


class ProductResponse(BaseModel):
    """Schema for returning product data in API responses.

    Attributes:
        id: The product's unique identifier.
        store_id: The parent store's UUID.
        title: Display title of the product.
        slug: URL-friendly unique slug (within the store).
        description: Product description (may be null).
        price: Selling price.
        compare_at_price: Compare-at price (may be null).
        cost: Supplier cost (may be null).
        images: List of image URL strings.
        status: Current product status.
        seo_title: SEO title (may be null).
        seo_description: SEO meta description (may be null).
        created_at: When the product was created.
        updated_at: When the product was last modified.
        variants: List of product variants.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    title: str
    slug: str
    description: str | None
    price: Decimal
    compare_at_price: Decimal | None
    cost: Decimal | None
    images: list[str] | None
    status: ProductStatus
    seo_title: str | None
    seo_description: str | None
    created_at: datetime
    updated_at: datetime
    variants: list[VariantResponse] = []


class PaginatedProductResponse(BaseModel):
    """Schema for paginated product list responses.

    Attributes:
        items: List of products on this page.
        total: Total number of products matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[ProductResponse]
    total: int
    page: int
    per_page: int
    pages: int
