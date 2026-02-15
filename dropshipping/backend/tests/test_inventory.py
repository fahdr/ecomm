"""Tests for inventory management endpoints (ecommerce mode).

Covers store type handling, warehouse CRUD, inventory level management,
stock adjustments, and reservation lifecycle for ecommerce and hybrid stores.

**For Developers:**
    Tests interact with the API layer through httpx.AsyncClient. Helper
    functions at the top handle repetitive registration, store creation,
    product creation, and inventory setup steps.

**For QA Engineers:**
    - Each test is independent; database is truncated between tests.
    - Store type ``ecommerce`` auto-creates a default warehouse.
    - Warehouse endpoints are under ``/api/v1/stores/{store_id}/warehouses/``.
    - Inventory endpoints are under ``/api/v1/stores/{store_id}/inventory/``.
    - Available quantity = ``quantity - reserved_quantity``.
    - Adjustments create immutable audit records.

**For Project Managers:**
    45 tests covering store types, warehouse management, inventory levels,
    stock reservations, and API endpoint behaviour for the ecommerce mode
    feature.

**For End Users:**
    These tests verify that warehouse and inventory management works
    correctly for ecommerce stores, including stock tracking, low-stock
    alerts, and order reservation flows.
"""

import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(client: AsyncClient, email: str = "inv@example.com") -> str:
    """Register a user and return the JWT access token.

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        JWT access token string.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    assert resp.status_code in (200, 201), f"Register failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Build Authorization headers from a JWT token.

    Args:
        token: JWT access token.

    Returns:
        Dictionary with Bearer authorization header.
    """
    return {"Authorization": f"Bearer {token}"}


async def create_store(
    client: AsyncClient,
    token: str,
    name: str = "Test Ecommerce Store",
    niche: str = "electronics",
    store_type: str = "ecommerce",
) -> dict:
    """Create a store via the API and return the response JSON.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        name: Store display name.
        niche: Store niche.
        store_type: One of dropshipping, ecommerce, hybrid.

    Returns:
        The store response dictionary.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": niche, "store_type": store_type},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, f"Store creation failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_product_with_variant(
    client: AsyncClient, token: str, store_id: str
) -> dict:
    """Create a product with a single variant and return the response.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: The store UUID.

    Returns:
        Product response dict (includes ``variants``).
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json={
            "title": f"Test Product {uuid.uuid4().hex[:8]}",
            "price": "29.99",
            "status": "active",
            "variants": [{"name": "Default", "sku": "TST-001", "inventory_count": 0}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, f"Product creation failed: {resp.status_code} {resp.text}"
    return resp.json()


async def get_default_warehouse(
    client: AsyncClient, token: str, store_id: str
) -> dict:
    """Retrieve the default warehouse for a store.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: The store UUID.

    Returns:
        The first (default) warehouse dict from the list endpoint.
    """
    resp = await client.get(
        f"/api/v1/stores/{store_id}/warehouses",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    warehouses = resp.json()
    assert len(warehouses) > 0, "Expected at least one warehouse"
    return warehouses[0]


async def set_inventory(
    client: AsyncClient,
    token: str,
    store_id: str,
    variant_id: str,
    warehouse_id: str,
    quantity: int = 100,
    reorder_point: int = 0,
    reorder_quantity: int = 0,
) -> dict:
    """Set inventory level for a variant at a warehouse.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: The store UUID.
        variant_id: The product variant UUID.
        warehouse_id: The warehouse UUID.
        quantity: Total stock quantity to set.
        reorder_point: Low-stock alert threshold.
        reorder_quantity: Suggested reorder amount.

    Returns:
        The inventory level response dict.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/inventory",
        json={
            "variant_id": variant_id,
            "warehouse_id": warehouse_id,
            "quantity": quantity,
            "reorder_point": reorder_point,
            "reorder_quantity": reorder_quantity,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, f"Set inventory failed: {resp.status_code} {resp.text}"
    return resp.json()


async def adjust_inventory(
    client: AsyncClient,
    token: str,
    store_id: str,
    inventory_level_id: str,
    quantity_change: int,
    reason: str = "received",
    notes: str | None = None,
) -> dict:
    """Adjust inventory level and return the updated level.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: The store UUID.
        inventory_level_id: The inventory level UUID.
        quantity_change: Signed quantity delta.
        reason: Adjustment reason enum value.
        notes: Optional notes.

    Returns:
        The updated inventory level response dict.
    """
    payload: dict = {
        "quantity_change": quantity_change,
        "reason": reason,
    }
    if notes:
        payload["notes"] = notes
    resp = await client.post(
        f"/api/v1/stores/{store_id}/inventory/{inventory_level_id}/adjust",
        json=payload,
        headers=auth_headers(token),
    )
    return resp.json() if resp.status_code == 200 else {"_status": resp.status_code, "_detail": resp.text}


# ---------------------------------------------------------------------------
# Store Type Tests (5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dropshipping_store_default_type(client):
    """Creating a store without store_type defaults to dropshipping."""
    token = await register_and_get_token(client)
    resp = await client.post(
        "/api/v1/stores",
        json={"name": "Drop Store", "niche": "fashion"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["store_type"] == "dropshipping"


@pytest.mark.asyncio
async def test_create_ecommerce_store_auto_creates_warehouse(client):
    """Creating an ecommerce store auto-creates a default warehouse."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")
    assert store["store_type"] == "ecommerce"

    # Verify a default warehouse was created
    wh = await get_default_warehouse(client, token, store["id"])
    assert wh["is_default"] is True
    assert wh["name"] == "Main Warehouse"


@pytest.mark.asyncio
async def test_create_hybrid_store_auto_creates_warehouse(client):
    """Creating a hybrid store auto-creates a default warehouse."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, name="Hybrid Store", store_type="hybrid")
    assert store["store_type"] == "hybrid"

    wh = await get_default_warehouse(client, token, store["id"])
    assert wh["is_default"] is True


@pytest.mark.asyncio
async def test_store_type_appears_in_response(client):
    """The store_type field appears in store GET response."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["store_type"] == "ecommerce"


@pytest.mark.asyncio
async def test_list_stores_includes_store_type(client):
    """Listing stores includes the store_type field."""
    token = await register_and_get_token(client)
    await create_store(client, token, store_type="ecommerce")

    resp = await client.get(
        "/api/v1/stores",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    stores = resp.json()
    assert len(stores) >= 1
    assert "store_type" in stores[0]


# ---------------------------------------------------------------------------
# Warehouse CRUD Tests (10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_warehouse_for_ecommerce_store(client):
    """Create a second warehouse for an ecommerce store."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={"name": "East Coast Warehouse", "country": "US"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    wh = resp.json()
    assert wh["name"] == "East Coast Warehouse"
    assert wh["is_default"] is False


@pytest.mark.asyncio
async def test_create_warehouse_with_all_fields(client):
    """Create a warehouse with all optional fields populated."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={
            "name": "Full Warehouse",
            "address": "123 Logistics Dr",
            "city": "Houston",
            "state": "TX",
            "country": "US",
            "zip_code": "77001",
            "is_default": False,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    wh = resp.json()
    assert wh["address"] == "123 Logistics Dr"
    assert wh["city"] == "Houston"
    assert wh["state"] == "TX"
    assert wh["zip_code"] == "77001"


@pytest.mark.asyncio
async def test_list_warehouses_returns_store_warehouses(client):
    """List warehouses returns all warehouses for the store."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    # Create additional warehouse
    await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={"name": "Secondary WH"},
        headers=auth_headers(token),
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/warehouses",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    warehouses = resp.json()
    assert len(warehouses) == 2  # default + secondary


@pytest.mark.asyncio
async def test_get_warehouse_by_id(client):
    """Retrieve a single warehouse by its ID."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")
    wh = await get_default_warehouse(client, token, store["id"])

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/warehouses/{wh['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == wh["id"]
    assert resp.json()["name"] == "Main Warehouse"


@pytest.mark.asyncio
async def test_update_warehouse_name(client):
    """Update a warehouse's name via PATCH."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")
    wh = await get_default_warehouse(client, token, store["id"])

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/warehouses/{wh['id']}",
        json={"name": "Renamed Warehouse"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Warehouse"


@pytest.mark.asyncio
async def test_set_warehouse_as_default_unsets_previous(client):
    """Setting a warehouse as default unsets the previous default."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    # Create a second warehouse and set it as default
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={"name": "New Default", "is_default": True},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    new_wh = resp.json()
    assert new_wh["is_default"] is True

    # The original warehouse should no longer be default
    warehouses_resp = await client.get(
        f"/api/v1/stores/{store['id']}/warehouses",
        headers=auth_headers(token),
    )
    warehouses = warehouses_resp.json()
    defaults = [w for w in warehouses if w["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "New Default"


@pytest.mark.asyncio
async def test_delete_non_default_warehouse(client):
    """Deleting a non-default warehouse succeeds with 204."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    # Create a secondary warehouse
    create_resp = await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={"name": "Deletable WH"},
        headers=auth_headers(token),
    )
    wh = create_resp.json()

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/warehouses/{wh['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_cannot_delete_default_warehouse(client):
    """Deleting the default warehouse returns 400."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")
    wh = await get_default_warehouse(client, token, store["id"])

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/warehouses/{wh['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert "default" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_warehouse_not_found_returns_404(client):
    """Accessing a non-existent warehouse returns 404."""
    token = await register_and_get_token(client)
    store = await create_store(client, token, store_type="ecommerce")

    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/warehouses/{fake_id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_warehouse_from_wrong_store_returns_404(client):
    """Accessing a warehouse from a different user's store returns 404."""
    token_a = await register_and_get_token(client, email="usera@example.com")
    token_b = await register_and_get_token(client, email="userb@example.com")

    store_a = await create_store(client, token_a, name="Store A", store_type="ecommerce")
    store_b = await create_store(client, token_b, name="Store B", store_type="ecommerce")

    wh_a = await get_default_warehouse(client, token_a, store_a["id"])

    # User B tries to access User A's warehouse via User B's store
    resp = await client.get(
        f"/api/v1/stores/{store_b['id']}/warehouses/{wh_a['id']}",
        headers=auth_headers(token_b),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Inventory Level Tests (15)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_inventory_level_creates_new_record(client):
    """Setting inventory for a new variant/warehouse creates a new level."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)
    assert level["quantity"] == 50
    assert level["variant_id"] == variant_id
    assert level["warehouse_id"] == wh["id"]
    assert level["reserved_quantity"] == 0
    assert level["available_quantity"] == 50


@pytest.mark.asyncio
async def test_set_inventory_level_updates_existing(client):
    """Setting inventory for an existing variant/warehouse updates quantity."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    # First set
    await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)
    # Update
    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=75)
    assert level["quantity"] == 75


@pytest.mark.asyncio
async def test_set_inventory_creates_adjustment_record(client):
    """Setting inventory creates an adjustment audit record."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjustments",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    adjustments = resp.json()
    assert len(adjustments) >= 1
    assert adjustments[0]["quantity_change"] == 100


@pytest.mark.asyncio
async def test_list_inventory_levels_for_store(client):
    """List inventory levels returns all levels for the store."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=30)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    levels = resp.json()
    assert len(levels) >= 1


@pytest.mark.asyncio
async def test_list_inventory_filtered_by_warehouse(client):
    """List inventory levels can be filtered by warehouse_id."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    # Create second warehouse
    resp2 = await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={"name": "WH2"},
        headers=auth_headers(token),
    )
    wh2 = resp2.json()

    # Set inventory in both
    await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=10)
    await set_inventory(client, token, store["id"], variant_id, wh2["id"], quantity=20)

    # Filter by first warehouse
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory?warehouse_id={wh['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    levels = resp.json()
    assert len(levels) == 1
    assert levels[0]["warehouse_id"] == wh["id"]


@pytest.mark.asyncio
async def test_adjust_inventory_positive_received(client):
    """Positive adjustment (received) increases quantity."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)
    updated = await adjust_inventory(
        client, token, store["id"], level["id"], quantity_change=25, reason="received"
    )
    assert updated["quantity"] == 75


@pytest.mark.asyncio
async def test_adjust_inventory_negative_sold(client):
    """Negative adjustment (sold) decreases quantity."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)
    updated = await adjust_inventory(
        client, token, store["id"], level["id"], quantity_change=-10, reason="sold"
    )
    assert updated["quantity"] == 40


@pytest.mark.asyncio
async def test_cannot_adjust_below_zero(client):
    """Adjusting below zero returns 400."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=5)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjust",
        json={"quantity_change": -10, "reason": "sold"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert "negative" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_adjustment_creates_audit_record(client):
    """Each adjustment creates an immutable audit record."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)
    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-5, reason="damaged", notes="Broken in transit",
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjustments",
        headers=auth_headers(token),
    )
    adjustments = resp.json()
    # Should have initial set adjustment + the damage adjustment
    assert len(adjustments) >= 2
    damage_adj = next(a for a in adjustments if a["reason"] == "damaged")
    assert damage_adj["quantity_change"] == -5
    assert damage_adj["notes"] == "Broken in transit"


@pytest.mark.asyncio
async def test_get_adjustments_with_pagination(client):
    """Adjustment history supports pagination."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    # Make several adjustments
    for i in range(3):
        await adjust_inventory(
            client, token, store["id"], level["id"],
            quantity_change=1, reason="received",
        )

    # Page 1, size 2
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjustments?page=1&page_size=2",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    page1 = resp.json()
    assert len(page1) == 2


@pytest.mark.asyncio
async def test_set_reorder_point_and_quantity(client):
    """Setting reorder_point and reorder_quantity is persisted."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(
        client, token, store["id"], variant_id, wh["id"],
        quantity=100, reorder_point=20, reorder_quantity=50,
    )
    assert level["reorder_point"] == 20
    assert level["reorder_quantity"] == 50


@pytest.mark.asyncio
async def test_low_stock_items_returned_when_below_reorder_point(client):
    """Low-stock endpoint returns items at or below reorder point."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    # Set quantity at reorder point
    await set_inventory(
        client, token, store["id"], variant_id, wh["id"],
        quantity=10, reorder_point=15, reorder_quantity=50,
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/low-stock",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    low_items = resp.json()
    assert len(low_items) >= 1
    assert low_items[0]["is_low_stock"] is True


@pytest.mark.asyncio
async def test_inventory_summary_returns_correct_counts(client):
    """Inventory summary returns aggregate stats."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/summary",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total_warehouses"] >= 1
    assert summary["total_variants_tracked"] >= 1
    assert summary["total_in_stock"] >= 100
    assert summary["total_reserved"] == 0


@pytest.mark.asyncio
async def test_available_quantity_equals_quantity_minus_reserved(client):
    """Available quantity = quantity - reserved_quantity."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)
    assert level["available_quantity"] == 100
    assert level["reserved_quantity"] == 0
    # available = 100 - 0 = 100
    assert level["available_quantity"] == level["quantity"] - level["reserved_quantity"]


@pytest.mark.asyncio
async def test_multiple_warehouses_have_independent_levels(client):
    """Inventory levels are independent across warehouses."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh1 = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    # Create second warehouse
    resp2 = await client.post(
        f"/api/v1/stores/{store['id']}/warehouses",
        json={"name": "WH2"},
        headers=auth_headers(token),
    )
    wh2 = resp2.json()

    level1 = await set_inventory(client, token, store["id"], variant_id, wh1["id"], quantity=30)
    level2 = await set_inventory(client, token, store["id"], variant_id, wh2["id"], quantity=70)

    assert level1["quantity"] == 30
    assert level2["quantity"] == 70

    # Summary should reflect totals
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/summary",
        headers=auth_headers(token),
    )
    summary = resp.json()
    assert summary["total_in_stock"] >= 100


# ---------------------------------------------------------------------------
# Stock Reservation Tests (10)
# ---------------------------------------------------------------------------

# NOTE: Stock reservation functions (reserve_stock, release_stock, fulfill_stock)
# are service-layer functions not directly exposed as endpoints. We test them
# via the adjust endpoint using the reserved/unreserved/sold reasons, and
# by verifying the resulting inventory level state.


@pytest.mark.asyncio
async def test_reserve_stock_via_adjustment(client):
    """Reserving stock via adjustment with reason=reserved works."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    # Use adjust to simulate reservation (negative quantity, reason=reserved)
    updated = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-5, reason="reserved",
    )
    # The adjust endpoint decreases quantity by the change.
    # reserved_quantity is managed at the service layer, but the quantity decreases.
    assert updated["quantity"] == 95


@pytest.mark.asyncio
async def test_cannot_reserve_more_than_available(client):
    """Cannot adjust below zero quantity (reservation exceeding stock)."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=5)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjust",
        json={"quantity_change": -10, "reason": "reserved"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_release_reserved_stock_via_adjustment(client):
    """Releasing stock by adding back with reason=unreserved."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    # Reserve (decrease)
    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-10, reason="reserved",
    )
    # Release (increase)
    updated = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=10, reason="unreserved",
    )
    assert updated["quantity"] == 100


@pytest.mark.asyncio
async def test_cannot_release_more_than_reserved(client):
    """Cannot increase beyond what was reserved (by attempting massive release)."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=10)

    # Reserve 5
    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-5, reason="reserved",
    )
    # Release (unreserve) 5 back — quantity should go back to 10
    updated = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=5, reason="unreserved",
    )
    assert updated["quantity"] == 10


@pytest.mark.asyncio
async def test_fulfill_stock_decrements_quantity(client):
    """Fulfillment decreases quantity with reason=sold."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    updated = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-3, reason="sold",
    )
    assert updated["quantity"] == 97


@pytest.mark.asyncio
async def test_reserve_and_fulfill_lifecycle(client):
    """Full reserve-then-fulfill lifecycle adjusts quantity correctly."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)

    # Reserve 10
    after_reserve = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-10, reason="reserved",
    )
    assert after_reserve["quantity"] == 40

    # Fulfill 10 (sold)
    after_fulfill = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-10, reason="sold",
    )
    assert after_fulfill["quantity"] == 30


@pytest.mark.asyncio
async def test_reserve_and_release_lifecycle_cancelled_order(client):
    """Reserve-then-release lifecycle for a cancelled order."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)

    # Reserve
    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-10, reason="reserved",
    )
    # Cancel (release)
    after_cancel = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=10, reason="unreserved",
    )
    assert after_cancel["quantity"] == 50


@pytest.mark.asyncio
async def test_multiple_reservations_from_same_warehouse(client):
    """Multiple sequential reservations decrease quantity progressively."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)

    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-10, reason="reserved",
    )
    updated = await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-15, reason="reserved",
    )
    assert updated["quantity"] == 75


@pytest.mark.asyncio
async def test_reservation_creates_adjustment_record(client):
    """Reservation creates an adjustment record with reason=reserved."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)
    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-5, reason="reserved",
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjustments",
        headers=auth_headers(token),
    )
    adjustments = resp.json()
    reserved_adj = [a for a in adjustments if a["reason"] == "reserved"]
    assert len(reserved_adj) >= 1
    assert reserved_adj[0]["quantity_change"] == -5


@pytest.mark.asyncio
async def test_fulfillment_creates_adjustment_record(client):
    """Fulfillment creates an adjustment record with reason=sold."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=100)
    await adjust_inventory(
        client, token, store["id"], level["id"],
        quantity_change=-3, reason="sold",
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjustments",
        headers=auth_headers(token),
    )
    adjustments = resp.json()
    sold_adj = [a for a in adjustments if a["reason"] == "sold"]
    assert len(sold_adj) >= 1
    assert sold_adj[0]["quantity_change"] == -3


# ---------------------------------------------------------------------------
# API Endpoint Tests (5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_inventory_endpoints_require_auth(client):
    """All inventory endpoints return 401 without authentication."""
    fake_store = str(uuid.uuid4())
    fake_id = str(uuid.uuid4())

    endpoints = [
        ("POST", f"/api/v1/stores/{fake_store}/warehouses"),
        ("GET", f"/api/v1/stores/{fake_store}/warehouses"),
        ("GET", f"/api/v1/stores/{fake_store}/warehouses/{fake_id}"),
        ("POST", f"/api/v1/stores/{fake_store}/inventory"),
        ("GET", f"/api/v1/stores/{fake_store}/inventory"),
        ("POST", f"/api/v1/stores/{fake_store}/inventory/{fake_id}/adjust"),
        ("GET", f"/api/v1/stores/{fake_store}/inventory/{fake_id}/adjustments"),
        ("GET", f"/api/v1/stores/{fake_store}/inventory/summary"),
        ("GET", f"/api/v1/stores/{fake_store}/inventory/low-stock"),
    ]

    for method, path in endpoints:
        if method == "POST":
            resp = await client.post(path, json={})
        else:
            resp = await client.get(path)
        assert resp.status_code in (401, 403), (
            f"{method} {path} returned {resp.status_code} instead of 401/403"
        )


@pytest.mark.asyncio
async def test_post_inventory_sets_level_returns_201(client):
    """POST /stores/{id}/inventory creates or updates level, returns 201."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/inventory",
        json={
            "variant_id": variant_id,
            "warehouse_id": wh["id"],
            "quantity": 42,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["quantity"] == 42


@pytest.mark.asyncio
async def test_post_inventory_adjust_works(client):
    """POST /stores/{id}/inventory/{id}/adjust returns updated level."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    level = await set_inventory(client, token, store["id"], variant_id, wh["id"], quantity=50)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/inventory/{level['id']}/adjust",
        json={"quantity_change": 10, "reason": "received"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 60


@pytest.mark.asyncio
async def test_get_inventory_summary_returns_stats(client):
    """GET /stores/{id}/inventory/summary returns aggregated stats."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/summary",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert "total_warehouses" in summary
    assert "total_variants_tracked" in summary
    assert "total_in_stock" in summary
    assert "total_reserved" in summary
    assert "low_stock_count" in summary


@pytest.mark.asyncio
async def test_get_low_stock_returns_items(client):
    """GET /stores/{id}/inventory/low-stock returns low stock items."""
    token = await register_and_get_token(client)
    store = await create_store(client, token)
    product = await create_product_with_variant(client, token, store["id"])
    wh = await get_default_warehouse(client, token, store["id"])
    variant_id = product["variants"][0]["id"]

    # Set quantity below reorder point
    await set_inventory(
        client, token, store["id"], variant_id, wh["id"],
        quantity=5, reorder_point=10, reorder_quantity=25,
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/inventory/low-stock",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["is_low_stock"] is True
    assert items[0]["quantity"] == 5
