"""
Tests for site management API endpoints.

Covers the full CRUD lifecycle for sites (domains), including creation,
listing with pagination, retrieval by ID, updates, deletion, and the
domain verification endpoint.

For Developers:
    Uses the `auth_headers` fixture from conftest.py for authenticated
    requests. Each test creates its own site data to ensure isolation.
    The `setup_db` autouse fixture truncates all tables between tests.

For QA Engineers:
    These tests verify:
    - Create site returns 201 with correct fields.
    - List sites returns paginated response scoped to the authenticated user.
    - Get site by ID returns 200 or 404 for invalid IDs.
    - Update site (PATCH) modifies only provided fields.
    - Delete site returns 204 and the site is no longer retrievable.
    - Domain verification sets is_verified=True.
    - Operations on non-existent sites return 404.

For Project Managers:
    Sites are the top-level resource in RankPilot. All tests here
    ensure the foundation of the platform works reliably.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helper ─────────────────────────────────────────────────────────────────


async def create_test_site(
    client: AsyncClient,
    auth_headers: dict,
    domain: str = "example.com",
    sitemap_url: str | None = None,
) -> dict:
    """
    Create a site via the API and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        domain: The domain name for the site.
        sitemap_url: Optional XML sitemap URL.

    Returns:
        The created site as a dict (SiteResponse).
    """
    payload: dict = {"domain": domain}
    if sitemap_url is not None:
        payload["sitemap_url"] = sitemap_url

    resp = await client.post(
        "/api/v1/sites",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ── Create Site Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_site_basic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites creates a site and returns it with all expected fields."""
    data = await create_test_site(client, auth_headers, domain="test-site.com")

    assert data["domain"] == "test-site.com"
    assert data["is_verified"] is False
    assert data["status"] == "pending"
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["sitemap_url"] is None


@pytest.mark.asyncio
async def test_create_site_with_sitemap(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites with a sitemap_url stores the sitemap URL."""
    data = await create_test_site(
        client,
        auth_headers,
        domain="sitemap-site.com",
        sitemap_url="https://sitemap-site.com/sitemap.xml",
    )

    assert data["domain"] == "sitemap-site.com"
    assert data["sitemap_url"] == "https://sitemap-site.com/sitemap.xml"


@pytest.mark.asyncio
async def test_create_site_duplicate_domain(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites with a duplicate domain returns 400."""
    await create_test_site(client, auth_headers, domain="dupe-domain.com")

    resp = await client.post(
        "/api/v1/sites",
        json={"domain": "dupe-domain.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_site_invalid_domain_too_short(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites with a domain shorter than 3 chars returns 422."""
    resp = await client.post(
        "/api/v1/sites",
        json={"domain": "ab"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_site_unauthenticated(client: AsyncClient):
    """POST /api/v1/sites without auth returns 401."""
    resp = await client.post(
        "/api/v1/sites",
        json={"domain": "noauth.com"},
    )
    assert resp.status_code == 401


# ── List Sites Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sites_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites with no sites returns an empty paginated response."""
    resp = await client.get("/api/v1/sites", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_sites_returns_created(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites returns sites that were previously created."""
    await create_test_site(client, auth_headers, domain="list-test-1.com")
    await create_test_site(client, auth_headers, domain="list-test-2.com")

    resp = await client.get("/api/v1/sites", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    domains = {item["domain"] for item in data["items"]}
    assert "list-test-1.com" in domains
    assert "list-test-2.com" in domains


@pytest.mark.asyncio
async def test_list_sites_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites respects page and per_page parameters."""
    for i in range(5):
        await create_test_site(client, auth_headers, domain=f"page-test-{i}.com")

    # Request page 1 with 2 items per page
    resp = await client.get(
        "/api/v1/sites",
        params={"page": 1, "per_page": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 2


@pytest.mark.asyncio
async def test_list_sites_scoped_to_user(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites only returns sites for the authenticated user."""
    from tests.conftest import register_and_login

    # User 1 creates a site
    await create_test_site(client, auth_headers, domain="user1-site.com")

    # User 2 creates a different site
    user2_headers = await register_and_login(client, email="user2@example.com")
    await create_test_site(client, user2_headers, domain="user2-site.com")

    # User 1 should only see their own site
    resp = await client.get("/api/v1/sites", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["domain"] == "user1-site.com"


# ── Get Site by ID Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_site_by_id(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites/{id} returns the correct site."""
    site = await create_test_site(client, auth_headers, domain="get-test.com")
    site_id = site["id"]

    resp = await client.get(f"/api/v1/sites/{site_id}", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == site_id
    assert data["domain"] == "get-test.com"


@pytest.mark.asyncio
async def test_get_site_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites/{id} with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/sites/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_site_other_user(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/sites/{id} for another user's site returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="owned-by-user1.com")
    site_id = site["id"]

    # User 2 tries to access user 1's site
    user2_headers = await register_and_login(client, email="otheruser@example.com")
    resp = await client.get(f"/api/v1/sites/{site_id}", headers=user2_headers)
    assert resp.status_code == 404


# ── Update Site Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_site_domain(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sites/{id} updates the domain field."""
    site = await create_test_site(client, auth_headers, domain="old-domain.com")
    site_id = site["id"]

    resp = await client.patch(
        f"/api/v1/sites/{site_id}",
        json={"domain": "new-domain.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["domain"] == "new-domain.com"
    assert data["id"] == site_id


@pytest.mark.asyncio
async def test_update_site_sitemap(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sites/{id} updates the sitemap_url field."""
    site = await create_test_site(client, auth_headers, domain="sitemap-update.com")
    site_id = site["id"]

    resp = await client.patch(
        f"/api/v1/sites/{site_id}",
        json={"sitemap_url": "https://sitemap-update.com/sitemap.xml"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["sitemap_url"] == "https://sitemap-update.com/sitemap.xml"


@pytest.mark.asyncio
async def test_update_site_status(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sites/{id} updates the status field."""
    site = await create_test_site(client, auth_headers, domain="status-update.com")
    site_id = site["id"]

    resp = await client.patch(
        f"/api/v1/sites/{site_id}",
        json={"status": "active"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_update_site_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/sites/{id} with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/sites/{fake_id}",
        json={"domain": "ghost.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Delete Site Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_site(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/sites/{id} removes the site and returns 204."""
    site = await create_test_site(client, auth_headers, domain="delete-me.com")
    site_id = site["id"]

    resp = await client.delete(f"/api/v1/sites/{site_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify the site is gone
    resp = await client.get(f"/api/v1/sites/{site_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_site_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/sites/{id} with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/sites/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_site_other_user(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/sites/{id} for another user's site returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="protected-delete.com")
    site_id = site["id"]

    user2_headers = await register_and_login(client, email="deleter@example.com")
    resp = await client.delete(f"/api/v1/sites/{site_id}", headers=user2_headers)
    assert resp.status_code == 404


# ── Verify Site Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites/{id}/verify sets is_verified to True."""
    site = await create_test_site(client, auth_headers, domain="verify-me.com")
    site_id = site["id"]

    assert site["is_verified"] is False

    resp = await client.post(f"/api/v1/sites/{site_id}/verify", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["is_verified"] is True
    assert data["id"] == site_id


@pytest.mark.asyncio
async def test_verify_site_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites/{id}/verify with a non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/sites/{fake_id}/verify", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_site_other_user(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/sites/{id}/verify for another user's site returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="other-verify.com")
    site_id = site["id"]

    user2_headers = await register_and_login(client, email="verifier@example.com")
    resp = await client.post(f"/api/v1/sites/{site_id}/verify", headers=user2_headers)
    assert resp.status_code == 404
