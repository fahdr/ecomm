"""Tests for customer account endpoints (orders and wishlist).

Covers customer order listing, order detail, wishlist CRUD, and
access control.

**For QA Engineers:**
    Tests verify that customers only see their own orders, guest orders
    are not visible, and wishlist operations validate product existence.
"""

import pytest
import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_store_with_product(client) -> dict:
    """Create a user, store, and active product. Returns all data."""
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

    product_resp = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={
            "title": "Test Product",
            "price": "29.99",
            "status": "active",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    product = product_resp.json()

    return {
        "store": store,
        "slug": store["slug"],
        "user_token": user_token,
        "product": product,
    }


async def _register_customer(client, slug: str, email="cust@test.com") -> dict:
    """Register a customer and return tokens."""
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": email, "password": "password123"},
    )
    return resp.json()


async def _create_customer_order(client, slug: str, product_id: str, token: str) -> dict:
    """Create an order as a logged-in customer."""
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "cust@test.com",
            "items": [{"product_id": product_id, "quantity": 1}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _create_guest_order(client, slug: str, product_id: str) -> dict:
    """Create an order as a guest (no auth token)."""
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "guest@test.com",
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Customer Orders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_list_orders_empty(client):
    """Customer with no orders sees empty list."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders",
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_customer_list_orders_with_data(client):
    """Customer sees their own orders after checkout."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    await _create_customer_order(
        client, setup["slug"], setup["product"]["id"], cust["access_token"]
    )

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders",
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["customer_email"] == "cust@test.com"


@pytest.mark.asyncio
async def test_customer_only_sees_own_orders(client):
    """Customer A cannot see Customer B's orders."""
    setup = await _setup_store_with_product(client)
    cust_a = await _register_customer(client, setup["slug"], "a@test.com")
    cust_b = await _register_customer(client, setup["slug"], "b@test.com")

    await _create_customer_order(
        client, setup["slug"], setup["product"]["id"], cust_a["access_token"]
    )

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders",
        headers={"Authorization": f"Bearer {cust_b['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_guest_order_not_visible_to_customer(client):
    """Guest orders (customer_id=NULL) are not visible to logged-in customers."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    await _create_guest_order(client, setup["slug"], setup["product"]["id"])

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders",
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_customer_order_detail(client):
    """Customer can view details of their own order."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    order = await _create_customer_order(
        client, setup["slug"], setup["product"]["id"], cust["access_token"]
    )

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders/{order['order_id']}",
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == order["order_id"]


@pytest.mark.asyncio
async def test_customer_order_not_found(client):
    """Requesting a non-existent order returns 404."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_customer_orders_require_auth(client):
    """Order listing without auth returns 401."""
    setup = await _setup_store_with_product(client)
    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/orders",
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_to_wishlist(client):
    """Customer can add a product to their wishlist."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    resp = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        json={"product_id": setup["product"]["id"]},
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_id"] == setup["product"]["id"]
    assert "product" in data


@pytest.mark.asyncio
async def test_add_duplicate_to_wishlist(client):
    """Adding the same product twice returns 409."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])
    headers = {"Authorization": f"Bearer {cust['access_token']}"}

    await client.post(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        json={"product_id": setup["product"]["id"]},
        headers=headers,
    )

    resp = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        json={"product_id": setup["product"]["id"]},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_nonexistent_product_to_wishlist(client):
    """Adding a non-existent product returns 404."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    resp = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        json={"product_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_wishlist(client):
    """Customer can list their wishlist items."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])
    headers = {"Authorization": f"Bearer {cust['access_token']}"}

    await client.post(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        json={"product_id": setup["product"]["id"]},
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["product"]["title"] == "Test Product"


@pytest.mark.asyncio
async def test_remove_from_wishlist(client):
    """Customer can remove an item from their wishlist."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])
    headers = {"Authorization": f"Bearer {cust['access_token']}"}

    add_resp = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        json={"product_id": setup["product"]["id"]},
        headers=headers,
    )
    item_id = add_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist/{item_id}",
        headers=headers,
    )
    assert resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
        headers=headers,
    )
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_wishlist_item(client):
    """Removing a non-existent wishlist item returns 404."""
    setup = await _setup_store_with_product(client)
    cust = await _register_customer(client, setup["slug"])

    resp = await client.delete(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {cust['access_token']}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_wishlist_requires_auth(client):
    """Wishlist endpoints without auth return 401."""
    setup = await _setup_store_with_product(client)

    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/account/wishlist",
    )
    assert resp.status_code == 401
