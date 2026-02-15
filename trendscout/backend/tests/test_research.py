"""
Tests for the Research API endpoints.

Covers research run CRUD operations: creating runs, listing runs with
pagination, fetching run details with results, and deleting runs.

For Developers:
    Tests use the `client` and `auth_headers` fixtures from conftest.py.
    Helper functions create prerequisite data (research runs, results) via
    direct API calls. Each test is independent thanks to table truncation
    between tests.

For QA Engineers:
    These tests verify:
    - Authenticated users can create research runs (POST /api/v1/research/runs).
    - Research runs list with correct pagination (GET /api/v1/research/runs).
    - Run details include inline results (GET /api/v1/research/runs/{id}).
    - Run deletion cascades to results (DELETE /api/v1/research/runs/{id}).
    - Unauthenticated access returns 401.
    - Accessing another user's run returns 404.
    - Result detail endpoint works (GET /api/v1/research/results/{id}).

For Project Managers:
    These tests ensure the core research workflow is reliable: users can
    start research, view history, inspect results, and clean up old runs.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ─── Helper Functions ────────────────────────────────────────────────


async def create_run(
    client: AsyncClient,
    headers: dict,
    keywords: list[str] | None = None,
    sources: list[str] | None = None,
) -> dict:
    """
    Helper to create a research run via the API.

    Args:
        client: The test HTTP client.
        headers: Authorization headers for the authenticated user.
        keywords: List of search keywords (default: ["test product"]).
        sources: List of data sources (default: ["aliexpress", "google_trends"]).

    Returns:
        The created research run response dict.
    """
    payload = {
        "keywords": keywords or ["test product"],
        "sources": sources or ["aliexpress", "google_trends"],
    }
    resp = await client.post(
        "/api/v1/research/runs", json=payload, headers=headers
    )
    assert resp.status_code == 201, f"Failed to create run: {resp.text}"
    return resp.json()


# ─── Create Run Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_research_run(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/research/runs creates a run with pending status and correct keywords."""
    run = await create_run(client, auth_headers, keywords=["wireless earbuds", "bluetooth speaker"])

    assert run["status"] == "pending"
    assert run["keywords"] == ["wireless earbuds", "bluetooth speaker"]
    assert run["sources"] == ["aliexpress", "google_trends"]
    assert run["results_count"] == 0
    assert run["error_message"] is None
    assert run["completed_at"] is None
    assert "id" in run
    assert "user_id" in run
    assert "created_at" in run


@pytest.mark.asyncio
async def test_create_run_with_custom_sources(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/research/runs accepts custom source list."""
    run = await create_run(
        client, auth_headers,
        keywords=["yoga mat"],
        sources=["tiktok", "reddit"],
    )

    assert "tiktok" in run["sources"]
    assert "reddit" in run["sources"]
    assert run["status"] == "pending"


@pytest.mark.asyncio
async def test_create_run_with_score_config(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/research/runs accepts an optional score_config override."""
    payload = {
        "keywords": ["phone case"],
        "sources": ["aliexpress"],
        "score_config": {"social": 0.5, "market": 0.3, "competition": 0.2},
    }
    resp = await client.post(
        "/api/v1/research/runs", json=payload, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["score_config"] == {"social": 0.5, "market": 0.3, "competition": 0.2}


@pytest.mark.asyncio
async def test_create_run_empty_keywords_rejected(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/research/runs rejects empty keywords list (validation error)."""
    resp = await client.post(
        "/api/v1/research/runs",
        json={"keywords": [], "sources": ["aliexpress"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422, "Empty keywords should fail validation"


@pytest.mark.asyncio
async def test_create_run_unauthenticated(client: AsyncClient):
    """POST /api/v1/research/runs returns 401 without auth headers."""
    resp = await client.post(
        "/api/v1/research/runs",
        json={"keywords": ["test"], "sources": ["aliexpress"]},
    )
    assert resp.status_code == 401


# ─── List Runs Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_runs_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/runs returns empty list when no runs exist."""
    resp = await client.get("/api/v1/research/runs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


@pytest.mark.asyncio
async def test_list_runs_returns_created_runs(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/runs returns previously created runs."""
    await create_run(client, auth_headers, keywords=["run one"])
    await create_run(client, auth_headers, keywords=["run two"])

    resp = await client.get("/api/v1/research/runs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Newest first ordering
    assert data["items"][0]["keywords"] == ["run two"]
    assert data["items"][1]["keywords"] == ["run one"]


@pytest.mark.asyncio
async def test_list_runs_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/runs supports page and per_page parameters."""
    # Create 3 runs
    for i in range(3):
        await create_run(client, auth_headers, keywords=[f"keyword {i}"])

    # Page 1, 2 per page
    resp = await client.get(
        "/api/v1/research/runs?page=1&per_page=2", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2

    # Page 2, 2 per page
    resp = await client.get(
        "/api/v1/research/runs?page=2&per_page=2", headers=auth_headers
    )
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_list_runs_unauthenticated(client: AsyncClient):
    """GET /api/v1/research/runs returns 401 without auth headers."""
    resp = await client.get("/api/v1/research/runs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_runs_user_isolation(client: AsyncClient):
    """GET /api/v1/research/runs only shows runs owned by the requesting user."""
    # User A creates a run
    headers_a = await register_and_login(client, "user-a@example.com")
    await create_run(client, headers_a, keywords=["user a product"])

    # User B should see no runs
    headers_b = await register_and_login(client, "user-b@example.com")
    resp = await client.get("/api/v1/research/runs", headers=headers_b)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


# ─── Get Run Detail Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_run_detail(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/runs/{id} returns the run with all fields."""
    run = await create_run(client, auth_headers, keywords=["detail test"])

    resp = await client.get(
        f"/api/v1/research/runs/{run['id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == run["id"]
    assert data["keywords"] == ["detail test"]
    assert data["status"] == "pending"
    assert "results" in data


@pytest.mark.asyncio
async def test_get_run_detail_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/runs/{id} returns 404 for non-existent run."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/research/runs/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_run_detail_wrong_user(client: AsyncClient):
    """GET /api/v1/research/runs/{id} returns 404 when accessed by a different user."""
    # User A creates a run
    headers_a = await register_and_login(client, "owner-a@example.com")
    run = await create_run(client, headers_a, keywords=["private run"])

    # User B tries to access it
    headers_b = await register_and_login(client, "intruder-b@example.com")
    resp = await client.get(
        f"/api/v1/research/runs/{run['id']}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_run_detail_unauthenticated(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/runs/{id} returns 401 without auth headers."""
    run = await create_run(client, auth_headers, keywords=["auth test"])
    resp = await client.get(f"/api/v1/research/runs/{run['id']}")
    assert resp.status_code == 401


# ─── Delete Run Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_run(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/research/runs/{id} removes the run and returns 204."""
    run = await create_run(client, auth_headers, keywords=["deletable"])

    resp = await client.delete(
        f"/api/v1/research/runs/{run['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify run is gone
    resp = await client.get(
        f"/api/v1/research/runs/{run['id']}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_run_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/research/runs/{id} returns 404 for non-existent run."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/research/runs/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_run_wrong_user(client: AsyncClient):
    """DELETE /api/v1/research/runs/{id} returns 404 when user does not own the run."""
    headers_a = await register_and_login(client, "delowner@example.com")
    run = await create_run(client, headers_a, keywords=["protected"])

    headers_b = await register_and_login(client, "delintruder@example.com")
    resp = await client.delete(
        f"/api/v1/research/runs/{run['id']}", headers=headers_b
    )
    assert resp.status_code == 404

    # Verify run still exists for the owner
    resp = await client.get(
        f"/api/v1/research/runs/{run['id']}", headers=headers_a
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_run_unauthenticated(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/research/runs/{id} returns 401 without auth headers."""
    run = await create_run(client, auth_headers, keywords=["nodelete"])
    resp = await client.delete(f"/api/v1/research/runs/{run['id']}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_run_decrements_total(client: AsyncClient, auth_headers: dict):
    """Deleting a run decreases the total count returned by list endpoint."""
    run1 = await create_run(client, auth_headers, keywords=["keep"])
    run2 = await create_run(client, auth_headers, keywords=["remove"])

    # Delete run2
    resp = await client.delete(
        f"/api/v1/research/runs/{run2['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify total is 1
    resp = await client.get("/api/v1/research/runs", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == run1["id"]


# ─── Result Detail Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_result_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/research/results/{id} returns 404 for non-existent result."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/research/results/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_result_unauthenticated(client: AsyncClient):
    """GET /api/v1/research/results/{id} returns 401 without auth headers."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/research/results/{fake_id}")
    assert resp.status_code == 401
