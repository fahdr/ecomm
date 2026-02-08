"""Tests for category CRUD, tree structure, and product assignment endpoints (Feature F9).

Covers category creation, listing (pagination), retrieval by ID, update,
deletion, hierarchical tree queries, and assigning/removing products
from categories.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Helper functions register users and create stores/categories/products
    to reduce boilerplate. Tests verify CRUD operations, parent-child
    hierarchy, slug auto-generation, and product-category associations.
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
        **kwargs: Additional category fields (parent_id, slug, position, etc.).

    Returns:
        The JSON response dictionary for the created category.
    """
    data = {"name": name, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/categories",
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
# Create Category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_category_success(client):
    """Creating a category returns 201 with the category data and auto-generated slug."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/categories",
        json={"name": "Laptops", "description": "All laptop products"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Laptops"
    assert data["slug"] == "laptops"
    assert data["description"] == "All laptop products"
    assert data["parent_id"] is None
    assert data["position"] == 0
    assert data["product_count"] == 0
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_category_no_auth(client):
    """Creating a category without authentication returns 401."""
    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/categories",
        json={"name": "Unauthorized"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List Categories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_categories_pagination(client):
    """Listing categories returns paginated results with correct metadata."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_category(client, token, store["id"], name="Cat A")
    await create_test_category(client, token, store["id"], name="Cat B")
    await create_test_category(client, token, store["id"], name="Cat C")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/categories?page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["pages"] == 2


# ---------------------------------------------------------------------------
# Get Category by ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_category_by_id(client):
    """Retrieving a category by ID returns the full category data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    cat = await create_test_category(client, token, store["id"], name="Phones")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == cat["id"]
    assert data["name"] == "Phones"


@pytest.mark.asyncio
async def test_get_category_not_found(client):
    """Retrieving a non-existent category returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/categories/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update Category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_category_success(client):
    """Updating a category's name and description succeeds and reflects changes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    cat = await create_test_category(client, token, store["id"], name="Old Name")

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}",
        json={"name": "New Name", "description": "Updated description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Updated description"


# ---------------------------------------------------------------------------
# Delete Category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_category_success(client):
    """Deleting a category returns 204 and the category is no longer retrievable."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    cat = await create_test_category(client, token, store["id"], name="To Delete")

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Verify it is gone.
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Category Tree (parent-child hierarchy)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_child_category(client):
    """Creating a child category with a parent_id links them correctly."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    parent = await create_test_category(client, token, store["id"], name="Electronics")
    child = await create_test_category(
        client, token, store["id"], name="Laptops", parent_id=parent["id"]
    )

    assert child["parent_id"] == parent["id"]
    assert child["name"] == "Laptops"


# ---------------------------------------------------------------------------
# Assign Product to Category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_product_to_category(client):
    """Assigning a product to a category returns 201 with confirmation."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    cat = await create_test_category(client, token, store["id"], name="Gadgets")
    product = await create_test_product(client, token, store["id"], title="Widget")

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}/products",
        json={"product_ids": [product["id"]]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category_id"] == cat["id"]
    assert product["id"] in data["product_ids"]
    assert "message" in data


@pytest.mark.asyncio
async def test_remove_product_from_category(client):
    """Removing a product from a category returns 204."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    cat = await create_test_category(client, token, store["id"], name="Gadgets")
    product = await create_test_product(client, token, store["id"], title="Widget")

    # Assign first.
    await client.post(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}/products",
        json={"product_ids": [product["id"]]},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Remove.
    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/categories/{cat['id']}/products/{product['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
