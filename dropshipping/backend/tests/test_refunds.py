"""Tests for refund CRUD and processing endpoints (Feature F14).

Covers refund creation, listing (pagination), retrieval by ID, status
updates (approve/reject), and refund processing (Stripe mock).

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Helper functions register users, create stores, products, and orders
    to reduce boilerplate. To create a refund, an order must first exist.
    Orders are created via the public checkout endpoint which uses mock
    Stripe in development. The ``reason`` field uses predefined
    ``RefundReason`` enum values (``defective``, ``wrong_item``,
    ``not_as_described``, ``changed_mind``, ``other``). Extended
    details go in ``reason_details``.
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


async def create_test_product(
    client,
    token: str,
    store_id: str,
    title: str = "Test Product",
    price: float = 29.99,
    status: str = "active",
    **kwargs,
) -> dict:
    """Create a product and return the response data.

    The product is created with 'active' status by default so it can
    be used in checkout.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        status: Product status (default 'active' for checkout).
        **kwargs: Additional product fields.

    Returns:
        The JSON response dictionary for the created product.
    """
    data = {"title": title, "price": price, "status": status, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def create_test_order(
    client, store_slug: str, product_id: str, customer_email: str = "buyer@example.com"
) -> dict:
    """Create an order via the public checkout and return the checkout response.

    Uses the public checkout endpoint which creates a pending order and
    returns a mock Stripe checkout URL.

    Args:
        client: The async HTTP test client.
        store_slug: The store's URL slug.
        product_id: UUID of the product to purchase.
        customer_email: Customer's email address.

    Returns:
        The JSON response dictionary with checkout_url, session_id, and order_id.
    """
    resp = await client.post(
        f"/api/v1/public/stores/{store_slug}/checkout",
        json={
            "customer_email": customer_email,
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping_address": {
                "name": "Test Customer",
                "line1": "123 Test St",
                "city": "Testville",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
        },
    )
    return resp.json()


async def create_test_refund(
    client,
    token: str,
    store_id: str,
    order_id: str,
    amount: float = 29.99,
    reason: str = "other",
    **kwargs,
) -> dict:
    """Create a refund and return the response data.

    The ``reason`` parameter should be one of the ``RefundReason`` enum
    values: ``defective``, ``wrong_item``, ``not_as_described``,
    ``changed_mind``, or ``other``. Free-text reasons are converted to
    ``other`` by the API.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        order_id: UUID of the order to refund.
        amount: Refund amount.
        reason: Predefined refund reason (default ``"other"``).
        **kwargs: Additional refund fields (reason_details, etc.).

    Returns:
        The JSON response dictionary for the created refund.
    """
    data = {
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        **kwargs,
    }
    resp = await client.post(
        f"/api/v1/stores/{store_id}/refunds",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Refund
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_refund_success(client):
    """Creating a refund request returns 201 with pending status."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Refund Store")
    product = await create_test_product(client, token, store["id"], title="Refund Item", price=50.0)
    checkout = await create_test_order(client, store["slug"], product["id"])

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/refunds",
        json={
            "order_id": str(checkout["order_id"]),
            "amount": 50.0,
            "reason": "not_as_described",
            "reason_details": "Customer complaint - item did not match listing",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert float(data["amount"]) == 50.0
    assert data["reason"] == "not_as_described"
    assert data["reason_details"] == "Customer complaint - item did not match listing"
    assert data["stripe_refund_id"] is None
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_refund_no_auth(client):
    """Creating a refund without authentication returns 401."""
    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/refunds",
        json={
            "order_id": "00000000-0000-0000-0000-000000000000",
            "amount": 10.0,
            "reason": "other",
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List Refunds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_refunds_pagination(client):
    """Listing refunds returns paginated results with correct metadata."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="List Refund Store")
    product = await create_test_product(client, token, store["id"], title="List Item", price=25.0)

    # Create two orders and a refund for each.
    checkout1 = await create_test_order(client, store["slug"], product["id"], "b1@example.com")
    checkout2 = await create_test_order(client, store["slug"], product["id"], "b2@example.com")
    await create_test_refund(client, token, store["id"], str(checkout1["order_id"]), amount=25.0)
    await create_test_refund(client, token, store["id"], str(checkout2["order_id"]), amount=25.0)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/refunds?page=1&per_page=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["pages"] == 2


# ---------------------------------------------------------------------------
# Get Refund by ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_refund_by_id(client):
    """Retrieving a refund by ID returns the full refund data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Get Refund Store")
    product = await create_test_product(client, token, store["id"], title="Get Item", price=40.0)
    checkout = await create_test_order(client, store["slug"], product["id"])
    refund = await create_test_refund(client, token, store["id"], str(checkout["order_id"]), amount=40.0)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/refunds/{refund['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == refund["id"]
    assert float(data["amount"]) == 40.0


@pytest.mark.asyncio
async def test_get_refund_not_found(client):
    """Retrieving a non-existent refund returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Missing Refund Store")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/refunds/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Process Refund
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_refund_after_approval(client):
    """Processing an approved refund returns the updated refund with completed status."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Process Store")
    product = await create_test_product(client, token, store["id"], title="Process Item", price=60.0)
    checkout = await create_test_order(client, store["slug"], product["id"])
    refund = await create_test_refund(
        client, token, store["id"], str(checkout["order_id"]), amount=60.0
    )

    # First approve the refund.
    approve_resp = await client.patch(
        f"/api/v1/stores/{store['id']}/refunds/{refund['id']}",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # Now process it.
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/refunds/{refund['id']}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["refund"]["status"] == "completed"
    assert "message" in data


@pytest.mark.asyncio
async def test_process_refund_already_completed_fails(client):
    """Processing a refund that is already completed returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Fail Process Store")
    product = await create_test_product(client, token, store["id"], title="Fail Item", price=30.0)
    checkout = await create_test_order(client, store["slug"], product["id"])
    refund = await create_test_refund(
        client, token, store["id"], str(checkout["order_id"]), amount=30.0
    )

    # Approve and process the refund first.
    await client.patch(
        f"/api/v1/stores/{store['id']}/refunds/{refund['id']}",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        f"/api/v1/stores/{store['id']}/refunds/{refund['id']}/process",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to process again -- should fail because it is already completed.
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/refunds/{refund['id']}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
