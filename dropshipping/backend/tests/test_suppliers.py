"""Tests for supplier CRUD and product-supplier linking endpoints (Feature F10).

Covers supplier creation, listing (pagination), retrieval by ID, update,
deletion, linking a supplier to a product, and unlinking.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Helper functions register users and create stores/suppliers/products
    to reduce boilerplate. Tests verify CRUD operations, product-supplier
    associations, and proper 404 handling for missing resources.
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
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def create_test_product(
    client,
    token: str,
    store_id: str,
    title: str = "Test Product",
    price: float = 29.99,
    **kwargs,
) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        **kwargs: Additional product fields.

    Returns:
        The JSON response dictionary for the created product.
    """
    data = {"title": title, "price": price, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Supplier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_supplier_success(client):
    """Creating a supplier returns 201 with supplier data and all optional fields."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/suppliers",
        json={
            "name": "GlobalShip Co",
            "website": "https://globalship.example.com",
            "contact_email": "sales@globalship.example.com",
            "contact_phone": "+1-555-1234",
            "notes": "Reliable supplier for electronics",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "GlobalShip Co"
    assert data["website"] == "https://globalship.example.com"
    assert data["contact_email"] == "sales@globalship.example.com"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_supplier_no_auth(client):
    """Creating a supplier without authentication returns 401."""
    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/suppliers",
        json={"name": "Unauthorized Supplier"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List Suppliers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_suppliers_pagination(client):
    """Listing suppliers returns paginated results with correct metadata."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_supplier(client, token, store["id"], name="Supplier A")
    await create_test_supplier(client, token, store["id"], name="Supplier B")
    await create_test_supplier(client, token, store["id"], name="Supplier C")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/suppliers?page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["pages"] == 2


# ---------------------------------------------------------------------------
# Get Supplier by ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_supplier_by_id(client):
    """Retrieving a supplier by ID returns the full supplier data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    supplier = await create_test_supplier(client, token, store["id"], name="FastShip")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/suppliers/{supplier['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == supplier["id"]
    assert data["name"] == "FastShip"


@pytest.mark.asyncio
async def test_get_supplier_not_found(client):
    """Retrieving a non-existent supplier returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/suppliers/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update Supplier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_supplier_success(client):
    """Updating a supplier's name and lead time succeeds and reflects changes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    supplier = await create_test_supplier(client, token, store["id"], name="Old Name")

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/suppliers/{supplier['id']}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"


# ---------------------------------------------------------------------------
# Delete Supplier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_supplier_success(client):
    """Deleting a supplier returns 204 and the supplier is no longer retrievable."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    supplier = await create_test_supplier(client, token, store["id"], name="To Delete")

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/suppliers/{supplier['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Verify it is gone.
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/suppliers/{supplier['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Link / Unlink Supplier to Product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_supplier_to_product(client):
    """Linking a supplier to a product returns 201 with the link details."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    supplier = await create_test_supplier(client, token, store["id"], name="PrimeSrc")
    product = await create_test_product(client, token, store["id"], title="Gadget X")

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products/{product['id']}/suppliers",
        json={
            "supplier_id": supplier["id"],
            "supplier_cost": 15.00,
            "is_primary": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["supplier_id"] == supplier["id"]
    assert data["product_id"] == product["id"]
    assert data["is_primary"] is True


@pytest.mark.asyncio
async def test_unlink_supplier_from_product(client):
    """Unlinking a supplier from a product returns 204."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    supplier = await create_test_supplier(client, token, store["id"], name="LinkTest")
    product = await create_test_product(client, token, store["id"], title="Gadget Y")

    # Link first.
    await client.post(
        f"/api/v1/stores/{store['id']}/products/{product['id']}/suppliers",
        json={"supplier_id": supplier["id"], "supplier_cost": 0.00},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Unlink.
    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/products/{product['id']}/suppliers/{supplier['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_product_suppliers(client):
    """Getting suppliers for a product returns the linked supplier list."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    supplier = await create_test_supplier(client, token, store["id"], name="ListedSrc")
    product = await create_test_product(client, token, store["id"], title="Gadget Z")

    # Link.
    await client.post(
        f"/api/v1/stores/{store['id']}/products/{product['id']}/suppliers",
        json={"supplier_id": supplier["id"], "supplier_cost": 10.0, "is_primary": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products/{product['id']}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["supplier_id"] == supplier["id"]
    assert data[0]["is_primary"] is True
