"""
AI-driven suggestions service for TrendScout.

Provides intelligent trend predictions and actionable product research
suggestions by analyzing user data through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. All AI calls are tracked for cost and usage.
    Two functions: ``predict_trends`` for trend analysis, and
    ``get_ai_suggestions`` for general product research advice.

For Project Managers:
    AI suggestions are a premium feature that helps merchants discover
    trending products before competitors. Each call consumes LLM tokens
    billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Verify JSON parsing fallback when LLM returns malformed output.
    Test both success and error paths for each function.

For End Users:
    Get AI-powered trend predictions and product research suggestions
    from the dashboard. The AI analyzes your research data and market
    trends to recommend high-potential products.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def predict_trends(db: AsyncSession, user_id: str) -> dict:
    """Analyze research data and predict upcoming product trends.

    Sends the user's research context to the LLM Gateway for trend
    forecasting. Returns structured predictions with confidence scores.

    Args:
        db: Async database session for querying user research data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - predictions: List of predicted trends with names and scores.
            - generated_at: ISO timestamp of when predictions were generated.
            - provider: The LLM provider used (e.g., 'anthropic', 'openai').
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Analyze current e-commerce market data and predict the top 5 "
            "upcoming product trends. For each trend, provide a name, "
            "description, confidence score (0-100), estimated market size, "
            "and recommended action. Return JSON with a 'predictions' array."
        ),
        system=(
            "You are an expert product trend analyst specializing in "
            "e-commerce and dropshipping markets. You identify emerging "
            "trends before they go mainstream. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="trend_prediction",
        max_tokens=1500,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"predictions": [result.get("content", "No predictions available.")]}

    return {
        "predictions": parsed.get("predictions", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Get AI-powered suggestions for the user's product research.

    Provides actionable recommendations to improve research strategy,
    identify gaps, and optimize product selection.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of actionable suggestion strings.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Based on common product research patterns, provide 3-5 "
            "actionable suggestions to improve product research strategy. "
            "Focus on niche selection, competitor analysis, pricing "
            "optimization, and trend timing. Return JSON with a "
            "'suggestions' array of objects, each with 'title', "
            "'description', and 'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert product research advisor for e-commerce "
            "entrepreneurs. You help merchants find winning products by "
            "analyzing market data and research patterns. Always return "
            "valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="research_suggestions",
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
