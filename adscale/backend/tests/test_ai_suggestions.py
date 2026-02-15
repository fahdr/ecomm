"""
Tests for AdScale AI suggestions service and API endpoints.

Covers AI-powered ad copy optimization and campaign improvement suggestions.

For Developers:
    Tests mock ``ecomm_core.llm_client.call_llm`` to avoid real HTTP calls.

For QA Engineers:
    These tests verify:
    - GET /api/v1/ai/suggestions returns ad improvement suggestions (authenticated).
    - POST /api/v1/ai/optimize-ad returns ad optimizations (authenticated).
    - Unauthenticated requests return 401.
    - Malformed LLM responses are handled gracefully.

For Project Managers:
    These tests ensure the AI ad optimization features in AdScale work correctly.
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
async def test_optimize_ad_unauthenticated(client: AsyncClient):
    """POST /api/v1/ai/optimize-ad returns 401 without auth."""
    resp = await client.post("/api/v1/ai/optimize-ad", json={"ad_id": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggestions_success(client: AsyncClient):
    """GET /api/v1/ai/suggestions returns ad campaign suggestions."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "suggestions": [
            {"title": "Refine targeting", "description": "Narrow audience for better ROAS", "priority": "high"},
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
async def test_optimize_ad_success(client: AsyncClient):
    """POST /api/v1/ai/optimize-ad returns ad optimization suggestions."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "optimizations": [
            {"element": "headline", "current_assessment": "Generic", "improvement": "Add urgency", "expected_lift": "15%"},
        ]
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            "/api/v1/ai/optimize-ad",
            json={"ad_id": "ad-123"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "optimizations" in data
    assert data["ad_id"] == "ad-123"
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
