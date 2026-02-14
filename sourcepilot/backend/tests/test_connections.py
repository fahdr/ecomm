"""
Store connection endpoint tests for SourcePilot.

Tests cover creating, listing, updating, deleting, and setting default
store connections (e.g., Shopify, WooCommerce stores).

For QA Engineers:
    Verifies CRUD operations on store connections, duplicate store
    detection, default connection management, authorization isolation,
    and validation of required fields.
"""

import uuid

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_connection(
    client: AsyncClient,
    headers: dict,
    *,
    store_name: str = "My Shop",
    platform: str = "shopify",
    store_url: str = "https://myshop.myshopify.com",
    api_key: str = "test-key-123",
) -> dict:
    """Create a store connection via the API and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Auth headers for the request.
        store_name: Display name for the store.
        platform: E-commerce platform type.
        store_url: URL of the store.
        api_key: Store API key.

    Returns:
        The created connection as a dict.
    """
    resp = await client.post(
        "/api/v1/connections",
        json={
            "store_name": store_name,
            "platform": platform,
            "store_url": store_url,
            "api_key": api_key,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"Failed to create connection: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Create connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_connection(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections creates a store connection."""
    data = await _create_connection(client, auth_headers)
    assert "id" in data
    assert data["store_name"] == "My Shop"
    assert data["platform"] == "shopify"


@pytest.mark.asyncio
async def test_create_connection_woocommerce(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections works for WooCommerce stores."""
    data = await _create_connection(
        client,
        auth_headers,
        store_name="WooShop",
        platform="woocommerce",
        store_url="https://wooshop.com",
    )
    assert data["platform"] == "woocommerce"


@pytest.mark.asyncio
async def test_create_connection_duplicate_store(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections with same store URL returns 409 or 400."""
    await _create_connection(client, auth_headers)
    resp = await client.post(
        "/api/v1/connections",
        json={
            "store_name": "Same Shop",
            "platform": "shopify",
            "store_url": "https://myshop.myshopify.com",
            "api_key": "another-key",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (400, 409)


@pytest.mark.asyncio
async def test_create_connection_missing_fields(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections with missing required fields returns 422."""
    resp = await client.post(
        "/api/v1/connections",
        json={"store_name": "Incomplete"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_connection_unauthenticated(client: AsyncClient):
    """POST /api/v1/connections without auth returns 401."""
    resp = await client.post(
        "/api/v1/connections",
        json={
            "store_name": "Ghost Shop",
            "platform": "shopify",
            "store_url": "https://ghost.myshopify.com",
            "api_key": "key",
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List connections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections with no connections returns empty list."""
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_connections(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections returns all user's connections."""
    await _create_connection(
        client, auth_headers, store_name="Shop A", store_url="https://a.myshopify.com"
    )
    await _create_connection(
        client,
        auth_headers,
        store_name="Shop B",
        platform="woocommerce",
        store_url="https://b.example.com",
    )
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_connections_isolation(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections does not return other users' connections."""
    await _create_connection(client, auth_headers, store_name="User1 Shop")

    other_headers = await register_and_login(client)
    resp = await client.get("/api/v1/connections", headers=other_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_connections_unauthenticated(client: AsyncClient):
    """GET /api/v1/connections without auth returns 401."""
    resp = await client.get("/api/v1/connections")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_connection(client: AsyncClient, auth_headers: dict):
    """PUT /api/v1/connections/{id} updates connection details."""
    created = await _create_connection(client, auth_headers)
    conn_id = created["id"]
    resp = await client.put(
        f"/api/v1/connections/{conn_id}",
        json={"store_name": "Renamed Shop", "api_key": "new-key-456"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["store_name"] == "Renamed Shop"


@pytest.mark.asyncio
async def test_update_connection_not_found(client: AsyncClient, auth_headers: dict):
    """PUT /api/v1/connections/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.put(
        f"/api/v1/connections/{fake_id}",
        json={"store_name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_connection_other_user(client: AsyncClient, auth_headers: dict):
    """PUT /api/v1/connections/{id} by different user returns 403 or 404."""
    created = await _create_connection(client, auth_headers)
    conn_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.put(
        f"/api/v1/connections/{conn_id}",
        json={"store_name": "Stolen"},
        headers=other_headers,
    )
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Delete connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_connection(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} removes the connection."""
    created = await _create_connection(client, auth_headers)
    conn_id = created["id"]
    resp = await client.delete(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert resp.status_code in (200, 204)

    # Verify connection is gone
    list_resp = await client.get("/api/v1/connections", headers=auth_headers)
    body = list_resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    ids = [item["id"] for item in items]
    assert conn_id not in ids


@pytest.mark.asyncio
async def test_delete_connection_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/connections/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_other_user(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} by different user returns 403 or 404."""
    created = await _create_connection(client, auth_headers)
    conn_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.delete(f"/api/v1/connections/{conn_id}", headers=other_headers)
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Set default connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_default_connection(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/default marks a connection as the default."""
    conn_a = await _create_connection(
        client, auth_headers, store_name="Shop A", store_url="https://a.myshopify.com"
    )
    conn_b = await _create_connection(
        client,
        auth_headers,
        store_name="Shop B",
        store_url="https://b.myshopify.com",
    )

    resp = await client.post(
        f"/api/v1/connections/{conn_b['id']}/default", headers=auth_headers
    )
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_set_default_connection_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/default with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/connections/{fake_id}/default", headers=auth_headers
    )
    assert resp.status_code == 404
