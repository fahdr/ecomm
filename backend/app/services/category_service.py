"""Category business logic.

Handles CRUD operations for hierarchical product categories within a store,
including tree building, product assignment, and slug generation.

**For Developers:**
    Categories support self-referential parent-child nesting via
    ``parent_id``. The ``get_category_tree`` function builds a full
    hierarchical tree in memory from a flat list. Category slugs are
    auto-generated from the name and scoped unique within a store.
    Product-to-category assignment uses the ``product_categories``
    junction table.

**For QA Engineers:**
    - ``create_category`` generates a slug unique within the store.
    - ``list_categories`` returns a flat paginated list or an unpaginated
      tree depending on the ``include_children`` flag.
    - ``delete_category`` is a hard delete; child categories are orphaned
      (their ``parent_id`` becomes NULL via ON DELETE SET NULL).
    - ``assign_products_to_category`` is idempotent (skips duplicates).
    - ``get_products_by_category`` only returns active products.

**For Project Managers:**
    This service powers Feature 9 (Categories & Navigation) from the
    backlog, enabling store owners to organise products into a browsable
    hierarchy for their storefront.

**For End Users:**
    Create categories to organise your products so customers can browse
    by type. Nest subcategories (e.g. "Clothing" > "Men" > "T-Shirts")
    and assign products to multiple categories.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, ProductCategory
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.utils.slug import slugify


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


async def _generate_category_slug(
    db: AsyncSession, store_id: uuid.UUID, name: str, exclude_id=None,
) -> str:
    """Generate a unique category slug within a store.

    Derives a base slug from the name and appends numeric suffixes
    until uniqueness within the store is achieved.

    Args:
        db: Async database session.
        store_id: The store's UUID for scoping uniqueness.
        name: The category name to derive the slug from.
        exclude_id: Optional UUID of the current category to exclude from
            the uniqueness check (used during updates).

    Returns:
        A unique slug string within the store.
    """
    base_slug = slugify(name)
    slug = base_slug
    counter = 2

    while True:
        query = select(Category).where(
            Category.store_id == store_id,
            Category.slug == slug,
        )
        if exclude_id is not None:
            query = query.where(Category.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def create_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: str | None = None,
    image_url: str | None = None,
    parent_id: uuid.UUID | None = None,
    position: int = 0,
) -> Category:
    """Create a new category in a store.

    Generates a unique slug from the category name. If ``parent_id``
    is provided, validates that the parent category exists and belongs
    to the same store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        name: Display name of the category.
        description: Optional description text.
        image_url: Optional URL for a category image.
        parent_id: Optional UUID of the parent category for nesting.
        position: Sort order within the same parent level (default 0).

    Returns:
        The newly created Category ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or the parent category doesn't exist.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if parent_id is not None:
        parent_result = await db.execute(
            select(Category).where(
                Category.id == parent_id,
                Category.store_id == store_id,
            )
        )
        if parent_result.scalar_one_or_none() is None:
            raise ValueError("Parent category not found")

    slug = await _generate_category_slug(db, store_id, name)

    category = Category(
        store_id=store_id,
        name=name,
        slug=slug,
        description=description,
        image_url=image_url,
        parent_id=parent_id,
        position=position,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def list_categories(
    db: AsyncSession,
    store_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
    include_children: bool = False,
) -> tuple[list[Category], int]:
    """List categories for a store with pagination.

    When ``include_children`` is False, returns a flat paginated list
    of all categories. When True, returns only top-level categories
    (the tree can be navigated via the ``children`` relationship).

    Note: This function does NOT require ownership verification because
    categories are used on the public storefront as well.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        page: Page number (1-based).
        per_page: Number of items per page.
        include_children: If True, only return root categories (parent_id
            is None) so the tree can be traversed via relationships.

    Returns:
        A tuple of (categories list, total count).
    """
    query = select(Category).where(
        Category.store_id == store_id,
        Category.is_active.is_(True),
    )
    count_query = select(func.count(Category.id)).where(
        Category.store_id == store_id,
        Category.is_active.is_(True),
    )

    if include_children:
        query = query.where(Category.parent_id.is_(None))
        count_query = count_query.where(Category.parent_id.is_(None))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Category.position, Category.name).offset(offset).limit(per_page)

    result = await db.execute(query)
    categories = list(result.scalars().all())

    return categories, total


async def get_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    """Retrieve a single category by ID.

    Does not require ownership verification as categories are public.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        category_id: The UUID of the category to retrieve.

    Returns:
        The Category ORM instance with relationships loaded.

    Raises:
        ValueError: If the category doesn't exist in the store.
    """
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.store_id == store_id,
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise ValueError("Category not found")
    return category


async def update_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    **kwargs,
) -> Category:
    """Update a category's fields (partial update).

    Regenerates the slug if the name changes. Only provided (non-None)
    keyword arguments are applied.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        category_id: The UUID of the category to update.
        **kwargs: Keyword arguments for fields to update (name, description,
            image_url, parent_id, position, is_active).

    Returns:
        The updated Category ORM instance.

    Raises:
        ValueError: If the store or category doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)
    category = await get_category(db, store_id, category_id)

    for key, value in kwargs.items():
        if value is not None:
            setattr(category, key, value)

    # Regenerate slug if name changed
    if "name" in kwargs and kwargs["name"] is not None:
        category.slug = await _generate_category_slug(
            db, store_id, kwargs["name"], exclude_id=category.id
        )

    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> None:
    """Permanently delete a category.

    Child categories will have their ``parent_id`` set to NULL (orphaned)
    via the ON DELETE SET NULL foreign key constraint. Product-category
    links are cascade-deleted.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        category_id: The UUID of the category to delete.

    Raises:
        ValueError: If the store or category doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)
    category = await get_category(db, store_id, category_id)
    await db.delete(category)
    await db.flush()


async def get_category_tree(
    db: AsyncSession,
    store_id: uuid.UUID,
) -> list[dict]:
    """Build a hierarchical category tree for a store.

    Fetches all active categories for the store and assembles them into
    a nested tree structure in memory. Each node is a dict containing
    the category's fields and a ``children`` list of child nodes.

    Args:
        db: Async database session.
        store_id: The store's UUID.

    Returns:
        A list of root-level category dicts, each with nested ``children``.
    """
    result = await db.execute(
        select(Category).where(
            Category.store_id == store_id,
            Category.is_active.is_(True),
        ).order_by(Category.position, Category.name)
    )
    categories = list(result.scalars().all())

    # Build lookup and tree
    lookup: dict[uuid.UUID, dict] = {}
    for cat in categories:
        lookup[cat.id] = {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "image_url": cat.image_url,
            "parent_id": cat.parent_id,
            "position": cat.position,
            "children": [],
        }

    roots: list[dict] = []
    for cat_id, node in lookup.items():
        parent_id = node["parent_id"]
        if parent_id is not None and parent_id in lookup:
            lookup[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


async def assign_products_to_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    product_ids: list[uuid.UUID],
) -> None:
    """Assign multiple products to a category.

    Idempotent: if a product is already assigned to the category, the
    duplicate is silently skipped.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        category_id: The UUID of the target category.
        product_ids: List of product UUIDs to assign.

    Raises:
        ValueError: If the store or category doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)
    await get_category(db, store_id, category_id)

    for pid in product_ids:
        # Check if already assigned
        existing = await db.execute(
            select(ProductCategory).where(
                ProductCategory.product_id == pid,
                ProductCategory.category_id == category_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(ProductCategory(product_id=pid, category_id=category_id))

    await db.flush()


async def remove_product_from_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    product_id: uuid.UUID,
) -> None:
    """Remove a product from a category.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        category_id: The UUID of the category.
        product_id: The UUID of the product to remove.

    Raises:
        ValueError: If the store or category doesn't exist, the store
            belongs to another user, or the product is not in the category.
    """
    await _verify_store_ownership(db, store_id, user_id)
    await get_category(db, store_id, category_id)

    result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.product_id == product_id,
            ProductCategory.category_id == category_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise ValueError("Product is not assigned to this category")

    await db.delete(link)
    await db.flush()


async def get_products_by_category(
    db: AsyncSession,
    store_id: uuid.UUID,
    category_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Product], int]:
    """Get active products belonging to a specific category.

    Only returns products with ``active`` status. Does not require
    ownership verification as this is a public storefront function.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        category_id: The UUID of the category.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (products list, total count).

    Raises:
        ValueError: If the category doesn't exist in the store.
    """
    await get_category(db, store_id, category_id)

    query = (
        select(Product)
        .join(ProductCategory, ProductCategory.product_id == Product.id)
        .where(
            ProductCategory.category_id == category_id,
            Product.store_id == store_id,
            Product.status == ProductStatus.active,
        )
    )
    count_query = (
        select(func.count(Product.id))
        .join(ProductCategory, ProductCategory.product_id == Product.id)
        .where(
            ProductCategory.category_id == category_id,
            Product.store_id == store_id,
            Product.status == ProductStatus.active,
        )
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    products = list(result.scalars().all())

    return products, total
