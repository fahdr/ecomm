"""Pydantic schemas for product category endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/categories/*`` routes.

**For Developers:**
    ``CreateCategoryRequest`` and ``UpdateCategoryRequest`` are input schemas.
    ``CategoryResponse`` uses ``from_attributes`` and supports recursive
    ``children`` for tree rendering. ``AssignProductCategoryRequest`` links
    products to categories.

**For QA Engineers:**
    - ``CreateCategoryRequest.name`` is required, 1-255 characters.
    - ``parent_id`` enables nested categories (one level deep or more).
    - ``position`` controls sort order; defaults to 0.
    - ``CategoryResponse.product_count`` is optional and populated only
      when the endpoint includes an aggregate query.

**For Project Managers:**
    Categories organise the product catalogue into a navigable hierarchy.
    They appear in storefront navigation menus and can be targeted by
    discount codes.

**For End Users:**
    Browse products by category on the storefront. Store owners arrange
    categories in a tree structure and assign products to them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateCategoryRequest(BaseModel):
    """Schema for creating a new product category.

    Attributes:
        name: Display name of the category (1-255 characters).
        description: Optional longer description shown on the category page.
        image_url: Optional hero/banner image URL for the category.
        parent_id: Optional UUID of the parent category to nest under.
        position: Sort-order position within the parent (defaults to 0).
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Category name"
    )
    description: str | None = Field(
        None, max_length=1000, description="Category description"
    )
    image_url: str | None = Field(
        None, max_length=2048, description="Category image URL"
    )
    parent_id: uuid.UUID | None = Field(
        None, description="Parent category UUID for nesting"
    )
    position: int = Field(
        0, ge=0, description="Sort-order position"
    )


class UpdateCategoryRequest(BaseModel):
    """Schema for updating an existing category (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        name: New category name (1-255 characters).
        description: New description.
        image_url: New image URL.
        parent_id: New parent category UUID.
        position: New sort-order position.
        is_active: Whether the category is visible on the storefront.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    image_url: str | None = Field(None, max_length=2048)
    parent_id: uuid.UUID | None = None
    position: int | None = Field(None, ge=0)
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    """Schema for returning category data in API responses.

    Supports recursive ``children`` for tree rendering.

    Attributes:
        id: The category's unique identifier.
        store_id: The parent store's UUID.
        name: Display name of the category.
        slug: URL-friendly unique slug (within the store).
        description: Category description (may be null).
        image_url: Hero/banner image URL (may be null).
        parent_id: Parent category UUID (may be null for root categories).
        position: Sort-order position.
        is_active: Whether the category is visible on the storefront.
        product_count: Number of products in this category (populated on
            list endpoints; may be null on detail endpoints).
        created_at: When the category was created.
        updated_at: When the category was last modified.
        children: Nested child categories (populated on tree endpoints).
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    parent_id: uuid.UUID | None
    position: int
    is_active: bool
    product_count: int | None = None
    created_at: datetime
    updated_at: datetime
    children: list[CategoryResponse] | None = None


class PaginatedCategoryResponse(BaseModel):
    """Schema for paginated category list responses.

    Attributes:
        items: List of categories on this page.
        total: Total number of categories matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[CategoryResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AssignProductCategoryRequest(BaseModel):
    """Schema for assigning a product to one or more categories.

    Attributes:
        category_ids: List of category UUIDs to assign the product to.
            Replaces any existing category assignments for the product.
    """

    category_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Category UUIDs to assign"
    )
