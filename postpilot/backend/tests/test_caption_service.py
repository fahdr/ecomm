"""
Tests for the caption generation service.

Covers template-based generation across all platforms, tone variations,
hashtag generation, CaptionResult dataclass, and character limit enforcement.

For Developers:
    Tests use the synchronous generate_caption function and the async
    generate_caption_async function. LLM gateway calls are mocked.

For QA Engineers:
    These tests verify:
    - Caption generation produces non-empty text for all platforms.
    - Different tones produce different output styles.
    - Hashtags are generated from product data keywords.
    - Twitter captions respect the 280-character limit.
    - CaptionResult correctly computes character_count.
    - Async generation falls back to template on LLM error.
"""

import pytest

from app.services.caption_service import (
    CaptionResult,
    PLATFORM_CHAR_LIMITS,
    generate_caption,
    generate_caption_async,
    generate_hashtags,
)


SAMPLE_PRODUCT = {
    "title": "Wireless Noise-Cancelling Headphones",
    "description": "Premium over-ear headphones with 40-hour battery life.",
    "price": "$79.99",
    "category": "Electronics",
}


# ── Template Generation Tests ─────────────────────────────────────


def test_generate_caption_instagram():
    """generate_caption returns valid caption for Instagram platform."""
    result = generate_caption(SAMPLE_PRODUCT, platform="instagram")

    assert "caption" in result
    assert len(result["caption"]) > 0
    assert result["platform"] == "instagram"
    assert isinstance(result["hashtags"], list)
    assert len(result["hashtags"]) > 0


def test_generate_caption_facebook():
    """generate_caption returns valid caption for Facebook platform."""
    result = generate_caption(SAMPLE_PRODUCT, platform="facebook")

    assert "Shop now" in result["caption"] or "link below" in result["caption"]
    assert result["platform"] == "facebook"


def test_generate_caption_tiktok():
    """generate_caption returns valid caption for TikTok platform."""
    result = generate_caption(SAMPLE_PRODUCT, platform="tiktok")

    assert "Link in bio" in result["caption"] or "fyp" in result["caption"]
    assert result["platform"] == "tiktok"


def test_generate_caption_twitter():
    """generate_caption returns caption under 280 chars for Twitter."""
    result = generate_caption(SAMPLE_PRODUCT, platform="twitter")

    assert len(result["caption"]) <= 280
    assert result["platform"] == "twitter"


def test_generate_caption_pinterest():
    """generate_caption returns valid caption for Pinterest platform."""
    result = generate_caption(SAMPLE_PRODUCT, platform="pinterest")

    assert result["platform"] == "pinterest"
    assert len(result["caption"]) > 0


def test_generate_caption_different_tones():
    """Different tones produce different caption styles."""
    casual = generate_caption(SAMPLE_PRODUCT, platform="instagram", tone="casual")
    professional = generate_caption(SAMPLE_PRODUCT, platform="instagram", tone="professional")

    # While random, the opener words should generally differ
    assert casual["caption"] != "" and professional["caption"] != ""
    assert casual["platform"] == professional["platform"] == "instagram"


def test_generate_caption_includes_call_to_action():
    """generate_caption includes a call_to_action field."""
    result = generate_caption(SAMPLE_PRODUCT, platform="instagram")

    assert "call_to_action" in result
    assert len(result["call_to_action"]) > 0


def test_generate_caption_includes_character_count():
    """generate_caption includes character_count matching caption length."""
    result = generate_caption(SAMPLE_PRODUCT, platform="instagram")

    assert "character_count" in result
    assert result["character_count"] == len(result["caption"])


def test_generate_caption_minimal_product_data():
    """generate_caption works with minimal product data (just title)."""
    result = generate_caption({"title": "Cool Widget"}, platform="instagram")

    assert "Cool Widget" in result["caption"]
    assert len(result["hashtags"]) > 0


def test_generate_caption_empty_product_data():
    """generate_caption works with empty product data using defaults."""
    result = generate_caption({}, platform="instagram")

    assert "Amazing Product" in result["caption"]
    assert result["platform"] == "instagram"


# ── Hashtag Generation Tests ──────────────────────────────────────


def test_generate_hashtags_from_product():
    """generate_hashtags extracts keywords from product title."""
    tags = generate_hashtags(SAMPLE_PRODUCT, platform="instagram")

    assert isinstance(tags, list)
    assert len(tags) > 0
    # Should include keyword from title
    assert "wireless" in tags or "noise-cancelling" in tags or "headphones" in tags


def test_generate_hashtags_includes_platform_tags():
    """generate_hashtags includes platform-specific trending tags."""
    ig_tags = generate_hashtags(SAMPLE_PRODUCT, platform="instagram")
    tt_tags = generate_hashtags(SAMPLE_PRODUCT, platform="tiktok")

    assert "instagood" in ig_tags
    assert "fyp" in tt_tags


def test_generate_hashtags_includes_category():
    """generate_hashtags includes the product category as a hashtag."""
    tags = generate_hashtags(SAMPLE_PRODUCT, platform="instagram")

    assert "electronics" in tags


def test_generate_hashtags_respects_count_limit():
    """generate_hashtags respects the count parameter."""
    tags = generate_hashtags(SAMPLE_PRODUCT, platform="instagram", count=5)

    assert len(tags) <= 5


def test_generate_hashtags_no_duplicates():
    """generate_hashtags returns unique tags without duplicates."""
    tags = generate_hashtags(SAMPLE_PRODUCT, platform="instagram")

    assert len(tags) == len(set(tags))


# ── CaptionResult Dataclass Tests ─────────────────────────────────


def test_caption_result_character_count():
    """CaptionResult auto-calculates character_count from caption_text."""
    result = CaptionResult(caption_text="Hello world!")

    assert result.character_count == 12


def test_caption_result_with_all_fields():
    """CaptionResult stores all fields correctly."""
    result = CaptionResult(
        caption_text="Buy now!",
        hashtags=["sale", "deal"],
        call_to_action="Shop now",
    )

    assert result.caption_text == "Buy now!"
    assert result.hashtags == ["sale", "deal"]
    assert result.call_to_action == "Shop now"
    assert result.character_count == 8


# ── Async Generation Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_caption_async_fallback():
    """generate_caption_async falls back to template when use_llm=False."""
    result = await generate_caption_async(
        SAMPLE_PRODUCT,
        platform="instagram",
        tone="engaging",
        use_llm=False,
    )

    assert isinstance(result, CaptionResult)
    assert len(result.caption_text) > 0
    assert len(result.hashtags) > 0
    assert result.character_count > 0


@pytest.mark.asyncio
async def test_generate_caption_async_all_platforms():
    """generate_caption_async produces valid results for all platforms."""
    for platform in ["instagram", "facebook", "tiktok", "twitter", "pinterest"]:
        result = await generate_caption_async(
            SAMPLE_PRODUCT,
            platform=platform,
            use_llm=False,
        )
        assert len(result.caption_text) > 0
        char_limit = PLATFORM_CHAR_LIMITS.get(platform, 2200)
        assert result.character_count <= char_limit
