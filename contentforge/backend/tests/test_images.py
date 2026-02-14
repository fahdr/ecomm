"""
Image management endpoint tests.

Covers listing, retrieving, and deleting processed product images.
Images are created as side-effects of content generation jobs that
include image_urls, so the test setup creates generation jobs with
images first, then exercises the image-specific endpoints.

For Developers:
    Tests use the `register_and_login` helper from conftest.py to create
    authenticated users. Each test is independent (database is truncated
    between tests via the `setup_db` autouse fixture).

    Image records are created indirectly by POSTing to `/content/generate`
    with `image_urls` — the mock processing pipeline marks them as
    completed with simulated dimensions and sizes.

For QA Engineers:
    Run with: `pytest tests/test_images.py -v`
    Tests cover:
    - Listing images with pagination
    - Retrieving a single image by ID
    - Deleting an image
    - User isolation (user A cannot access user B's images)
    - 404 handling for nonexistent images
    - Empty list for users with no images
    - Unauthenticated access (401)

For Project Managers:
    Images are tied to generation jobs. These tests ensure that the image
    gallery endpoint works correctly, that pagination is functional, and
    that users can only see and manage their own processed images.

For End Users:
    These tests verify that your product images are correctly tracked,
    optimized, and only visible to you. You can view and delete images
    from the Images section of the dashboard.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


async def _create_job_with_images(
    client: AsyncClient, headers: dict, image_urls: list[str] | None = None
) -> dict:
    """
    Helper to create a generation job that includes product images.

    Creates a manual generation job with the given image URLs. The mock
    processing pipeline will mark images as completed with simulated data.

    Args:
        client: The test HTTP client.
        headers: Authorization headers for the authenticated user.
        image_urls: List of image URLs to process (defaults to two test URLs).

    Returns:
        The generation job response dict including image_items.
    """
    if image_urls is None:
        image_urls = [
            "https://example.com/product/photo1.jpg",
            "https://example.com/product/photo2.png",
        ]

    resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Product With Images"},
            "content_types": ["title"],
            "image_urls": image_urls,
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_list_images(client: AsyncClient):
    """GET /images/ returns paginated list of user's images."""
    headers = await register_and_login(client)

    # Create a job with 2 images
    await _create_job_with_images(client, headers)

    resp = await client.get("/api/v1/images/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert len(data["items"]) == 2

    # Verify each image has expected fields
    for img in data["items"]:
        assert img["status"] == "completed"
        assert img["format"] == "webp"
        assert img["width"] == 800
        assert img["height"] == 600
        assert img["size_bytes"] == 45000
        assert img["original_url"].startswith("https://example.com/")
        assert img["optimized_url"] is not None


@pytest.mark.asyncio
async def test_list_images_pagination(client: AsyncClient):
    """GET /images/ supports pagination with page and per_page params."""
    headers = await register_and_login(client)

    # Create 2 jobs with 2 images each = 4 images total
    await _create_job_with_images(
        client, headers, ["https://example.com/a1.jpg", "https://example.com/a2.jpg"]
    )
    await _create_job_with_images(
        client, headers, ["https://example.com/b1.jpg", "https://example.com/b2.jpg"]
    )

    # Fetch page 1 with per_page=2
    resp = await client.get("/api/v1/images/?page=1&per_page=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page"] == 1

    # Fetch page 2 with per_page=2
    resp = await client.get("/api/v1/images/?page=2&per_page=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_list_images_empty(client: AsyncClient):
    """GET /images/ returns empty list for a user with no images."""
    headers = await register_and_login(client)

    resp = await client.get("/api/v1/images/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_image_by_id(client: AsyncClient):
    """GET /images/{id} returns details for a specific image."""
    headers = await register_and_login(client)

    job_data = await _create_job_with_images(client, headers)
    image_id = job_data["image_items"][0]["id"]

    resp = await client.get(f"/api/v1/images/{image_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == image_id
    assert data["status"] == "completed"
    assert data["format"] == "webp"
    assert data["width"] == 800
    assert data["height"] == 600


@pytest.mark.asyncio
async def test_get_image_not_found(client: AsyncClient):
    """GET /images/{id} returns 404 for nonexistent image."""
    headers = await register_and_login(client)

    resp = await client.get(
        "/api/v1/images/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_image(client: AsyncClient):
    """DELETE /images/{id} removes the image record."""
    headers = await register_and_login(client)

    job_data = await _create_job_with_images(client, headers)
    image_id = job_data["image_items"][0]["id"]

    # Delete
    resp = await client.delete(f"/api/v1/images/{image_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get(f"/api/v1/images/{image_id}", headers=headers)
    assert resp.status_code == 404

    # Total image count should be reduced by 1
    resp = await client.get("/api/v1/images/", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_delete_image_not_found(client: AsyncClient):
    """DELETE /images/{id} returns 404 for nonexistent image."""
    headers = await register_and_login(client)

    resp = await client.delete(
        "/api/v1/images/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_image_isolation_between_users(client: AsyncClient):
    """Users cannot access or delete each other's images."""
    headers_a = await register_and_login(client, "img-user-a@example.com")
    headers_b = await register_and_login(client, "img-user-b@example.com")

    # User A creates a job with images
    job_data = await _create_job_with_images(client, headers_a)
    image_id = job_data["image_items"][0]["id"]

    # User B cannot fetch it
    resp = await client.get(f"/api/v1/images/{image_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B cannot delete it
    resp = await client.delete(f"/api/v1/images/{image_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B's image list should be empty
    resp = await client.get("/api/v1/images/", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_images_across_multiple_jobs(client: AsyncClient):
    """Images from different generation jobs appear in the same list."""
    headers = await register_and_login(client)

    # Job 1 with 1 image
    await _create_job_with_images(
        client, headers, ["https://example.com/job1-img.jpg"]
    )

    # Job 2 with 3 images
    await _create_job_with_images(
        client,
        headers,
        [
            "https://example.com/job2-img1.jpg",
            "https://example.com/job2-img2.jpg",
            "https://example.com/job2-img3.jpg",
        ],
    )

    resp = await client.get("/api/v1/images/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4


@pytest.mark.asyncio
async def test_delete_image_does_not_affect_job(client: AsyncClient):
    """Deleting an image does not delete the parent generation job."""
    headers = await register_and_login(client)

    job_data = await _create_job_with_images(client, headers)
    job_id = job_data["id"]
    image_id = job_data["image_items"][0]["id"]

    # Delete the image
    resp = await client.delete(f"/api/v1/images/{image_id}", headers=headers)
    assert resp.status_code == 204

    # Job should still exist
    resp = await client.get(f"/api/v1/content/jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_unauthenticated_access_images(client: AsyncClient):
    """Image endpoints require authentication."""
    resp = await client.get("/api/v1/images/")
    assert resp.status_code == 401

    resp = await client.delete(
        "/api/v1/images/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_image_has_correct_job_id(client: AsyncClient):
    """Each image record references the correct parent generation job."""
    headers = await register_and_login(client)

    job_data = await _create_job_with_images(
        client, headers, ["https://example.com/linked.jpg"]
    )
    job_id = job_data["id"]

    resp = await client.get("/api/v1/images/", headers=headers)
    assert resp.status_code == 200
    images = resp.json()["items"]
    assert len(images) == 1
    assert images[0]["job_id"] == job_id
