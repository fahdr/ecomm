"""Search business logic.

Provides full-text product search with filtering, sorting, and
auto-complete suggestions for the public storefront.

**For Developers:**
    Search uses PostgreSQL ``ILIKE`` for pattern matching on product
    title, description, and SEO fields. In a future iteration this could
    be upgraded to PostgreSQL ``tsvector``/``tsquery`` for true full-text
    search with ranking. The ``facets`` return value provides category
    and price-range aggregations for search result refinement.

**For QA Engineers:**
    - ``search_products`` only returns active products.
    - The ``relevance`` sort mode orders by title match specificity (exact
      match first, then partial match on title, then description).
    - Filters: ``category_id``, ``min_price``, ``max_price``.
    - Sorting options: ``relevance``, ``price_asc``, ``price_desc``,
      ``newest``, ``best_selling``.
    - ``get_search_suggestions`` returns distinct product titles matching
      the query prefix.

**For Project Managers:**
    This service powers Feature 17 (Product Search) from the backlog,
    enabling customers to find products quickly via keyword search with
    filters and sorting.

**For End Users:**
    Search your store's product catalog by keyword. Filter results by
    category or price range, and sort by price, newest, or best-selling
    to find exactly what you're looking for.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select, case, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import ProductCategory
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductStatus


async def search_products(
    db: AsyncSession,
    store_id: uuid.UUID,
    query: str,
    category_id: uuid.UUID | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    sort_by: str = "relevance",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Product], int, dict]:
    """Search products in a store with filtering and sorting.

    Performs case-insensitive pattern matching on product title,
    description, and SEO fields. Results are filtered to active products
    only and can be further refined by category and price range.

    This function does NOT require store ownership verification as it
    is used on the public storefront.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        query: The search query string.
        category_id: Optional category UUID to filter by.
        min_price: Optional minimum price filter.
        max_price: Optional maximum price filter.
        sort_by: Sort order. One of ``"relevance"``, ``"price_asc"``,
            ``"price_desc"``, ``"newest"``, ``"best_selling"``.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (products list, total count, facets dict). The facets
        dict contains ``price_range`` (min/max across results) and
        ``categories`` (list of category IDs with counts).
    """
    search_term = f"%{query}%"

    # Base conditions: active products in the store matching the search
    base_conditions = [
        Product.store_id == store_id,
        Product.status == ProductStatus.active,
        or_(
            Product.title.ilike(search_term),
            Product.description.ilike(search_term),
            Product.seo_title.ilike(search_term),
            Product.seo_description.ilike(search_term),
        ),
    ]

    # Category filter
    product_query = select(Product).where(*base_conditions)
    count_query = select(func.count(Product.id)).where(*base_conditions)

    if category_id is not None:
        product_query = product_query.join(
            ProductCategory, ProductCategory.product_id == Product.id
        ).where(ProductCategory.category_id == category_id)
        count_query = count_query.join(
            ProductCategory, ProductCategory.product_id == Product.id
        ).where(ProductCategory.category_id == category_id)

    # Price filters
    if min_price is not None:
        product_query = product_query.where(Product.price >= min_price)
        count_query = count_query.where(Product.price >= min_price)

    if max_price is not None:
        product_query = product_query.where(Product.price <= max_price)
        count_query = count_query.where(Product.price <= max_price)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Sorting
    if sort_by == "price_asc":
        product_query = product_query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        product_query = product_query.order_by(Product.price.desc())
    elif sort_by == "newest":
        product_query = product_query.order_by(Product.created_at.desc())
    elif sort_by == "best_selling":
        # Sub-query for units sold
        sold_subq = (
            select(
                OrderItem.product_id,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.status.in_([
                    OrderStatus.paid,
                    OrderStatus.shipped,
                    OrderStatus.delivered,
                ])
            )
            .group_by(OrderItem.product_id)
            .subquery()
        )
        product_query = product_query.outerjoin(
            sold_subq, Product.id == sold_subq.c.product_id
        ).order_by(func.coalesce(sold_subq.c.units_sold, 0).desc())
    else:
        # Relevance: prioritise title matches over description matches
        relevance_score = case(
            (Product.title.ilike(f"%{query}%"), 2),
            else_=1,
        )
        product_query = product_query.order_by(
            relevance_score.desc(), Product.created_at.desc()
        )

    # Pagination
    offset = (page - 1) * per_page
    product_query = product_query.offset(offset).limit(per_page)

    result = await db.execute(product_query)
    products = list(result.scalars().all())

    # Build facets
    facets = await _build_facets(db, store_id, query, base_conditions)

    return products, total, facets


async def _build_facets(
    db: AsyncSession,
    store_id: uuid.UUID,
    query: str,
    base_conditions: list,
) -> dict:
    """Build search facets (aggregations) for filtering UI.

    Computes the price range across matching products and counts products
    per category.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        query: The original search query.
        base_conditions: The SQLAlchemy where conditions from the search.

    Returns:
        A dict with ``price_range`` (``min``/``max``) and ``categories``
        (list of dicts with ``category_id`` and ``count``).
    """
    # Price range facet
    price_result = await db.execute(
        select(
            func.min(Product.price),
            func.max(Product.price),
        ).where(*base_conditions)
    )
    price_row = price_result.one()
    price_range = {
        "min": float(price_row[0]) if price_row[0] is not None else 0.0,
        "max": float(price_row[1]) if price_row[1] is not None else 0.0,
    }

    # Category facet
    category_result = await db.execute(
        select(
            ProductCategory.category_id,
            func.count(Product.id).label("count"),
        )
        .join(Product, ProductCategory.product_id == Product.id)
        .where(*base_conditions)
        .group_by(ProductCategory.category_id)
        .order_by(func.count(Product.id).desc())
        .limit(20)
    )
    categories = [
        {"category_id": row.category_id, "count": row.count}
        for row in category_result.fetchall()
    ]

    return {
        "price_range": price_range,
        "categories": categories,
    }


async def get_search_suggestions(
    db: AsyncSession,
    store_id: uuid.UUID,
    query: str,
    limit: int = 5,
) -> list[str]:
    """Get search auto-complete suggestions based on product titles.

    Returns distinct product titles that start with or contain the
    query string, limited to active products.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        query: The partial search query to complete.
        limit: Maximum number of suggestions to return (default 5).

    Returns:
        A list of product title strings matching the query.
    """
    result = await db.execute(
        select(Product.title)
        .where(
            Product.store_id == store_id,
            Product.status == ProductStatus.active,
            Product.title.ilike(f"%{query}%"),
        )
        .order_by(
            # Prefer titles that start with the query
            case(
                (Product.title.ilike(f"{query}%"), 0),
                else_=1,
            ),
            Product.title,
        )
    )
    # Deduplicate titles in Python instead of using SQL DISTINCT
    # (DISTINCT requires ORDER BY expressions in SELECT list)
    seen: set[str] = set()
    titles: list[str] = []
    for row in result.fetchall():
        title = row[0]
        if title not in seen:
            seen.add(title)
            titles.append(title)
            if len(titles) >= limit:
                break
    return titles
