"""
Tests for TrendScout AI suggestions service and API endpoints.

Covers AI-powered trend predictions and product research suggestions,
including LLM call mocking, JSON parsing, and error handling.

For Developers:
    Tests mock ``ecomm_core.llm_client.call_llm`` to avoid real HTTP calls.
    Both service-level and API-level tests are included.

For QA Engineers:
    These tests verify:
    - GET /api/v1/ai/suggestions returns suggestions (authenticated).
    - POST /api/v1/ai/predict-trends returns predictions (authenticated).
    - Unauthenticated requests return 401.
    - Malformed LLM responses are handled gracefully.

For Project Managers:
    These tests ensure the AI features in TrendScout work correctly
    and degrade gracefully when the LLM gateway returns unexpected output.
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
async def test_predict_trends_unauthenticated(client: AsyncClient):
    """POST /api/v1/ai/predict-trends returns 401 without auth."""
    resp = await client.post("/api/v1/ai/predict-trends")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggestions_success(client: AsyncClient):
    """GET /api/v1/ai/suggestions returns suggestions when authenticated."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "suggestions": [
            {"title": "Explore niche markets", "description": "Focus on under-served niches", "priority": "high"},
            {"title": "Monitor trends", "description": "Use Google Trends daily", "priority": "medium"},
        ]
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.get("/api/v1/ai/suggestions", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) == 2
    assert "generated_at" in data
    assert data["provider"] == "mock"


@pytest.mark.asyncio
async def test_predict_trends_success(client: AsyncClient):
    """POST /api/v1/ai/predict-trends returns predictions when authenticated."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "predictions": [
            {"name": "Eco-friendly products", "confidence": 85, "description": "Growing trend"},
            {"name": "Smart home devices", "confidence": 78, "description": "Steady growth"},
        ]
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/v1/ai/predict-trends", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 2
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_ai_suggestions_malformed_json(client: AsyncClient):
    """GET /api/v1/ai/suggestions handles malformed LLM JSON gracefully."""
    headers = await register_and_login(client)
    mock_response = {
        "content": "This is not valid JSON",
        "provider": "mock",
        "model": "mock-v1",
        "cost_usd": 0.001,
    }

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.get("/api/v1/ai/suggestions", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data


@pytest.mark.asyncio
async def test_predict_trends_malformed_json(client: AsyncClient):
    """POST /api/v1/ai/predict-trends handles malformed LLM JSON gracefully."""
    headers = await register_and_login(client)
    mock_response = {
        "content": "Not JSON at all",
        "provider": "mock",
        "model": "mock-v1",
        "cost_usd": 0.0,
    }

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/v1/ai/predict-trends", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
