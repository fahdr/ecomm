"""
Product browsing API endpoints.

Provides cross-competitor product listing and individual product detail
with full price history.

For Developers:
    Products are accessed through two patterns:
    1. Per-competitor: GET /competitors/{id}/products (in competitors.py)
    2. Cross-competitor: GET /products (this file) — aggregates across all competitors

    The product detail endpoint includes the full price_history JSON array.

For QA Engineers:
    Test product listing with various filters (status, sort_by).
    Verify pagination works correctly. Check that product detail
    includes price history entries.

For Project Managers:
    The product feed gives users a unified view of all competitor
    products. Filtering and sorting help users find opportunities.

For End Users:
    Browse all products across your monitored competitors. Filter by
    status, sort by price or date, and view detailed price history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.competitor import (
    CompetitorProductListResponse,
    CompetitorProductResponse,
)
from app.services.competitor_service import get_product, list_all_products

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=CompetitorProductListResponse)
async def list_products_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (active, removed)"
    ),
    sort_by: str = Query(
        "last_seen",
        description="Sort by: last_seen, first_seen, price, title",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all products across all of the user's competitors.

    Supports filtering by product status and sorting by various fields.
    Products are enriched with their competitor's name for display.

    Args:
        page: Page number (1-based).
        per_page: Items per page (max 100).
        status_filter: Optional status filter ('active', 'removed').
        sort_by: Sort field ('last_seen', 'first_seen', 'price', 'title').
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorProductListResponse with paginated products.
    """
    products, total = await list_all_products(
        db,
        current_user.id,
        page=page,
        per_page=per_page,
        status_filter=status_filter,
        sort_by=sort_by,
    )

    # Enrich with competitor name
    items = []
    for p in products:
        resp = CompetitorProductResponse.model_validate(p)
        if p.competitor:
            resp.competitor_name = p.competitor.name
        items.append(resp)

    return CompetitorProductListResponse(
        items=items, total=total, page=page, per_page=per_page
    )


@router.get("/{product_id}", response_model=CompetitorProductResponse)
async def get_product_endpoint(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single product with full price history.

    Verifies the product belongs to one of the user's competitors
    before returning it.

    Args:
        product_id: The product's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CompetitorProductResponse with full price history.

    Raises:
        HTTPException 404: If the product is not found or not accessible.
    """
    import uuid

    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await get_product(db, current_user.id, pid)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    resp = CompetitorProductResponse.model_validate(product)
    if product.competitor:
        resp.competitor_name = product.competitor.name
    return resp
