"""Tests for bulk operations endpoints (Feature F26).

Covers bulk updating products, bulk deleting products, and bulk price
adjustment. Tests verify the per-item success/failure result structure
and that partial failures are reported correctly.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Bulk endpoints are store-scoped: ``/stores/{store_id}/bulk/products/...``.
    Maximum 100 products per bulk operation. Partial failures return 200
    with a results array showing per-item status.
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
) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        status: Product status.

    Returns:
        The JSON response dictionary for the created product.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json={"title": title, "price": price, "status": status},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Bulk Update Products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_update_products_success(client):
    """Bulk updating products returns per-item results with successes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    p1 = await create_test_product(client, token, store["id"], title="Widget A")
    p2 = await create_test_product(client, token, store["id"], title="Widget B")

    response = await client.post(
        f"/api/v1/stores/{store['id']}/bulk/products/update",
        json={
            "product_ids": [p1["id"], p2["id"]],
            "updates": {"title": "Widget Updated"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["succeeded"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert result["success"] is True


@pytest.mark.asyncio
async def test_bulk_update_nonexistent_product(client):
    """Bulk update with a non-existent product ID reports that item as failed."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/bulk/products/update",
        json={
            "product_ids": ["00000000-0000-0000-0000-000000000000"],
            "updates": {"title": "Ghost"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["failed"] >= 1


@pytest.mark.asyncio
async def test_bulk_update_no_auth(client):
    """Bulk updating without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/bulk/products/update",
        json={
            "product_ids": ["00000000-0000-0000-0000-000000000000"],
            "updates": {"title": "No Auth"},
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Bulk Delete Products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_delete_products_success(client):
    """Bulk deleting products returns per-item results with successes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    p1 = await create_test_product(client, token, store["id"], title="Del A")
    p2 = await create_test_product(client, token, store["id"], title="Del B")

    response = await client.post(
        f"/api/v1/stores/{store['id']}/bulk/products/delete",
        json={"product_ids": [p1["id"], p2["id"]]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["succeeded"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_bulk_delete_nonexistent_products(client):
    """Bulk delete with non-existent product IDs reports failures."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/bulk/products/delete",
        json={"product_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["failed"] >= 1


# ---------------------------------------------------------------------------
# Bulk Price Adjustment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_price_adjustment_percentage(client):
    """Bulk price adjustment with percentage returns per-item results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    p1 = await create_test_product(client, token, store["id"], title="Priced A", price=100.00)
    p2 = await create_test_product(client, token, store["id"], title="Priced B", price=50.00)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/bulk/products/price",
        json={
            "product_ids": [p1["id"], p2["id"]],
            "adjustment_type": "percentage",
            "adjustment_value": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["succeeded"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_bulk_price_adjustment_fixed(client):
    """Bulk price adjustment with fixed amount returns per-item results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    p1 = await create_test_product(client, token, store["id"], title="Fixed A", price=100.00)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/bulk/products/price",
        json={
            "product_ids": [p1["id"]],
            "adjustment_type": "fixed",
            "adjustment_value": -5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["succeeded"] == 1


@pytest.mark.asyncio
async def test_bulk_price_adjustment_store_not_found(client):
    """Bulk price adjustment on a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/bulk/products/price",
        json={
            "product_ids": ["00000000-0000-0000-0000-000000000000"],
            "adjustment_type": "percentage",
            "adjustment_value": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
