"""
Tests for the LLM Gateway customer override endpoints.

For Developers:
    Tests CRUD for per-customer provider/model overrides.

For QA Engineers:
    Verify override creation, filtering by user_id, and deletion.
"""

import pytest


@pytest.mark.asyncio
async def test_create_override(client, auth_headers):
    """Create a customer override."""
    resp = await client.post(
        "/api/v1/overrides",
        json={
            "user_id": "user-123",
            "service_name": "trendscout",
            "provider_name": "claude",
            "model_name": "claude-opus-4-6",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == "user-123"
    assert data["service_name"] == "trendscout"
    assert data["provider_name"] == "claude"


@pytest.mark.asyncio
async def test_create_global_override(client, auth_headers):
    """Create a customer override without service_name (applies to all)."""
    resp = await client.post(
        "/api/v1/overrides",
        json={
            "user_id": "user-456",
            "provider_name": "openai",
            "model_name": "gpt-4o",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_name"] is None


@pytest.mark.asyncio
async def test_list_overrides(client, auth_headers):
    """List all overrides."""
    await client.post(
        "/api/v1/overrides",
        json={"user_id": "u1", "provider_name": "claude", "model_name": "m1"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/overrides",
        json={"user_id": "u2", "provider_name": "openai", "model_name": "m2"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/overrides", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_overrides_by_user(client, auth_headers):
    """Filter overrides by user_id."""
    await client.post(
        "/api/v1/overrides",
        json={"user_id": "u1", "provider_name": "claude", "model_name": "m1"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/overrides",
        json={"user_id": "u2", "provider_name": "openai", "model_name": "m2"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/overrides?user_id=u1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "u1"


@pytest.mark.asyncio
async def test_delete_override(client, auth_headers):
    """Delete an override."""
    resp = await client.post(
        "/api/v1/overrides",
        json={"user_id": "u1", "provider_name": "claude", "model_name": "m1"},
        headers=auth_headers,
    )
    override_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/overrides/{override_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/overrides", headers=auth_headers)
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_override(client, auth_headers):
    """Deleting a non-existent override returns 404."""
    resp = await client.delete(
        "/api/v1/overrides/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404
