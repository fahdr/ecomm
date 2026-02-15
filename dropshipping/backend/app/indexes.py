"""
Database index definitions for the dropshipping platform.

Contains all performance-critical indexes organized by table. These indexes
are designed to accelerate the most common query patterns: store lookups,
product browsing, order filtering, and analytics aggregation.

For Developers:
    Run ``make db-create-indexes`` to apply all indexes idempotently.
    Each statement uses ``CREATE INDEX IF NOT EXISTS`` so it is safe to
    run multiple times. Add new indexes to ``CRITICAL_INDEXES`` and
    re-run the target.

    To apply programmatically::

        from app.indexes import apply_indexes
        await apply_indexes(engine)

For QA Engineers:
    After running ``make db-create-indexes``, verify indexes exist with:
        \\di+ idx_* in psql, or SELECT indexname FROM pg_indexes
        WHERE tablename = 'products';

For Project Managers:
    These indexes are the primary database performance optimization for
    Phase 7. They target the top query patterns identified during load
    testing and eliminate full-table scans on the largest tables.

For End Users:
    These optimizations make your dashboard and storefront load faster,
    especially for stores with thousands of products and orders.
"""

import logging
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ── Critical Indexes ────────────────────────────────────────────────────
#
# Each entry is an idempotent CREATE INDEX IF NOT EXISTS statement.
# Organized by table for readability.

CRITICAL_INDEXES: Sequence[str] = [
    # ── Products — most queried table ─────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_products_store_id ON products(store_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_status ON products(status)",
    "CREATE INDEX IF NOT EXISTS idx_products_store_slug ON products(store_id, slug)",

    # ── Orders — frequently filtered ──────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_orders_store_id ON orders(store_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
    "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC)",

    # ── Variants ──────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_variants_product_id ON product_variants(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_variants_sku ON product_variants(sku)",

    # ── Reviews ───────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_store_id ON reviews(store_id)",

    # ── Analytics ─────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_analytics_store_date ON analytics_events(store_id, created_at DESC)",

    # ── Categories ────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_categories_store_id ON categories(store_id)",
    "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)",

    # ── Customers ─────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_customers_store_id ON customers(store_id)",
    "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(store_id, email)",

    # ── Discounts ─────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_discounts_store_code ON discounts(store_id, code)",
    "CREATE INDEX IF NOT EXISTS idx_discounts_active ON discounts(store_id, is_active, starts_at, ends_at)",

    # ── Inventory (Phase 3 tables) ────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_inventory_levels_variant ON inventory_levels(variant_id, warehouse_id)",
    "CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_level ON inventory_adjustments(inventory_level_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_warehouses_store ON warehouses(store_id)",
]


async def apply_indexes(engine: AsyncEngine) -> int:
    """
    Apply all critical indexes to the database.

    Executes each ``CREATE INDEX IF NOT EXISTS`` statement within a single
    transaction. Logs each index creation and reports failures without
    aborting the entire batch.

    Args:
        engine: The async SQLAlchemy engine connected to the target database.

    Returns:
        The number of indexes successfully applied.
    """
    applied = 0
    async with engine.begin() as conn:
        for stmt in CRITICAL_INDEXES:
            try:
                await conn.execute(text(stmt))
                applied += 1
                # Extract index name for logging
                idx_name = stmt.split("IF NOT EXISTS ")[-1].split(" ON")[0]
                logger.info("Index applied: %s", idx_name)
            except Exception as exc:
                logger.warning("Failed to apply index: %s — %s", stmt, exc)
    logger.info("Applied %d / %d indexes", applied, len(CRITICAL_INDEXES))
    return applied
