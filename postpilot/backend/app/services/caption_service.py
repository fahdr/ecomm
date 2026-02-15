"""
AI caption generation service for social media posts.

Generates captions and hashtag suggestions from product data with
platform-specific formatting. In mock mode, uses template-based content.
When the LLM Gateway is available, routes through it for intelligent
caption generation via Claude or another LLM.

For Developers:
    ``generate_caption`` is the main entry point for caption creation. It
    accepts product data (dict), platform, and tone parameters. The mock
    implementation creates realistic-looking captions with platform-specific
    formatting. ``generate_hashtags`` generates hashtags from product keywords.

    ``CaptionResult`` is a dataclass that standardizes the output format.
    The ``generate_caption_via_llm`` function calls the LLM gateway for
    AI-powered generation and falls back to template generation on errors.

For QA Engineers:
    Test with various product data shapes (minimal, complete, empty fields).
    Verify that different tones produce different outputs.
    Test platform-specific formatting (Instagram hashtags, TikTok trends,
    Twitter 280-char limit, Pinterest keywords).

For Project Managers:
    AI caption generation is a key value proposition -- it saves users time
    by automatically creating engaging social media content from product data.

For End Users:
    PostPilot generates captions for your products automatically. Choose
    your preferred tone (casual, professional, playful) and target platform
    for the best results.
"""

import logging
import random
from dataclasses import dataclass, field

from app.services.llm_client import LLMGatewayError, call_llm

logger = logging.getLogger(__name__)

# Platform-specific character limits
PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "instagram": 2200,
    "facebook": 63206,
    "tiktok": 2200,
    "twitter": 280,
    "pinterest": 500,
}

# Platform-specific system prompts for LLM-based generation
PLATFORM_SYSTEM_PROMPTS: dict[str, str] = {
    "instagram": (
        "You are a social media expert specializing in Instagram content. "
        "Generate engaging captions with relevant hashtags. Keep under 2200 characters. "
        "Include a strong call to action. Use line breaks for readability. "
        "Suggest up to 30 relevant hashtags."
    ),
    "facebook": (
        "You are a social media expert specializing in Facebook content. "
        "Generate longer-form, conversational captions that encourage engagement. "
        "Include a question or call to action to boost comments. "
        "Keep the tone warm and community-focused."
    ),
    "tiktok": (
        "You are a social media expert specializing in TikTok content. "
        "Generate trendy, short, attention-grabbing captions. "
        "Use trending language and slang. Include 3-5 relevant hashtags. "
        "Reference trending sounds or challenges when appropriate."
    ),
    "twitter": (
        "You are a social media expert specializing in Twitter/X content. "
        "Generate concise, punchy tweets under 280 characters. "
        "Make every word count. Include 2-3 relevant hashtags within the limit. "
        "Use wit, urgency, or curiosity to drive engagement."
    ),
    "pinterest": (
        "You are a social media expert specializing in Pinterest content. "
        "Generate keyword-rich, descriptive pin descriptions under 500 characters. "
        "Focus on search discoverability. Include relevant keywords naturally. "
        "Describe the product's benefits and use cases."
    ),
}


@dataclass
class CaptionResult:
    """
    Standardized result from caption generation.

    Attributes:
        caption_text: The generated caption text.
        hashtags: List of suggested hashtags (without # prefix).
        call_to_action: A suggested call-to-action phrase.
        character_count: Length of the generated caption text.
    """

    caption_text: str
    hashtags: list[str] = field(default_factory=list)
    call_to_action: str = ""
    character_count: int = 0

    def __post_init__(self):
        """Calculate character count after initialization."""
        self.character_count = len(self.caption_text)


def generate_caption(
    product_data: dict,
    platform: str = "instagram",
    tone: str = "engaging",
) -> dict:
    """
    Generate an AI caption and hashtags from product data (synchronous mock version).

    In mock mode, creates a template-based caption. This function maintains
    backward compatibility with the original synchronous API.

    Args:
        product_data: Dict with product info (title, description, price, etc.).
        platform: Target platform (instagram, facebook, tiktok, twitter, pinterest).
        tone: Desired caption tone (casual, professional, playful, engaging).

    Returns:
        Dict with 'caption', 'hashtags', and 'platform' keys.
    """
    title = product_data.get("title", "Amazing Product")
    description = product_data.get("description", "Check out this incredible find!")
    price = product_data.get("price", "")

    # Platform-specific formatting
    caption = _build_caption(title, description, price, platform, tone)
    hashtags = generate_hashtags(product_data, platform)

    # Build call to action
    cta = _build_call_to_action(platform)

    return {
        "caption": caption,
        "hashtags": hashtags,
        "platform": platform,
        "call_to_action": cta,
        "character_count": len(caption),
    }


async def generate_caption_async(
    product_data: dict,
    platform: str = "instagram",
    tone: str = "engaging",
    user_id: str = "",
    use_llm: bool = False,
) -> CaptionResult:
    """
    Generate a caption asynchronously, optionally using the LLM gateway.

    Falls back to template generation if LLM gateway is unavailable.

    Args:
        product_data: Dict with product info (title, description, price, etc.).
        platform: Target platform (instagram, facebook, tiktok, twitter, pinterest).
        tone: Desired caption tone (casual, professional, playful, engaging).
        user_id: UUID string of the requesting user.
        use_llm: Whether to attempt LLM-based generation.

    Returns:
        CaptionResult with caption text, hashtags, call to action, and character count.
    """
    if use_llm:
        try:
            return await _generate_via_llm(product_data, platform, tone, user_id)
        except (LLMGatewayError, Exception) as exc:
            logger.warning("LLM generation failed, falling back to template: %s", exc)

    # Fallback to template-based generation
    result = generate_caption(product_data, platform, tone)
    return CaptionResult(
        caption_text=result["caption"],
        hashtags=result["hashtags"],
        call_to_action=result.get("call_to_action", ""),
    )


async def _generate_via_llm(
    product_data: dict,
    platform: str,
    tone: str,
    user_id: str,
) -> CaptionResult:
    """
    Generate a caption using the LLM Gateway.

    Constructs a platform-specific prompt and sends it to the gateway.

    Args:
        product_data: Product information dict.
        platform: Target social media platform.
        tone: Desired caption tone.
        user_id: User UUID for quota tracking.

    Returns:
        CaptionResult parsed from LLM response.

    Raises:
        LLMGatewayError: If the gateway call fails.
    """
    system_prompt = PLATFORM_SYSTEM_PROMPTS.get(platform, PLATFORM_SYSTEM_PROMPTS["instagram"])

    title = product_data.get("title", "Product")
    description = product_data.get("description", "")
    price = product_data.get("price", "")
    category = product_data.get("category", "")

    prompt = (
        f"Generate a {tone} social media caption for {platform}.\n\n"
        f"Product: {title}\n"
        f"Description: {description}\n"
        f"Price: {price}\n"
        f"Category: {category}\n\n"
        f"Return the caption text, hashtags (without # prefix, comma-separated), "
        f"and a call to action."
    )

    response = await call_llm(
        prompt=prompt,
        system=system_prompt,
        user_id=user_id,
        task_type="caption_generation",
        temperature=0.8,
    )

    # Parse LLM response
    content = response.get("content", "")
    hashtags = generate_hashtags(product_data, platform)
    cta = _build_call_to_action(platform)

    # Enforce character limit
    char_limit = PLATFORM_CHAR_LIMITS.get(platform, 2200)
    if len(content) > char_limit:
        content = content[:char_limit - 3] + "..."

    return CaptionResult(
        caption_text=content,
        hashtags=hashtags,
        call_to_action=cta,
    )


def _build_caption(
    title: str,
    description: str,
    price: str,
    platform: str,
    tone: str,
) -> str:
    """
    Build a mock caption based on platform and tone.

    Creates platform-specific caption formatting with tone-appropriate
    language. Each combination produces a unique template.

    Args:
        title: Product title.
        description: Product description.
        price: Product price string.
        platform: Target platform.
        tone: Desired tone.

    Returns:
        Generated caption string.
    """
    price_line = f"\n\nNow just {price}!" if price else ""

    tone_openers = {
        "casual": [
            f"Hey, check this out! {title}",
            f"Just found something cool: {title}",
            f"You need this in your life: {title}",
        ],
        "professional": [
            f"Introducing {title}",
            f"Discover {title} — crafted for excellence",
            f"Elevate your experience with {title}",
        ],
        "playful": [
            f"OMG, {title} is here and it's a vibe!",
            f"Plot twist: {title} just dropped!",
            f"Stop scrolling! {title} is calling your name!",
        ],
        "engaging": [
            f"Ready to level up? Meet {title}",
            f"Your new favorite thing: {title}",
            f"We can't stop talking about {title}",
        ],
    }

    openers = tone_openers.get(tone, tone_openers["engaging"])
    opener = random.choice(openers)

    if platform == "tiktok":
        caption = f"{opener}\n\n{description}{price_line}\n\nLink in bio! #fyp #trending"
    elif platform == "facebook":
        caption = f"{opener}\n\n{description}{price_line}\n\nShop now at the link below!"
    elif platform == "twitter":
        # Twitter: 280 char limit, keep it tight
        short_desc = description[:100] + "..." if len(description) > 100 else description
        caption = f"{opener} - {short_desc}"
        if len(caption) > 270:
            caption = caption[:267] + "..."
    elif platform == "pinterest":
        caption = f"{opener}\n\n{description}{price_line}\n\nDiscover more on our shop!"
    else:  # instagram
        caption = f"{opener}\n\n{description}{price_line}\n\nDouble-tap if you love this!"

    # Enforce platform character limits
    char_limit = PLATFORM_CHAR_LIMITS.get(platform, 2200)
    if len(caption) > char_limit:
        caption = caption[:char_limit - 3] + "..."

    return caption


def _build_call_to_action(platform: str) -> str:
    """
    Build a platform-appropriate call to action.

    Args:
        platform: The target social media platform.

    Returns:
        A call-to-action string suitable for the platform.
    """
    cta_map = {
        "instagram": "Link in bio to shop now!",
        "facebook": "Click the link below to shop!",
        "tiktok": "Link in bio!",
        "twitter": "Shop now ->",
        "pinterest": "Save this pin for later!",
    }
    return cta_map.get(platform, "Shop now!")


def generate_hashtags(
    product_data: dict,
    platform: str = "instagram",
    count: int = 30,
) -> list[str]:
    """
    Generate relevant hashtags from product data.

    Extracts keywords from product title and description, then combines
    them with platform-specific trending hashtags.

    Args:
        product_data: Dict with product info.
        platform: Target platform for hashtag relevance.
        count: Maximum number of hashtags to generate (default: 30).

    Returns:
        List of hashtag strings (without # prefix).
    """
    title = product_data.get("title", "")
    category = product_data.get("category", "")

    # Extract keywords from title
    stop_words = {"the", "a", "an", "is", "it", "to", "for", "and", "or", "of", "in", "on", "at"}
    words = [
        w.lower().strip(".,!?;:\"'")
        for w in title.split()
        if w.lower() not in stop_words and len(w) > 2
    ]

    # Base hashtags from product data
    base_tags = words[:4]

    if category:
        base_tags.append(category.lower().replace(" ", ""))

    # Platform-specific popular tags
    platform_tags = {
        "instagram": ["instagood", "shopnow", "newdrop", "musthave", "trending",
                       "instashop", "dailyfinds", "styleinspo"],
        "facebook": ["shoplocal", "newproduct", "mustbuy", "trending",
                      "deals", "shopnow"],
        "tiktok": ["fyp", "viral", "trending", "tiktokmademebuyit", "newfinds",
                    "foryou", "foryoupage"],
        "twitter": ["shopnow", "newdrop", "trending", "musthave"],
        "pinterest": ["shopnow", "homedecor", "styleinspo", "musthave",
                       "pinterestfinds", "aesthetic"],
    }

    extra = platform_tags.get(platform, platform_tags["instagram"])
    all_tags = base_tags + extra

    # Deduplicate and limit
    seen: set[str] = set()
    unique_tags: list[str] = []
    for tag in all_tags:
        clean_tag = tag.replace(" ", "").replace("#", "")
        if clean_tag and clean_tag not in seen:
            seen.add(clean_tag)
            unique_tags.append(clean_tag)

    return unique_tags[:count]
