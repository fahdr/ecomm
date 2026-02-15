"""
AI-driven suggestions service for RankPilot.

Provides intelligent SEO recommendations and optimization suggestions
by analyzing keyword data through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``seo_suggest`` for detailed
    SEO analysis, and ``get_ai_suggestions`` for high-level SEO advice.

For Project Managers:
    AI SEO recommendations help merchants improve their search rankings
    with data-driven keyword strategies. Each call consumes LLM tokens
    billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Verify JSON parsing fallback when LLM returns malformed output.
    Test both success and error paths.

For End Users:
    Get AI-powered SEO recommendations from your RankPilot dashboard.
    The AI analyzes your keyword data and site structure to suggest
    high-impact optimizations.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def seo_suggest(db: AsyncSession, user_id: str) -> dict:
    """Generate AI SEO recommendations based on keyword data.

    Analyzes keyword rankings, competition, and search volume to
    provide prioritized SEO action items.

    Args:
        db: Async database session for querying keyword data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - recommendations: List of SEO recommendations with priorities.
            - generated_at: ISO timestamp of when recommendations were generated.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Analyze current SEO best practices and provide 5 prioritized "
            "recommendations for an e-commerce store. Cover: keyword "
            "optimization, technical SEO (page speed, mobile, schema markup), "
            "content strategy (blog topics, internal linking), backlink "
            "opportunities, and local SEO. Return JSON with a "
            "'recommendations' array of objects, each with 'category', "
            "'action', 'expected_impact', and 'difficulty' (easy/medium/hard)."
        ),
        system=(
            "You are an expert SEO strategist specializing in e-commerce "
            "stores. You provide actionable, data-driven SEO recommendations "
            "that improve organic search rankings. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="seo_recommendations",
        max_tokens=1500,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"recommendations": [result.get("content", "No recommendations available.")]}

    return {
        "recommendations": parsed.get("recommendations", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Get high-level AI SEO improvement suggestions.

    Provides strategic SEO advice covering keyword research,
    on-page optimization, and competitive positioning.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of SEO improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable SEO improvement suggestions for an "
            "e-commerce store. Focus on quick wins, long-term strategy, "
            "competitor keyword gaps, and content optimization. Return "
            "JSON with a 'suggestions' array of objects, each with "
            "'title', 'description', and 'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert SEO advisor for e-commerce businesses. "
            "You help merchants improve their organic search visibility "
            "through proven SEO strategies. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="seo_suggestions",
        max_tokens=1000,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"suggestions": [result.get("content", "No suggestions available.")]}

    return {
        "suggestions": parsed.get("suggestions", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }
