"""
Product scoring service for TrendScout.

Calculates a weighted composite score (0-100) for each discovered product
across five dimensions: Social, Market, Competition, SEO, and Fundamentals.

Default weight distribution:
    - Social:       40%  (engagement metrics, trending indicators)
    - Market:       30%  (search volume, demand signals)
    - Competition:  15%  (number of sellers, saturation)
    - SEO:          10%  (keyword relevance, search ranking potential)
    - Fundamentals:  5%  (price range, margin potential, shipping feasibility)

For Developers:
    The `calculate_score` function accepts raw product data and an optional
    weight override dict. Each sub-score function extracts relevant signals
    from the raw data and normalizes them to 0-100. The final score is a
    weighted average clamped to [0, 100].

    Sub-score functions intentionally handle missing/malformed data gracefully
    by returning a neutral 50 when data is insufficient.

For Project Managers:
    The scoring algorithm determines how products are ranked in research
    results. Adjusting weights (via score_config on a run) lets users
    prioritize different aspects of product viability.

For QA Engineers:
    Test with balanced inputs (all sub-scores equal), skewed inputs
    (one dimension dominant), and edge cases (empty raw_data, all zeros).
    Verify the final score is always in [0, 100].

For End Users:
    Each product receives a score from 0 to 100 based on social buzz,
    market demand, competition level, SEO potential, and business
    fundamentals. Higher scores indicate stronger opportunities.
"""

# Default weight configuration — keys must match sub-score function names
DEFAULT_WEIGHTS: dict[str, float] = {
    "social": 0.40,
    "market": 0.30,
    "competition": 0.15,
    "seo": 0.10,
    "fundamentals": 0.05,
}

# Valid weight dimension names
VALID_DIMENSIONS = frozenset(DEFAULT_WEIGHTS.keys())


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """
    Clamp a numeric value to a range.

    Args:
        value: The value to clamp.
        low: Minimum allowed value.
        high: Maximum allowed value.

    Returns:
        The clamped value.
    """
    return max(low, min(high, value))


def _score_social(raw_data: dict) -> float:
    """
    Score the social/engagement dimension of a product.

    Evaluates engagement metrics like likes, shares, views, comments,
    and trending indicators from the raw data.

    Args:
        raw_data: The product's raw source data.

    Returns:
        Social sub-score from 0 to 100.
    """
    social = raw_data.get("social", {})
    if not social:
        return 50.0

    likes = social.get("likes", 0)
    shares = social.get("shares", 0)
    views = social.get("views", 0)
    comments = social.get("comments", 0)
    trending = social.get("trending", False)

    # Normalize engagement to 0-100 using log-scale thresholds
    engagement = likes + shares * 2 + comments * 1.5
    if engagement > 10000:
        engagement_score = 95.0
    elif engagement > 5000:
        engagement_score = 80.0
    elif engagement > 1000:
        engagement_score = 65.0
    elif engagement > 100:
        engagement_score = 45.0
    elif engagement > 10:
        engagement_score = 30.0
    else:
        engagement_score = 15.0

    # View-based reach score
    if views > 1_000_000:
        view_score = 90.0
    elif views > 100_000:
        view_score = 70.0
    elif views > 10_000:
        view_score = 50.0
    elif views > 1000:
        view_score = 35.0
    else:
        view_score = 20.0

    # Trending bonus
    trending_bonus = 15.0 if trending else 0.0

    score = (engagement_score * 0.5 + view_score * 0.3 + trending_bonus * 0.2)
    return _clamp(score + (10.0 if trending else 0.0))


def _score_market(raw_data: dict) -> float:
    """
    Score the market demand dimension of a product.

    Evaluates search volume, demand signals, order counts, and
    interest trends from the raw data.

    Args:
        raw_data: The product's raw source data.

    Returns:
        Market sub-score from 0 to 100.
    """
    market = raw_data.get("market", {})
    if not market:
        return 50.0

    search_volume = market.get("search_volume", 0)
    order_count = market.get("order_count", 0)
    growth_rate = market.get("growth_rate", 0.0)  # percentage 0-100+

    # Search volume score
    if search_volume > 100_000:
        sv_score = 95.0
    elif search_volume > 50_000:
        sv_score = 80.0
    elif search_volume > 10_000:
        sv_score = 65.0
    elif search_volume > 1000:
        sv_score = 45.0
    elif search_volume > 100:
        sv_score = 30.0
    else:
        sv_score = 15.0

    # Order count score
    if order_count > 10_000:
        oc_score = 90.0
    elif order_count > 5000:
        oc_score = 75.0
    elif order_count > 1000:
        oc_score = 60.0
    elif order_count > 100:
        oc_score = 40.0
    else:
        oc_score = 20.0

    # Growth rate score
    if growth_rate > 50:
        gr_score = 95.0
    elif growth_rate > 20:
        gr_score = 75.0
    elif growth_rate > 5:
        gr_score = 55.0
    elif growth_rate > 0:
        gr_score = 40.0
    else:
        gr_score = 20.0

    return _clamp(sv_score * 0.4 + oc_score * 0.35 + gr_score * 0.25)


def _score_competition(raw_data: dict) -> float:
    """
    Score the competition/saturation dimension of a product.

    Lower competition yields higher scores (less saturated = more opportunity).

    Args:
        raw_data: The product's raw source data.

    Returns:
        Competition sub-score from 0 to 100 (higher = less competition).
    """
    competition = raw_data.get("competition", {})
    if not competition:
        return 50.0

    seller_count = competition.get("seller_count", 0)
    saturation = competition.get("saturation", 0.5)  # 0-1 scale
    review_avg = competition.get("avg_review_rating", 4.0)

    # Fewer sellers = higher score (inverse relationship)
    if seller_count < 5:
        seller_score = 95.0
    elif seller_count < 20:
        seller_score = 80.0
    elif seller_count < 50:
        seller_score = 60.0
    elif seller_count < 200:
        seller_score = 40.0
    else:
        seller_score = 20.0

    # Lower saturation = higher score
    saturation_score = _clamp((1.0 - saturation) * 100)

    # Lower average review quality = easier to compete
    if review_avg < 3.5:
        review_score = 80.0
    elif review_avg < 4.0:
        review_score = 65.0
    elif review_avg < 4.5:
        review_score = 45.0
    else:
        review_score = 30.0

    return _clamp(seller_score * 0.5 + saturation_score * 0.3 + review_score * 0.2)


def _score_seo(raw_data: dict) -> float:
    """
    Score the SEO/discoverability dimension of a product.

    Evaluates keyword relevance, search ranking potential, and
    content optimization signals.

    Args:
        raw_data: The product's raw source data.

    Returns:
        SEO sub-score from 0 to 100.
    """
    seo = raw_data.get("seo", {})
    if not seo:
        return 50.0

    keyword_relevance = seo.get("keyword_relevance", 0.5)  # 0-1
    search_position = seo.get("search_position", 50)  # 1 = top
    content_quality = seo.get("content_quality", 0.5)  # 0-1

    # Keyword relevance (already 0-1)
    relevance_score = keyword_relevance * 100

    # Search position (lower = better)
    if search_position <= 3:
        position_score = 95.0
    elif search_position <= 10:
        position_score = 80.0
    elif search_position <= 25:
        position_score = 60.0
    elif search_position <= 50:
        position_score = 40.0
    else:
        position_score = 20.0

    # Content quality
    quality_score = content_quality * 100

    return _clamp(relevance_score * 0.4 + position_score * 0.35 + quality_score * 0.25)


def _score_fundamentals(raw_data: dict) -> float:
    """
    Score the business fundamentals dimension of a product.

    Evaluates price range, estimated margin potential, shipping feasibility,
    and product weight/dimensions.

    Args:
        raw_data: The product's raw source data.

    Returns:
        Fundamentals sub-score from 0 to 100.
    """
    fundamentals = raw_data.get("fundamentals", {})
    if not fundamentals:
        return 50.0

    price = fundamentals.get("price", 0)
    margin_percent = fundamentals.get("margin_percent", 0)  # 0-100
    shipping_days = fundamentals.get("shipping_days", 30)
    weight_kg = fundamentals.get("weight_kg", 1.0)

    # Price sweet spot: $10-$60 is ideal for dropshipping
    if 10 <= price <= 60:
        price_score = 90.0
    elif 5 <= price < 10 or 60 < price <= 100:
        price_score = 65.0
    elif 100 < price <= 200:
        price_score = 45.0
    else:
        price_score = 25.0

    # Margin: higher is better
    if margin_percent >= 60:
        margin_score = 95.0
    elif margin_percent >= 40:
        margin_score = 75.0
    elif margin_percent >= 25:
        margin_score = 55.0
    elif margin_percent >= 10:
        margin_score = 35.0
    else:
        margin_score = 15.0

    # Shipping: faster is better
    if shipping_days <= 7:
        shipping_score = 95.0
    elif shipping_days <= 14:
        shipping_score = 75.0
    elif shipping_days <= 21:
        shipping_score = 50.0
    else:
        shipping_score = 25.0

    # Weight: lighter is better for shipping cost
    if weight_kg < 0.5:
        weight_score = 90.0
    elif weight_kg < 1.0:
        weight_score = 70.0
    elif weight_kg < 3.0:
        weight_score = 50.0
    else:
        weight_score = 25.0

    return _clamp(
        price_score * 0.3
        + margin_score * 0.35
        + shipping_score * 0.2
        + weight_score * 0.15
    )


# Mapping of dimension names to their scoring functions
_SCORE_FUNCTIONS: dict[str, callable] = {
    "social": _score_social,
    "market": _score_market,
    "competition": _score_competition,
    "seo": _score_seo,
    "fundamentals": _score_fundamentals,
}


def calculate_score(
    raw_data: dict,
    config: dict | None = None,
) -> float:
    """
    Calculate the composite weighted product score.

    Runs each dimension's sub-score function on the raw data, then
    computes a weighted average using the provided (or default) weights.
    The final score is clamped to [0, 100].

    Args:
        raw_data: The product's raw source data containing dimension-specific
                  sub-dicts ('social', 'market', 'competition', 'seo',
                  'fundamentals').
        config: Optional weight overrides. Keys are dimension names with
                float values. Missing dimensions use default weights.
                Values are normalized so they sum to 1.0.

    Returns:
        Composite score from 0.0 to 100.0.
    """
    # Merge custom config with defaults
    weights = dict(DEFAULT_WEIGHTS)
    if config:
        for key, value in config.items():
            if key in VALID_DIMENSIONS and isinstance(value, (int, float)):
                weights[key] = float(value)

    # Normalize weights so they sum to 1.0
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights.items()}

    # Calculate weighted sum
    score = 0.0
    for dimension, weight in weights.items():
        score_fn = _SCORE_FUNCTIONS[dimension]
        sub_score = score_fn(raw_data)
        score += sub_score * weight

    return round(_clamp(score), 1)
