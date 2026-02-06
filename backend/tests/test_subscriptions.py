"""Tests for subscription, billing, and plan enforcement endpoints.

Covers plan listing, checkout session creation (mock mode), billing overview,
portal session, plan enforcement (store and product limits), and webhook
event handling for subscription lifecycle.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    All subscription tests run in mock mode (no Stripe keys), which creates
    subscription records directly in the database.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# Direct DB access for webhook tests that need stripe_customer_id
# (not exposed via the public API).
_test_engine = create_async_engine(
    settings.database_url, echo=False, poolclass=NullPool
)
_TestSession = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


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


def auth_header(token: str) -> dict:
    """Build an Authorization header dict.

    Args:
        token: JWT access token.

    Returns:
        A dict with the Authorization header.
    """
    return {"Authorization": f"Bearer {token}"}


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
        json={"name": name, "niche": niche, "description": "A test store"},
        headers=auth_header(token),
    )
    return resp.json()


async def subscribe_user(client, token: str, plan: str = "starter") -> dict:
    """Subscribe a user to a plan (mock mode creates subscription directly).

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        plan: Plan tier to subscribe to.

    Returns:
        The checkout session response dict.
    """
    resp = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": plan},
        headers=auth_header(token),
    )
    return resp.json()


async def get_user_stripe_customer_id(user_id: str) -> str:
    """Look up a user's stripe_customer_id directly from the database.

    Needed for webhook tests because the public API doesn't expose this field.

    Args:
        user_id: The user's UUID string.

    Returns:
        The Stripe customer ID string.
    """
    async with _TestSession() as session:
        result = await session.execute(
            text("SELECT stripe_customer_id FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        row = result.fetchone()
        return row[0] if row else ""


# ---------------------------------------------------------------------------
# Plan Listing (Public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_plans_returns_all_tiers(client):
    """GET /plans returns all 4 plan tiers without requiring authentication."""
    response = await client.get("/api/v1/subscriptions/plans")

    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 4

    tiers = [p["tier"] for p in plans]
    assert "free" in tiers
    assert "starter" in tiers
    assert "growth" in tiers
    assert "pro" in tiers


@pytest.mark.asyncio
async def test_list_plans_contains_correct_free_tier(client):
    """Free tier has 0 price, 1 store, 25 products, 50 orders, 0 trial days."""
    response = await client.get("/api/v1/subscriptions/plans")
    plans = {p["tier"]: p for p in response.json()}

    free = plans["free"]
    assert free["name"] == "Free"
    assert free["price_monthly_cents"] == 0
    assert free["max_stores"] == 1
    assert free["max_products_per_store"] == 25
    assert free["max_orders_per_month"] == 50
    assert free["trial_days"] == 0


@pytest.mark.asyncio
async def test_list_plans_contains_correct_pro_tier(client):
    """Pro tier has unlimited limits (-1) and 14 trial days."""
    response = await client.get("/api/v1/subscriptions/plans")
    plans = {p["tier"]: p for p in response.json()}

    pro = plans["pro"]
    assert pro["name"] == "Pro"
    assert pro["price_monthly_cents"] == 19900
    assert pro["max_stores"] == -1
    assert pro["max_products_per_store"] == -1
    assert pro["max_orders_per_month"] == -1
    assert pro["trial_days"] == 14


# ---------------------------------------------------------------------------
# Checkout Session Creation (Mock Mode)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_starter_plan_success(client):
    """Mock mode checkout for starter plan returns 201 with checkout URL."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "starter"},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert "checkout_url" in data
    assert "session_id" in data


@pytest.mark.asyncio
async def test_checkout_creates_subscription_in_mock_mode(client):
    """Mock mode checkout creates a subscription and updates user plan."""
    token = await register_and_get_token(client)

    await subscribe_user(client, token, "starter")

    # Verify user plan updated
    me_resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_resp.json()["plan"] == "starter"

    # Verify subscription exists
    sub_resp = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    assert sub_resp.status_code == 200
    sub = sub_resp.json()
    assert sub is not None
    assert sub["plan"] == "starter"
    assert sub["status"] == "active"


@pytest.mark.asyncio
async def test_checkout_growth_plan_success(client):
    """Mock mode checkout for growth plan works correctly."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "growth"},
        headers=auth_header(token),
    )
    assert response.status_code == 201

    me_resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_resp.json()["plan"] == "growth"


@pytest.mark.asyncio
async def test_checkout_free_plan_rejected(client):
    """Subscribing to the free plan returns 400."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "free"},
        headers=auth_header(token),
    )
    assert response.status_code == 400
    assert "free" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_checkout_already_subscribed_rejected(client):
    """A user with an active subscription cannot create a second one."""
    token = await register_and_get_token(client)

    resp1 = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "starter"},
        headers=auth_header(token),
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "growth"},
        headers=auth_header(token),
    )
    assert resp2.status_code == 400
    assert "already" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_checkout_requires_auth(client):
    """POST /checkout without authentication returns 401."""
    response = await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "starter"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Current Subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_current_subscription_none_for_free_user(client):
    """A free-tier user has no subscription (returns null)."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_current_subscription_returns_active_sub(client):
    """After subscribing, GET /current returns the active subscription."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "growth")

    response = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    assert response.status_code == 200
    sub = response.json()
    assert sub["plan"] == "growth"
    assert sub["status"] == "active"
    assert sub["cancel_at_period_end"] is False


# ---------------------------------------------------------------------------
# Billing Overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_billing_overview_free_user(client):
    """Free-tier user billing overview shows free plan, no subscription, zero usage."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/subscriptions/billing", headers=auth_header(token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_plan"] == "free"
    assert data["plan_name"] == "Free"
    assert data["subscription"] is None

    usage = data["usage"]
    assert usage["stores_used"] == 0
    assert usage["stores_limit"] == 1
    assert usage["products_used"] == 0
    assert usage["products_limit_per_store"] == 25
    assert usage["orders_this_month"] == 0
    assert usage["orders_limit"] == 50


@pytest.mark.asyncio
async def test_billing_overview_with_subscription(client):
    """Subscribed user billing overview shows upgraded plan and subscription."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    response = await client.get(
        "/api/v1/subscriptions/billing", headers=auth_header(token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_plan"] == "starter"
    assert data["plan_name"] == "Starter"
    assert data["subscription"] is not None
    assert data["subscription"]["plan"] == "starter"

    usage = data["usage"]
    assert usage["stores_limit"] == 3
    assert usage["products_limit_per_store"] == 100
    assert usage["orders_limit"] == 500


@pytest.mark.asyncio
async def test_billing_overview_counts_stores(client):
    """Billing overview correctly counts the user's stores in usage."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    await create_test_store(client, token, name="Store 1")
    await create_test_store(client, token, name="Store 2")

    response = await client.get(
        "/api/v1/subscriptions/billing", headers=auth_header(token)
    )
    usage = response.json()["usage"]
    assert usage["stores_used"] == 2


@pytest.mark.asyncio
async def test_billing_overview_requires_auth(client):
    """GET /billing without authentication returns 401."""
    response = await client.get("/api/v1/subscriptions/billing")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Portal Session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portal_session_requires_stripe_customer(client):
    """POST /portal returns 400 if the user has no Stripe customer ID."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/subscriptions/portal", headers=auth_header(token)
    )
    assert response.status_code == 400
    assert "subscribe" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_portal_session_success(client):
    """POST /portal returns a portal URL after the user has subscribed."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    response = await client.post(
        "/api/v1/subscriptions/portal", headers=auth_header(token)
    )
    assert response.status_code == 200
    assert "portal_url" in response.json()


# ---------------------------------------------------------------------------
# Plan Enforcement — Store Limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_free_plan_store_limit(client):
    """Free plan allows 1 store; creating a second returns 403."""
    token = await register_and_get_token(client)

    resp1 = await client.post(
        "/api/v1/stores",
        json={"name": "First Store", "niche": "tech"},
        headers=auth_header(token),
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/api/v1/stores",
        json={"name": "Second Store", "niche": "fashion"},
        headers=auth_header(token),
    )
    assert resp2.status_code == 403
    assert "limit" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upgraded_plan_allows_more_stores(client):
    """Starter plan allows 3 stores; user can create beyond the free limit."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    for i in range(3):
        resp = await client.post(
            "/api/v1/stores",
            json={"name": f"Store {i + 1}", "niche": "tech"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201

    resp4 = await client.post(
        "/api/v1/stores",
        json={"name": "Store 4", "niche": "tech"},
        headers=auth_header(token),
    )
    assert resp4.status_code == 403


@pytest.mark.asyncio
async def test_deleted_stores_dont_count_toward_limit(client):
    """Soft-deleted stores are not counted against the plan limit."""
    token = await register_and_get_token(client)

    store = await create_test_store(client, token, name="To Delete")
    await client.delete(
        f"/api/v1/stores/{store['id']}", headers=auth_header(token)
    )

    resp = await client.post(
        "/api/v1/stores",
        json={"name": "New Store", "niche": "tech"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Plan Enforcement — Product Limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_free_plan_product_limit(client):
    """Free plan allows 25 products per store; product 26 returns 403."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    for i in range(25):
        resp = await client.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"title": f"Product {i + 1}", "price": 9.99},
            headers=auth_header(token),
        )
        assert resp.status_code == 201, f"Product {i + 1} should succeed"

    resp26 = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={"title": "Product 26", "price": 9.99},
        headers=auth_header(token),
    )
    assert resp26.status_code == 403
    assert "limit" in resp26.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upgraded_plan_allows_more_products(client):
    """Starter plan allows 100 products; user can create beyond the free limit."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")
    store = await create_test_store(client, token)

    for i in range(26):
        resp = await client.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"title": f"Product {i + 1}", "price": 9.99},
            headers=auth_header(token),
        )
        assert resp.status_code == 201, f"Product {i + 1} should succeed on starter"


@pytest.mark.asyncio
async def test_archived_products_dont_count_toward_limit(client):
    """Archived (soft-deleted) products are not counted against the limit."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    products = []
    for i in range(25):
        resp = await client.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"title": f"Product {i + 1}", "price": 9.99},
            headers=auth_header(token),
        )
        products.append(resp.json())

    await client.delete(
        f"/api/v1/stores/{store['id']}/products/{products[0]['id']}",
        headers=auth_header(token),
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={"title": "Replacement Product", "price": 9.99},
        headers=auth_header(token),
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Webhook Handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_reverts_to_free(client):
    """Webhook for customer.subscription.deleted reverts user to free plan."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    me_resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    user_data = me_resp.json()
    assert user_data["plan"] == "starter"

    sub_resp = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    sub_data = sub_resp.json()

    # Look up stripe_customer_id from DB (not exposed via API)
    customer_id = await get_user_stripe_customer_id(user_data["id"])

    webhook_payload = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": sub_data["stripe_subscription_id"],
                "customer": customer_id,
                "status": "canceled",
                "items": {"data": []},
                "metadata": {"plan": "starter"},
                "current_period_start": 1700000000,
                "current_period_end": 1702592000,
                "cancel_at_period_end": False,
                "trial_start": None,
                "trial_end": None,
            }
        },
    }

    response = await client.post(
        "/api/v1/webhooks/stripe",
        json=webhook_payload,
        headers={"stripe-signature": "mock_sig"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify user reverted to free
    me_resp2 = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_resp2.json()["plan"] == "free"


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed(client):
    """Webhook for invoice.payment_failed sets subscription to past_due."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    sub_resp = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    sub_data = sub_resp.json()

    webhook_payload = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": sub_data["stripe_subscription_id"],
            }
        },
    }

    response = await client.post(
        "/api/v1/webhooks/stripe",
        json=webhook_payload,
        headers={"stripe-signature": "mock_sig"},
    )
    assert response.status_code == 200

    sub_resp2 = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    assert sub_resp2.json()["status"] == "past_due"


@pytest.mark.asyncio
async def test_webhook_subscription_updated(client):
    """Webhook for customer.subscription.updated syncs plan changes."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    me_resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    user_data = me_resp.json()

    sub_resp = await client.get(
        "/api/v1/subscriptions/current", headers=auth_header(token)
    )
    sub_data = sub_resp.json()

    customer_id = await get_user_stripe_customer_id(user_data["id"])

    # Simulate subscription.updated webhook upgrading to growth
    webhook_payload = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": sub_data["stripe_subscription_id"],
                "customer": customer_id,
                "status": "active",
                "items": {"data": []},
                "metadata": {"plan": "growth"},
                "current_period_start": 1700000000,
                "current_period_end": 1702592000,
                "cancel_at_period_end": False,
                "trial_start": None,
                "trial_end": None,
            }
        },
    }

    response = await client.post(
        "/api/v1/webhooks/stripe",
        json=webhook_payload,
        headers={"stripe-signature": "mock_sig"},
    )
    assert response.status_code == 200

    me_resp2 = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_resp2.json()["plan"] == "growth"


# ---------------------------------------------------------------------------
# User Plan Field in Auth Response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_response_includes_plan_field(client):
    """GET /auth/me returns the user's plan field (defaults to free)."""
    token = await register_and_get_token(client)

    response = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["plan"] == "free"


@pytest.mark.asyncio
async def test_user_plan_updates_after_subscription(client):
    """User plan field updates to starter after subscribing."""
    token = await register_and_get_token(client)
    await subscribe_user(client, token, "starter")

    response = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.json()["plan"] == "starter"
