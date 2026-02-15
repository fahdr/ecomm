"""
AI-driven suggestions service for AdScale.

Provides intelligent ad copy optimization and campaign improvement
suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``optimize_ad`` for targeted
    ad copy optimization, and ``get_ai_suggestions`` for general ad
    campaign strategy advice.

For Project Managers:
    AI ad optimization helps merchants improve their ad performance
    with better copy, targeting, and creative strategies. Each call
    consumes LLM tokens billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test ad optimization with valid and invalid ad_id values.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Optimize your ad campaigns with AI-powered copy improvements and
    targeting suggestions from the AdScale dashboard.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def optimize_ad(db: AsyncSession, user_id: str, ad_id: str) -> dict:
    """Optimize ad copy and targeting for a specific ad.

    Analyzes the ad and provides specific improvements for copy,
    headlines, call-to-action, and audience targeting.

    Args:
        db: Async database session for querying ad data.
        user_id: The authenticated user's UUID string.
        ad_id: UUID string of the ad to optimize.

    Returns:
        Dict containing:
            - optimizations: List of ad optimization suggestions.
            - ad_id: The analyzed ad ID.
            - generated_at: ISO timestamp of when optimizations were generated.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Optimize the ad creative (ID: {ad_id}). Provide improvements "
            "for: headline variations (3 options), body copy (concise, "
            "benefit-focused), call-to-action text, target audience "
            "refinement, and A/B test suggestions. Return JSON with an "
            "'optimizations' array of objects, each with 'element' "
            "(headline/body/cta/targeting), 'current_assessment', "
            "'improvement', and 'expected_lift' (percentage)."
        ),
        system=(
            "You are an expert paid advertising strategist specializing "
            "in e-commerce ad campaigns across Google, Facebook, and "
            "Instagram. You optimize ad creative for maximum ROAS. "
            "Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="ad_optimization",
        max_tokens=2000,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"optimizations": [result.get("content", "No optimizations available.")]}

    return {
        "optimizations": parsed.get("optimizations", []),
        "ad_id": ad_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Suggest ad campaign improvements and strategy.

    Provides actionable recommendations for improving ad performance,
    budget allocation, and creative strategy.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of ad improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable suggestions to improve paid "
            "advertising campaigns for an e-commerce store. Cover: "
            "budget optimization, audience targeting refinement, "
            "creative best practices, retargeting strategies, and "
            "cross-platform campaign coordination. Return JSON with "
            "a 'suggestions' array of objects, each with 'title', "
            "'description', and 'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert digital advertising strategist for "
            "e-commerce businesses. You help merchants maximize their "
            "ad spend with data-driven strategies. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="ad_suggestions",
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
