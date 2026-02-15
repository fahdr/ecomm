"""
Tests for optimization rule management API endpoints.

Validates CRUD operations for automated optimization rules, including
the execute-now endpoint for manual rule triggering.

For Developers:
    Rules are user-scoped (no ad account or campaign dependency for
    creation). The execute-now endpoint evaluates the rule against
    the user's active campaigns.

For QA Engineers:
    Covers: create success, list with pagination, get by ID, update
    fields (name, threshold, is_active, rule_type), delete, execute-now,
    ownership isolation, invalid IDs, unauthenticated access.

For Project Managers:
    Optimization rules are a premium automation feature that lets users
    automate campaign management based on performance thresholds.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ─────────────────────────────────────────────────────────────


async def _create_rule(
    client: AsyncClient,
    headers: dict,
    name: str = "Pause Low ROAS",
    rule_type: str = "pause_low_roas",
    conditions: dict | None = None,
    threshold: float = 1.5,
    is_active: bool = True,
) -> object:
    """
    Create an optimization rule and return the raw response.

    Args:
        client: Async HTTP test client.
        headers: Auth headers.
        name: Human-readable rule name.
        rule_type: One of pause_low_roas, scale_high_roas, adjust_bid, increase_budget.
        conditions: JSON dict with evaluation conditions.
        threshold: Numeric threshold for the rule condition.
        is_active: Whether the rule starts enabled.

    Returns:
        httpx.Response: The raw response from the API.
    """
    if conditions is None:
        conditions = {"metric": "roas", "operator": "less_than"}

    return await client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": name,
            "rule_type": rule_type,
            "conditions": conditions,
            "threshold": threshold,
            "is_active": is_active,
        },
    )


# ── Create Rule Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_rule_success(client: AsyncClient, auth_headers: dict):
    """POST /rules with valid data returns 201 and the rule details."""
    resp = await _create_rule(client, auth_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Pause Low ROAS"
    assert data["rule_type"] == "pause_low_roas"
    assert data["threshold"] == 1.5
    assert data["is_active"] is True
    assert data["conditions"] == {"metric": "roas", "operator": "less_than"}
    assert data["executions_count"] == 0
    assert data["last_executed"] is None
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_rule_all_types(client: AsyncClient, auth_headers: dict):
    """Rules can be created with every valid rule type."""
    rule_types = ["pause_low_roas", "scale_high_roas", "adjust_bid", "increase_budget"]

    for rt in rule_types:
        resp = await _create_rule(
            client, auth_headers, name=f"Rule {rt}", rule_type=rt
        )
        assert resp.status_code == 201
        assert resp.json()["rule_type"] == rt


@pytest.mark.asyncio
async def test_create_rule_inactive(client: AsyncClient, auth_headers: dict):
    """A rule can be created in inactive state."""
    resp = await _create_rule(
        client, auth_headers, name="Disabled Rule", is_active=False
    )
    assert resp.status_code == 201
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_create_rule_custom_conditions(client: AsyncClient, auth_headers: dict):
    """Rules accept arbitrary JSON conditions."""
    conditions = {
        "metric": "cpa",
        "operator": "greater_than",
        "lookback_days": 7,
    }
    resp = await _create_rule(
        client,
        auth_headers,
        name="High CPA Alert",
        rule_type="adjust_bid",
        conditions=conditions,
        threshold=25.0,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["conditions"]["lookback_days"] == 7
    assert data["threshold"] == 25.0


@pytest.mark.asyncio
async def test_create_rule_unauthenticated(client: AsyncClient):
    """POST /rules without auth returns 401."""
    resp = await client.post(
        "/api/v1/rules",
        json={
            "name": "No Auth Rule",
            "rule_type": "pause_low_roas",
            "conditions": {},
            "threshold": 1.0,
        },
    )
    assert resp.status_code == 401


# ── List Rules Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_rules_empty(client: AsyncClient, auth_headers: dict):
    """GET /rules with no rules returns empty list."""
    resp = await client.get("/api/v1/rules", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_rules_with_data(client: AsyncClient, auth_headers: dict):
    """GET /rules returns all created rules."""
    await _create_rule(client, auth_headers, name="Rule A")
    await _create_rule(client, auth_headers, name="Rule B", rule_type="scale_high_roas")

    resp = await client.get("/api/v1/rules", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_rules_pagination(client: AsyncClient, auth_headers: dict):
    """GET /rules respects offset and limit parameters."""
    for i in range(5):
        await _create_rule(client, auth_headers, name=f"Rule {i}")

    resp = await client.get(
        "/api/v1/rules",
        headers=auth_headers,
        params={"offset": 2, "limit": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["offset"] == 2


@pytest.mark.asyncio
async def test_list_rules_user_isolation(client: AsyncClient):
    """Rules from user A are not visible to user B."""
    headers_a = await register_and_login(client, "rule-owner@test.com")
    headers_b = await register_and_login(client, "rule-other@test.com")

    await _create_rule(client, headers_a, name="A's Private Rule")

    resp = await client.get("/api/v1/rules", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Get Single Rule Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_rule_by_id(client: AsyncClient, auth_headers: dict):
    """GET /rules/{id} returns the correct rule."""
    create_resp = await _create_rule(client, auth_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/rules/{rule_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == rule_id
    assert resp.json()["name"] == "Pause Low ROAS"


@pytest.mark.asyncio
async def test_get_rule_not_found(client: AsyncClient, auth_headers: dict):
    """GET /rules/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/api/v1/rules/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_rule_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """GET /rules/{bad-format} returns 400."""
    resp = await client.get(
        "/api/v1/rules/not-a-uuid", headers=auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_other_users_rule_returns_404(client: AsyncClient):
    """A user cannot view another user's rule (returns 404)."""
    headers_a = await register_and_login(client, "rule-view-a@test.com")
    headers_b = await register_and_login(client, "rule-view-b@test.com")

    create_resp = await _create_rule(client, headers_a, name="Private Rule")
    rule_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/rules/{rule_id}", headers=headers_b
    )
    assert resp.status_code == 404


# ── Update Rule Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_rule_name(client: AsyncClient, auth_headers: dict):
    """PATCH /rules/{id} updates the rule name."""
    create_resp = await _create_rule(client, auth_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers,
        json={"name": "Updated Rule Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Rule Name"


@pytest.mark.asyncio
async def test_update_rule_threshold(client: AsyncClient, auth_headers: dict):
    """PATCH /rules/{id} updates the threshold value."""
    create_resp = await _create_rule(client, auth_headers, threshold=1.5)
    rule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers,
        json={"threshold": 3.0},
    )
    assert resp.status_code == 200
    assert resp.json()["threshold"] == 3.0


@pytest.mark.asyncio
async def test_update_rule_deactivate(client: AsyncClient, auth_headers: dict):
    """PATCH /rules/{id} can deactivate a rule."""
    create_resp = await _create_rule(client, auth_headers, is_active=True)
    rule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_rule_type(client: AsyncClient, auth_headers: dict):
    """PATCH /rules/{id} can change the rule type."""
    create_resp = await _create_rule(
        client, auth_headers, rule_type="pause_low_roas"
    )
    rule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers,
        json={"rule_type": "increase_budget"},
    )
    assert resp.status_code == 200
    assert resp.json()["rule_type"] == "increase_budget"


@pytest.mark.asyncio
async def test_update_rule_conditions(client: AsyncClient, auth_headers: dict):
    """PATCH /rules/{id} can update conditions JSON."""
    create_resp = await _create_rule(client, auth_headers)
    rule_id = create_resp.json()["id"]

    new_conditions = {"metric": "ctr", "operator": "less_than", "lookback_days": 14}
    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers,
        json={"conditions": new_conditions},
    )
    assert resp.status_code == 200
    assert resp.json()["conditions"]["metric"] == "ctr"
    assert resp.json()["conditions"]["lookback_days"] == 14


@pytest.mark.asyncio
async def test_update_nonexistent_rule_returns_404(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /rules/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/rules/{fake_id}",
        headers=auth_headers,
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404


# ── Delete Rule Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_rule_success(client: AsyncClient, auth_headers: dict):
    """DELETE /rules/{id} returns 204 and removes the rule."""
    create_resp = await _create_rule(client, auth_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/rules/{rule_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await client.get(
        f"/api/v1/rules/{rule_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_rule_returns_404(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /rules/{nonexistent} returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(
        f"/api/v1/rules/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_rule_returns_404(client: AsyncClient):
    """A user cannot delete another user's rule (returns 404)."""
    headers_a = await register_and_login(client, "rule-del-a@test.com")
    headers_b = await register_and_login(client, "rule-del-b@test.com")

    create_resp = await _create_rule(client, headers_a, name="A's Rule")
    rule_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/rules/{rule_id}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_rule_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """DELETE /rules/{bad-format} returns 400."""
    resp = await client.delete(
        "/api/v1/rules/not-a-uuid", headers=auth_headers
    )
    assert resp.status_code == 400


# ── Execute Rule Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_rule_no_campaigns(client: AsyncClient, auth_headers: dict):
    """POST /rules/{id}/execute with no campaigns returns 0 affected."""
    create_resp = await _create_rule(client, auth_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/rules/{rule_id}/execute", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rule_id"] == rule_id
    assert data["campaigns_affected"] == 0
    assert isinstance(data["actions_taken"], list)


@pytest.mark.asyncio
async def test_execute_nonexistent_rule_returns_404(
    client: AsyncClient, auth_headers: dict
):
    """POST /rules/{nonexistent}/execute returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/rules/{fake_id}/execute", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_execute_rule_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """POST /rules/{bad-format}/execute returns 400."""
    resp = await client.post(
        "/api/v1/rules/not-a-uuid/execute", headers=auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_execute_rule_unauthenticated(client: AsyncClient):
    """POST /rules/{id}/execute without auth returns 401."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/v1/rules/{fake_id}/execute")
    assert resp.status_code == 401
