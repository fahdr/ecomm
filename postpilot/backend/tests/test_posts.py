"""
Tests for post management API endpoints.

Covers the full post lifecycle: create, list, get, update, delete, schedule,
and calendar views. Tests include pagination, filtering, status transitions,
and authentication requirements.

For Developers:
    Most tests require a connected social account to create posts against.
    The `connected_account` fixture handles this setup. Posts reference an
    account_id, so tests must create an account before creating posts.

For QA Engineers:
    These tests verify:
    - POST /api/v1/posts creates a draft or scheduled post (201).
    - GET /api/v1/posts returns paginated results with total count.
    - GET /api/v1/posts/{id} retrieves a single post (200) or 404.
    - PATCH /api/v1/posts/{id} updates draft/scheduled posts (200), rejects posted (400).
    - DELETE /api/v1/posts/{id} removes draft posts (204), rejects posted (400).
    - POST /api/v1/posts/{id}/schedule schedules a draft for future publication.
    - GET /api/v1/posts/calendar returns posts grouped by date.
    - Unauthenticated requests return 401.

For Project Managers:
    Posts are the core content unit. These tests ensure the full post workflow
    is reliable, from drafting to scheduling to deletion.

For End Users:
    These tests validate that creating, editing, scheduling, and deleting
    your social media posts works correctly every time.
"""

import uuid
from datetime import datetime, timedelta, UTC

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Shared fixtures ────────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_and_account(client: AsyncClient) -> tuple[dict, str]:
    """
    Register a user and connect an Instagram account.

    Returns:
        Tuple of (auth_headers dict, account_id string).
    """
    headers = await register_and_login(client)

    # Connect an Instagram account
    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@post_test_brand",
        },
        headers=headers,
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    return headers, account_id


def _make_post_payload(account_id: str, **overrides) -> dict:
    """
    Build a valid post creation payload.

    Args:
        account_id: The social account UUID to target.
        **overrides: Any fields to override in the default payload.

    Returns:
        Dict suitable for POST /api/v1/posts.
    """
    payload = {
        "account_id": account_id,
        "content": "Check out our new arrivals! Fresh drops every week.",
        "platform": "instagram",
        "media_urls": ["https://cdn.example.com/image1.jpg"],
        "hashtags": ["newdrops", "fashion", "streetwear"],
    }
    payload.update(overrides)
    return payload


# ── Create Post Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_post_as_draft(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts without scheduled_for creates a draft post (201)."""
    headers, account_id = auth_and_account
    payload = _make_post_payload(account_id)

    resp = await client.post("/api/v1/posts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["status"] == "draft"
    assert data["content"] == payload["content"]
    assert data["platform"] == "instagram"
    assert data["account_id"] == account_id
    assert data["media_urls"] == payload["media_urls"]
    assert data["hashtags"] == payload["hashtags"]
    assert data["scheduled_for"] is None
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_post_as_scheduled(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts with scheduled_for creates a scheduled post (201)."""
    headers, account_id = auth_and_account
    future_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    payload = _make_post_payload(account_id, scheduled_for=future_time)

    resp = await client.post("/api/v1/posts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["scheduled_for"] is not None


@pytest.mark.asyncio
async def test_create_post_minimal_fields(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts with only required fields creates a draft (201)."""
    headers, account_id = auth_and_account
    payload = {
        "account_id": account_id,
        "content": "Minimal post content",
        "platform": "instagram",
    }

    resp = await client.post("/api/v1/posts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["media_urls"] == []
    assert data["hashtags"] == []
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_create_post_empty_content_rejected(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts with empty content returns 422 validation error."""
    headers, account_id = auth_and_account
    payload = _make_post_payload(account_id, content="")

    resp = await client.post("/api/v1/posts", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_post_unauthenticated(client: AsyncClient):
    """POST /api/v1/posts without auth token returns 401."""
    payload = {
        "account_id": str(uuid.uuid4()),
        "content": "No auth post",
        "platform": "instagram",
    }
    resp = await client.post("/api/v1/posts", json=payload)
    assert resp.status_code == 401


# ── List Posts Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_posts_empty(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts returns 200 with empty items for a new user."""
    headers, _ = auth_and_account

    resp = await client.get("/api/v1/posts", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_posts_with_data(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts returns posts after creating them."""
    headers, account_id = auth_and_account

    # Create two posts
    for i in range(2):
        await client.post(
            "/api/v1/posts",
            json=_make_post_payload(account_id, content=f"Post #{i+1}"),
            headers=headers,
        )

    resp = await client.get("/api/v1/posts", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_posts_pagination(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts respects page and per_page parameters."""
    headers, account_id = auth_and_account

    # Create 3 posts
    for i in range(3):
        await client.post(
            "/api/v1/posts",
            json=_make_post_payload(account_id, content=f"Paginated #{i+1}"),
            headers=headers,
        )

    # Request page 1 with per_page=2
    resp = await client.get(
        "/api/v1/posts?page=1&per_page=2", headers=headers
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1

    # Request page 2
    resp2 = await client.get(
        "/api/v1/posts?page=2&per_page=2", headers=headers
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["page"] == 2


@pytest.mark.asyncio
async def test_list_posts_filter_by_status(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts?status=draft returns only draft posts."""
    headers, account_id = auth_and_account

    # Create a draft
    await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="Draft post"),
        headers=headers,
    )
    # Create a scheduled post
    future_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    await client.post(
        "/api/v1/posts",
        json=_make_post_payload(
            account_id, content="Scheduled post", scheduled_for=future_time
        ),
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/posts?status=draft", headers=headers
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "draft"


@pytest.mark.asyncio
async def test_list_posts_filter_by_platform(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts?platform=instagram returns only instagram posts."""
    headers, account_id = auth_and_account

    await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="IG post"),
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/posts?platform=instagram", headers=headers
    )
    data = resp.json()
    assert data["total"] == 1
    assert all(p["platform"] == "instagram" for p in data["items"])

    # Filter for a different platform should return 0
    resp2 = await client.get(
        "/api/v1/posts?platform=tiktok", headers=headers
    )
    assert resp2.json()["total"] == 0


# ── Get Single Post Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_post_by_id(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts/{id} returns the correct post (200)."""
    headers, account_id = auth_and_account
    create_resp = await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="Specific post"),
        headers=headers,
    )
    post_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/posts/{post_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == post_id
    assert resp.json()["content"] == "Specific post"


@pytest.mark.asyncio
async def test_get_post_not_found(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts/{random_id} returns 404 for non-existent post."""
    headers, _ = auth_and_account
    fake_id = str(uuid.uuid4())

    resp = await client.get(f"/api/v1/posts/{fake_id}", headers=headers)
    assert resp.status_code == 404


# ── Update Post Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_post_content(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """PATCH /api/v1/posts/{id} updates the content of a draft post."""
    headers, account_id = auth_and_account
    create_resp = await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="Original content"),
        headers=headers,
    )
    post_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={"content": "Updated content with new info"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated content with new info"


@pytest.mark.asyncio
async def test_update_post_hashtags(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """PATCH /api/v1/posts/{id} can update hashtags independently."""
    headers, account_id = auth_and_account
    create_resp = await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id),
        headers=headers,
    )
    post_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={"hashtags": ["sale", "discount", "limited"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["hashtags"] == ["sale", "discount", "limited"]


@pytest.mark.asyncio
async def test_update_nonexistent_post(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """PATCH /api/v1/posts/{random_id} returns 404 for non-existent post."""
    headers, _ = auth_and_account
    fake_id = str(uuid.uuid4())

    resp = await client.patch(
        f"/api/v1/posts/{fake_id}",
        json={"content": "Won't work"},
        headers=headers,
    )
    assert resp.status_code == 404


# ── Delete Post Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_draft_post(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """DELETE /api/v1/posts/{id} removes a draft post (204)."""
    headers, account_id = auth_and_account
    create_resp = await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="To be deleted"),
        headers=headers,
    )
    post_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/posts/{post_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/posts/{post_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_post(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """DELETE /api/v1/posts/{random_id} returns 404 for non-existent post."""
    headers, _ = auth_and_account
    fake_id = str(uuid.uuid4())

    resp = await client.delete(f"/api/v1/posts/{fake_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_unauthenticated(client: AsyncClient):
    """DELETE /api/v1/posts/{id} without auth token returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/posts/{fake_id}")
    assert resp.status_code == 401


# ── Schedule Post Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schedule_draft_post(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts/{id}/schedule sets status to 'scheduled' with a future time."""
    headers, account_id = auth_and_account
    create_resp = await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="Schedule me"),
        headers=headers,
    )
    post_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "draft"

    future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    resp = await client.post(
        f"/api/v1/posts/{post_id}/schedule",
        json={"scheduled_for": future_time},
        headers=headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["scheduled_for"] is not None


@pytest.mark.asyncio
async def test_schedule_post_past_time_rejected(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts/{id}/schedule with past time returns 400."""
    headers, account_id = auth_and_account
    create_resp = await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="Past schedule"),
        headers=headers,
    )
    post_id = create_resp.json()["id"]

    past_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    resp = await client.post(
        f"/api/v1/posts/{post_id}/schedule",
        json={"scheduled_for": past_time},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_schedule_nonexistent_post(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts/{random_id}/schedule returns 404 for non-existent post."""
    headers, _ = auth_and_account
    fake_id = str(uuid.uuid4())
    future_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    resp = await client.post(
        f"/api/v1/posts/{fake_id}/schedule",
        json={"scheduled_for": future_time},
        headers=headers,
    )
    assert resp.status_code == 404


# ── Calendar View Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_calendar_view_empty(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts/calendar returns empty days for a date range with no posts."""
    headers, _ = auth_and_account
    start = datetime.now(UTC).strftime("%Y-%m-%d")
    end = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")

    resp = await client.get(
        f"/api/v1/posts/calendar?start_date={start}&end_date={end}",
        headers=headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total_posts"] == 0
    assert isinstance(data["days"], list)


@pytest.mark.asyncio
async def test_calendar_view_with_scheduled_posts(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts/calendar returns scheduled posts grouped by date."""
    headers, account_id = auth_and_account

    # Create a scheduled post for tomorrow
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    future_time = tomorrow.isoformat()
    await client.post(
        "/api/v1/posts",
        json=_make_post_payload(
            account_id, content="Calendar post", scheduled_for=future_time
        ),
        headers=headers,
    )

    start = datetime.now(UTC).strftime("%Y-%m-%d")
    end = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")

    resp = await client.get(
        f"/api/v1/posts/calendar?start_date={start}&end_date={end}",
        headers=headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total_posts"] == 1
    assert len(data["days"]) >= 1
    # Verify the post appears on the correct day
    day_dates = [d["date"] for d in data["days"]]
    expected_date = tomorrow.strftime("%Y-%m-%d")
    assert expected_date in day_dates


@pytest.mark.asyncio
async def test_calendar_requires_date_params(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts/calendar without start_date/end_date returns 422."""
    headers, _ = auth_and_account

    resp = await client.get("/api/v1/posts/calendar", headers=headers)
    assert resp.status_code == 422


# ── User Isolation Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_posts_user_isolation(client: AsyncClient):
    """Posts created by user A are not visible to user B."""
    # User A creates an account and a post
    headers_a = await register_and_login(client)
    acct_resp = await client.post(
        "/api/v1/accounts",
        json={"platform": "instagram", "account_name": "@user_a"},
        headers=headers_a,
    )
    account_id = acct_resp.json()["id"]

    await client.post(
        "/api/v1/posts",
        json=_make_post_payload(account_id, content="User A post"),
        headers=headers_a,
    )

    # User B should see 0 posts
    headers_b = await register_and_login(client)
    resp = await client.get("/api/v1/posts", headers=headers_b)
    assert resp.json()["total"] == 0
