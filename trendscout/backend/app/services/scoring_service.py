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


# ─── Enhanced Product Scoring ───────────────────────────────────────
#
# The enhanced scoring system evaluates products using dropshipping-
# specific dimensions with configurable weights.  It can operate on
# either raw source data or structured product dicts.


ENHANCED_DEFAULT_WEIGHTS: dict[str, float] = {
    "profit_margin": 0.30,
    "demand_signal": 0.25,
    "competition": 0.20,
    "trend_velocity": 0.15,
    "quality": 0.10,
}
"""
Enhanced scoring weight configuration for dropshipping product evaluation.

For Project Managers:
    These weights reflect the priority order for product viability:
    profit margin is most important, followed by demand signals.

For End Users:
    Customize these weights in your research run settings to
    prioritize what matters most to your business.
"""

VALID_ENHANCED_DIMENSIONS = frozenset(ENHANCED_DEFAULT_WEIGHTS.keys())


def _score_profit_margin(product_data: dict) -> float:
    """
    Score the profit margin potential of a product.

    Calculates margin as (sell_price - supplier_cost) / sell_price
    when both values are available, otherwise falls back to the
    ``margin_percent`` field in fundamentals.

    Args:
        product_data: Product data dict with optional ``sell_price``,
                      ``supplier_cost``, or nested ``fundamentals.margin_percent``.

    Returns:
        Profit margin sub-score from 0 to 100.
    """
    sell_price = product_data.get("sell_price", 0)
    supplier_cost = product_data.get("supplier_cost", 0)

    if sell_price > 0 and supplier_cost > 0:
        margin = (sell_price - supplier_cost) / sell_price * 100
    else:
        # Fallback to fundamentals data
        fundamentals = product_data.get("fundamentals", {})
        if isinstance(fundamentals, dict):
            margin = fundamentals.get("margin_percent", 0)
        else:
            margin = 0

    if margin >= 60:
        return 95.0
    elif margin >= 45:
        return 80.0
    elif margin >= 30:
        return 65.0
    elif margin >= 15:
        return 45.0
    elif margin > 0:
        return 25.0
    else:
        return 10.0


def _score_demand_signal(product_data: dict) -> float:
    """
    Score the demand signal strength for a product.

    Evaluates search volume, order count, and growth rate from
    the market data sub-dict.

    Args:
        product_data: Product data dict with optional ``market`` sub-dict.

    Returns:
        Demand signal sub-score from 0 to 100.
    """
    market = product_data.get("market", {})
    if not isinstance(market, dict) or not market:
        return 50.0

    search_volume = market.get("search_volume", 0)
    order_count = market.get("order_count", 0)

    # Normalize search volume
    if search_volume > 100_000:
        sv = 95.0
    elif search_volume > 50_000:
        sv = 80.0
    elif search_volume > 10_000:
        sv = 65.0
    elif search_volume > 1_000:
        sv = 45.0
    else:
        sv = 20.0

    # Normalize order count
    if order_count > 10_000:
        oc = 90.0
    elif order_count > 5_000:
        oc = 75.0
    elif order_count > 1_000:
        oc = 60.0
    elif order_count > 100:
        oc = 40.0
    else:
        oc = 20.0

    return _clamp(sv * 0.55 + oc * 0.45)


def _score_enhanced_competition(product_data: dict) -> float:
    """
    Score the competition level for a product (lower competition = higher score).

    Args:
        product_data: Product data dict with optional ``competition`` sub-dict.

    Returns:
        Competition sub-score from 0 to 100 (higher = less competition).
    """
    competition = product_data.get("competition", {})
    if not isinstance(competition, dict) or not competition:
        return 50.0

    seller_count = competition.get("seller_count", 0)
    saturation = competition.get("saturation", 0.5)

    if seller_count < 5:
        sc = 95.0
    elif seller_count < 20:
        sc = 80.0
    elif seller_count < 50:
        sc = 60.0
    elif seller_count < 200:
        sc = 40.0
    else:
        sc = 20.0

    sat_score = _clamp((1.0 - saturation) * 100)
    return _clamp(sc * 0.6 + sat_score * 0.4)


def _score_trend_velocity(product_data: dict) -> float:
    """
    Score the trend velocity — how fast interest is growing.

    Compares recent volume against historical volume when available,
    otherwise uses the growth_rate from market data.

    Args:
        product_data: Product data dict with optional ``recent_volume``,
                      ``historical_volume``, or ``market.growth_rate``.

    Returns:
        Trend velocity sub-score from 0 to 100.
    """
    recent = product_data.get("recent_volume", 0)
    historical = product_data.get("historical_volume", 0)

    if recent > 0 and historical > 0:
        velocity = ((recent - historical) / historical) * 100
    else:
        market = product_data.get("market", {})
        if isinstance(market, dict):
            velocity = market.get("growth_rate", 0)
        else:
            velocity = 0

    if velocity > 100:
        return 95.0
    elif velocity > 50:
        return 80.0
    elif velocity > 20:
        return 65.0
    elif velocity > 5:
        return 50.0
    elif velocity > 0:
        return 35.0
    else:
        return 15.0


def _score_quality(product_data: dict) -> float:
    """
    Score the product quality indicators.

    Evaluates review ratings, content quality, and shipping speed.

    Args:
        product_data: Product data dict with optional ``competition``,
                      ``seo``, and ``fundamentals`` sub-dicts.

    Returns:
        Quality sub-score from 0 to 100.
    """
    competition = product_data.get("competition", {})
    seo = product_data.get("seo", {})
    fundamentals = product_data.get("fundamentals", {})

    if not isinstance(competition, dict):
        competition = {}
    if not isinstance(seo, dict):
        seo = {}
    if not isinstance(fundamentals, dict):
        fundamentals = {}

    review_rating = competition.get("avg_review_rating", 3.5)
    content_quality = seo.get("content_quality", 0.5)
    shipping_days = fundamentals.get("shipping_days", 21)

    # Review rating score (higher = better quality)
    if review_rating >= 4.5:
        review_score = 90.0
    elif review_rating >= 4.0:
        review_score = 70.0
    elif review_rating >= 3.5:
        review_score = 50.0
    else:
        review_score = 30.0

    content_score = _clamp(content_quality * 100)

    if shipping_days <= 7:
        ship_score = 90.0
    elif shipping_days <= 14:
        ship_score = 70.0
    elif shipping_days <= 21:
        ship_score = 50.0
    else:
        ship_score = 25.0

    return _clamp(review_score * 0.4 + content_score * 0.3 + ship_score * 0.3)


_ENHANCED_SCORE_FUNCTIONS: dict[str, callable] = {
    "profit_margin": _score_profit_margin,
    "demand_signal": _score_demand_signal,
    "competition": _score_enhanced_competition,
    "trend_velocity": _score_trend_velocity,
    "quality": _score_quality,
}
"""Mapping of enhanced dimension names to their scoring functions."""


def score_product(
    product_data: dict,
    config: dict | None = None,
) -> float:
    """
    Calculate an enhanced composite product score using dropshipping-specific
    dimensions.

    Runs each enhanced dimension's sub-score function on the product data,
    then computes a weighted average.  The final score is clamped to [0, 100].

    For Developers:
        This is the preferred scoring entry point for new research pipelines.
        The older ``calculate_score`` remains for backward compatibility with
        existing Celery tasks and mock data generators.

    For QA Engineers:
        Test with complete product data, partial data (missing dimensions),
        and edge cases (all zeros, negative growth rates, zero price).

    For End Users:
        Products are scored from 0 to 100 based on profit potential,
        demand strength, competition level, trend momentum, and quality
        indicators.

    Args:
        product_data: Product data dict. May contain top-level keys
                      (``sell_price``, ``supplier_cost``, ``recent_volume``,
                      ``historical_volume``) and/or sub-dicts (``market``,
                      ``competition``, ``seo``, ``fundamentals``).
        config: Optional weight overrides. Keys are dimension names from
                ``ENHANCED_DEFAULT_WEIGHTS`` with float values.

    Returns:
        Composite score from 0.0 to 100.0, rounded to one decimal.
    """
    weights = dict(ENHANCED_DEFAULT_WEIGHTS)
    if config:
        for key, value in config.items():
            if key in VALID_ENHANCED_DIMENSIONS and isinstance(value, (int, float)):
                weights[key] = float(value)

    # Normalize weights
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights.items()}

    score = 0.0
    for dimension, weight in weights.items():
        score_fn = _ENHANCED_SCORE_FUNCTIONS[dimension]
        sub_score = score_fn(product_data)
        score += sub_score * weight

    return round(_clamp(score), 1)
