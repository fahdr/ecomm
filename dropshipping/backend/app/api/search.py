"""Search API router.

Provides public search endpoints for the storefront. Customers can search
products by keyword with filtering, sorting, and pagination. A suggestions
endpoint supports autocomplete functionality.

**For Developers:**
    The router is prefixed with ``/public/stores/{slug}/search`` (full path:
    ``/api/v1/public/stores/{slug}/search/...``). No authentication is required.
    Service functions in ``search_service`` handle query building and ranking.

**For QA Engineers:**
    - No authentication required (public endpoints).
    - Search supports ``query``, ``category_id``, ``min_price``, ``max_price``.
    - Sort options: ``relevance``, ``price_asc``, ``price_desc``,
      ``newest``, ``best_selling``.
    - Only active products from active stores are returned.
    - Suggestions return up to 10 autocomplete results.

**For End Users:**
    - Search for products across the store catalog.
    - Filter results by category and price range.
    - Sort results by relevance, price, or newest.
    - Get instant search suggestions as you type.
"""

import math
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.database import get_db
from app.schemas.search import SearchResponse

router = APIRouter(prefix="/public/stores/{slug}/search", tags=["search"])


# ---------------------------------------------------------------------------
# Suggestion schemas (not in app.schemas.search)
# ---------------------------------------------------------------------------


class SearchSuggestionResponse(BaseModel):
    """A single search suggestion for autocomplete.

    Attributes:
        text: The suggestion text.
        product_id: Optional product UUID for direct linking.
        product_slug: Optional product slug for URL building.
        category: Optional category name for context.
    """

    text: str
    product_id: Optional[uuid.UUID] = None
    product_slug: Optional[str] = None
    category: Optional[str] = None


class SearchSuggestionsResponse(BaseModel):
    """List of search suggestions.

    Attributes:
        suggestions: List of autocomplete suggestions.
        query: The partial query that generated these suggestions.
    """

    suggestions: list[SearchSuggestionResponse]
    query: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=SearchResponse)
async def search_products_endpoint(
    slug: str,
    query: Optional[str] = Query(None, description="Search query text"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category ID"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price filter"),
    sort_by: str = Query(
        "relevance",
        description="Sort order: relevance, price_asc, price_desc, newest, best_selling",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search products in a store (public).

    Full-text search across product titles and descriptions with optional
    filtering by category and price range. Results can be sorted by
    relevance, price, or recency.

    Args:
        slug: The store's URL slug.
        query: Optional search text. If omitted, returns all products.
        category_id: Optional category UUID to filter by.
        min_price: Optional minimum price filter.
        max_price: Optional maximum price filter.
        sort_by: Sort order (relevance, price_asc, price_desc, newest, best_selling).
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedSearchResponse with matching products and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or is not active.
        HTTPException 400: If sort_by value is invalid.
    """
    valid_sort_options = {
        "relevance",
        "price_asc",
        "price_desc",
        "newest",
        "best_selling",
    }
    if sort_by not in valid_sort_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Must be one of: {', '.join(sorted(valid_sort_options))}",
        )

    from app.models.store import Store, StoreStatus
    from app.services import search_service

    # Resolve store from slug
    store_result = await db.execute(
        select(Store).where(
            Store.slug == slug,
            Store.status == StoreStatus.active,
        )
    )
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    try:
        products, total, facets = await search_service.search_products(
            db,
            store_id=store.id,
            query=query or "",
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    from app.schemas.public import PublicProductResponse

    return SearchResponse(
        items=[PublicProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        query=query,
        facets=facets,
    )


@router.get("/suggest", response_model=SearchSuggestionsResponse)
async def search_suggestions_endpoint(
    slug: str,
    query: str = Query(..., min_length=1, description="Partial search query"),
    db: AsyncSession = Depends(get_db),
) -> SearchSuggestionsResponse:
    """Get search suggestions for autocomplete (public).

    Returns up to 10 product title suggestions matching the partial
    query. Used for real-time search-as-you-type functionality.

    Args:
        slug: The store's URL slug.
        query: The partial search text (minimum 1 character).
        db: Async database session injected by FastAPI.

    Returns:
        SearchSuggestionsResponse with a list of autocomplete suggestions.

    Raises:
        HTTPException 404: If the store is not found or is not active.
    """
    from app.models.store import Store, StoreStatus
    from app.services import search_service

    # Resolve store from slug
    store_result = await db.execute(
        select(Store).where(
            Store.slug == slug,
            Store.status == StoreStatus.active,
        )
    )
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    try:
        suggestion_titles = await search_service.get_search_suggestions(
            db, store_id=store.id, query=query, limit=10
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return SearchSuggestionsResponse(
        suggestions=[SearchSuggestionResponse(text=t) for t in suggestion_titles],
        query=query,
    )
