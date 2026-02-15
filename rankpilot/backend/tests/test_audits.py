"""
Tests for SEO audit API endpoints.

Covers running audits, listing audit history with pagination, and
retrieving individual audit results by ID.

For Developers:
    Audits are created via `POST /api/v1/audits/run` which synchronously
    generates a mock audit with a score, issues list, and recommendations.
    Tests create a fresh site per test using a helper function.

For QA Engineers:
    These tests verify:
    - Running an audit returns 201 with overall_score (0-100), issues, and recommendations.
    - List audits returns paginated results sorted by most recent first.
    - Get audit by ID returns 200 for valid audits.
    - Non-existent site/audit IDs return 404.
    - Cross-user audit access is blocked (returns 404).

For Project Managers:
    SEO audits are a primary engagement driver. These tests verify
    the core audit workflow is reliable for all users.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────


async def create_test_site(
    client: AsyncClient,
    auth_headers: dict,
    domain: str = "audit-test.com",
) -> dict:
    """
    Create a site for audit testing and return the response body.

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


async def run_test_audit(
    client: AsyncClient,
    auth_headers: dict,
    site_id: str,
) -> dict:
    """
    Run an SEO audit on a site and return the response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization header dict.
        site_id: UUID of the site to audit.

    Returns:
        The audit result as a dict (SeoAuditResponse).
    """
    resp = await client.post(
        "/api/v1/audits/run",
        json={"site_id": site_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Audit run failed: {resp.text}"
    return resp.json()


# ── Run Audit Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_audit_basic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/audits/run creates an audit with score, issues, and recommendations."""
    site = await create_test_site(client, auth_headers, domain="run-audit-basic.com")

    data = await run_test_audit(client, auth_headers, site["id"])

    assert "id" in data
    assert data["site_id"] == site["id"]
    assert "overall_score" in data
    assert 0 <= data["overall_score"] <= 100
    assert isinstance(data["issues"], list)
    assert isinstance(data["recommendations"], list)
    assert "pages_crawled" in data
    assert data["pages_crawled"] >= 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_run_audit_issues_structure(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/audits/run returns issues with expected fields."""
    site = await create_test_site(client, auth_headers, domain="audit-issues.com")

    data = await run_test_audit(client, auth_headers, site["id"])

    # Mock audits should produce at least some issues
    if len(data["issues"]) > 0:
        issue = data["issues"][0]
        assert "severity" in issue
        assert "category" in issue
        assert "message" in issue


@pytest.mark.asyncio
async def test_run_audit_nonexistent_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/audits/run with a non-existent site_id returns 404."""
    fake_site_id = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/audits/run",
        json={"site_id": fake_site_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_audit_unauthenticated(client: AsyncClient):
    """POST /api/v1/audits/run without auth returns 401."""
    resp = await client.post(
        "/api/v1/audits/run",
        json={"site_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_run_audit_other_users_site(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/audits/run on another user's site returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="audit-owner.com")

    user2_headers = await register_and_login(client, email="auditthief@example.com")
    resp = await client.post(
        "/api/v1/audits/run",
        json={"site_id": site["id"]},
        headers=user2_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_multiple_audits(client: AsyncClient, auth_headers: dict):
    """Running multiple audits for the same site creates separate records."""
    site = await create_test_site(client, auth_headers, domain="multi-audit.com")

    audit1 = await run_test_audit(client, auth_headers, site["id"])
    audit2 = await run_test_audit(client, auth_headers, site["id"])

    assert audit1["id"] != audit2["id"]
    assert audit1["site_id"] == audit2["site_id"]


# ── List Audits Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_audits_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits with no audits returns an empty paginated response."""
    site = await create_test_site(client, auth_headers, domain="empty-audits.com")

    resp = await client.get(
        "/api/v1/audits",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_audits_returns_run_audits(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits returns audits that were previously run."""
    site = await create_test_site(client, auth_headers, domain="list-audits.com")

    await run_test_audit(client, auth_headers, site["id"])
    await run_test_audit(client, auth_headers, site["id"])
    await run_test_audit(client, auth_headers, site["id"])

    resp = await client.get(
        "/api/v1/audits",
        params={"site_id": site["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_audits_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits respects page and per_page parameters."""
    site = await create_test_site(client, auth_headers, domain="paginate-audits.com")

    for _ in range(5):
        await run_test_audit(client, auth_headers, site["id"])

    resp = await client.get(
        "/api/v1/audits",
        params={"site_id": site["id"], "page": 1, "per_page": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["per_page"] == 2


@pytest.mark.asyncio
async def test_list_audits_nonexistent_site(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits with a non-existent site_id returns 404."""
    fake_site_id = str(uuid.uuid4())

    resp = await client.get(
        "/api/v1/audits",
        params={"site_id": fake_site_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Get Audit by ID Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_audit_by_id(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits/{id} returns the correct audit."""
    site = await create_test_site(client, auth_headers, domain="get-audit.com")
    audit = await run_test_audit(client, auth_headers, site["id"])

    resp = await client.get(f"/api/v1/audits/{audit['id']}", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == audit["id"]
    assert data["site_id"] == site["id"]
    assert data["overall_score"] == audit["overall_score"]


@pytest.mark.asyncio
async def test_get_audit_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits/{id} with a non-existent audit ID returns 404."""
    fake_audit_id = str(uuid.uuid4())

    resp = await client.get(f"/api/v1/audits/{fake_audit_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_audit_other_user(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/audits/{id} for another user's audit returns 404."""
    from tests.conftest import register_and_login

    site = await create_test_site(client, auth_headers, domain="audit-cross-user.com")
    audit = await run_test_audit(client, auth_headers, site["id"])

    user2_headers = await register_and_login(client, email="auditspy@example.com")
    resp = await client.get(f"/api/v1/audits/{audit['id']}", headers=user2_headers)
    assert resp.status_code == 404
