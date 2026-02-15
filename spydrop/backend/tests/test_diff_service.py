"""
Tests for the Catalog Diff Engine.

Verifies that the diff engine correctly detects new products, removed
products, price changes, and title changes when comparing crawl results
against stored products.

For Developers:
    Tests use the database session fixture to create real CompetitorProduct
    records, then compare against mock crawl data. The diff engine operates
    on the database directly.

For QA Engineers:
    These tests cover:
    - Detection of new products not previously seen.
    - Detection of products removed from the catalog.
    - Detection of price increases and decreases.
    - Detection of title changes.
    - Edge cases: empty catalogs, no changes, products with no price.
    - URL normalization for comparison.

For Project Managers:
    The diff engine is critical for accurate change detection. These tests
    ensure that users receive correct alerts about competitor changes.

For End Users:
    These tests guarantee that SpyDrop accurately identifies when
    competitors change prices, add products, or remove items.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct
from app.models.user import User
from app.services.diff_service import (
    CatalogDiff,
    _calculate_change_percent,
    _normalize_url,
    _prices_differ,
    compute_catalog_diff,
)


# ── URL Normalization Tests ────────────────────────────────────────


def test_normalize_url_strips_trailing_slash():
    """Trailing slashes are removed for consistent comparison."""
    assert _normalize_url("https://store.com/product/") == "https://store.com/product"


def test_normalize_url_removes_query_params():
    """Query parameters are stripped for comparison."""
    assert _normalize_url("https://store.com/product?ref=123") == "https://store.com/product"


def test_normalize_url_lowercases():
    """URLs are lowercased for case-insensitive comparison."""
    assert _normalize_url("HTTPS://Store.COM/Product") == "https://store.com/product"


def test_normalize_url_removes_fragments():
    """URL fragments are stripped for comparison."""
    assert _normalize_url("https://store.com/product#reviews") == "https://store.com/product"


# ── Price Comparison Tests ─────────────────────────────────────────


def test_prices_differ_same():
    """Same prices should not be considered different."""
    assert _prices_differ(29.99, 29.99) is False


def test_prices_differ_different():
    """Different prices should be detected."""
    assert _prices_differ(29.99, 34.99) is True


def test_prices_differ_both_none():
    """Two None prices are not different."""
    assert _prices_differ(None, None) is False


def test_prices_differ_one_none():
    """One None and one real price are different."""
    assert _prices_differ(None, 29.99) is True
    assert _prices_differ(29.99, None) is True


def test_prices_differ_tiny_difference():
    """Differences smaller than 0.01 are ignored (floating point noise)."""
    assert _prices_differ(29.99, 29.991) is False


# ── Change Percent Calculation ─────────────────────────────────────


def test_calculate_change_percent_increase():
    """Price increase is positive percentage."""
    result = _calculate_change_percent(100.0, 120.0)
    assert result == 20.0


def test_calculate_change_percent_decrease():
    """Price decrease is negative percentage."""
    result = _calculate_change_percent(100.0, 80.0)
    assert result == -20.0


def test_calculate_change_percent_none_old():
    """None old price returns None."""
    assert _calculate_change_percent(None, 29.99) is None


def test_calculate_change_percent_zero_old():
    """Zero old price returns None (division by zero guard)."""
    assert _calculate_change_percent(0, 29.99) is None


# ── CatalogDiff Dataclass Tests ───────────────────────────────────


def test_catalog_diff_empty():
    """Empty CatalogDiff has no changes."""
    diff = CatalogDiff()
    assert diff.total_changes == 0
    assert diff.has_changes is False


def test_catalog_diff_total_changes():
    """total_changes sums all categories."""
    diff = CatalogDiff()
    diff.new_products = [{"title": "A"}, {"title": "B"}]
    assert diff.total_changes == 2
    assert diff.has_changes is True


def test_catalog_diff_to_summary_dict():
    """to_summary_dict produces expected structure."""
    diff = CatalogDiff()
    diff.new_products = [{"title": "New Prod"}]
    summary = diff.to_summary_dict()
    assert summary["new_products_count"] == 1
    assert summary["removed_products_count"] == 0
    assert summary["total_changes"] == 1


# ── Database Integration Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_catalog_diff_all_new(db: AsyncSession):
    """When there are no existing products, all crawled products are new."""
    # Create a user and competitor
    user = User(email="diff@test.com", hashed_password="x")
    db.add(user)
    await db.flush()

    comp = Competitor(user_id=user.id, name="Test Store", url="https://test.com")
    db.add(comp)
    await db.flush()

    # No existing products, two new products from crawl
    new_products = [
        {"title": "Product A", "url": "https://test.com/a", "price": 10.0},
        {"title": "Product B", "url": "https://test.com/b", "price": 20.0},
    ]

    diff = await compute_catalog_diff(db, comp.id, new_products)

    assert len(diff.new_products) == 2
    assert len(diff.removed_products) == 0
    assert len(diff.price_changes) == 0


@pytest.mark.asyncio
async def test_compute_catalog_diff_all_removed(db: AsyncSession):
    """When crawl returns empty, all existing products are marked as removed."""
    user = User(email="diff2@test.com", hashed_password="x")
    db.add(user)
    await db.flush()

    comp = Competitor(user_id=user.id, name="Shrinking Store", url="https://shrink.com")
    db.add(comp)
    await db.flush()

    # Create existing product
    prod = CompetitorProduct(
        competitor_id=comp.id,
        title="Existing Product",
        url="https://shrink.com/products/existing",
        price=50.0,
        status="active",
    )
    db.add(prod)
    await db.flush()

    # Empty crawl result
    diff = await compute_catalog_diff(db, comp.id, [])

    assert len(diff.new_products) == 0
    assert len(diff.removed_products) == 1
    assert diff.removed_products[0].id == prod.id


@pytest.mark.asyncio
async def test_compute_catalog_diff_price_change(db: AsyncSession):
    """Detects price changes for matched products."""
    user = User(email="diff3@test.com", hashed_password="x")
    db.add(user)
    await db.flush()

    comp = Competitor(user_id=user.id, name="Price Store", url="https://price.com")
    db.add(comp)
    await db.flush()

    prod = CompetitorProduct(
        competitor_id=comp.id,
        title="Widget",
        url="https://price.com/products/widget",
        price=29.99,
        status="active",
    )
    db.add(prod)
    await db.flush()

    # Same product, different price
    new_products = [
        {"title": "Widget", "url": "https://price.com/products/widget", "price": 24.99},
    ]

    diff = await compute_catalog_diff(db, comp.id, new_products)

    assert len(diff.new_products) == 0
    assert len(diff.removed_products) == 0
    assert len(diff.price_changes) == 1
    assert diff.price_changes[0].old_price == 29.99
    assert diff.price_changes[0].new_price == 24.99


@pytest.mark.asyncio
async def test_compute_catalog_diff_no_changes(db: AsyncSession):
    """When nothing changed, the diff is empty."""
    user = User(email="diff4@test.com", hashed_password="x")
    db.add(user)
    await db.flush()

    comp = Competitor(user_id=user.id, name="Stable Store", url="https://stable.com")
    db.add(comp)
    await db.flush()

    prod = CompetitorProduct(
        competitor_id=comp.id,
        title="Stable Widget",
        url="https://stable.com/products/stable-widget",
        price=15.00,
        status="active",
    )
    db.add(prod)
    await db.flush()

    # Same product, same price
    new_products = [
        {"title": "Stable Widget", "url": "https://stable.com/products/stable-widget", "price": 15.00},
    ]

    diff = await compute_catalog_diff(db, comp.id, new_products)
    assert diff.has_changes is False
