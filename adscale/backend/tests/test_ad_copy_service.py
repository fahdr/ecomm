"""
Tests for the ad copy generation service.

Validates AI-powered ad copy generation with platform-specific constraints,
LLM response parsing, and template fallback behavior.

For Developers:
    Tests mock ``call_llm`` to avoid real LLM Gateway calls.  The mock
    returns structured JSON matching what the gateway would return.

For QA Engineers:
    Covers: Google Ads copy (character limits), Meta Ads copy, TikTok copy,
    LLM failure fallback, response parsing (valid JSON, invalid JSON),
    variant generation, and platform constraint enforcement.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.ad_copy_service import (
    AdCopyResult,
    PLATFORM_CONSTRAINTS,
    _fallback_ad_copy,
    _get_system_prompt,
    _parse_llm_response,
    generate_ad_copy,
    generate_ad_variants,
)


# ── Unit Tests (no DB needed) ────────────────────────────────────────


def test_fallback_ad_copy_google():
    """Fallback generates copy within Google Ads constraints."""
    product_data = {
        "name": "Running Shoes",
        "description": "Lightweight running shoes for marathon training",
        "price": 99.99,
    }
    result = _fallback_ad_copy(product_data, "google_ads")

    assert isinstance(result, AdCopyResult)
    assert len(result.headlines) >= 1
    assert len(result.descriptions) >= 1
    assert len(result.call_to_actions) >= 1
    # All headlines within Google 30-char limit
    for h in result.headlines:
        assert len(h) <= 30


def test_fallback_ad_copy_no_price():
    """Fallback handles missing price gracefully."""
    product_data = {"name": "Widget", "description": "A useful widget"}
    result = _fallback_ad_copy(product_data, "meta_ads")

    assert isinstance(result, AdCopyResult)
    assert len(result.headlines) >= 1


def test_get_system_prompt_google():
    """System prompt for Google Ads includes character limits."""
    prompt = _get_system_prompt("google_ads")
    assert "30" in prompt  # headline limit
    assert "90" in prompt  # description limit


def test_get_system_prompt_meta():
    """System prompt for Meta Ads includes its specific constraints."""
    prompt = _get_system_prompt("meta_ads")
    assert "125" in prompt  # primary text limit
    assert "40" in prompt   # headline limit


def test_get_system_prompt_tiktok():
    """System prompt for TikTok Ads mentions short punchy format."""
    prompt = _get_system_prompt("tiktok_ads")
    assert "50" in prompt   # headline limit
    assert "100" in prompt  # description limit


def test_get_system_prompt_unknown_defaults_to_google():
    """Unknown platform falls back to Google Ads format."""
    prompt = _get_system_prompt("unknown_platform")
    assert "30" in prompt


def test_parse_llm_response_valid_json():
    """Parsing valid JSON response returns correct AdCopyResult."""
    content = json.dumps({
        "headlines": ["Buy Now", "Great Deal", "Save Big"],
        "descriptions": ["Amazing product at a great price"],
        "call_to_actions": ["Shop Now"],
        "display_url_path": "/shop/product",
    })

    result = _parse_llm_response(content, "google_ads")
    assert len(result.headlines) == 3
    assert result.headlines[0] == "Buy Now"
    assert len(result.descriptions) == 1
    assert result.display_url_path == "/shop/product"


def test_parse_llm_response_enforces_constraints():
    """Parsing enforces platform-specific character limits."""
    content = json.dumps({
        "headlines": ["This is a very long headline that exceeds thirty characters"],
        "descriptions": ["Short desc"],
        "call_to_actions": ["Buy"],
    })

    result = _parse_llm_response(content, "google_ads")
    # Google limit is 30 chars
    for h in result.headlines:
        assert len(h) <= 30


def test_parse_llm_response_markdown_code_block():
    """Parsing handles JSON wrapped in markdown code blocks."""
    content = '```json\n{"headlines": ["Test"], "descriptions": ["Desc"], "call_to_actions": ["Buy"]}\n```'

    result = _parse_llm_response(content, "google_ads")
    assert result.headlines == ["Test"]


def test_parse_llm_response_invalid_json():
    """Parsing gracefully handles non-JSON responses."""
    content = "This is plain text, not JSON at all."
    result = _parse_llm_response(content, "google_ads")

    assert len(result.headlines) >= 1
    assert len(result.descriptions) >= 1
    assert result.call_to_actions == ["Shop Now"]


# ── Integration Tests (mock LLM) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_ad_copy_success(db):
    """generate_ad_copy returns parsed LLM output on success."""
    mock_llm_response = {
        "content": json.dumps({
            "headlines": ["Buy Shoes", "Best Shoes", "Shop Shoes"],
            "descriptions": ["Premium running shoes for athletes"],
            "call_to_actions": ["Shop Now", "Buy Now"],
            "display_url_path": "/shop/shoes",
        }),
        "provider": "claude",
        "model": "test",
    }

    with patch("app.services.ad_copy_service.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await generate_ad_copy(
            db=db,
            user_id="test-user",
            product_data={"name": "Running Shoes", "description": "Fast shoes"},
            platform="google_ads",
        )

    assert isinstance(result, AdCopyResult)
    assert len(result.headlines) >= 1
    assert "Shoes" in result.headlines[0] or "shoes" in result.headlines[0].lower()
    mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_ad_copy_llm_failure_fallback(db):
    """generate_ad_copy falls back to templates when LLM is unavailable."""
    from app.services.llm_client import LLMGatewayError

    with patch("app.services.ad_copy_service.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMGatewayError("Gateway down")

        result = await generate_ad_copy(
            db=db,
            user_id="test-user",
            product_data={"name": "Running Shoes", "description": "Fast shoes"},
            platform="google_ads",
        )

    assert isinstance(result, AdCopyResult)
    assert len(result.headlines) >= 1
    assert any("Shoes" in h for h in result.headlines)


@pytest.mark.asyncio
async def test_generate_ad_variants_returns_multiple(db):
    """generate_ad_variants returns the requested number of variants."""
    from app.services.llm_client import LLMGatewayError

    # Use fallback for predictable results
    with patch("app.services.ad_copy_service.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMGatewayError("Gateway down")

        variants = await generate_ad_variants(
            db=db,
            user_id="test-user",
            product_data={"name": "Widget", "description": "Cool widget"},
            platform="meta_ads",
            count=3,
        )

    assert len(variants) == 3
    assert all(isinstance(v, AdCopyResult) for v in variants)


@pytest.mark.asyncio
async def test_generate_ad_variants_caps_at_10(db):
    """generate_ad_variants caps variant count at 10."""
    from app.services.llm_client import LLMGatewayError

    with patch("app.services.ad_copy_service.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMGatewayError("Gateway down")

        variants = await generate_ad_variants(
            db=db,
            user_id="test-user",
            product_data={"name": "Widget", "description": "Cool widget"},
            platform="google_ads",
            count=20,  # Should be capped to 10
        )

    assert len(variants) == 10
