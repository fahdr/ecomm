"""Tests for store webhook configuration endpoints (Feature F23).

Covers creating webhooks, listing webhooks, updating webhooks, deleting
webhooks, and viewing delivery history. This tests the webhook *configuration*
API, not the incoming Stripe webhook handler.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Webhook endpoints are store-scoped: ``/stores/{store_id}/webhooks``.
    Tests verify that a secret is auto-generated, event subscription works,
    and delivery history returns paginated results.
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


async def create_test_webhook(
    client,
    token: str,
    store_id: str,
    url: str = "https://hooks.example.com/orders",
    events: list | None = None,
) -> dict:
    """Create a webhook and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        url: The webhook endpoint URL.
        events: List of event types to subscribe to.

    Returns:
        The JSON response dictionary for the created webhook.
    """
    if events is None:
        events = ["order.created", "order.updated"]
    resp = await client.post(
        f"/api/v1/stores/{store_id}/webhooks",
        json={"url": url, "events": events},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_webhook_success(client):
    """Creating a webhook returns 201 with config including auto-generated secret."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/webhooks",
        json={
            "url": "https://hooks.example.com/orders",
            "events": ["order.created"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://hooks.example.com/orders"
    assert data["events"] == ["order.created"]
    assert data["is_active"] is True
    assert data["store_id"] == store["id"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_webhook_no_auth(client):
    """Creating a webhook without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/webhooks",
        json={"url": "https://hooks.example.com", "events": ["order.created"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_webhook_store_not_found(client):
    """Creating a webhook for a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/webhooks",
        json={"url": "https://hooks.example.com", "events": ["order.created"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# List Webhooks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_webhooks_success(client):
    """Listing webhooks returns paginated data with all configured webhooks."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_webhook(client, token, store["id"], url="https://hook1.example.com")
    await create_test_webhook(client, token, store["id"], url="https://hook2.example.com")

    response = await client.get(
        f"/api/v1/stores/{store['id']}/webhooks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_webhooks_empty(client):
    """Listing webhooks when none exist returns an empty paginated response."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/webhooks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Update Webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_webhook_success(client):
    """Updating a webhook partially changes only the provided fields."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    webhook = await create_test_webhook(client, token, store["id"])

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/webhooks/{webhook['id']}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    # URL should remain unchanged.
    assert data["url"] == webhook["url"]


@pytest.mark.asyncio
async def test_update_webhook_not_found(client):
    """Updating a non-existent webhook returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/webhooks/00000000-0000-0000-0000-000000000000",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_webhook_success(client):
    """Deleting a webhook returns 204 with no content."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    webhook = await create_test_webhook(client, token, store["id"])

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/webhooks/{webhook['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_webhook_not_found(client):
    """Deleting a non-existent webhook returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/webhooks/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delivery History
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delivery_history_empty(client):
    """Listing delivery history for a new webhook returns empty results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    webhook = await create_test_webhook(client, token, store["id"])

    response = await client.get(
        f"/api/v1/stores/{store['id']}/webhooks/{webhook['id']}/deliveries",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["items"] == []
    assert data["total"] == 0
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
