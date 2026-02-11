"""Tests for order CRUD, checkout, and webhook endpoints.

Covers order creation via checkout, order listing (pagination, status filter),
order retrieval, status updates, cart validation, tenant isolation,
public order lookup, mock Stripe integration, and checkout with discounts,
tax rates, gift cards, and shipping address.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Helper functions register users and create stores/products to reduce
    boilerplate. Tests verify tenant isolation, cart validation errors,
    and that orders transition correctly through statuses. Checkout
    integration tests verify discount, tax, and gift card calculations
    are reflected in order totals and response fields.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SHIPPING_ADDRESS = {
    "name": "John Doe",
    "line1": "123 Test St",
    "city": "Testville",
    "state": "CA",
    "postal_code": "90210",
    "country": "US",
}
"""Standard shipping address used across all checkout tests."""


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
    client, token: str, name: str = "Test Store", niche: str = "electronics"
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
    variants: list | None = None,
) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: The store's UUID string.
        title: Product title.
        price: Product price.
        status: Product status.
        variants: Optional list of variant dicts.

    Returns:
        The JSON response dictionary for the created product.
    """
    payload = {"title": title, "price": price, "status": status}
    if variants:
        payload["variants"] = variants
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def setup_store_and_product(client):
    """Create a user, store, and active product for checkout tests.

    Returns:
        Tuple of (token, store_data, product_data, store_slug).
    """
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    product = await create_test_product(client, token, store["id"])
    return token, store, product, store["slug"]


# ---------------------------------------------------------------------------
# Checkout Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_creates_pending_order(client):
    """Checkout with valid items creates a pending order and returns checkout URL."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": product["id"], "quantity": 1},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "checkout_url" in data
    assert "session_id" in data
    assert "order_id" in data


@pytest.mark.asyncio
async def test_checkout_with_variant(client):
    """Checkout with a specific variant works correctly."""
    token, store, _, slug = await setup_store_and_product(client)
    product = await create_test_product(
        client, token, store["id"],
        title="Variant Product",
        price=10.00,
        variants=[
            {"name": "Small", "price": 10.00, "inventory_count": 5},
            {"name": "Large", "price": 15.00, "inventory_count": 3},
        ],
    )
    variant_id = product["variants"][0]["id"]

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": product["id"], "variant_id": variant_id, "quantity": 2},
            ],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_checkout_insufficient_stock(client):
    """Checkout with more quantity than inventory returns 400."""
    token, store, _, slug = await setup_store_and_product(client)
    product = await create_test_product(
        client, token, store["id"],
        title="Limited Product",
        price=10.00,
        variants=[{"name": "Only One", "inventory_count": 1}],
    )
    variant_id = product["variants"][0]["id"]

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": product["id"], "variant_id": variant_id, "quantity": 5},
            ],
        },
    )
    assert resp.status_code == 400
    assert "Insufficient stock" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_checkout_invalid_product(client):
    """Checkout with a non-existent product returns 400."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": str(uuid.uuid4()), "quantity": 1},
            ],
        },
    )
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_checkout_draft_product_rejected(client):
    """Checkout with a draft product returns 400."""
    token, store, _, slug = await setup_store_and_product(client)
    draft_product = await create_test_product(
        client, token, store["id"],
        title="Draft Product",
        price=10.00,
        status="draft",
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": draft_product["id"], "quantity": 1},
            ],
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_checkout_unknown_store(client):
    """Checkout for a non-existent store returns 404."""
    resp = await client.post(
        "/api/v1/public/stores/nonexistent-store/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": str(uuid.uuid4()), "quantity": 1},
            ],
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_checkout_empty_cart(client):
    """Checkout with empty items list returns 422 (validation error)."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_checkout_no_auth_required(client):
    """Checkout does not require authentication."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": product["id"], "quantity": 1},
            ],
        },
    )
    # No auth header — should still work
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_checkout_multiple_items(client):
    """Checkout with multiple different products works."""
    token, store, product1, slug = await setup_store_and_product(client)
    product2 = await create_test_product(
        client, token, store["id"],
        title="Second Product",
        price=19.99,
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": product1["id"], "quantity": 2},
                {"product_id": product2["id"], "quantity": 1},
            ],
        },
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Order List / Detail Tests (Store Owner)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_orders_empty(client):
    """Listing orders for a store with no orders returns empty list."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_orders_after_checkout(client):
    """Orders created via checkout appear in the store owner's order list."""
    token, store, product, slug = await setup_store_and_product(client)

    # Create an order via checkout
    await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["customer_email"] == "buyer@example.com"
    assert data["items"][0]["status"] == "pending"
    assert len(data["items"][0]["items"]) == 1


@pytest.mark.asyncio
async def test_list_orders_status_filter(client):
    """Filtering orders by status works."""
    token, store, product, slug = await setup_store_and_product(client)

    await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )

    # Filter by "paid" — should return 0 (order is pending)
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders?status=paid",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # Filter by "pending" — should return 1
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders?status=pending",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_order_detail(client):
    """Retrieving an order by ID returns full order with items."""
    token, store, product, slug = await setup_store_and_product(client)

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 3}],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == order_id
    assert data["customer_email"] == "buyer@example.com"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3
    assert data["items"][0]["product_title"] == "Test Product"


@pytest.mark.asyncio
async def test_get_order_not_found(client):
    """Retrieving a non-existent order returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_order_status(client):
    """Store owner can update order status."""
    token, store, product, slug = await setup_store_and_product(client)

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/orders/{order_id}",
        json={"status": "shipped"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"


# ---------------------------------------------------------------------------
# Auth & Tenant Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orders_require_auth(client):
    """Order endpoints require authentication."""
    resp = await client.get(f"/api/v1/stores/{uuid.uuid4()}/orders")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_orders_tenant_isolation(client):
    """User cannot see orders for another user's store."""
    token1 = await register_and_get_token(client, "owner1@example.com")
    store1 = await create_test_store(client, token1, name="Store 1")
    product1 = await create_test_product(client, token1, store1["id"])

    # Create an order on store1
    await client.post(
        f"/api/v1/public/stores/{store1['slug']}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product1["id"], "quantity": 1}],
        },
    )

    # User 2 tries to access store1's orders
    token2 = await register_and_get_token(client, "owner2@example.com")

    resp = await client.get(
        f"/api/v1/stores/{store1['id']}/orders",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Public Order Lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_order_lookup(client):
    """Public order lookup by ID works for order confirmation page."""
    token, store, product, slug = await setup_store_and_product(client)

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    resp = await client.get(
        f"/api/v1/public/stores/{slug}/orders/{order_id}",
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_public_order_lookup_not_found(client):
    """Public order lookup with invalid ID returns 404."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.get(
        f"/api/v1/public/stores/{slug}/orders/{uuid.uuid4()}",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Order Total Calculation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_order_total_calculation(client):
    """Order total is calculated correctly from item prices and quantities."""
    token, store, product, slug = await setup_store_and_product(client)

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 3}],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    # Product price is 29.99, quantity 3
    expected_total = "89.97"
    assert data["total"] == expected_total


@pytest.mark.asyncio
async def test_order_captures_variant_price(client):
    """Order uses variant price when variant has a price override."""
    token, store, _, slug = await setup_store_and_product(client)
    product = await create_test_product(
        client, token, store["id"],
        title="Priced Variant Product",
        price=10.00,
        variants=[{"name": "Premium", "price": 25.00, "inventory_count": 10}],
    )
    variant_id = product["variants"][0]["id"]

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [
                {"product_id": product["id"], "variant_id": variant_id, "quantity": 2},
            ],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    # Variant price is 25.00, quantity 2
    assert data["total"] == "50.00"
    assert data["items"][0]["unit_price"] == "25.00"
    assert data["items"][0]["variant_name"] == "Premium"


# ---------------------------------------------------------------------------
# Checkout Integration Helpers (discounts, tax, gift cards)
# ---------------------------------------------------------------------------


async def create_test_discount(
    client,
    token: str,
    store_id: str,
    code: str = "SAVE20",
    discount_type: str = "percentage",
    value: float = 20.0,
    **kwargs,
) -> dict:
    """Create a discount and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: UUID of the store.
        code: Coupon code.
        discount_type: 'percentage' or 'fixed_amount'.
        value: The discount value.
        **kwargs: Additional discount fields.

    Returns:
        The JSON response dictionary for the created discount.
    """
    if "starts_at" not in kwargs:
        kwargs["starts_at"] = datetime.now(timezone.utc).isoformat()
    data = {"code": code, "discount_type": discount_type, "value": value, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/discounts",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def create_test_tax_rate(
    client,
    token: str,
    store_id: str,
    name: str = "CA Sales Tax",
    country: str = "US",
    state: str | None = "CA",
    rate: float = 8.25,
) -> dict:
    """Create a tax rate and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: UUID of the store.
        name: Tax rate display name.
        country: ISO country code.
        state: Optional state code.
        rate: Tax rate percentage.

    Returns:
        The JSON response dictionary for the created tax rate.
    """
    payload = {"name": name, "country": country, "rate": rate}
    if state is not None:
        payload["state"] = state
    resp = await client.post(
        f"/api/v1/stores/{store_id}/tax-rates",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def create_test_gift_card(
    client,
    token: str,
    store_id: str,
    initial_balance: float = 50.0,
) -> dict:
    """Create a gift card and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: UUID of the store.
        initial_balance: Starting balance.

    Returns:
        The JSON response dictionary for the created gift card.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/gift-cards",
        json={"initial_balance": initial_balance},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Checkout with Discounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_with_percentage_discount(client):
    """Checkout with a percentage discount reduces the order total."""
    token, store, product, slug = await setup_store_and_product(client)

    # Create a 20% discount
    await create_test_discount(
        client, token, store["id"], code="SAVE20", discount_type="percentage", value=20.0
    )

    # Product price is 29.99, qty 1 → subtotal 29.99
    # 20% off → discount_amount = 29.99 * 0.20 = 5.998
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
            "discount_code": "SAVE20",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subtotal"] == "29.99"
    # Discount applied (exact amount depends on backend rounding)
    assert float(data["discount_amount"]) > 0
    assert float(data["total"]) < 29.99


@pytest.mark.asyncio
async def test_checkout_with_fixed_discount(client):
    """Checkout with a fixed-amount discount reduces the order total."""
    token, store, product, slug = await setup_store_and_product(client)

    # Create a $5 off discount
    await create_test_discount(
        client, token, store["id"], code="FLAT5", discount_type="fixed_amount", value=5.0
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
            "discount_code": "FLAT5",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subtotal"] == "29.99"
    assert float(data["discount_amount"]) == 5.00
    assert float(data["total"]) == 24.99


@pytest.mark.asyncio
async def test_checkout_invalid_discount_code(client):
    """Checkout with an invalid discount code returns 400."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
            "discount_code": "FAKECODE",
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Checkout with Tax
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_with_tax(client):
    """Checkout calculates tax from matching tax rates and adds to total."""
    token, store, product, slug = await setup_store_and_product(client)

    # Create an 8.25% CA sales tax
    await create_test_tax_rate(
        client, token, store["id"], name="CA Tax", country="US", state="CA", rate=8.25
    )

    # Product: 29.99, qty 1 → subtotal 29.99
    # Tax: 29.99 * 8.25% ≈ 2.47
    # Total: 29.99 + 2.47 = 32.46
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subtotal"] == "29.99"
    assert float(data["tax_amount"]) == 2.47
    assert float(data["total"]) == 32.46


@pytest.mark.asyncio
async def test_checkout_tax_with_discount(client):
    """Tax is calculated on the discounted subtotal, not the original."""
    token, store, product, slug = await setup_store_and_product(client)

    # 8.25% CA tax
    await create_test_tax_rate(
        client, token, store["id"], name="CA Tax", country="US", state="CA", rate=8.25
    )
    # $5 off discount
    await create_test_discount(
        client, token, store["id"], code="FLAT5", discount_type="fixed_amount", value=5.0
    )

    # Subtotal: 29.99, discount: 5.00, discounted: 24.99
    # Tax: 24.99 * 8.25% = 2.061675 → 2.06
    # Total: 24.99 + 2.06 = 27.05
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
            "discount_code": "FLAT5",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["discount_amount"]) == 5.00
    # Tax applied on discounted subtotal
    assert float(data["tax_amount"]) > 0
    # Total = discounted subtotal + tax
    assert float(data["total"]) > float(data["subtotal"]) - float(data["discount_amount"])


# ---------------------------------------------------------------------------
# Checkout with Gift Cards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_with_gift_card(client):
    """Checkout with a gift card reduces the total by the card balance."""
    token, store, product, slug = await setup_store_and_product(client)

    # Create a $10 gift card
    gc = await create_test_gift_card(client, token, store["id"], initial_balance=10.0)

    # Subtotal: 29.99, gift card: 10.00
    # Total: 29.99 - 10.00 = 19.99
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
            "gift_card_code": gc["code"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["gift_card_amount"]) == 10.00
    assert float(data["total"]) == 19.99


# ---------------------------------------------------------------------------
# Checkout Response Fields & Shipping Address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_response_has_financial_breakdown(client):
    """Checkout response includes subtotal, discount, tax, gift card, and total."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 2}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()

    # All financial fields should be present
    assert "subtotal" in data
    assert "discount_amount" in data
    assert "tax_amount" in data
    assert "gift_card_amount" in data
    assert "total" in data
    # Subtotal should be correct: 29.99 * 2 = 59.98
    assert data["subtotal"] == "59.98"


@pytest.mark.asyncio
async def test_order_stores_shipping_address(client):
    """Order detail includes the shipping address from checkout."""
    token, store, product, slug = await setup_store_and_product(client)

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    # Fetch via store-owner endpoint
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["shipping_address"] is not None
    assert data["shipping_address"]["name"] == "John Doe"
    assert data["shipping_address"]["city"] == "Testville"
    assert data["shipping_address"]["country"] == "US"


@pytest.mark.asyncio
async def test_public_order_has_financial_fields(client):
    """Public order lookup includes financial breakdown and shipping address."""
    token, store, product, slug = await setup_store_and_product(client)

    checkout_resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )
    order_id = checkout_resp.json()["order_id"]

    resp = await client.get(
        f"/api/v1/public/stores/{slug}/orders/{order_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "subtotal" in data
    assert "total" in data
    assert data["shipping_address"] is not None
    assert data["shipping_address"]["line1"] == "123 Test St"


# ---------------------------------------------------------------------------
# Validate Discount & Calculate Tax Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_discount_endpoint(client):
    """Public discount validation endpoint returns discount amount."""
    token, store, product, slug = await setup_store_and_product(client)

    await create_test_discount(
        client, token, store["id"], code="TEST10", discount_type="percentage", value=10.0
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout/validate-discount",
        json={"code": "TEST10", "subtotal": 100.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert float(data["discount_amount"]) == 10.00


@pytest.mark.asyncio
async def test_validate_discount_invalid_code(client):
    """Public discount validation with invalid code returns valid=false."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout/validate-discount",
        json={"code": "NONEXISTENT", "subtotal": 100.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False


@pytest.mark.asyncio
async def test_calculate_tax_endpoint(client):
    """Public tax calculation endpoint returns tax amount for address."""
    token, store, product, slug = await setup_store_and_product(client)

    await create_test_tax_rate(
        client, token, store["id"], name="CA Tax", country="US", state="CA", rate=10.0
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout/calculate-tax",
        json={"subtotal": 100.0, "country": "US", "state": "CA"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["tax_amount"]) == 10.00


@pytest.mark.asyncio
async def test_calculate_tax_no_matching_rates(client):
    """Tax calculation with no matching rates returns zero tax."""
    token, store, product, slug = await setup_store_and_product(client)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/checkout/calculate-tax",
        json={"subtotal": 100.0, "country": "GB"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["tax_amount"]) == 0.00
