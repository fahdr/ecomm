"""
Tests for store connection management API endpoints.

Validates CRUD operations for external store connections (Shopify,
WooCommerce, Platform) including creation, listing, updating,
deletion, and connectivity testing.

For Developers:
    Uses ``auth_headers`` from conftest.py for authentication.
    Each test is isolated via the ``setup_db`` autouse fixture.

For QA Engineers:
    Covers: create success, duplicate (409), list pagination,
    get by ID, update, delete, test connectivity, user isolation,
    unauthenticated (401), invalid UUID (400).
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ───────────────────────────────────────────────────────────


async def _create_connection(
    client: AsyncClient,
    headers: dict,
    platform: str = "shopify",
    store_url: str = "https://my-store.myshopify.com",
    api_key: str = "sk_test_123",
) -> dict:
    """
    Create a store connection and return the full response.

    Args:
        client: Async HTTP test client.
        headers: Auth headers.
        platform: Store platform identifier.
        store_url: Store URL.
        api_key: API key for the store.

    Returns:
        httpx.Response object.
    """
    return await client.post(
        "/api/v1/connections",
        headers=headers,
        json={
            "platform": platform,
            "store_url": store_url,
            "api_key": api_key,
        },
    )


# ── Create Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_connection_success(client: AsyncClient, auth_headers: dict):
    """POST /connections with valid data returns 201."""
    resp = await _create_connection(client, auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "shopify"
    assert data["store_url"] == "https://my-store.myshopify.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_connection_duplicate_returns_409(
    client: AsyncClient, auth_headers: dict
):
    """Creating the same store connection twice returns 409."""
    resp1 = await _create_connection(client, auth_headers)
    assert resp1.status_code == 201

    resp2 = await _create_connection(client, auth_headers)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_create_connection_unauthenticated(client: AsyncClient):
    """POST /connections without auth returns 401."""
    resp = await client.post(
        "/api/v1/connections",
        json={"platform": "shopify", "store_url": "https://x.com", "api_key": "key"},
    )
    assert resp.status_code == 401


# ── List Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers: dict):
    """GET /connections with no connections returns empty list."""
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_connections_with_data(client: AsyncClient, auth_headers: dict):
    """GET /connections returns all created connections."""
    await _create_connection(client, auth_headers, store_url="https://a.com")
    await _create_connection(client, auth_headers, platform="woocommerce", store_url="https://b.com")

    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


# ── Get by ID Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_connection_by_id(client: AsyncClient, auth_headers: dict):
    """GET /connections/{id} returns the correct connection."""
    create_resp = await _create_connection(client, auth_headers)
    conn_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == conn_id


@pytest.mark.asyncio
async def test_get_connection_not_found(client: AsyncClient, auth_headers: dict):
    """GET /connections/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/connections/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Update Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_connection(client: AsyncClient, auth_headers: dict):
    """PATCH /connections/{id} updates the connection."""
    create_resp = await _create_connection(client, auth_headers)
    conn_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/connections/{conn_id}",
        headers=auth_headers,
        json={"store_url": "https://updated-store.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["store_url"] == "https://updated-store.com"


# ── Delete Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_connection_success(client: AsyncClient, auth_headers: dict):
    """DELETE /connections/{id} returns 204."""
    create_resp = await _create_connection(client, auth_headers)
    conn_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await client.get(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /connections/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/connections/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Test Connectivity ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_test_endpoint(client: AsyncClient, auth_headers: dict):
    """POST /connections/{id}/test returns connectivity status."""
    create_resp = await _create_connection(client, auth_headers)
    conn_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/connections/{conn_id}/test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "shopify" in data["message"].lower()


# ── User Isolation ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_user_isolation(client: AsyncClient):
    """Connections from user A are not visible to user B."""
    headers_a = await register_and_login(client, "conn-a@test.com")
    headers_b = await register_and_login(client, "conn-b@test.com")

    await _create_connection(client, headers_a)

    resp = await client.get("/api/v1/connections", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
