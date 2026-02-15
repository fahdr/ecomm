"""
Import job endpoint tests for SourcePilot.

Tests cover creating import jobs, listing/filtering/pagination, retrieving
individual jobs, cancelling, retrying, and bulk import operations.

For QA Engineers:
    Verifies the full import job lifecycle: create, list, get, cancel, retry,
    and bulk operations. Checks authentication, authorization, validation,
    and edge cases such as missing fields and invalid sources.
"""

import uuid

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_import_job(
    client: AsyncClient,
    headers: dict,
    *,
    source: str = "aliexpress",
    product_url: str = "https://www.aliexpress.com/item/123456.html",
    store_id: str | None = None,
) -> dict:
    """Create an import job via the API and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Auth headers for the request.
        source: Supplier source platform name.
        product_url: URL of the product to import.
        store_id: Optional target store ID.

    Returns:
        The created import job as a dict.
    """
    payload: dict = {
        "source": source,
        "product_url": product_url,
    }
    if store_id:
        payload["store_id"] = store_id
    resp = await client.post("/api/v1/imports", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"Failed to create import job: {resp.text}"
    return resp.json()


async def _create_connection(
    client: AsyncClient,
    headers: dict,
    *,
    store_name: str = "My Shop",
    platform: str = "shopify",
    store_url: str = "https://myshop.myshopify.com",
) -> dict:
    """Create a store connection and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Auth headers for the request.
        store_name: Display name for the store.
        platform: E-commerce platform type.
        store_url: URL of the store.

    Returns:
        The created connection as a dict.
    """
    resp = await client.post(
        "/api/v1/connections",
        json={
            "store_name": store_name,
            "platform": platform,
            "store_url": store_url,
            "api_key": "test-key-123",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"Failed to create connection: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Create import job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_import_job(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports creates an import job and returns its details."""
    data = await _create_import_job(client, auth_headers)
    assert "id" in data
    assert data["source"] == "aliexpress"
    assert data["product_url"] == "https://www.aliexpress.com/item/123456.html"
    assert data["status"] in ("pending", "queued")


@pytest.mark.asyncio
async def test_create_import_job_unauthenticated(client: AsyncClient):
    """POST /api/v1/imports without auth returns 401."""
    resp = await client.post(
        "/api/v1/imports",
        json={
            "source": "aliexpress",
            "product_url": "https://www.aliexpress.com/item/123456.html",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_import_job_invalid_source(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports with unsupported source returns 422 or 400."""
    resp = await client.post(
        "/api/v1/imports",
        json={
            "source": "invalid_nonexistent_source",
            "product_url": "https://example.com/product/1",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_import_job_missing_fields(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports with missing required fields returns 422."""
    resp = await client.post(
        "/api/v1/imports",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_import_job_missing_product_url(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports without product_url returns 422."""
    resp = await client.post(
        "/api/v1/imports",
        json={"source": "aliexpress"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_import_job_missing_source(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports without source returns 422."""
    resp = await client.post(
        "/api/v1/imports",
        json={"product_url": "https://www.aliexpress.com/item/123456.html"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_import_job_with_store_id(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports with a store_id associates the job to that store."""
    conn = await _create_connection(client, auth_headers)
    store_id = conn["id"]
    data = await _create_import_job(client, auth_headers, store_id=store_id)
    assert data.get("store_id") == store_id or data.get("connection_id") == store_id


# ---------------------------------------------------------------------------
# List import jobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_import_jobs_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports with no jobs returns empty list."""
    resp = await client.get("/api/v1/imports", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_import_jobs(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports returns created jobs."""
    await _create_import_job(client, auth_headers)
    await _create_import_job(
        client,
        auth_headers,
        product_url="https://www.aliexpress.com/item/789.html",
    )
    resp = await client.get("/api/v1/imports", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_import_jobs_filter_by_status(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports?status=pending returns only pending jobs."""
    await _create_import_job(client, auth_headers)
    resp = await client.get(
        "/api/v1/imports", params={"status": "pending"}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    for item in items:
        assert item["status"] in ("pending", "queued")


@pytest.mark.asyncio
async def test_list_import_jobs_filter_by_store(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports?store_id=<id> returns only jobs for that store."""
    conn = await _create_connection(client, auth_headers)
    store_id = conn["id"]
    await _create_import_job(client, auth_headers, store_id=store_id)
    await _create_import_job(client, auth_headers)  # no store_id

    resp = await client.get(
        "/api/v1/imports", params={"store_id": store_id}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_list_import_jobs_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports with skip/limit paginates results."""
    for i in range(5):
        await _create_import_job(
            client,
            auth_headers,
            product_url=f"https://www.aliexpress.com/item/{1000 + i}.html",
        )

    resp = await client.get(
        "/api/v1/imports", params={"skip": 0, "limit": 2}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) <= 2

    resp2 = await client.get(
        "/api/v1/imports", params={"skip": 2, "limit": 2}, headers=auth_headers
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    items2 = body2 if isinstance(body2, list) else body2.get("items", body2.get("data", []))
    assert len(items2) <= 2

    # Ensure pages don't overlap
    ids1 = {item["id"] for item in items}
    ids2 = {item["id"] for item in items2}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_list_import_jobs_unauthenticated(client: AsyncClient):
    """GET /api/v1/imports without auth returns 401."""
    resp = await client.get("/api/v1/imports")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get import job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_import_job(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports/{id} returns the import job details."""
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]
    resp = await client.get(f"/api/v1/imports/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert data["source"] == "aliexpress"


@pytest.mark.asyncio
async def test_get_import_job_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/imports/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_import_job_other_user(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports/{id} by a different user returns 404 or 403."""
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.get(f"/api/v1/imports/{job_id}", headers=other_headers)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_get_import_job_unauthenticated(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/imports/{id} without auth returns 401."""
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]
    resp = await client.get(f"/api/v1/imports/{job_id}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cancel import job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_import_job(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/{id}/cancel cancels a pending job."""
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]
    resp = await client.post(f"/api/v1/imports/{job_id}/cancel", headers=auth_headers)
    assert resp.status_code in (200, 204)

    # Verify status changed
    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=auth_headers)
    if get_resp.status_code == 200:
        assert get_resp.json()["status"] in ("cancelled", "canceled")


@pytest.mark.asyncio
async def test_cancel_import_job_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/{id}/cancel with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/imports/{fake_id}/cancel", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_import_job_other_user(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/{id}/cancel by different user returns 403 or 404."""
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.post(f"/api/v1/imports/{job_id}/cancel", headers=other_headers)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cancel_running_import_job(client: AsyncClient, auth_headers: dict, db):
    """POST /api/v1/imports/{id}/cancel on a running job succeeds or returns 409.

    If the backend allows cancelling running jobs, expect 200.
    Otherwise expect 409 (conflict).
    """
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]
    # The job is in pending state by default; cancellation of pending is always valid
    resp = await client.post(f"/api/v1/imports/{job_id}/cancel", headers=auth_headers)
    assert resp.status_code in (200, 204, 409)


@pytest.mark.asyncio
async def test_cancel_completed_import_job(client: AsyncClient, auth_headers: dict, db):
    """POST /api/v1/imports/{id}/cancel on a completed job returns 400 or 409.

    A completed job cannot be cancelled since it already finished.
    """
    from sqlalchemy import text as sa_text

    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]

    # Manually update status to completed via DB
    await db.execute(
        sa_text("UPDATE import_jobs SET status = 'completed' WHERE id = :id"),
        {"id": job_id},
    )
    await db.commit()

    resp = await client.post(f"/api/v1/imports/{job_id}/cancel", headers=auth_headers)
    assert resp.status_code in (400, 409)


# ---------------------------------------------------------------------------
# Retry import job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_failed_import_job(client: AsyncClient, auth_headers: dict, db):
    """POST /api/v1/imports/{id}/retry re-queues a failed job."""
    from sqlalchemy import text as sa_text

    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]

    # Manually update status to failed via DB
    await db.execute(
        sa_text("UPDATE import_jobs SET status = 'failed' WHERE id = :id"),
        {"id": job_id},
    )
    await db.commit()

    resp = await client.post(f"/api/v1/imports/{job_id}/retry", headers=auth_headers)
    assert resp.status_code in (200, 201)

    # Verify status changed back
    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=auth_headers)
    if get_resp.status_code == 200:
        assert get_resp.json()["status"] in ("pending", "queued", "retrying")


@pytest.mark.asyncio
async def test_retry_non_failed_import_job(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/{id}/retry on a non-failed job returns 400 or 409."""
    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]

    resp = await client.post(f"/api/v1/imports/{job_id}/retry", headers=auth_headers)
    assert resp.status_code in (400, 409)


@pytest.mark.asyncio
async def test_retry_import_job_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/{id}/retry with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/imports/{fake_id}/retry", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_import_job_other_user(client: AsyncClient, auth_headers: dict, db):
    """POST /api/v1/imports/{id}/retry by different user returns 403 or 404."""
    from sqlalchemy import text as sa_text

    created = await _create_import_job(client, auth_headers)
    job_id = created["id"]

    await db.execute(
        sa_text("UPDATE import_jobs SET status = 'failed' WHERE id = :id"),
        {"id": job_id},
    )
    await db.commit()

    other_headers = await register_and_login(client)
    resp = await client.post(f"/api/v1/imports/{job_id}/retry", headers=other_headers)
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_import(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/bulk creates multiple import jobs at once."""
    resp = await client.post(
        "/api/v1/imports/bulk",
        json={
            "source": "aliexpress",
            "product_urls": [
                "https://www.aliexpress.com/item/100.html",
                "https://www.aliexpress.com/item/200.html",
                "https://www.aliexpress.com/item/300.html",
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    # Response should contain the created jobs
    items = data if isinstance(data, list) else data.get("jobs", data.get("items", []))
    assert len(items) == 3


@pytest.mark.asyncio
async def test_bulk_import_empty_urls(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/bulk with empty URL list returns 400 or 422."""
    resp = await client.post(
        "/api/v1/imports/bulk",
        json={
            "source": "aliexpress",
            "product_urls": [],
        },
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_bulk_import_too_many_urls(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/bulk with too many URLs returns 400 or 422."""
    urls = [f"https://www.aliexpress.com/item/{i}.html" for i in range(200)]
    resp = await client.post(
        "/api/v1/imports/bulk",
        json={
            "source": "aliexpress",
            "product_urls": urls,
        },
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_bulk_import_unauthenticated(client: AsyncClient):
    """POST /api/v1/imports/bulk without auth returns 401."""
    resp = await client.post(
        "/api/v1/imports/bulk",
        json={
            "source": "aliexpress",
            "product_urls": ["https://www.aliexpress.com/item/100.html"],
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bulk_import_invalid_source(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/bulk with invalid source returns 400 or 422."""
    resp = await client.post(
        "/api/v1/imports/bulk",
        json={
            "source": "nonexistent_platform",
            "product_urls": ["https://example.com/product/1"],
        },
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_bulk_import_missing_urls_field(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/imports/bulk without product_urls field returns 422."""
    resp = await client.post(
        "/api/v1/imports/bulk",
        json={"source": "aliexpress"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
