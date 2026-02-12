"""
AI analysis service for TrendScout product insights.

Generates structured product analysis using Claude (Anthropic) or
returns realistic mock analysis when no API key is configured.

The analysis covers: summary, opportunity score, risk factors,
recommended price range, target audience, and marketing angles.

For Developers:
    If `ANTHROPIC_API_KEY` is set in the environment, the service calls
    the Claude API via the Anthropic Python SDK. Otherwise it returns
    deterministic mock analysis derived from the product data. This makes
    local development and testing work without an API key.

    The mock analysis uses product title hashing for consistent outputs
    given the same input — this helps with snapshot testing.

For Project Managers:
    AI analysis is a premium feature. Free-tier users get basic scoring
    only; Pro and Enterprise users receive full AI-powered insights
    per result. When the API key is not configured, the system falls
    back to high-quality mock data for demos.

For QA Engineers:
    Test both mock mode (no API key) and real mode (with key). In mock
    mode, verify the response structure matches the AnalysisResult shape.
    In real mode, verify graceful degradation when the API is unreachable.

For End Users:
    Each research result can include an AI analysis with a summary,
    opportunity score, risk factors, pricing recommendations,
    target audience insights, and marketing angle suggestions.
"""

import hashlib
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Analysis response shape
AnalysisResult = dict[str, Any]


def _generate_mock_analysis(product_data: dict) -> AnalysisResult:
    """
    Generate deterministic mock AI analysis from product data.

    Uses a hash of the product title to produce consistent but varied
    mock responses for the same input. This is useful for testing and
    demo environments.

    Args:
        product_data: Dict with at least 'product_title' and optionally
                      'price', 'source', 'score'.

    Returns:
        Analysis dict matching the Claude output schema.
    """
    title = product_data.get("product_title", "Unknown Product")
    price = product_data.get("price", 19.99)
    source = product_data.get("source", "unknown")
    score = product_data.get("score", 50.0)

    # Use title hash for deterministic variety
    title_hash = int(hashlib.md5(title.encode()).hexdigest()[:8], 16)
    variety_index = title_hash % 5

    # Opportunity score derived from composite score with some variation
    opportunity = min(100, max(10, int(score * 0.9 + (variety_index * 4))))

    # Risk factors pool
    risk_pools = [
        [
            "High shipping times from overseas suppliers",
            "Potential quality control issues with budget products",
            "Seasonal demand fluctuations may affect sales",
        ],
        [
            "Intense competition from established sellers",
            "Thin margins require high volume for profitability",
            "Customer expectations may exceed product quality",
        ],
        [
            "Regulatory compliance required for certain markets",
            "Supply chain disruptions could affect availability",
            "Price wars with competitors may erode margins",
        ],
        [
            "Market trend may be short-lived (fad risk)",
            "Requires significant ad spend for visibility",
            "Returns rate historically high for this category",
        ],
        [
            "Intellectual property concerns with generic products",
            "Logistics complexity for fragile or oversized items",
            "Currency fluctuations impact supplier costs",
        ],
    ]

    # Marketing angles pool
    marketing_pools = [
        [
            "Leverage TikTok trends and short-form video content",
            "Create comparison content vs premium alternatives",
            "Target impulse buyers with urgency-driven campaigns",
        ],
        [
            "Focus on lifestyle imagery and aspirational messaging",
            "Partner with micro-influencers in the niche",
            "Use retargeting ads for abandoned cart recovery",
        ],
        [
            "Highlight unique features vs commodity alternatives",
            "Bundle with complementary products for higher AOV",
            "Seasonal gift-guide positioning for holiday periods",
        ],
        [
            "Target problem-solution messaging for pain points",
            "Create unboxing and review content for social proof",
            "Geographic targeting for markets with low competition",
        ],
        [
            "Use user-generated content for authentic promotion",
            "Position as an affordable premium alternative",
            "Leverage email marketing for repeat customer retention",
        ],
    ]

    # Target audience pool
    audience_pools = [
        "Budget-conscious millennials aged 25-34 interested in trending products",
        "Gen Z consumers aged 18-24 who discover products via social media",
        "Online shoppers aged 30-45 looking for value-for-money lifestyle items",
        "Tech-savvy consumers aged 22-38 who compare products before purchasing",
        "Gift shoppers aged 28-50 seeking unique and affordable presents",
    ]

    # Price range based on input price
    low_price = round(max(price * 1.5, price + 5), 2)
    high_price = round(max(price * 3.0, price + 20), 2)

    return {
        "summary": (
            f"'{title}' sourced from {source} shows "
            f"{'strong' if score >= 70 else 'moderate' if score >= 40 else 'limited'} "
            f"market potential with a composite score of {score:.0f}/100. "
            f"{'The product benefits from high social engagement and growing search interest.' if score >= 60 else 'Further market validation is recommended before committing significant ad spend.'}"
        ),
        "opportunity_score": opportunity,
        "risk_factors": risk_pools[variety_index],
        "recommended_price_range": {
            "low": low_price,
            "high": high_price,
            "currency": product_data.get("currency", "USD"),
        },
        "target_audience": audience_pools[variety_index],
        "marketing_angles": marketing_pools[variety_index],
    }


async def analyze_product(product_data: dict) -> AnalysisResult:
    """
    Generate AI-powered analysis for a product discovery.

    If ANTHROPIC_API_KEY is configured, sends product data to Claude for
    structured analysis. Otherwise returns mock analysis.

    Args:
        product_data: Dict containing at minimum:
            - product_title (str): The product name.
            - price (float): Product price.
            - source (str): Data source identifier.
            - score (float): Composite score from scoring service.
            - raw_data (dict): Full raw data from the source.

    Returns:
        AnalysisResult dict with keys:
            - summary (str): One-paragraph analysis summary.
            - opportunity_score (int): 0-100 opportunity rating.
            - risk_factors (list[str]): Key risk factors.
            - recommended_price_range (dict): {low, high, currency}.
            - target_audience (str): Description of ideal buyer persona.
            - marketing_angles (list[str]): Suggested marketing strategies.
    """
    if not settings.anthropic_api_key:
        logger.info("No Anthropic API key configured — returning mock analysis")
        return _generate_mock_analysis(product_data)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        prompt = f"""Analyze this product for dropshipping potential and return a structured JSON analysis.

Product Data:
- Title: {product_data.get('product_title', 'Unknown')}
- Price: {product_data.get('price', 'Unknown')} {product_data.get('currency', 'USD')}
- Source: {product_data.get('source', 'Unknown')}
- Composite Score: {product_data.get('score', 'Unknown')}/100
- Raw Data: {str(product_data.get('raw_data', {}))[:2000]}

Return a JSON object with exactly these keys:
1. "summary": A 2-3 sentence analysis of the product's dropshipping potential.
2. "opportunity_score": An integer 0-100 rating of the overall opportunity.
3. "risk_factors": A list of 3 specific risk factors (strings).
4. "recommended_price_range": An object with "low" (float), "high" (float), and "currency" (string) keys.
5. "target_audience": A one-sentence description of the ideal buyer persona.
6. "marketing_angles": A list of 3 specific marketing strategies (strings).

Return ONLY the JSON object, no markdown formatting."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the Claude response
        import json

        response_text = message.content[0].text
        analysis = json.loads(response_text)

        # Validate required keys exist
        required_keys = {
            "summary",
            "opportunity_score",
            "risk_factors",
            "recommended_price_range",
            "target_audience",
            "marketing_angles",
        }
        if not required_keys.issubset(analysis.keys()):
            logger.warning("Claude response missing keys, falling back to mock")
            return _generate_mock_analysis(product_data)

        return analysis

    except Exception as e:
        logger.error(f"AI analysis failed: {e}. Falling back to mock analysis.")
        return _generate_mock_analysis(product_data)
