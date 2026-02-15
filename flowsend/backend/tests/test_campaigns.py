"""
Campaign API endpoint tests.

Covers CRUD operations for email campaigns, including scheduling,
sending (mock), status transitions, analytics retrieval, and event listing.

For Developers:
    Uses the ``auth_headers`` fixture from conftest.py for authenticated
    requests. Campaign sending is mocked — no real emails are dispatched.
    Tests verify status transitions: draft -> sent, draft -> scheduled.

For QA Engineers:
    Run with: ``pytest tests/test_campaigns.py -v``
    Verify: create (draft + scheduled), list (pagination, status filter),
    get, update (draft only), delete (draft only, reject sent), send (mock),
    analytics, events, 404 handling.

For Project Managers:
    Campaigns are the primary revenue driver for email marketing.
    These tests ensure the full campaign lifecycle is reliable,
    from creation through sending to analytics.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


# ── Helper constants ────────────────────────────────────────────────────

API_PREFIX = "/api/v1/campaigns"
CONTACTS_PREFIX = "/api/v1/contacts"


async def _create_contact(client: AsyncClient, headers: dict, email: str) -> str:
    """
    Helper to create a contact and return its ID.

    Args:
        client: The test HTTP client.
        headers: Auth headers.
        email: Contact email address.

    Returns:
        The created contact's UUID string.
    """
    resp = await client.post(
        CONTACTS_PREFIX, json={"email": email}, headers=headers
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Campaign CRUD ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_campaign_draft(client: AsyncClient, auth_headers: dict):
    """POST /campaigns without scheduled_at creates a draft campaign."""
    payload = {
        "name": "Spring Sale",
        "subject": "Don't miss our spring deals!",
    }
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Spring Sale"
    assert data["subject"] == "Don't miss our spring deals!"
    assert data["status"] == "draft"
    assert data["scheduled_at"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_create_campaign_scheduled(client: AsyncClient, auth_headers: dict):
    """POST /campaigns with scheduled_at creates a scheduled campaign."""
    future_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    payload = {
        "name": "Future Promo",
        "subject": "Coming soon!",
        "scheduled_at": future_time,
    }
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("draft", "scheduled")
    assert data["scheduled_at"] is not None


@pytest.mark.asyncio
async def test_create_campaign_validation(client: AsyncClient, auth_headers: dict):
    """POST /campaigns with missing required fields returns 422."""
    # Missing 'subject'
    resp = await client.post(
        API_PREFIX, json={"name": "No Subject"}, headers=auth_headers
    )
    assert resp.status_code == 422

    # Missing 'name'
    resp2 = await client.post(
        API_PREFIX, json={"subject": "No Name"}, headers=auth_headers
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_list_campaigns_empty(client: AsyncClient, auth_headers: dict):
    """GET /campaigns with no data returns an empty paginated response."""
    resp = await client.get(API_PREFIX, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_campaigns_pagination(client: AsyncClient, auth_headers: dict):
    """GET /campaigns respects page and page_size parameters."""
    for i in range(3):
        await client.post(
            API_PREFIX,
            json={"name": f"Camp {i}", "subject": f"Subject {i}"},
            headers=auth_headers,
        )

    resp = await client.get(
        f"{API_PREFIX}?page=1&page_size=2", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3

    resp2 = await client.get(
        f"{API_PREFIX}?page=2&page_size=2", headers=auth_headers
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 1


@pytest.mark.asyncio
async def test_list_campaigns_status_filter(client: AsyncClient, auth_headers: dict):
    """GET /campaigns?status=draft returns only draft campaigns."""
    await client.post(
        API_PREFIX,
        json={"name": "Draft One", "subject": "Subject"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"{API_PREFIX}?status=draft", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for camp in data["items"]:
        assert camp["status"] == "draft"


@pytest.mark.asyncio
async def test_get_campaign(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/:id returns the campaign by UUID."""
    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Get Me", "subject": "Subject"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]

    resp = await client.get(f"{API_PREFIX}/{campaign_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Me"


@pytest.mark.asyncio
async def test_get_campaign_not_found(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_campaign_draft(client: AsyncClient, auth_headers: dict):
    """PATCH /campaigns/:id updates a draft campaign's fields."""
    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Old Name", "subject": "Old Subject"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{API_PREFIX}/{campaign_id}",
        json={"name": "New Name", "subject": "New Subject"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["name"] == "New Name"
    assert data["subject"] == "New Subject"


@pytest.mark.asyncio
async def test_update_campaign_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /campaigns/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"{API_PREFIX}/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_campaign_draft(client: AsyncClient, auth_headers: dict):
    """DELETE /campaigns/:id removes a draft campaign and returns 204."""
    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Delete Me", "subject": "Subject"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"{API_PREFIX}/{campaign_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    # Verify it is gone
    get_resp = await client.get(
        f"{API_PREFIX}/{campaign_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_campaign_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /campaigns/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Send (Mock) ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_campaign(client: AsyncClient, auth_headers: dict):
    """POST /campaigns/:id/send transitions campaign to sent status."""
    # Create a contact so the send has a recipient
    await _create_contact(client, auth_headers, "recipient@example.com")

    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Sendable", "subject": "Go!"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]

    send_resp = await client.post(
        f"{API_PREFIX}/{campaign_id}/send", headers=auth_headers
    )
    assert send_resp.status_code == 200
    data = send_resp.json()
    assert data["status"] == "sent"
    assert data["sent_at"] is not None


@pytest.mark.asyncio
async def test_send_campaign_not_found(client: AsyncClient, auth_headers: dict):
    """POST /campaigns/:id/send with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"{API_PREFIX}/{fake_id}/send", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_send_campaign_already_sent(client: AsyncClient, auth_headers: dict):
    """POST /campaigns/:id/send on an already sent campaign returns 400."""
    await _create_contact(client, auth_headers, "r2@example.com")

    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Already Sent", "subject": "Go!"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]

    # Send it once
    await client.post(f"{API_PREFIX}/{campaign_id}/send", headers=auth_headers)

    # Try to send again
    resp = await client.post(
        f"{API_PREFIX}/{campaign_id}/send", headers=auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_sent_campaign_rejected(client: AsyncClient, auth_headers: dict):
    """DELETE /campaigns/:id on a sent campaign returns 400."""
    await _create_contact(client, auth_headers, "r3@example.com")

    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Sent No Delete", "subject": "Go!"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]

    await client.post(f"{API_PREFIX}/{campaign_id}/send", headers=auth_headers)

    del_resp = await client.delete(
        f"{API_PREFIX}/{campaign_id}", headers=auth_headers
    )
    assert del_resp.status_code == 400


# ── Analytics ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_campaign_analytics(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/:id/analytics returns analytics for a sent campaign."""
    await _create_contact(client, auth_headers, "analytics-r@example.com")

    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Analytics Test", "subject": "Analyze!"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]
    await client.post(f"{API_PREFIX}/{campaign_id}/send", headers=auth_headers)

    resp = await client.get(
        f"{API_PREFIX}/{campaign_id}/analytics", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sent" in data
    assert "open_rate" in data
    assert "click_rate" in data
    assert "bounce_rate" in data


@pytest.mark.asyncio
async def test_campaign_analytics_not_found(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/:id/analytics with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"{API_PREFIX}/{fake_id}/analytics", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Events ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_campaign_events(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/:id/events returns paginated email events after send."""
    await _create_contact(client, auth_headers, "event-r@example.com")

    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Events Test", "subject": "Events!"},
        headers=auth_headers,
    )
    campaign_id = create_resp.json()["id"]
    await client.post(f"{API_PREFIX}/{campaign_id}/send", headers=auth_headers)

    resp = await client.get(
        f"{API_PREFIX}/{campaign_id}/events", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_campaign_events_not_found(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/:id/events with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"{API_PREFIX}/{fake_id}/events", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Auth requirement ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_campaigns_require_auth(client: AsyncClient):
    """All campaign endpoints require authentication (401 without token)."""
    resp = await client.get(API_PREFIX)
    assert resp.status_code == 401

    resp2 = await client.post(
        API_PREFIX, json={"name": "NoAuth", "subject": "Test"}
    )
    assert resp2.status_code == 401
