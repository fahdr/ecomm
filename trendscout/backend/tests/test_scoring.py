"""
Tests for the enhanced product scoring service.

Covers the configurable weight system, individual dimension scoring
functions, and the composite score_product function.

For Developers:
    These are pure unit tests — no database or network access needed.
    Each test verifies a specific scoring dimension or the composite
    calculation with various product data inputs.

For QA Engineers:
    These tests verify:
    - Default weights produce consistent scores.
    - Custom weight overrides change the composite score.
    - Each dimension handles missing data gracefully (returns ~50).
    - Profit margin calculation from sell_price/supplier_cost.
    - Trend velocity from recent/historical volume comparison.
    - Edge cases: empty data, zero prices, negative growth.
    - Score is always clamped to [0, 100].

For Project Managers:
    The scoring algorithm determines product ranking in research results.
    These tests ensure the algorithm is deterministic and handles
    all real-world data variations correctly.
"""

import pytest

from app.services.scoring_service import (
    _clamp,
    _score_profit_margin,
    _score_demand_signal,
    _score_enhanced_competition,
    _score_trend_velocity,
    _score_quality,
    calculate_score,
    score_product,
    ENHANCED_DEFAULT_WEIGHTS,
)


# ─── Clamp Function Tests ──────────────────────────────────────────


def test_clamp_within_range():
    """_clamp returns value unchanged when within bounds."""
    assert _clamp(50.0) == 50.0


def test_clamp_below_minimum():
    """_clamp returns minimum when value is below range."""
    assert _clamp(-10.0) == 0.0


def test_clamp_above_maximum():
    """_clamp returns maximum when value is above range."""
    assert _clamp(150.0) == 100.0


# ─── Profit Margin Scoring ─────────────────────────────────────────


def test_profit_margin_from_prices():
    """_score_profit_margin calculates margin from sell_price and supplier_cost."""
    # 60% margin: (50 - 20) / 50 = 0.6
    data = {"sell_price": 50.0, "supplier_cost": 20.0}
    score = _score_profit_margin(data)
    assert score == 95.0  # >= 60% margin


def test_profit_margin_low_margin():
    """_score_profit_margin returns low score for thin margins."""
    # 10% margin: (10 - 9) / 10 = 0.1
    data = {"sell_price": 10.0, "supplier_cost": 9.0}
    score = _score_profit_margin(data)
    assert score == 25.0  # margin > 0 but < 15%


def test_profit_margin_from_fundamentals():
    """_score_profit_margin falls back to fundamentals.margin_percent."""
    data = {"fundamentals": {"margin_percent": 45}}
    score = _score_profit_margin(data)
    assert score == 80.0  # >= 45%


def test_profit_margin_no_data():
    """_score_profit_margin returns lowest score for missing data."""
    score = _score_profit_margin({})
    assert score == 10.0  # margin = 0


def test_profit_margin_zero_sell_price():
    """_score_profit_margin handles zero sell_price gracefully."""
    data = {"sell_price": 0, "supplier_cost": 10.0}
    score = _score_profit_margin(data)
    assert 0 <= score <= 100


# ─── Demand Signal Scoring ─────────────────────────────────────────


def test_demand_signal_high():
    """_score_demand_signal returns high score for strong demand."""
    data = {"market": {"search_volume": 200_000, "order_count": 15_000}}
    score = _score_demand_signal(data)
    assert score > 80.0


def test_demand_signal_low():
    """_score_demand_signal returns low score for weak demand."""
    data = {"market": {"search_volume": 50, "order_count": 10}}
    score = _score_demand_signal(data)
    assert score < 25.0


def test_demand_signal_no_data():
    """_score_demand_signal returns neutral 50 for missing data."""
    score = _score_demand_signal({})
    assert score == 50.0


# ─── Competition Scoring ───────────────────────────────────────────


def test_competition_low():
    """_score_enhanced_competition returns high score for low competition."""
    data = {"competition": {"seller_count": 3, "saturation": 0.1}}
    score = _score_enhanced_competition(data)
    assert score > 85.0


def test_competition_high():
    """_score_enhanced_competition returns low score for high competition."""
    data = {"competition": {"seller_count": 500, "saturation": 0.9}}
    score = _score_enhanced_competition(data)
    assert score < 25.0


def test_competition_no_data():
    """_score_enhanced_competition returns neutral 50 for missing data."""
    score = _score_enhanced_competition({})
    assert score == 50.0


# ─── Trend Velocity Scoring ────────────────────────────────────────


def test_trend_velocity_from_volumes():
    """_score_trend_velocity calculates from recent vs historical volume."""
    # 200% growth: (300 - 100) / 100 = 2.0 = 200%
    data = {"recent_volume": 300, "historical_volume": 100}
    score = _score_trend_velocity(data)
    assert score == 95.0  # > 100%


def test_trend_velocity_moderate():
    """_score_trend_velocity returns moderate score for 25% growth."""
    # 25% growth
    data = {"recent_volume": 125, "historical_volume": 100}
    score = _score_trend_velocity(data)
    assert score == 65.0  # > 20%


def test_trend_velocity_from_growth_rate():
    """_score_trend_velocity falls back to market.growth_rate."""
    data = {"market": {"growth_rate": 30}}
    score = _score_trend_velocity(data)
    assert score == 65.0  # > 20%


def test_trend_velocity_negative():
    """_score_trend_velocity returns low score for negative growth."""
    data = {"market": {"growth_rate": -10}}
    score = _score_trend_velocity(data)
    assert score == 15.0


def test_trend_velocity_no_data():
    """_score_trend_velocity returns low score for missing data (0 growth)."""
    score = _score_trend_velocity({})
    assert score == 15.0  # velocity = 0


# ─── Quality Scoring ───────────────────────────────────────────────


def test_quality_high():
    """_score_quality returns high score for quality product indicators."""
    data = {
        "competition": {"avg_review_rating": 4.7},
        "seo": {"content_quality": 0.9},
        "fundamentals": {"shipping_days": 5},
    }
    score = _score_quality(data)
    assert score > 75.0


def test_quality_low():
    """_score_quality returns low score for poor quality indicators."""
    data = {
        "competition": {"avg_review_rating": 2.5},
        "seo": {"content_quality": 0.2},
        "fundamentals": {"shipping_days": 45},
    }
    score = _score_quality(data)
    assert score < 35.0


def test_quality_no_data():
    """_score_quality handles all-empty data gracefully."""
    score = _score_quality({})
    assert 0 <= score <= 100


# ─── Composite score_product Tests ─────────────────────────────────


def test_score_product_with_full_data():
    """score_product returns a reasonable score for complete product data."""
    data = {
        "sell_price": 50.0,
        "supplier_cost": 15.0,
        "market": {
            "search_volume": 50_000,
            "order_count": 5_000,
            "growth_rate": 25.0,
        },
        "competition": {
            "seller_count": 15,
            "saturation": 0.3,
            "avg_review_rating": 4.2,
        },
        "seo": {
            "keyword_relevance": 0.8,
            "content_quality": 0.7,
        },
        "fundamentals": {
            "margin_percent": 70,
            "shipping_days": 10,
            "weight_kg": 0.5,
        },
    }
    score = score_product(data)
    assert 0 <= score <= 100
    assert score > 50  # Good product should score above average


def test_score_product_with_custom_weights():
    """score_product applies custom weight overrides."""
    data = {
        "sell_price": 100.0,
        "supplier_cost": 10.0,  # 90% margin
        "market": {"search_volume": 10, "order_count": 0},  # Very low demand
    }

    # Weight heavily toward profit margin
    margin_focused = score_product(data, config={"profit_margin": 0.9, "demand_signal": 0.1})

    # Weight heavily toward demand
    demand_focused = score_product(data, config={"profit_margin": 0.1, "demand_signal": 0.9})

    # High margin but low demand: margin-focused should score higher
    assert margin_focused > demand_focused


def test_score_product_empty_data():
    """score_product handles empty data dict without crashing."""
    score = score_product({})
    assert 0 <= score <= 100


def test_score_product_always_in_range():
    """score_product always returns a value between 0 and 100."""
    test_cases = [
        {},
        {"sell_price": 0, "supplier_cost": 0},
        {"market": {"search_volume": 999_999_999}},
        {"competition": {"seller_count": 0, "saturation": 0}},
        {"recent_volume": 1_000_000, "historical_volume": 1},
    ]
    for data in test_cases:
        score = score_product(data)
        assert 0 <= score <= 100, f"Score {score} out of range for {data}"


# ─── Legacy calculate_score Backward Compatibility ─────────────────


def test_calculate_score_still_works():
    """calculate_score (legacy) still produces valid scores."""
    raw_data = {
        "social": {"likes": 5000, "shares": 1000, "views": 100000, "trending": True},
        "market": {"search_volume": 50000, "order_count": 5000, "growth_rate": 20},
        "competition": {"seller_count": 20, "saturation": 0.3, "avg_review_rating": 4.0},
        "seo": {"keyword_relevance": 0.8, "search_position": 5, "content_quality": 0.7},
        "fundamentals": {"price": 30, "margin_percent": 50, "shipping_days": 10, "weight_kg": 0.5},
    }
    score = calculate_score(raw_data)
    assert 0 <= score <= 100
    assert score > 50  # Strong product should score well


def test_enhanced_weights_sum_to_one():
    """ENHANCED_DEFAULT_WEIGHTS values sum to approximately 1.0."""
    total = sum(ENHANCED_DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001
