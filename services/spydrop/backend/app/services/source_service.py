"""
Source matching service — find potential suppliers for competitor products.

Generates mock supplier matches with confidence scores and margin
calculations. In production, this would integrate with supplier APIs
(AliExpress, DHgate, 1688, etc.) or AI-powered product matching.

For Developers:
    The `find_sources` function generates 1-4 mock supplier matches per
    product with realistic supplier names, URLs, costs, confidence scores,
    and margin calculations. Existing matches for the product are cleared
    before generating new ones.

For QA Engineers:
    Test source finding via POST /api/v1/sources/{product_id}/find.
    Verify confidence scores are between 0 and 1, margins are calculated
    correctly, and existing matches are replaced on re-run.

For Project Managers:
    Source matching is a premium feature (Pro tier and above). It helps
    users identify where competitors source products, enabling them to
    compete by sourcing similar items.

For End Users:
    Find where competitors get their products and see potential profit
    margins. Use this to decide which products are worth selling.
"""

import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import CompetitorProduct
from app.models.source_match import SourceMatch

# Mock supplier data for generating realistic matches
_SUPPLIERS = [
    {"name": "AliExpress", "domain": "aliexpress.com"},
    {"name": "DHgate", "domain": "dhgate.com"},
    {"name": "1688", "domain": "1688.com"},
    {"name": "Made-in-China", "domain": "made-in-china.com"},
    {"name": "Global Sources", "domain": "globalsources.com"},
    {"name": "Alibaba", "domain": "alibaba.com"},
    {"name": "Banggood", "domain": "banggood.com"},
    {"name": "LightInTheBox", "domain": "lightinthebox.com"},
]


async def find_sources(
    db: AsyncSession, product_id: uuid.UUID
) -> list[SourceMatch]:
    """
    Find potential supplier sources for a competitor product.

    Generates mock source matches with realistic supplier data,
    confidence scores, and margin calculations. Existing matches
    for the product are cleared before generating new ones.

    Args:
        db: Async database session.
        product_id: The CompetitorProduct's UUID.

    Returns:
        List of newly created SourceMatch records.

    Raises:
        ValueError: If the product is not found.
    """
    # Load product
    result = await db.execute(
        select(CompetitorProduct).where(CompetitorProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")

    # Clear existing matches
    existing = await db.execute(
        select(SourceMatch).where(
            SourceMatch.competitor_product_id == product_id
        )
    )
    for match in existing.scalars().all():
        await db.delete(match)

    # Generate 1-4 mock matches
    num_matches = random.randint(1, 4)
    selected_suppliers = random.sample(
        _SUPPLIERS, min(num_matches, len(_SUPPLIERS))
    )

    matches: list[SourceMatch] = []
    competitor_price = product.price or 0.0

    for supplier in selected_suppliers:
        # Generate a cost that's 20-70% of the competitor price
        if competitor_price > 0:
            cost_ratio = random.uniform(0.20, 0.70)
            cost = round(competitor_price * cost_ratio, 2)
            margin = round(
                ((competitor_price - cost) / competitor_price) * 100, 1
            )
        else:
            cost = round(random.uniform(2.0, 50.0), 2)
            margin = None

        # Generate confidence score (higher for well-known suppliers)
        base_confidence = random.uniform(0.55, 0.95)
        confidence = round(base_confidence, 2)

        # Generate a plausible product URL slug
        slug = product.title.lower().replace(" ", "-")[:50]
        product_id_str = random.randint(10000, 99999)

        match = SourceMatch(
            competitor_product_id=product.id,
            supplier=supplier["name"],
            supplier_url=(
                f"https://{supplier['domain']}/item/{slug}-{product_id_str}.html"
            ),
            cost=cost,
            currency=product.currency,
            confidence_score=confidence,
            margin_percent=margin,
        )
        db.add(match)
        matches.append(match)

    await db.flush()
    return matches


async def list_source_matches(
    db: AsyncSession,
    product_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[SourceMatch], int]:
    """
    List source matches for a product with pagination.

    Ordered by confidence score (highest first).

    Args:
        db: Async database session.
        product_id: The CompetitorProduct's UUID.
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Tuple of (list of SourceMatch records, total count).
    """
    from sqlalchemy import func as sqlfunc

    count_result = await db.execute(
        select(sqlfunc.count(SourceMatch.id)).where(
            SourceMatch.competitor_product_id == product_id
        )
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(SourceMatch)
        .where(SourceMatch.competitor_product_id == product_id)
        .order_by(SourceMatch.confidence_score.desc())
        .offset(offset)
        .limit(per_page)
    )
    matches = list(result.scalars().all())

    return matches, total
