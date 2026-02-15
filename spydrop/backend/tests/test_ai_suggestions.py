"""
Tests for SpyDrop AI suggestions service and API endpoints.

Covers AI-powered competitor analysis and competitive intelligence suggestions.

For Developers:
    Tests mock ``ecomm_core.llm_client.call_llm`` to avoid real HTTP calls.

For QA Engineers:
    These tests verify:
    - GET /api/v1/ai/suggestions returns competitive suggestions (authenticated).
    - POST /api/v1/ai/competitor-analysis returns analysis (authenticated).
    - Unauthenticated requests return 401.
    - Malformed LLM responses are handled gracefully.

For Project Managers:
    These tests ensure the AI competitor analysis features in SpyDrop work correctly.
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
async def test_competitor_analysis_unauthenticated(client: AsyncClient):
    """POST /api/v1/ai/competitor-analysis returns 401 without auth."""
    resp = await client.post("/api/v1/ai/competitor-analysis", json={"competitor_id": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggestions_success(client: AsyncClient):
    """GET /api/v1/ai/suggestions returns competitive intelligence suggestions."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "suggestions": [
            {"title": "Monitor pricing changes", "description": "Track competitor pricing weekly", "priority": "high"},
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
async def test_competitor_analysis_success(client: AsyncClient):
    """POST /api/v1/ai/competitor-analysis returns detailed analysis."""
    headers = await register_and_login(client)
    mock_response = _mock_llm_response({
        "analysis": [
            {"category": "Pricing", "finding": "Below market average", "opportunity": "Premium positioning", "urgency": "medium"},
        ]
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            "/api/v1/ai/competitor-analysis",
            json={"competitor_id": "competitor-123"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "analysis" in data
    assert data["competitor_id"] == "competitor-123"
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
