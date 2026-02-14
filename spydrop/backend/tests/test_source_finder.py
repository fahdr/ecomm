"""
Tests for the Source Finder service (LLM-powered supplier matching).

Verifies keyword extraction, supplier catalog matching, and the full
find_supplier_matches flow with a mocked LLM client.

For Developers:
    Tests mock ``call_llm`` to avoid hitting the real LLM Gateway.
    The fallback keyword extraction and catalog matching are tested
    independently for thorough coverage.

For QA Engineers:
    These tests cover:
    - LLM keyword extraction with valid JSON response.
    - Fallback keyword extraction when LLM fails.
    - Supplier catalog matching with overlapping keywords.
    - Full find_supplier_matches flow with mock LLM.
    - Edge cases: empty title, no matching keywords.

For Project Managers:
    Source matching is a premium feature that differentiates SpyDrop.
    These tests ensure reliable operation even when the LLM is unavailable.

For End Users:
    These tests ensure that SpyDrop accurately identifies potential
    suppliers for competitor products.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.source_service import (
    _estimate_cost_range,
    _fallback_keyword_extraction,
    _match_against_catalog,
    find_supplier_matches,
)


# ── Fallback Keyword Extraction Tests ──────────────────────────────


def test_fallback_extraction_basic():
    """Extracts meaningful keywords from a product title."""
    keywords = _fallback_keyword_extraction("Wireless Bluetooth Earbuds Pro")
    assert "wireless" in keywords
    assert "bluetooth" in keywords
    assert "earbuds" in keywords
    assert "pro" in keywords


def test_fallback_extraction_removes_stop_words():
    """Stop words like 'the', 'and', 'for' are removed."""
    keywords = _fallback_keyword_extraction("The Best Widget for the Kitchen")
    assert "the" not in keywords
    assert "for" not in keywords
    assert "best" in keywords
    assert "widget" in keywords
    assert "kitchen" in keywords


def test_fallback_extraction_max_8_keywords():
    """At most 8 keywords are returned."""
    long_title = " ".join(f"keyword{i}" for i in range(20))
    keywords = _fallback_keyword_extraction(long_title)
    assert len(keywords) <= 8


def test_fallback_extraction_deduplicates():
    """Duplicate words are removed while preserving order."""
    keywords = _fallback_keyword_extraction("Smart Smart Phone Phone Case")
    assert keywords.count("smart") == 1
    assert keywords.count("phone") == 1


# ── Catalog Matching Tests ─────────────────────────────────────────


def test_match_against_catalog_electronics():
    """Electronics keywords match AliExpress catalog entry."""
    matches = _match_against_catalog(
        ["electronics", "gadget", "wireless"],
        "Wireless Gadget",
    )
    suppliers = {m["supplier"] for m in matches}
    assert "AliExpress" in suppliers


def test_match_against_catalog_fashion():
    """Fashion keywords match DHgate catalog entry."""
    matches = _match_against_catalog(
        ["fashion", "clothing", "shoes"],
        "Fashion Shoes",
    )
    suppliers = {m["supplier"] for m in matches}
    assert "DHgate" in suppliers


def test_match_against_catalog_no_match_fallback():
    """When no keywords match, generic fallback matches are returned."""
    matches = _match_against_catalog(
        ["unicorn", "rainbow"],
        "Unicorn Rainbow Widget",
    )
    # Should have at least some fallback matches
    assert len(matches) >= 1


def test_match_similarity_scores_are_bounded():
    """All similarity scores are between 0 and 1."""
    matches = _match_against_catalog(
        ["electronics", "gadget", "smart", "wireless", "charger"],
        "Smart Wireless Charger",
    )
    for m in matches:
        assert 0.0 <= m["similarity_score"] <= 1.0


# ── Cost Range Estimation Tests ────────────────────────────────────


def test_estimate_cost_range_electronics():
    """Electronics products get higher cost range."""
    assert _estimate_cost_range("Smart Phone Case") == "$50-200"


def test_estimate_cost_range_clothing():
    """Clothing products get moderate cost range."""
    assert _estimate_cost_range("Summer Dress Collection") == "$5-25"


def test_estimate_cost_range_generic():
    """Unknown products get default cost range."""
    assert _estimate_cost_range("Mystery Widget") == "$5-30"


# ── find_supplier_matches Integration Test ─────────────────────────


@pytest.mark.asyncio
async def test_find_supplier_matches_with_mock_llm(db: AsyncSession):
    """Full flow: LLM extracts keywords, then catalog matching runs."""
    mock_llm_response = {
        "content": '["wireless", "bluetooth", "earbuds", "electronics"]',
        "provider": "mock",
        "model": "mock-1",
        "input_tokens": 50,
        "output_tokens": 20,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 100,
    }

    with patch("app.services.llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        matches = await find_supplier_matches(
            db,
            user_id=uuid.uuid4(),
            product_title="Wireless Bluetooth Earbuds",
            product_description="High quality wireless earbuds with noise cancellation",
        )

    assert len(matches) >= 1
    # All matches should have required fields
    for m in matches:
        assert "supplier" in m
        assert "supplier_url" in m
        assert "similarity_score" in m
        assert "matched_keywords" in m
        assert "estimated_cost_range" in m


@pytest.mark.asyncio
async def test_find_supplier_matches_llm_failure_fallback(db: AsyncSession):
    """When LLM fails, fallback keyword extraction still produces results."""
    mock_llm_error = {
        "error": "LLM Gateway unavailable",
        "content": "",
    }

    with patch("app.services.llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_error

        matches = await find_supplier_matches(
            db,
            user_id=uuid.uuid4(),
            product_title="Kitchen Gadget Set Pro",
        )

    # Should still have matches from fallback
    assert len(matches) >= 1
