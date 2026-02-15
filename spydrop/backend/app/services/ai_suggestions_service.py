"""
AI-driven suggestions service for SpyDrop.

Provides intelligent competitor analysis and competitive intelligence
suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``analyze_competitor`` for
    detailed competitor insights, and ``get_ai_suggestions`` for general
    competitive intelligence advice.

For Project Managers:
    AI competitor analysis helps merchants understand their competitive
    landscape and identify opportunities. Each call consumes LLM tokens
    billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test competitor analysis with valid and invalid competitor_id values.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Get AI-powered competitor analysis and competitive intelligence
    from your SpyDrop dashboard. The AI analyzes competitor stores
    to help you find opportunities and improve your positioning.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def analyze_competitor(db: AsyncSession, user_id: str, competitor_id: str) -> dict:
    """Generate detailed AI-powered competitor insights.

    Analyzes a specific competitor to provide actionable intelligence
    on their strategy, pricing, and market positioning.

    Args:
        db: Async database session for querying competitor data.
        user_id: The authenticated user's UUID string.
        competitor_id: UUID string of the competitor to analyze.

    Returns:
        Dict containing:
            - analysis: Structured competitor analysis with categories.
            - competitor_id: The analyzed competitor ID.
            - generated_at: ISO timestamp of when analysis was generated.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Provide a detailed competitive analysis for competitor "
            f"(ID: {competitor_id}). Cover: pricing strategy analysis, "
            "product catalog strengths/weaknesses, marketing channels used, "
            "SEO positioning, social media presence, and customer experience. "
            "For each area, suggest counter-strategies. Return JSON with an "
            "'analysis' array of objects, each with 'category', 'finding', "
            "'opportunity', and 'urgency' (high/medium/low)."
        ),
        system=(
            "You are an expert competitive intelligence analyst "
            "specializing in e-commerce markets. You provide actionable "
            "insights that help merchants outperform competitors. "
            "Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="competitor_analysis",
        max_tokens=2000,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"analysis": [result.get("content", "No analysis available.")]}

    return {
        "analysis": parsed.get("analysis", []),
        "competitor_id": competitor_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Get competitive intelligence suggestions.

    Provides strategic recommendations for competitive positioning,
    market differentiation, and opportunity identification.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of competitive intelligence suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable competitive intelligence suggestions "
            "for an e-commerce merchant. Focus on: competitor monitoring "
            "strategies, price positioning, market gap identification, "
            "differentiation tactics, and timing of competitive moves. "
            "Return JSON with a 'suggestions' array of objects, each with "
            "'title', 'description', and 'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert competitive strategy advisor for "
            "e-commerce businesses. You help merchants stay ahead of "
            "competitors through smart market positioning. Always return "
            "valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="competitive_suggestions",
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
