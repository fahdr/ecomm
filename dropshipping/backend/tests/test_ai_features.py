"""
Tests for Dropshipping platform AI features API endpoints.

Covers AI-powered product description generation and pricing suggestions,
including store ownership validation, LLM call mocking, and error handling.

For Developers:
    Tests mock ``ecomm_core.llm_client.call_llm`` to avoid real HTTP calls.
    Store creation is done via API helpers to test full ownership validation.

For QA Engineers:
    These tests verify:
    - POST /stores/{id}/products/{id}/ai-description generates descriptions.
    - POST /stores/{id}/products/{id}/ai-pricing suggests pricing.
    - Unauthenticated requests return 401.
    - Non-owned stores return 404.
    - Malformed LLM responses are handled gracefully.

For Project Managers:
    These tests ensure the AI product features in the dropshipping platform
    work correctly with proper store ownership enforcement.
"""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest


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


async def _register_and_get_token(client, email: str = "aitest@example.com") -> str:
    """Register a user and return the access token.

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        The JWT access token string.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    return resp.json()["access_token"]


async def _create_store(client, token: str, name: str = "AI Test Store") -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        name: Store name.

    Returns:
        The created store response dict.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _create_product(client, token: str, store_id: str) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: UUID of the store.

    Returns:
        The created product response dict.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json={"title": "AI Test Product", "price": 29.99},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


@pytest.mark.asyncio
async def test_ai_description_unauthenticated(client):
    """POST ai-description returns 401 without auth."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/stores/{fake_id}/products/{fake_id}/ai-description")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_pricing_unauthenticated(client):
    """POST ai-pricing returns 401 without auth."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/stores/{fake_id}/products/{fake_id}/ai-pricing")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_description_store_not_found(client):
    """POST ai-description returns 404 for non-existent store."""
    token = await _register_and_get_token(client, "notfound@example.com")
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/stores/{fake_id}/products/{fake_id}/ai-description",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ai_description_success(client):
    """POST ai-description generates a product description."""
    token = await _register_and_get_token(client, "aidesc@example.com")
    store = await _create_store(client, token)
    product = await _create_product(client, token, store["id"])

    mock_response = _mock_llm_response({
        "description": {
            "title_variants": ["Premium Widget", "Widget Pro", "Ultra Widget"],
            "short_description": "A premium widget for all your needs.",
            "bullet_points": ["Durable", "Lightweight", "Affordable"],
        }
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            f"/api/v1/stores/{store['id']}/products/{product['id']}/ai-description",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "description" in data
    assert data["product_id"] == product["id"]
    assert data["store_id"] == store["id"]
    assert "generated_at" in data
    assert data["provider"] == "mock"


@pytest.mark.asyncio
async def test_ai_pricing_success(client):
    """POST ai-pricing generates pricing suggestions."""
    token = await _register_and_get_token(client, "aiprice@example.com")
    store = await _create_store(client, token, "Pricing Store")
    product = await _create_product(client, token, store["id"])

    mock_response = _mock_llm_response({
        "pricing": {
            "recommended_price_range": {"min": 24.99, "max": 39.99},
            "pricing_strategy": "competitive",
            "psychological_tips": ["Use .99 endings"],
        }
    })

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            f"/api/v1/stores/{store['id']}/products/{product['id']}/ai-pricing",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "pricing" in data
    assert data["product_id"] == product["id"]
    assert data["store_id"] == store["id"]
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_ai_description_malformed_json(client):
    """POST ai-description handles malformed LLM JSON gracefully."""
    token = await _register_and_get_token(client, "malformed@example.com")
    store = await _create_store(client, token, "Malformed Store")
    product = await _create_product(client, token, store["id"])

    mock_response = {"content": "Not valid JSON", "provider": "mock", "cost_usd": 0.0}

    with patch("app.services.ai_suggestions_service.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            f"/api/v1/stores/{store['id']}/products/{product['id']}/ai-description",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "description" in data
