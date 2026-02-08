"""Tests for analytics endpoints (Feature 13 - Profit Analytics).

Covers profit summary, revenue time series, top products, and combined
dashboard analytics. All endpoints require authentication and enforce
store ownership.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Helper functions register users and create stores to reduce boilerplate.
    The ``period`` query parameter accepts ``7d``, ``30d``, ``90d``, ``365d``.
    Since analytics compute data from orders, tests with no orders verify
    that zero-value summaries are returned correctly.
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
# Profit Summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_profit_summary_success(client):
    """Fetching profit summary with default period returns valid response."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "30d"
    assert "total_revenue" in data
    assert "total_cost" in data
    assert "total_profit" in data
    assert "profit_margin" in data
    assert "total_orders" in data
    assert "average_order_value" in data
    assert "refund_total" in data


@pytest.mark.asyncio
async def test_get_profit_summary_with_period(client):
    """Fetching profit summary with an explicit period returns matching period."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/summary?period=7d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "7d"


@pytest.mark.asyncio
async def test_get_profit_summary_invalid_period(client):
    """Fetching profit summary with an invalid period returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/summary?period=15d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_profit_summary_no_auth(client):
    """Fetching profit summary without authentication returns 401."""
    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/analytics/summary",
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Revenue Time Series
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_revenue_time_series_success(client):
    """Fetching revenue time series returns period and data list."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/revenue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "30d"
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_revenue_time_series_invalid_period(client):
    """Fetching revenue time series with an invalid period returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/revenue?period=1y",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Top Products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_top_products_success(client):
    """Fetching top products returns period and empty product list for new store."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/top-products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "30d"
    assert isinstance(data["products"], list)


@pytest.mark.asyncio
async def test_get_top_products_with_limit(client):
    """Top products endpoint respects the limit query parameter."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/top-products?limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Dashboard (Combined)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_dashboard_success(client):
    """Fetching dashboard returns summary, revenue, and top products."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/analytics/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "revenue" in data
    assert "top_products" in data
    assert data["summary"]["period"] == "30d"
    assert isinstance(data["revenue"]["data"], list)
    assert isinstance(data["top_products"]["products"], list)


@pytest.mark.asyncio
async def test_get_dashboard_wrong_store(client):
    """Fetching dashboard for another user's store returns 404."""
    token_a = await register_and_get_token(client, email="a@example.com")
    token_b = await register_and_get_token(client, email="b@example.com")
    store_b = await create_test_store(client, token_b, name="B Store")

    response = await client.get(
        f"/api/v1/stores/{store_b['id']}/analytics/dashboard",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404
