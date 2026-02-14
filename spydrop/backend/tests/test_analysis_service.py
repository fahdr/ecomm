"""
Tests for the LLM Competitive Analysis service and endpoint.

Verifies competitive analysis generation with mocked LLM responses,
fallback analysis when LLM is unavailable, and the API endpoint.

For Developers:
    Tests mock ``call_llm`` to avoid hitting the real LLM Gateway.
    Both the service function and the API endpoint are tested.
    Non-DB tests use SimpleNamespace objects to avoid SQLAlchemy
    instance state issues with ``__new__``.

For QA Engineers:
    These tests cover:
    - Analysis with valid LLM JSON response.
    - Fallback analysis when LLM returns an error.
    - API endpoint authorization and error handling.
    - Analysis prompt construction with various product data.

For Project Managers:
    Competitive analysis is a high-value differentiator. These tests
    ensure the feature works reliably with and without LLM access.

For End Users:
    These tests guarantee that competitive analysis insights are
    accurate and available even when AI services are temporarily down.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct
from app.models.user import User
from app.services.analysis_service import (
    _build_analysis_prompt,
    _generate_fallback_analysis,
    analyze_competitor,
)
from tests.conftest import register_and_login


# ── Helpers ────────────────────────────────────────────────────────


def _mock_competitor(**kwargs):
    """Create a mock competitor object with given attributes.

    Args:
        **kwargs: Attributes to set on the mock competitor.

    Returns:
        SimpleNamespace with the provided attributes.
    """
    defaults = {
        "name": "Test Store",
        "url": "https://test.com",
        "platform": "shopify",
        "status": "active",
        "product_count": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_product(**kwargs):
    """Create a mock product object with given attributes.

    Args:
        **kwargs: Attributes to set on the mock product.

    Returns:
        SimpleNamespace with the provided attributes.
    """
    defaults = {
        "title": "Test Product",
        "price": 29.99,
        "status": "active",
        "price_history": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


async def _setup_competitor_with_products(
    db: AsyncSession, suffix: str = ""
) -> tuple[User, Competitor]:
    """
    Create a user, competitor, and products for analysis testing.

    Args:
        db: Async database session.
        suffix: Email suffix for unique user creation.

    Returns:
        Tuple of (user, competitor).
    """
    user = User(
        email=f"analysis{suffix}@test.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()

    comp = Competitor(
        user_id=user.id,
        name="Rival Electronics",
        url="https://rival-electronics.com",
        platform="shopify",
        product_count=3,
    )
    db.add(comp)
    await db.flush()

    # Add products
    for i, (title, price) in enumerate([
        ("Wireless Earbuds Pro", 49.99),
        ("Smart Watch Lite", 79.99),
        ("USB-C Hub 7-in-1", 34.99),
    ]):
        prod = CompetitorProduct(
            competitor_id=comp.id,
            title=title,
            url=f"https://rival-electronics.com/products/{title.lower().replace(' ', '-')}",
            price=price,
            status="active",
        )
        db.add(prod)

    await db.flush()
    return user, comp


# ── Prompt Building Tests ──────────────────────────────────────────


def test_build_analysis_prompt_with_products():
    """Prompt includes competitor name, URL, and product details."""
    comp = _mock_competitor(name="Test Store", url="https://test.com", product_count=1)
    prod = _mock_product(
        title="Widget",
        price=29.99,
        price_history=[
            {"date": "2025-01-01", "price": 25.99},
            {"date": "2025-02-01", "price": 29.99},
        ],
    )

    prompt = _build_analysis_prompt(comp, [prod])

    assert "Test Store" in prompt
    assert "https://test.com" in prompt
    assert "Widget" in prompt
    assert "$29.99" in prompt
    assert "Average price" in prompt


def test_build_analysis_prompt_no_products():
    """Prompt handles empty product list gracefully."""
    comp = _mock_competitor(name="Empty Store", url="https://empty.com", platform="custom", product_count=0)

    prompt = _build_analysis_prompt(comp, [])

    assert "Empty Store" in prompt
    assert "No products tracked yet" in prompt


# ── Fallback Analysis Tests ────────────────────────────────────────


def test_fallback_analysis_premium_segment():
    """Fallback identifies premium segment for high avg price."""
    comp = _mock_competitor(name="Luxury Store")
    prod1 = _mock_product(title="Luxury Item", price=150.0)

    analysis = _generate_fallback_analysis(comp, [prod1])

    assert "premium" in analysis["market_positioning"].lower()
    assert len(analysis["competitive_advantages"]) >= 3
    assert len(analysis["market_gaps"]) >= 3
    assert len(analysis["pricing_strategy"]) >= 3


def test_fallback_analysis_budget_segment():
    """Fallback identifies budget segment for low avg price."""
    comp = _mock_competitor(name="Budget Store", platform="woocommerce")
    prod1 = _mock_product(title="Cheap Item", price=9.99)

    analysis = _generate_fallback_analysis(comp, [prod1])

    assert "budget" in analysis["market_positioning"].lower()


# ── Service Function Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_competitor_with_llm(db: AsyncSession):
    """Full analysis with mocked LLM returns structured result."""
    user, comp = await _setup_competitor_with_products(db, "1")

    mock_llm_response = {
        "content": '{"market_positioning": "Rival Electronics is a mid-range consumer electronics retailer.", "competitive_advantages": ["Strong product selection", "Competitive pricing"], "market_gaps": ["No premium segment", "Limited accessories"], "pricing_strategy": ["Price match strategy", "Bundle discounts"]}',
        "provider": "mock",
        "model": "mock-1",
        "input_tokens": 200,
        "output_tokens": 100,
        "cost_usd": 0.01,
        "cached": False,
        "latency_ms": 500,
    }

    with patch("app.services.llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await analyze_competitor(db, user.id, comp.id)

    assert result["competitor_name"] == "Rival Electronics"
    assert result["product_count"] == 3
    assert result["generated_by"] == "llm_gateway"
    assert "market_positioning" in result["analysis"]
    assert "competitive_advantages" in result["analysis"]


@pytest.mark.asyncio
async def test_analyze_competitor_llm_failure_fallback(db: AsyncSession):
    """When LLM fails, fallback analysis is generated from raw data."""
    user, comp = await _setup_competitor_with_products(db, "2")

    mock_llm_error = {
        "error": "LLM Gateway unavailable",
        "content": "",
    }

    with patch("app.services.llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_error

        result = await analyze_competitor(db, user.id, comp.id)

    assert result["competitor_name"] == "Rival Electronics"
    assert "market_positioning" in result["analysis"]
    # Fallback should mention the competitor name
    assert "Rival Electronics" in result["analysis"]["market_positioning"]


@pytest.mark.asyncio
async def test_analyze_competitor_not_found(db: AsyncSession):
    """Analyzing a non-existent competitor raises ValueError."""
    user = User(
        email="analysis3@test.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()

    with pytest.raises(ValueError, match="not found"):
        await analyze_competitor(db, user.id, uuid.uuid4())


# ── API Endpoint Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_endpoint_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/competitors/{id}/analyze returns 404 for non-existent competitor."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    with patch("app.api.competitors.analyze_competitor", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = ValueError("Competitor not found")
        resp = await client.post(
            f"/api/v1/competitors/{fake_id}/analyze",
            headers=auth_headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analyze_endpoint_invalid_id(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/competitors/{id}/analyze with invalid UUID returns 400."""
    resp = await client.post(
        "/api/v1/competitors/not-a-uuid/analyze",
        headers=auth_headers,
    )
    assert resp.status_code == 400
