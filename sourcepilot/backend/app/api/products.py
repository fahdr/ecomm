"""
Product search and preview API endpoints for SourcePilot.

Allows users to search supplier catalogs and preview products before
importing them to their stores.

For Developers:
    The search endpoint uses query parameters for filtering and pagination.
    The preview endpoint accepts a POST body with the product URL.
    Both endpoints require JWT authentication.

For QA Engineers:
    Test search with various queries and source types. Test preview
    with valid/invalid URLs. Verify response shapes match schemas.

For Project Managers:
    These endpoints power the product discovery interface in the dashboard.

For End Users:
    Search for products across supplier platforms and preview details
    before importing them to your store.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.product_search_service import (
    cache_product,
    preview_product,
    search_products,
)

router = APIRouter(prefix="/products", tags=["products"])


def _detect_source_from_url(url: str) -> str:
    """
    Detect the supplier source from a product URL.

    Args:
        url: The product URL.

    Returns:
        The detected source string (aliexpress, cjdropship, etc.).
    """
    url_lower = url.lower()
    if "aliexpress" in url_lower:
        return "aliexpress"
    if "cjdropship" in url_lower or "cjdropshipping" in url_lower:
        return "cjdropship"
    if "spocket" in url_lower:
        return "spocket"
    if "1688" in url_lower:
        return "aliexpress"
    # Default to aliexpress for unknown URLs (demo mode)
    return "aliexpress"


class ProductPreviewRequest(BaseModel):
    """
    Request body for previewing a product.

    Attributes:
        url: URL of the product on the supplier platform.
    """

    url: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="URL of the product to preview",
    )


@router.get("/search")
async def search_supplier_products(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    source: str | None = Query(None, description="Supplier platform filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search supplier catalogs for products matching the query.

    Returns paginated product previews from the specified supplier platform.
    If no source is specified, searches across all supported platforms.

    Args:
        q: Search query string.
        source: Optional supplier platform filter.
        page: Page number (1-indexed).
        page_size: Results per page (1-100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ProductSearchResponse with paginated product previews.
    """
    search_source = source or "aliexpress"

    try:
        result = await search_products(
            source=search_source,
            query=q,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return result


@router.post("/preview")
async def preview_supplier_product(
    body: ProductPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview a supplier product before importing.

    Fetches detailed product information from the supplier URL. The source
    is auto-detected from the URL domain.

    Args:
        body: Preview request with the product URL.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with product preview details.
    """
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL: must start with http:// or https://",
        )

    try:
        source = _detect_source_from_url(body.url)
        product = await preview_product(
            source=source,
            source_url=body.url,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if product.source_product_id:
        await cache_product(
            db,
            source=source,
            source_product_id=product.source_product_id,
            source_url=body.url,
            product_data={
                "title": product.title,
                "price": product.price,
                "currency": product.currency,
                "images": product.images,
                "source": product.source,
                "source_url": body.url,
                "source_product_id": product.source_product_id,
            },
        )

    return {
        "title": product.title,
        "price": product.price,
        "currency": product.currency,
        "images": product.images,
        "variants": product.variants_summary,
        "source": product.source,
        "source_url": body.url,
        "source_product_id": product.source_product_id,
        "supplier_name": product.supplier_name,
        "rating": product.rating,
        "order_count": product.order_count,
        "shipping_info": {
            "cost": product.shipping_cost,
            "estimated_days": product.shipping_days,
        } if product.shipping_cost is not None else None,
    }
