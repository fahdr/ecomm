"""
AI-driven suggestions service for SourcePilot.

Provides intelligent supplier scoring and sourcing improvement
suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``score_supplier`` for
    AI-driven supplier reliability scoring, and ``get_ai_suggestions``
    for general sourcing strategy advice.

For Project Managers:
    AI supplier scoring helps merchants evaluate supplier reliability
    before committing to partnerships. Each call consumes LLM tokens
    billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test supplier scoring with valid and invalid supplier URLs.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Score suppliers with AI-powered reliability analysis and get
    sourcing strategy suggestions from your SourcePilot dashboard.
    The AI evaluates suppliers based on multiple quality factors.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def score_supplier(db: AsyncSession, user_id: str, supplier_url: str) -> dict:
    """AI-powered scoring of supplier reliability and quality.

    Analyzes a supplier URL and provides a structured reliability
    assessment with scores across multiple dimensions.

    Args:
        db: Async database session for querying supplier data.
        user_id: The authenticated user's UUID string.
        supplier_url: URL of the supplier to evaluate.

    Returns:
        Dict containing:
            - scoring: Structured reliability scores by category.
            - overall_score: Aggregate reliability score (0-100).
            - supplier_url: The evaluated supplier URL.
            - generated_at: ISO timestamp of when scoring was generated.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Evaluate the supplier at '{supplier_url}' for dropshipping "
            "reliability. Score the following dimensions (0-100): "
            "product_quality, shipping_speed, communication, pricing "
            "competitiveness, return_policy, catalog_breadth, and "
            "platform_reputation. Provide an overall_score (weighted "
            "average) and a brief recommendation. Return JSON with a "
            "'scoring' object containing dimension scores, 'overall_score' "
            "integer, and 'recommendation' string."
        ),
        system=(
            "You are an expert supplier evaluation analyst for "
            "dropshipping businesses. You assess supplier reliability "
            "based on industry benchmarks and risk factors. "
            "Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="supplier_scoring",
        max_tokens=1500,
        temperature=0.5,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {
            "scoring": {},
            "overall_score": 0,
            "recommendation": result.get("content", "Unable to score supplier."),
        }

    return {
        "scoring": parsed.get("scoring", {}),
        "overall_score": parsed.get("overall_score", 0),
        "supplier_url": supplier_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Suggest supplier sourcing improvements and strategies.

    Provides actionable recommendations for improving supplier
    relationships, diversifying sources, and optimizing costs.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of sourcing improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable suggestions to improve supplier "
            "sourcing strategy for a dropshipping business. Cover: "
            "supplier diversification, quality control processes, "
            "negotiation tactics, shipping optimization, and risk "
            "mitigation. Return JSON with a 'suggestions' array of "
            "objects, each with 'title', 'description', and 'priority' "
            "(high/medium/low)."
        ),
        system=(
            "You are an expert supply chain advisor for dropshipping "
            "businesses. You help merchants find reliable suppliers "
            "and optimize their sourcing operations. Always return "
            "valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="sourcing_suggestions",
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
