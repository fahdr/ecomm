"""
AI-driven suggestions service for PostPilot.

Provides intelligent social media caption generation and post
improvement suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``generate_caption`` for
    platform-specific caption creation, and ``get_ai_suggestions``
    for general social media strategy advice.

For Project Managers:
    AI caption generation helps merchants create engaging social media
    content faster with platform-optimized copy. Each call consumes
    LLM tokens billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test caption generation with various platform/tone combinations.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Generate AI-powered social media captions and get posting strategy
    suggestions from your PostPilot dashboard. The AI creates
    platform-optimized content for Instagram, TikTok, Facebook, and more.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def generate_caption(
    db: AsyncSession, user_id: str, topic: str, platform: str, tone: str
) -> dict:
    """Generate a social media caption for a specific platform and tone.

    Creates engaging, platform-optimized captions with hashtags
    and call-to-action elements.

    Args:
        db: Async database session.
        user_id: The authenticated user's UUID string.
        topic: The topic or product to write about.
        platform: Target platform (e.g., "instagram", "tiktok", "facebook").
        tone: Desired tone (e.g., "professional", "casual", "humorous").

    Returns:
        Dict containing:
            - captions: List of caption variations with hashtags.
            - platform: The target platform.
            - tone: The requested tone.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Generate 3 social media caption variants for '{topic}' on "
            f"{platform} with a {tone} tone. For each variant, provide: "
            "caption text (platform-appropriate length), hashtags (5-10 "
            "relevant tags), call_to_action, and best_posting_time. "
            "Return JSON with a 'captions' array."
        ),
        system=(
            "You are an expert social media copywriter specializing in "
            f"e-commerce content for {platform}. You create engaging, "
            "viral-worthy captions that drive engagement and sales. "
            "Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="caption_generation",
        max_tokens=1500,
        temperature=0.8,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"captions": [result.get("content", "No captions generated.")]}

    return {
        "captions": parsed.get("captions", []),
        "platform": platform,
        "tone": tone,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Suggest social media post improvements and strategy.

    Provides actionable recommendations for improving social media
    presence and engagement.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of social media improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable social media strategy suggestions "
            "for an e-commerce store. Cover: content calendar planning, "
            "platform-specific best practices, engagement tactics, "
            "influencer collaboration tips, and analytics-driven "
            "optimization. Return JSON with a 'suggestions' array of "
            "objects, each with 'title', 'description', and 'priority' "
            "(high/medium/low)."
        ),
        system=(
            "You are an expert social media strategist for e-commerce "
            "businesses. You help merchants grow their following and "
            "drive sales through social media. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="social_suggestions",
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
