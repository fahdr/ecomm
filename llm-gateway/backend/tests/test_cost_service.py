"""
Tests for the cost calculation service.

For Developers:
    Unit tests for the ``calculate_cost()`` function with various
    provider/model combinations.

For QA Engineers:
    Verify that cost calculations are reasonable and match known pricing.
"""

import pytest

from app.services.cost_service import calculate_cost


def test_claude_sonnet_cost():
    """Claude Sonnet pricing: $3/M input, $15/M output."""
    cost = calculate_cost("claude", "claude-sonnet-4-5-20250929", 1000, 500)
    expected = (1000 * 3.00 + 500 * 15.00) / 1_000_000
    assert cost == pytest.approx(expected, abs=0.0001)


def test_openai_gpt4o_cost():
    """GPT-4o pricing: $2.50/M input, $10/M output."""
    cost = calculate_cost("openai", "gpt-4o", 1000, 500)
    expected = (1000 * 2.50 + 500 * 10.00) / 1_000_000
    assert cost == pytest.approx(expected, abs=0.0001)


def test_gemini_flash_cost():
    """Gemini 2.0 Flash pricing: $0.10/M input, $0.40/M output."""
    cost = calculate_cost("gemini", "gemini-2.0-flash", 5000, 2000)
    expected = (5000 * 0.10 + 2000 * 0.40) / 1_000_000
    assert cost == pytest.approx(expected, abs=0.0001)


def test_unknown_model_fallback():
    """Unknown model falls back to provider's first pricing entry."""
    cost = calculate_cost("claude", "claude-unknown-model", 1000, 500)
    # Falls back to first claude entry: haiku ($0.80/$4.00)
    expected = (1000 * 0.80 + 500 * 4.00) / 1_000_000
    assert cost == pytest.approx(expected, abs=0.0001)


def test_unknown_provider_fallback():
    """Unknown provider uses default pricing."""
    cost = calculate_cost("unknown", "some-model", 1000, 500)
    # Default: $1.00/M input, $3.00/M output
    expected = (1000 * 1.00 + 500 * 3.00) / 1_000_000
    assert cost == pytest.approx(expected, abs=0.0001)


def test_zero_tokens():
    """Zero tokens costs zero."""
    assert calculate_cost("claude", "claude-sonnet-4-5-20250929", 0, 0) == 0.0
