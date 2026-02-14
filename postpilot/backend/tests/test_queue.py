"""
Tests for content queue management API endpoints.

Covers the full content queue workflow: creating queue items, listing with
pagination and filtering, AI caption generation, approval/rejection workflow,
deletion rules, and authentication requirements.

For Developers:
    Queue items store product_data (JSON dict) and target platforms. The
    AI caption generation endpoint calls the caption_service which returns
    deterministic mock captions in test mode. The approval workflow moves
    items through pending -> approved/rejected status transitions.

For QA Engineers:
    These tests verify:
    - POST /api/v1/queue creates a pending queue item (201).
    - GET /api/v1/queue returns paginated results with total count.
    - GET /api/v1/queue/{id} retrieves a single item (200) or 404.
    - DELETE /api/v1/queue/{id} removes pending items (204), rejects approved (400).
    - POST /api/v1/queue/{id}/generate populates ai_generated_content.
    - POST /api/v1/queue/{id}/approve changes status to approved.
    - POST /api/v1/queue/{id}/reject changes status to rejected.
    - POST /api/v1/queue/generate-caption returns standalone caption without persisting.
    - Unauthenticated requests return 401.
    - Status transition rules are enforced.

For Project Managers:
    The content queue automates social media content creation by combining
    product data with AI-generated captions. These tests ensure the entire
    workflow is reliable.

For End Users:
    These tests validate that adding products to the queue, generating AI
    captions, and reviewing them works correctly before scheduling posts.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Fixtures ───────────────────────────────────────────────────────


SAMPLE_PRODUCT_DATA = {
    "title": "Wireless Noise-Cancelling Headphones",
    "description": "Premium over-ear headphones with 40-hour battery life and active noise cancellation.",
    "price": 79.99,
    "image_url": "https://cdn.example.com/headphones.jpg",
    "category": "Electronics",
}


@pytest.fixture
def queue_item_payload() -> dict:
    """
    Build a valid content queue item creation payload.

    Returns:
        Dict with product_data and platforms fields.
    """
    return {
        "product_data": SAMPLE_PRODUCT_DATA,
        "platforms": ["instagram", "facebook"],
    }


@pytest.fixture
def queue_item_payload_single_platform() -> dict:
    """
    Build a queue item payload targeting a single platform.

    Returns:
        Dict with product_data and a single-item platforms list.
    """
    return {
        "product_data": {
            "title": "Vintage Leather Backpack",
            "description": "Handcrafted genuine leather backpack with brass hardware.",
            "price": 129.00,
            "image_url": "https://cdn.example.com/backpack.jpg",
        },
        "platforms": ["tiktok"],
    }


# ── Create Queue Item Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_create_queue_item(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """POST /api/v1/queue creates a pending queue item (201)."""
    resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["status"] == "pending"
    assert data["product_data"]["title"] == SAMPLE_PRODUCT_DATA["title"]
    assert data["platforms"] == ["instagram", "facebook"]
    assert data["ai_generated_content"] is None
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_queue_item_empty_platforms(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/queue with empty platforms list still creates an item (201)."""
    resp = await client.post(
        "/api/v1/queue",
        json={
            "product_data": SAMPLE_PRODUCT_DATA,
            "platforms": [],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["platforms"] == []


@pytest.mark.asyncio
async def test_create_queue_item_unauthenticated(
    client: AsyncClient, queue_item_payload: dict
):
    """POST /api/v1/queue without auth token returns 401."""
    resp = await client.post("/api/v1/queue", json=queue_item_payload)
    assert resp.status_code == 401


# ── List Queue Items Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_queue_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/queue returns 200 with empty items for a new user."""
    resp = await client.get("/api/v1/queue", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_queue_with_items(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """GET /api/v1/queue returns items after creating them."""
    # Create two items
    await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    await client.post(
        "/api/v1/queue",
        json={
            "product_data": {"title": "Second Product", "price": 49.99},
            "platforms": ["instagram"],
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/queue", headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_queue_pagination(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """GET /api/v1/queue respects page and per_page parameters."""
    # Create 3 items
    for i in range(3):
        await client.post(
            "/api/v1/queue",
            json={
                "product_data": {"title": f"Product #{i+1}", "price": 10 + i},
                "platforms": ["instagram"],
            },
            headers=auth_headers,
        )

    # Request page 1 with per_page=2
    resp = await client.get(
        "/api/v1/queue?page=1&per_page=2", headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1

    # Request page 2
    resp2 = await client.get(
        "/api/v1/queue?page=2&per_page=2", headers=auth_headers
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["page"] == 2


@pytest.mark.asyncio
async def test_list_queue_filter_by_status(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """GET /api/v1/queue?status=pending returns only pending items."""
    # Create an item (it starts as pending)
    await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )

    resp = await client.get(
        "/api/v1/queue?status=pending", headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 1
    assert all(item["status"] == "pending" for item in data["items"])

    # Filter for approved should return 0
    resp2 = await client.get(
        "/api/v1/queue?status=approved", headers=auth_headers
    )
    assert resp2.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_queue_unauthenticated(client: AsyncClient):
    """GET /api/v1/queue without auth token returns 401."""
    resp = await client.get("/api/v1/queue")
    assert resp.status_code == 401


# ── Get Single Queue Item Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_queue_item(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """GET /api/v1/queue/{id} returns the correct queue item (200)."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/queue/{item_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id
    assert resp.json()["product_data"]["title"] == SAMPLE_PRODUCT_DATA["title"]


@pytest.mark.asyncio
async def test_get_queue_item_not_found(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/queue/{random_id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/queue/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_queue_item_user_isolation(client: AsyncClient):
    """User B cannot access queue items created by user A."""
    # User A creates a queue item
    headers_a = await register_and_login(client)
    create_resp = await client.post(
        "/api/v1/queue",
        json={
            "product_data": {"title": "Private Product", "price": 99},
            "platforms": ["instagram"],
        },
        headers=headers_a,
    )
    item_id = create_resp.json()["id"]

    # User B tries to access it
    headers_b = await register_and_login(client)
    resp = await client.get(f"/api/v1/queue/{item_id}", headers=headers_b)
    assert resp.status_code == 404


# ── Delete Queue Item Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_pending_queue_item(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """DELETE /api/v1/queue/{id} removes a pending queue item (204)."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/queue/{item_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(
        f"/api/v1/queue/{item_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_approved_queue_item_rejected(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """DELETE /api/v1/queue/{id} returns 400 for approved items (cannot delete)."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    # Approve the item first
    await client.post(
        f"/api/v1/queue/{item_id}/approve", headers=auth_headers
    )

    # Try to delete — should fail
    resp = await client.delete(
        f"/api/v1/queue/{item_id}", headers=auth_headers
    )
    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_nonexistent_queue_item(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /api/v1/queue/{random_id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/queue/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


# ── AI Caption Generation Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_caption_for_queue_item(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """POST /api/v1/queue/{id}/generate populates ai_generated_content."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    # AI content should be None initially
    assert create_resp.json()["ai_generated_content"] is None

    # Generate caption
    resp = await client.post(
        f"/api/v1/queue/{item_id}/generate", headers=auth_headers
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["ai_generated_content"] is not None
    assert len(data["ai_generated_content"]) > 0


@pytest.mark.asyncio
async def test_generate_caption_nonexistent_item(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/queue/{random_id}/generate returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/queue/{fake_id}/generate", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_standalone_caption_generation(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/queue/generate-caption returns caption without persisting data."""
    resp = await client.post(
        "/api/v1/queue/generate-caption",
        json={
            "product_data": SAMPLE_PRODUCT_DATA,
            "platform": "instagram",
            "tone": "playful",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "caption" in data
    assert "hashtags" in data
    assert "platform" in data
    assert len(data["caption"]) > 0
    assert isinstance(data["hashtags"], list)


@pytest.mark.asyncio
async def test_standalone_caption_default_platform(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/queue/generate-caption uses default platform/tone if not provided."""
    resp = await client.post(
        "/api/v1/queue/generate-caption",
        json={
            "product_data": {"title": "Simple Product", "price": 25.00},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "instagram"  # default


# ── Approve Workflow Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_pending_item(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """POST /api/v1/queue/{id}/approve changes status from pending to approved."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "pending"

    resp = await client.post(
        f"/api/v1/queue/{item_id}/approve", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_already_approved_rejected(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """POST /api/v1/queue/{id}/approve returns 400 if item is already approved."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    # Approve first time
    await client.post(
        f"/api/v1/queue/{item_id}/approve", headers=auth_headers
    )

    # Approve second time — should fail
    resp = await client.post(
        f"/api/v1/queue/{item_id}/approve", headers=auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_nonexistent_item(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/queue/{random_id}/approve returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/queue/{fake_id}/approve", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Reject Workflow Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_pending_item(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """POST /api/v1/queue/{id}/reject changes status from pending to rejected."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/queue/{item_id}/reject", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_already_rejected(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """POST /api/v1/queue/{id}/reject returns 400 if item is already rejected."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    # Reject first time
    await client.post(
        f"/api/v1/queue/{item_id}/reject", headers=auth_headers
    )

    # Reject second time — should fail
    resp = await client.post(
        f"/api/v1/queue/{item_id}/reject", headers=auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reject_nonexistent_item(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/queue/{random_id}/reject returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/queue/{fake_id}/reject", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_rejected_item_allowed(
    client: AsyncClient, auth_headers: dict, queue_item_payload: dict
):
    """DELETE /api/v1/queue/{id} succeeds for rejected items (204)."""
    create_resp = await client.post(
        "/api/v1/queue", json=queue_item_payload, headers=auth_headers
    )
    item_id = create_resp.json()["id"]

    # Reject the item
    await client.post(
        f"/api/v1/queue/{item_id}/reject", headers=auth_headers
    )

    # Delete should succeed
    resp = await client.delete(
        f"/api/v1/queue/{item_id}", headers=auth_headers
    )
    assert resp.status_code == 204


# ── User Isolation Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_queue_items_user_isolation(client: AsyncClient):
    """Queue items created by user A are not visible to user B in list view."""
    # User A creates queue items
    headers_a = await register_and_login(client)
    await client.post(
        "/api/v1/queue",
        json={
            "product_data": {"title": "User A Product"},
            "platforms": ["instagram"],
        },
        headers=headers_a,
    )

    # User B should see empty list
    headers_b = await register_and_login(client)
    resp = await client.get("/api/v1/queue", headers=headers_b)
    assert resp.json()["total"] == 0
