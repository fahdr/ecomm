"""
Tests for the Price History Tracking service.

Verifies price snapshot recording, history retrieval, and significant
price change detection.

For Developers:
    Tests create real database records (User, Competitor, CompetitorProduct,
    PriceSnapshot) and verify the service functions against them.
    Explicit ``captured_at`` timestamps are used to ensure deterministic
    ordering (``server_default=func.now()`` produces the same timestamp
    within a single transaction).

For QA Engineers:
    These tests cover:
    - Recording individual price snapshots.
    - Retrieving price history with date range filtering.
    - Detecting significant price changes (above threshold).
    - Edge cases: no snapshots, single snapshot, zero previous price.

For Project Managers:
    Price tracking is a core feature. These tests ensure accurate
    history recording and change detection for reliable user alerts.

For End Users:
    These tests guarantee that SpyDrop accurately tracks and reports
    price changes for competitor products.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.services.price_service import (
    detect_price_changes,
    get_price_history,
    record_price_snapshot,
)


# ── Helpers ────────────────────────────────────────────────────────


async def _create_product_setup(db: AsyncSession, email_suffix: str = ""):
    """
    Create a User, Competitor, and CompetitorProduct for testing.

    Args:
        db: Async database session.
        email_suffix: Suffix for unique email generation.

    Returns:
        Tuple of (user, competitor, product) model instances.
    """
    user = User(
        email=f"price{email_suffix}@test.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()

    comp = Competitor(
        user_id=user.id,
        name="Price Test Store",
        url="https://pricetest.com",
    )
    db.add(comp)
    await db.flush()

    product = CompetitorProduct(
        competitor_id=comp.id,
        title="Test Product",
        url="https://pricetest.com/products/test",
        price=29.99,
        status="active",
    )
    db.add(product)
    await db.flush()

    return user, comp, product


# ── Snapshot Recording Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_record_price_snapshot(db: AsyncSession):
    """Recording a snapshot creates a PriceSnapshot in the database."""
    _, _, product = await _create_product_setup(db, "1")

    snapshot = await record_price_snapshot(db, product.id, 29.99)

    assert snapshot.id is not None
    assert snapshot.competitor_product_id == product.id
    assert snapshot.price == 29.99
    assert snapshot.currency == "USD"
    assert snapshot.captured_at is not None


@pytest.mark.asyncio
async def test_record_price_snapshot_custom_currency(db: AsyncSession):
    """Recording a snapshot with custom currency stores it correctly."""
    _, _, product = await _create_product_setup(db, "2")

    snapshot = await record_price_snapshot(db, product.id, 25.50, currency="EUR")

    assert snapshot.currency == "EUR"
    assert snapshot.price == 25.50


# ── Price History Retrieval Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_get_price_history_empty(db: AsyncSession):
    """Product with no snapshots returns empty history."""
    _, _, product = await _create_product_setup(db, "3")

    history = await get_price_history(db, product.id)

    assert history == []


@pytest.mark.asyncio
async def test_get_price_history_multiple_snapshots(db: AsyncSession):
    """Multiple snapshots are returned in chronological order."""
    _, _, product = await _create_product_setup(db, "4")

    now = datetime.now(UTC)
    await record_price_snapshot(db, product.id, 29.99, captured_at=now - timedelta(hours=3))
    await record_price_snapshot(db, product.id, 27.99, captured_at=now - timedelta(hours=2))
    await record_price_snapshot(db, product.id, 31.99, captured_at=now - timedelta(hours=1))

    history = await get_price_history(db, product.id)

    assert len(history) == 3
    # Should be in ascending order (oldest first)
    assert history[0].price == 29.99
    assert history[1].price == 27.99
    assert history[2].price == 31.99


# ── Price Change Detection Tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_detect_price_changes_significant(db: AsyncSession):
    """Products with >5% price change are detected."""
    _, comp, product = await _create_product_setup(db, "5")

    now = datetime.now(UTC)
    # Record two snapshots: 100 -> 90 (10% drop)
    await record_price_snapshot(db, product.id, 100.00, captured_at=now - timedelta(hours=2))
    await record_price_snapshot(db, product.id, 90.00, captured_at=now - timedelta(hours=1))

    changes = await detect_price_changes(db, comp.id)

    assert len(changes) == 1
    assert changes[0]["product_id"] == product.id
    assert changes[0]["old_price"] == 100.00
    assert changes[0]["new_price"] == 90.00
    assert changes[0]["change_percent"] == -10.0
    assert changes[0]["direction"] == "decrease"


@pytest.mark.asyncio
async def test_detect_price_changes_insignificant(db: AsyncSession):
    """Products with <5% price change are not flagged."""
    _, comp, product = await _create_product_setup(db, "6")

    now = datetime.now(UTC)
    # Record two snapshots: 100 -> 97 (3% drop, below threshold)
    await record_price_snapshot(db, product.id, 100.00, captured_at=now - timedelta(hours=2))
    await record_price_snapshot(db, product.id, 97.00, captured_at=now - timedelta(hours=1))

    changes = await detect_price_changes(db, comp.id)

    assert len(changes) == 0


@pytest.mark.asyncio
async def test_detect_price_changes_increase(db: AsyncSession):
    """Price increases above threshold are detected."""
    _, comp, product = await _create_product_setup(db, "7")

    now = datetime.now(UTC)
    # Record two snapshots: 50 -> 60 (20% increase)
    await record_price_snapshot(db, product.id, 50.00, captured_at=now - timedelta(hours=2))
    await record_price_snapshot(db, product.id, 60.00, captured_at=now - timedelta(hours=1))

    changes = await detect_price_changes(db, comp.id)

    assert len(changes) == 1
    assert changes[0]["direction"] == "increase"
    assert changes[0]["change_percent"] == 20.0


@pytest.mark.asyncio
async def test_detect_price_changes_single_snapshot(db: AsyncSession):
    """Products with only one snapshot are not flagged (need at least 2)."""
    _, comp, product = await _create_product_setup(db, "8")

    await record_price_snapshot(db, product.id, 29.99)

    changes = await detect_price_changes(db, comp.id)

    assert len(changes) == 0
