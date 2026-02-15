"""
Tests for SourcePilot AI suggestions service and API endpoints.

Covers AI-powered supplier scoring and sourcing improvement suggestions.

For Developers:
    Tests mock ``ecomm_core.llm_client.call_llm`` to avoid real HTTP calls.

For QA Engineers:
    These tests verify:
    - GET /api/v1/ai/suggestions returns sourcing suggestions (authenticated).
    - POST /api/v1/ai/score-supplier returns supplier scores (authenticated).
    - Unauthenticated requests return 401.
    - Malformed LLM responses are handled gracefully.

For Project Managers:
    These tests ensure the AI supplier scoring features in SourcePilot work correctly.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


def _mock_llm_response(content_dict: dict) -> dict:
    """Create a mock LLM gateway response.

    Args:
        content_dict: The parsed content to return as JSON string.

    Returns:
        Dict mimicking the LLM gateway response format.
    """
    return {
        "content": json.dumps(content_dict),
        "provider": "mock",
        "model": "mock-v1",
        "input_tokens": 50,
        "output_tokens": 100,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 10,
    }


@pytest.mark.asyncio
async def test_ai_suggestions_unauthenticated(client: AsyncClient):
    """GET /api/v1/ai/suggestions returns 401 without auth."""
    resp = await client.get("/api/v1/ai/suggestions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_score_supplier_unauthenticated(client: AsyncClient):
    """POST /api/v1/ai/score-supplier returns 401 without auth."""
    resp = await client.post("/api/v1/ai/score-supplier", json={"supplier_url": "https://example.com"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggestions_success(client: AsyncClient):
    """GET /api/v1/ai/suggestions returns sourcing improvement suggestions."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "suggestions": [
            {"title": "Diversify suppliers", "description": "Don't rely on a single supplier", "priority": "high"},
        ]
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.get("/api/v1/ai/suggestions", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) == 1
    assert data["provider"] == "mock"


@pytest.mark.asyncio
async def test_score_supplier_success(client: AsyncClient):
    """POST /api/v1/ai/score-supplier returns reliability scoring."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "scoring": {"product_quality": 85, "shipping_speed": 70, "communication": 90},
        "overall_score": 82,
        "recommendation": "Reliable supplier with good communication",
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            "/api/v1/ai/score-supplier",
            json={"supplier_url": "https://supplier.example.com"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "scoring" in data
    assert "overall_score" in data
    assert data["supplier_url"] == "https://supplier.example.com"
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_ai_suggestions_malformed_json(client: AsyncClient):
    """GET /api/v1/ai/suggestions handles malformed LLM JSON gracefully."""
    headers = await register_and_login(client)
    mock_response = {"content": "Not valid JSON", "provider": "mock", "cost_usd": 0.0}

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.get("/api/v1/ai/suggestions", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
