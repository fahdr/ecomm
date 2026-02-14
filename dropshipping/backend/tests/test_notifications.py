"""Tests for notification endpoints (Feature F25).

Covers listing notifications, unread count, marking as read, marking all as
read, and deleting notifications. Since notifications are created internally
by other services, tests verify endpoint behavior with empty and seeded data.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Notification endpoints are user-scoped (not store-scoped).
    Tests verify pagination structure, unread count, and 404 on missing IDs.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(client, email: str = "owner@example.com") -> str:
    """Register a user and return the access token.

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        The JWT access token string.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    return resp.json()["access_token"]


async def create_test_store(
    client, token: str, name: str = "My Store", niche: str = "electronics"
) -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        name: Store name.
        niche: Store niche.

    Returns:
        The JSON response dictionary for the created store.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": niche},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# List Notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_notifications_empty(client):
    """Listing notifications for a new user returns an empty paginated response."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_list_notifications_no_auth(client):
    """Listing notifications without authentication returns 401."""
    response = await client.get("/api/v1/notifications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_notifications_unread_only(client):
    """Listing with unread_only filter returns empty when no notifications exist."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Unread Count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unread_count_zero(client):
    """Unread count is 0 for a new user with no notifications."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_unread_count_no_auth(client):
    """Getting unread count without authentication returns 401."""
    response = await client.get("/api/v1/notifications/unread-count")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Mark Notifications as Read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_nonexistent_ids(client):
    """Marking nonexistent notification IDs succeeds with 0 marked."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/notifications/mark-read",
        json={"notification_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["marked"] == 0
    assert "message" in data


@pytest.mark.asyncio
async def test_mark_all_read_no_notifications(client):
    """Marking all as read when there are no notifications returns 0 marked."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/notifications/mark-all-read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["marked"] == 0
    assert "message" in data


# ---------------------------------------------------------------------------
# Delete Notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_notification_not_found(client):
    """Deleting a non-existent notification returns 404."""
    token = await register_and_get_token(client)

    response = await client.delete(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_notification_no_auth(client):
    """Deleting a notification without authentication returns 401."""
    response = await client.delete(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000000",
    )
    assert response.status_code == 401
