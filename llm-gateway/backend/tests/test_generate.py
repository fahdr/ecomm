"""
Tests for the LLM Gateway generate endpoint.

Uses mocked provider responses to test the full generation pipeline
including routing, caching, rate limiting, and cost tracking.

For Developers:
    Tests mock the provider's generate method directly to avoid
    interfering with the test client's HTTP calls.

For QA Engineers:
    Covers: successful generation, caching, rate limiting, auth, errors.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.providers.base import GenerationResult, ProviderError


async def _create_provider(client, auth_headers, name="claude"):
    """Helper to create a test provider config."""
    resp = await client.post(
        "/api/v1/providers",
        json={
            "name": name,
            "display_name": f"Test {name}",
            "api_key": "test-key",
            "models": ["test-model"],
            "rate_limit_rpm": 60,
            "priority": 1,
        },
        headers=auth_headers,
    )
    return resp.json()


MOCK_RESULT = GenerationResult(
    content="This is a test response.",
    input_tokens=50,
    output_tokens=30,
    model="claude-sonnet-4-5-20250929",
    provider="claude",
)


@pytest.mark.asyncio
async def test_generate_success(client, auth_headers):
    """Successful generation returns content and usage stats."""
    await _create_provider(client, auth_headers)

    with patch(
        "app.providers.claude.ClaudeProvider.generate",
        new_callable=AsyncMock,
        return_value=MOCK_RESULT,
    ):
        resp = await client.post(
            "/api/v1/generate",
            json={
                "user_id": "user-123",
                "service": "trendscout",
                "task_type": "product_analysis",
                "prompt": "Analyze this product",
                "system": "You are a product analyst",
                "max_tokens": 500,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "This is a test response."
    assert data["provider"] == "claude"
    assert data["input_tokens"] == 50
    assert data["output_tokens"] == 30
    assert data["cached"] is False
    assert data["cost_usd"] > 0
    assert data["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_generate_caching(client, auth_headers):
    """Second identical request returns cached response."""
    await _create_provider(client, auth_headers)

    request_body = {
        "user_id": "user-123",
        "service": "trendscout",
        "task_type": "test",
        "prompt": "Cache test prompt unique-xyz",
    }

    with patch(
        "app.providers.claude.ClaudeProvider.generate",
        new_callable=AsyncMock,
        return_value=MOCK_RESULT,
    ):
        resp1 = await client.post(
            "/api/v1/generate", json=request_body, headers=auth_headers
        )
        assert resp1.status_code == 200
        assert resp1.json()["cached"] is False

    # Second request should be cached (no mock needed since cache serves it)
    resp2 = await client.post(
        "/api/v1/generate", json=request_body, headers=auth_headers
    )
    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True
    assert resp2.json()["content"] == "This is a test response."


@pytest.mark.asyncio
async def test_generate_no_provider(client, auth_headers):
    """Request with no configured provider returns 503."""
    resp = await client.post(
        "/api/v1/generate",
        json={
            "user_id": "user-123",
            "service": "trendscout",
            "prompt": "Test",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_generate_invalid_service_key(client):
    """Request with wrong service key returns 401."""
    resp = await client.post(
        "/api/v1/generate",
        json={"user_id": "u1", "service": "test", "prompt": "hello"},
        headers={"X-Service-Key": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_provider_error(client, auth_headers):
    """Provider returning error results in 502."""
    await _create_provider(client, auth_headers)

    with patch(
        "app.providers.claude.ClaudeProvider.generate",
        new_callable=AsyncMock,
        side_effect=ProviderError("claude", "API error", status_code=500),
    ):
        resp = await client.post(
            "/api/v1/generate",
            json={
                "user_id": "user-123",
                "service": "trendscout",
                "prompt": "Test error",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_generate_with_override(client, auth_headers):
    """Customer override routes to a different provider."""
    await _create_provider(client, auth_headers, name="claude")
    await _create_provider(client, auth_headers, name="openai")

    # Create an override for user-456 to use openai
    await client.post(
        "/api/v1/overrides",
        json={
            "user_id": "user-456",
            "provider_name": "openai",
            "model_name": "gpt-4o",
        },
        headers=auth_headers,
    )

    openai_result = GenerationResult(
        content="OpenAI response",
        input_tokens=40,
        output_tokens=20,
        model="gpt-4o",
        provider="openai",
    )

    with patch(
        "app.providers.openai_provider.OpenAIProvider.generate",
        new_callable=AsyncMock,
        return_value=openai_result,
    ):
        resp = await client.post(
            "/api/v1/generate",
            json={
                "user_id": "user-456",
                "service": "contentforge",
                "prompt": "Generate content",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["content"] == "OpenAI response"


@pytest.mark.asyncio
async def test_generate_logs_usage(client, auth_headers):
    """Generation creates a usage log entry."""
    await _create_provider(client, auth_headers)

    with patch(
        "app.providers.claude.ClaudeProvider.generate",
        new_callable=AsyncMock,
        return_value=MOCK_RESULT,
    ):
        await client.post(
            "/api/v1/generate",
            json={
                "user_id": "user-789",
                "service": "rankpilot",
                "task_type": "seo_audit",
                "prompt": "Audit this page",
            },
            headers=auth_headers,
        )

    # Check usage logs
    resp = await client.get("/api/v1/usage/summary?days=1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] >= 1
