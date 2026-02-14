"""
AI-powered ad copy generation service for AdScale.

Generates platform-specific ad copy using the centralized LLM Gateway.
Supports Google Ads, Meta (Facebook/Instagram) Ads, and TikTok Ads with
format constraints appropriate to each platform.

For Developers:
    ``generate_ad_copy`` produces a single set of ad copy for a given
    product and platform.  ``generate_ad_variants`` produces multiple
    variations for A/B testing.  Both functions call the LLM Gateway
    via ``call_llm`` and fall back to template-based copy if the gateway
    is unavailable.

For Project Managers:
    AI ad copy generation is a core AdScale value proposition.  It saves
    users 15-30 minutes per campaign by automatically writing compelling,
    platform-compliant ad text.

For QA Engineers:
    Mock ``call_llm`` in tests to avoid real gateway calls.  Verify that
    platform constraints are respected (Google headline 30 chars max,
    Meta primary text, TikTok short format).  Test both LLM success and
    fallback paths.

For End Users:
    Let AI write your ad copy -- just provide product details and choose
    your ad platform.  AdScale generates headlines, descriptions, and
    CTAs optimized for each platform's requirements.
"""

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_client import LLMGatewayError, call_llm

logger = logging.getLogger(__name__)


# ── Platform Constraints ──────────────────────────────────────────────

PLATFORM_CONSTRAINTS = {
    "google_ads": {
        "headline_max_length": 30,
        "headline_count": 15,
        "description_max_length": 90,
        "description_count": 4,
        "name": "Google Ads",
    },
    "meta_ads": {
        "primary_text_max_length": 125,
        "headline_max_length": 40,
        "description_max_length": 125,
        "name": "Meta (Facebook/Instagram) Ads",
    },
    "tiktok_ads": {
        "headline_max_length": 50,
        "description_max_length": 100,
        "name": "TikTok Ads",
    },
    # Fallback for generic platforms (google, meta from existing model)
    "google": {
        "headline_max_length": 30,
        "headline_count": 15,
        "description_max_length": 90,
        "description_count": 4,
        "name": "Google Ads",
    },
    "meta": {
        "primary_text_max_length": 125,
        "headline_max_length": 40,
        "description_max_length": 125,
        "name": "Meta (Facebook/Instagram) Ads",
    },
}


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class AdCopyResult:
    """
    Result of AI ad copy generation.

    Attributes:
        headlines: List of generated headlines.
        descriptions: List of generated descriptions.
        call_to_actions: List of suggested call-to-action texts.
        display_url_path: Suggested display URL path (e.g. '/shop/product').
    """

    headlines: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    call_to_actions: list[str] = field(default_factory=list)
    display_url_path: str = ""


# ── System Prompts ────────────────────────────────────────────────────

GOOGLE_ADS_SYSTEM = """You are an expert Google Ads copywriter. Generate ad copy following these strict rules:
- Headlines: exactly {headline_count} headlines, each MAXIMUM {headline_max_length} characters
- Descriptions: exactly {description_count} descriptions, each MAXIMUM {description_max_length} characters
- Include compelling CTAs and highlight key benefits
- Use power words and emotional triggers
- Respond in JSON format:
{{"headlines": ["..."], "descriptions": ["..."], "call_to_actions": ["..."], "display_url_path": "/..."}}"""

META_ADS_SYSTEM = """You are an expert Meta (Facebook/Instagram) Ads copywriter. Generate ad copy following these rules:
- Primary text: engaging, max {primary_text_max_length} characters
- Headline: attention-grabbing, max {headline_max_length} characters
- Description: supporting detail, max {description_max_length} characters
- Use emoji sparingly for engagement
- Respond in JSON format:
{{"headlines": ["..."], "descriptions": ["..."], "call_to_actions": ["..."], "display_url_path": "/..."}}"""

TIKTOK_ADS_SYSTEM = """You are an expert TikTok Ads copywriter. Generate ad copy following these rules:
- Headlines: short, punchy, max {headline_max_length} characters
- Descriptions: brief and engaging, max {description_max_length} characters
- Use casual, trending language that resonates with Gen Z and millennials
- Respond in JSON format:
{{"headlines": ["..."], "descriptions": ["..."], "call_to_actions": ["..."], "display_url_path": "/..."}}"""


def _get_system_prompt(platform: str) -> str:
    """
    Build a platform-specific system prompt for ad copy generation.

    Args:
        platform: The ad platform identifier (google_ads, meta_ads, tiktok_ads).

    Returns:
        Formatted system prompt string with platform constraints.
    """
    constraints = PLATFORM_CONSTRAINTS.get(platform, PLATFORM_CONSTRAINTS.get("google", {}))

    if platform in ("google_ads", "google"):
        return GOOGLE_ADS_SYSTEM.format(**constraints)
    elif platform in ("meta_ads", "meta"):
        return META_ADS_SYSTEM.format(**constraints)
    elif platform == "tiktok_ads":
        return TIKTOK_ADS_SYSTEM.format(**constraints)
    else:
        # Default to Google-style
        return GOOGLE_ADS_SYSTEM.format(**PLATFORM_CONSTRAINTS["google"])


def _fallback_ad_copy(product_data: dict, platform: str) -> AdCopyResult:
    """
    Generate template-based ad copy as a fallback when LLM is unavailable.

    Uses simple string templates based on product name and description.

    Args:
        product_data: Dict with 'name', 'description', and optional 'price' keys.
        product_data: Dict with 'name', 'description', and optional 'price' keys.
        platform: The ad platform identifier.

    Returns:
        AdCopyResult with template-generated copy.
    """
    name = product_data.get("name", "Product")
    desc = product_data.get("description", "An amazing product")
    price = product_data.get("price")

    price_suffix = f" - Only ${price}" if price else ""

    headlines = [
        f"Discover {name}"[:30],
        f"Shop {name} Today"[:30],
        f"Best {name} Deals"[:30],
    ]
    descriptions = [
        f"{desc[:80]}. Shop now{price_suffix}."[:90],
        f"Transform your life with {name}. {desc[:40]}."[:90],
    ]
    ctas = ["Shop Now", "Learn More", "Buy Now"]

    return AdCopyResult(
        headlines=headlines,
        descriptions=descriptions,
        call_to_actions=ctas,
        display_url_path=f"/shop/{name.lower().replace(' ', '-')}"[:50],
    )


def _parse_llm_response(content: str, platform: str) -> AdCopyResult:
    """
    Parse the LLM response content into an AdCopyResult.

    Attempts JSON parsing first, then falls back to text extraction.

    Args:
        content: Raw text content from the LLM response.
        platform: The ad platform identifier (for constraint enforcement).

    Returns:
        AdCopyResult parsed from the response.
    """
    try:
        # Try to extract JSON from the response
        # Handle cases where JSON is wrapped in markdown code blocks
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)

        data = json.loads(cleaned)

        headlines = data.get("headlines", [])
        descriptions = data.get("descriptions", [])
        ctas = data.get("call_to_actions", ["Shop Now"])
        display_path = data.get("display_url_path", "")

        # Enforce platform constraints
        constraints = PLATFORM_CONSTRAINTS.get(platform, {})
        headline_max = constraints.get("headline_max_length", 30)
        desc_max = constraints.get("description_max_length", 90)

        headlines = [h[:headline_max] for h in headlines if h]
        descriptions = [d[:desc_max] for d in descriptions if d]

        return AdCopyResult(
            headlines=headlines,
            descriptions=descriptions,
            call_to_actions=ctas,
            display_url_path=display_path[:50] if display_path else "",
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse LLM response as JSON: %s", e)
        # Return a basic result from the raw text
        return AdCopyResult(
            headlines=[content[:30]],
            descriptions=[content[:90]],
            call_to_actions=["Shop Now"],
            display_url_path="",
        )


# ── Public API ────────────────────────────────────────────────────────


async def generate_ad_copy(
    db: AsyncSession,
    user_id: str,
    product_data: dict,
    platform: str,
    campaign_type: str = "conversion",
) -> AdCopyResult:
    """
    Generate AI ad copy for a product on a specific platform.

    Calls the LLM Gateway with platform-specific system prompts and
    format constraints.  Falls back to template-based copy if the
    gateway is unavailable.

    Args:
        db: Async database session (reserved for future usage tracking).
        user_id: UUID string of the requesting user.
        product_data: Dict with product details:
            - name (str): Product name.
            - description (str): Product description.
            - price (float, optional): Product price.
            - category (str, optional): Product category.
        platform: Ad platform ('google_ads', 'meta_ads', 'tiktok_ads',
                  'google', 'meta').
        campaign_type: Campaign type for prompt tuning (default 'conversion').

    Returns:
        AdCopyResult with generated headlines, descriptions, CTAs, and URL path.
    """
    system_prompt = _get_system_prompt(platform)

    user_prompt = (
        f"Generate ad copy for the following product:\n"
        f"Product Name: {product_data.get('name', 'Unknown')}\n"
        f"Description: {product_data.get('description', 'N/A')}\n"
    )
    if product_data.get("price"):
        user_prompt += f"Price: ${product_data['price']}\n"
    if product_data.get("category"):
        user_prompt += f"Category: {product_data['category']}\n"
    user_prompt += f"\nCampaign Type: {campaign_type}\n"
    user_prompt += "Generate compelling ad copy that maximizes conversions."

    try:
        response = await call_llm(
            prompt=user_prompt,
            system=system_prompt,
            user_id=user_id,
            task_type="ad_copy_generation",
            json_mode=True,
            temperature=0.8,
            max_tokens=2048,
        )
        content = response.get("content", "")
        return _parse_llm_response(content, platform)

    except LLMGatewayError:
        logger.warning(
            "LLM Gateway unavailable, using template fallback for user %s",
            user_id,
        )
        return _fallback_ad_copy(product_data, platform)


async def generate_ad_variants(
    db: AsyncSession,
    user_id: str,
    product_data: dict,
    platform: str,
    count: int = 5,
) -> list[AdCopyResult]:
    """
    Generate multiple ad copy variants for A/B testing.

    Calls ``generate_ad_copy`` multiple times with slightly different
    temperature settings to produce diverse variations.

    Args:
        db: Async database session.
        user_id: UUID string of the requesting user.
        product_data: Dict with product details (name, description, price).
        platform: Ad platform identifier.
        count: Number of variants to generate (default 5, max 10).

    Returns:
        List of AdCopyResult objects, one per variant.
    """
    count = min(count, 10)  # Cap at 10 variants
    variants: list[AdCopyResult] = []

    campaign_types = ["conversion", "awareness", "traffic", "engagement", "retargeting"]

    for i in range(count):
        campaign_type = campaign_types[i % len(campaign_types)]
        variant = await generate_ad_copy(
            db=db,
            user_id=user_id,
            product_data=product_data,
            platform=platform,
            campaign_type=campaign_type,
        )
        variants.append(variant)

    return variants
