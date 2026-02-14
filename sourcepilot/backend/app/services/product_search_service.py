"""
Product search service for querying supplier catalogs and caching results.

Provides product search, preview, and caching functionality. In production,
search calls would hit real supplier APIs; currently uses mock data generators
for development and testing.

For Developers:
    The cache layer (``get_cached_product`` / ``cache_product``) reduces
    redundant supplier API calls. Cache TTL is 24 hours by default.
    Mock data generators use deterministic seeding for reproducible results.

For Project Managers:
    This service powers the product discovery interface. Users can search
    supplier catalogs and preview products before importing.

For QA Engineers:
    Test search with various query strings and source types. Verify
    cache hit/miss behavior. Test pagination boundaries.

For End Users:
    Search for products across supplier platforms and preview details
    before deciding to import them to your store.
"""

import hashlib
import logging
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportSource
from app.models.product_cache import ProductCache
from app.schemas.products import ProductPreview, ProductSearchResponse

logger = logging.getLogger(__name__)

# Default cache TTL in hours
CACHE_TTL_HOURS = 24


async def search_products(
    source: str,
    query: str,
    page: int = 1,
    page_size: int = 20,
) -> ProductSearchResponse:
    """
    Search supplier catalogs for products matching the query.

    Currently uses mock data generators. In production, this would
    call the actual supplier API (AliExpress, CJ Dropship, Spocket).

    Args:
        source: Supplier platform to search.
        query: Search query string.
        page: Page number (1-indexed).
        page_size: Results per page.

    Returns:
        ProductSearchResponse with paginated product previews.

    Raises:
        ValueError: If the source is not a valid supplier platform.
    """
    valid_sources = {s.value for s in ImportSource}
    if source not in valid_sources:
        raise ValueError(
            f"Invalid source '{source}'. Valid sources: {', '.join(sorted(valid_sources))}"
        )

    # Generate mock products based on source and query
    all_products = _generate_mock_search_results(source, query)

    # Apply pagination
    total = len(all_products)
    start = (page - 1) * page_size
    end = start + page_size
    page_products = all_products[start:end]

    return ProductSearchResponse(
        products=page_products,
        total=total,
        page=page,
        page_size=page_size,
        source=source,
    )


async def preview_product(
    source: str,
    source_url: str,
) -> ProductPreview:
    """
    Fetch and return a detailed product preview from a supplier URL.

    Currently returns mock data based on the URL. In production, this
    would scrape or API-fetch the actual product page.

    Args:
        source: Supplier platform identifier.
        source_url: Full URL of the product on the supplier platform.

    Returns:
        ProductPreview with product details.

    Raises:
        ValueError: If the source is not a valid supplier platform.
    """
    valid_sources = {s.value for s in ImportSource}
    if source not in valid_sources:
        raise ValueError(
            f"Invalid source '{source}'. Valid sources: {', '.join(sorted(valid_sources))}"
        )

    # Generate deterministic mock preview from URL
    seed = int(hashlib.md5(source_url.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    title = f"Product from {source.title()} - {source_url.split('/')[-1][:20]}"
    price = round(rng.uniform(5.99, 149.99), 2)

    return ProductPreview(
        title=title,
        price=price,
        currency="USD",
        images=[
            f"https://{source}-cdn.example.com/img/{rng.randint(1000, 9999)}.jpg"
            for _ in range(rng.randint(2, 6))
        ],
        variants_summary=[
            {"name": "Color", "options": ["Black", "White", "Blue"]},
            {"name": "Size", "options": ["S", "M", "L", "XL"]},
        ],
        source=source,
        source_url=source_url,
        source_product_id=str(rng.randint(100000, 999999)),
        rating=round(rng.uniform(3.5, 5.0), 1),
        order_count=rng.randint(50, 15000),
        supplier_name=f"{source.title()} Supplier #{rng.randint(100, 999)}",
        shipping_cost=round(rng.uniform(0, 9.99), 2),
        shipping_days=rng.randint(3, 30),
    )


async def get_cached_product(
    db: AsyncSession,
    source: str,
    source_product_id: str,
) -> ProductCache | None:
    """
    Retrieve a cached product entry if it exists and is not expired.

    Args:
        db: Async database session.
        source: Supplier platform identifier.
        source_product_id: Product ID on the supplier platform.

    Returns:
        The ProductCache if found and valid, None if missing or expired.
    """
    now = datetime.now(UTC)
    result = await db.execute(
        select(ProductCache).where(
            ProductCache.source == ImportSource(source),
            ProductCache.source_product_id == source_product_id,
            ProductCache.expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def cache_product(
    db: AsyncSession,
    source: str,
    source_product_id: str,
    source_url: str | None,
    product_data: dict,
) -> ProductCache:
    """
    Create or update a product cache entry.

    If a cache entry already exists for this source + product_id, it is
    replaced with the new data and a fresh expiration time.

    Args:
        db: Async database session.
        source: Supplier platform identifier.
        source_product_id: Product ID on the supplier platform.
        source_url: Product URL on the supplier platform.
        product_data: Full product data to cache.

    Returns:
        The created or updated ProductCache entry.
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=CACHE_TTL_HOURS)

    # Check for existing entry
    existing = await db.execute(
        select(ProductCache).where(
            ProductCache.source == ImportSource(source),
            ProductCache.source_product_id == source_product_id,
        )
    )
    cache_entry = existing.scalar_one_or_none()

    if cache_entry:
        cache_entry.product_data = product_data
        cache_entry.source_url = source_url
        cache_entry.expires_at = expires_at
    else:
        cache_entry = ProductCache(
            source=ImportSource(source),
            source_product_id=source_product_id,
            source_url=source_url,
            product_data=product_data,
            expires_at=expires_at,
        )
        db.add(cache_entry)

    await db.flush()
    await db.refresh(cache_entry)
    return cache_entry


def _generate_mock_search_results(
    source: str,
    query: str,
) -> list[ProductPreview]:
    """
    Generate deterministic mock search results for a supplier query.

    Uses a seeded random number generator for reproducible results
    across identical queries.

    Args:
        source: Supplier platform identifier.
        query: Search query string.

    Returns:
        List of ProductPreview objects (typically 15-30 items).
    """
    seed_str = f"{source}_{query}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    count = rng.randint(15, 30)
    products = []

    templates = {
        "aliexpress": [
            "{q} Premium Quality - Free Shipping",
            "{q} Hot Sale 2024 New Arrival",
            "{q} Wholesale Price - Fast Delivery",
            "{q} Pro Version - Top Rated",
            "{q} Budget Friendly - Best Seller",
        ],
        "cjdropship": [
            "CJ {q} - Dropship Ready",
            "{q} with Fast US Warehouse Shipping",
            "{q} Custom Branding Available",
            "Premium {q} - CJ Exclusive",
            "{q} Bundle Pack - High Margin",
        ],
        "spocket": [
            "{q} - US/EU Supplier",
            "{q} Premium from Verified Supplier",
            "Handcrafted {q} - Small Batch",
            "{q} Fast Shipping - Spocket Verified",
            "{q} Eco-Friendly - Trending Now",
        ],
        "manual": [
            "{q} Custom Product",
            "{q} Private Label Option",
            "{q} Direct From Manufacturer",
            "{q} Custom Specification",
            "{q} OEM/ODM Available",
        ],
    }

    source_templates = templates.get(source, templates["manual"])

    for i in range(count):
        template = source_templates[i % len(source_templates)]
        title = template.format(q=query.title())
        price = round(rng.uniform(2.99, 199.99), 2)
        product_id = str(rng.randint(100000, 999999))

        products.append(ProductPreview(
            title=title,
            price=price,
            currency="USD",
            images=[
                f"https://{source}-cdn.example.com/img/{rng.randint(1000, 9999)}.jpg"
                for _ in range(rng.randint(1, 4))
            ],
            variants_summary=[],
            source=source,
            source_url=f"https://{source}.example.com/product/{product_id}",
            source_product_id=product_id,
            rating=round(rng.uniform(3.0, 5.0), 1),
            order_count=rng.randint(10, 20000),
            supplier_name=f"{source.title()} Store #{rng.randint(100, 999)}",
            shipping_cost=round(rng.uniform(0, 12.99), 2),
            shipping_days=rng.randint(3, 35),
        ))

    return products
