"""
AI-driven suggestions service for FlowSend.

Provides intelligent campaign copy generation, customer segmentation,
and marketing improvement suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Three functions: ``generate_campaign_copy``
    for email/SMS copy, ``ai_segment_contacts`` for intelligent
    segmentation, and ``get_ai_suggestions`` for campaign advice.

For Project Managers:
    AI campaign features help merchants create better email and SMS
    campaigns with optimized copy and smart audience segmentation.
    Each call consumes LLM tokens billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test campaign copy generation with various audience/name combos.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Generate AI-powered email and SMS campaign copy, segment your
    contacts intelligently, and get suggestions to improve your
    marketing campaigns from the FlowSend dashboard.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def generate_campaign_copy(
    db: AsyncSession, user_id: str, campaign_name: str, audience: str
) -> dict:
    """Generate AI-powered email/SMS campaign copy.

    Creates compelling marketing copy tailored to the specified
    campaign name and target audience.

    Args:
        db: Async database session.
        user_id: The authenticated user's UUID string.
        campaign_name: Name/theme of the campaign (e.g., "Summer Sale").
        audience: Target audience description (e.g., "repeat customers").

    Returns:
        Dict containing:
            - copy_variants: List of copy variations with subject lines and body.
            - campaign_name: The campaign this copy was generated for.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Generate 3 email campaign copy variants for a campaign called "
            f"'{campaign_name}' targeting '{audience}'. For each variant, "
            "provide: subject_line, preview_text, body_html (short), "
            "and sms_version (under 160 chars). Return JSON with a "
            "'copy_variants' array."
        ),
        system=(
            "You are an expert email marketing copywriter specializing in "
            "e-commerce campaigns. You write high-converting copy with "
            "compelling subject lines and clear calls to action. "
            "Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="campaign_copy",
        max_tokens=2000,
        temperature=0.8,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"copy_variants": [result.get("content", "No copy generated.")]}

    return {
        "copy_variants": parsed.get("copy_variants", []),
        "campaign_name": campaign_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def ai_segment_contacts(db: AsyncSession, user_id: str) -> dict:
    """AI-driven customer segmentation recommendations.

    Suggests intelligent contact segments based on common
    e-commerce customer behavior patterns.

    Args:
        db: Async database session for querying contact data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - segments: List of recommended segments with criteria.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Suggest 5 intelligent customer segments for an e-commerce "
            "email marketing campaign. For each segment, provide: name, "
            "description, criteria (behavioral triggers), recommended "
            "campaign_type, and expected_engagement (high/medium/low). "
            "Return JSON with a 'segments' array."
        ),
        system=(
            "You are an expert in customer segmentation and email "
            "marketing for e-commerce. You create data-driven segments "
            "that maximize engagement and conversion. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="contact_segmentation",
        max_tokens=1500,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"segments": [result.get("content", "No segments available.")]}

    return {
        "segments": parsed.get("segments", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Suggest campaign improvements and marketing strategy.

    Provides actionable recommendations to improve email and SMS
    campaign performance.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of campaign improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable suggestions to improve email and SMS "
            "marketing campaigns for an e-commerce store. Cover: subject "
            "line optimization, send timing, A/B testing strategies, "
            "personalization techniques, and automation workflows. Return "
            "JSON with a 'suggestions' array of objects, each with "
            "'title', 'description', and 'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert email and SMS marketing strategist for "
            "e-commerce businesses. You help merchants increase open "
            "rates, click-through rates, and conversions. Always return "
            "valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="campaign_suggestions",
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
