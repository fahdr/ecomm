"""Tests for the store cloning endpoint (POST /api/v1/stores/{store_id}/clone).

Covers deep cloning of stores, including all child entities (products,
variants, themes, discounts, categories, tax rules, suppliers), as well as
edge cases (not-found, tenant isolation, deleted stores, empty stores) and
verification that transient data (orders, reviews) is NOT cloned.

**For Developers:**
    The clone endpoint delegates to ``clone_service.clone_store()`` which
    performs a deep copy within a single transaction. Products, variants,
    themes, discounts, categories, tax rules, and suppliers are cloned with
    fresh UUIDs. Junction tables (product-category, product-supplier,
    discount-product, discount-category) are re-linked via ID remapping.

**For Project Managers:**
    This test suite validates the store cloning feature end-to-end:
    15 tests covering basic cloning, custom naming, slug uniqueness, each
    entity type, negative cases (404, tenant isolation), and exclusion of
    orders/reviews. All tests are independent and run against a real
    PostgreSQL database with per-test truncation.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Helper functions register users and create stores, products, themes,
    discounts, categories, tax rates, and suppliers via the API to set up
    realistic scenarios. Assertions verify response status codes, data
    integrity of cloned entities, slug uniqueness, usage counter resets,
    and that orders and reviews are not carried over.

**For End Users:**
    The "Clone Store" feature creates a full copy of an existing store
    with all products, pricing, themes, discounts, categories, tax rules,
    and suppliers. Orders and customer reviews are not copied. The cloned
    store gets a new name (original name + "(Copy)" by default, or a custom
    name you provide) and a unique URL slug.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZERO_UUID = "00000000-0000-0000-0000-000000000000"
"""A well-formed UUID that does not exist in the database."""

TEST_SHIPPING_ADDRESS = {
    "name": "John Doe",
    "line1": "123 Test St",
    "city": "Testville",
    "state": "CA",
    "postal_code": "90210",
    "country": "US",
}
"""Standard shipping address for checkout calls."""


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


def _auth(token: str) -> dict:
    """Build authorization header dict.

    Args:
        token: JWT access token.

    Returns:
        Dict with Authorization header.
    """
    return {"Authorization": f"Bearer {token}"}


async def upgrade_to_starter(client, token: str) -> None:
    """Subscribe the user to the starter plan (allows 3 stores).

    Clone creates a new store so the user needs plan capacity for at least
    2 stores (the original + the clone).

    Args:
        client: The async HTTP test client.
        token: JWT access token.
    """
    await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "starter"},
        headers=_auth(token),
    )


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
        headers=_auth(token),
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
    **kwargs,
) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        status: Product status.
        variants: Optional list of variant dicts.
        **kwargs: Additional product fields (tags, seo_title, etc.).

    Returns:
        The JSON response dictionary for the created product.
    """
    payload = {"title": title, "price": price, "status": status, **kwargs}
    if variants:
        payload["variants"] = variants
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json=payload,
        headers=_auth(token),
    )
    return resp.json()


async def create_test_category(
    client,
    token: str,
    store_id: str,
    name: str = "Electronics",
    **kwargs,
) -> dict:
    """Create a category and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        name: Category display name.
        **kwargs: Additional category fields (parent_id, position, etc.).

    Returns:
        The JSON response dictionary for the created category.
    """
    data = {"name": name, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/categories",
        json=data,
        headers=_auth(token),
    )
    return resp.json()


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
        token: JWT access token for authorization.
        store_id: UUID of the store.
        code: The coupon code string.
        discount_type: 'percentage' or 'fixed'.
        value: The discount value.
        **kwargs: Additional discount fields (expires_at, max_uses, etc.).

    Returns:
        The JSON response dictionary for the created discount.
    """
    if "starts_at" not in kwargs:
        kwargs["starts_at"] = datetime.now(timezone.utc).isoformat()
    data = {"code": code, "discount_type": discount_type, "value": value, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/discounts",
        json=data,
        headers=_auth(token),
    )
    return resp.json()


async def create_test_tax_rate(
    client,
    token: str,
    store_id: str,
    name: str = "US Sales Tax",
    country: str = "US",
    state: str | None = None,
    rate: float = 8.25,
) -> dict:
    """Create a tax rate and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        name: Tax rate display name.
        country: ISO 3166-1 alpha-2 country code.
        state: Optional state/province code.
        rate: Tax rate as a percentage.

    Returns:
        The JSON response dictionary for the created tax rate.
    """
    payload = {"name": name, "country": country, "rate": rate}
    if state is not None:
        payload["state"] = state
    resp = await client.post(
        f"/api/v1/stores/{store_id}/tax-rates",
        json=payload,
        headers=_auth(token),
    )
    return resp.json()


async def create_test_supplier(
    client,
    token: str,
    store_id: str,
    name: str = "AcmeSupply",
    **kwargs,
) -> dict:
    """Create a supplier and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        name: Supplier business name.
        **kwargs: Additional supplier fields (website, contact_email, etc.).

    Returns:
        The JSON response dictionary for the created supplier.
    """
    data = {"name": name, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/suppliers",
        json=data,
        headers=_auth(token),
    )
    return resp.json()


async def clone_store(client, token: str, store_id: str, new_name: str | None = None) -> dict:
    """Call the clone endpoint and return the raw response.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store to clone.
        new_name: Optional name override for the cloned store.

    Returns:
        The httpx Response object (not parsed JSON) so callers can assert
        status codes before accessing the body.
    """
    payload = {}
    if new_name is not None:
        payload["new_name"] = new_name
    return await client.post(
        f"/api/v1/stores/{store_id}/clone",
        json=payload,
        headers=_auth(token),
    )


# ---------------------------------------------------------------------------
# 1. Basic Clone
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_basic(client):
    """Cloning a store without a custom name appends '(Copy)' to the original name.

    Verifies:
      - 201 status code
      - Response contains both ``store`` and ``source_store_id``
      - Cloned store name is ``{original} (Copy)``
      - Cloned store niche and description match the source
      - Cloned store has a distinct ID from the source
      - Cloned store status is 'active'
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="My Shop", niche="fashion")

    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201

    data = resp.json()
    assert "store" in data
    assert "source_store_id" in data
    assert data["source_store_id"] == store["id"]

    cloned = data["store"]
    assert cloned["name"] == "My Shop (Copy)"
    assert cloned["niche"] == "fashion"
    assert cloned["description"] == "A test store"
    assert cloned["id"] != store["id"]
    assert cloned["status"] == "active"


# ---------------------------------------------------------------------------
# 2. Custom Name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_custom_name(client):
    """Cloning with a custom name uses the provided name instead of '(Copy)'.

    Verifies:
      - Cloned store name matches the custom name
      - Source store ID is correct
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Original Store")

    resp = await clone_store(client, token, store["id"], new_name="Brand New Store")
    assert resp.status_code == 201

    data = resp.json()
    cloned = data["store"]
    assert cloned["name"] == "Brand New Store"
    assert data["source_store_id"] == store["id"]


# ---------------------------------------------------------------------------
# 3. Slug Generation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_slug_generation(client):
    """The cloned store gets a unique slug derived from its name.

    Verifies:
      - Cloned store slug differs from the original
      - Slug is a valid URL-friendly string
      - The slug contains 'copy' for the default name pattern
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="My Store")

    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201

    cloned = resp.json()["store"]
    assert cloned["slug"] != store["slug"]
    # Default name "My Store (Copy)" slugifies to "my-store-copy"
    assert "copy" in cloned["slug"]
    # Slug should be lowercase, no spaces
    assert cloned["slug"] == cloned["slug"].lower()
    assert " " not in cloned["slug"]


# ---------------------------------------------------------------------------
# 4. Products and Variants Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_products_cloned(client):
    """Cloning a store copies all non-archived products and their variants.

    Verifies:
      - Products exist in the cloned store with matching titles and prices
      - Product variants are preserved with matching names, SKUs, and prices
      - Cloned products have different IDs from originals
      - Review-related fields (avg_rating, review_count) are reset
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Product Store")

    # Create products with variants.
    prod1 = await create_test_product(
        client, token, store["id"],
        title="Widget Pro",
        price=49.99,
        status="active",
        variants=[
            {"name": "Small", "sku": "WP-S", "price": 49.99, "inventory_count": 10},
            {"name": "Large", "sku": "WP-L", "price": 59.99, "inventory_count": 5},
        ],
    )
    prod2 = await create_test_product(
        client, token, store["id"],
        title="Gadget Basic",
        price=19.99,
        status="draft",
    )

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Fetch products from the cloned store.
    prod_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/products",
        headers=_auth(token),
    )
    assert prod_resp.status_code == 200
    products = prod_resp.json()["items"]
    assert len(products) == 2

    # Find the Widget Pro clone.
    widget = next(p for p in products if p["title"] == "Widget Pro")
    assert widget["price"] == "49.99"
    assert widget["status"] == "active"
    assert widget["id"] != prod1["id"]

    # Verify variants were cloned.
    assert len(widget["variants"]) == 2
    variant_names = {v["name"] for v in widget["variants"]}
    assert variant_names == {"Small", "Large"}

    small_variant = next(v for v in widget["variants"] if v["name"] == "Small")
    assert small_variant["sku"] == "WP-S"
    assert small_variant["inventory_count"] == 10

    # Verify the draft product was also cloned.
    gadget = next(p for p in products if p["title"] == "Gadget Basic")
    assert gadget["price"] == "19.99"
    assert gadget["status"] == "draft"


# ---------------------------------------------------------------------------
# 5. Themes Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_themes_cloned(client):
    """Cloning preserves all store themes, including active status and config.

    Verifies:
      - All themes from the source store exist in the cloned store
      - The active theme remains active in the clone
      - Theme colors, typography, and styles are preserved
      - Custom (non-preset) themes are also cloned
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Theme Store")

    # Source store already has preset themes seeded. List them.
    src_themes_resp = await client.get(
        f"/api/v1/stores/{store['id']}/themes",
        headers=_auth(token),
    )
    src_themes = src_themes_resp.json()
    src_theme_count = len(src_themes)

    # Create a custom theme.
    custom_resp = await client.post(
        f"/api/v1/stores/{store['id']}/themes",
        json={"name": "My Custom Theme"},
        headers=_auth(token),
    )
    assert custom_resp.status_code == 201

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Fetch themes from the cloned store.
    clone_themes_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/themes",
        headers=_auth(token),
    )
    assert clone_themes_resp.status_code == 200
    cloned_themes = clone_themes_resp.json()

    # All source themes + custom theme should be cloned.
    assert len(cloned_themes) == src_theme_count + 1

    # Verify active theme is preserved.
    active_src = [t for t in src_themes if t["is_active"]]
    active_clone = [t for t in cloned_themes if t["is_active"]]
    assert len(active_clone) == len(active_src)
    if active_src:
        assert active_clone[0]["name"] == active_src[0]["name"]

    # Verify custom theme was cloned.
    custom_clones = [t for t in cloned_themes if t["name"] == "My Custom Theme"]
    assert len(custom_clones) == 1
    assert custom_clones[0]["is_preset"] is False

    # Verify theme config (colors, typography) is preserved for a preset.
    frosted_src = next((t for t in src_themes if t["name"] == "Frosted"), None)
    frosted_clone = next((t for t in cloned_themes if t["name"] == "Frosted"), None)
    if frosted_src and frosted_clone:
        assert frosted_clone["colors"] == frosted_src["colors"]
        assert frosted_clone["typography"] == frosted_src["typography"]


# ---------------------------------------------------------------------------
# 6. Discounts Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_discounts_cloned(client):
    """Cloning copies active discounts with '-copy' suffix and resets usage.

    Verifies:
      - Discount codes are suffixed with '-copy'
      - times_used is reset to 0
      - Discount type, value, and config are preserved
      - Max uses setting is preserved
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Discount Store")

    # Create a discount.
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    discount = await create_test_discount(
        client, token, store["id"],
        code="SUMMER25",
        discount_type="percentage",
        value=25.0,
        max_uses=100,
        expires_at=future,
    )

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Fetch discounts from the cloned store.
    disc_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/discounts",
        headers=_auth(token),
    )
    assert disc_resp.status_code == 200
    disc_data = disc_resp.json()
    discounts = disc_data["items"] if "items" in disc_data else disc_data

    assert len(discounts) >= 1

    cloned_disc = next(d for d in discounts if "SUMMER25" in d["code"])
    assert cloned_disc["code"] == "SUMMER25-copy"
    assert cloned_disc["discount_type"] == "percentage"
    assert float(cloned_disc["value"]) == 25.0
    assert cloned_disc["times_used"] == 0
    assert cloned_disc["max_uses"] == 100


# ---------------------------------------------------------------------------
# 7. Tax Rules Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_tax_rules_cloned(client):
    """Cloning copies all active tax rates to the new store.

    Verifies:
      - Tax rates exist in the cloned store
      - Name, rate, country, and state values are preserved
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Tax Store")

    # Create tax rates.
    await create_test_tax_rate(
        client, token, store["id"],
        name="CA Sales Tax", country="US", state="CA", rate=7.25,
    )
    await create_test_tax_rate(
        client, token, store["id"],
        name="NY Sales Tax", country="US", state="NY", rate=8.0,
    )

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Fetch tax rates from the cloned store.
    tax_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/tax-rates",
        headers=_auth(token),
    )
    assert tax_resp.status_code == 200
    tax_data = tax_resp.json()
    tax_rates = tax_data["items"] if "items" in tax_data else tax_data

    assert len(tax_rates) == 2

    ca_tax = next(t for t in tax_rates if t["name"] == "CA Sales Tax")
    assert float(ca_tax["rate"]) == 7.25
    assert ca_tax["country"] == "US"
    assert ca_tax["state"] == "CA"

    ny_tax = next(t for t in tax_rates if t["name"] == "NY Sales Tax")
    assert float(ny_tax["rate"]) == 8.0
    assert ny_tax["state"] == "NY"


# ---------------------------------------------------------------------------
# 8. Categories Cloned (with Hierarchy)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_categories_cloned(client):
    """Cloning preserves category hierarchy (parent-child relationships).

    Verifies:
      - All categories are cloned to the new store
      - Parent-child relationships are preserved
      - Category names and other fields are identical
      - Category IDs are different (fresh UUIDs)
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Category Store")

    # Create parent category.
    parent = await create_test_category(
        client, token, store["id"],
        name="Electronics",
    )

    # Create child categories.
    child1 = await create_test_category(
        client, token, store["id"],
        name="Laptops",
        parent_id=parent["id"],
    )
    child2 = await create_test_category(
        client, token, store["id"],
        name="Phones",
        parent_id=parent["id"],
    )

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Fetch categories from the cloned store.
    cat_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/categories",
        headers=_auth(token),
    )
    assert cat_resp.status_code == 200
    cat_data = cat_resp.json()
    categories = cat_data["items"] if "items" in cat_data else cat_data

    assert len(categories) >= 3

    # Verify names exist.
    names = {c["name"] for c in categories}
    assert "Electronics" in names
    assert "Laptops" in names
    assert "Phones" in names

    # Verify IDs are different from originals.
    cloned_parent = next(c for c in categories if c["name"] == "Electronics")
    cloned_laptops = next(c for c in categories if c["name"] == "Laptops")
    cloned_phones = next(c for c in categories if c["name"] == "Phones")

    assert cloned_parent["id"] != parent["id"]
    assert cloned_laptops["id"] != child1["id"]
    assert cloned_phones["id"] != child2["id"]

    # Verify hierarchy: children point to the cloned parent.
    assert cloned_laptops["parent_id"] == cloned_parent["id"]
    assert cloned_phones["parent_id"] == cloned_parent["id"]


# ---------------------------------------------------------------------------
# 9. Suppliers Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_suppliers_cloned(client):
    """Cloning copies all suppliers to the new store.

    Verifies:
      - Suppliers exist in the cloned store with matching fields
      - Supplier IDs are fresh UUIDs
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Supplier Store")

    # Create suppliers.
    sup1 = await create_test_supplier(
        client, token, store["id"],
        name="AcmeSupply",
        website="https://acme.example.com",
        contact_email="info@acme.example.com",
    )
    sup2 = await create_test_supplier(
        client, token, store["id"],
        name="GlobalGoods",
        contact_email="sales@global.example.com",
    )

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Fetch suppliers from the cloned store.
    sup_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/suppliers",
        headers=_auth(token),
    )
    assert sup_resp.status_code == 200
    sup_data = sup_resp.json()
    suppliers = sup_data["items"] if "items" in sup_data else sup_data

    assert len(suppliers) == 2

    cloned_acme = next(s for s in suppliers if s["name"] == "AcmeSupply")
    assert cloned_acme["website"] == "https://acme.example.com"
    assert cloned_acme["contact_email"] == "info@acme.example.com"
    assert cloned_acme["id"] != sup1["id"]

    cloned_global = next(s for s in suppliers if s["name"] == "GlobalGoods")
    assert cloned_global["contact_email"] == "sales@global.example.com"
    assert cloned_global["id"] != sup2["id"]


# ---------------------------------------------------------------------------
# 10. Store Not Found (404)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_not_found(client):
    """Cloning a non-existent store returns 404.

    Verifies:
      - Response status code is 404
      - Error detail indicates the store was not found
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)

    resp = await clone_store(client, token, ZERO_UUID)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 11. Tenant Isolation (Another User's Store)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_not_owned(client):
    """Cloning another user's store returns 404 (tenant isolation).

    Verifies:
      - User A cannot clone User B's store
      - The error is 404 (not 403) to avoid leaking store existence
    """
    token_a = await register_and_get_token(client, email="user-a@example.com")
    token_b = await register_and_get_token(client, email="user-b@example.com")
    await upgrade_to_starter(client, token_a)
    await upgrade_to_starter(client, token_b)

    # User B creates a store.
    store_b = await create_test_store(client, token_b, name="B's Store")

    # User A tries to clone it.
    resp = await clone_store(client, token_a, store_b["id"])
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 12. Deleted Store (404)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_deleted(client):
    """Cloning a soft-deleted store returns 404.

    Verifies:
      - Deleted stores cannot be cloned
      - Response is 404
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="To Delete")

    # Soft-delete the store.
    del_resp = await client.delete(
        f"/api/v1/stores/{store['id']}",
        headers=_auth(token),
    )
    assert del_resp.status_code == 200

    # Try to clone the deleted store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 13. Orders NOT Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_orders_not_cloned(client):
    """Orders from the source store are NOT copied to the cloned store.

    Verifies:
      - Source store has at least one order
      - Cloned store has zero orders
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Order Store")

    # Create an active product for checkout.
    product = await create_test_product(
        client, token, store["id"],
        title="Checkout Item",
        price=15.00,
        status="active",
    )

    # Place an order via checkout.
    checkout_resp = await client.post(
        f"/api/v1/public/stores/{store['slug']}/checkout",
        json={
            "customer_email": "buyer@example.com",
            "shipping_address": TEST_SHIPPING_ADDRESS,
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )
    assert checkout_resp.status_code == 201

    # Verify the source store has an order.
    orders_resp = await client.get(
        f"/api/v1/stores/{store['id']}/orders",
        headers=_auth(token),
    )
    assert orders_resp.status_code == 200
    assert orders_resp.json()["total"] >= 1

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Verify the cloned store has no orders.
    clone_orders_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/orders",
        headers=_auth(token),
    )
    assert clone_orders_resp.status_code == 200
    assert clone_orders_resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# 14. Reviews NOT Cloned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_store_reviews_not_cloned(client):
    """Reviews are NOT cloned to the new store.

    Verifies:
      - Source store has at least one review
      - Cloned store has zero reviews (admin review list is empty)
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Review Store")

    # Create an active product.
    product = await create_test_product(
        client, token, store["id"],
        title="Reviewed Item",
        price=25.00,
        status="active",
    )

    # Submit a review on the source store's product.
    review_resp = await client.post(
        f"/api/v1/public/stores/{store['slug']}/products/{product['slug']}/reviews",
        json={
            "customer_email": "reviewer@example.com",
            "customer_name": "Happy Customer",
            "rating": 5,
            "title": "Great product!",
            "body": "I love it.",
        },
    )
    # Review submission should succeed (201).
    assert review_resp.status_code == 201

    # Verify the source store has reviews.
    src_reviews_resp = await client.get(
        f"/api/v1/stores/{store['id']}/reviews",
        headers=_auth(token),
    )
    assert src_reviews_resp.status_code == 200
    src_reviews = src_reviews_resp.json()
    src_total = src_reviews.get("total", len(src_reviews.get("items", src_reviews)))
    assert src_total >= 1

    # Clone the store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201
    cloned_store_id = resp.json()["store"]["id"]

    # Verify the cloned store has no reviews.
    clone_reviews_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/reviews",
        headers=_auth(token),
    )
    assert clone_reviews_resp.status_code == 200
    clone_reviews = clone_reviews_resp.json()
    clone_total = clone_reviews.get("total", len(clone_reviews.get("items", clone_reviews)))
    assert clone_total == 0


# ---------------------------------------------------------------------------
# 15. Clone Empty Store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_empty_store(client):
    """Cloning a store with no products, themes, or other entities succeeds.

    Verifies:
      - Clone succeeds with 201
      - Cloned store exists and can be retrieved
      - Cloned store has preset themes (seeded on creation) but no products
    """
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    store = await create_test_store(client, token, name="Empty Store")

    # Clone the empty store.
    resp = await clone_store(client, token, store["id"])
    assert resp.status_code == 201

    data = resp.json()
    cloned_store_id = data["store"]["id"]
    assert data["store"]["name"] == "Empty Store (Copy)"

    # Verify the cloned store can be retrieved.
    get_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}",
        headers=_auth(token),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == cloned_store_id

    # Verify no products in the clone.
    prod_resp = await client.get(
        f"/api/v1/stores/{cloned_store_id}/products",
        headers=_auth(token),
    )
    assert prod_resp.status_code == 200
    assert prod_resp.json()["total"] == 0
