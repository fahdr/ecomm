"""Tests for customer account endpoints.

Covers customer registration, login, token refresh, profile management,
order history, wishlist, and address CRUD.

**For QA Engineers:**
    Each test creates its own user, store, and customer data for isolation.
    The conftest.py truncates all tables before each test.
"""

import uuid

import pytest

# ── Helpers ─────────────────────────────────────────────────────────────


async def create_user_and_store(client):
    """Register a platform user, log in, and create a store.

    Returns:
        tuple: (auth_headers, store_slug, store_id)
    """
    email = f"owner-{uuid.uuid4().hex[:8]}@test.com"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    store_resp = await client.post("/api/v1/stores", json={
        "name": f"Test Store {uuid.uuid4().hex[:6]}",
        "niche": "electronics",
    }, headers=headers)
    store = store_resp.json()
    return headers, store["slug"], store["id"]


async def register_customer(client, slug, email="customer@test.com"):
    """Register a customer and return (customer_data, token_headers)."""
    resp = await client.post(f"/api/v1/public/stores/{slug}/customers/register", json={
        "email": email,
        "password": "custpass123",
        "first_name": "Test",
        "last_name": "Customer",
    })
    data = resp.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return data, headers


async def create_product(client, store_id, headers, title="Test Product", price=29.99):
    """Create an active product in the store. Returns product data."""
    resp = await client.post(f"/api/v1/stores/{store_id}/products", json={
        "title": title,
        "price": price,
        "description": "A test product",
        "status": "active",
    }, headers=headers)
    return resp.json()


# ── Auth Tests ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_customer_register(client):
    """Customer can register for a store and receives tokens."""
    _, slug, _ = await create_user_and_store(client)
    resp = await client.post(f"/api/v1/public/stores/{slug}/customers/register", json={
        "email": "newcust@test.com",
        "password": "custpass123",
        "first_name": "Jane",
        "last_name": "Doe",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["customer"]["email"] == "newcust@test.com"
    assert data["customer"]["first_name"] == "Jane"


@pytest.mark.anyio
async def test_customer_register_duplicate(client):
    """Registering with the same email in the same store returns 400."""
    _, slug, _ = await create_user_and_store(client)
    await client.post(f"/api/v1/public/stores/{slug}/customers/register", json={
        "email": "dup@test.com",
        "password": "custpass123",
    })
    resp = await client.post(f"/api/v1/public/stores/{slug}/customers/register", json={
        "email": "dup@test.com",
        "password": "custpass123",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_customer_login(client):
    """Customer can log in with correct credentials."""
    _, slug, _ = await create_user_and_store(client)
    await register_customer(client, slug, "login@test.com")
    resp = await client.post(f"/api/v1/public/stores/{slug}/customers/login", json={
        "email": "login@test.com",
        "password": "custpass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.anyio
async def test_customer_login_wrong_password(client):
    """Login with wrong password returns 401."""
    _, slug, _ = await create_user_and_store(client)
    await register_customer(client, slug, "wrong@test.com")
    resp = await client.post(f"/api/v1/public/stores/{slug}/customers/login", json={
        "email": "wrong@test.com",
        "password": "badpassword",
    })
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_customer_refresh_token(client):
    """Customer can refresh their access token."""
    _, slug, _ = await create_user_and_store(client)
    reg_data, _ = await register_customer(client, slug)
    resp = await client.post(f"/api/v1/public/stores/{slug}/customers/refresh", json={
        "refresh_token": reg_data["refresh_token"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.anyio
async def test_customer_get_profile(client):
    """Authenticated customer can view their profile."""
    _, slug, _ = await create_user_and_store(client)
    _, cust_headers = await register_customer(client, slug, "profile@test.com")
    resp = await client.get(
        f"/api/v1/public/stores/{slug}/customers/me",
        headers=cust_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "profile@test.com"


@pytest.mark.anyio
async def test_customer_update_profile(client):
    """Customer can update their name."""
    _, slug, _ = await create_user_and_store(client)
    _, cust_headers = await register_customer(client, slug)
    resp = await client.patch(
        f"/api/v1/public/stores/{slug}/customers/me",
        json={"first_name": "Updated"},
        headers=cust_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"


@pytest.mark.anyio
async def test_customer_change_password(client):
    """Customer can change their password."""
    _, slug, _ = await create_user_and_store(client)
    _, cust_headers = await register_customer(client, slug, "chpw@test.com")
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/change-password",
        json={"current_password": "custpass123", "new_password": "newpass456"},
        headers=cust_headers,
    )
    assert resp.status_code == 204

    # Verify new password works
    login_resp = await client.post(f"/api/v1/public/stores/{slug}/customers/login", json={
        "email": "chpw@test.com",
        "password": "newpass456",
    })
    assert login_resp.status_code == 200


# ── Order History Tests ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_customer_order_history(client):
    """Customer can view their order history."""
    owner_headers, slug, store_id = await create_user_and_store(client)
    product = await create_product(client, store_id, owner_headers)
    _, cust_headers = await register_customer(client, slug, "orders@test.com")

    # Place an order via checkout
    checkout_resp = await client.post(f"/api/v1/public/stores/{slug}/checkout", json={
        "customer_email": "orders@test.com",
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": {
            "name": "Test", "line1": "123 St", "city": "NYC",
            "postal_code": "10001", "country": "US",
        },
    })
    assert checkout_resp.status_code in (200, 201)

    # View orders
    resp = await client.get(
        f"/api/v1/public/stores/{slug}/customers/me/orders",
        headers=cust_headers,
    )
    assert resp.status_code == 200
    orders = resp.json()
    assert len(orders) >= 1
    assert orders[0]["items"][0]["product_title"] == "Test Product"


# ── Wishlist Tests ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_customer_wishlist_crud(client):
    """Customer can add, list, and remove wishlist items."""
    owner_headers, slug, store_id = await create_user_and_store(client)
    product = await create_product(client, store_id, owner_headers)
    _, cust_headers = await register_customer(client, slug, "wish@test.com")

    # Add to wishlist
    add_resp = await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/wishlist/{product['id']}",
        headers=cust_headers,
    )
    assert add_resp.status_code == 201

    # List wishlist
    list_resp = await client.get(
        f"/api/v1/public/stores/{slug}/customers/me/wishlist",
        headers=cust_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["product_title"] == "Test Product"

    # Remove from wishlist
    del_resp = await client.delete(
        f"/api/v1/public/stores/{slug}/customers/me/wishlist/{product['id']}",
        headers=cust_headers,
    )
    assert del_resp.status_code == 204


@pytest.mark.anyio
async def test_wishlist_duplicate_returns_409(client):
    """Adding the same product to wishlist twice returns 409."""
    owner_headers, slug, store_id = await create_user_and_store(client)
    product = await create_product(client, store_id, owner_headers)
    _, cust_headers = await register_customer(client, slug, "dup-wish@test.com")

    await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/wishlist/{product['id']}",
        headers=cust_headers,
    )
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/wishlist/{product['id']}",
        headers=cust_headers,
    )
    assert resp.status_code == 409


# ── Address Tests ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_customer_address_crud(client):
    """Customer can create, list, update, and delete addresses."""
    _, slug, _ = await create_user_and_store(client)
    _, cust_headers = await register_customer(client, slug, "addr@test.com")

    # Create
    create_resp = await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/addresses",
        json={
            "label": "Home", "name": "Jane Doe",
            "line1": "123 Main St", "city": "Portland",
            "postal_code": "97201", "country": "US",
            "is_default": True,
        },
        headers=cust_headers,
    )
    assert create_resp.status_code == 201
    addr = create_resp.json()
    assert addr["label"] == "Home"
    assert addr["is_default"] is True

    # List
    list_resp = await client.get(
        f"/api/v1/public/stores/{slug}/customers/me/addresses",
        headers=cust_headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update
    update_resp = await client.patch(
        f"/api/v1/public/stores/{slug}/customers/me/addresses/{addr['id']}",
        json={
            "label": "Office", "name": "Jane Doe",
            "line1": "456 Work Ave", "city": "Portland",
            "postal_code": "97201", "country": "US",
            "is_default": True,
        },
        headers=cust_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["label"] == "Office"

    # Delete
    del_resp = await client.delete(
        f"/api/v1/public/stores/{slug}/customers/me/addresses/{addr['id']}",
        headers=cust_headers,
    )
    assert del_resp.status_code == 204


@pytest.mark.anyio
async def test_address_set_default(client):
    """Setting an address as default unsets the previous default."""
    _, slug, _ = await create_user_and_store(client)
    _, cust_headers = await register_customer(client, slug, "def-addr@test.com")

    # Create two addresses
    addr1_resp = await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/addresses",
        json={
            "label": "Home", "name": "A",
            "line1": "1 St", "city": "C", "postal_code": "00000", "country": "US",
            "is_default": True,
        },
        headers=cust_headers,
    )
    addr1 = addr1_resp.json()

    addr2_resp = await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/addresses",
        json={
            "label": "Office", "name": "B",
            "line1": "2 St", "city": "C", "postal_code": "00000", "country": "US",
            "is_default": False,
        },
        headers=cust_headers,
    )
    addr2 = addr2_resp.json()

    # Set addr2 as default
    await client.post(
        f"/api/v1/public/stores/{slug}/customers/me/addresses/{addr2['id']}/default",
        headers=cust_headers,
    )

    # List — addr2 should be default, addr1 should not
    list_resp = await client.get(
        f"/api/v1/public/stores/{slug}/customers/me/addresses",
        headers=cust_headers,
    )
    addrs = list_resp.json()
    defaults = [a for a in addrs if a["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == addr2["id"]
