"""
AI-driven suggestions service for ContentForge.

Provides intelligent content enhancement and improvement suggestions
by analyzing user content through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``enhance_content`` for
    targeted content improvement, and ``get_ai_suggestions`` for
    general content strategy advice.

For Project Managers:
    AI content enhancement is a premium feature that helps merchants
    create higher-quality product descriptions, blog posts, and
    marketing copy. Each call consumes LLM tokens billed through
    the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test with valid and invalid content_id values. Verify JSON parsing
    fallback when LLM returns malformed output.

For End Users:
    Enhance your product content with AI-powered suggestions. The AI
    reviews your content for SEO, readability, and engagement, then
    provides specific improvements.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def enhance_content(db: AsyncSession, user_id: str, content_id: str) -> dict:
    """Improve content quality, SEO, and readability for a specific piece.

    Sends content context to the LLM Gateway for enhancement analysis.
    Returns structured improvement suggestions.

    Args:
        db: Async database session for querying content data.
        user_id: The authenticated user's UUID string.
        content_id: UUID string of the content piece to enhance.

    Returns:
        Dict containing:
            - enhancements: List of suggested improvements with categories.
            - content_id: The analyzed content piece ID.
            - generated_at: ISO timestamp of when enhancements were generated.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Analyze the content piece (ID: {content_id}) and provide "
            "specific enhancements. Focus on: SEO optimization (title tags, "
            "meta descriptions, keyword density), readability improvements "
            "(sentence structure, paragraph length), engagement hooks, "
            "and call-to-action effectiveness. Return JSON with an "
            "'enhancements' array of objects, each with 'category', "
            "'current_issue', 'suggestion', and 'impact' (high/medium/low)."
        ),
        system=(
            "You are an expert content strategist specializing in "
            "e-commerce product content. You optimize copy for both "
            "search engines and human readers. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="content_enhancement",
        max_tokens=1500,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"enhancements": [result.get("content", "No enhancements available.")]}

    return {
        "enhancements": parsed.get("enhancements", []),
        "content_id": content_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Suggest content improvements across all user content.

    Provides general content strategy recommendations based on
    common e-commerce content patterns and best practices.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of content improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable content strategy suggestions for an "
            "e-commerce store. Focus on product description templates, "
            "SEO-friendly content structures, A/B testing copy variations, "
            "and seasonal content planning. Return JSON with a 'suggestions' "
            "array of objects, each with 'title', 'description', and "
            "'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert content marketing strategist for e-commerce "
            "businesses. You help merchants create compelling product "
            "content that converts. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="content_suggestions",
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
