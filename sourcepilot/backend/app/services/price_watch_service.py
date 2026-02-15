"""
Price watch service for monitoring supplier product price changes.

Handles CRUD operations for price watches and provides the sync logic
that checks for price changes across all active watches.

For Developers:
    Price values are stored as ``Decimal(10, 2)`` in the model but
    accepted/returned as floats in the API schemas. The
    ``sync_all_prices`` function is called by the Celery beat schedule
    and the manual sync endpoint. The ``connection_id`` parameter in
    the API maps to the ``store_id`` column in the database.

For Project Managers:
    Price watches help users stay competitive by tracking supplier cost
    changes. The sync runs periodically via Celery beat and can also
    be triggered manually.

For QA Engineers:
    Test price watch creation with valid/invalid data. Verify that
    the sync updates ``current_price`` and ``price_changed`` correctly.
    Test deactivated watches are skipped during sync.

For End Users:
    Add price watches to track when supplier prices change.
    The system checks prices periodically, and you can also
    trigger a manual check at any time.
"""

import hashlib
import logging
import random
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_watch import PriceWatch
from app.schemas.price_watch import PriceWatchCreate

logger = logging.getLogger(__name__)


async def create_price_watch(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: PriceWatchCreate,
) -> PriceWatch:
    """
    Create a new price watch for a supplier product.

    Stores the user-provided ``product_url``, ``source``, and
    ``threshold_percent``. Optionally associates the watch with a
    store connection via ``connection_id`` (stored as ``store_id``).

    Args:
        db: Async database session.
        user_id: UUID of the owning user.
        data: Price watch creation data containing product_url, source,
              threshold_percent, and optional connection_id.

    Returns:
        The newly created PriceWatch.
    """
    watch = PriceWatch(
        user_id=user_id,
        product_url=data.product_url,
        source=data.source,
        threshold_percent=Decimal(str(data.threshold_percent)),
        store_id=data.connection_id,
        is_active=True,
    )
    db.add(watch)
    await db.flush()
    await db.refresh(watch)
    return watch


async def get_price_watches(
    db: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID | None = None,
) -> list[PriceWatch]:
    """
    Get all price watches for a user, optionally filtered by connection.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        connection_id: Optional connection (store) ID filter, mapped to store_id.

    Returns:
        List of PriceWatch records ordered by creation date (newest first).
    """
    base_filter = [PriceWatch.user_id == user_id]
    if connection_id:
        base_filter.append(PriceWatch.store_id == connection_id)

    result = await db.execute(
        select(PriceWatch)
        .where(*base_filter)
        .order_by(PriceWatch.created_at.desc())
    )
    return list(result.scalars().all())


async def get_price_watch(
    db: AsyncSession,
    watch_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PriceWatch | None:
    """
    Get a single price watch by ID, scoped to the requesting user.

    Args:
        db: Async database session.
        watch_id: The price watch's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The PriceWatch if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(PriceWatch).where(
            PriceWatch.id == watch_id,
            PriceWatch.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_price_watch(
    db: AsyncSession,
    watch_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Delete a price watch.

    Args:
        db: Async database session.
        watch_id: The price watch's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        True if deleted, False if not found or not owned.
    """
    watch = await get_price_watch(db, watch_id, user_id)
    if not watch:
        return False

    await db.delete(watch)
    await db.flush()
    return True


async def sync_all_prices(db: AsyncSession) -> dict:
    """
    Check all active price watches for price changes.

    Fetches current prices for all active watches and updates the
    ``current_price`` and ``price_changed`` fields accordingly.
    Currently uses mock price generation; in production this would
    call actual supplier APIs.

    Args:
        db: Async database session.

    Returns:
        Dict with sync results: total checked, changed count, errors.
    """
    result = await db.execute(
        select(PriceWatch).where(PriceWatch.is_active == True)  # noqa: E712
    )
    watches = list(result.scalars().all())

    checked = 0
    changed = 0
    errors = 0
    now = datetime.now(UTC).replace(tzinfo=None)

    for watch in watches:
        try:
            # Use product_url or source_product_id as identifier for mock pricing
            product_key = watch.source_product_id or watch.product_url or str(watch.id)
            # Mock price fetch - in production, call supplier API
            new_price = _fetch_mock_price(
                watch.source, product_key
            )

            watch.current_price = Decimal(str(new_price))
            watch.last_checked_at = now
            watch.price_changed = watch.current_price != watch.last_price
            checked += 1
            if watch.price_changed:
                changed += 1

        except Exception as e:
            logger.error(
                f"Error syncing price for watch {watch.id}: {e}"
            )
            errors += 1

    await db.flush()

    logger.info(
        f"Price sync completed: {checked} checked, {changed} changed, {errors} errors"
    )
    return {
        "total_checked": checked,
        "total_changed": changed,
        "total_errors": errors,
    }


def _fetch_mock_price(source: str, product_id: str) -> float:
    """
    Generate a mock current price for a supplier product.

    Uses a seeded random generator to produce small price fluctuations
    from a base price, simulating real supplier price changes.

    Args:
        source: Supplier platform identifier.
        product_id: Product ID on the supplier.

    Returns:
        Mock current price as a float.
    """
    seed_str = f"{source}_{product_id}_{datetime.now(UTC).strftime('%Y%m%d%H')}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    # Base price from product ID
    base_seed = int(hashlib.md5(f"{source}_{product_id}".encode()).hexdigest()[:8], 16)
    base_rng = random.Random(base_seed)
    base_price = round(base_rng.uniform(5.99, 149.99), 2)

    # Apply small fluctuation (+-10%)
    fluctuation = rng.uniform(-0.10, 0.10)
    return round(base_price * (1 + fluctuation), 2)
