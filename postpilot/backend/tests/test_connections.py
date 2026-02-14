"""
Tests for the store connection management API endpoints.

Covers CRUD operations for store connections: creating, listing,
retrieving, updating, and deleting connections.

For Developers:
    Tests use the client and auth_headers fixtures from conftest.py.
    Store connections store encrypted credentials that should never
    appear in API responses.

For QA Engineers:
    These tests verify:
    - POST /api/v1/connections creates a connection (201).
    - GET /api/v1/connections lists all connections (200).
    - GET /api/v1/connections/{id} retrieves a single connection (200).
    - PATCH /api/v1/connections/{id} updates a connection (200).
    - DELETE /api/v1/connections/{id} removes a connection (204).
    - API keys are not returned in responses.
    - Unauthenticated requests return 401.
    - User isolation is enforced.

For Project Managers:
    Store connections enable product imports from external e-commerce
    platforms, feeding into the automated content generation pipeline.

For End Users:
    These tests validate that connecting and managing your online store
    works reliably for product imports.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


@pytest.fixture
def shopify_payload() -> dict:
    """
    Build a valid Shopify store connection payload.

    Returns:
        Dict with platform, store_url, api_key, and api_secret fields.
    """
    return {
        "platform": "shopify",
        "store_url": "https://test-store.myshopify.com",
        "api_key": "shpat_test_key_1234567890",
        "api_secret": "shpss_test_secret_abcdef",
    }


# ── Create Connection Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_connection(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """POST /api/v1/connections creates a store connection (201)."""
    resp = await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["platform"] == "shopify"
    assert data["store_url"] == "https://test-store.myshopify.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_connection_no_credentials_in_response(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """POST /api/v1/connections does not return API keys in the response."""
    resp = await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )
    data = resp.json()

    assert "api_key_encrypted" not in data
    assert "api_secret_encrypted" not in data
    assert "api_key" not in data
    assert "api_secret" not in data


@pytest.mark.asyncio
async def test_create_connection_unauthenticated(
    client: AsyncClient, shopify_payload: dict
):
    """POST /api/v1/connections without auth returns 401."""
    resp = await client.post("/api/v1/connections", json=shopify_payload)
    assert resp.status_code == 401


# ── List Connections Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_connections_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/connections returns empty list for new user."""
    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_connections_after_create(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """GET /api/v1/connections returns created connections."""
    await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["platform"] == "shopify"


@pytest.mark.asyncio
async def test_list_connections_user_isolation(client: AsyncClient):
    """Connections created by user A are not visible to user B."""
    headers_a = await register_and_login(client)
    await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://a-store.myshopify.com",
            "api_key": "key_a",
        },
        headers=headers_a,
    )

    headers_b = await register_and_login(client)
    resp = await client.get("/api/v1/connections", headers=headers_b)
    assert len(resp.json()) == 0


# ── Get Single Connection Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_get_connection(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """GET /api/v1/connections/{id} returns the correct connection."""
    create_resp = await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/connections/{conn_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == conn_id


@pytest.mark.asyncio
async def test_get_connection_not_found(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/connections/{random_id} returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/connections/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Update Connection Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_update_connection(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """PATCH /api/v1/connections/{id} updates store_url."""
    create_resp = await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/connections/{conn_id}",
        json={"store_url": "https://updated-store.myshopify.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["store_url"] == "https://updated-store.myshopify.com"


@pytest.mark.asyncio
async def test_update_connection_deactivate(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """PATCH /api/v1/connections/{id} can deactivate a connection."""
    create_resp = await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/connections/{conn_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# ── Delete Connection Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_connection(
    client: AsyncClient, auth_headers: dict, shopify_payload: dict
):
    """DELETE /api/v1/connections/{id} removes the connection (204)."""
    create_resp = await client.post(
        "/api/v1/connections",
        json=shopify_payload,
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/connections/{conn_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(
        f"/api/v1/connections/{conn_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_not_found(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /api/v1/connections/{random_id} returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/connections/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404
