"""
Billing endpoint tests.

For QA Engineers:
    Tests cover plan listing, checkout session creation,
    billing overview, and subscription management. All tests
    run in Stripe mock mode.
"""

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


@pytest.mark.asyncio
async def test_list_plans(client: AsyncClient):
    """GET /billing/plans returns all plan tiers."""
    resp = await client.get("/api/v1/billing/plans")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) == 3
    tiers = {p["tier"] for p in plans}
    assert tiers == {"free", "pro", "enterprise"}


@pytest.mark.asyncio
async def test_list_plans_has_pricing(client: AsyncClient):
    """GET /billing/plans includes pricing details."""
    resp = await client.get("/api/v1/billing/plans")
    plans = resp.json()
    free_plan = next(p for p in plans if p["tier"] == "free")
    assert free_plan["price_monthly_cents"] == 0
    assert free_plan["trial_days"] == 0


@pytest.mark.asyncio
async def test_checkout_pro_plan(client: AsyncClient):
    """POST /billing/checkout creates a checkout session for pro plan."""
    headers = await register_and_login(client)
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "checkout_url" in data
    assert "session_id" in data


@pytest.mark.asyncio
async def test_checkout_free_plan_fails(client: AsyncClient):
    """POST /billing/checkout for free plan returns 400."""
    headers = await register_and_login(client)
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "free"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_checkout_duplicate_subscription_fails(client: AsyncClient):
    """POST /billing/checkout with existing subscription returns 400."""
    headers = await register_and_login(client)
    # First checkout succeeds (mock mode creates subscription directly)
    await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro"},
        headers=headers,
    )
    # Second checkout fails
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "enterprise"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_billing_overview(client: AsyncClient):
    """GET /billing/overview returns plan, subscription, and usage."""
    headers = await register_and_login(client)
    resp = await client.get("/api/v1/billing/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_plan"] == "free"
    assert data["plan_name"] == "Free"
    assert "usage" in data
    assert "metrics" in data["usage"]


@pytest.mark.asyncio
async def test_billing_overview_after_subscribe(client: AsyncClient):
    """GET /billing/overview reflects upgraded plan after checkout."""
    headers = await register_and_login(client)
    # Subscribe to pro (mock mode)
    await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro"},
        headers=headers,
    )
    resp = await client.get("/api/v1/billing/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_plan"] == "pro"


@pytest.mark.asyncio
async def test_get_current_subscription_none(client: AsyncClient):
    """GET /billing/current returns null when no subscription."""
    headers = await register_and_login(client)
    resp = await client.get("/api/v1/billing/current", headers=headers)
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_get_current_subscription_after_subscribe(client: AsyncClient):
    """GET /billing/current returns subscription after checkout."""
    headers = await register_and_login(client)
    await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro"},
        headers=headers,
    )
    resp = await client.get("/api/v1/billing/current", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["plan"] == "pro"
    assert data["status"] == "active"
