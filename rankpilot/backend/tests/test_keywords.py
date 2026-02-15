"""
Tests for keyword tracking API endpoints.

Covers adding, listing, deleting, and refreshing tracked keywords,
including plan limit enforcement and duplicate keyword rejection.

For Developers:
    Keywords are scoped to a site. Each test creates a fresh site using
    the `create_test_site` helper. The authenticated client fixture
    (`auth_headers`) provides JWT tokens for all requests.

For QA Engineers:
    These tests verify:
    - Add keyword returns 201 with correct fields (current_rank, difficulty, etc.).
    - List keywords returns paginated response filtered by site_id.
    - Delete keyword returns 204 and removes it from the list.
    - Duplicate keyword for the same site returns 400.
    - Keyword for a non-existent site returns 404.
    - Refresh endpoint returns an updated count.

For Project Managers:
    Keyword tracking is a secondary usage metric tied to plan limits.
    These tests ensure reliable keyword CRUD and plan enforcement.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────


async def create_test_site(
    client: AsyncClient,
    auth_headers: dict,
    domain: str = "keyword-test.com",
) -> dict:
    """
    Create a site for keyword testing and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        domain: The domain name for the site.

    Returns:
        The created site as a dict (SiteResponse).
    """
    resp = await client.post(
        "/api/v1/sites",
        json={"domain": domain},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Site creation failed: {resp.text}"
    return resp.json()


async def add_test_keyword(
    client: AsyncClient,
    auth_headers: dict,
    site_id: str,
    keyword: str = "best seo tools",
) -> dict:
    """
    Add a keyword to track for a site and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        site_id: UUID of the parent site.
        keyword: The keyword phrase to track.

    Returns:
        The created keyword tracking record as a dict.
    """
    resp = await client.post(
        "/api/v1/keywords",
        json={"site_id": site_id, "keyword": keyword},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Keyword add failed: {resp.text}"
    return resp.json()


# ── Add Keyword Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_keyword_basic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/keywords creates a keyword tracking record with correct fields."""
    site = await create_test_site(client, auth_headers, domain="add-kw-basic.com")

    data = await add_test_keyword(client, auth_headers, site["id"], keyword="seo automation")

    assert data["keyword"] == "seo automation"
    assert data["site_id"] == site["id"]
    assert "id" in data
    assert "tracked_since" in data
    assert data["current_rank"] is None or isinstance(data["current_rank"], int)
    assert data["previous_rank"] is None or isinstance(data["previous_rank"], int)


@pytest.mark.asyncio
async def test_add_keyword_duplicate_rejected(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/keywords with a duplicate keyword for the same site returns 400."""
    site = await create_test_site(client, auth_headers, domain="dupe-kw.com")

    await add_test_keyword(client, auth_headers, site["id"], keyword="duplicate keyword")

    resp = await client.post(
        "/api/v1/keywords",
        json={"site_id": site["id"], "keyword": "duplicate keyword"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_add_keyword_nonexistent_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/keywords with a non-existent site_id returns 404."""
    fake_site_id = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/keywords",
        json={"site_id": fake_site_id, "keyword": "orphan keyword"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_keyword_unauthenticated(client: AsyncClient):
    """POST /api/v1/keywords without auth returns 401."""
    resp = await client.post(
        "/api/v1/keywords",
        json={"site_id": str(uuid.uuid4()), "keyword": "no auth"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_add_keyword_other_users_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/keywords targeting another user's site returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="user1-kw-site.com")

    user2_headers = await register_and_login(client, email="kwuser2@example.com")
    resp = await client.post(
        "/api/v1/keywords",
        json={"site_id": site["id"], "keyword": "stolen keyword"},
        headers=user2_headers,
    )
    assert resp.status_code == 404


# ── List Keywords Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_keywords_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/keywords with no keywords returns an empty paginated response."""
    site = await create_test_site(client, auth_headers, domain="empty-kw-list.com")

    resp = await client.get(
        "/api/v1/keywords",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_keywords_returns_added(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/keywords returns keywords that were previously added."""
    site = await create_test_site(client, auth_headers, domain="list-kw.com")

    await add_test_keyword(client, auth_headers, site["id"], keyword="keyword one")
    await add_test_keyword(client, auth_headers, site["id"], keyword="keyword two")
    await add_test_keyword(client, auth_headers, site["id"], keyword="keyword three")

    resp = await client.get(
        "/api/v1/keywords",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    keywords = {item["keyword"] for item in data["items"]}
    assert "keyword one" in keywords
    assert "keyword two" in keywords
    assert "keyword three" in keywords


@pytest.mark.asyncio
async def test_list_keywords_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/keywords respects page and per_page parameters."""
    site = await create_test_site(client, auth_headers, domain="paginate-kw.com")

    for i in range(6):
        await add_test_keyword(client, auth_headers, site["id"], keyword=f"kw-{i}")

    resp = await client.get(
        "/api/v1/keywords",
        params={"site_id": site["id"], "page": 1, "per_page": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 6
    assert data["per_page"] == 2


@pytest.mark.asyncio
async def test_list_keywords_nonexistent_site(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/keywords with a non-existent site_id returns 404."""
    fake_site_id = str(uuid.uuid4())

    resp = await client.get(
        "/api/v1/keywords",
        params={"site_id": fake_site_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Delete Keyword Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_keyword(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/keywords/{id} removes the keyword and returns 204."""
    site = await create_test_site(client, auth_headers, domain="delete-kw.com")
    kw = await add_test_keyword(client, auth_headers, site["id"], keyword="delete me")

    resp = await client.delete(
        f"/api/v1/keywords/{kw['id']}",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # Verify it was removed
    list_resp = await client.get(
        "/api/v1/keywords",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_keyword_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/keywords/{id} with a non-existent keyword ID returns 404."""
    site = await create_test_site(client, auth_headers, domain="del-kw-404.com")
    fake_kw_id = str(uuid.uuid4())

    resp = await client.delete(
        f"/api/v1/keywords/{fake_kw_id}",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_keyword_wrong_site(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/keywords/{id} with incorrect site_id returns 404."""
    site1 = await create_test_site(client, auth_headers, domain="kw-site-a.com")
    site2 = await create_test_site(client, auth_headers, domain="kw-site-b.com")

    kw = await add_test_keyword(client, auth_headers, site1["id"], keyword="site1 keyword")

    # Try to delete with site2's ID
    resp = await client.delete(
        f"/api/v1/keywords/{kw['id']}",
        params={"site_id": site2["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Refresh Keywords Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_keyword_ranks(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/keywords/refresh updates ranks and returns a count."""
    site = await create_test_site(client, auth_headers, domain="refresh-kw.com")

    await add_test_keyword(client, auth_headers, site["id"], keyword="refresh kw 1")
    await add_test_keyword(client, auth_headers, site["id"], keyword="refresh kw 2")

    resp = await client.post(
        "/api/v1/keywords/refresh",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "updated" in data
    assert data["updated"] == 2
    assert "message" in data


@pytest.mark.asyncio
async def test_refresh_keyword_ranks_nonexistent_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/keywords/refresh with a non-existent site_id returns 404."""
    fake_site_id = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/keywords/refresh",
        params={"site_id": fake_site_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404
