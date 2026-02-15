"""
Tests for the Store Connection API endpoints.

Verifies CRUD operations for store connections including creation,
listing, deletion, and connection testing.

For Developers:
    Tests use the standard ``client`` and ``auth_headers`` fixtures.
    API credentials are verified to be masked in responses.

For QA Engineers:
    These tests cover:
    - Creating connections with valid and invalid platforms.
    - Listing connections (empty and with data).
    - Deleting connections.
    - Testing connections (with and without API keys).
    - Authorization: unauthenticated access returns 401.
    - API key masking in responses.

For Project Managers:
    Store connections enable the catalog comparison feature. These tests
    ensure the connection management API is reliable and secure.

For End Users:
    These tests guarantee that your store connections are managed
    correctly and that your API credentials are never exposed.
"""

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────


async def create_connection_via_api(
    client: AsyncClient,
    headers: dict,
    platform: str = "shopify",
    store_url: str = "https://mystore.myshopify.com",
    api_key: str | None = "sk_test_key",
    api_secret: str | None = "sk_test_secret",
) -> dict:
    """
    Create a store connection via the API and return the response JSON.

    Args:
        client: Test HTTP client.
        headers: Authorization headers.
        platform: E-commerce platform.
        store_url: Store URL.
        api_key: API key (optional).
        api_secret: API secret (optional).

    Returns:
        Dict containing the connection response data.
    """
    payload = {
        "platform": platform,
        "store_url": store_url,
    }
    if api_key is not None:
        payload["api_key"] = api_key
    if api_secret is not None:
        payload["api_secret"] = api_secret

    resp = await client.post(
        "/api/v1/connections/",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ── Create Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_connection_success(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/ creates a connection and returns 201."""
    data = await create_connection_via_api(client, auth_headers)

    assert data["platform"] == "shopify"
    assert data["store_url"] == "https://mystore.myshopify.com"
    assert data["has_api_key"] is True
    assert data["has_api_secret"] is True
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_connection_invalid_platform(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/ with invalid platform returns 400."""
    resp = await client.post(
        "/api/v1/connections/",
        json={
            "platform": "etsy",
            "store_url": "https://etsy.com/shop/myshop",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Invalid platform" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_connection_credentials_masked(client: AsyncClient, auth_headers: dict):
    """Connection responses never contain raw API keys."""
    data = await create_connection_via_api(client, auth_headers, api_key="secret123")

    # Response should NOT contain the raw key
    assert "secret123" not in str(data)
    # Should indicate presence via boolean
    assert data["has_api_key"] is True


@pytest.mark.asyncio
async def test_create_connection_unauthenticated(client: AsyncClient):
    """POST /api/v1/connections/ without auth returns 401."""
    resp = await client.post(
        "/api/v1/connections/",
        json={"platform": "shopify", "store_url": "https://x.com"},
    )
    assert resp.status_code == 401


# ── List Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections/ returns empty list for new user."""
    resp = await client.get("/api/v1/connections/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_connections_with_data(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections/ returns connections after creation."""
    await create_connection_via_api(client, auth_headers, platform="shopify")
    await create_connection_via_api(
        client, auth_headers,
        platform="woocommerce",
        store_url="https://woo.example.com",
    )

    resp = await client.get("/api/v1/connections/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


# ── Delete Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_connection_success(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} removes the connection."""
    created = await create_connection_via_api(client, auth_headers)
    conn_id = created["id"]

    resp = await client.delete(
        f"/api/v1/connections/{conn_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it is gone
    list_resp = await client.get("/api/v1/connections/", headers=auth_headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_connection_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} with non-existent ID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(
        f"/api/v1/connections/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Test Connection Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_test_with_key(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test succeeds when API key is set."""
    created = await create_connection_via_api(client, auth_headers)
    conn_id = created["id"]

    resp = await client.post(
        f"/api/v1/connections/{conn_id}/test", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Successfully connected" in data["message"]


@pytest.mark.asyncio
async def test_connection_test_without_key(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test fails when no API key is set."""
    created = await create_connection_via_api(
        client, auth_headers, api_key=None, api_secret=None
    )
    conn_id = created["id"]

    resp = await client.post(
        f"/api/v1/connections/{conn_id}/test", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "No API key" in data["message"]
