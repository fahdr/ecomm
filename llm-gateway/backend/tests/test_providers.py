"""
Tests for the LLM Gateway provider management endpoints.

For Developers:
    Tests CRUD operations for provider configurations.
    Requires the X-Service-Key header for authentication.

For QA Engineers:
    Covers create, list, get, update, delete, and duplicate detection.
"""

import pytest


@pytest.mark.asyncio
async def test_create_provider(client, auth_headers):
    """Create a new provider configuration."""
    resp = await client.post(
        "/api/v1/providers",
        json={
            "name": "claude",
            "display_name": "Anthropic Claude",
            "api_key": "sk-ant-test-key",
            "models": ["claude-sonnet-4-5-20250929", "claude-3-5-haiku-20241022"],
            "rate_limit_rpm": 100,
            "priority": 1,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "claude"
    assert data["display_name"] == "Anthropic Claude"
    assert data["is_enabled"] is True
    assert len(data["models"]) == 2
    assert data["priority"] == 1


@pytest.mark.asyncio
async def test_create_duplicate_provider(client, auth_headers):
    """Creating a provider with an existing name returns 409."""
    body = {
        "name": "openai",
        "display_name": "OpenAI",
        "api_key": "sk-test-key",
    }
    resp = await client.post("/api/v1/providers", json=body, headers=auth_headers)
    assert resp.status_code == 201

    resp = await client.post("/api/v1/providers", json=body, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_providers(client, auth_headers):
    """List all providers returns ordered by priority."""
    await client.post(
        "/api/v1/providers",
        json={"name": "openai", "display_name": "OpenAI", "api_key": "key1", "priority": 2},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/providers",
        json={"name": "claude", "display_name": "Claude", "api_key": "key2", "priority": 1},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/providers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "claude"
    assert data[1]["name"] == "openai"


@pytest.mark.asyncio
async def test_get_provider(client, auth_headers):
    """Get a single provider by ID."""
    resp = await client.post(
        "/api/v1/providers",
        json={"name": "gemini", "display_name": "Google Gemini", "api_key": "gkey"},
        headers=auth_headers,
    )
    provider_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "gemini"


@pytest.mark.asyncio
async def test_update_provider(client, auth_headers):
    """Update a provider's settings."""
    resp = await client.post(
        "/api/v1/providers",
        json={"name": "mistral", "display_name": "Mistral", "api_key": "mkey"},
        headers=auth_headers,
    )
    provider_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/providers/{provider_id}",
        json={"display_name": "Mistral AI", "is_enabled": False, "priority": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Mistral AI"
    assert data["is_enabled"] is False
    assert data["priority"] == 5


@pytest.mark.asyncio
async def test_delete_provider(client, auth_headers):
    """Delete a provider removes it from the list."""
    resp = await client.post(
        "/api/v1/providers",
        json={"name": "custom", "display_name": "Custom", "api_key": "ckey"},
        headers=auth_headers,
    )
    provider_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Requests without service key return 422 (missing required header)."""
    resp = await client.get("/api/v1/providers")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_service_key(client):
    """Requests with wrong service key return 401."""
    resp = await client.get(
        "/api/v1/providers",
        headers={"X-Service-Key": "wrong-key"},
    )
    assert resp.status_code == 401
