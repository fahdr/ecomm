"""Product business logic.

Handles CRUD operations for products scoped to a store. All functions
verify store ownership before performing operations.

**For Developers:**
    All functions take ``store_id`` and ``user_id`` to enforce ownership.
    Soft-delete sets ``status`` to ``archived`` rather than removing the row.
    Pagination is handled in ``list_products`` with optional search and
    status filtering.

**For QA Engineers:**
    - ``create_product`` generates a unique slug from the product title.
    - ``list_products`` excludes archived products by default unless
      ``status_filter`` is explicitly set to ``archived``.
    - ``get_product`` raises ``ValueError`` if the product doesn't exist or
      the store doesn't belong to the user.
    - ``delete_product`` performs a soft-delete (sets status to ``archived``).
    - Variants are created/replaced atomically with the product.
"""

import math
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductStatus, ProductVariant
from app.models.store import Store, StoreStatus
from app.utils.slug import generate_unique_slug


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def _generate_product_slug(
    db: AsyncSession, store_id: uuid.UUID, title: str
) -> str:
    """Generate a unique product slug within a store.

    Uses the title to create a base slug, then checks for uniqueness
    within the store scope (not globally).

    Args:
        db: Async database session.
        store_id: The store's UUID for scoping uniqueness.
        title: The product title to derive the slug from.

    Returns:
        A unique slug string within the store.
    """
    from app.utils.slug import slugify

    base_slug = slugify(title)
    slug = base_slug
    counter = 2

    while True:
        result = await db.execute(
            select(Product).where(
                Product.store_id == store_id, Product.slug == slug
            )
        )
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def create_product(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    price: Decimal,
    description: str | None = None,
    compare_at_price: Decimal | None = None,
    cost: Decimal | None = None,
    images: list[str] | None = None,
    status: ProductStatus = ProductStatus.draft,
    seo_title: str | None = None,
    seo_description: str | None = None,
    variants: list[dict] | None = None,
) -> Product:
    """Create a new product in a store.

    Verifies store ownership, generates a unique slug from the title,
    and optionally creates variants.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        title: Display title of the product.
        price: Selling price.
        description: Optional product description.
        compare_at_price: Optional compare-at price.
        cost: Optional supplier cost.
        images: Optional list of image URL strings.
        status: Product status (defaults to draft).
        seo_title: Optional SEO title.
        seo_description: Optional SEO meta description.
        variants: Optional list of variant dicts with name, sku, price, inventory_count.

    Returns:
        The newly created Product ORM instance with variants loaded.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    slug = await _generate_product_slug(db, store_id, title)

    product = Product(
        store_id=store_id,
        title=title,
        slug=slug,
        description=description,
        price=price,
        compare_at_price=compare_at_price,
        cost=cost,
        images=images or [],
        status=status,
        seo_title=seo_title,
        seo_description=seo_description,
    )
    db.add(product)
    await db.flush()

    if variants:
        for v in variants:
            variant = ProductVariant(
                product_id=product.id,
                name=v["name"],
                sku=v.get("sku"),
                price=v.get("price"),
                inventory_count=v.get("inventory_count", 0),
            )
            db.add(variant)
        await db.flush()

    await db.refresh(product)
    return product


async def list_products(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    status_filter: ProductStatus | None = None,
) -> tuple[list[Product], int]:
    """List products for a store with pagination, search, and status filtering.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        search: Optional search term to filter by title (case-insensitive).
        status_filter: Optional status to filter by.

    Returns:
        A tuple of (products list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Product).where(Product.store_id == store_id)
    count_query = select(func.count(Product.id)).where(Product.store_id == store_id)

    if status_filter is not None:
        query = query.where(Product.status == status_filter)
        count_query = count_query.where(Product.status == status_filter)
    else:
        query = query.where(Product.status != ProductStatus.archived)
        count_query = count_query.where(Product.status != ProductStatus.archived)

    if search:
        query = query.where(Product.title.ilike(f"%{search}%"))
        count_query = count_query.where(Product.title.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    products = list(result.scalars().all())

    return products, total


async def get_product(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    """Retrieve a single product, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_id: The UUID of the product to retrieve.

    Returns:
        The Product ORM instance with variants loaded.

    Raises:
        ValueError: If the store or product doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ValueError("Product not found")
    return product


async def update_product(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    **fields,
) -> Product:
    """Update a product's fields (partial update).

    Only provided (non-None) fields are updated. The slug is regenerated
    if the title changes. If ``variants`` is provided, existing variants
    are replaced entirely.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_id: The UUID of the product to update.
        **fields: Keyword arguments for fields to update.

    Returns:
        The updated Product ORM instance.

    Raises:
        ValueError: If the store or product doesn't exist, or the store
            belongs to another user.
    """
    product = await get_product(db, store_id, user_id, product_id)

    variants_data = fields.pop("variants", None)

    for key, value in fields.items():
        if value is not None:
            setattr(product, key, value)

    if "title" in fields and fields["title"] is not None:
        product.slug = await _generate_product_slug(db, store_id, fields["title"])

    if variants_data is not None:
        # Replace all existing variants
        for variant in list(product.variants):
            await db.delete(variant)
        await db.flush()

        for v in variants_data:
            variant = ProductVariant(
                product_id=product.id,
                name=v["name"],
                sku=v.get("sku"),
                price=v.get("price"),
                inventory_count=v.get("inventory_count", 0),
            )
            db.add(variant)

    await db.flush()
    await db.refresh(product)
    return product


async def delete_product(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    """Soft-delete a product by setting its status to ``archived``.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        product_id: The UUID of the product to delete.

    Returns:
        The soft-deleted Product ORM instance.

    Raises:
        ValueError: If the store or product doesn't exist, or the store
            belongs to another user.
    """
    product = await get_product(db, store_id, user_id, product_id)
    product.status = ProductStatus.archived
    await db.flush()
    await db.refresh(product)
    return product
