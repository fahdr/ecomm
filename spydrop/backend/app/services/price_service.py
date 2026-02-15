"""
Price History Tracking service for SpyDrop.

Records price snapshots for competitor products and provides functions
for querying price history and detecting significant price changes.

For Developers:
    Three main functions:
    - ``record_price_snapshot(db, competitor_product_id, price)`` — save a price observation.
    - ``get_price_history(db, competitor_product_id, days)`` — query history for a product.
    - ``detect_price_changes(db, competitor_id)`` — find products with significant changes.

    Price change detection compares the most recent snapshot against the
    one before it for each product. A change is "significant" if it exceeds
    the ``SIGNIFICANT_CHANGE_THRESHOLD`` (5% by default).

For QA Engineers:
    Test snapshot recording, history retrieval with date ranges, and
    price change detection with various price movement scenarios.
    Verify that ``detect_price_changes`` correctly identifies both
    price drops and increases above the threshold.

For Project Managers:
    Price tracking is a core differentiator for SpyDrop. Users rely on
    accurate price history to understand competitor pricing strategies
    and identify opportunities for competitive pricing.

For End Users:
    View how competitor prices have changed over time. SpyDrop tracks
    every price change so you can spot trends and act quickly.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import CompetitorProduct
from app.models.price_snapshot import PriceSnapshot

logger = logging.getLogger(__name__)

# Minimum percentage change to be considered "significant"
SIGNIFICANT_CHANGE_THRESHOLD = 5.0


async def record_price_snapshot(
    db: AsyncSession,
    competitor_product_id: uuid.UUID,
    price: float,
    currency: str = "USD",
    captured_at: datetime | None = None,
) -> PriceSnapshot:
    """
    Record a price snapshot for a competitor product.

    Creates a new PriceSnapshot entry with the current timestamp
    (or an explicitly provided timestamp for historical imports).
    Called during scans when a product's price is observed.

    Args:
        db: Async database session.
        competitor_product_id: UUID of the CompetitorProduct being tracked.
        price: The observed price value.
        currency: Currency code (default 'USD').
        captured_at: Optional explicit timestamp (defaults to server now()).

    Returns:
        The newly created PriceSnapshot record.
    """
    kwargs: dict = {
        "competitor_product_id": competitor_product_id,
        "price": price,
        "currency": currency,
    }
    if captured_at is not None:
        kwargs["captured_at"] = captured_at
    snapshot = PriceSnapshot(**kwargs)
    db.add(snapshot)
    await db.flush()
    logger.debug(
        "Recorded price snapshot: product=%s, price=%.2f %s",
        competitor_product_id,
        price,
        currency,
    )
    return snapshot


async def get_price_history(
    db: AsyncSession,
    competitor_product_id: uuid.UUID,
    days: int = 90,
) -> list[PriceSnapshot]:
    """
    Get price history for a competitor product within a date range.

    Returns snapshots ordered by captured_at (oldest first) for
    charting purposes.

    Args:
        db: Async database session.
        competitor_product_id: UUID of the CompetitorProduct to query.
        days: Number of days of history to retrieve (default 90).

    Returns:
        List of PriceSnapshot records ordered by capture time ascending.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.competitor_product_id == competitor_product_id,
            PriceSnapshot.captured_at >= cutoff,
        )
        .order_by(PriceSnapshot.captured_at.asc())
    )
    return list(result.scalars().all())


async def detect_price_changes(
    db: AsyncSession,
    competitor_id: uuid.UUID,
) -> list[dict]:
    """
    Detect products with significant recent price changes for a competitor.

    For each active product, compares the two most recent price snapshots.
    Returns products where the price changed by more than
    ``SIGNIFICANT_CHANGE_THRESHOLD`` percent.

    Args:
        db: Async database session.
        competitor_id: UUID of the competitor to check.

    Returns:
        List of dicts with keys:
            - product_id (UUID): The product's UUID.
            - title (str): Product title.
            - old_price (float): Previous price.
            - new_price (float): Current price.
            - change_percent (float): Percentage change.
            - direction (str): 'increase' or 'decrease'.
    """
    # Get all active products for this competitor
    prod_result = await db.execute(
        select(CompetitorProduct).where(
            CompetitorProduct.competitor_id == competitor_id,
            CompetitorProduct.status == "active",
        )
    )
    products = list(prod_result.scalars().all())

    changes: list[dict] = []

    for product in products:
        # Get the two most recent snapshots
        snap_result = await db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.competitor_product_id == product.id)
            .order_by(PriceSnapshot.captured_at.desc())
            .limit(2)
        )
        snapshots = list(snap_result.scalars().all())

        if len(snapshots) < 2:
            continue

        newest = snapshots[0]
        previous = snapshots[1]

        if previous.price == 0:
            continue

        change_pct = ((newest.price - previous.price) / previous.price) * 100

        if abs(change_pct) >= SIGNIFICANT_CHANGE_THRESHOLD:
            changes.append({
                "product_id": product.id,
                "title": product.title,
                "old_price": previous.price,
                "new_price": newest.price,
                "change_percent": round(change_pct, 2),
                "direction": "increase" if change_pct > 0 else "decrease",
            })

    logger.info(
        "Detected %d significant price changes for competitor %s",
        len(changes),
        competitor_id,
    )
    return changes
