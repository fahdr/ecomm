"""
Tests for the Store Connections API endpoints.

Covers CRUD operations for store connections: creating, listing,
deleting, and testing connectivity to external e-commerce stores.

For Developers:
    Tests use the ``client`` and ``auth_headers`` fixtures from conftest.py.
    Store connections are the bridge between TrendScout and external stores
    (Shopify, WooCommerce, platform).

For QA Engineers:
    These tests verify:
    - Create connection (POST /api/v1/connections).
    - List connections (GET /api/v1/connections).
    - Delete connection (DELETE /api/v1/connections/{id}).
    - Test connectivity (POST /api/v1/connections/{id}/test).
    - Credentials are redacted in responses (has_api_key/has_api_secret flags).
    - Invalid platforms are rejected (400).
    - Unauthenticated access returns 401.
    - Cross-user access returns 404.

For Project Managers:
    Store connections enable the product import workflow.  Users connect
    their store, then push winning products from research results directly
    into their catalog.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ─── Helper Functions ────────────────────────────────────────────────


async def create_connection(
    client: AsyncClient,
    headers: dict,
    platform: str = "shopify",
    store_url: str = "https://my-shop.myshopify.com",
    api_key: str = "shpat_test_key_123",
    api_secret: str | None = "shpss_test_secret_456",
) -> dict:
    """
    Helper to create a store connection via the API.

    Args:
        client: The test HTTP client.
        headers: Authorization headers for the authenticated user.
        platform: Store platform identifier.
        store_url: Base URL of the store.
        api_key: API key for the store.
        api_secret: API secret for the store (optional).

    Returns:
        The created store connection response dict.
    """
    payload = {
        "platform": platform,
        "store_url": store_url,
        "api_key": api_key,
        "api_secret": api_secret,
    }
    resp = await client.post("/api/v1/connections", json=payload, headers=headers)
    assert resp.status_code == 201, f"Failed to create connection: {resp.text}"
    return resp.json()


# ─── Create Connection Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_shopify_connection(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections creates a Shopify connection with credentials redacted."""
    conn = await create_connection(client, auth_headers, platform="shopify")

    assert conn["platform"] == "shopify"
    assert conn["store_url"] == "https://my-shop.myshopify.com"
    assert conn["has_api_key"] is True
    assert conn["has_api_secret"] is True
    assert conn["is_active"] is True
    assert "id" in conn
    assert "user_id" in conn
    assert "created_at" in conn
    assert "updated_at" in conn
    # Credentials must NOT be in the response
    assert "api_key" not in conn
    assert "api_key_encrypted" not in conn
    assert "api_secret" not in conn
    assert "api_secret_encrypted" not in conn


@pytest.mark.asyncio
async def test_create_woocommerce_connection(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections creates a WooCommerce connection."""
    conn = await create_connection(
        client, auth_headers,
        platform="woocommerce",
        store_url="https://my-woo-store.com",
        api_key="ck_test_123",
        api_secret="cs_test_456",
    )
    assert conn["platform"] == "woocommerce"
    assert conn["store_url"] == "https://my-woo-store.com"


@pytest.mark.asyncio
async def test_create_platform_connection(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections creates a platform connection."""
    conn = await create_connection(
        client, auth_headers,
        platform="platform",
        store_url="https://my-store.dropship.com",
        api_key="platform_key_123",
        api_secret=None,
    )
    assert conn["platform"] == "platform"
    assert conn["has_api_secret"] is False


@pytest.mark.asyncio
async def test_create_connection_invalid_platform(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections rejects invalid platform with 400."""
    resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "amazon",
            "store_url": "https://amazon.com",
            "api_key": "test",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Invalid platform" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_connection_unauthenticated(client: AsyncClient):
    """POST /api/v1/connections returns 401 without auth headers."""
    resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://shop.example.com",
            "api_key": "test",
        },
    )
    assert resp.status_code == 401


# ─── List Connections Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections returns empty list when no connections exist."""
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_connections_returns_created(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections returns previously created connections."""
    await create_connection(client, auth_headers, platform="shopify")
    await create_connection(
        client, auth_headers,
        platform="woocommerce",
        store_url="https://woo.example.com",
        api_key="woo_key",
    )

    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2

    # Ordered by platform name
    platforms = [item["platform"] for item in data["items"]]
    assert platforms == sorted(platforms)


@pytest.mark.asyncio
async def test_list_connections_user_isolation(client: AsyncClient):
    """GET /api/v1/connections only shows connections owned by the requesting user."""
    headers_a = await register_and_login(client, "conn-user-a@example.com")
    await create_connection(client, headers_a, platform="shopify")

    headers_b = await register_and_login(client, "conn-user-b@example.com")
    resp = await client.get("/api/v1/connections", headers=headers_b)
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_connections_unauthenticated(client: AsyncClient):
    """GET /api/v1/connections returns 401 without auth headers."""
    resp = await client.get("/api/v1/connections")
    assert resp.status_code == 401


# ─── Delete Connection Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_connection(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} removes the connection and returns 204."""
    conn = await create_connection(client, auth_headers)

    resp = await client.delete(
        f"/api/v1/connections/{conn['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_delete_connection_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} returns 404 for non-existent connection."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/connections/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_wrong_user(client: AsyncClient):
    """DELETE /api/v1/connections/{id} returns 404 when user does not own the connection."""
    headers_a = await register_and_login(client, "conn-owner@example.com")
    conn = await create_connection(client, headers_a)

    headers_b = await register_and_login(client, "conn-intruder@example.com")
    resp = await client.delete(
        f"/api/v1/connections/{conn['id']}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_unauthenticated(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/connections/{id} returns 401 without auth headers."""
    conn = await create_connection(client, auth_headers)
    resp = await client.delete(f"/api/v1/connections/{conn['id']}")
    assert resp.status_code == 401


# ─── Test Connectivity Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_test_success(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test returns success for active connection."""
    conn = await create_connection(client, auth_headers, platform="shopify")

    resp = await client.post(
        f"/api/v1/connections/{conn['id']}/test", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "shopify" in data["message"].lower() or "Shopify" in data["message"]


@pytest.mark.asyncio
async def test_connection_test_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test returns 404 for non-existent connection."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/connections/{fake_id}/test", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_connection_test_unauthenticated(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/connections/{id}/test returns 401 without auth headers."""
    conn = await create_connection(client, auth_headers)
    resp = await client.post(f"/api/v1/connections/{conn['id']}/test")
    assert resp.status_code == 401
