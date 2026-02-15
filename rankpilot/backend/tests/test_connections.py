"""
Tests for store connection API endpoints.

Covers CRUD for store connections and the connection test endpoint.

For Developers:
    Store connections require JWT auth. Each test creates connections
    using the ``auth_headers`` fixture from conftest.py.

For QA Engineers:
    These tests verify:
    - Create connection returns 201 with all required fields.
    - List connections returns paginated results scoped to the user.
    - Get connection by ID returns 200 or 404.
    - Update connection modifies only provided fields.
    - Delete connection returns 204.
    - Test connection endpoint returns success message.
    - Cross-user connection access is blocked (404).

For Project Managers:
    Store connections enable data import from e-commerce platforms,
    improving the accuracy of SEO audits and content generation.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────


async def create_test_connection(
    client: AsyncClient,
    auth_headers: dict,
    platform: str = "shopify",
    store_url: str = "https://myshop.myshopify.com",
) -> dict:
    """
    Create a store connection via the API and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        platform: E-commerce platform name.
        store_url: Store base URL.

    Returns:
        The created connection as a dict (StoreConnectionResponse).
    """
    resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": platform,
            "store_url": store_url,
            "api_key": "test-key-123",
            "api_secret": "test-secret-456",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Connection creation failed: {resp.text}"
    return resp.json()


# ── Create Connection Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_connection_basic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections creates a connection with correct fields."""
    data = await create_test_connection(client, auth_headers)

    assert data["platform"] == "shopify"
    assert data["store_url"] == "https://myshop.myshopify.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_connection_woocommerce(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections works for woocommerce platform."""
    data = await create_test_connection(
        client, auth_headers,
        platform="woocommerce",
        store_url="https://mystore.com",
    )
    assert data["platform"] == "woocommerce"


@pytest.mark.asyncio
async def test_create_connection_invalid_platform(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections with invalid platform returns 422."""
    resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "invalid_platform",
            "store_url": "https://example.com",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_connection_unauthenticated(client: AsyncClient):
    """POST /api/v1/connections without auth returns 401."""
    resp = await client.post(
        "/api/v1/connections",
        json={"platform": "shopify", "store_url": "https://example.com"},
    )
    assert resp.status_code == 401


# ── List Connections Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections with no connections returns empty list."""
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_connections_returns_created(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections returns connections that were created."""
    await create_test_connection(client, auth_headers, store_url="https://shop1.com")
    await create_test_connection(client, auth_headers, platform="woocommerce", store_url="https://shop2.com")

    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


# ── Get Connection by ID Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_connection_by_id(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections/{id} returns the correct connection."""
    conn = await create_test_connection(client, auth_headers, store_url="https://get-test.com")

    resp = await client.get(f"/api/v1/connections/{conn['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == conn["id"]


@pytest.mark.asyncio
async def test_get_connection_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/connections/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Update Connection Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_connection(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/connections/{id} updates the store_url."""
    conn = await create_test_connection(client, auth_headers, store_url="https://old-store.com")

    resp = await client.patch(
        f"/api/v1/connections/{conn['id']}",
        json={"store_url": "https://new-store.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["store_url"] == "https://new-store.com"


@pytest.mark.asyncio
async def test_update_connection_deactivate(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/connections/{id} with is_active=false deactivates it."""
    conn = await create_test_connection(client, auth_headers, store_url="https://deactivate.com")

    resp = await client.patch(
        f"/api/v1/connections/{conn['id']}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# ── Delete Connection Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_connection(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} removes the connection."""
    conn = await create_test_connection(client, auth_headers, store_url="https://delete-me.com")

    resp = await client.delete(f"/api/v1/connections/{conn['id']}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get(f"/api/v1/connections/{conn['id']}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/connections/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Test Connection Endpoint Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_test_endpoint(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test returns success for valid connection."""
    conn = await create_test_connection(client, auth_headers, store_url="https://test-conn.com")

    resp = await client.post(
        f"/api/v1/connections/{conn['id']}/test",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["success"] is True
    assert "message" in data
    assert data["platform"] == "shopify"


@pytest.mark.asyncio
async def test_connection_test_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/connections/{fake_id}/test", headers=auth_headers)
    assert resp.status_code == 404


# ── Cross-User Access Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_cross_user_blocked(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections/{id} for another user's connection returns 404."""
    from tests.conftest import register_and_login

    conn = await create_test_connection(client, auth_headers, store_url="https://private.com")

    user2_headers = await register_and_login(client, email="conn-spy@example.com")
    resp = await client.get(f"/api/v1/connections/{conn['id']}", headers=user2_headers)
    assert resp.status_code == 404
