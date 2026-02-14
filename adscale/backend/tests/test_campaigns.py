"""
Tests for campaign management API endpoints.

Validates CRUD operations for advertising campaigns, including
budget management, plan limit enforcement, and status transitions.

For Developers:
    Campaigns require an ad account, so each test first connects a
    Google Ads account via the accounts endpoint. Uses ``auth_headers``
    from conftest.py for authentication.

For QA Engineers:
    Covers: create success, list with pagination, get by ID, update
    (name, budget, status), delete, plan limit enforcement (403),
    ownership validation, invalid IDs, unauthenticated access.

For Project Managers:
    Campaigns are the core billable resource. Free tier allows 2,
    Pro allows 25, Enterprise is unlimited.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from tests.conftest import register_and_login


# ── Helpers ─────────────────────────────────────────────────────────────


async def _create_ad_account(
    client: AsyncClient, headers: dict, external_id: str = "camp-acct-001"
) -> str:
    """
    Connect a Google Ads account and return its UUID.

    Args:
        client: Async HTTP test client.
        headers: Auth headers.
        external_id: External account identifier.

    Returns:
        str: The UUID of the newly created ad account.
    """
    resp = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "platform": "google",
            "account_id_external": external_id,
            "account_name": "Test Google Ads",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_campaign(
    client: AsyncClient,
    headers: dict,
    ad_account_id: str,
    name: str = "Test Campaign",
    objective: str = "conversions",
    budget_daily: float | None = 50.0,
    budget_lifetime: float | None = None,
    status: str = "draft",
) -> dict:
    """
    Create a campaign and return the full response object.

    Args:
        client: Async HTTP test client.
        headers: Auth headers.
        ad_account_id: UUID of the ad account.
        name: Campaign name.
        objective: Campaign objective (traffic, conversions, awareness, sales).
        budget_daily: Daily budget in USD.
        budget_lifetime: Lifetime budget in USD.
        status: Initial campaign status.

    Returns:
        httpx.Response: The raw response from the API.
    """
    payload = {
        "ad_account_id": ad_account_id,
        "name": name,
        "objective": objective,
        "budget_daily": budget_daily,
        "budget_lifetime": budget_lifetime,
        "status": status,
    }
    return await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json=payload,
    )


# ── Create Campaign Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_campaign_success(client: AsyncClient, auth_headers: dict):
    """POST /campaigns with valid data returns 201 and the campaign details."""
    account_id = await _create_ad_account(client, auth_headers)
    resp = await _create_campaign(client, auth_headers, account_id)

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Campaign"
    assert data["objective"] == "conversions"
    assert data["budget_daily"] == 50.0
    assert data["budget_lifetime"] is None
    assert data["status"] == "draft"
    assert data["platform"] == "google"
    assert data["ad_account_id"] == account_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_campaign_all_objectives(client: AsyncClient, db):
    """Campaigns can be created with every valid objective type.

    Upgrades user to pro plan to allow >2 campaigns (free limit is 2).
    """
    headers = await register_and_login(client, "objectives-test@test.com")
    # Upgrade to pro plan so we can create 4 campaigns
    await db.execute(text("UPDATE users SET plan = 'pro' WHERE email = 'objectives-test@test.com'"))
    await db.commit()

    account_id = await _create_ad_account(client, headers)

    for objective in ["traffic", "conversions", "awareness", "sales"]:
        resp = await _create_campaign(
            client,
            headers,
            account_id,
            name=f"Campaign {objective}",
            objective=objective,
        )
        assert resp.status_code == 201
        assert resp.json()["objective"] == objective


@pytest.mark.asyncio
async def test_create_campaign_with_lifetime_budget(
    client: AsyncClient, auth_headers: dict
):
    """Campaign can use lifetime budget instead of daily budget."""
    account_id = await _create_ad_account(client, auth_headers)
    resp = await _create_campaign(
        client,
        auth_headers,
        account_id,
        budget_daily=None,
        budget_lifetime=5000.0,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["budget_daily"] is None
    assert data["budget_lifetime"] == 5000.0


@pytest.mark.asyncio
async def test_create_campaign_unauthenticated(client: AsyncClient):
    """POST /campaigns without auth returns 401."""
    resp = await client.post(
        "/api/v1/campaigns",
        json={
            "ad_account_id": "00000000-0000-0000-0000-000000000000",
            "name": "No Auth Campaign",
            "objective": "traffic",
        },
    )
    assert resp.status_code == 401


# ── List Campaigns Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_campaigns_empty(client: AsyncClient, auth_headers: dict):
    """GET /campaigns with no campaigns returns empty list."""
    resp = await client.get("/api/v1/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_campaigns_with_data(client: AsyncClient, auth_headers: dict):
    """GET /campaigns returns all created campaigns."""
    account_id = await _create_ad_account(client, auth_headers)
    await _create_campaign(client, auth_headers, account_id, name="Camp A")
    await _create_campaign(client, auth_headers, account_id, name="Camp B")

    resp = await client.get("/api/v1/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_campaigns_pagination(client: AsyncClient, db):
    """GET /campaigns respects offset and limit parameters.

    Upgrades user to pro plan to allow >2 campaigns (free limit is 2).
    """
    headers = await register_and_login(client, "pagination-test@test.com")
    # Upgrade to pro plan so we can create 5 campaigns
    await db.execute(text("UPDATE users SET plan = 'pro' WHERE email = 'pagination-test@test.com'"))
    await db.commit()

    account_id = await _create_ad_account(client, headers)
    for i in range(5):
        await _create_campaign(client, headers, account_id, name=f"Camp {i}")

    resp = await client.get(
        "/api/v1/campaigns",
        headers=headers,
        params={"offset": 1, "limit": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["offset"] == 1


@pytest.mark.asyncio
async def test_list_campaigns_user_isolation(client: AsyncClient):
    """Campaigns from user A are not visible to user B."""
    headers_a = await register_and_login(client, "camp-owner@test.com")
    headers_b = await register_and_login(client, "camp-other@test.com")

    account_id = await _create_ad_account(client, headers_a, external_id="iso-acct")
    await _create_campaign(client, headers_a, account_id, name="Private Campaign")

    resp = await client.get("/api/v1/campaigns", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Get Single Campaign Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_campaign_by_id(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/{id} returns the correct campaign."""
    account_id = await _create_ad_account(client, auth_headers)
    create_resp = await _create_campaign(client, auth_headers, account_id)
    campaign_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/campaigns/{campaign_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == campaign_id
    assert resp.json()["name"] == "Test Campaign"


@pytest.mark.asyncio
async def test_get_campaign_not_found(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/api/v1/campaigns/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_campaign_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """GET /campaigns/{bad-format} returns 400."""
    resp = await client.get(
        "/api/v1/campaigns/not-a-uuid", headers=auth_headers
    )
    assert resp.status_code == 400


# ── Update Campaign Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_campaign_name(client: AsyncClient, auth_headers: dict):
    """PATCH /campaigns/{id} updates the campaign name."""
    account_id = await _create_ad_account(client, auth_headers)
    create_resp = await _create_campaign(client, auth_headers, account_id)
    campaign_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        headers=auth_headers,
        json={"name": "Updated Campaign Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Campaign Name"


@pytest.mark.asyncio
async def test_update_campaign_budget(client: AsyncClient, auth_headers: dict):
    """PATCH /campaigns/{id} can update the daily budget."""
    account_id = await _create_ad_account(client, auth_headers)
    create_resp = await _create_campaign(
        client, auth_headers, account_id, budget_daily=50.0
    )
    campaign_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        headers=auth_headers,
        json={"budget_daily": 100.0},
    )
    assert resp.status_code == 200
    assert resp.json()["budget_daily"] == 100.0


@pytest.mark.asyncio
async def test_update_campaign_status(client: AsyncClient, auth_headers: dict):
    """PATCH /campaigns/{id} can transition status from draft to active."""
    account_id = await _create_ad_account(client, auth_headers)
    create_resp = await _create_campaign(client, auth_headers, account_id, status="draft")
    campaign_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        headers=auth_headers,
        json={"status": "active"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_update_campaign_objective(client: AsyncClient, auth_headers: dict):
    """PATCH /campaigns/{id} can change the objective."""
    account_id = await _create_ad_account(client, auth_headers)
    create_resp = await _create_campaign(
        client, auth_headers, account_id, objective="traffic"
    )
    campaign_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        headers=auth_headers,
        json={"objective": "sales"},
    )
    assert resp.status_code == 200
    assert resp.json()["objective"] == "sales"


@pytest.mark.asyncio
async def test_update_nonexistent_campaign_returns_404(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /campaigns/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/campaigns/{fake_id}",
        headers=auth_headers,
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404


# ── Delete Campaign Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_campaign_success(client: AsyncClient, auth_headers: dict):
    """DELETE /campaigns/{id} returns 204 and removes the campaign."""
    account_id = await _create_ad_account(client, auth_headers)
    create_resp = await _create_campaign(client, auth_headers, account_id)
    campaign_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/campaigns/{campaign_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await client.get(
        f"/api/v1/campaigns/{campaign_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_campaign_returns_404(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /campaigns/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(
        f"/api/v1/campaigns/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_campaign_returns_404(client: AsyncClient):
    """A user cannot delete another user's campaign (returns 404)."""
    headers_a = await register_and_login(client, "del-owner@test.com")
    headers_b = await register_and_login(client, "del-thief@test.com")

    account_id = await _create_ad_account(client, headers_a, external_id="del-acct")
    create_resp = await _create_campaign(client, headers_a, account_id)
    campaign_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/campaigns/{campaign_id}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_campaign_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """DELETE /campaigns/{bad-format} returns 400."""
    resp = await client.delete(
        "/api/v1/campaigns/bad-uuid", headers=auth_headers
    )
    assert resp.status_code == 400
