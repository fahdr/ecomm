"""Tests for dashboard customer management endpoints.

Covers listing customers, customer detail with order stats, and
customer order history as viewed by the store owner.

**For QA Engineers:**
    Tests verify store ownership checks, search functionality, and
    correct order statistics (order_count, total_spent).
"""

import pytest
import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_store_with_customer(client) -> dict:
    """Create user, store, customer, and product. Returns all data."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "ownerpass123"},
    )
    user_token = reg.json()["access_token"]
    store_resp = await client.post(
        "/api/v1/stores",
        json={"name": "Test Store", "niche": "Electronics"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    store = store_resp.json()

    # Create product
    product_resp = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={"title": "Gadget", "price": "50.00", "status": "active"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    product = product_resp.json()

    # Register a customer
    cust_resp = await client.post(
        f"/api/v1/public/stores/{store['slug']}/auth/register",
        json={
            "email": "customer@test.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        },
    )
    cust_tokens = cust_resp.json()

    return {
        "store": store,
        "user_token": user_token,
        "product": product,
        "customer_token": cust_tokens["access_token"],
    }


# ---------------------------------------------------------------------------
# List Customers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_customers_empty(client):
    """Store with no customers returns empty list."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "ownerpass123"},
    )
    token = reg.json()["access_token"]
    store = (
        await client.post(
            "/api/v1/stores",
            json={"name": "Empty Store", "niche": "N/A"},
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/customers/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_customers_with_data(client):
    """Store with registered customers returns them."""
    setup = await _setup_store_with_customer(client)

    resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "customer@test.com"
    assert data["items"][0]["first_name"] == "John"


@pytest.mark.asyncio
async def test_list_customers_search(client):
    """Search filters customers by email."""
    setup = await _setup_store_with_customer(client)
    slug = setup["store"]["slug"]

    # Register another customer
    await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": "other@test.com", "password": "password123"},
    )

    resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/?search=customer",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "customer@test.com"


@pytest.mark.asyncio
async def test_list_customers_wrong_store(client):
    """Accessing another user's store customers returns 404."""
    setup = await _setup_store_with_customer(client)

    # Register a different user
    other_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "other-owner@example.com", "password": "ownerpass123"},
    )
    other_token = other_reg.json()["access_token"]

    resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Customer Detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_detail(client):
    """Customer detail returns profile and order stats."""
    setup = await _setup_store_with_customer(client)
    slug = setup["store"]["slug"]

    # Create an order as the customer
    await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "customer@test.com",
            "items": [{"product_id": setup["product"]["id"], "quantity": 2}],
        },
        headers={"Authorization": f"Bearer {setup['customer_token']}"},
    )

    # Get customer list to find customer_id
    list_resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    customer_id = list_resp.json()["items"][0]["id"]

    resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/{customer_id}",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "customer@test.com"
    assert data["order_count"] == 1
    assert float(data["total_spent"]) == 100.00  # 50.00 * 2


@pytest.mark.asyncio
async def test_customer_detail_not_found(client):
    """Requesting a non-existent customer returns 404."""
    setup = await _setup_store_with_customer(client)

    resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Customer Orders (Dashboard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_orders_from_dashboard(client):
    """Store owner can view a specific customer's orders."""
    setup = await _setup_store_with_customer(client)
    slug = setup["store"]["slug"]

    await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "customer@test.com",
            "items": [{"product_id": setup["product"]["id"], "quantity": 1}],
        },
        headers={"Authorization": f"Bearer {setup['customer_token']}"},
    )

    list_resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    customer_id = list_resp.json()["items"][0]["id"]

    resp = await client.get(
        f"/api/v1/stores/{setup['store']['id']}/customers/{customer_id}/orders",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["customer_email"] == "customer@test.com"
