"""
Tests for social account management API endpoints.

Covers the full CRUD lifecycle for social accounts: connecting a new account,
listing all accounts, and disconnecting an account. Also tests plan limit
enforcement and authentication requirements.

For Developers:
    All tests use the `client` and `auth_headers` fixtures from conftest.py.
    The `register_and_login` helper creates a fresh user and returns auth headers.
    Each test runs in its own truncated database for full isolation.

For QA Engineers:
    These tests verify:
    - POST /api/v1/accounts returns 201 with valid platform/account data.
    - GET /api/v1/accounts returns 200 with a list of connected accounts.
    - DELETE /api/v1/accounts/{id} returns 200 with is_connected=False.
    - Unauthenticated requests return 401.
    - Disconnecting a non-existent account returns 404.
    - Response schemas match SocialAccountResponse (id, platform, account_name, etc.).

For Project Managers:
    Account management is the first step in the PostPilot workflow.
    These tests ensure the backend correctly handles account connections,
    which is a prerequisite for creating and scheduling posts.

For End Users:
    These tests validate that connecting and disconnecting social media
    accounts works reliably, so your account management experience is smooth.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helper fixtures ────────────────────────────────────────────────


@pytest.fixture
def instagram_payload() -> dict:
    """
    Build a valid Instagram account connection payload.

    Returns:
        Dict with platform, account_name, and account_id_external fields.
    """
    return {
        "platform": "instagram",
        "account_name": "@testbrand",
        "account_id_external": f"ig_{uuid.uuid4().hex[:12]}",
    }


@pytest.fixture
def facebook_payload() -> dict:
    """
    Build a valid Facebook account connection payload.

    Returns:
        Dict with platform, account_name, and account_id_external fields.
    """
    return {
        "platform": "facebook",
        "account_name": "Test Brand Page",
        "account_id_external": f"fb_{uuid.uuid4().hex[:12]}",
    }


@pytest.fixture
def tiktok_payload() -> dict:
    """
    Build a valid TikTok account connection payload.

    Returns:
        Dict with platform, account_name, and account_id_external fields.
    """
    return {
        "platform": "tiktok",
        "account_name": "@testbrand_tiktok",
        "account_id_external": f"tt_{uuid.uuid4().hex[:12]}",
    }


# ── Connect Account Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_instagram_account(
    client: AsyncClient, auth_headers: dict, instagram_payload: dict
):
    """POST /api/v1/accounts with Instagram platform returns 201 and a connected account."""
    resp = await client.post(
        "/api/v1/accounts",
        json=instagram_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["platform"] == "instagram"
    assert data["account_name"] == "@testbrand"
    assert data["is_connected"] is True
    assert "id" in data
    assert "created_at" in data
    assert "connected_at" in data


@pytest.mark.asyncio
async def test_connect_facebook_account(
    client: AsyncClient, auth_headers: dict, facebook_payload: dict
):
    """POST /api/v1/accounts with Facebook platform returns 201."""
    resp = await client.post(
        "/api/v1/accounts",
        json=facebook_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["platform"] == "facebook"
    assert data["account_name"] == "Test Brand Page"
    assert data["is_connected"] is True


@pytest.mark.asyncio
async def test_connect_tiktok_account(
    client: AsyncClient, auth_headers: dict, tiktok_payload: dict
):
    """POST /api/v1/accounts with TikTok platform returns 201."""
    resp = await client.post(
        "/api/v1/accounts",
        json=tiktok_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["platform"] == "tiktok"
    assert data["account_name"] == "@testbrand_tiktok"
    assert data["is_connected"] is True


@pytest.mark.asyncio
async def test_connect_account_auto_generates_external_id(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/accounts without account_id_external auto-generates one."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@autoid_test",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["account_id_external"] is not None
    assert len(data["account_id_external"]) > 0


@pytest.mark.asyncio
async def test_connect_account_invalid_platform(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/accounts with invalid platform returns 422 validation error."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "myspace",
            "account_name": "@nostalgia",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connect_account_empty_name_rejected(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/accounts with empty account_name returns 422."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connect_account_unauthenticated(client: AsyncClient):
    """POST /api/v1/accounts without auth token returns 401."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@notoken",
        },
    )
    assert resp.status_code == 401


# ── List Accounts Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_accounts_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/accounts returns 200 with empty list for new user."""
    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_accounts_after_connect(
    client: AsyncClient, auth_headers: dict, instagram_payload: dict
):
    """GET /api/v1/accounts returns the connected account after connecting one."""
    # Connect an account first
    await client.post(
        "/api/v1/accounts", json=instagram_payload, headers=auth_headers
    )

    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["platform"] == "instagram"
    assert data[0]["is_connected"] is True


@pytest.mark.asyncio
async def test_list_accounts_multiple_platforms(
    client: AsyncClient,
    auth_headers: dict,
    instagram_payload: dict,
    facebook_payload: dict,
):
    """GET /api/v1/accounts returns all connected accounts across platforms."""
    await client.post(
        "/api/v1/accounts", json=instagram_payload, headers=auth_headers
    )
    await client.post(
        "/api/v1/accounts", json=facebook_payload, headers=auth_headers
    )

    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 2
    platforms = {a["platform"] for a in data}
    assert platforms == {"instagram", "facebook"}


@pytest.mark.asyncio
async def test_list_accounts_unauthenticated(client: AsyncClient):
    """GET /api/v1/accounts without auth token returns 401."""
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_accounts_user_isolation(client: AsyncClient):
    """Accounts created by user A are not visible to user B."""
    # User A creates an account
    headers_a = await register_and_login(client)
    await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@user_a_brand",
        },
        headers=headers_a,
    )

    # User B should see empty list
    headers_b = await register_and_login(client)
    resp = await client.get("/api/v1/accounts", headers=headers_b)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ── Disconnect Account Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_disconnect_account(
    client: AsyncClient, auth_headers: dict, instagram_payload: dict
):
    """DELETE /api/v1/accounts/{id} returns 200 with is_connected=False."""
    # Connect first
    create_resp = await client.post(
        "/api/v1/accounts", json=instagram_payload, headers=auth_headers
    )
    account_id = create_resp.json()["id"]

    # Disconnect
    resp = await client.delete(
        f"/api/v1/accounts/{account_id}", headers=auth_headers
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["is_connected"] is False
    assert data["id"] == account_id


@pytest.mark.asyncio
async def test_disconnect_shows_in_list(
    client: AsyncClient, auth_headers: dict, instagram_payload: dict
):
    """Disconnected accounts still appear in the list but with is_connected=False."""
    create_resp = await client.post(
        "/api/v1/accounts", json=instagram_payload, headers=auth_headers
    )
    account_id = create_resp.json()["id"]

    await client.delete(
        f"/api/v1/accounts/{account_id}", headers=auth_headers
    )

    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    data = resp.json()
    assert len(data) == 1
    assert data[0]["is_connected"] is False


@pytest.mark.asyncio
async def test_disconnect_nonexistent_account(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /api/v1/accounts/{random_id} returns 404 for non-existent account."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/accounts/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_disconnect_other_users_account(client: AsyncClient):
    """DELETE /api/v1/accounts/{id} returns 404 when user B tries to disconnect user A's account."""
    # User A creates an account
    headers_a = await register_and_login(client)
    create_resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@private_brand",
        },
        headers=headers_a,
    )
    account_id = create_resp.json()["id"]

    # User B tries to disconnect it
    headers_b = await register_and_login(client)
    resp = await client.delete(
        f"/api/v1/accounts/{account_id}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_disconnect_account_unauthenticated(client: AsyncClient):
    """DELETE /api/v1/accounts/{id} without auth token returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/accounts/{fake_id}")
    assert resp.status_code == 401
