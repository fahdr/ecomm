"""
Tests for ad creative management API endpoints.

Validates CRUD operations for ad creatives and AI-powered copy generation.
Creatives belong to ad groups, which belong to campaigns, which belong to
ad accounts — ownership is validated through this full chain.

For Developers:
    Each test sets up the full chain: account -> campaign -> ad group -> creative.
    The ``_setup_chain`` helper abstracts this so individual tests stay concise.

For QA Engineers:
    Covers: create success, list with filter, get by ID, update fields,
    delete, ownership validation through the chain, AI copy generation,
    invalid IDs, unauthenticated access.

For Project Managers:
    Creatives are the actual ad content (headline, description, image, CTA).
    AI copy generation is a premium feature powered by Claude.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ─────────────────────────────────────────────────────────────


async def _setup_chain(
    client: AsyncClient, headers: dict, external_id: str = "creative-acct"
) -> dict:
    """
    Create the full account -> campaign -> ad group chain and return all IDs.

    Args:
        client: Async HTTP test client.
        headers: Auth headers.
        external_id: External account identifier (unique per test).

    Returns:
        dict: Keys ``account_id``, ``campaign_id``, ``ad_group_id``.
    """
    # Connect ad account
    acct_resp = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "platform": "google",
            "account_id_external": external_id,
            "account_name": "Creative Test Acct",
        },
    )
    assert acct_resp.status_code == 201
    account_id = acct_resp.json()["id"]

    # Create campaign
    camp_resp = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "ad_account_id": account_id,
            "name": "Creative Test Campaign",
            "objective": "conversions",
            "budget_daily": 100.0,
        },
    )
    assert camp_resp.status_code == 201
    campaign_id = camp_resp.json()["id"]

    # Create ad group
    ag_resp = await client.post(
        "/api/v1/ad-groups",
        headers=headers,
        json={
            "campaign_id": campaign_id,
            "name": "Creative Test Ad Group",
            "targeting": {"age": "18-35", "interests": ["tech"]},
            "bid_strategy": "auto_cpc",
        },
    )
    assert ag_resp.status_code == 201
    ad_group_id = ag_resp.json()["id"]

    return {
        "account_id": account_id,
        "campaign_id": campaign_id,
        "ad_group_id": ad_group_id,
    }


async def _create_creative(
    client: AsyncClient,
    headers: dict,
    ad_group_id: str,
    headline: str = "Amazing Product",
    description: str = "The best product you will ever use.",
    destination_url: str = "https://example.com/product",
    call_to_action: str = "Shop Now",
) -> object:
    """
    Create an ad creative and return the raw response.

    Args:
        client: Async HTTP test client.
        headers: Auth headers.
        ad_group_id: UUID of the parent ad group.
        headline: Ad headline text.
        description: Ad description text.
        destination_url: Landing page URL.
        call_to_action: CTA button text.

    Returns:
        httpx.Response: The raw response from the API.
    """
    return await client.post(
        "/api/v1/creatives",
        headers=headers,
        json={
            "ad_group_id": ad_group_id,
            "headline": headline,
            "description": description,
            "destination_url": destination_url,
            "call_to_action": call_to_action,
        },
    )


# ── Create Creative Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_creative_success(client: AsyncClient, auth_headers: dict):
    """POST /creatives with valid data returns 201 and the creative details."""
    chain = await _setup_chain(client, auth_headers)
    resp = await _create_creative(client, auth_headers, chain["ad_group_id"])

    assert resp.status_code == 201
    data = resp.json()
    assert data["headline"] == "Amazing Product"
    assert data["description"] == "The best product you will ever use."
    assert data["destination_url"] == "https://example.com/product"
    assert data["call_to_action"] == "Shop Now"
    assert data["status"] == "active"
    assert data["ad_group_id"] == chain["ad_group_id"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_creative_custom_cta(client: AsyncClient, auth_headers: dict):
    """Creative can be created with a custom call-to-action."""
    chain = await _setup_chain(client, auth_headers, external_id="cta-acct")
    resp = await _create_creative(
        client,
        auth_headers,
        chain["ad_group_id"],
        call_to_action="Learn More",
    )
    assert resp.status_code == 201
    assert resp.json()["call_to_action"] == "Learn More"


@pytest.mark.asyncio
async def test_create_creative_invalid_ad_group(
    client: AsyncClient, auth_headers: dict
):
    """POST /creatives with a nonexistent ad group returns 400."""
    fake_ag_id = "00000000-0000-0000-0000-000000000000"
    resp = await _create_creative(client, auth_headers, fake_ag_id)
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_creative_unauthenticated(client: AsyncClient):
    """POST /creatives without auth returns 401."""
    resp = await client.post(
        "/api/v1/creatives",
        json={
            "ad_group_id": "00000000-0000-0000-0000-000000000000",
            "headline": "No Auth",
            "description": "Should fail",
            "destination_url": "https://example.com",
        },
    )
    assert resp.status_code == 401


# ── List Creatives Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_creatives_empty(client: AsyncClient, auth_headers: dict):
    """GET /creatives with no creatives returns empty list."""
    resp = await client.get("/api/v1/creatives", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_creatives_with_data(client: AsyncClient, auth_headers: dict):
    """GET /creatives returns all creatives belonging to the user."""
    chain = await _setup_chain(client, auth_headers, external_id="list-acct")
    await _create_creative(
        client, auth_headers, chain["ad_group_id"], headline="Ad A"
    )
    await _create_creative(
        client, auth_headers, chain["ad_group_id"], headline="Ad B"
    )

    resp = await client.get("/api/v1/creatives", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_creatives_filter_by_ad_group(
    client: AsyncClient, auth_headers: dict
):
    """GET /creatives?ad_group_id= filters to a specific ad group."""
    chain = await _setup_chain(client, auth_headers, external_id="filter-acct")

    # Create second ad group in the same campaign
    ag2_resp = await client.post(
        "/api/v1/ad-groups",
        headers=auth_headers,
        json={
            "campaign_id": chain["campaign_id"],
            "name": "Second Ad Group",
            "targeting": {},
        },
    )
    assert ag2_resp.status_code == 201
    ag2_id = ag2_resp.json()["id"]

    # Create creatives in different ad groups
    await _create_creative(
        client, auth_headers, chain["ad_group_id"], headline="Group 1 Ad"
    )
    await _create_creative(
        client, auth_headers, ag2_id, headline="Group 2 Ad"
    )

    # Filter by first ad group
    resp = await client.get(
        "/api/v1/creatives",
        headers=auth_headers,
        params={"ad_group_id": chain["ad_group_id"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["headline"] == "Group 1 Ad"


@pytest.mark.asyncio
async def test_list_creatives_user_isolation(client: AsyncClient):
    """Creatives from user A are not visible to user B."""
    headers_a = await register_and_login(client, "creative-owner@test.com")
    headers_b = await register_and_login(client, "creative-other@test.com")

    chain = await _setup_chain(client, headers_a, external_id="iso-creative-acct")
    await _create_creative(client, headers_a, chain["ad_group_id"])

    resp = await client.get("/api/v1/creatives", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Get Single Creative Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_creative_by_id(client: AsyncClient, auth_headers: dict):
    """GET /creatives/{id} returns the correct creative."""
    chain = await _setup_chain(client, auth_headers, external_id="get-acct")
    create_resp = await _create_creative(client, auth_headers, chain["ad_group_id"])
    creative_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/creatives/{creative_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == creative_id


@pytest.mark.asyncio
async def test_get_creative_not_found(client: AsyncClient, auth_headers: dict):
    """GET /creatives/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/api/v1/creatives/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_creative_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """GET /creatives/{bad-format} returns 400."""
    resp = await client.get(
        "/api/v1/creatives/not-a-uuid", headers=auth_headers
    )
    assert resp.status_code == 400


# ── Update Creative Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_creative_headline(client: AsyncClient, auth_headers: dict):
    """PATCH /creatives/{id} updates the headline."""
    chain = await _setup_chain(client, auth_headers, external_id="upd-acct")
    create_resp = await _create_creative(client, auth_headers, chain["ad_group_id"])
    creative_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/creatives/{creative_id}",
        headers=auth_headers,
        json={"headline": "Updated Headline"},
    )
    assert resp.status_code == 200
    assert resp.json()["headline"] == "Updated Headline"


@pytest.mark.asyncio
async def test_update_creative_status(client: AsyncClient, auth_headers: dict):
    """PATCH /creatives/{id} can change status to paused."""
    chain = await _setup_chain(client, auth_headers, external_id="upd-status-acct")
    create_resp = await _create_creative(client, auth_headers, chain["ad_group_id"])
    creative_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/creatives/{creative_id}",
        headers=auth_headers,
        json={"status": "paused"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_update_creative_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /creatives/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/creatives/{fake_id}",
        headers=auth_headers,
        json={"headline": "Ghost"},
    )
    assert resp.status_code == 404


# ── Delete Creative Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_creative_success(client: AsyncClient, auth_headers: dict):
    """DELETE /creatives/{id} returns 204 and removes the creative."""
    chain = await _setup_chain(client, auth_headers, external_id="del-acct")
    create_resp = await _create_creative(client, auth_headers, chain["ad_group_id"])
    creative_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/creatives/{creative_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await client.get(
        f"/api/v1/creatives/{creative_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_creative_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /creatives/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(
        f"/api/v1/creatives/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_creative_returns_404(client: AsyncClient):
    """A user cannot delete another user's creative (returns 404)."""
    headers_a = await register_and_login(client, "cr-owner@test.com")
    headers_b = await register_and_login(client, "cr-thief@test.com")

    chain = await _setup_chain(client, headers_a, external_id="del-other-acct")
    create_resp = await _create_creative(client, headers_a, chain["ad_group_id"])
    creative_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/creatives/{creative_id}", headers=headers_b
    )
    assert resp.status_code == 404


# ── AI Copy Generation Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_copy_success(client: AsyncClient, auth_headers: dict):
    """POST /creatives/generate-copy returns AI-generated headline, description, CTA."""
    resp = await client.post(
        "/api/v1/creatives/generate-copy",
        headers=auth_headers,
        json={
            "product_name": "Smart Watch Pro",
            "product_description": "A premium smartwatch with health tracking.",
            "target_audience": "Fitness enthusiasts",
            "tone": "energetic",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "headline" in data
    assert "description" in data
    assert "call_to_action" in data
    # Verify non-empty strings
    assert len(data["headline"]) > 0
    assert len(data["description"]) > 0
    assert len(data["call_to_action"]) > 0


@pytest.mark.asyncio
async def test_generate_copy_minimal_fields(client: AsyncClient, auth_headers: dict):
    """POST /creatives/generate-copy works with only required fields."""
    resp = await client.post(
        "/api/v1/creatives/generate-copy",
        headers=auth_headers,
        json={
            "product_name": "Widget",
            "product_description": "A useful widget for everyday tasks.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "headline" in data
    assert "description" in data
    assert "call_to_action" in data


@pytest.mark.asyncio
async def test_generate_copy_unauthenticated(client: AsyncClient):
    """POST /creatives/generate-copy without auth returns 401."""
    resp = await client.post(
        "/api/v1/creatives/generate-copy",
        json={
            "product_name": "No Auth",
            "product_description": "Should fail",
        },
    )
    assert resp.status_code == 401
