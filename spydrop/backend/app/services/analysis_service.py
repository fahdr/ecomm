"""
LLM-powered Competitive Analysis service for SpyDrop.

Uses the centralized LLM Gateway to generate market positioning analysis,
competitive advantages, market gaps, and pricing strategy recommendations
for a specific competitor.

For Developers:
    The main entry point is ``analyze_competitor(db, user_id, competitor_id)``.
    It loads the competitor's data (products, price trends, scan history),
    constructs a detailed prompt, and sends it to the LLM Gateway.

    The analysis is structured into four sections:
    1. Market Positioning — where the competitor sits in the market.
    2. Competitive Advantages — what they do well.
    3. Market Gaps — opportunities they are missing.
    4. Pricing Strategy — recommendations for competitive pricing.

For QA Engineers:
    Mock ``call_llm`` in tests to verify the analysis endpoint returns
    correctly structured data. Test with competitors that have varying
    numbers of products (0, 1, many) and price histories.

For Project Managers:
    Competitive analysis is a high-value, differentiated feature. It
    transforms raw product data into actionable business intelligence,
    making SpyDrop more than just a price tracker.

For End Users:
    Get AI-powered insights about your competitors' strategies.
    Understand their strengths, weaknesses, and pricing patterns
    to make better decisions for your own store.
"""

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct

logger = logging.getLogger(__name__)


async def analyze_competitor(
    db: AsyncSession,
    user_id: uuid.UUID,
    competitor_id: uuid.UUID,
) -> dict:
    """
    Generate a comprehensive competitive analysis for a competitor using LLM.

    Loads the competitor's product catalog, price data, and scan history,
    then asks the LLM to produce market positioning analysis, competitive
    advantages, market gaps, and pricing recommendations.

    Args:
        db: Async database session.
        user_id: The requesting user's UUID (for LLM usage tracking).
        competitor_id: The competitor's UUID to analyze.

    Returns:
        Dict with analysis results:
            - competitor_name (str): Name of the analyzed competitor.
            - competitor_url (str): Competitor's store URL.
            - product_count (int): Number of tracked products.
            - analysis (dict): Structured analysis with sections:
                - market_positioning (str): Market position assessment.
                - competitive_advantages (list[str]): Identified advantages.
                - market_gaps (list[str]): Identified opportunities.
                - pricing_strategy (list[str]): Pricing recommendations.
            - generated_by (str): Always 'llm_gateway'.

    Raises:
        ValueError: If the competitor is not found or not owned by user.
    """
    from app.services.llm_client import call_llm

    # Load competitor
    result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.user_id == user_id,
        )
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise ValueError("Competitor not found")

    # Load products for context
    prod_result = await db.execute(
        select(CompetitorProduct)
        .where(CompetitorProduct.competitor_id == competitor_id)
        .order_by(CompetitorProduct.price.desc().nulls_last())
        .limit(20)
    )
    products = list(prod_result.scalars().all())

    # Build analysis prompt
    prompt = _build_analysis_prompt(competitor, products)

    system = (
        "You are an expert e-commerce market analyst. Analyze the competitor data "
        "provided and return a structured JSON response with the following fields:\n"
        '- "market_positioning": A paragraph describing the competitor\'s market position.\n'
        '- "competitive_advantages": A list of 3-5 string advantages the competitor has.\n'
        '- "market_gaps": A list of 3-5 string opportunities the competitor is missing.\n'
        '- "pricing_strategy": A list of 3-5 string pricing recommendations.\n'
        "Return ONLY valid JSON, no other text."
    )

    llm_result = await call_llm(
        prompt=prompt,
        system=system,
        user_id=str(user_id),
        task_type="competitive_analysis",
        max_tokens=2000,
        temperature=0.7,
        json_mode=True,
    )

    # Parse LLM response
    analysis = _parse_analysis_response(llm_result, competitor, products)

    return {
        "competitor_name": competitor.name,
        "competitor_url": competitor.url,
        "product_count": len(products),
        "analysis": analysis,
        "generated_by": "llm_gateway",
    }


def _build_analysis_prompt(
    competitor: Competitor,
    products: list[CompetitorProduct],
) -> str:
    """
    Build the analysis prompt from competitor and product data.

    Constructs a detailed context with product names, prices, and
    price history for the LLM to analyze.

    Args:
        competitor: The Competitor record.
        products: List of CompetitorProduct records (up to 20).

    Returns:
        Formatted prompt string with competitor data.
    """
    lines = [
        f"Competitor: {competitor.name}",
        f"URL: {competitor.url}",
        f"Platform: {competitor.platform}",
        f"Status: {competitor.status}",
        f"Total products tracked: {competitor.product_count}",
        "",
        "Product catalog (up to 20 products):",
    ]

    if not products:
        lines.append("  No products tracked yet.")
    else:
        for i, product in enumerate(products, 1):
            price_str = f"${product.price:.2f}" if product.price else "N/A"
            status_str = f" [{product.status}]" if product.status != "active" else ""
            lines.append(f"  {i}. {product.title} — {price_str}{status_str}")

            # Include price history summary
            if product.price_history and isinstance(product.price_history, list):
                history = product.price_history
                if len(history) > 1:
                    first = history[0]
                    last = history[-1]
                    lines.append(
                        f"     Price trend: {first.get('price', '?')} -> {last.get('price', '?')} "
                        f"({first.get('date', '?')} to {last.get('date', '?')})"
                    )

    # Add price statistics
    prices = [p.price for p in products if p.price is not None and p.price > 0]
    if prices:
        lines.extend([
            "",
            "Price statistics:",
            f"  Average price: ${sum(prices) / len(prices):.2f}",
            f"  Min price: ${min(prices):.2f}",
            f"  Max price: ${max(prices):.2f}",
            f"  Price range: ${max(prices) - min(prices):.2f}",
        ])

    return "\n".join(lines)


def _parse_analysis_response(
    llm_result: dict,
    competitor: Competitor,
    products: list[CompetitorProduct],
) -> dict:
    """
    Parse the LLM analysis response into a structured dict.

    Falls back to generating a basic analysis from the raw data if
    the LLM response cannot be parsed as JSON.

    Args:
        llm_result: Response dict from the LLM client.
        competitor: The Competitor record (for fallback).
        products: The product list (for fallback).

    Returns:
        Dict with market_positioning, competitive_advantages,
        market_gaps, and pricing_strategy fields.
    """
    content = llm_result.get("content", "")

    if llm_result.get("error") or not content:
        logger.warning(
            "LLM analysis failed, using fallback: %s", llm_result.get("error", "empty response")
        )
        return _generate_fallback_analysis(competitor, products)

    try:
        analysis = json.loads(content)
        if isinstance(analysis, dict):
            return {
                "market_positioning": analysis.get("market_positioning", "Analysis not available."),
                "competitive_advantages": analysis.get("competitive_advantages", []),
                "market_gaps": analysis.get("market_gaps", []),
                "pricing_strategy": analysis.get("pricing_strategy", []),
            }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse LLM analysis JSON: %s", content[:200])

    return _generate_fallback_analysis(competitor, products)


def _generate_fallback_analysis(
    competitor: Competitor,
    products: list[CompetitorProduct],
) -> dict:
    """
    Generate a basic analysis from raw data when LLM is unavailable.

    Uses simple heuristics based on product count, price range, and
    platform type.

    Args:
        competitor: The Competitor record.
        products: List of CompetitorProduct records.

    Returns:
        Dict with basic analysis sections.
    """
    prices = [p.price for p in products if p.price is not None and p.price > 0]
    avg_price = sum(prices) / len(prices) if prices else 0

    # Determine market segment
    if avg_price > 100:
        segment = "premium"
    elif avg_price > 30:
        segment = "mid-range"
    else:
        segment = "budget"

    return {
        "market_positioning": (
            f"{competitor.name} operates as a {segment} {competitor.platform} store "
            f"with {len(products)} tracked products. Their average price point is "
            f"${avg_price:.2f}, positioning them in the {segment} market segment."
        ),
        "competitive_advantages": [
            f"Established {competitor.platform} presence",
            f"Product catalog of {len(products)} items",
            f"Active in the {segment} price segment",
        ],
        "market_gaps": [
            "Consider expanding price range to reach more customers",
            "Look for underserved product categories",
            "Explore complementary product bundles",
        ],
        "pricing_strategy": [
            f"Target prices {'below' if avg_price > 30 else 'at or slightly above'} "
            f"${avg_price:.2f} to compete effectively",
            "Monitor competitor price changes weekly for quick response",
            "Consider volume discounts to attract bulk buyers",
        ],
    }
