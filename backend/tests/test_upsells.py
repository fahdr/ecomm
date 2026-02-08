"""Tests for upsell CRUD endpoints (Feature 18 - Upsells & Cross-sells).

Covers creating, listing, getting, updating, and deleting upsell rules.
Upsell rules link a source product to a target product for recommendations.
All admin endpoints require authentication and enforce store ownership.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Upsell admin routes are at ``/api/v1/stores/{store_id}/upsells/...``.
    POST create returns 201, DELETE returns 204.
    Upsell types: ``upsell``, ``cross_sell``, ``bundle``.
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


async def create_test_upsell(
    client,
    token: str,
    store_id: str,
    source_product_id: str,
    target_product_id: str,
    upsell_type: str = "cross_sell",
) -> dict:
    """Create an upsell rule and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        source_product_id: UUID of the source product.
        target_product_id: UUID of the recommended product.
        upsell_type: Type of recommendation (upsell, cross_sell, bundle).

    Returns:
        The JSON response dictionary for the created upsell.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/upsells",
        json={
            "source_product_id": source_product_id,
            "target_product_id": target_product_id,
            "upsell_type": upsell_type,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Upsell
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_upsell_success(client):
    """Creating an upsell rule returns 201 with the upsell data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    product_a = await create_test_product(client, token, store["id"], title="Product A")
    product_b = await create_test_product(client, token, store["id"], title="Product B")

    response = await client.post(
        f"/api/v1/stores/{store['id']}/upsells",
        json={
            "source_product_id": product_a["id"],
            "target_product_id": product_b["id"],
            "upsell_type": "cross_sell",
            "title": "You might also like",
            "discount_percent": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_product_id"] == product_a["id"]
    assert data["target_product_id"] == product_b["id"]
    assert data["upsell_type"] == "cross_sell"
    assert data["title"] == "You might also like"
    assert data["store_id"] == store["id"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_upsell_no_auth(client):
    """Creating an upsell without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/upsells",
        json={
            "source_product_id": "00000000-0000-0000-0000-000000000001",
            "target_product_id": "00000000-0000-0000-0000-000000000002",
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List Upsells
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_upsells_success(client):
    """Listing upsells returns paginated results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    pa = await create_test_product(client, token, store["id"], title="Source")
    pb = await create_test_product(client, token, store["id"], title="Target 1")
    pc = await create_test_product(client, token, store["id"], title="Target 2")

    await create_test_upsell(client, token, store["id"], pa["id"], pb["id"])
    await create_test_upsell(client, token, store["id"], pa["id"], pc["id"])

    response = await client.get(
        f"/api/v1/stores/{store['id']}/upsells",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_upsells_empty(client):
    """Listing upsells with none returns an empty paginated result."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/upsells",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Update Upsell
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_upsell_success(client):
    """Updating an upsell rule changes the specified fields."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    pa = await create_test_product(client, token, store["id"], title="Src")
    pb = await create_test_product(client, token, store["id"], title="Tgt")

    upsell = await create_test_upsell(client, token, store["id"], pa["id"], pb["id"])

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/upsells/{upsell['id']}",
        json={"title": "Updated Title", "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_upsell_not_found(client):
    """Updating a non-existent upsell returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/upsells/00000000-0000-0000-0000-000000000000",
        json={"title": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Upsell
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_upsell_success(client):
    """Deleting an upsell rule returns 204 and removes it from the list."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    pa = await create_test_product(client, token, store["id"], title="S")
    pb = await create_test_product(client, token, store["id"], title="T")

    upsell = await create_test_upsell(client, token, store["id"], pa["id"], pb["id"])

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/upsells/{upsell['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Confirm it was removed from the list.
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/upsells",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_upsell_not_found(client):
    """Deleting a non-existent upsell returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/upsells/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
