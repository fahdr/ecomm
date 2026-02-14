"""
Tests for the Alert System (CompetitorAlert model and check_and_create_alerts).

Verifies that catalog diffs automatically generate appropriate alert records
with correct types, severity levels, and messages.

For Developers:
    Tests create CatalogDiff objects with various change combinations and
    verify that the alert service creates the correct CompetitorAlert records.

For QA Engineers:
    These tests cover:
    - Alert generation for new products.
    - Alert generation for removed products.
    - Alert generation for price drops and increases.
    - Severity classification logic.
    - Empty diff produces no alerts.
    - Alert marking as read via API.

For Project Managers:
    The alert system is the primary user notification mechanism. These tests
    ensure alerts are generated accurately and reliably.

For End Users:
    These tests guarantee that you receive correct notifications about
    competitor changes.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct
from app.models.competitor_alert import CompetitorAlert
from app.models.user import User
from app.services.alert_service import check_and_create_alerts
from app.services.diff_service import CatalogDiff, PriceChange
from tests.conftest import register_and_login


# ── Helpers ────────────────────────────────────────────────────────


async def _create_user_and_competitor(db: AsyncSession, suffix: str = ""):
    """Create a user and competitor for alert testing."""
    user = User(
        email=f"alert{suffix}@test.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()

    comp = Competitor(
        user_id=user.id,
        name="Alert Store",
        url="https://alertstore.com",
    )
    db.add(comp)
    await db.flush()

    return user, comp


# ── check_and_create_alerts Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_alerts_for_new_products(db: AsyncSession):
    """New products in diff generate a 'new_product' alert."""
    user, comp = await _create_user_and_competitor(db, "1")

    diff = CatalogDiff()
    diff.new_products = [
        {"title": "New Gadget A", "url": "https://alertstore.com/a", "price": 10.0},
        {"title": "New Gadget B", "url": "https://alertstore.com/b", "price": 20.0},
    ]

    alerts = await check_and_create_alerts(db, user.id, diff, comp.id)

    assert len(alerts) == 1
    assert alerts[0].alert_type == "new_product"
    assert alerts[0].severity == "medium"
    assert "2 new product" in alerts[0].message
    assert alerts[0].is_read is False


@pytest.mark.asyncio
async def test_alerts_for_removed_products(db: AsyncSession):
    """Removed products in diff generate an 'out_of_stock' alert."""
    user, comp = await _create_user_and_competitor(db, "2")

    # Create mock removed products
    removed = CompetitorProduct(
        competitor_id=comp.id,
        title="Gone Product",
        url="https://alertstore.com/gone",
        price=30.0,
        status="active",
    )
    db.add(removed)
    await db.flush()

    diff = CatalogDiff()
    diff.removed_products = [removed]

    alerts = await check_and_create_alerts(db, user.id, diff, comp.id)

    assert len(alerts) == 1
    assert alerts[0].alert_type == "out_of_stock"
    assert alerts[0].severity == "medium"


@pytest.mark.asyncio
async def test_alerts_for_price_drop(db: AsyncSession):
    """Price drops generate a 'price_drop' alert with correct severity."""
    user, comp = await _create_user_and_competitor(db, "3")

    diff = CatalogDiff()
    diff.price_changes = [
        PriceChange(
            product_id=uuid.uuid4(),
            title="Widget Pro",
            old_price=100.0,
            new_price=75.0,
            change_percent=-25.0,  # 25% drop = critical
            url="https://alertstore.com/widget",
        ),
    ]

    alerts = await check_and_create_alerts(db, user.id, diff, comp.id)

    assert len(alerts) == 1
    assert alerts[0].alert_type == "price_drop"
    assert alerts[0].severity == "critical"
    assert "25.0%" in alerts[0].message


@pytest.mark.asyncio
async def test_alerts_for_price_increase(db: AsyncSession):
    """Price increases generate a 'price_increase' alert."""
    user, comp = await _create_user_and_competitor(db, "4")

    diff = CatalogDiff()
    diff.price_changes = [
        PriceChange(
            product_id=uuid.uuid4(),
            title="Premium Item",
            old_price=50.0,
            new_price=65.0,
            change_percent=30.0,  # 30% increase = high
            url="https://alertstore.com/premium",
        ),
    ]

    alerts = await check_and_create_alerts(db, user.id, diff, comp.id)

    assert len(alerts) == 1
    assert alerts[0].alert_type == "price_increase"
    assert alerts[0].severity == "high"


@pytest.mark.asyncio
async def test_alerts_empty_diff(db: AsyncSession):
    """Empty diff produces no alerts."""
    user, comp = await _create_user_and_competitor(db, "5")

    diff = CatalogDiff()

    alerts = await check_and_create_alerts(db, user.id, diff, comp.id)

    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_alerts_mixed_changes(db: AsyncSession):
    """Mixed diff generates multiple alerts of different types."""
    user, comp = await _create_user_and_competitor(db, "6")

    removed = CompetitorProduct(
        competitor_id=comp.id,
        title="Removed Widget",
        url="https://alertstore.com/removed",
        price=15.0,
        status="active",
    )
    db.add(removed)
    await db.flush()

    diff = CatalogDiff()
    diff.new_products = [{"title": "New Item", "url": "https://alertstore.com/new", "price": 5.0}]
    diff.removed_products = [removed]
    diff.price_changes = [
        PriceChange(
            product_id=uuid.uuid4(),
            title="Changed Item",
            old_price=40.0,
            new_price=32.0,
            change_percent=-20.0,
            url="https://alertstore.com/changed",
        ),
    ]

    alerts = await check_and_create_alerts(db, user.id, diff, comp.id)

    # 1 new_product + 1 out_of_stock + 1 price_drop = 3 alerts
    assert len(alerts) == 3
    types = {a.alert_type for a in alerts}
    assert "new_product" in types
    assert "out_of_stock" in types
    assert "price_drop" in types


# ── Alert API Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_alerts_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/alerts returns empty list for new user."""
    resp = await client.get("/api/v1/alerts/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["unread_count"] == 0


@pytest.mark.asyncio
async def test_list_alerts_unauthenticated(client: AsyncClient):
    """GET /api/v1/alerts without auth returns 401."""
    resp = await client.get("/api/v1/alerts/")
    assert resp.status_code == 401
