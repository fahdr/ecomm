"""
AI caption generation service for social media posts.

Generates captions and hashtag suggestions from product data. In the
current implementation, caption generation is mocked with template-based
content. When an Anthropic API key is configured, it would use Claude
for intelligent caption generation.

For Developers:
    The `generate_caption` function is the main entry point. It accepts
    product data (dict), platform, and tone parameters. The mock
    implementation creates realistic-looking captions with platform-specific
    formatting. The `suggest_hashtags` function generates relevant hashtags
    from product keywords.

For QA Engineers:
    Test with various product data shapes (minimal, complete, empty fields).
    Verify that different tones produce different outputs.
    Test platform-specific formatting (Instagram hashtags, TikTok trends, etc.).

For Project Managers:
    AI caption generation is a key value proposition — it saves users time
    by automatically creating engaging social media content from product data.

For End Users:
    PostPilot generates captions for your products automatically. Choose
    your preferred tone (casual, professional, playful) and target platform
    for the best results.
"""

import random


def generate_caption(
    product_data: dict,
    platform: str = "instagram",
    tone: str = "engaging",
) -> dict:
    """
    Generate an AI caption and hashtags from product data.

    In mock mode, creates a template-based caption. With a real AI backend,
    this would call Claude or another LLM for creative caption generation.

    Args:
        product_data: Dict with product info (title, description, price, etc.).
        platform: Target platform (instagram, facebook, tiktok).
        tone: Desired caption tone (casual, professional, playful, engaging).

    Returns:
        Dict with 'caption', 'hashtags', and 'platform' keys.
    """
    title = product_data.get("title", "Amazing Product")
    description = product_data.get("description", "Check out this incredible find!")
    price = product_data.get("price", "")

    # Platform-specific formatting
    caption = _build_caption(title, description, price, platform, tone)
    hashtags = suggest_hashtags(product_data, platform)

    return {
        "caption": caption,
        "hashtags": hashtags,
        "platform": platform,
    }


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
        return f"{opener}\n\n{description}{price_line}\n\nLink in bio! #fyp #trending"
    elif platform == "facebook":
        return f"{opener}\n\n{description}{price_line}\n\nShop now at the link below!"
    else:  # instagram
        return f"{opener}\n\n{description}{price_line}\n\nDouble-tap if you love this!"


def suggest_hashtags(
    product_data: dict,
    platform: str = "instagram",
) -> list[str]:
    """
    Generate relevant hashtags from product data.

    Extracts keywords from product title and description, then combines
    them with platform-specific trending hashtags.

    Args:
        product_data: Dict with product info.
        platform: Target platform for hashtag relevance.

    Returns:
        List of hashtag strings (without # prefix, 8-12 tags).
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
        "instagram": ["instagood", "shopnow", "newdrop", "musthave", "trending"],
        "facebook": ["shoplocal", "newproduct", "mustbuy", "trending"],
        "tiktok": ["fyp", "viral", "trending", "tiktokmademebuyit", "newfinds"],
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

    return unique_tags[:10]
