"""
AI-driven features service for the Dropshipping platform.

Provides intelligent product description generation and AI-powered
pricing suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``generate_product_description``
    for AI product copy, and ``suggest_pricing`` for competitive price
    optimization.

For Project Managers:
    AI product features help merchants create compelling product listings
    and optimize pricing for maximum profit and conversion. Each call
    consumes LLM tokens billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test with valid and invalid store_id/product_id combinations.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Generate AI-powered product descriptions and get pricing suggestions
    from your store dashboard. The AI creates compelling copy and
    analyzes market data to recommend optimal prices.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def generate_product_description(
    db: AsyncSession, store_id: str, product_id: str
) -> dict:
    """Generate an AI-powered product description.

    Creates compelling, SEO-optimized product copy including title
    variations, descriptions, bullet points, and meta tags.

    Args:
        db: Async database session for querying product data.
        store_id: UUID string of the store.
        product_id: UUID string of the product.

    Returns:
        Dict containing:
            - description: Generated product description with variants.
            - product_id: The product this description was generated for.
            - store_id: The store the product belongs to.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Generate a compelling product description for product "
            f"(ID: {product_id}) in store (ID: {store_id}). Provide: "
            "title_variants (3 options), short_description (50-100 words), "
            "long_description (200-300 words, HTML-formatted), "
            "bullet_points (5-7 key features), seo_title, "
            "meta_description (under 160 chars), and suggested_tags "
            "(5-8 tags). Return JSON with a 'description' object."
        ),
        system=(
            "You are an expert e-commerce copywriter who creates "
            "compelling, conversion-optimized product descriptions. "
            "Your copy is SEO-friendly, highlights benefits over "
            "features, and includes emotional triggers that drive "
            "purchases. Always return valid JSON."
        ),
        user_id=store_id,
        service_name=settings.service_name,
        task_type="product_description",
        max_tokens=2000,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"description": result.get("content", "No description generated.")}

    return {
        "description": parsed.get("description", parsed),
        "product_id": product_id,
        "store_id": store_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def suggest_pricing(
    db: AsyncSession, store_id: str, product_id: str
) -> dict:
    """Generate AI-powered pricing suggestions for a product.

    Analyzes market positioning and provides pricing strategy
    recommendations with competitive analysis.

    Args:
        db: Async database session for querying product data.
        store_id: UUID string of the store.
        product_id: UUID string of the product.

    Returns:
        Dict containing:
            - pricing: Structured pricing recommendations.
            - product_id: The product analyzed.
            - store_id: The store the product belongs to.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Suggest optimal pricing strategies for product "
            f"(ID: {product_id}) in store (ID: {store_id}). Provide: "
            "recommended_price_range (min/max), pricing_strategy "
            "(penetration/premium/competitive/value), psychological "
            "pricing tips, bundle_suggestions, discount_strategy, "
            "and margin_analysis. Return JSON with a 'pricing' object."
        ),
        system=(
            "You are an expert e-commerce pricing strategist. You "
            "analyze market positioning, competitor pricing, and "
            "consumer psychology to recommend optimal price points "
            "that maximize both conversion and profit margins. "
            "Always return valid JSON."
        ),
        user_id=store_id,
        service_name=settings.service_name,
        task_type="pricing_suggestion",
        max_tokens=1500,
        temperature=0.5,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"pricing": result.get("content", "No pricing suggestions available.")}

    return {
        "pricing": parsed.get("pricing", parsed),
        "product_id": product_id,
        "store_id": store_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }
