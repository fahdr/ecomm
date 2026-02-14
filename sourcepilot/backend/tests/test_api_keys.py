"""
API Key endpoint tests.

For QA Engineers:
    Tests cover key creation, listing, revocation, and authentication
    via X-API-Key header.
"""

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient):
    """POST /api-keys creates a key and returns the raw key."""
    headers = await register_and_login(client)
    resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "scopes": ["read", "write"]},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "key" in data
    assert data["name"] == "Test Key"
    assert data["scopes"] == ["read", "write"]
    assert len(data["key"]) > 20


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient):
    """GET /api-keys returns keys without raw key values."""
    headers = await register_and_login(client)
    await client.post(
        "/api/v1/api-keys",
        json={"name": "Key 1"},
        headers=headers,
    )
    await client.post(
        "/api/v1/api-keys",
        json={"name": "Key 2"},
        headers=headers,
    )

    resp = await client.get("/api/v1/api-keys", headers=headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) == 2
    # Raw key should not be present
    for key in keys:
        assert "key" not in key
        assert "key_prefix" in key


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient):
    """DELETE /api-keys/{id} revokes the key."""
    headers = await register_and_login(client)
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "To Revoke"},
        headers=headers,
    )
    key_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert resp.status_code == 204

    # Verify key is now inactive
    list_resp = await client.get("/api/v1/api-keys", headers=headers)
    keys = list_resp.json()
    revoked = next(k for k in keys if k["id"] == key_id)
    assert revoked["is_active"] is False


@pytest.mark.asyncio
async def test_auth_via_api_key(client: AsyncClient):
    """X-API-Key header authenticates and returns user profile."""
    headers = await register_and_login(client)
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Auth Test", "scopes": ["read"]},
        headers=headers,
    )
    raw_key = create_resp.json()["key"]

    # Use API key to access usage endpoint
    resp = await client.get(
        "/api/v1/usage",
        headers={"X-API-Key": raw_key},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_via_invalid_api_key(client: AsyncClient):
    """X-API-Key with invalid key returns 401."""
    resp = await client.get(
        "/api/v1/usage",
        headers={"X-API-Key": "invalid_key_12345"},
    )
    assert resp.status_code == 401
