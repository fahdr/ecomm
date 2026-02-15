"""
Tests for RankPilot AI suggestions service and API endpoints.

Covers AI-powered SEO recommendations and optimization suggestions.

For Developers:
    Tests mock ``ecomm_core.llm_client.call_llm`` to avoid real HTTP calls.

For QA Engineers:
    These tests verify:
    - GET /api/v1/ai/suggestions returns SEO suggestions (authenticated).
    - POST /api/v1/ai/seo-suggest returns detailed recommendations (authenticated).
    - Unauthenticated requests return 401.
    - Malformed LLM responses are handled gracefully.

For Project Managers:
    These tests ensure the AI SEO features in RankPilot work correctly.
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
async def test_seo_suggest_unauthenticated(client: AsyncClient):
    """POST /api/v1/ai/seo-suggest returns 401 without auth."""
    resp = await client.post("/api/v1/ai/seo-suggest")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggestions_success(client: AsyncClient):
    """GET /api/v1/ai/suggestions returns SEO suggestions when authenticated."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "suggestions": [
            {"title": "Optimize meta tags", "description": "Add unique meta descriptions", "priority": "high"},
            {"title": "Internal linking", "description": "Improve internal link structure", "priority": "medium"},
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
async def test_seo_suggest_success(client: AsyncClient):
    """POST /api/v1/ai/seo-suggest returns recommendations when authenticated."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "recommendations": [
            {"category": "Technical SEO", "action": "Fix page speed", "expected_impact": "high", "difficulty": "medium"},
            {"category": "Content", "action": "Add blog posts", "expected_impact": "medium", "difficulty": "easy"},
        ]
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post("/api/v1/ai/seo-suggest", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) == 2
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
