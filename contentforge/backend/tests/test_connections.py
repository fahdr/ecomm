"""
Store connections API endpoint tests.

Tests the full CRUD lifecycle for store connections including creation,
listing, deletion, connectivity testing, and access control.

For Developers:
    Tests use the ``register_and_login`` helper from conftest.py. Each test
    is independent (database is truncated between tests). The ``StoreConnection``
    model is automatically included in the test schema via models/__init__.py.

For QA Engineers:
    Run with: ``pytest tests/test_connections.py -v``
    Tests cover:
    - Create connection with valid platform (201)
    - Create connection with invalid platform (400)
    - List connections (only returns current user's)
    - Test connection connectivity (mock success)
    - Delete connection (204)
    - Delete nonexistent connection (404)
    - User isolation (user A cannot see/delete user B's connections)
    - Unauthenticated access (401)
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_shopify_connection(client: AsyncClient):
    """POST /connections creates a Shopify store connection."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "mystore.myshopify.com",
            "api_key": "shpat_test_key_123456",
            "api_secret": "shpss_test_secret_789",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "shopify"
    assert data["store_url"] == "mystore.myshopify.com"
    assert data["is_active"] is True
    assert data["last_synced_at"] is None
    assert "id" in data
    assert "user_id" in data
    # Credentials should NOT be in the response
    assert "api_key_encrypted" not in data
    assert "api_secret_encrypted" not in data
    assert "api_key" not in data


@pytest.mark.asyncio
async def test_create_woocommerce_connection(client: AsyncClient):
    """POST /connections creates a WooCommerce store connection."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "woocommerce",
            "store_url": "https://mystore.com",
            "api_key": "ck_test_consumer_key",
            "api_secret": "cs_test_consumer_secret",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["platform"] == "woocommerce"


@pytest.mark.asyncio
async def test_create_platform_connection(client: AsyncClient):
    """POST /connections creates a platform store connection."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "platform",
            "store_url": "https://myplatform.ecomm.io",
            "api_key": "platform_api_key_123",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["platform"] == "platform"


@pytest.mark.asyncio
async def test_create_connection_invalid_platform(client: AsyncClient):
    """POST /connections rejects unsupported platform."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "etsy",
            "store_url": "mystore.etsy.com",
            "api_key": "test_key",
        },
    )
    assert resp.status_code == 400
    assert "platform" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_connections(client: AsyncClient):
    """GET /connections returns the current user's connections."""
    headers = await register_and_login(client)

    # Create two connections
    await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "store1.myshopify.com",
            "api_key": "key1",
        },
    )
    await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "woocommerce",
            "store_url": "https://store2.com",
            "api_key": "key2",
            "api_secret": "secret2",
        },
    )

    resp = await client.get("/api/v1/connections/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    platforms = {c["platform"] for c in data}
    assert platforms == {"shopify", "woocommerce"}


@pytest.mark.asyncio
async def test_delete_connection(client: AsyncClient):
    """DELETE /connections/{id} removes the connection."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "deletable.myshopify.com",
            "api_key": "del_key",
        },
    )
    conn_id = create_resp.json()["id"]

    # Delete
    resp = await client.delete(f"/api/v1/connections/{conn_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get("/api/v1/connections/", headers=headers)
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_connection_not_found(client: AsyncClient):
    """DELETE /connections/{id} returns 404 for nonexistent connection."""
    headers = await register_and_login(client)
    resp = await client.delete(
        "/api/v1/connections/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_test_connection(client: AsyncClient):
    """POST /connections/{id}/test returns connectivity result."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "testable.myshopify.com",
            "api_key": "test_key",
        },
    )
    conn_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/connections/{conn_id}/test", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["connection_id"] == conn_id
    assert "store_name" in data
    assert data["product_count"] is not None
    assert "testable.myshopify.com" in data["message"]


@pytest.mark.asyncio
async def test_test_connection_not_found(client: AsyncClient):
    """POST /connections/{id}/test returns 404 for nonexistent connection."""
    headers = await register_and_login(client)
    resp = await client.post(
        "/api/v1/connections/00000000-0000-0000-0000-000000000000/test",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_connection_isolation_between_users(client: AsyncClient):
    """Users cannot see or delete each other's store connections."""
    headers_a = await register_and_login(client, "conn-user-a@example.com")
    headers_b = await register_and_login(client, "conn-user-b@example.com")

    # User A creates a connection
    create_resp = await client.post(
        "/api/v1/connections/",
        headers=headers_a,
        json={
            "platform": "shopify",
            "store_url": "private-store.myshopify.com",
            "api_key": "private_key",
        },
    )
    conn_id = create_resp.json()["id"]

    # User B cannot see it in their list
    resp = await client.get("/api/v1/connections/", headers=headers_b)
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    # User B cannot delete it
    resp = await client.delete(f"/api/v1/connections/{conn_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B cannot test it
    resp = await client.post(f"/api/v1/connections/{conn_id}/test", headers=headers_b)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_access_connections(client: AsyncClient):
    """Connection endpoints require authentication."""
    resp = await client.get("/api/v1/connections/")
    assert resp.status_code == 401

    resp = await client.post(
        "/api/v1/connections/",
        json={
            "platform": "shopify",
            "store_url": "test.myshopify.com",
            "api_key": "key",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_test_connection_updates_last_synced(client: AsyncClient):
    """Testing a connection updates the last_synced_at timestamp."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "sync-test.myshopify.com",
            "api_key": "sync_key",
        },
    )
    conn_id = create_resp.json()["id"]
    assert create_resp.json()["last_synced_at"] is None

    # Test the connection
    await client.post(f"/api/v1/connections/{conn_id}/test", headers=headers)

    # List to check updated last_synced_at
    resp = await client.get("/api/v1/connections/", headers=headers)
    connections = resp.json()
    assert len(connections) == 1
    assert connections[0]["last_synced_at"] is not None
