"""
Content generation endpoint tests.

For Developers:
    Tests cover the full generation lifecycle including job creation,
    listing, retrieval, content editing, deletion, bulk generation,
    and plan limit enforcement.

For QA Engineers:
    Each test is independent (database is truncated between tests).
    Tests use the `register_and_login` helper to create authenticated users.
    Plan limit tests create exactly the limit + 1 jobs to verify enforcement.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_generation_job_from_url(client: AsyncClient):
    """POST /content/generate with a URL creates a completed job."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_url": "https://example.com/product/widget",
            "source_type": "url",
            "source_data": {
                "name": "Super Widget",
                "price": "29.99",
                "category": "Gadgets",
                "features": ["Wireless", "Rechargeable", "Compact"],
            },
            "content_types": ["title", "description", "meta_description", "keywords", "bullet_points"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    assert data["source_url"] == "https://example.com/product/widget"
    assert data["source_type"] == "url"
    assert len(data["content_items"]) == 5

    # Verify content types
    content_types = {item["content_type"] for item in data["content_items"]}
    assert content_types == {"title", "description", "meta_description", "keywords", "bullet_points"}

    # Verify word counts are populated
    for item in data["content_items"]:
        assert item["word_count"] > 0
        assert item["content"] != ""
        assert item["version"] == 1


@pytest.mark.asyncio
async def test_create_generation_job_manual(client: AsyncClient):
    """POST /content/generate with manual data creates a completed job."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {
                "name": "Ergonomic Keyboard",
                "price": "89.99",
                "category": "Electronics",
                "features": ["Split design", "Mechanical keys", "RGB lighting"],
            },
            "content_types": ["title", "description"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    assert data["source_type"] == "manual"
    assert len(data["content_items"]) == 2

    content_types = {item["content_type"] for item in data["content_items"]}
    assert content_types == {"title", "description"}


@pytest.mark.asyncio
async def test_generation_plan_limit(client: AsyncClient):
    """POST /content/generate returns 403 when free tier limit (10) is exceeded."""
    headers = await register_and_login(client)

    # Create 10 jobs (free tier limit)
    for i in range(10):
        resp = await client.post(
            "/api/v1/content/generate",
            headers=headers,
            json={
                "source_type": "manual",
                "source_data": {"name": f"Product {i}"},
                "content_types": ["title"],
            },
        )
        assert resp.status_code == 201, f"Job {i} failed: {resp.text}"

    # 11th job should fail
    resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Product 11"},
            "content_types": ["title"],
        },
    )
    assert resp.status_code == 403
    assert "limit" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_generation_jobs(client: AsyncClient):
    """GET /content/jobs returns paginated list of user's jobs."""
    headers = await register_and_login(client)

    # Create 3 jobs
    for i in range(3):
        await client.post(
            "/api/v1/content/generate",
            headers=headers,
            json={
                "source_type": "manual",
                "source_data": {"name": f"Product {i}"},
                "content_types": ["title"],
            },
        )

    resp = await client.get("/api/v1/content/jobs", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert len(data["items"]) == 3

    # Test pagination
    resp = await client.get(
        "/api/v1/content/jobs?page=1&per_page=2", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_job_with_content(client: AsyncClient):
    """GET /content/jobs/{id} returns job with all generated content."""
    headers = await register_and_login(client)

    # Create a job
    create_resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {
                "name": "Test Product",
                "price": "49.99",
                "features": ["Feature A", "Feature B"],
            },
            "content_types": ["title", "description", "keywords"],
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # Fetch the job
    resp = await client.get(f"/api/v1/content/jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert data["status"] == "completed"
    assert len(data["content_items"]) == 3

    # Verify each content item has content
    for item in data["content_items"]:
        assert item["content"] != ""
        assert item["word_count"] > 0


@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient):
    """DELETE /content/jobs/{id} removes the job and all content."""
    headers = await register_and_login(client)

    # Create a job
    create_resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Deletable Product"},
            "content_types": ["title"],
        },
    )
    job_id = create_resp.json()["id"]

    # Delete
    resp = await client.delete(f"/api/v1/content/jobs/{job_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/api/v1/content/jobs/{job_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_edit_generated_content(client: AsyncClient):
    """PATCH /content/{content_id} updates the content text."""
    headers = await register_and_login(client)

    # Create a job
    create_resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Editable Product"},
            "content_types": ["title"],
        },
    )
    content_id = create_resp.json()["content_items"][0]["id"]

    # Edit the content
    resp = await client.patch(
        f"/api/v1/content/{content_id}",
        headers=headers,
        json={"content": "My Custom Title That I Wrote"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "My Custom Title That I Wrote"
    assert data["word_count"] == 6


@pytest.mark.asyncio
async def test_delete_job_not_found(client: AsyncClient):
    """DELETE /content/jobs/{id} returns 404 for nonexistent job."""
    headers = await register_and_login(client)
    resp = await client.delete(
        "/api/v1/content/jobs/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient):
    """GET /content/jobs/{id} returns 404 for nonexistent job."""
    headers = await register_and_login(client)
    resp = await client.get(
        "/api/v1/content/jobs/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_job_isolation_between_users(client: AsyncClient):
    """Users cannot access each other's generation jobs."""
    headers_a = await register_and_login(client, "user-a@example.com")
    headers_b = await register_and_login(client, "user-b@example.com")

    # User A creates a job
    create_resp = await client.post(
        "/api/v1/content/generate",
        headers=headers_a,
        json={
            "source_type": "manual",
            "source_data": {"name": "Private Product"},
            "content_types": ["title"],
        },
    )
    job_id = create_resp.json()["id"]

    # User B cannot access it
    resp = await client.get(f"/api/v1/content/jobs/{job_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B's job list should be empty
    resp = await client.get("/api/v1/content/jobs", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_generation_with_images(client: AsyncClient):
    """POST /content/generate with image_urls creates image jobs."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Product With Images"},
            "content_types": ["title"],
            "image_urls": [
                "https://example.com/img1.jpg",
                "https://example.com/img2.png",
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["image_items"]) == 2
    for img in data["image_items"]:
        assert img["status"] == "completed"
        assert img["format"] == "webp"
        assert img["width"] == 800
        assert img["height"] == 600


@pytest.mark.asyncio
async def test_bulk_generation_from_urls(client: AsyncClient):
    """POST /content/generate/bulk creates multiple jobs from URLs."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/generate/bulk",
        headers=headers,
        json={
            "urls": [
                "https://example.com/product-1",
                "https://example.com/product-2",
            ],
            "content_types": ["title", "description"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    for job in data:
        assert job["status"] == "completed"
        assert len(job["content_items"]) == 2


@pytest.mark.asyncio
async def test_unauthenticated_access(client: AsyncClient):
    """Content endpoints require authentication."""
    resp = await client.post(
        "/api/v1/content/generate",
        json={"source_type": "manual", "source_data": {"name": "Test"}},
    )
    assert resp.status_code == 401

    resp = await client.get("/api/v1/content/jobs")
    assert resp.status_code == 401
