"""
Flow API endpoint tests.

Covers CRUD operations for automated email flows, including lifecycle
transitions (draft -> active -> paused), step validation, and execution listing.

For Developers:
    Uses the ``auth_headers`` fixture from conftest.py for authenticated
    requests. Flow lifecycle: draft -> active (requires steps) -> paused.
    Active flows cannot be updated (must pause first).

For QA Engineers:
    Run with: ``pytest tests/test_flows.py -v``
    Verify: create, list (pagination, status filter), get, update (draft/paused),
    update active rejected, delete, activate (with steps), activate (no steps
    rejected), pause, executions listing, 404 handling.

For Project Managers:
    Flows are the core automation feature. They reduce manual work and
    improve engagement through timely automated email sequences. These
    tests cover the full lifecycle.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helper constants ────────────────────────────────────────────────────

API_PREFIX = "/api/v1/flows"

VALID_FLOW = {
    "name": "Welcome Series",
    "description": "Onboarding flow for new subscribers",
    "trigger_type": "signup",
    "trigger_config": {"source": "website"},
    "steps": [
        {"type": "email", "template": "welcome", "delay_hours": 0},
        {"type": "email", "template": "follow-up", "delay_hours": 24},
    ],
}


# ── Flow CRUD ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_flow(client: AsyncClient, auth_headers: dict):
    """POST /flows creates a flow in draft status and returns 201."""
    resp = await client.post(API_PREFIX, json=VALID_FLOW, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Welcome Series"
    assert data["description"] == "Onboarding flow for new subscribers"
    assert data["trigger_type"] == "signup"
    assert data["status"] == "draft"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_flow_minimal(client: AsyncClient, auth_headers: dict):
    """POST /flows with only required fields (name, trigger_type) succeeds."""
    payload = {
        "name": "Simple Flow",
        "trigger_type": "purchase",
    }
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Simple Flow"
    assert data["trigger_type"] == "purchase"
    assert data["status"] == "draft"
    assert data["description"] is None


@pytest.mark.asyncio
async def test_create_flow_all_trigger_types(client: AsyncClient, auth_headers: dict):
    """POST /flows succeeds with each valid trigger_type."""
    valid_triggers = ["signup", "purchase", "abandoned_cart", "custom", "scheduled"]
    for trigger in valid_triggers:
        resp = await client.post(
            API_PREFIX,
            json={"name": f"Flow {trigger}", "trigger_type": trigger},
            headers=auth_headers,
        )
        assert resp.status_code == 201, f"Failed for trigger_type={trigger}"
        assert resp.json()["trigger_type"] == trigger


@pytest.mark.asyncio
async def test_create_flow_missing_name(client: AsyncClient, auth_headers: dict):
    """POST /flows without name returns 422."""
    resp = await client.post(
        API_PREFIX,
        json={"trigger_type": "signup"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_flow_missing_trigger_type(client: AsyncClient, auth_headers: dict):
    """POST /flows without trigger_type returns 422."""
    resp = await client.post(
        API_PREFIX,
        json={"name": "No Trigger"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_flows_empty(client: AsyncClient, auth_headers: dict):
    """GET /flows with no data returns an empty paginated response."""
    resp = await client.get(API_PREFIX, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_flows_pagination(client: AsyncClient, auth_headers: dict):
    """GET /flows respects page and page_size parameters."""
    for i in range(3):
        await client.post(
            API_PREFIX,
            json={"name": f"Flow {i}", "trigger_type": "signup"},
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
async def test_list_flows_status_filter(client: AsyncClient, auth_headers: dict):
    """GET /flows?status=draft returns only draft flows."""
    await client.post(
        API_PREFIX,
        json={"name": "Draft Flow", "trigger_type": "signup"},
        headers=auth_headers,
    )

    resp = await client.get(f"{API_PREFIX}?status=draft", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for flow in data["items"]:
        assert flow["status"] == "draft"


@pytest.mark.asyncio
async def test_get_flow(client: AsyncClient, auth_headers: dict):
    """GET /flows/:id returns the flow by UUID."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    resp = await client.get(f"{API_PREFIX}/{flow_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Welcome Series"


@pytest.mark.asyncio
async def test_get_flow_not_found(client: AsyncClient, auth_headers: dict):
    """GET /flows/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_flow_draft(client: AsyncClient, auth_headers: dict):
    """PATCH /flows/:id updates a draft flow's fields."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{API_PREFIX}/{flow_id}",
        json={
            "name": "Updated Welcome Series",
            "description": "New description",
            "steps": [
                {"type": "email", "template": "new-welcome", "delay_hours": 0},
            ],
        },
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["name"] == "Updated Welcome Series"
    assert data["description"] == "New description"


@pytest.mark.asyncio
async def test_update_flow_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /flows/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"{API_PREFIX}/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_flow(client: AsyncClient, auth_headers: dict):
    """DELETE /flows/:id removes the flow and returns 204."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"{API_PREFIX}/{flow_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    # Verify it is gone
    get_resp = await client.get(
        f"{API_PREFIX}/{flow_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_flow_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /flows/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Flow Lifecycle (Activate / Pause) ───────────────────────────────────


@pytest.mark.asyncio
async def test_activate_flow_with_steps(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/activate on a flow with steps transitions to active."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    activate_resp = await client.post(
        f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_activate_flow_without_steps(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/activate on a flow with no steps returns 400."""
    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Empty Flow", "trigger_type": "signup", "steps": []},
        headers=auth_headers,
    )
    flow_id = create_resp.json()["id"]

    activate_resp = await client.post(
        f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers
    )
    assert activate_resp.status_code == 400


@pytest.mark.asyncio
async def test_activate_flow_not_found(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/activate with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"{API_PREFIX}/{fake_id}/activate", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pause_active_flow(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/pause on an active flow transitions to paused."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    # Activate first
    await client.post(f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers)

    # Then pause
    pause_resp = await client.post(
        f"{API_PREFIX}/{flow_id}/pause", headers=auth_headers
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_pause_draft_flow_rejected(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/pause on a draft flow returns 400."""
    create_resp = await client.post(
        API_PREFIX,
        json={"name": "Draft Pause", "trigger_type": "signup", "steps": []},
        headers=auth_headers,
    )
    flow_id = create_resp.json()["id"]

    pause_resp = await client.post(
        f"{API_PREFIX}/{flow_id}/pause", headers=auth_headers
    )
    assert pause_resp.status_code == 400


@pytest.mark.asyncio
async def test_pause_flow_not_found(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/pause with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"{API_PREFIX}/{fake_id}/pause", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_active_flow_rejected(client: AsyncClient, auth_headers: dict):
    """PATCH /flows/:id on an active flow returns 400 (must pause first)."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    await client.post(f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers)

    patch_resp = await client.patch(
        f"{API_PREFIX}/{flow_id}",
        json={"name": "Cannot Update Active"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 400


@pytest.mark.asyncio
async def test_update_paused_flow(client: AsyncClient, auth_headers: dict):
    """PATCH /flows/:id on a paused flow succeeds."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    # Activate then pause
    await client.post(f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers)
    await client.post(f"{API_PREFIX}/{flow_id}/pause", headers=auth_headers)

    # Now update should work
    patch_resp = await client.patch(
        f"{API_PREFIX}/{flow_id}",
        json={"name": "Paused and Updated"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Paused and Updated"


@pytest.mark.asyncio
async def test_reactivate_paused_flow(client: AsyncClient, auth_headers: dict):
    """POST /flows/:id/activate on a paused flow transitions back to active."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    # Activate, pause, then reactivate
    await client.post(f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers)
    await client.post(f"{API_PREFIX}/{flow_id}/pause", headers=auth_headers)

    activate_resp = await client.post(
        f"{API_PREFIX}/{flow_id}/activate", headers=auth_headers
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"


# ── Flow Executions ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_flow_executions_empty(client: AsyncClient, auth_headers: dict):
    """GET /flows/:id/executions returns empty list when no executions exist."""
    create_resp = await client.post(
        API_PREFIX, json=VALID_FLOW, headers=auth_headers
    )
    flow_id = create_resp.json()["id"]

    resp = await client.get(
        f"{API_PREFIX}/{flow_id}/executions", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_flow_executions_not_found(
    client: AsyncClient, auth_headers: dict
):
    """GET /flows/:id/executions with unknown flow UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"{API_PREFIX}/{fake_id}/executions", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Auth requirement ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flows_require_auth(client: AsyncClient):
    """All flow endpoints require authentication (401 without token)."""
    resp = await client.get(API_PREFIX)
    assert resp.status_code == 401

    resp2 = await client.post(API_PREFIX, json=VALID_FLOW)
    assert resp2.status_code == 401
