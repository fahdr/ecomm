"""Store cloning service.

Handles deep cloning of a store, including all products, variants,
themes, discounts, categories, tax rules, and suppliers.

**For Developers:**
    ``clone_store()`` is the main entry point. It creates a new store
    record and copies all child entities using dedicated ``_clone_*``
    helper functions. Each helper remaps UUIDs so cloned records have
    fresh identifiers. Junction tables (product-category, product-supplier,
    discount-product, discount-category) are re-linked using ID maps.

**For QA Engineers:**
    - Cloned stores get a slug like ``{original}-copy``, ``{original}-copy-2``.
    - Orders, reviews, analytics, customer data, webhooks, and teams are NOT cloned.
    - Discount usage counters are reset to 0.
    - Discount codes are suffixed with ``-copy`` to avoid cross-store confusion.
    - The ``is_active`` theme flag is preserved so the same theme is active.
    - Category hierarchies (parent-child) are preserved using ID remapping.

**For End Users:**
    Clone an existing store to quickly create a copy with all your
    products, themes, discounts, and settings. Orders and customer
    data are not copied.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, ProductCategory
from app.models.discount import (
    Discount,
    DiscountCategory,
    DiscountProduct,
    DiscountStatus,
)
from app.models.product import Product, ProductVariant
from app.models.store import Store, StoreStatus
from app.models.supplier import ProductSupplier, Supplier
from app.models.tax import TaxRate
from app.models.theme import StoreTheme
from app.utils.slug import generate_unique_slug


async def clone_store(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_store_id: uuid.UUID,
    new_name: str | None = None,
) -> Store:
    """Clone a store with all products, variants, themes, discounts, and more.

    Creates a new store record owned by the same user, then copies all child
    entities. Orders, reviews, analytics, customer data, webhooks, and teams
    are NOT cloned.

    Args:
        db: Async database session.
        user_id: UUID of the user performing the clone (must own the source store).
        source_store_id: UUID of the store to clone.
        new_name: Optional name override. Defaults to ``{original_name} (Copy)``.

    Returns:
        The newly created Store ORM instance with all cloned child records.

    Raises:
        ValueError: If the source store is not found or doesn't belong to the user.
    """
    # Fetch and verify ownership of the source store.
    result = await db.execute(select(Store).where(Store.id == source_store_id))
    source = result.scalar_one_or_none()
    if source is None or source.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if source.user_id != user_id:
        raise ValueError("Store not found")

    # Create the cloned store.
    clone_name = new_name or f"{source.name} (Copy)"
    slug = await generate_unique_slug(db, Store, clone_name)

    new_store = Store(
        user_id=user_id,
        name=clone_name,
        slug=slug,
        niche=source.niche,
        description=source.description,
        default_currency=source.default_currency,
        theme=source.theme,
        logo_url=source.logo_url,
        favicon_url=source.favicon_url,
        custom_css=source.custom_css,
        status=StoreStatus.active,
    )
    db.add(new_store)
    await db.flush()

    # Clone child entities. Order matters because some depend on ID maps.
    category_id_map = await _clone_categories(db, source.id, new_store.id)
    product_id_map, variant_id_map = await _clone_products(db, source.id, new_store.id)
    supplier_id_map = await _clone_suppliers(db, source.id, new_store.id)
    await _clone_product_categories(db, product_id_map, category_id_map)
    await _clone_product_suppliers(db, product_id_map, supplier_id_map)
    await _clone_themes(db, source.id, new_store.id)
    await _clone_discounts(db, source.id, new_store.id, product_id_map, category_id_map)
    await _clone_tax_rules(db, source.id, new_store.id)

    await db.refresh(new_store)
    return new_store


async def _clone_categories(
    db: AsyncSession,
    source_store_id: uuid.UUID,
    target_store_id: uuid.UUID,
) -> dict[uuid.UUID, uuid.UUID]:
    """Clone all categories, preserving parent-child hierarchy.

    Args:
        db: Async database session.
        source_store_id: ID of the source store.
        target_store_id: ID of the target (cloned) store.

    Returns:
        A mapping from old category IDs to new category IDs.
    """
    result = await db.execute(
        select(Category)
        .where(Category.store_id == source_store_id)
        .order_by(Category.position)
    )
    categories = list(result.scalars().all())

    id_map: dict[uuid.UUID, uuid.UUID] = {}

    # First pass: clone all categories without parent links.
    for cat in categories:
        new_id = uuid.uuid4()
        id_map[cat.id] = new_id
        new_cat = Category(
            id=new_id,
            store_id=target_store_id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            image_url=cat.image_url,
            parent_id=None,
            position=cat.position,
            is_active=cat.is_active,
        )
        db.add(new_cat)

    await db.flush()

    # Second pass: set parent_id using the ID map.
    for cat in categories:
        if cat.parent_id and cat.parent_id in id_map:
            result2 = await db.execute(
                select(Category).where(Category.id == id_map[cat.id])
            )
            new_cat = result2.scalar_one()
            new_cat.parent_id = id_map[cat.parent_id]

    await db.flush()
    return id_map


async def _clone_products(
    db: AsyncSession,
    source_store_id: uuid.UUID,
    target_store_id: uuid.UUID,
) -> tuple[dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, uuid.UUID]]:
    """Clone all non-archived products and their variants.

    Args:
        db: Async database session.
        source_store_id: ID of the source store.
        target_store_id: ID of the target (cloned) store.

    Returns:
        A tuple of (product_id_map, variant_id_map) mapping old IDs to new IDs.
    """
    result = await db.execute(
        select(Product).where(
            Product.store_id == source_store_id,
            Product.status != "archived",
        )
    )
    products = list(result.scalars().all())

    product_id_map: dict[uuid.UUID, uuid.UUID] = {}
    variant_id_map: dict[uuid.UUID, uuid.UUID] = {}

    for product in products:
        new_product_id = uuid.uuid4()
        product_id_map[product.id] = new_product_id

        new_product = Product(
            id=new_product_id,
            store_id=target_store_id,
            title=product.title,
            slug=product.slug,
            description=product.description,
            price=product.price,
            compare_at_price=product.compare_at_price,
            cost=product.cost,
            images=product.images,
            status=product.status,
            tags=product.tags,
            seo_title=product.seo_title,
            seo_description=product.seo_description,
            avg_rating=None,
            review_count=0,
        )
        db.add(new_product)

        # Clone variants for this product.
        for variant in product.variants:
            new_variant_id = uuid.uuid4()
            variant_id_map[variant.id] = new_variant_id

            new_variant = ProductVariant(
                id=new_variant_id,
                product_id=new_product_id,
                name=variant.name,
                sku=variant.sku,
                price=variant.price,
                inventory_count=variant.inventory_count,
            )
            db.add(new_variant)

    await db.flush()
    return product_id_map, variant_id_map


async def _clone_product_categories(
    db: AsyncSession,
    product_id_map: dict[uuid.UUID, uuid.UUID],
    category_id_map: dict[uuid.UUID, uuid.UUID],
) -> int:
    """Clone product-category junction records using remapped IDs.

    Args:
        db: Async database session.
        product_id_map: Mapping from old to new product IDs.
        category_id_map: Mapping from old to new category IDs.

    Returns:
        Number of junction records created.
    """
    if not product_id_map or not category_id_map:
        return 0

    old_product_ids = list(product_id_map.keys())
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.product_id.in_(old_product_ids))
    )
    junctions = list(result.scalars().all())

    count = 0
    for junc in junctions:
        new_product_id = product_id_map.get(junc.product_id)
        new_category_id = category_id_map.get(junc.category_id)
        if new_product_id and new_category_id:
            db.add(ProductCategory(
                product_id=new_product_id,
                category_id=new_category_id,
            ))
            count += 1

    await db.flush()
    return count


async def _clone_suppliers(
    db: AsyncSession,
    source_store_id: uuid.UUID,
    target_store_id: uuid.UUID,
) -> dict[uuid.UUID, uuid.UUID]:
    """Clone all active suppliers.

    Args:
        db: Async database session.
        source_store_id: ID of the source store.
        target_store_id: ID of the target (cloned) store.

    Returns:
        A mapping from old supplier IDs to new supplier IDs.
    """
    result = await db.execute(
        select(Supplier).where(Supplier.store_id == source_store_id)
    )
    suppliers = list(result.scalars().all())

    id_map: dict[uuid.UUID, uuid.UUID] = {}

    for sup in suppliers:
        new_id = uuid.uuid4()
        id_map[sup.id] = new_id
        db.add(Supplier(
            id=new_id,
            store_id=target_store_id,
            name=sup.name,
            website=sup.website,
            contact_email=sup.contact_email,
            contact_phone=sup.contact_phone,
            notes=sup.notes,
            status=sup.status,
            reliability_score=sup.reliability_score,
            avg_shipping_days=sup.avg_shipping_days,
        ))

    await db.flush()
    return id_map


async def _clone_product_suppliers(
    db: AsyncSession,
    product_id_map: dict[uuid.UUID, uuid.UUID],
    supplier_id_map: dict[uuid.UUID, uuid.UUID],
) -> int:
    """Clone product-supplier junction records using remapped IDs.

    Args:
        db: Async database session.
        product_id_map: Mapping from old to new product IDs.
        supplier_id_map: Mapping from old to new supplier IDs.

    Returns:
        Number of junction records created.
    """
    if not product_id_map or not supplier_id_map:
        return 0

    old_product_ids = list(product_id_map.keys())
    result = await db.execute(
        select(ProductSupplier).where(ProductSupplier.product_id.in_(old_product_ids))
    )
    junctions = list(result.scalars().all())

    count = 0
    for junc in junctions:
        new_product_id = product_id_map.get(junc.product_id)
        new_supplier_id = supplier_id_map.get(junc.supplier_id)
        if new_product_id and new_supplier_id:
            db.add(ProductSupplier(
                product_id=new_product_id,
                supplier_id=new_supplier_id,
                cost=junc.cost,
                sku=junc.sku,
                source_url=junc.source_url,
                is_primary=junc.is_primary,
            ))
            count += 1

    await db.flush()
    return count


async def _clone_themes(
    db: AsyncSession,
    source_store_id: uuid.UUID,
    target_store_id: uuid.UUID,
) -> int:
    """Clone all theme configs, preserving active/inactive state.

    Args:
        db: Async database session.
        source_store_id: ID of the source store.
        target_store_id: ID of the target (cloned) store.

    Returns:
        Number of themes cloned.
    """
    result = await db.execute(
        select(StoreTheme).where(StoreTheme.store_id == source_store_id)
    )
    themes = list(result.scalars().all())

    for theme in themes:
        db.add(StoreTheme(
            store_id=target_store_id,
            name=theme.name,
            is_active=theme.is_active,
            is_preset=theme.is_preset,
            colors=theme.colors,
            typography=theme.typography,
            styles=theme.styles,
            blocks=theme.blocks,
            logo_url=theme.logo_url,
            favicon_url=theme.favicon_url,
            custom_css=theme.custom_css,
        ))

    await db.flush()
    return len(themes)


async def _clone_discounts(
    db: AsyncSession,
    source_store_id: uuid.UUID,
    target_store_id: uuid.UUID,
    product_id_map: dict[uuid.UUID, uuid.UUID],
    category_id_map: dict[uuid.UUID, uuid.UUID],
) -> int:
    """Clone all non-expired discounts. Reset usage counters and suffix codes.

    Args:
        db: Async database session.
        source_store_id: ID of the source store.
        target_store_id: ID of the target (cloned) store.
        product_id_map: Mapping from old to new product IDs.
        category_id_map: Mapping from old to new category IDs.

    Returns:
        Number of discounts cloned.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Discount).where(
            Discount.store_id == source_store_id,
            Discount.status != DiscountStatus.expired,
        )
    )
    discounts = list(result.scalars().all())

    discount_id_map: dict[uuid.UUID, uuid.UUID] = {}

    for disc in discounts:
        # Skip already expired discounts based on date.
        if disc.expires_at and disc.expires_at < now:
            continue

        new_id = uuid.uuid4()
        discount_id_map[disc.id] = new_id

        db.add(Discount(
            id=new_id,
            store_id=target_store_id,
            code=f"{disc.code}-copy",
            description=disc.description,
            discount_type=disc.discount_type,
            value=disc.value,
            minimum_order_amount=disc.minimum_order_amount,
            max_uses=disc.max_uses,
            times_used=0,
            starts_at=disc.starts_at,
            expires_at=disc.expires_at,
            status=disc.status,
            applies_to=disc.applies_to,
        ))

    await db.flush()

    # Clone discount-product and discount-category junctions.
    for old_disc_id, new_disc_id in discount_id_map.items():
        # Products.
        prod_result = await db.execute(
            select(DiscountProduct).where(DiscountProduct.discount_id == old_disc_id)
        )
        for dp in prod_result.scalars().all():
            new_prod_id = product_id_map.get(dp.product_id)
            if new_prod_id:
                db.add(DiscountProduct(
                    discount_id=new_disc_id,
                    product_id=new_prod_id,
                ))

        # Categories.
        cat_result = await db.execute(
            select(DiscountCategory).where(DiscountCategory.discount_id == old_disc_id)
        )
        for dc in cat_result.scalars().all():
            new_cat_id = category_id_map.get(dc.category_id)
            if new_cat_id:
                db.add(DiscountCategory(
                    discount_id=new_disc_id,
                    category_id=new_cat_id,
                ))

    await db.flush()
    return len(discount_id_map)


async def _clone_tax_rules(
    db: AsyncSession,
    source_store_id: uuid.UUID,
    target_store_id: uuid.UUID,
) -> int:
    """Clone all active tax rates.

    Args:
        db: Async database session.
        source_store_id: ID of the source store.
        target_store_id: ID of the target (cloned) store.

    Returns:
        Number of tax rules cloned.
    """
    result = await db.execute(
        select(TaxRate).where(
            TaxRate.store_id == source_store_id,
            TaxRate.is_active.is_(True),
        )
    )
    tax_rates = list(result.scalars().all())

    for tr in tax_rates:
        db.add(TaxRate(
            store_id=target_store_id,
            name=tr.name,
            rate=tr.rate,
            country=tr.country,
            state=tr.state,
            zip_code=tr.zip_code,
            is_active=True,
            priority=tr.priority,
            is_inclusive=tr.is_inclusive,
        ))

    await db.flush()
    return len(tax_rates)
