"""Pydantic schemas for product search endpoints (Feature 17).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/public/stores/{slug}/search`` route.

**For Developers:**
    ``SearchRequest`` captures the full-text query along with optional
    filters and pagination. ``SearchResponse`` wraps
    ``PublicProductResponse`` items with facet data for filtering UIs.

**For QA Engineers:**
    - ``SearchRequest.query`` is required, minimum 1 character.
    - ``SearchRequest.sort_by`` accepts ``"relevance"``, ``"price_asc"``,
      ``"price_desc"``, ``"newest"``, ``"best_selling"``.
    - ``SearchResponse.facets`` may include category counts, price ranges,
      etc. depending on implementation.
    - Defaults: ``page=1``, ``per_page=20``.

**For Project Managers:**
    Search is a critical storefront feature. Customers need to find
    products quickly with filtering by category and price range. Faceted
    search enables dynamic filter UIs.

**For End Users:**
    Search for products by typing keywords. Filter results by category,
    price range, and sort by relevance, price, or newest arrivals.
"""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.public import PublicProductResponse


class SearchRequest(BaseModel):
    """Schema for a product search query with filters.

    Attributes:
        query: Full-text search query string.
        category_id: Optional category UUID to filter results.
        min_price: Optional minimum price filter.
        max_price: Optional maximum price filter.
        sort_by: Sort order for results. Defaults to ``"relevance"``.
            Options: ``"relevance"``, ``"price_asc"``, ``"price_desc"``,
            ``"newest"``, ``"best_selling"``.
        page: Page number (1-based). Defaults to 1.
        per_page: Number of results per page. Defaults to 20.
    """

    query: str = Field(
        ..., min_length=1, max_length=500, description="Search query"
    )
    category_id: uuid.UUID | None = Field(
        None, description="Filter by category UUID"
    )
    min_price: Decimal | None = Field(
        None, ge=0, description="Minimum price filter"
    )
    max_price: Decimal | None = Field(
        None, ge=0, description="Maximum price filter"
    )
    sort_by: str = Field(
        "relevance",
        description='Sort order: "relevance", "price_asc", "price_desc", "newest", "best_selling"',
    )
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(
        20, ge=1, le=100, description="Results per page"
    )


class SearchResponse(BaseModel):
    """Schema for paginated product search results.

    Attributes:
        items: List of matching products on this page.
        total: Total number of products matching the query.
        query: The original search query string.
        page: Current page number (1-based).
        per_page: Number of results per page.
        pages: Total number of pages.
        facets: Optional facet data for building filter UIs (e.g.
            category counts, price range bounds). Structure depends
            on implementation.
    """

    items: list[PublicProductResponse]
    total: int
    query: str | None = None
    page: int
    per_page: int
    pages: int
    facets: dict | None = None
