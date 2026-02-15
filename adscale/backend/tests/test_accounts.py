"""
Tests for ad account CRUD API endpoints.

Validates connecting, listing, and disconnecting external advertising
platform accounts (Google Ads, Meta Ads).

For Developers:
    Uses the ``auth_headers`` fixture from conftest.py for authenticated
    requests. Each test is isolated — the ``setup_db`` autouse fixture
    truncates all tables between tests.

For QA Engineers:
    Covers: connect success, duplicate account (409), list with pagination,
    disconnect success, disconnect nonexistent (404), unauthenticated (401),
    invalid ID format (400).

For Project Managers:
    Ad accounts are the entry point — users must connect at least one
    before they can create campaigns.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helper ──────────────────────────────────────────────────────────────


async def _connect_account(
    client: AsyncClient,
    headers: dict,
    platform: str = "google",
    external_id: str = "acct-001",
    name: str = "My Google Ads",
) -> dict:
    """
    Helper to connect an ad account and return the response JSON.

    Args:
        client: Async HTTP test client.
        headers: Auth headers from ``register_and_login``.
        platform: Ad platform ("google" or "meta").
        external_id: External account identifier.
        name: Human-readable account name.

    Returns:
        dict: The parsed JSON response body.
    """
    resp = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "platform": platform,
            "account_id_external": external_id,
            "account_name": name,
        },
    )
    return resp


# ── Connect Account Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_google_account(client: AsyncClient, auth_headers: dict):
    """POST /accounts with valid Google Ads data returns 201 and the new account."""
    resp = await _connect_account(client, auth_headers, platform="google")
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "google"
    assert data["account_id_external"] == "acct-001"
    assert data["account_name"] == "My Google Ads"
    assert data["is_connected"] is True
    assert data["status"] == "active"
    assert "id" in data
    assert "user_id" in data
    assert "connected_at" in data


@pytest.mark.asyncio
async def test_connect_meta_account(client: AsyncClient, auth_headers: dict):
    """POST /accounts with valid Meta Ads data returns 201."""
    resp = await _connect_account(
        client, auth_headers, platform="meta", external_id="meta-123", name="My Meta Ads"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "meta"
    assert data["account_id_external"] == "meta-123"
    assert data["account_name"] == "My Meta Ads"


@pytest.mark.asyncio
async def test_connect_duplicate_account_returns_409(
    client: AsyncClient, auth_headers: dict
):
    """Connecting the same external account twice returns 409 Conflict."""
    resp1 = await _connect_account(client, auth_headers)
    assert resp1.status_code == 201

    resp2 = await _connect_account(client, auth_headers)
    assert resp2.status_code == 409
    assert "already connected" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_connect_same_external_id_different_platform(
    client: AsyncClient, auth_headers: dict
):
    """The same external ID on different platforms should not conflict."""
    resp1 = await _connect_account(
        client, auth_headers, platform="google", external_id="shared-id"
    )
    assert resp1.status_code == 201

    resp2 = await _connect_account(
        client, auth_headers, platform="meta", external_id="shared-id"
    )
    assert resp2.status_code == 201


@pytest.mark.asyncio
async def test_connect_account_unauthenticated(client: AsyncClient):
    """POST /accounts without auth returns 401."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "google",
            "account_id_external": "acct-999",
            "account_name": "No Auth",
        },
    )
    assert resp.status_code == 401


# ── List Accounts Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_accounts_empty(client: AsyncClient, auth_headers: dict):
    """GET /accounts with no connected accounts returns empty list."""
    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["offset"] == 0
    assert data["limit"] == 50


@pytest.mark.asyncio
async def test_list_accounts_with_data(client: AsyncClient, auth_headers: dict):
    """GET /accounts after connecting 2 accounts returns them both."""
    await _connect_account(client, auth_headers, external_id="a1", name="Acct A")
    await _connect_account(
        client, auth_headers, platform="meta", external_id="a2", name="Acct B"
    )

    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_accounts_pagination(client: AsyncClient, auth_headers: dict):
    """GET /accounts respects offset and limit query parameters."""
    for i in range(5):
        await _connect_account(
            client, auth_headers, external_id=f"pg-{i}", name=f"Account {i}"
        )

    resp = await client.get(
        "/api/v1/accounts", headers=auth_headers, params={"offset": 2, "limit": 2}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["offset"] == 2
    assert data["limit"] == 2


@pytest.mark.asyncio
async def test_list_accounts_user_isolation(client: AsyncClient):
    """Accounts from user A are not visible to user B."""
    headers_a = await register_and_login(client, "user-a@test.com")
    headers_b = await register_and_login(client, "user-b@test.com")

    await _connect_account(client, headers_a, external_id="only-a", name="A's acct")

    resp = await client.get("/api/v1/accounts", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_accounts_unauthenticated(client: AsyncClient):
    """GET /accounts without auth returns 401."""
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 401


# ── Disconnect Account Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_disconnect_account_success(client: AsyncClient, auth_headers: dict):
    """DELETE /accounts/{id} returns 204 and marks the account as disconnected."""
    create_resp = await _connect_account(client, auth_headers)
    account_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/accounts/{account_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it's marked disconnected in the list
    list_resp = await client.get("/api/v1/accounts", headers=auth_headers)
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["is_connected"] is False
    assert items[0]["status"] == "paused"


@pytest.mark.asyncio
async def test_disconnect_nonexistent_account_returns_404(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /accounts/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(
        f"/api/v1/accounts/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_disconnect_account_invalid_uuid_returns_400(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /accounts/{bad-format} returns 400."""
    resp = await client.delete(
        "/api/v1/accounts/not-a-uuid", headers=auth_headers
    )
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_disconnect_other_users_account_returns_404(client: AsyncClient):
    """A user cannot disconnect another user's account (returns 404)."""
    headers_a = await register_and_login(client, "owner@test.com")
    headers_b = await register_and_login(client, "thief@test.com")

    create_resp = await _connect_account(client, headers_a)
    account_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/accounts/{account_id}", headers=headers_b
    )
    assert resp.status_code == 404
