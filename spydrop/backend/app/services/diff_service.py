"""
Catalog Diff Engine for SpyDrop.

Compares new crawl results against stored products to detect changes:
new products, removed products, price changes, and title changes.

For Developers:
    The main entry point is ``compute_catalog_diff(db, competitor_id, new_products)``.
    It loads existing products from the database, matches them against the
    new crawl results by URL (primary) or title similarity (fallback), and
    categorizes all changes into a ``CatalogDiff`` dataclass.

    The diff result feeds into the alert system and scan result recording.

For QA Engineers:
    Test with various scenarios:
    - All new products (empty existing catalog).
    - All removed products (empty new crawl).
    - Mixed changes (some new, some removed, some price/title changes).
    - Products with same URL but different prices or titles.
    - Edge cases: None prices, empty titles, duplicate URLs.

For Project Managers:
    The diff engine is the intelligence layer between crawling and alerting.
    It determines exactly what changed between scans, enabling precise
    alerts and actionable insights for users.

For End Users:
    SpyDrop automatically detects when competitors change prices, add
    new products, or remove items. The diff engine powers this detection.
"""

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import CompetitorProduct

logger = logging.getLogger(__name__)


@dataclass
class PriceChange:
    """
    Record of a price change for a specific product.

    Attributes:
        product_id: UUID of the existing CompetitorProduct.
        title: Product title for display.
        old_price: Previous price (may be None).
        new_price: New price (may be None).
        change_percent: Percentage change (positive = increase, negative = decrease).
        url: Product page URL.
    """

    product_id: uuid.UUID
    title: str
    old_price: float | None
    new_price: float | None
    change_percent: float | None
    url: str


@dataclass
class OtherChange:
    """
    Record of a non-price change for a specific product.

    Attributes:
        product_id: UUID of the existing CompetitorProduct.
        field: The field that changed (e.g., 'title').
        old_value: Previous field value.
        new_value: New field value.
        url: Product page URL.
    """

    product_id: uuid.UUID
    field: str
    old_value: str
    new_value: str
    url: str


@dataclass
class CatalogDiff:
    """
    Result of comparing a new crawl against the stored product catalog.

    Summarizes all changes detected between the existing database state
    and the latest crawl results.

    Attributes:
        new_products: List of product dicts not previously seen.
        removed_products: List of CompetitorProduct records no longer in the crawl.
        price_changes: List of PriceChange records for products with different prices.
        other_changes: List of OtherChange records for non-price field changes.
    """

    new_products: list[dict] = field(default_factory=list)
    removed_products: list[CompetitorProduct] = field(default_factory=list)
    price_changes: list[PriceChange] = field(default_factory=list)
    other_changes: list[OtherChange] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        """
        Total number of changes detected across all categories.

        Returns:
            Integer sum of all change categories.
        """
        return (
            len(self.new_products)
            + len(self.removed_products)
            + len(self.price_changes)
            + len(self.other_changes)
        )

    @property
    def has_changes(self) -> bool:
        """
        Whether any changes were detected.

        Returns:
            True if at least one change was found.
        """
        return self.total_changes > 0

    def to_summary_dict(self) -> dict:
        """
        Convert the diff to a summary dict suitable for API responses.

        Returns:
            Dict with counts and details of each change category.
        """
        return {
            "new_products_count": len(self.new_products),
            "removed_products_count": len(self.removed_products),
            "price_changes_count": len(self.price_changes),
            "other_changes_count": len(self.other_changes),
            "total_changes": self.total_changes,
            "price_changes": [
                {
                    "product_id": str(pc.product_id),
                    "title": pc.title,
                    "old_price": pc.old_price,
                    "new_price": pc.new_price,
                    "change_percent": pc.change_percent,
                }
                for pc in self.price_changes
            ],
        }


async def compute_catalog_diff(
    db: AsyncSession,
    competitor_id: uuid.UUID,
    new_products: list[dict],
) -> CatalogDiff:
    """
    Compare new crawl results against stored products to detect all changes.

    Matches products by URL (primary key for comparison). Products in the
    new crawl that don't match any existing product by URL are considered
    new. Existing products not found in the new crawl are considered removed.
    Matched products are checked for price and title changes.

    Args:
        db: Async database session.
        competitor_id: UUID of the competitor whose products are being compared.
        new_products: List of product dicts from the latest crawl, each containing
            at minimum 'title', 'url', and optionally 'price'.

    Returns:
        CatalogDiff dataclass summarizing all detected changes.
    """
    diff = CatalogDiff()

    # Load existing active products for this competitor
    result = await db.execute(
        select(CompetitorProduct).where(
            CompetitorProduct.competitor_id == competitor_id,
            CompetitorProduct.status == "active",
        )
    )
    existing_products = list(result.scalars().all())

    # Build lookup by URL for fast matching
    existing_by_url: dict[str, CompetitorProduct] = {}
    for product in existing_products:
        normalized_url = _normalize_url(product.url)
        existing_by_url[normalized_url] = product

    # Track which existing products were matched
    matched_existing_ids: set[uuid.UUID] = set()

    # Process each product from the new crawl
    for new_prod in new_products:
        new_url = _normalize_url(new_prod.get("url", ""))
        new_title = new_prod.get("title", "").strip()
        new_price = new_prod.get("price")

        if not new_url and not new_title:
            continue  # Skip products with no identifiable data

        # Try to match by URL first
        existing = existing_by_url.get(new_url)

        if existing:
            matched_existing_ids.add(existing.id)

            # Check for price changes
            if _prices_differ(existing.price, new_price):
                change_pct = _calculate_change_percent(existing.price, new_price)
                diff.price_changes.append(
                    PriceChange(
                        product_id=existing.id,
                        title=existing.title,
                        old_price=existing.price,
                        new_price=new_price,
                        change_percent=change_pct,
                        url=existing.url,
                    )
                )

            # Check for title changes
            if new_title and new_title != existing.title:
                diff.other_changes.append(
                    OtherChange(
                        product_id=existing.id,
                        field="title",
                        old_value=existing.title,
                        new_value=new_title,
                        url=existing.url,
                    )
                )
        else:
            # New product not seen before
            diff.new_products.append(new_prod)

    # Find removed products (existing but not in new crawl)
    for product in existing_products:
        if product.id not in matched_existing_ids:
            diff.removed_products.append(product)

    logger.info(
        "Catalog diff for competitor %s: %d new, %d removed, %d price changes, %d other changes",
        competitor_id,
        len(diff.new_products),
        len(diff.removed_products),
        len(diff.price_changes),
        len(diff.other_changes),
    )

    return diff


def _normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison by removing trailing slashes,
    query parameters, and fragments.

    Args:
        url: The URL to normalize.

    Returns:
        Lowercase normalized URL string.
    """
    url = url.strip().lower()
    # Remove query params and fragments
    url = url.split("?")[0].split("#")[0]
    # Remove trailing slash
    url = url.rstrip("/")
    return url


def _prices_differ(
    old_price: float | None, new_price: float | None
) -> bool:
    """
    Determine if two prices are meaningfully different.

    Treats None as a distinct value (no price vs. a price is a change).
    Uses a small epsilon for floating-point comparison.

    Args:
        old_price: Previous price (may be None).
        new_price: New price (may be None).

    Returns:
        True if the prices differ meaningfully.
    """
    if old_price is None and new_price is None:
        return False
    if old_price is None or new_price is None:
        return True
    return abs(old_price - new_price) > 0.01


def _calculate_change_percent(
    old_price: float | None, new_price: float | None
) -> float | None:
    """
    Calculate the percentage change between two prices.

    Args:
        old_price: Previous price.
        new_price: New price.

    Returns:
        Percentage change (positive = increase, negative = decrease),
        or None if the old price is zero or None.
    """
    if old_price is None or new_price is None or old_price == 0:
        return None
    return round(((new_price - old_price) / old_price) * 100, 2)
