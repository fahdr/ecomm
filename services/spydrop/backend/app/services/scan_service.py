"""
Scan service — mock competitor store scanning and product change detection.

Simulates scanning a competitor's store by generating random product
additions, removals, and price changes. In production, this would be
replaced with actual web scraping or API integration logic.

For Developers:
    The `run_scan` function is the main entry point. It creates a
    ScanResult record and simulates product changes. The mock data
    uses realistic product names, prices, and image URLs.

    The scan flow:
    1. Load competitor and existing products
    2. Randomly add new products (0-3)
    3. Randomly remove existing products (0-1)
    4. Randomly change prices on existing products (0-2)
    5. Create ScanResult with counts
    6. Update competitor.last_scanned and product_count

For QA Engineers:
    Test scan triggering via POST /api/v1/scans/{competitor_id}/trigger.
    Verify scan results contain correct counts. Check that products are
    actually created/modified in the database after a scan.

For Project Managers:
    Scans are currently mock data for demo purposes. In production,
    this module would integrate with real scraping infrastructure.

For End Users:
    Trigger scans to check competitors for changes. Each scan discovers
    new products, price changes, and removed items.
"""

import random
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct
from app.models.scan import ScanResult

# Mock product name parts for generating realistic product names
_ADJECTIVES = [
    "Premium", "Deluxe", "Ultra", "Pro", "Essential", "Classic",
    "Modern", "Vintage", "Eco", "Smart", "Wireless", "Portable",
]
_NOUNS = [
    "Widget", "Gadget", "Device", "Tool", "Kit", "Set",
    "System", "Pack", "Bundle", "Station", "Hub", "Module",
]
_CATEGORIES = [
    "Home", "Kitchen", "Office", "Outdoor", "Fitness", "Tech",
    "Beauty", "Garden", "Auto", "Travel", "Pet", "Sports",
]


def _generate_product_name() -> str:
    """
    Generate a realistic mock product name.

    Returns:
        A string like 'Premium Kitchen Widget Pro'.
    """
    adj = random.choice(_ADJECTIVES)
    cat = random.choice(_CATEGORIES)
    noun = random.choice(_NOUNS)
    return f"{adj} {cat} {noun}"


def _generate_price() -> float:
    """
    Generate a realistic mock price between $5 and $200.

    Returns:
        A float price rounded to 2 decimal places.
    """
    return round(random.uniform(5.0, 199.99), 2)


def _generate_image_url() -> str:
    """
    Generate a placeholder image URL.

    Returns:
        A URL to a placeholder image service.
    """
    size = random.choice([200, 300, 400])
    return f"https://picsum.photos/{size}/{size}?random={random.randint(1, 10000)}"


async def run_scan(
    db: AsyncSession, competitor_id: uuid.UUID
) -> ScanResult:
    """
    Simulate scanning a competitor store for product changes.

    Generates mock product additions, removals, and price changes.
    Creates a ScanResult summarizing the changes and updates the
    competitor's last_scanned timestamp and product_count.

    Args:
        db: Async database session.
        competitor_id: The competitor's UUID to scan.

    Returns:
        The created ScanResult record.

    Raises:
        ValueError: If the competitor is not found.
    """
    start_time = time.time()

    # Load competitor
    result = await db.execute(
        select(Competitor).where(Competitor.id == competitor_id)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise ValueError("Competitor not found")

    # Load existing active products
    prod_result = await db.execute(
        select(CompetitorProduct).where(
            CompetitorProduct.competitor_id == competitor_id,
            CompetitorProduct.status == "active",
        )
    )
    existing_products = list(prod_result.scalars().all())

    now = datetime.now(UTC)
    now_str = now.strftime("%Y-%m-%d")
    new_count = 0
    removed_count = 0
    price_change_count = 0

    # 1. Add new products (0-3)
    num_new = random.randint(0, 3)
    for _ in range(num_new):
        name = _generate_product_name()
        price = _generate_price()
        product = CompetitorProduct(
            competitor_id=competitor_id,
            title=name,
            url=f"{competitor.url}/products/{name.lower().replace(' ', '-')}",
            image_url=_generate_image_url(),
            price=price,
            currency="USD",
            first_seen=now,
            last_seen=now,
            price_history=[{"date": now_str, "price": price}],
            status="active",
        )
        db.add(product)
        new_count += 1

    # 2. Mark some products as removed (0-1, only if products exist)
    if existing_products and random.random() < 0.3:
        num_remove = min(1, len(existing_products))
        to_remove = random.sample(existing_products, num_remove)
        for product in to_remove:
            product.status = "removed"
            product.last_seen = now
            removed_count += 1

    # 3. Change prices on existing active products (0-2)
    active_products = [p for p in existing_products if p.status == "active"]
    if active_products:
        num_changes = min(random.randint(0, 2), len(active_products))
        to_change = random.sample(active_products, num_changes)
        for product in to_change:
            old_price = product.price or 0.0
            # Change by -30% to +20%
            change_pct = random.uniform(-0.30, 0.20)
            new_price = round(max(1.0, old_price * (1 + change_pct)), 2)
            product.price = new_price
            product.last_seen = now

            # Append to price history
            history = list(product.price_history) if product.price_history else []
            history.append({"date": now_str, "price": new_price})
            product.price_history = history

            price_change_count += 1

    # Update all remaining active products' last_seen
    for product in active_products:
        if product.status == "active":
            product.last_seen = now

    # Calculate scan duration
    duration = round(time.time() - start_time, 2)

    # Create scan result
    scan_result = ScanResult(
        competitor_id=competitor_id,
        new_products_count=new_count,
        removed_products_count=removed_count,
        price_changes_count=price_change_count,
        scanned_at=now,
        duration_seconds=duration,
    )
    db.add(scan_result)

    # Update competitor
    competitor.last_scanned = now
    prod_count_result = await db.execute(
        select(func.count(CompetitorProduct.id)).where(
            CompetitorProduct.competitor_id == competitor_id,
            CompetitorProduct.status == "active",
        )
    )
    # Account for newly added products (not yet flushed)
    competitor.product_count = prod_count_result.scalar_one() + new_count

    await db.flush()

    return scan_result


async def list_scan_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    competitor_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ScanResult], int]:
    """
    List scan results for a user's competitors with pagination.

    Optionally filter by a specific competitor. Results are ordered
    by scan time (most recent first).

    Args:
        db: Async database session.
        user_id: The user's UUID.
        competitor_id: Optional competitor filter.
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Tuple of (list of ScanResult records, total count).
    """
    # Get user's competitor IDs
    comp_result = await db.execute(
        select(Competitor.id).where(Competitor.user_id == user_id)
    )
    competitor_ids = [row[0] for row in comp_result.all()]

    if not competitor_ids:
        return [], 0

    # Build filter
    base_filter = ScanResult.competitor_id.in_(competitor_ids)
    if competitor_id:
        base_filter = base_filter & (ScanResult.competitor_id == competitor_id)

    # Count
    count_result = await db.execute(
        select(func.count(ScanResult.id)).where(base_filter)
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ScanResult)
        .where(base_filter)
        .order_by(ScanResult.scanned_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    scans = list(result.scalars().all())

    return scans, total
