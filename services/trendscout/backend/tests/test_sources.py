"""
Tests for the Source Configuration API endpoints.

Covers CRUD operations for external data source configurations:
creating, listing, updating, and deleting source configs. Also
verifies that credentials are never leaked in API responses.

For Developers:
    Tests use the `client` and `auth_headers` fixtures from conftest.py.
    Source configs represent external API connections (AliExpress, TikTok,
    Google Trends, Reddit) with encrypted credentials and settings.

For QA Engineers:
    These tests verify:
    - Create source config (POST /api/v1/sources).
    - List user's source configs (GET /api/v1/sources).
    - Update config credentials, settings, and active state (PATCH /api/v1/sources/{id}).
    - Delete config (DELETE /api/v1/sources/{id}).
    - Credentials are redacted in all responses (has_credentials flag only).
    - Invalid source types are rejected (400).
    - Unauthenticated access returns 401.
    - Cross-user access returns 404.

For Project Managers:
    Source configs control which external APIs are available for product
    research. Users must configure at least one source before running research.
    These tests ensure the configuration workflow is reliable and secure.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ─── Helper Functions ────────────────────────────────────────────────


async def create_source(
    client: AsyncClient,
    headers: dict,
    source_type: str = "aliexpress",
    credentials: dict | None = None,
    settings: dict | None = None,
) -> dict:
    """
    Helper to create a source config via the API.

    Args:
        client: The test HTTP client.
        headers: Authorization headers for the authenticated user.
        source_type: External source identifier (default: "aliexpress").
        credentials: Source-specific credentials (default: empty dict).
        settings: Source-specific settings (default: empty dict).

    Returns:
        The created source config response dict.
    """
    payload = {
        "source_type": source_type,
        "credentials": credentials or {},
        "settings": settings or {},
    }
    resp = await client.post("/api/v1/sources", json=payload, headers=headers)
    assert resp.status_code == 201, f"Failed to create source: {resp.text}"
    return resp.json()


# ─── Create Source Config Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_source_config(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sources creates a config with correct fields and is_active=True."""
    config = await create_source(
        client,
        auth_headers,
        source_type="aliexpress",
        credentials={"api_key": "secret_key_123"},
        settings={"region": "US", "language": "en"},
    )

    assert config["source_type"] == "aliexpress"
    assert config["has_credentials"] is True
    assert config["settings"] == {"region": "US", "language": "en"}
    assert config["is_active"] is True
    assert "id" in config
    assert "user_id" in config
    assert "created_at" in config
    assert "updated_at" in config


@pytest.mark.asyncio
async def test_create_source_credentials_redacted(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sources never returns raw credentials in the response."""
    config = await create_source(
        client,
        auth_headers,
        source_type="tiktok",
        credentials={"access_token": "super_secret_token"},
    )

    # Credentials should be redacted — only has_credentials flag visible
    assert "credentials" not in config
    assert config["has_credentials"] is True


@pytest.mark.asyncio
async def test_create_source_no_credentials(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sources with empty credentials sets has_credentials=False."""
    config = await create_source(
        client,
        auth_headers,
        source_type="google_trends",
        credentials={},
    )

    assert config["has_credentials"] is False


@pytest.mark.asyncio
async def test_create_source_all_valid_types(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sources accepts all four valid source types."""
    valid_types = ["aliexpress", "tiktok", "google_trends", "reddit"]

    for stype in valid_types:
        config = await create_source(client, auth_headers, source_type=stype)
        assert config["source_type"] == stype


@pytest.mark.asyncio
async def test_create_source_invalid_type(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sources rejects invalid source types with 400."""
    resp = await client.post(
        "/api/v1/sources",
        json={"source_type": "amazon", "credentials": {}, "settings": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Invalid source type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_source_unauthenticated(client: AsyncClient):
    """POST /api/v1/sources returns 401 without auth headers."""
    resp = await client.post(
        "/api/v1/sources",
        json={"source_type": "aliexpress", "credentials": {}, "settings": {}},
    )
    assert resp.status_code == 401


# ─── List Source Configs Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sources_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sources returns empty list when no configs exist."""
    resp = await client.get("/api/v1/sources", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_sources_returns_configs(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sources returns previously created configs."""
    await create_source(client, auth_headers, source_type="aliexpress")
    await create_source(client, auth_headers, source_type="reddit")

    resp = await client.get("/api/v1/sources", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2

    # Should be ordered by source_type
    source_types = [item["source_type"] for item in data["items"]]
    assert source_types == sorted(source_types)


@pytest.mark.asyncio
async def test_list_sources_credentials_always_redacted(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sources never exposes raw credentials in any listed config."""
    await create_source(
        client, auth_headers,
        source_type="tiktok",
        credentials={"token": "very_secret"},
    )

    resp = await client.get("/api/v1/sources", headers=auth_headers)
    data = resp.json()

    for item in data["items"]:
        assert "credentials" not in item
        assert "has_credentials" in item


@pytest.mark.asyncio
async def test_list_sources_user_isolation(client: AsyncClient):
    """GET /api/v1/sources only shows configs owned by the requesting user."""
    headers_a = await register_and_login(client, "src-user-a@example.com")
    await create_source(client, headers_a, source_type="aliexpress")

    headers_b = await register_and_login(client, "src-user-b@example.com")
    resp = await client.get("/api/v1/sources", headers=headers_b)
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_sources_unauthenticated(client: AsyncClient):
    """GET /api/v1/sources returns 401 without auth headers."""
    resp = await client.get("/api/v1/sources")
    assert resp.status_code == 401


# ─── Update Source Config Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_update_source_settings(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sources/{id} updates the settings field."""
    config = await create_source(
        client, auth_headers,
        source_type="aliexpress",
        settings={"region": "US"},
    )

    resp = await client.patch(
        f"/api/v1/sources/{config['id']}",
        json={"settings": {"region": "UK", "language": "en"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["settings"] == {"region": "UK", "language": "en"}


@pytest.mark.asyncio
async def test_update_source_credentials(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sources/{id} updates credentials (response still redacted)."""
    config = await create_source(
        client, auth_headers,
        source_type="google_trends",
        credentials={},
    )
    assert config["has_credentials"] is False

    resp = await client.patch(
        f"/api/v1/sources/{config['id']}",
        json={"credentials": {"api_key": "new_key_abc"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["has_credentials"] is True
    assert "credentials" not in updated


@pytest.mark.asyncio
async def test_update_source_active_toggle(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sources/{id} can toggle the is_active flag."""
    config = await create_source(client, auth_headers, source_type="reddit")
    assert config["is_active"] is True

    # Deactivate
    resp = await client.patch(
        f"/api/v1/sources/{config['id']}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Reactivate
    resp = await client.patch(
        f"/api/v1/sources/{config['id']}",
        json={"is_active": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_update_source_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sources/{id} returns 404 for non-existent config."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/sources/{fake_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_source_wrong_user(client: AsyncClient):
    """PATCH /api/v1/sources/{id} returns 404 when user does not own the config."""
    headers_a = await register_and_login(client, "src-owner@example.com")
    config = await create_source(client, headers_a, source_type="aliexpress")

    headers_b = await register_and_login(client, "src-intruder@example.com")
    resp = await client.patch(
        f"/api/v1/sources/{config['id']}",
        json={"is_active": False},
        headers=headers_b,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_source_unauthenticated(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sources/{id} returns 401 without auth headers."""
    config = await create_source(client, auth_headers, source_type="aliexpress")
    resp = await client.patch(
        f"/api/v1/sources/{config['id']}",
        json={"is_active": False},
    )
    assert resp.status_code == 401


# ─── Delete Source Config Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_source_config(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/sources/{id} removes the config and returns 204."""
    config = await create_source(client, auth_headers, source_type="reddit")

    resp = await client.delete(
        f"/api/v1/sources/{config['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify config is gone from the list
    resp = await client.get("/api/v1/sources", headers=auth_headers)
    data = resp.json()
    config_ids = [item["id"] for item in data["items"]]
    assert config["id"] not in config_ids


@pytest.mark.asyncio
async def test_delete_source_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/sources/{id} returns 404 for non-existent config."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/sources/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_source_wrong_user(client: AsyncClient):
    """DELETE /api/v1/sources/{id} returns 404 when user does not own the config."""
    headers_a = await register_and_login(client, "delsrc-owner@example.com")
    config = await create_source(client, headers_a, source_type="tiktok")

    headers_b = await register_and_login(client, "delsrc-intruder@example.com")
    resp = await client.delete(
        f"/api/v1/sources/{config['id']}", headers=headers_b
    )
    assert resp.status_code == 404

    # Verify config still exists for the owner
    resp = await client.get("/api/v1/sources", headers=headers_a)
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_delete_source_unauthenticated(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/sources/{id} returns 401 without auth headers."""
    config = await create_source(client, auth_headers, source_type="aliexpress")
    resp = await client.delete(f"/api/v1/sources/{config['id']}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_source_decrements_list(client: AsyncClient, auth_headers: dict):
    """Deleting a source config reduces the count returned by list endpoint."""
    c1 = await create_source(client, auth_headers, source_type="aliexpress")
    c2 = await create_source(client, auth_headers, source_type="reddit")

    # Delete one
    resp = await client.delete(
        f"/api/v1/sources/{c2['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify only one remains
    resp = await client.get("/api/v1/sources", headers=auth_headers)
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["source_type"] == "aliexpress"
