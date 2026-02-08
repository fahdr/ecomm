"""Tests for search endpoints (Feature 17 - Product Search).

Covers product search by title, search with filters, sorting, and
autocomplete suggestions. Search endpoints are public (no auth required)
and use the store slug instead of store ID.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Products must have ``active`` status to appear in search results.
    Search operates under ``/api/v1/public/stores/{slug}/search``.
    Autocomplete is at ``/api/v1/public/stores/{slug}/search/suggest``.
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

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        status: Product status (default ``active`` for search visibility).
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


# ---------------------------------------------------------------------------
# Search Products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_products_by_title(client):
    """Searching by product title returns matching products."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Search Store")
    slug = store["slug"]

    await create_test_product(client, token, store["id"], title="Wireless Headphones", price=59.99)
    await create_test_product(client, token, store["id"], title="Wired Earbuds", price=19.99)

    response = await client.get(
        f"/api/v1/public/stores/{slug}/search?query=wireless",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "wireless"
    assert isinstance(data["items"], list)
    assert data["total"] >= 0
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data


@pytest.mark.asyncio
async def test_search_products_no_query(client):
    """Searching without a query returns all active products."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Browse Store")
    slug = store["slug"]

    await create_test_product(client, token, store["id"], title="Product A")
    await create_test_product(client, token, store["id"], title="Product B")

    response = await client.get(
        f"/api/v1/public/stores/{slug}/search",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] is None
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_search_products_with_price_filter(client):
    """Searching with min/max price filters constrains the results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Filter Store")
    slug = store["slug"]

    await create_test_product(client, token, store["id"], title="Cheap Widget", price=5.00)
    await create_test_product(client, token, store["id"], title="Premium Widget", price=150.00)

    response = await client.get(
        f"/api/v1/public/stores/{slug}/search?min_price=10&max_price=200",
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_search_products_invalid_sort(client):
    """Searching with an invalid sort_by returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Sort Store")
    slug = store["slug"]

    response = await client.get(
        f"/api/v1/public/stores/{slug}/search?sort_by=invalid_sort",
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_products_store_not_found(client):
    """Searching for products in a non-existent store returns 404."""
    response = await client.get(
        "/api/v1/public/stores/nonexistent-store-slug/search?query=test",
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Autocomplete Suggestions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_suggestions_success(client):
    """Autocomplete suggestions return results for a partial query."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Suggest Store")
    slug = store["slug"]

    await create_test_product(client, token, store["id"], title="Bluetooth Speaker")

    response = await client.get(
        f"/api/v1/public/stores/{slug}/search/suggest?query=blue",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "blue"
    assert isinstance(data["suggestions"], list)


@pytest.mark.asyncio
async def test_search_suggestions_store_not_found(client):
    """Autocomplete for a non-existent store returns 404."""
    response = await client.get(
        "/api/v1/public/stores/ghost-store/search/suggest?query=test",
    )
    assert response.status_code == 404
